"""Tests for the Basal in-role check (US-050)."""

from unittest.mock import AsyncMock

import pytest

from phishguard.agents.prompts.in_role_basal import IN_ROLE_CRITERIA
from phishguard.decisions import SignalDecision
from phishguard.decisions.basal_client import BasalAnswer
from phishguard.models.in_role import IN_ROLE_WARNING_MESSAGE, InRoleWarning
from phishguard.models.persona import PersonaProfile, PersonaType
from phishguard.services.in_role_check import (
    IN_ROLE_NODE,
    build_in_role_state,
    check_in_role,
)


@pytest.fixture
def persona() -> PersonaProfile:
    return PersonaProfile(
        persona_type=PersonaType.NAIVE_RETIREE,
        name="Margaret Thompson",
        age=72,
        style_description="Trusting and polite, easily confused by technology",
        background="Retired teacher, recently widowed",
    )


def _service(decision: SignalDecision | Exception) -> AsyncMock:
    service = AsyncMock()
    if isinstance(decision, Exception):
        service.decide_signal.side_effect = decision
    else:
        service.decide_signal.return_value = decision
    return service


def _basal(answer: str, p: float) -> BasalAnswer:
    other = "in_role" if answer == "breaks_role" else "breaks_role"
    return BasalAnswer(
        answer=answer,
        probabilities={answer: p, other: 1 - p},
        confidence=p,
        latency_ms=5,
    )


async def test_breaks_role_from_basal_returns_warning(persona):
    service = _service(
        SignalDecision(
            source="basal", answer="breaks_role", basal=_basal("breaks_role", 0.87)
        )
    )

    result = await check_in_role(persona, "I am an AI.", "s1", "m1", service=service)

    assert result == InRoleWarning(message=IN_ROLE_WARNING_MESSAGE, confidence=0.87)


async def test_in_role_from_basal_returns_none(persona):
    service = _service(
        SignalDecision(source="basal", answer="in_role", basal=_basal("in_role", 0.9))
    )

    assert await check_in_role(persona, "Oh dear", "s1", "m1", service=service) is None


async def test_source_none_returns_none(persona):
    service = _service(SignalDecision(source="none", answer=None, basal=None))

    assert await check_in_role(persona, "Oh dear", "s1", "m1", service=service) is None


async def test_decide_signal_error_returns_none(persona):
    service = _service(RuntimeError("boom"))

    assert await check_in_role(persona, "Oh dear", "s1", "m1", service=service) is None


async def test_state_and_ids_passed_through(persona):
    service = _service(SignalDecision(source="none", answer=None, basal=None))

    await check_in_role(persona, "Hello there friend", "s1", "m1", service=service)

    args = service.decide_signal.call_args.args
    kwargs = service.decide_signal.call_args.kwargs
    question = kwargs.get("question", args[0] if args else None)
    state = kwargs.get("state", args[1] if len(args) > 1 else None)
    assert question.node == IN_ROLE_NODE
    assert "Hello there friend" in state
    assert persona.style_description in state
    assert "Margaret" not in state
    assert "widowed" not in state
    assert kwargs["session_id"] == "s1"
    assert kwargs["message_id"] == "m1"
    assert kwargs.get("reference_kind") is None
    assert kwargs.get("reference_answer") is None


def test_build_in_role_state_layout(persona):
    state = build_in_role_state(persona, "Hi")

    assert state == (
        "Naive Retiree, age 72\n"
        "Trusting and polite, easily confused by technology\n"
        "\n"
        "Reply:\nHi"
    )


def test_criteria_keys():
    assert set(IN_ROLE_CRITERIA) == {"in_role", "breaks_role"}
