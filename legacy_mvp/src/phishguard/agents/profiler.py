"""Profiler Agent for phishing email classification.

This module implements the ProfilerAgent, which analyzes email content and
classifies it into one of the predefined phishing attack categories using
LLM-powered analysis.
"""

import json
import logging
import time
from typing import Final

from phishguard.agents.prompts.profiler import (
    PROFILER_SYSTEM_PROMPT,
    get_profiler_user_prompt,
)
from phishguard.llm import LLMClient, LLMRequestError, create_llm_client
from phishguard.models import AttackType, ClassificationResult

logger = logging.getLogger(__name__)

CLASSIFICATION_TEMPERATURE: Final[float] = 0.2
CLASSIFICATION_MAX_TOKENS: Final[int] = 200
MAX_PARSE_RETRIES: Final[int] = 1


class ClassificationError(Exception):
    """Raised when email classification fails.

    This exception indicates a failure in the classification process,
    such as LLM communication errors or unexpected response formats.
    It should be caught and handled by the caller.
    """


class ProfilerAgent:
    """Agent responsible for classifying phishing emails into attack categories.

    The ProfilerAgent analyzes email content using an LLM to determine the type
    of phishing attack being attempted. It supports 8 phishing categories plus
    a NOT_PHISHING category for legitimate emails.

    The agent uses a low temperature setting for consistent classification
    results and includes retry logic for handling malformed LLM responses.

    Attributes:
        _client: LLM client for generating classifications.

    Example:
        >>> client = create_llm_client()
        >>> profiler = ProfilerAgent(client)
        >>> result = await profiler.classify("Dear Friend, I am a prince...")
        >>> print(result.attack_type)
        AttackType.NIGERIAN_419
    """

    def __init__(self, client: LLMClient | None = None) -> None:
        """Initialize the ProfilerAgent with an LLM client.

        Args:
            client: Optional LLM client for dependency injection.
                If not provided, a default client will be created.
                This allows for easy testing with mock clients.
        """
        self._client = client or create_llm_client()

    async def classify(self, email_content: str) -> tuple[ClassificationResult, bool]:
        """Classify a phishing email into an attack category.

        Analyzes the provided email content using an LLM to determine
        the type of phishing attack. The method tracks classification
        time and handles malformed responses gracefully.

        Args:
            email_content: The raw email body text to analyze.
                Should be pre-sanitized by InputSanitizer.

        Returns:
            A tuple containing:
                - ClassificationResult with attack type, confidence,
                  reasoning, and classification time.
                - Boolean indicating if the fallback LLM model was used.

        Raises:
            ClassificationError: If the LLM request fails after retries.

        Note:
            Malformed LLM responses are handled internally with a retry
            mechanism. If parsing fails after retries, a safe fallback
            result (NOT_PHISHING with low confidence) is returned rather
            than raising an exception.
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
                response = await self._client.chat_completion(
                    messages=messages,
                    temperature=CLASSIFICATION_TEMPERATURE,
                    max_tokens=CLASSIFICATION_MAX_TOKENS,
                )
                used_fallback = response.used_fallback

                result = self._parse_classification_response(
                    response.content,
                    self._calculate_elapsed_ms(start_time),
                )
                return result, used_fallback

            except LLMRequestError as e:
                logger.error("LLM request failed during classification: %s", e)
                raise ClassificationError(f"Failed to classify email: {e}") from e

            except (json.JSONDecodeError, KeyError, ValueError) as e:
                attempts += 1
                last_error = str(e)
                logger.warning(
                    "Malformed LLM response (attempt %d/%d): %s",
                    attempts,
                    MAX_PARSE_RETRIES + 1,
                    e,
                )

                if attempts > MAX_PARSE_RETRIES:
                    break

        # Return safe fallback after all parse retries exhausted
        logger.warning(
            "Returning fallback classification after %d failed parse attempts. "
            "Last error: %s",
            attempts,
            last_error,
        )
        return (
            self._create_fallback_result(
                self._calculate_elapsed_ms(start_time),
                last_error,
            ),
            used_fallback,
        )

    def _parse_classification_response(
        self,
        response_content: str,
        elapsed_ms: int,
    ) -> ClassificationResult:
        """Parse the LLM response into a ClassificationResult.

        Args:
            response_content: Raw JSON string from the LLM.
            elapsed_ms: Classification time in milliseconds.

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
        )

    def _create_fallback_result(
        self,
        elapsed_ms: int,
        error_detail: str | None = None,
    ) -> ClassificationResult:
        """Create a safe fallback classification result.

        Used when the LLM response cannot be parsed after retries.
        Returns NOT_PHISHING with low confidence to avoid false positives.

        Args:
            elapsed_ms: Classification time in milliseconds.
            error_detail: Optional error message for reasoning.

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
