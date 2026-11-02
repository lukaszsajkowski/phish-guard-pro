"""Unit tests for the Basal -> LLM decision cascade."""

import asyncio
import gc
import logging
import time
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, patch

import pytest

from phishguard.core import Settings
from phishguard.decisions import (
    ChoiceQuestion,
    Decision,
    DecisionService,
    cascade,
    create_decision_service,
)
from phishguard.decisions.basal_client import (
    BasalAnswer,
    BasalClient,
    BasalUnavailableError,
)
from phishguard.decisions.cascade import drain_background_tasks
from phishguard.decisions.recorder import DecisionRecord
from phishguard.llm.client import LLMRequestError

LANGUAGE_PATCH = "phishguard.decisions.cascade.is_basal_language"

QUESTION = ChoiceQuestion(
    node="profiler.attack_type",
    instructions="Classify the email.",
    criteria={"romance_scam": "Romance scam", "nigerian_419": "Advance fee"},
)
STATE = "Dear friend, I am a prince and need your help."


class FakeLLMResult:
    def __init__(self, answer: str = "nigerian_419", model: str = "gpt-test"):
        self.answer = answer
        self.model = model


def _basal_answer(answer: str = "romance_scam", confidence: float = 0.95):
    other = "nigerian_419" if answer == "romance_scam" else "romance_scam"
    return BasalAnswer(
        answer=answer,
        probabilities={answer: confidence, other: round(1 - confidence, 4)},
        confidence=confidence,
        latency_ms=7,
    )


def _basal(answer: BasalAnswer | None = None, error: Exception | None = None):
    basal = AsyncMock(spec=BasalClient)
    if error is not None:
        basal.ask_choice.side_effect = error
    else:
        basal.ask_choice.return_value = answer or _basal_answer()
    return basal


def _service(basal, mode, rows: list[DecisionRecord], threshold: float = 0.9):
    async def recorder(record: DecisionRecord) -> None:
        rows.append(record)

    return DecisionService(
        basal=basal,
        mode=mode,
        threshold_for=lambda node: threshold,
        basal_model="basal-test",
        recorder=recorder,
    )


def _llm(result: FakeLLMResult | None = None, error: Exception | None = None):
    llm_call = AsyncMock()
    if error is not None:
        llm_call.side_effect = error
    else:
        llm_call.return_value = result or FakeLLMResult()
    return llm_call


async def _decide(service, llm_call, session_id: str | None = "s-1") -> Decision:
    return await service.decide_choice(
        QUESTION,
        STATE,
        session_id,
        llm_call=llm_call,
        llm_answer=lambda r: r.answer,
        llm_model=lambda r: r.model,
    )


@pytest.fixture(autouse=True)
def _language_ok():
    with patch(LANGUAGE_PATCH, return_value=True) as gate:
        yield gate


@pytest.fixture(autouse=True)
async def _drain() -> AsyncIterator[None]:
    yield
    await drain_background_tasks()


# --- off -------------------------------------------------------------------


async def test_off_uses_only_llm_and_writes_no_row():
    recorder = AsyncMock()
    basal = _basal()
    service = DecisionService(
        basal=basal,
        mode="off",
        threshold_for=lambda node: 0.9,
        recorder=recorder,
    )
    llm_call = _llm()

    decision = await _decide(service, llm_call)

    assert decision.source == "llm"
    assert decision.answer == "nigerian_419"
    assert decision.basal is None
    assert isinstance(decision.llm_result, FakeLLMResult)
    basal.ask_choice.assert_not_awaited()
    llm_call.assert_awaited_once()
    recorder.assert_not_called()


# --- live ------------------------------------------------------------------


async def test_live_non_basal_language_skips_basal(_language_ok):
    _language_ok.return_value = False
    rows: list[DecisionRecord] = []
    basal = _basal()
    service = _service(basal, "live", rows)

    decision = await _decide(service, _llm())

    basal.ask_choice.assert_not_awaited()
    assert decision.source == "llm"
    assert decision.answer == "nigerian_419"
    assert rows[0].skip_reason == "language"
    assert rows[0].mode == "live"


async def test_live_language_gate_error_treated_as_unavailable(_language_ok):
    _language_ok.side_effect = RuntimeError("model missing")
    rows: list[DecisionRecord] = []
    basal = _basal()
    service = _service(basal, "live", rows)

    decision = await _decide(service, _llm())

    basal.ask_choice.assert_not_awaited()
    assert decision.source == "llm"
    assert rows[0].skip_reason == "unavailable"


async def test_live_basal_unavailable_falls_back_to_llm():
    rows: list[DecisionRecord] = []
    service = _service(_basal(error=BasalUnavailableError("down")), "live", rows)

    decision = await _decide(service, _llm())

    assert decision.source == "llm"
    assert decision.answer == "nigerian_419"
    assert decision.basal is None
    assert rows[0].skip_reason == "unavailable"
    assert rows[0].basal_answer is None


