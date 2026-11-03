"""Unit tests for DecisionService.decide_signal (Basal next to a reference)."""

import asyncio
from unittest.mock import AsyncMock, patch

from phishguard.decisions import (
    ChoiceQuestion,
    DecisionService,
    SignalDecision,
)
from phishguard.decisions.basal_client import (
    BasalAnswer,
    BasalClient,
    BasalUnavailableError,
)
from phishguard.decisions.cascade import drain_background_tasks
from phishguard.decisions.recorder import DecisionRecord

LANGUAGE_PATCH = "phishguard.decisions.cascade.is_basal_language"

QUESTION = ChoiceQuestion(
    node="response.in_role",
    instructions="Does the reply stay in role?",
    criteria={"in_role": "Stays in role", "breaks_role": "Breaks role"},
)
STATE = "Sure, I can send the money tomorrow."


def _answer(answer: str = "breaks_role", confidence: float = 0.9) -> BasalAnswer:
    other = "in_role" if answer == "breaks_role" else "breaks_role"
    return BasalAnswer(
        answer=answer,
        probabilities={answer: confidence, other: round(1 - confidence, 4)},
        confidence=confidence,
        latency_ms=5,
    )


def _basal(answer: BasalAnswer | None = None, error: Exception | None = None):
    basal = AsyncMock(spec=BasalClient)
    if error is not None:
        basal.ask_choice.side_effect = error
    else:
        basal.ask_choice.return_value = answer or _answer()
    return basal


def _service(basal, mode, rows, threshold: float = 0.9, recorder=None):
    async def default_recorder(record: DecisionRecord) -> None:
        rows.append(record)

    return DecisionService(
        basal=basal,
        mode=mode,
        threshold_for=lambda node: threshold,
        basal_model="basal-test",
        recorder=recorder or default_recorder,
    )


async def _signal(service, session_id="s1", reference_answer=None):
    return await service.decide_signal(
        QUESTION,
        STATE,
        session_id,
        message_id="m1",
        reference_kind="regex" if reference_answer is not None else None,
        reference_answer=reference_answer,
    )


async def test_off_returns_reference_without_basal_or_row():
    rows: list[DecisionRecord] = []
    basal = _basal()
    service = _service(basal, "off", rows)

    result = await _signal(service, reference_answer="engaged")

    assert result == SignalDecision("regex", "engaged", None)
    basal.ask_choice.assert_not_called()
    assert rows == []


async def test_shadow_returns_reference_before_basal_finishes():
    rows: list[DecisionRecord] = []
    release = asyncio.Event()
    basal = _basal()

    async def slow_ask(*args, **kwargs):
        await release.wait()
        return _answer()

    basal.ask_choice.side_effect = slow_ask
    service = _service(basal, "shadow", rows)

    with patch(LANGUAGE_PATCH, return_value=True):
        result = await _signal(service, reference_answer="engaged")
        assert result == SignalDecision("regex", "engaged", None)
        assert rows == []
        release.set()
        await drain_background_tasks()

    assert len(rows) == 1
    row = rows[0]
    assert row.mode == "shadow"
    assert row.message_id == "m1"
    assert row.source == "regex"
    assert row.final_answer == "engaged"
    assert row.reference_kind == "regex"
    assert row.reference_answer == "engaged"
    assert row.basal_answer == "breaks_role"
    assert row.llm_answer is None
    assert row.llm_model is None
    assert row.llm_ms is None


async def test_shadow_below_threshold_sets_skip_reason():
    rows: list[DecisionRecord] = []
    service = _service(_basal(_answer(confidence=0.6)), "shadow", rows)

    with patch(LANGUAGE_PATCH, return_value=True):
        result = await _signal(service)
        await drain_background_tasks()

    assert result == SignalDecision("none", None, None)
    assert rows[0].skip_reason == "below_threshold"
    assert rows[0].source == "none"
    assert rows[0].final_answer == ""


async def test_shadow_without_session_does_not_call_basal():
    rows: list[DecisionRecord] = []
    basal = _basal()
    service = _service(basal, "shadow", rows)

    with patch(LANGUAGE_PATCH, return_value=True):
        result = await _signal(service, session_id=None, reference_answer="x")
        await drain_background_tasks()

    assert result == SignalDecision("regex", "x", None)
    basal.ask_choice.assert_not_called()
    assert rows == []


async def test_live_at_threshold_uses_basal():
    rows: list[DecisionRecord] = []
    basal_answer = _answer(confidence=0.9)
    service = _service(_basal(basal_answer), "live", rows, threshold=0.9)

    with patch(LANGUAGE_PATCH, return_value=True):
        result = await _signal(service, reference_answer="engaged")

    assert result == SignalDecision("basal", "breaks_role", basal_answer)
    assert len(rows) == 1
    assert rows[0].source == "basal"
    assert rows[0].final_answer == "breaks_role"
    assert rows[0].skip_reason is None
    assert rows[0].reference_answer == "engaged"
    assert rows[0].llm_answer is None


async def test_live_below_threshold_falls_back_to_reference():
    rows: list[DecisionRecord] = []
    basal_answer = _answer(confidence=0.5)
    service = _service(_basal(basal_answer), "live", rows)

    with patch(LANGUAGE_PATCH, return_value=True):
        result = await _signal(service, reference_answer="engaged")

    assert result == SignalDecision("regex", "engaged", basal_answer)
    assert rows[0].source == "regex"
    assert rows[0].final_answer == "engaged"
    assert rows[0].skip_reason == "below_threshold"
    assert rows[0].basal_answer == "breaks_role"
    assert rows[0].reference_kind == "regex"


async def test_live_below_threshold_without_reference_is_none():
    rows: list[DecisionRecord] = []
    basal_answer = _answer(confidence=0.5)
    service = _service(_basal(basal_answer), "live", rows)

    with patch(LANGUAGE_PATCH, return_value=True):
        result = await _signal(service)

    assert result == SignalDecision("none", None, basal_answer)
    assert rows[0].source == "none"
    assert rows[0].final_answer == ""
    assert rows[0].reference_kind is None


async def test_live_basal_timeout_returns_reference():
    rows: list[DecisionRecord] = []
    service = _service(
        _basal(error=BasalUnavailableError("slow", is_timeout=True)), "live", rows
    )

    with patch(LANGUAGE_PATCH, return_value=True):
        result = await _signal(service, reference_answer="engaged")

    assert result == SignalDecision("regex", "engaged", None)
    assert rows[0].skip_reason == "timeout"
    assert rows[0].basal_answer is None


async def test_live_language_gate_rejection_returns_reference():
    rows: list[DecisionRecord] = []
    basal = _basal()
    service = _service(basal, "live", rows)

    with patch(LANGUAGE_PATCH, return_value=False):
        result = await _signal(service)

    assert result == SignalDecision("none", None, None)
    basal.ask_choice.assert_not_called()
    assert rows[0].skip_reason == "language"


async def test_live_recorder_error_still_returns_result():
    async def broken(record: DecisionRecord) -> None:
        raise RuntimeError("db down")

    service = _service(_basal(), "live", [], recorder=broken)

    with patch(LANGUAGE_PATCH, return_value=True):
        result = await _signal(service, reference_answer="engaged")

    assert result.source == "basal"
    assert result.answer == "breaks_role"
