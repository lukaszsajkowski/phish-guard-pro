"""Profiler Agent for phishing email classification.

This module implements the ProfilerAgent, which analyzes email content and
classifies it into one of the predefined phishing attack categories. The
attack-type decision goes through the Basal decision cascade (US-049): a local
Basal model may decide, otherwise the LLM does.
"""

import json
import logging
import time
from collections.abc import Callable
from typing import Final

from phishguard.agents.prompts.profiler import (
    PROFILER_SYSTEM_PROMPT,
    get_profiler_user_prompt,
)
from phishguard.agents.prompts.profiler_basal import (
    ATTACK_TYPE_CRITERIA,
    PROFILER_BASAL_INSTRUCTIONS,
)
from phishguard.decisions import (
    ChoiceQuestion,
    DecisionService,
    create_decision_service,
)
from phishguard.decisions.basal_client import BasalAnswer
from phishguard.decisions.recorder import record_llm_usage
from phishguard.llm import LLMClient, LLMRequestError, LLMResponse, create_llm_client
from phishguard.llm.budget import warn_if_budget_exhausted
from phishguard.models.classification import AttackType, ClassificationResult

logger = logging.getLogger(__name__)

CLASSIFICATION_TEMPERATURE: Final[float] = 0.2
CLASSIFICATION_MAX_TOKENS: Final[int] = 2000
MAX_PARSE_RETRIES: Final[int] = 1
PROFILER_NODE: Final[str] = "profiler.attack_type"
USAGE_AGENT: Final[str] = "profiler"


class ClassificationError(Exception):
    """Raised when email classification fails.

    This exception indicates a failure in the classification process,
    such as LLM communication errors or unexpected response formats.
    It should be caught and handled by the caller.
    """


class ClassificationParseError(ClassificationError):
    """The LLM response could not be parsed after all retries."""

    def __init__(
        self, message: str, last_error: str | None, used_fallback: bool
    ) -> None:
        super().__init__(message)
        self.last_error = last_error
        self.used_fallback = used_fallback


def build_basal_reasoning(answer: BasalAnswer) -> str:
    """Template reasoning for a Basal decision (Basal writes no rationale)."""
    top = AttackType(answer.answer).display_name
    text = f"Classified locally by Basal: {top} (p={answer.confidence:.2f})."
    # Only keys that were asked as options; a stray key from a misconfigured
    # server must not turn the reasoning text into a crash.
    runner_ups = {
        k: v
        for k, v in answer.probabilities.items()
        if k != answer.answer and k in ATTACK_TYPE_CRITERIA
    }
    if runner_ups:
        key = max(runner_ups, key=runner_ups.__getitem__)
        second = AttackType(key).display_name
        text += f" Runner-up: {second} (p={runner_ups[key]:.2f})."
    return text


