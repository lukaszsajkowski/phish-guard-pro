"""Token budget must leave room for hidden reasoning tokens."""

import json
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from phishguard.agents import conversation, profiler
from phishguard.decisions import DecisionService
from phishguard.llm import LLMResponse
from phishguard.llm.budget import warn_if_budget_exhausted
from phishguard.models.classification import AttackType

MIN_BUDGET = 2000


def _llm(content: str) -> MagicMock:
    llm = MagicMock()
    llm.chat_completion = AsyncMock(
        return_value=LLMResponse(
            content=content, model_used="gpt-6-luna", completion_tokens=50
        )
    )
    return llm


@pytest.mark.asyncio
async def test_profiler_token_budget_leaves_room_for_reasoning(monkeypatch):
    monkeypatch.setenv("BASAL_URL", "")
    from phishguard.core import get_settings

    get_settings.cache_clear()
    llm = _llm(
        json.dumps({"attack_type": "nigerian_419", "confidence": 90, "reasoning": "x"})
    )
    off = DecisionService(
        basal=None, mode="off", threshold_for=lambda n: 0.9, recorder=None
    )
    agent = profiler.ProfilerAgent(llm_client=llm, decision_service=off)

    await agent.classify("email")

    assert profiler.CLASSIFICATION_MAX_TOKENS >= MIN_BUDGET
    kwargs = llm.chat_completion.await_args.kwargs
    assert kwargs["max_tokens"] == profiler.CLASSIFICATION_MAX_TOKENS
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_conversation_token_budget_leaves_room_for_reasoning():
    llm = _llm(json.dumps({"response": "Hi there"}))
    validator = MagicMock()
    validator.validate.return_value = MagicMock(is_safe=True)
    agent = conversation.ConversationAgent(llm_client=llm, validator=validator)

    with patch.object(conversation, "get_conversation_system_prompt", return_value="s"):
        await agent.generate_response(
            persona=MagicMock(),
            email_content="hello",
            attack_type=AttackType.NIGERIAN_419,
        )

    assert conversation.CONVERSATION_MAX_TOKENS >= MIN_BUDGET
    kwargs = llm.chat_completion.await_args.kwargs
    assert kwargs["max_tokens"] == conversation.CONVERSATION_MAX_TOKENS


def test_empty_response_at_budget_logs_warning(caplog):
    cap = 2000
    exhausted = LLMResponse(content="", model_used="gpt-6-luna", completion_tokens=cap)
    normal = LLMResponse(content="ok", model_used="gpt-6-luna", completion_tokens=40)
    short_empty = LLMResponse(content="", model_used="gpt-6-luna", completion_tokens=3)

    with caplog.at_level(logging.WARNING):
        warn_if_budget_exhausted(normal, agent="profiler", max_tokens=cap)
        warn_if_budget_exhausted(short_empty, agent="profiler", max_tokens=cap)
    assert caplog.records == []

    with caplog.at_level(logging.WARNING):
        warn_if_budget_exhausted(exhausted, agent="profiler", max_tokens=cap)
    assert len(caplog.records) == 1
    msg = caplog.records[0].getMessage()
    assert "token budget exhausted" in msg
    assert "profiler" in msg and "gpt-6-luna" in msg and "2000" in msg
