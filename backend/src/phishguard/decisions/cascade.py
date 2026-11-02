"""Basal -> LLM cascade for closed (single-choice) questions.

Modes:
- ``off``: only the LLM answers; no decision row is written.
- ``shadow``: the LLM answers; Basal runs in a background task and its answer
  is only logged. The caller never waits for Basal.
- ``live``: Basal answers when its confidence reaches the node threshold
  (inclusive); otherwise the LLM answers. If the LLM then fails and Basal had
  an answer, Basal's answer is used as ``basal_low_confidence``.

A Basal failure, a language-gate failure, or a failed decision-log write never
fails a decision. Decision rows never contain the question state (email text).
"""

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Literal

from phishguard.core import Settings, get_settings
from phishguard.decisions.basal_client import (
    BasalAnswer,
    BasalClient,
    BasalUnavailableError,
)
from phishguard.decisions.language import is_basal_language
from phishguard.decisions.recorder import DecisionRecord, record_decision

logger = logging.getLogger(__name__)

Mode = Literal["off", "shadow", "live"]
Source = Literal["llm", "basal", "basal_low_confidence"]
Recorder = Callable[[DecisionRecord], Awaitable[None]]

# Strong references to running shadow tasks so the GC does not collect them.
_background_tasks: set[asyncio.Task[None]] = set()


@dataclass(frozen=True)
class ChoiceQuestion:
    """A closed question: pick exactly one key of `criteria`."""

    node: str
    instructions: str
    criteria: dict[str, str]


@dataclass(frozen=True)
class Decision[T]:
    """Outcome of a routed decision."""

    source: Source
    answer: str
    basal: BasalAnswer | None
    llm_result: T | None


@dataclass(frozen=True)
class _LLMOutcome:
    answer: str
    model: str
    ms: int


def _resolve(
    future: asyncio.Future[_LLMOutcome | None], outcome: _LLMOutcome | None
) -> None:
    """Hand the LLM outcome to the shadow task, unless it was cancelled."""
    if not future.done():
        future.set_result(outcome)


async def drain_background_tasks() -> None:
    """Wait for all pending shadow-mode tasks (tests, eval, shutdown)."""
    while _background_tasks:
        await asyncio.gather(*list(_background_tasks), return_exceptions=True)