class ProfilerAgent:
    """Agent responsible for classifying phishing emails into attack categories.

    The ProfilerAgent determines the type of phishing attack being attempted.
    It supports 8 phishing categories plus a NOT_PHISHING category for
    legitimate emails. The decision is routed through a DecisionService: in
    ``off``/``shadow`` mode the LLM decides; in ``live`` mode Basal decides
    when confident enough.

    The LLM path uses a low temperature setting for consistent classification
    results and includes retry logic for handling malformed LLM responses.
    """

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        decision_service: DecisionService | None = None,
    ) -> None:
        """Initialize the ProfilerAgent.

        Args:
            llm_client: Optional LLMClient for dependency injection.
                If not provided, a default client with fallback support is created.
            decision_service: Optional DecisionService. If not provided, one is
                built from settings (empty BASAL_URL means LLM only).
        """
        self._llm_client = llm_client or create_llm_client()
        self._decision_service = decision_service or create_decision_service(
            node=PROFILER_NODE
        )

    async def classify(
        self, email_content: str, session_id: str | None = None
    ) -> ClassificationResult:
        """Classify a phishing email into an attack category.

        Args:
            email_content: The raw email body text to analyze.
                Should be pre-sanitized by InputSanitizer.
            session_id: Optional session id; when set, the decision and the
                LLM token usage are recorded against it.

        Returns:
            ClassificationResult with attack type, confidence, reasoning,
            classification time, fallback status, and decision source.

        Raises:
            ClassificationError: If the LLM request fails and no Basal answer
                is available to fall back on.
        """
        start_time = time.perf_counter()
        question = ChoiceQuestion(
            node=PROFILER_NODE,
            instructions=PROFILER_BASAL_INSTRUCTIONS,
            criteria=ATTACK_TYPE_CRITERIA,
        )

        try:
            decision = await self._decision_service.decide_choice(
                question,
                email_content,
                session_id,
                llm_call=lambda: self.classify_with_llm(
                    email_content, session_id=session_id
                ),
                llm_answer=lambda r: r.attack_type.value,
                llm_model=self._model_of,
            )
        except ClassificationParseError as e:
            logger.warning(
                "Returning fallback classification after failed parse attempts. "
                "Last error: %s",
                e.last_error,
            )
            return self._create_fallback_result(
                self._calculate_elapsed_ms(start_time),
                e.last_error,
                e.used_fallback,
            )
        except LLMRequestError as e:
            raise ClassificationError(f"Failed to classify email: {e}") from e

        if decision.source == "llm":
            assert decision.llm_result is not None
            return decision.llm_result.model_copy(update={"decision_source": "llm"})

        assert decision.basal is not None
        return ClassificationResult(
            attack_type=AttackType(decision.basal.answer),
            confidence=round(decision.basal.confidence * 100, 2),
            reasoning=build_basal_reasoning(decision.basal),
            classification_time_ms=self._calculate_elapsed_ms(start_time),
            decision_source=decision.source,
        )

    async def classify_with_llm(
        self,
        email_content: str,
        session_id: str | None = None,
        *,
        on_usage: Callable[[LLMResponse], None] | None = None,
    ) -> ClassificationResult:
        """Classify an email with the LLM only.

        Args:
            email_content: The raw email body text to analyze.
            session_id: Optional session id; when set, token usage is recorded.
            on_usage: Optional callback called with every LLMResponse received
                (e.g. to collect token counts without a session).

        Returns:
            ClassificationResult with ``decision_source="llm"``.

        Raises:
            ClassificationError: If the LLM request fails after retries.
            ClassificationParseError: If no response could be parsed after
                ``MAX_PARSE_RETRIES`` retries.
        """
        start_time = time.perf_counter()

        messages = [
            {"role": "system", "content": PROFILER_SYSTEM_PROMPT},
            {"role": "user", "content": get_profiler_user_prompt(email_content)},
        ]

        attempts = 0
        last_error: str | None = None
        used_fallback = False

        while attempts <= MAX_PARSE_RETRIES:
            try:
                # Use LLMClient for automatic retry and fallback (US-023)
                call_start = time.perf_counter()
                llm_response = await self._llm_client.chat_completion(
                    messages=messages,
                    temperature=CLASSIFICATION_TEMPERATURE,
                    max_tokens=CLASSIFICATION_MAX_TOKENS,
                )
                if session_id:
                    await record_llm_usage(
                        session_id,
                        USAGE_AGENT,
                        llm_response.model_used,
                        llm_response.prompt_tokens,
                        llm_response.completion_tokens,
                        int((time.perf_counter() - call_start) * 1000),
                    )
                if on_usage is not None:
                    try:
                        on_usage(llm_response)
                    except Exception:
                        # A buggy callback must not count as a parse failure.
                        logger.warning("on_usage callback failed", exc_info=True)
                warn_if_budget_exhausted(
                    llm_response,
                    agent=USAGE_AGENT,
                    max_tokens=CLASSIFICATION_MAX_TOKENS,
                )
                content = llm_response.content

                # Track if fallback model was used
                if llm_response.used_fallback:
                    used_fallback = True
                    logger.info(
                        "Using fallback model %s for classification",
                        llm_response.model_used,
                    )

                return self._parse_classification_response(
                    content,
                    self._calculate_elapsed_ms(start_time),
                    used_fallback,
                )

            except LLMRequestError as e:
                logger.error("LLM request failed during classification: %s", e)
                raise ClassificationError(f"Failed to classify email: {e}") from e
            except Exception as e:
                attempts += 1
                last_error = str(e)
                logger.warning(
                    "Error during classification (attempt %d/%d): %s",
                    attempts,
                    MAX_PARSE_RETRIES + 1,
                    e,
                )

        raise ClassificationParseError(
            f"Unparseable classification after {attempts} attempts: {last_error}",
            last_error,
            used_fallback,
        )

    def _model_of(self, result: ClassificationResult) -> str:
        """Name of the LLM model that produced `result`."""
        if result.used_fallback_model:
            return self._llm_client.fallback_model
        return self._llm_client.primary_model

    def _parse_classification_response(
        self,
        response_content: str,
        elapsed_ms: int,
        used_fallback: bool = False,
    ) -> ClassificationResult:
        """Parse the LLM response into a ClassificationResult.

        Args:
            response_content: Raw JSON string from the LLM.
            elapsed_ms: Classification time in milliseconds.
            used_fallback: Whether fallback model was used.

        Returns:
            Parsed ClassificationResult.

        Raises:
            json.JSONDecodeError: If response is not valid JSON.
            KeyError: If required fields are missing.
            ValueError: If attack_type is not a valid enum value.
        """
        # Strip potential markdown code block markers
        content = response_content.strip()
        if content.startswith("```"):
            # Remove markdown code fence
            lines = content.split("\n")
            # Skip first line (```json or ```) and last line (```)
            content = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
            content = content.strip()

        data = json.loads(content)

        attack_type_str = data["attack_type"]
        confidence = data["confidence"]
        reasoning = data["reasoning"]

        # Convert string to AttackType enum
        attack_type = AttackType(attack_type_str)

        return ClassificationResult(
            attack_type=attack_type,
            confidence=float(confidence),
            reasoning=reasoning,
            classification_time_ms=elapsed_ms,
            used_fallback_model=used_fallback,
        )

    def _create_fallback_result(
        self,
        elapsed_ms: int,
        error_detail: str | None = None,
        used_fallback: bool = False,
    ) -> ClassificationResult:
        """Create a safe fallback classification result.

        Used when the LLM response cannot be parsed after retries.
        Returns NOT_PHISHING with low confidence to avoid false positives.

        Args:
            elapsed_ms: Classification time in milliseconds.
            error_detail: Optional error message for reasoning.
            used_fallback: Whether fallback model was used.

        Returns:
            ClassificationResult with NOT_PHISHING and low confidence.
        """
        reasoning = (
            "Classification uncertain due to response parsing failure. "
            "Manual review recommended."
        )
        if error_detail:
            reasoning = f"{reasoning} Error: {error_detail}"

        return ClassificationResult(
            attack_type=AttackType.NOT_PHISHING,
            confidence=25.0,
            reasoning=reasoning,
            classification_time_ms=elapsed_ms,
            used_fallback_model=used_fallback,
        )

    @staticmethod
    def _calculate_elapsed_ms(start_time: float) -> int:
        """Calculate elapsed time in milliseconds since start_time.

        Args:
            start_time: Start time from time.perf_counter().

        Returns:
            Elapsed time in milliseconds as an integer.
        """
        return int((time.perf_counter() - start_time) * 1000)