async def test_live_basal_timeout_records_timeout():
    rows: list[DecisionRecord] = []
    error = BasalUnavailableError("slow", is_timeout=True)
    service = _service(_basal(error=error), "live", rows)

    decision = await _decide(service, _llm())

    assert decision.source == "llm"
    assert rows[0].skip_reason == "timeout"


async def test_live_confident_basal_decides_without_llm():
    rows: list[DecisionRecord] = []
    answer = _basal_answer("romance_scam", 0.95)
    service = _service(_basal(answer), "live", rows)
    llm_call = _llm()

    decision = await _decide(service, llm_call)

    llm_call.assert_not_awaited()
    assert decision.source == "basal"
    assert decision.answer == "romance_scam"
    assert decision.basal == answer
    assert decision.llm_result is None
    row = rows[0]
    assert row.source == "basal"
    assert row.final_answer == "romance_scam"
    assert row.skip_reason is None
    assert row.basal_answer == "romance_scam"
    assert row.basal_confidence == 0.95
    assert row.basal_probabilities == answer.probabilities
    assert row.basal_ms == 7
    assert row.basal_model == "basal-test"
    assert row.threshold == 0.9
    assert row.llm_answer is None


async def test_live_threshold_is_inclusive():
    rows: list[DecisionRecord] = []
    service = _service(_basal(_basal_answer("romance_scam", 0.9)), "live", rows, 0.9)
    llm_call = _llm()

    decision = await _decide(service, llm_call)

    assert decision.source == "basal"
    llm_call.assert_not_awaited()


async def test_live_below_threshold_llm_decides_and_basal_recorded():
    rows: list[DecisionRecord] = []
    answer = _basal_answer("romance_scam", 0.6)
    service = _service(_basal(answer), "live", rows)

    decision = await _decide(service, _llm())

    assert decision.source == "llm"
    assert decision.answer == "nigerian_419"
    assert decision.basal == answer
    row = rows[0]
    assert row.skip_reason == "below_threshold"
    assert row.basal_answer == "romance_scam"
    assert row.basal_confidence == 0.6
    assert row.llm_answer == "nigerian_419"
    assert row.final_answer == "nigerian_419"
    assert row.llm_ms is not None


async def test_live_below_threshold_llm_failure_uses_basal_low_confidence():
    rows: list[DecisionRecord] = []
    answer = _basal_answer("romance_scam", 0.6)
    service = _service(_basal(answer), "live", rows)

    decision = await _decide(service, _llm(error=LLMRequestError("boom")))

    assert decision.source == "basal_low_confidence"
    assert decision.answer == "romance_scam"
    assert decision.llm_result is None
    row = rows[0]
    assert row.source == "basal_low_confidence"
    assert row.final_answer == "romance_scam"
    assert row.llm_answer is None


async def test_live_llm_failure_without_basal_answer_reraises():
    rows: list[DecisionRecord] = []
    service = _service(_basal(error=BasalUnavailableError("down")), "live", rows)
    error = LLMRequestError("boom")

    with pytest.raises(LLMRequestError) as exc_info:
        await _decide(service, _llm(error=error))

    assert exc_info.value is error
    assert rows == []


# --- shadow ----------------------------------------------------------------


async def test_shadow_verdict_is_llm_even_with_confident_basal():
    rows: list[DecisionRecord] = []
    service = _service(_basal(_basal_answer("romance_scam", 0.99)), "shadow", rows)

    decision = await _decide(service, _llm())
    await drain_background_tasks()

    assert decision.source == "llm"
    assert decision.answer == "nigerian_419"
    assert decision.basal is None
    row = rows[0]
    assert row.mode == "shadow"
    assert row.source == "llm"
    assert row.final_answer == "nigerian_419"
    assert row.basal_answer == "romance_scam"
    assert row.llm_answer == "nigerian_419"
    assert row.skip_reason is None


async def test_shadow_does_not_wait_for_basal():
    rows: list[DecisionRecord] = []
    basal = AsyncMock(spec=BasalClient)

    async def slow_ask(*args, **kwargs) -> BasalAnswer:
        await asyncio.sleep(1)
        return _basal_answer("romance_scam", 0.95)

    basal.ask_choice.side_effect = slow_ask
    service = _service(basal, "shadow", rows)

    start = time.perf_counter()
    decision = await _decide(service, _llm())
    elapsed = time.perf_counter() - start

    assert elapsed < 0.2
    assert decision.source == "llm"
    assert rows == []

    await drain_background_tasks()

    assert len(rows) == 1
    assert rows[0].basal_answer == "romance_scam"
    assert rows[0].mode == "shadow"
    assert rows[0].llm_answer == "nigerian_419"


async def test_shadow_llm_failure_still_records(caplog: pytest.LogCaptureFixture):
    rows: list[DecisionRecord] = []
    service = _service(_basal(_basal_answer("romance_scam", 0.95)), "shadow", rows)
    error = LLMRequestError("boom")

    with caplog.at_level(logging.DEBUG):
        with pytest.raises(LLMRequestError) as exc_info:
            await _decide(service, _llm(error=error))
        await drain_background_tasks()
        gc.collect()
        await asyncio.sleep(0)

    assert exc_info.value is error
    assert len(rows) == 1
    assert rows[0].llm_answer is None
    assert rows[0].final_answer == ""
    assert rows[0].basal_answer == "romance_scam"
    assert "Task exception was never retrieved" not in caplog.text


