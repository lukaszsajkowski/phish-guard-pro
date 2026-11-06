"""Seams used by the Scammer Arena harness: persona seed, regen count, errors."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from phishguard.agents.conversation import (
    ConversationAgent,
    ResponseGenerationError,
    SafetyRegenerationExhaustedError,
)
from phishguard.llm import LLMRequestError, LLMResponse
from phishguard.models.classification import AttackType
from phishguard.models.conversation import ResponseGenerationResult
from phishguard.models.persona import PersonaProfile, PersonaType
from phishguard.orchestrator.nodes import generate_response, select_persona


@pytest.fixture(autouse=True)
def _basal_off(monkeypatch):
    from phishguard.core import get_settings

    monkeypatch.setenv("BASAL_URL", "")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _classification():
    return {
        "attack_type": "romance_scam",
        "confidence": 90.0,
        "reasoning": "r",
        "classification_time_ms": 1,
    }


def _persona() -> PersonaProfile:
    return PersonaProfile(
        persona_type=PersonaType.NAIVE_RETIREE,
        name="Jan Kowalski",
        age=70,
        style_description="polite",
        background="retired",
    )


def _agent_inputs():
    return {
        "persona": _persona(),
        "email_content": "Hello dear",
        "attack_type": AttackType.ROMANCE_SCAM,
    }


@pytest.mark.asyncio
async def test_select_persona_with_seed_is_deterministic():
    state = {"classification": _classification(), "persona_seed": 1234}

    first = await select_persona(state)
    second = await select_persona(state)

    assert first["persona"] == second["persona"]


@pytest.mark.asyncio
async def test_select_persona_without_seed_still_works():
    result = await select_persona({"classification": _classification()})

    assert result["persona"]["name"]


@pytest.mark.asyncio
async def test_generate_response_exposes_agent_regeneration_count():
    agent_result = ResponseGenerationResult(
        content="Hello there",
        generation_time_ms=5,
        safety_validated=True,
        regeneration_count=2,
        used_fallback_model=False,
    )
    state = {
        "persona": {
            "persona_type": "naive_retiree",
            "name": "Jan Kowalski",
            "age": 70,
            "style_description": "polite",
            "background": "retired",
        },
        "classification": _classification(),
        "email_content": "Hello dear",
        "conversation_history": [],
    }

    with (
        patch(
            "phishguard.agents.conversation.create_llm_client",
            return_value=MagicMock(),
        ),
        patch.object(
            ConversationAgent,
            "generate_response",
            new=AsyncMock(return_value=agent_result),
        ),
    ):
        out = await generate_response(state)

    assert out["agent_regeneration_count"] == 2


@pytest.mark.asyncio
async def test_exhausted_safety_raises_dedicated_error():
    client = MagicMock()
    client.chat_completion = AsyncMock(
        return_value=LLMResponse(content="draft", model_used="fake")
    )
    validator = MagicMock()
    validator.validate.return_value = MagicMock(
        is_safe=False, violation_summary="pii leak"
    )
    agent = ConversationAgent(llm_client=client, validator=validator)

    with pytest.raises(SafetyRegenerationExhaustedError) as exc_info:
        await agent.generate_response(**_agent_inputs())

    assert isinstance(exc_info.value, ResponseGenerationError)


@pytest.mark.asyncio
async def test_llm_failure_is_not_safety_exhausted():
    client = MagicMock()
    client.chat_completion = AsyncMock(side_effect=LLMRequestError("boom"))
    agent = ConversationAgent(llm_client=client)

    with pytest.raises(ResponseGenerationError) as exc_info:
        await agent.generate_response(**_agent_inputs())

    assert not isinstance(exc_info.value, SafetyRegenerationExhaustedError)
