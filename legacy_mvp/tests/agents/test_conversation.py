"""Comprehensive unit tests for the ConversationAgent.

These tests verify that the ConversationAgent correctly:
1. Generates responses in the persona's style
2. Validates output through the safety layer
3. Automatically regenerates on safety violations
4. Returns proper ResponseGenerationResult with metadata
5. Handles LLM errors gracefully
6. Uses injected dependencies for testing

Test Categories:
- Successful response generation
- Safety validation and regeneration
- Error handling
- Dependency injection
- Response cleaning
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from phishguard.agents import ConversationAgent, ResponseGenerationError
from phishguard.llm import LLMClient, LLMRequestError, LLMResponse
from phishguard.models import (
    AttackType,
    ConversationMessage,
    MessageSender,
    PersonaProfile,
    PersonaType,
    ResponseGenerationResult,
)
from phishguard.safety import (
    OutputValidator,
    SafetyViolation,
    ValidationResult,
    ViolationType,
)

# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def mock_llm_client() -> MagicMock:
    """Create a mock LLM client for testing."""
    client = MagicMock(spec=LLMClient)
    client.chat_completion = AsyncMock()
    return client


@pytest.fixture
def mock_validator() -> MagicMock:
    """Create a mock output validator for testing."""
    validator = MagicMock(spec=OutputValidator)
    # Default to safe validation
    validator.validate.return_value = ValidationResult(
        is_safe=True,
        violations=[],
        original_text="",
    )
    return validator


@pytest.fixture
def agent_with_mocks(
    mock_llm_client: MagicMock,
    mock_validator: MagicMock,
) -> ConversationAgent:
    """Create a ConversationAgent with injected mocks."""
    return ConversationAgent(client=mock_llm_client, validator=mock_validator)


@pytest.fixture
def naive_retiree_persona() -> PersonaProfile:
    """Create a Naive Retiree persona for testing."""
    return PersonaProfile(
        persona_type=PersonaType.NAIVE_RETIREE,
        name="Margaret Thompson",
        age=72,
        style_description="Trusting and polite, uses formal language.",
        background="Retired teacher, recently widowed, lives alone with two cats.",
    )


@pytest.fixture
def stressed_manager_persona() -> PersonaProfile:
    """Create a Stressed Manager persona for testing."""
    return PersonaProfile(
        persona_type=PersonaType.STRESSED_MANAGER,
        name="David Chen",
        age=45,
        style_description="Impatient and busy, prefers brief responses.",
        background="Marketing director at mid-size company.",
    )


@pytest.fixture
def sample_nigerian_419_email() -> str:
    """Sample Nigerian 419 phishing email content."""
    return """
    Dear Friend,

    I am Dr. Emeka Okafor, a lawyer representing the estate of the late
    Mr. Williams Johnson who left behind $15.5 million USD.

    Please reply with your full name and bank account details.

    Regards,
    Dr. Emeka Okafor
    """


@pytest.fixture
def safe_response() -> LLMResponse:
    """Create a mock safe LLM response."""
    return LLMResponse(
        content="Oh my, this sounds wonderful! But how did you find me? "
        "I'm just a retired teacher living alone. What would I need to do?",
        used_fallback=False,
        model_used="gpt-4o",
    )


@pytest.fixture
def unsafe_response() -> LLMResponse:
    """Create a mock response with unsafe content (SSN)."""
    return LLMResponse(
        content="Yes, my social security number is 123-45-6789 and I'd love to help!",
        used_fallback=False,
        model_used="gpt-4o",
    )


@pytest.fixture
def fallback_model_response() -> LLMResponse:
    """Create a mock response from the fallback model."""
    return LLMResponse(
        content="This sounds interesting. Please tell me more about the process.",
        used_fallback=True,
        model_used="gpt-4o-mini",
    )


# -----------------------------------------------------------------------------
# Test Classes
# -----------------------------------------------------------------------------


class TestConversationAgentSuccessfulGeneration:
    """Tests for successful response generation."""

    @pytest.mark.asyncio
    async def test_generate_response_returns_result(
        self,
        agent_with_mocks: ConversationAgent,
        mock_llm_client: MagicMock,
        mock_validator: MagicMock,
        naive_retiree_persona: PersonaProfile,
        sample_nigerian_419_email: str,
        safe_response: LLMResponse,
    ) -> None:
        """generate_response should return ResponseGenerationResult."""
        mock_llm_client.chat_completion.return_value = safe_response

        result = await agent_with_mocks.generate_response(
            persona=naive_retiree_persona,
            email_content=sample_nigerian_419_email,
            attack_type=AttackType.NIGERIAN_419,
            is_first_response=True,
        )

        assert isinstance(result, ResponseGenerationResult)
        assert result.content is not None
        assert len(result.content) > 0

    @pytest.mark.asyncio
    async def test_generate_response_includes_timing(
        self,
        agent_with_mocks: ConversationAgent,
        mock_llm_client: MagicMock,
        naive_retiree_persona: PersonaProfile,
        sample_nigerian_419_email: str,
        safe_response: LLMResponse,
    ) -> None:
        """Response should include generation time in milliseconds."""
        mock_llm_client.chat_completion.return_value = safe_response

        result = await agent_with_mocks.generate_response(
            persona=naive_retiree_persona,
            email_content=sample_nigerian_419_email,
            attack_type=AttackType.NIGERIAN_419,
            is_first_response=True,
        )

        assert result.generation_time_ms >= 0
        assert isinstance(result.generation_time_ms, int)

    @pytest.mark.asyncio
    async def test_generate_response_sets_safety_validated(
        self,
        agent_with_mocks: ConversationAgent,
        mock_llm_client: MagicMock,
        naive_retiree_persona: PersonaProfile,
        sample_nigerian_419_email: str,
        safe_response: LLMResponse,
    ) -> None:
        """Response should have safety_validated=True after passing validation."""
        mock_llm_client.chat_completion.return_value = safe_response

        result = await agent_with_mocks.generate_response(
            persona=naive_retiree_persona,
            email_content=sample_nigerian_419_email,
            attack_type=AttackType.NIGERIAN_419,
            is_first_response=True,
        )

        assert result.safety_validated is True

    @pytest.mark.asyncio
    async def test_generate_response_tracks_fallback_model(
        self,
        agent_with_mocks: ConversationAgent,
        mock_llm_client: MagicMock,
        naive_retiree_persona: PersonaProfile,
        sample_nigerian_419_email: str,
        fallback_model_response: LLMResponse,
    ) -> None:
        """Response should track when fallback model was used."""
        mock_llm_client.chat_completion.return_value = fallback_model_response

        result = await agent_with_mocks.generate_response(
            persona=naive_retiree_persona,
            email_content=sample_nigerian_419_email,
            attack_type=AttackType.NIGERIAN_419,
            is_first_response=True,
        )

        assert result.used_fallback_model is True


class TestConversationAgentSafetyValidation:
    """Tests for safety validation and regeneration."""

    @pytest.mark.asyncio
    async def test_validates_output_through_safety_layer(
        self,
        agent_with_mocks: ConversationAgent,
        mock_llm_client: MagicMock,
        mock_validator: MagicMock,
        naive_retiree_persona: PersonaProfile,
        sample_nigerian_419_email: str,
        safe_response: LLMResponse,
    ) -> None:
        """Agent should validate every response through OutputValidator."""
        mock_llm_client.chat_completion.return_value = safe_response

        await agent_with_mocks.generate_response(
            persona=naive_retiree_persona,
            email_content=sample_nigerian_419_email,
            attack_type=AttackType.NIGERIAN_419,
            is_first_response=True,
        )

        mock_validator.validate.assert_called()

    @pytest.mark.asyncio
    async def test_regenerates_on_unsafe_response(
        self,
        agent_with_mocks: ConversationAgent,
        mock_llm_client: MagicMock,
        mock_validator: MagicMock,
        naive_retiree_persona: PersonaProfile,
        sample_nigerian_419_email: str,
        unsafe_response: LLMResponse,
        safe_response: LLMResponse,
    ) -> None:
        """Agent should regenerate when response fails safety validation."""
        # First response is unsafe, second is safe
        mock_llm_client.chat_completion.side_effect = [unsafe_response, safe_response]

        # First validation fails, second passes
        mock_validator.validate.side_effect = [
            ValidationResult(
                is_safe=False,
                violations=[
                    SafetyViolation(
                        violation_type=ViolationType.SSN,
                        matched_text="123-45-6789",
                        description="SSN detected",
                    )
                ],
                original_text=unsafe_response.content,
            ),
            ValidationResult(
                is_safe=True,
                violations=[],
                original_text=safe_response.content,
            ),
        ]

        result = await agent_with_mocks.generate_response(
            persona=naive_retiree_persona,
            email_content=sample_nigerian_419_email,
            attack_type=AttackType.NIGERIAN_419,
            is_first_response=True,
        )

        # Should have called LLM twice
        assert mock_llm_client.chat_completion.call_count == 2
        # Should have regenerated once
        assert result.regeneration_count == 1
        # Final result should be safe
        assert result.safety_validated is True

    @pytest.mark.asyncio
    async def test_raises_error_after_max_regeneration_attempts(
        self,
        agent_with_mocks: ConversationAgent,
        mock_llm_client: MagicMock,
        mock_validator: MagicMock,
        naive_retiree_persona: PersonaProfile,
        sample_nigerian_419_email: str,
        unsafe_response: LLMResponse,
    ) -> None:
        """Agent should raise error after exhausting regeneration attempts."""
        mock_llm_client.chat_completion.return_value = unsafe_response
        mock_validator.validate.return_value = ValidationResult(
            is_safe=False,
            violations=[
                SafetyViolation(
                    violation_type=ViolationType.SSN,
                    matched_text="123-45-6789",
                    description="SSN detected",
                )
            ],
            original_text=unsafe_response.content,
        )

        with pytest.raises(ResponseGenerationError) as exc_info:
            await agent_with_mocks.generate_response(
                persona=naive_retiree_persona,
                email_content=sample_nigerian_419_email,
                attack_type=AttackType.NIGERIAN_419,
                is_first_response=True,
            )

        assert "safety" in str(exc_info.value).lower()


class TestConversationAgentErrorHandling:
    """Tests for error handling scenarios."""

    @pytest.mark.asyncio
    async def test_raises_error_on_llm_failure(
        self,
        agent_with_mocks: ConversationAgent,
        mock_llm_client: MagicMock,
        naive_retiree_persona: PersonaProfile,
        sample_nigerian_419_email: str,
    ) -> None:
        """Agent should raise ResponseGenerationError on LLM failure."""
        mock_llm_client.chat_completion.side_effect = LLMRequestError(
            "API connection failed"
        )

        with pytest.raises(ResponseGenerationError) as exc_info:
            await agent_with_mocks.generate_response(
                persona=naive_retiree_persona,
                email_content=sample_nigerian_419_email,
                attack_type=AttackType.NIGERIAN_419,
                is_first_response=True,
            )

        assert "Failed to generate response" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_error_preserves_original_exception(
        self,
        agent_with_mocks: ConversationAgent,
        mock_llm_client: MagicMock,
        naive_retiree_persona: PersonaProfile,
        sample_nigerian_419_email: str,
    ) -> None:
        """ResponseGenerationError should chain the original LLMRequestError."""
        original_error = LLMRequestError("Rate limit exceeded")
        mock_llm_client.chat_completion.side_effect = original_error

        with pytest.raises(ResponseGenerationError) as exc_info:
            await agent_with_mocks.generate_response(
                persona=naive_retiree_persona,
                email_content=sample_nigerian_419_email,
                attack_type=AttackType.NIGERIAN_419,
                is_first_response=True,
            )

        assert exc_info.value.__cause__ is original_error


class TestConversationAgentResponseCleaning:
    """Tests for response cleaning functionality."""

    @pytest.mark.asyncio
    async def test_removes_response_prefix(
        self,
        agent_with_mocks: ConversationAgent,
        mock_llm_client: MagicMock,
        naive_retiree_persona: PersonaProfile,
        sample_nigerian_419_email: str,
    ) -> None:
        """Agent should remove 'Response:' prefix from LLM output."""
        response = LLMResponse(
            content="Response: Oh my, this sounds wonderful!",
            used_fallback=False,
            model_used="gpt-4o",
        )
        mock_llm_client.chat_completion.return_value = response

        result = await agent_with_mocks.generate_response(
            persona=naive_retiree_persona,
            email_content=sample_nigerian_419_email,
            attack_type=AttackType.NIGERIAN_419,
            is_first_response=True,
        )

        assert not result.content.startswith("Response:")

    @pytest.mark.asyncio
    async def test_removes_wrapping_quotes(
        self,
        agent_with_mocks: ConversationAgent,
        mock_llm_client: MagicMock,
        naive_retiree_persona: PersonaProfile,
        sample_nigerian_419_email: str,
    ) -> None:
        """Agent should remove wrapping quotes from LLM output."""
        response = LLMResponse(
            content='"Oh my, this sounds wonderful!"',
            used_fallback=False,
            model_used="gpt-4o",
        )
        mock_llm_client.chat_completion.return_value = response

        result = await agent_with_mocks.generate_response(
            persona=naive_retiree_persona,
            email_content=sample_nigerian_419_email,
            attack_type=AttackType.NIGERIAN_419,
            is_first_response=True,
        )

        assert not result.content.startswith('"')
        assert not result.content.endswith('"')


class TestConversationAgentDependencyInjection:
    """Tests for dependency injection functionality."""

    @pytest.mark.asyncio
    async def test_uses_injected_client(
        self,
        mock_llm_client: MagicMock,
        mock_validator: MagicMock,
        naive_retiree_persona: PersonaProfile,
        sample_nigerian_419_email: str,
        safe_response: LLMResponse,
    ) -> None:
        """Agent should use the injected LLM client."""
        mock_llm_client.chat_completion.return_value = safe_response
        agent = ConversationAgent(client=mock_llm_client, validator=mock_validator)

        await agent.generate_response(
            persona=naive_retiree_persona,
            email_content=sample_nigerian_419_email,
            attack_type=AttackType.NIGERIAN_419,
            is_first_response=True,
        )

        mock_llm_client.chat_completion.assert_called_once()

    @pytest.mark.asyncio
    async def test_uses_injected_validator(
        self,
        mock_llm_client: MagicMock,
        mock_validator: MagicMock,
        naive_retiree_persona: PersonaProfile,
        sample_nigerian_419_email: str,
        safe_response: LLMResponse,
    ) -> None:
        """Agent should use the injected output validator."""
        mock_llm_client.chat_completion.return_value = safe_response
        agent = ConversationAgent(client=mock_llm_client, validator=mock_validator)

        await agent.generate_response(
            persona=naive_retiree_persona,
            email_content=sample_nigerian_419_email,
            attack_type=AttackType.NIGERIAN_419,
            is_first_response=True,
        )

        mock_validator.validate.assert_called()

    @pytest.mark.asyncio
    async def test_creates_default_dependencies_when_not_injected(self) -> None:
        """Agent should create default client and validator if not provided."""
        with patch("phishguard.agents.conversation.create_llm_client") as mock_factory:
            with patch(
                "phishguard.agents.conversation.OutputValidator"
            ) as mock_validator_class:
                mock_client = MagicMock(spec=LLMClient)
                mock_factory.return_value = mock_client
                mock_validator_class.return_value = MagicMock(spec=OutputValidator)

                ConversationAgent()

                mock_factory.assert_called_once()
                mock_validator_class.assert_called_once()


class TestConversationAgentPromptConstruction:
    """Tests for prompt construction passed to LLM."""

    @pytest.mark.asyncio
    async def test_includes_persona_in_prompt(
        self,
        agent_with_mocks: ConversationAgent,
        mock_llm_client: MagicMock,
        naive_retiree_persona: PersonaProfile,
        sample_nigerian_419_email: str,
        safe_response: LLMResponse,
    ) -> None:
        """Prompt should include persona name and details."""
        mock_llm_client.chat_completion.return_value = safe_response

        await agent_with_mocks.generate_response(
            persona=naive_retiree_persona,
            email_content=sample_nigerian_419_email,
            attack_type=AttackType.NIGERIAN_419,
            is_first_response=True,
        )

        call_kwargs = mock_llm_client.chat_completion.call_args.kwargs
        messages = call_kwargs["messages"]
        system_prompt = messages[0]["content"]

        assert naive_retiree_persona.name in system_prompt
        assert str(naive_retiree_persona.age) in system_prompt

    @pytest.mark.asyncio
    async def test_includes_email_content_in_prompt(
        self,
        agent_with_mocks: ConversationAgent,
        mock_llm_client: MagicMock,
        naive_retiree_persona: PersonaProfile,
        sample_nigerian_419_email: str,
        safe_response: LLMResponse,
    ) -> None:
        """Prompt should include the email content."""
        mock_llm_client.chat_completion.return_value = safe_response

        await agent_with_mocks.generate_response(
            persona=naive_retiree_persona,
            email_content=sample_nigerian_419_email,
            attack_type=AttackType.NIGERIAN_419,
            is_first_response=True,
        )

        call_kwargs = mock_llm_client.chat_completion.call_args.kwargs
        messages = call_kwargs["messages"]
        user_prompt = messages[1]["content"]

        assert "Dr. Emeka Okafor" in user_prompt

    @pytest.mark.asyncio
    async def test_uses_higher_temperature_for_creativity(
        self,
        agent_with_mocks: ConversationAgent,
        mock_llm_client: MagicMock,
        naive_retiree_persona: PersonaProfile,
        sample_nigerian_419_email: str,
        safe_response: LLMResponse,
    ) -> None:
        """Agent should use higher temperature for creative responses."""
        mock_llm_client.chat_completion.return_value = safe_response

        await agent_with_mocks.generate_response(
            persona=naive_retiree_persona,
            email_content=sample_nigerian_419_email,
            attack_type=AttackType.NIGERIAN_419,
            is_first_response=True,
        )

        call_kwargs = mock_llm_client.chat_completion.call_args.kwargs
        temperature = call_kwargs["temperature"]

        # Should use higher temperature (0.7-0.9) for creative roleplay
        assert temperature >= 0.7


class TestConversationAgentConversationHistory:
    """Tests for conversation history handling."""

    @pytest.mark.asyncio
    async def test_handles_empty_conversation_history(
        self,
        agent_with_mocks: ConversationAgent,
        mock_llm_client: MagicMock,
        naive_retiree_persona: PersonaProfile,
        sample_nigerian_419_email: str,
        safe_response: LLMResponse,
    ) -> None:
        """Agent should handle None or empty conversation history."""
        mock_llm_client.chat_completion.return_value = safe_response

        result = await agent_with_mocks.generate_response(
            persona=naive_retiree_persona,
            email_content=sample_nigerian_419_email,
            attack_type=AttackType.NIGERIAN_419,
            conversation_history=None,
            is_first_response=True,
        )

        assert result.content is not None

    @pytest.mark.asyncio
    async def test_includes_conversation_history_in_follow_up(
        self,
        agent_with_mocks: ConversationAgent,
        mock_llm_client: MagicMock,
        naive_retiree_persona: PersonaProfile,
        safe_response: LLMResponse,
    ) -> None:
        """Follow-up response should include conversation history."""
        mock_llm_client.chat_completion.return_value = safe_response

        history = [
            ConversationMessage(
                sender=MessageSender.BOT,
                content="Oh my, this sounds interesting!",
                turn_number=1,
            ),
            ConversationMessage(
                sender=MessageSender.SCAMMER,
                content="Yes, please send your bank details.",
                turn_number=1,
            ),
        ]

        await agent_with_mocks.generate_response(
            persona=naive_retiree_persona,
            email_content="Please provide your bank details now.",
            attack_type=AttackType.NIGERIAN_419,
            conversation_history=history,
            is_first_response=False,
        )

        call_kwargs = mock_llm_client.chat_completion.call_args.kwargs
        messages = call_kwargs["messages"]
        user_prompt = messages[1]["content"]

        # Should include previous messages
        has_content = "this sounds interesting" in user_prompt.lower()
        has_marker = "CONVERSATION_HISTORY" in user_prompt
        assert has_content or has_marker


class TestResponseGenerationResultModel:
    """Tests for ResponseGenerationResult model properties."""

    def test_generation_time_seconds_property(self) -> None:
        """generation_time_seconds should convert ms to seconds."""
        result = ResponseGenerationResult(
            content="Test response",
            generation_time_ms=2500,
            safety_validated=True,
            regeneration_count=0,
            used_fallback_model=False,
        )

        assert result.generation_time_seconds == 2.5

    def test_was_regenerated_property(self) -> None:
        """was_regenerated should be True when regeneration_count > 0."""
        result_no_regen = ResponseGenerationResult(
            content="Test",
            generation_time_ms=1000,
            regeneration_count=0,
        )
        result_with_regen = ResponseGenerationResult(
            content="Test",
            generation_time_ms=1000,
            regeneration_count=2,
        )

        assert result_no_regen.was_regenerated is False
        assert result_with_regen.was_regenerated is True


# -----------------------------------------------------------------------------
# Fixtures for Thinking Tests
# -----------------------------------------------------------------------------


@pytest.fixture
def json_response_with_thinking() -> LLMResponse:
    """Create a mock LLM response with structured JSON including thinking."""
    return LLMResponse(
        content='''{
            "thinking": {
                "turn_goal": "Build rapport and gather contact information",
                "selected_tactic": "Ask Questions",
                "reasoning": "The scammer mentioned an associate."
            },
            "response": "Oh my, this sounds wonderful! But who is your associate?"
        }''',
        used_fallback=False,
        model_used="gpt-4o",
    )


@pytest.fixture
def json_response_with_code_block() -> LLMResponse:
    """Create a mock LLM response with JSON wrapped in markdown code block."""
    return LLMResponse(
        content='''```json
{
    "thinking": {
        "turn_goal": "Extract payment method",
        "selected_tactic": "Show Interest",
        "reasoning": "Scammer wants money, so I will show enthusiasm."
    },
    "response": "Yes, I am very interested! How do I send the payment?"
}
```''',
        used_fallback=False,
        model_used="gpt-4o",
    )


@pytest.fixture
def plain_text_response() -> LLMResponse:
    """Create a mock LLM response without JSON (fallback case)."""
    return LLMResponse(
        content="Oh my, this sounds wonderful! But how did you find me?",
        used_fallback=False,
        model_used="gpt-4o",
    )


@pytest.fixture
def json_response_missing_thinking() -> LLMResponse:
    """Create a mock LLM response with JSON but missing thinking field."""
    return LLMResponse(
        content='{"response": "Hello, I am interested in your offer."}',
        used_fallback=False,
        model_used="gpt-4o",
    )


# -----------------------------------------------------------------------------
# Test Classes for Thinking Extraction
# -----------------------------------------------------------------------------


class TestConversationAgentThinkingExtraction:
    """Tests for agent thinking extraction from structured responses."""

    @pytest.mark.asyncio
    async def test_extracts_thinking_from_json_response(
        self,
        agent_with_mocks: ConversationAgent,
        mock_llm_client: MagicMock,
        mock_validator: MagicMock,
        naive_retiree_persona: PersonaProfile,
        sample_nigerian_419_email: str,
        json_response_with_thinking: LLMResponse,
    ) -> None:
        """Agent should extract AgentThinking from valid JSON response."""
        mock_llm_client.chat_completion.return_value = json_response_with_thinking

        result = await agent_with_mocks.generate_response(
            persona=naive_retiree_persona,
            email_content=sample_nigerian_419_email,
            attack_type=AttackType.NIGERIAN_419,
            is_first_response=True,
        )

        assert result.has_thinking is True
        assert result.thinking is not None
        expected_goal = "Build rapport and gather contact information"
        assert result.thinking.turn_goal == expected_goal
        assert result.thinking.selected_tactic == "Ask Questions"
        assert "associate" in result.thinking.reasoning

    @pytest.mark.asyncio
    async def test_extracts_thinking_from_code_block(
        self,
        agent_with_mocks: ConversationAgent,
        mock_llm_client: MagicMock,
        mock_validator: MagicMock,
        naive_retiree_persona: PersonaProfile,
        sample_nigerian_419_email: str,
        json_response_with_code_block: LLMResponse,
    ) -> None:
        """Agent should extract thinking from JSON wrapped in markdown code blocks."""
        mock_llm_client.chat_completion.return_value = json_response_with_code_block

        result = await agent_with_mocks.generate_response(
            persona=naive_retiree_persona,
            email_content=sample_nigerian_419_email,
            attack_type=AttackType.NIGERIAN_419,
            is_first_response=True,
        )

        assert result.has_thinking is True
        assert result.thinking.turn_goal == "Extract payment method"
        assert result.thinking.selected_tactic == "Show Interest"

    @pytest.mark.asyncio
    async def test_extracts_response_content_from_json(
        self,
        agent_with_mocks: ConversationAgent,
        mock_llm_client: MagicMock,
        mock_validator: MagicMock,
        naive_retiree_persona: PersonaProfile,
        sample_nigerian_419_email: str,
        json_response_with_thinking: LLMResponse,
    ) -> None:
        """Agent should extract response content from JSON structure."""
        mock_llm_client.chat_completion.return_value = json_response_with_thinking

        result = await agent_with_mocks.generate_response(
            persona=naive_retiree_persona,
            email_content=sample_nigerian_419_email,
            attack_type=AttackType.NIGERIAN_419,
            is_first_response=True,
        )

        assert "wonderful" in result.content
        assert "associate" in result.content

    @pytest.mark.asyncio
    async def test_graceful_fallback_for_plain_text_response(
        self,
        agent_with_mocks: ConversationAgent,
        mock_llm_client: MagicMock,
        mock_validator: MagicMock,
        naive_retiree_persona: PersonaProfile,
        sample_nigerian_419_email: str,
        plain_text_response: LLMResponse,
    ) -> None:
        """Agent should gracefully handle plain text (non-JSON) responses."""
        mock_llm_client.chat_completion.return_value = plain_text_response

        result = await agent_with_mocks.generate_response(
            persona=naive_retiree_persona,
            email_content=sample_nigerian_419_email,
            attack_type=AttackType.NIGERIAN_419,
            is_first_response=True,
        )

        # Should still return valid result
        assert result.content is not None
        assert len(result.content) > 0
        # Thinking should be None for plain text
        assert result.thinking is None
        assert result.has_thinking is False

    @pytest.mark.asyncio
    async def test_graceful_fallback_for_missing_thinking_field(
        self,
        agent_with_mocks: ConversationAgent,
        mock_llm_client: MagicMock,
        mock_validator: MagicMock,
        naive_retiree_persona: PersonaProfile,
        sample_nigerian_419_email: str,
        json_response_missing_thinking: LLMResponse,
    ) -> None:
        """Agent should handle JSON without thinking field gracefully."""
        mock_llm_client.chat_completion.return_value = json_response_missing_thinking

        result = await agent_with_mocks.generate_response(
            persona=naive_retiree_persona,
            email_content=sample_nigerian_419_email,
            attack_type=AttackType.NIGERIAN_419,
            is_first_response=True,
        )

        # Should still extract response content
        assert "interested" in result.content
        # Thinking should be None
        assert result.thinking is None

    @pytest.mark.asyncio
    async def test_thinking_does_not_affect_safety_validation(
        self,
        agent_with_mocks: ConversationAgent,
        mock_llm_client: MagicMock,
        mock_validator: MagicMock,
        naive_retiree_persona: PersonaProfile,
        sample_nigerian_419_email: str,
        json_response_with_thinking: LLMResponse,
    ) -> None:
        """Safety validation should only apply to response content, not thinking."""
        mock_llm_client.chat_completion.return_value = json_response_with_thinking

        await agent_with_mocks.generate_response(
            persona=naive_retiree_persona,
            email_content=sample_nigerian_419_email,
            attack_type=AttackType.NIGERIAN_419,
            is_first_response=True,
        )

        # Validator should be called with the response content, not the full JSON
        validate_call = mock_validator.validate.call_args
        validated_text = validate_call[0][0]
        # Should not contain thinking data
        assert "turn_goal" not in validated_text
        assert "selected_tactic" not in validated_text