async def test_shadow_basal_timeout_records_timeout():
    rows: list[DecisionRecord] = []
    error = BasalUnavailableError("slow", is_timeout=True)
    service = _service(_basal(error=error), "shadow", rows)

    decision = await _decide(service, _llm())
    await drain_background_tasks()

    assert decision.source == "llm"
    assert rows[0].skip_reason == "timeout"
    assert rows[0].basal_answer is None
    assert rows[0].llm_answer == "nigerian_419"


async def test_shadow_non_basal_language_records_language(_language_ok):
    _language_ok.return_value = False
    rows: list[DecisionRecord] = []
    basal = _basal()
    service = _service(basal, "shadow", rows)

    await _decide(service, _llm())
    await drain_background_tasks()

    basal.ask_choice.assert_not_awaited()
    assert rows[0].skip_reason == "language"
    assert rows[0].mode == "shadow"


async def test_shadow_recorder_error_never_leaks(caplog: pytest.LogCaptureFixture):
    async def broken_recorder(record: DecisionRecord) -> None:
        raise RuntimeError("db down")

    service = DecisionService(
        basal=_basal(),
        mode="shadow",
        threshold_for=lambda node: 0.9,
        recorder=broken_recorder,
    )

    with caplog.at_level(logging.DEBUG):
        decision = await _decide(service, _llm())
        await drain_background_tasks()
        gc.collect()
        await asyncio.sleep(0)

    assert decision.source == "llm"
    assert "Task exception was never retrieved" not in caplog.text


def _gated_shadow(rows: list[DecisionRecord]):
    """Shadow service whose Basal call signals when the task parks on the LLM."""
    basal_called = asyncio.Event()
    basal = AsyncMock(spec=BasalClient)

    def ask(*args, **kwargs) -> BasalAnswer:
        basal_called.set()
        return _basal_answer("romance_scam", 0.95)

    basal.ask_choice.side_effect = ask
    return _service(basal, "shadow", rows), basal_called


def _gated_llm(error: Exception | None = None):
    release = asyncio.Event()

    async def call() -> FakeLLMResult:
        await release.wait()
        if error is not None:
            raise error
        return FakeLLMResult()

    return call, release


async def test_shadow_task_cancelled_mid_llm_decision_still_returns():
    rows: list[DecisionRecord] = []
    service, basal_called = _gated_shadow(rows)
    llm_call, release = _gated_llm()

    pending = asyncio.create_task(_decide(service, llm_call))
    await basal_called.wait()  # shadow task is now parked on the LLM future
    (shadow_task,) = cascade._background_tasks
    shadow_task.cancel()
    release.set()
    decision = await pending

    assert decision.source == "llm"
    assert decision.answer == "nigerian_419"
    assert shadow_task.cancelled()
    assert rows == []


async def test_shadow_task_cancelled_mid_llm_llm_error_propagates():
    rows: list[DecisionRecord] = []
    service, basal_called = _gated_shadow(rows)
    error = LLMRequestError("boom")
    llm_call, release = _gated_llm(error)

    pending = asyncio.create_task(_decide(service, llm_call))
    await basal_called.wait()
    (shadow_task,) = cascade._background_tasks
    shadow_task.cancel()
    release.set()

    with pytest.raises(LLMRequestError) as exc_info:
        await pending
    assert exc_info.value is error


# --- recording -------------------------------------------------------------


@pytest.mark.parametrize("mode", ["shadow", "live"])
async def test_no_row_without_session_id(mode):
    rows: list[DecisionRecord] = []
    service = _service(_basal(_basal_answer("romance_scam", 0.6)), mode, rows)

    await _decide(service, _llm(), session_id=None)
    await drain_background_tasks()

    assert rows == []


@pytest.mark.parametrize("mode", ["off", "shadow", "live"])
async def test_no_row_without_recorder(mode):
    service = DecisionService(
        basal=_basal(_basal_answer("romance_scam", 0.95)),
        mode=mode,
        threshold_for=lambda node: 0.9,
        recorder=None,
    )

    decision = await _decide(service, _llm())
    await drain_background_tasks()

    assert decision.answer in {"romance_scam", "nigerian_419"}


# --- factory ---------------------------------------------------------------


def test_create_decision_service_off_without_url():
    service = create_decision_service(Settings(basal_url="", basal_mode="live"))

    assert service.mode == "off"
    assert service.basal is None


def test_create_decision_service_live_with_url():
    settings = Settings(
        basal_url="http://basal.test/ask",
        basal_mode="live",
        basal_threshold=0.8,
        basal_threshold_profiler=0.95,
    )

    service = create_decision_service(settings)

    assert service.mode == "live"
    assert isinstance(service.basal, BasalClient)
    assert service.threshold_for("profiler.attack_type") == 0.95
    assert service.threshold_for("other.node") == 0.8