class DecisionService:
    """Routes closed questions between Basal and the LLM and logs each decision."""

    def __init__(
        self,
        basal: BasalClient | None,
        mode: Mode,
        threshold_for: Callable[[str], float],
        basal_model: str = "",
        recorder: Recorder | None = record_decision,
    ) -> None:
        self.basal = basal
        self.mode: Mode = "off" if basal is None else mode
        self.threshold_for = threshold_for
        self._basal_model = basal_model or None
        self._recorder = recorder

    async def decide_choice[T](
        self,
        question: ChoiceQuestion,
        state: str,
        session_id: str | None,
        llm_call: Callable[[], Awaitable[T]],
        llm_answer: Callable[[T], str],
        llm_model: Callable[[T], str],
    ) -> Decision[T]:
        """Answer `question` about `state` according to the configured mode."""
        if self.mode == "live":
            return await self._decide_live(
                question, state, session_id, llm_call, llm_answer, llm_model
            )
        if self.mode == "shadow":
            return await self._decide_shadow(
                question, state, session_id, llm_call, llm_answer, llm_model
            )
        # off: no decisions row; the table only logs shadow/live decisions.
        return await self._decide_off(llm_call, llm_answer, llm_model)

    # --- modes -------------------------------------------------------------

    async def _decide_off[T](
        self,
        llm_call: Callable[[], Awaitable[T]],
        llm_answer: Callable[[T], str],
        llm_model: Callable[[T], str],
    ) -> Decision[T]:
        result, outcome = await self._run_llm(llm_call, llm_answer, llm_model)
        return Decision("llm", outcome.answer, None, result)

    async def _decide_live[T](
        self,
        question: ChoiceQuestion,
        state: str,
        session_id: str | None,
        llm_call: Callable[[], Awaitable[T]],
        llm_answer: Callable[[T], str],
        llm_model: Callable[[T], str],
    ) -> Decision[T]:
        threshold = self.threshold_for(question.node)
        basal, skip_reason = await self._ask_basal(question, state)

        if basal is not None and basal.confidence >= threshold:
            await self._record(
                session_id, question, "basal", basal.answer, basal, None, None
            )
            return Decision("basal", basal.answer, basal, None)

        skip_reason = skip_reason or "below_threshold"
        try:
            result, outcome = await self._run_llm(llm_call, llm_answer, llm_model)
        except Exception:
            if basal is None:
                raise
            logger.warning(
                "LLM failed for %s; using low-confidence Basal answer",
                question.node,
                exc_info=True,
            )
            await self._record(
                session_id,
                question,
                "basal_low_confidence",
                basal.answer,
                basal,
                None,
                skip_reason,
            )
            return Decision("basal_low_confidence", basal.answer, basal, None)

        await self._record(
            session_id, question, "llm", outcome.answer, basal, outcome, skip_reason
        )
        return Decision("llm", outcome.answer, basal, result)

    async def _decide_shadow[T](
        self,
        question: ChoiceQuestion,
        state: str,
        session_id: str | None,
        llm_call: Callable[[], Awaitable[T]],
        llm_answer: Callable[[T], str],
        llm_model: Callable[[T], str],
    ) -> Decision[T]:
        if session_id is None or self._recorder is None:
            # Nothing would be logged, so Basal's answer would be unused.
            result, outcome = await self._run_llm(llm_call, llm_answer, llm_model)
            return Decision("llm", outcome.answer, None, result)

        llm_future: asyncio.Future[_LLMOutcome | None] = (
            asyncio.get_running_loop().create_future()
        )
        task = asyncio.create_task(
            self._shadow_task(question, state, session_id, llm_future)
        )
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)

        try:
            result, outcome = await self._run_llm(llm_call, llm_answer, llm_model)
        except BaseException:
            _resolve(llm_future, None)
            raise
        _resolve(llm_future, outcome)
        return Decision("llm", outcome.answer, None, result)

    async def _shadow_task(
        self,
        question: ChoiceQuestion,
        state: str,
        session_id: str,
        llm_future: asyncio.Future[_LLMOutcome | None],
    ) -> None:
        try:
            basal, skip_reason = await self._ask_basal(question, state)
            outcome = await llm_future
            if basal is not None and basal.confidence < self.threshold_for(
                question.node
            ):
                skip_reason = "below_threshold"
            final_answer = outcome.answer if outcome is not None else ""
            await self._record(
                session_id, question, "llm", final_answer, basal, outcome, skip_reason
            )
        except Exception:
            logger.warning("Shadow decision task failed", exc_info=True)

    # --- helpers -----------------------------------------------------------

    async def _ask_basal(
        self, question: ChoiceQuestion, state: str
    ) -> tuple[BasalAnswer | None, str | None]:
        """Run the language gate and Basal; return (answer, skip_reason)."""
        try:
            usable = await asyncio.to_thread(is_basal_language, state)
        except Exception:
            logger.warning("Language gate failed; skipping Basal", exc_info=True)
            return None, "unavailable"
        if not usable:
            return None, "language"

        assert self.basal is not None
        try:
            answer = await self.basal.ask_choice(
                state, question.instructions, question.criteria
            )
        except BasalUnavailableError as exc:
            logger.warning("Basal unavailable for %s: %s", question.node, exc)
            return None, "timeout" if exc.is_timeout else "unavailable"
        except Exception:
            logger.warning("Basal call failed for %s", question.node, exc_info=True)
            return None, "unavailable"
        return answer, None

    @staticmethod
    async def _run_llm[T](
        llm_call: Callable[[], Awaitable[T]],
        llm_answer: Callable[[T], str],
        llm_model: Callable[[T], str],
    ) -> tuple[T, _LLMOutcome]:
        start = time.perf_counter()
        result = await llm_call()
        ms = int((time.perf_counter() - start) * 1000)
        return result, _LLMOutcome(llm_answer(result), llm_model(result), ms)

    async def _record(
        self,
        session_id: str | None,
        question: ChoiceQuestion,
        source: Source,
        final_answer: str,
        basal: BasalAnswer | None,
        llm: _LLMOutcome | None,
        skip_reason: str | None,
    ) -> None:
        """Write one decision row; never raises, no-op without session/recorder."""
        if session_id is None or self._recorder is None:
            return
        record = DecisionRecord(
            session_id=session_id,
            node=question.node,
            mode=self.mode,
            options=list(question.criteria),
            threshold=self.threshold_for(question.node),
            final_answer=final_answer,
            source=source,
            basal_answer=basal.answer if basal else None,
            basal_probabilities=basal.probabilities if basal else None,
            basal_confidence=basal.confidence if basal else None,
            basal_ms=basal.latency_ms if basal else None,
            basal_model=self._basal_model if basal else None,
            skip_reason=skip_reason,
            llm_answer=llm.answer if llm else None,
            llm_model=llm.model if llm else None,
            llm_ms=llm.ms if llm else None,
        )
        try:
            await self._recorder(record)
        except Exception:
            logger.warning("Failed to record decision", exc_info=True)


def create_decision_service(settings: Settings | None = None) -> DecisionService:
    """Build a DecisionService from settings (empty BASAL_URL means off)."""
    settings = settings or get_settings()
    mode = settings.basal_effective_mode
    basal = (
        BasalClient(settings.basal_url, settings.basal_timeout_s)
        if mode != "off"
        else None
    )
    return DecisionService(
        basal=basal,
        mode=mode,
        threshold_for=settings.basal_threshold_for,
        basal_model=settings.basal_model,
    )
