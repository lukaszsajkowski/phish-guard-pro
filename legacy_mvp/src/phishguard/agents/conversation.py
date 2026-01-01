"""Conversation Agent for generating victim persona responses.

This module implements the ConversationAgent, which generates believable
victim responses in the selected persona's style to engage scammers in
conversation while extracting threat intelligence.
"""

import json
import logging
import time
from typing import Final

from phishguard.agents.prompts.conversation import (
    get_conversation_system_prompt,
    get_conversation_user_prompt,
)
from phishguard.llm import LLMClient, LLMRequestError, create_llm_client
from phishguard.models import (
    AgentThinking,
    AttackType,
    ConversationMessage,
    PersonaProfile,
    ResponseGenerationResult,
)
from phishguard.safety import OutputValidator

logger = logging.getLogger(__name__)

# Generation parameters
CONVERSATION_TEMPERATURE: Final[float] = 0.8
CONVERSATION_MAX_TOKENS: Final[int] = 300
MAX_REGENERATION_ATTEMPTS: Final[int] = 3


class ResponseGenerationError(Exception):
    """Raised when response generation fails.

    This exception indicates a failure in generating a conversation response,
    such as LLM communication errors or repeated safety validation failures.
    """


class ConversationAgent:
    """Agent responsible for generating victim persona responses.

    The ConversationAgent generates believable responses in the selected
    persona's style. It uses the configured LLM to roleplay as the victim
    and applies safety validation to ensure no real PII is generated.

    The agent implements a "loose goals" strategy to maximize engagement:
    - Obtain payment details
    - Extend the conversation
    - Build trust
    - Ask open-ended questions

    Attributes:
        _client: LLM client for generating responses.
        _validator: Output validator for safety checks.

    Example:
        >>> agent = ConversationAgent()
        >>> result = await agent.generate_response(
        ...     persona=persona_profile,
        ...     email_content="Dear Friend, I have money for you...",
        ...     attack_type=AttackType.NIGERIAN_419,
        ...     is_first_response=True
        ... )
        >>> print(result.content)
        "Oh my, this sounds wonderful! But how did you find me?"
    """

    def __init__(
        self,
        client: LLMClient | None = None,
        validator: OutputValidator | None = None,
    ) -> None:
        """Initialize the ConversationAgent.

        Args:
            client: Optional LLM client for dependency injection.
                If not provided, a default client will be created.
            validator: Optional output validator for dependency injection.
                If not provided, a default validator will be created.
        """
        self._client = client or create_llm_client()
        self._validator = validator or OutputValidator()

    async def generate_response(
        self,
        persona: PersonaProfile,
        email_content: str,
        attack_type: AttackType,
        conversation_history: list[ConversationMessage] | None = None,
        is_first_response: bool = True,
    ) -> ResponseGenerationResult:
        """Generate a victim response in the persona's style.

        Generates a believable response to the scammer's message using the
        selected persona's communication style. The response is validated
        for safety and automatically regenerated if it contains real PII.

        Args:
            persona: The victim persona profile to roleplay.
            email_content: The scammer's message to respond to.
            attack_type: The classified type of phishing attack.
            conversation_history: Optional list of previous messages for context.
            is_first_response: Whether this is the first response in conversation.

        Returns:
            ResponseGenerationResult with the generated response and metadata.

        Raises:
            ResponseGenerationError: If generation fails after all retries,
                or if safety validation fails after max regeneration attempts.

        Note:
            The method automatically regenerates responses that fail safety
            validation, up to MAX_REGENERATION_ATTEMPTS times. After that,
            it raises an error rather than returning unsafe content.
        """
        start_time = time.perf_counter()

        # Build prompts
        system_prompt = get_conversation_system_prompt(persona, attack_type)
        user_prompt = get_conversation_user_prompt(
            email_content=email_content,
            conversation_history=self._format_history(conversation_history),
            is_first_response=is_first_response,
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        regeneration_count = 0
        used_fallback = False
        last_error: str | None = None
        current_thinking: AgentThinking | None = None

        while regeneration_count <= MAX_REGENERATION_ATTEMPTS:
            try:
                response = await self._client.chat_completion(
                    messages=messages,
                    temperature=CONVERSATION_TEMPERATURE,
                    max_tokens=CONVERSATION_MAX_TOKENS,
                )
                used_fallback = response.used_fallback

                # Parse structured response to extract content and thinking
                content, thinking = self._parse_structured_response(response.content)

                # Store thinking for potential return (even if safety fails)
                if thinking:
                    current_thinking = thinking

                # Validate output for safety
                validation_result = self._validator.validate(content)

                if validation_result.is_safe:
                    elapsed_ms = self._calculate_elapsed_ms(start_time)
                    logger.info(
                        "Response generated successfully in %dms "
                        "(regenerations: %d, fallback: %s, has_thinking: %s)",
                        elapsed_ms,
                        regeneration_count,
                        used_fallback,
                        current_thinking is not None,
                    )
                    return ResponseGenerationResult(
                        content=content,
                        generation_time_ms=elapsed_ms,
                        safety_validated=True,
                        regeneration_count=regeneration_count,
                        used_fallback_model=used_fallback,
                        thinking=current_thinking,
                    )

                # Safety validation failed - need to regenerate
                regeneration_count += 1
                last_error = validation_result.violation_summary
                logger.warning(
                    "Response failed safety validation (attempt %d/%d): %s",
                    regeneration_count,
                    MAX_REGENERATION_ATTEMPTS,
                    last_error,
                )

                # Add instruction to avoid the specific violation
                messages = self._add_safety_reminder(
                    messages, validation_result.violation_summary
                )

            except LLMRequestError as e:
                logger.error("LLM request failed during response generation: %s", e)
                raise ResponseGenerationError(
                    f"Failed to generate response: {e}"
                ) from e

        # All regeneration attempts exhausted
        elapsed_ms = self._calculate_elapsed_ms(start_time)
        logger.error(
            "Response generation failed after %d safety regeneration attempts. "
            "Last violation: %s",
            MAX_REGENERATION_ATTEMPTS,
            last_error,
        )
        raise ResponseGenerationError(
            f"Failed to generate safe response after {MAX_REGENERATION_ATTEMPTS} "
            f"attempts. Safety violations: {last_error}"
        )

    def _format_history(
        self, history: list[ConversationMessage] | None
    ) -> list[dict[str, str]] | None:
        """Format conversation history for the prompt.

        Args:
            history: List of conversation messages.

        Returns:
            Formatted history as list of dicts, or None if no history.
        """
        if not history:
            return None

        return [
            {
                "sender": msg.sender.value,
                "content": msg.content,
            }
            for msg in history
        ]

    def _parse_structured_response(
        self, raw_content: str
    ) -> tuple[str, AgentThinking | None]:
        """Parse structured JSON response from the LLM.

        Extracts the response content and thinking metadata from a JSON response.
        Falls back gracefully if the response is not valid JSON.

        Args:
            raw_content: Raw LLM response (expected to be JSON).

        Returns:
            Tuple of (response_content, agent_thinking).
            If parsing fails, returns (cleaned_content, None).
        """
        content = raw_content.strip()

        # Try to extract JSON from markdown code blocks if present
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            if end > start:
                content = content[start:end].strip()
        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            if end > start:
                content = content[start:end].strip()

        try:
            parsed = json.loads(content)

            # If parsed result is not a dict, fall back to raw content
            if not isinstance(parsed, dict):
                return self._clean_response(raw_content), None

            # Extract response content
            response_content = parsed.get("response", "")
            if not response_content:
                logger.warning("JSON response missing 'response' field")
                return self._clean_response(raw_content), None

            # Extract thinking metadata
            thinking_data = parsed.get("thinking")
            thinking = None

            if thinking_data and isinstance(thinking_data, dict):
                try:
                    thinking = AgentThinking(
                        turn_goal=thinking_data.get("turn_goal", ""),
                        selected_tactic=thinking_data.get("selected_tactic", ""),
                        reasoning=thinking_data.get("reasoning", ""),
                    )
                    logger.debug(
                        "Parsed agent thinking: goal=%s, tactic=%s",
                        thinking.turn_goal,
                        thinking.selected_tactic,
                    )
                except (ValueError, TypeError) as e:
                    logger.warning("Failed to create AgentThinking: %s", e)
                    thinking = None

            return self._clean_response(response_content), thinking

        except json.JSONDecodeError as e:
            logger.warning(
                "Failed to parse JSON response, falling back to raw content: %s", e
            )
            return self._clean_response(raw_content), None

    def _clean_response(self, content: str) -> str:
        """Clean the LLM response.

        Removes common artifacts like quotation marks wrapping the response,
        "Response:" prefixes, etc.

        Args:
            content: Raw LLM response content.

        Returns:
            Cleaned response text.
        """
        content = content.strip()

        # Remove common prefixes
        prefixes_to_remove = [
            "Response:",
            "Response: ",
            "Victim's response:",
            "Victim's response: ",
            "Message:",
            "Message: ",
        ]
        for prefix in prefixes_to_remove:
            if content.lower().startswith(prefix.lower()):
                content = content[len(prefix) :].strip()

        # Remove wrapping quotes if present
        if (content.startswith('"') and content.endswith('"')) or (
            content.startswith("'") and content.endswith("'")
        ):
            content = content[1:-1].strip()

        return content

    def _add_safety_reminder(
        self,
        messages: list[dict[str, str]],
        violations: str,
    ) -> list[dict[str, str]]:
        """Add a safety reminder to the messages after a violation.

        Args:
            messages: Current message list.
            violations: Summary of violations to avoid.

        Returns:
            Updated message list with safety reminder.
        """
        safety_reminder = (
            f"IMPORTANT: Your previous response contained unsafe content "
            f"({violations}). Generate a new response that uses ONLY fake/placeholder "
            f"data. For phone numbers, use 555-XXX-XXXX format. For emails, use "
            f"@example.com domain. Never include real SSN, bank accounts, or "
            f"corporate email addresses."
        )

        # Add as a new user message
        return messages + [{"role": "user", "content": safety_reminder}]

    @staticmethod
    def _calculate_elapsed_ms(start_time: float) -> int:
        """Calculate elapsed time in milliseconds.

        Args:
            start_time: Start time from time.perf_counter().

        Returns:
            Elapsed time in milliseconds as an integer.
        """
        return int((time.perf_counter() - start_time) * 1000)
