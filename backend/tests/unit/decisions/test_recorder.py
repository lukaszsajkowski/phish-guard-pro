"""Tests for the decision/usage recorder."""

import logging
from unittest.mock import MagicMock, patch

import pytest

from phishguard.decisions.recorder import (
    DecisionRecord,
    record_decision,
    record_llm_usage,
)

PATCH_TARGET = "phishguard.decisions.recorder._get_supabase_client"


def _record() -> DecisionRecord:
    return DecisionRecord(
        session_id="s-1",
        node="profiler.attack_type",
        mode="shadow",
        options=["nigerian_419", "not_phishing"],
        threshold=0.9,
        final_answer="nigerian_419",
        source="llm",
        basal_answer="nigerian_419",
        basal_probabilities={"nigerian_419": 0.95},
        basal_confidence=0.95,
        basal_ms=12,
        llm_answer="nigerian_419",
        llm_ms=800,
    )


@pytest.mark.asyncio
async def test_record_decision_inserts_row() -> None:
    client = MagicMock()
    with patch(PATCH_TARGET, return_value=client):
        await record_decision(_record())

    client.table.assert_called_with("decisions")
    row = client.table.return_value.insert.call_args.args[0]
    assert row["final_answer"] == "nigerian_419"
    assert row["source"] == "llm"
    assert row["mode"] == "shadow"
    assert row["session_id"] == "s-1"
    assert not {"email", "email_text", "text", "state", "content"} & set(row)
    client.table.return_value.insert.return_value.execute.assert_called_once()


@pytest.mark.asyncio
async def test_record_decision_swallows_errors(
    caplog: pytest.LogCaptureFixture,
) -> None:
    client = MagicMock()
    client.table.return_value.insert.return_value.execute.side_effect = Exception(
        "db down"
    )
    with (
        patch(PATCH_TARGET, return_value=client),
        caplog.at_level(logging.WARNING),
    ):
        result = await record_decision(_record())

    assert result is None
    assert any(r.levelno == logging.WARNING for r in caplog.records)


@pytest.mark.asyncio
async def test_record_llm_usage_inserts_row() -> None:
    client = MagicMock()
    with patch(PATCH_TARGET, return_value=client):
        await record_llm_usage(None, "profiler", "gpt-4o", 100, 20, 450)

    client.table.assert_called_with("llm_usage")
    row = client.table.return_value.insert.call_args.args[0]
    assert row == {
        "session_id": None,
        "agent": "profiler",
        "model": "gpt-4o",
        "prompt_tokens": 100,
        "completion_tokens": 20,
        "latency_ms": 450,
    }


@pytest.mark.asyncio
async def test_record_llm_usage_swallows_errors(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with (
        patch(PATCH_TARGET, side_effect=Exception("no client")),
        caplog.at_level(logging.WARNING),
    ):
        await record_llm_usage("s", "eval", "m", 1, 1, 1)
    assert any(r.levelno == logging.WARNING for r in caplog.records)
