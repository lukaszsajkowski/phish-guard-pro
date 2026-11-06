"""Tests for context-local LLM usage tracking."""

import asyncio

import pytest

from phishguard.llm import LLMClient, LLMClientConfig
from phishguard.llm import usage as usage_module
from phishguard.llm.providers import Completion
from phishguard.llm.usage import UsageEntry, UsageLog, track_usage


class FakeProvider:
    async def complete(self, messages, model, temperature, max_tokens):
        return Completion("ok", 10, 5)

    async def close(self) -> None:
        pass


def _client() -> LLMClient:
    return LLMClient(config=LLMClientConfig(), provider=FakeProvider())


MSGS = [{"role": "user", "content": "hi"}]


async def test_track_usage_records_each_completion():
    client = _client()
    with track_usage() as log:
        await client.chat_completion(MSGS)
        await client.chat_completion(MSGS)
    assert len(log.entries) == 2
    assert log.entries[0].prompt_tokens == 10
    assert log.entries[0].completion_tokens == 5


async def test_no_active_log_records_nothing():
    await _client().chat_completion(MSGS)
    assert usage_module._active_log.get() is None


async def test_usage_is_isolated_between_concurrent_tasks():
    client = _client()

    async def run(n: int) -> UsageLog:
        with track_usage() as log:
            for _ in range(n):
                await client.chat_completion(MSGS)
                await asyncio.sleep(0)
        return log

    log_a, log_b = await asyncio.gather(run(1), run(3))
    assert len(log_a.entries) == 1
    assert len(log_b.entries) == 3


async def test_nested_blocks_record_into_innermost_only():
    client = _client()
    with track_usage() as outer:
        with track_usage() as inner:
            await client.chat_completion(MSGS)
        await client.chat_completion(MSGS)
    assert len(inner.entries) == 1
    assert len(outer.entries) == 1


def test_total_cost_uses_price_table():
    log = UsageLog()
    log.entries.append(
        UsageEntry(
            model="gpt-6-luna",
            prompt_tokens=1_000_000,
            completion_tokens=1_000_000,
            latency_ms=1,
        )
    )
    assert log.total_cost_usd() == pytest.approx(0.60)


def test_total_cost_propagates_unpriced_model():
    log = UsageLog()
    log.entries.append(
        UsageEntry(
            model="no-such-model", prompt_tokens=1, completion_tokens=1, latency_ms=1
        )
    )
    with pytest.raises(KeyError):
        log.total_cost_usd()
