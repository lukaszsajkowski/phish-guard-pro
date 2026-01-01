"""Comprehensive unit tests for the ProfilerAgent.

These tests verify that the ProfilerAgent correctly:
1. Classifies emails using the LLM client
2. Returns valid (ClassificationResult, bool) tuples
3. Handles retry logic on transient errors
4. Returns fallback results when JSON parsing fails
5. Tracks classification time in milliseconds
6. Raises ClassificationError on LLM request failures
7. Uses injected LLM client for dependency injection

Test Categories:
- Successful classification scenarios
- Malformed JSON response handling
- LLM request error handling
- Classification time tracking
- Dependency injection
- Edge cases
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from phishguard.agents import ClassificationError, ProfilerAgent
from phishguard.llm import LLMClient, LLMRequestError, LLMResponse
from phishguard.models import AttackType, ClassificationResult

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
def profiler_with_mock_client(mock_llm_client: MagicMock) -> ProfilerAgent:
    """Create a ProfilerAgent with an injected mock client."""
    return ProfilerAgent(client=mock_llm_client)


@pytest.fixture
def nigerian_419_response() -> LLMResponse:
    """Create a mock LLM response for Nigerian 419 classification."""
    return LLMResponse(
        content=json.dumps(
            {
                "attack_type": "nigerian_419",
                "confidence": 95.5,
                "reasoning": "Classic advance-fee fraud indicators: foreign prince, "
                "large inheritance, request for personal banking details.",
            }
        ),
        used_fallback=False,
        model_used="gpt-4o",
    )


@pytest.fixture
def ceo_fraud_response() -> LLMResponse:
    """Create a mock LLM response for CEO fraud classification."""
    return LLMResponse(
        content=json.dumps(
            {
                "attack_type": "ceo_fraud",
                "confidence": 88.0,
                "reasoning": "Business email compromise: impersonates CEO, "
                "urgent wire transfer request, unusual payment instructions.",
            }
        ),
        used_fallback=False,
        model_used="gpt-4o",
    )


@pytest.fixture
def crypto_investment_response() -> LLMResponse:
    """Create a mock LLM response for crypto investment scam."""
    return LLMResponse(
        content=json.dumps(
            {
                "attack_type": "crypto_investment",
                "confidence": 92.0,
                "reasoning": "Cryptocurrency investment fraud: guaranteed returns, "
                "Bitcoin wallet address, urgency to invest.",
            }
        ),
        used_fallback=False,
        model_used="gpt-4o",
    )


@pytest.fixture
def fallback_model_response() -> LLMResponse:
    """Create a mock LLM response from fallback model."""
    return LLMResponse(
        content=json.dumps(
            {
                "attack_type": "tech_support",
                "confidence": 75.0,
                "reasoning": "Tech support scam indicators detected.",
            }
        ),
        used_fallback=True,
        model_used="gpt-4o-mini",
    )


@pytest.fixture
def malformed_json_response() -> LLMResponse:
    """Create a mock LLM response with malformed JSON."""
    return LLMResponse(
        content="This is not valid JSON at all",
        used_fallback=False,
        model_used="gpt-4o",
    )


@pytest.fixture
def partial_json_response() -> LLMResponse:
    """Create a mock LLM response with partial/incomplete JSON."""
    return LLMResponse(
        content='{"attack_type": "nigerian_419", "confidence":',
        used_fallback=False,
        model_used="gpt-4o",
    )


@pytest.fixture
def missing_field_json_response() -> LLMResponse:
    """Create a mock LLM response with missing required field."""
    return LLMResponse(
        content=json.dumps(
            {
                "attack_type": "nigerian_419",
                # missing "confidence" and "reasoning"
            }
        ),
        used_fallback=False,
        model_used="gpt-4o",
    )


@pytest.fixture
def markdown_wrapped_response() -> LLMResponse:
    """Create a mock LLM response wrapped in markdown code fence."""
    json_content = json.dumps(
        {
            "attack_type": "lottery_prize",
            "confidence": 90.0,
            "reasoning": "Lottery prize notification scam detected.",
        }
    )
    return LLMResponse(
        content=f"```json\n{json_content}\n```",
        used_fallback=False,
        model_used="gpt-4o",
    )


@pytest.fixture
def sample_nigerian_419_email() -> str:
    """Sample Nigerian 419 phishing email content."""
    return """
    Dear Friend,

    I am Dr. Emeka Okafor, a lawyer representing the estate of the late
    Mr. Williams Johnson who died in a plane crash with his wife and children.

    He left behind a sum of $15.5 million USD in a bank account with no
    next of kin. I am reaching out to you to assist in repatriating this
    fund as you share the same surname.

    You will receive 30% of the total sum as compensation for your assistance.
    Please reply with your full name, phone number, and bank account details.

    Regards,
    Dr. Emeka Okafor, Esq.
    """


@pytest.fixture
def sample_ceo_fraud_email() -> str:
    """Sample CEO fraud phishing email content."""
    return """
    Subject: URGENT: Wire Transfer Needed Today

    Hi,

    I'm in a meeting and cannot talk right now but I need you to process
    an urgent wire transfer. Please transfer $47,500 to the account below
    immediately. This is confidential - do not discuss with anyone.

    Account: 12345678901234
    Routing: 021000089
    Beneficiary: Global Partners LLC

    Complete this ASAP and confirm when done.

    Thanks,
    James (CEO)
    """


# -----------------------------------------------------------------------------
# Test Classes
# -----------------------------------------------------------------------------


class TestProfilerAgentSuccessfulClassification:
    """Tests for successful email classification scenarios."""

    @pytest.mark.asyncio
    async def test_classify_nigerian_419_email_returns_correct_category(
        self,
        profiler_with_mock_client: ProfilerAgent,
        mock_llm_client: MagicMock,
        nigerian_419_response: LLMResponse,
        sample_nigerian_419_email: str,
    ) -> None:
        """Nigerian 419 email should be classified as NIGERIAN_419."""
        mock_llm_client.chat_completion.return_value = nigerian_419_response

        result, used_fallback = await profiler_with_mock_client.classify(
            sample_nigerian_419_email
        )

        assert result.attack_type == AttackType.NIGERIAN_419
        assert result.confidence == 95.5
        assert "advance-fee fraud" in result.reasoning
        assert used_fallback is False

    @pytest.mark.asyncio
    async def test_classify_ceo_fraud_email_returns_correct_category(
        self,
        profiler_with_mock_client: ProfilerAgent,
        mock_llm_client: MagicMock,
        ceo_fraud_response: LLMResponse,
        sample_ceo_fraud_email: str,
    ) -> None:
        """CEO fraud email should be classified as CEO_FRAUD."""
        mock_llm_client.chat_completion.return_value = ceo_fraud_response

        result, used_fallback = await profiler_with_mock_client.classify(
            sample_ceo_fraud_email
        )

        assert result.attack_type == AttackType.CEO_FRAUD
        assert result.confidence == 88.0
        assert "Business email compromise" in result.reasoning
        assert used_fallback is False

    @pytest.mark.asyncio
    async def test_classify_returns_tuple_with_fallback_flag(
        self,
        profiler_with_mock_client: ProfilerAgent,
        mock_llm_client: MagicMock,
        nigerian_419_response: LLMResponse,
    ) -> None:
        """Classification should return tuple of (ClassificationResult, bool)."""
        mock_llm_client.chat_completion.return_value = nigerian_419_response

        result = await profiler_with_mock_client.classify("Test email content")

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], ClassificationResult)
        assert isinstance(result[1], bool)

    @pytest.mark.asyncio
    async def test_classify_with_fallback_model_returns_true_flag(
        self,
        profiler_with_mock_client: ProfilerAgent,
        mock_llm_client: MagicMock,
        fallback_model_response: LLMResponse,
    ) -> None:
        """Classification using fallback model should set used_fallback to True."""
        mock_llm_client.chat_completion.return_value = fallback_model_response

        result, used_fallback = await profiler_with_mock_client.classify(
            "Some email content"
        )

        assert result.attack_type == AttackType.TECH_SUPPORT
        assert used_fallback is True

    @pytest.mark.asyncio
    async def test_classify_handles_markdown_wrapped_json(
        self,
        profiler_with_mock_client: ProfilerAgent,
        mock_llm_client: MagicMock,
        markdown_wrapped_response: LLMResponse,
    ) -> None:
        """Classification should handle JSON wrapped in markdown code fences."""
        mock_llm_client.chat_completion.return_value = markdown_wrapped_response

        result, used_fallback = await profiler_with_mock_client.classify(
            "Test email about lottery"
        )

        assert result.attack_type == AttackType.LOTTERY_PRIZE
        assert result.confidence == 90.0
        assert used_fallback is False

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "attack_type_value,expected_enum",
        [
            ("nigerian_419", AttackType.NIGERIAN_419),
            ("ceo_fraud", AttackType.CEO_FRAUD),
            ("fake_invoice", AttackType.FAKE_INVOICE),
            ("romance_scam", AttackType.ROMANCE_SCAM),
            ("tech_support", AttackType.TECH_SUPPORT),
            ("lottery_prize", AttackType.LOTTERY_PRIZE),
            ("crypto_investment", AttackType.CRYPTO_INVESTMENT),
            ("delivery_scam", AttackType.DELIVERY_SCAM),
            ("not_phishing", AttackType.NOT_PHISHING),
        ],
        ids=[
            "nigerian_419",
            "ceo_fraud",
            "fake_invoice",
            "romance_scam",
            "tech_support",
            "lottery_prize",
            "crypto_investment",
            "delivery_scam",
            "not_phishing",
        ],
    )
    async def test_classify_all_attack_types(
        self,
        profiler_with_mock_client: ProfilerAgent,
        mock_llm_client: MagicMock,
        attack_type_value: str,
        expected_enum: AttackType,
    ) -> None:
        """All attack types should be correctly parsed and returned."""
        response = LLMResponse(
            content=json.dumps(
                {
                    "attack_type": attack_type_value,
                    "confidence": 85.0,
                    "reasoning": f"Detected {attack_type_value} indicators.",
                }
            ),
            used_fallback=False,
            model_used="gpt-4o",
        )
        mock_llm_client.chat_completion.return_value = response

        result, _ = await profiler_with_mock_client.classify("Test email")

        assert result.attack_type == expected_enum


class TestProfilerAgentClassificationTime:
    """Tests for classification time tracking."""

    @pytest.mark.asyncio
    async def test_classify_tracks_classification_time_in_milliseconds(
        self,
        profiler_with_mock_client: ProfilerAgent,
        mock_llm_client: MagicMock,
        nigerian_419_response: LLMResponse,
    ) -> None:
        """Classification should track time in milliseconds (time_ms > 0)."""
        mock_llm_client.chat_completion.return_value = nigerian_419_response

        result, _ = await profiler_with_mock_client.classify("Test email content")

        assert result.classification_time_ms >= 0
        assert isinstance(result.classification_time_ms, int)

    @pytest.mark.asyncio
    async def test_classify_time_increases_with_slow_response(
        self,
        profiler_with_mock_client: ProfilerAgent,
        mock_llm_client: MagicMock,
        nigerian_419_response: LLMResponse,
    ) -> None:
        """Classification time should reflect actual processing time."""
        import asyncio

        async def slow_response(*args, **kwargs):
            await asyncio.sleep(0.05)  # 50ms delay
            return nigerian_419_response

        mock_llm_client.chat_completion.side_effect = slow_response

        result, _ = await profiler_with_mock_client.classify("Test email content")

        # Should be at least 50ms due to the artificial delay
        assert result.classification_time_ms >= 50


class TestProfilerAgentMalformedJsonHandling:
    """Tests for handling malformed JSON responses."""

    @pytest.mark.asyncio
    async def test_classify_handles_malformed_json_returns_fallback(
        self,
        profiler_with_mock_client: ProfilerAgent,
        mock_llm_client: MagicMock,
        malformed_json_response: LLMResponse,
    ) -> None:
        """Malformed JSON should result in fallback classification."""
        mock_llm_client.chat_completion.return_value = malformed_json_response

        result, used_fallback = await profiler_with_mock_client.classify(
            "Test email content"
        )

        assert result.attack_type == AttackType.NOT_PHISHING
        assert result.confidence == 25.0
        assert "parsing failure" in result.reasoning.lower()
        assert "manual review" in result.reasoning.lower()

    @pytest.mark.asyncio
    async def test_classify_handles_partial_json_returns_fallback(
        self,
        profiler_with_mock_client: ProfilerAgent,
        mock_llm_client: MagicMock,
        partial_json_response: LLMResponse,
    ) -> None:
        """Partial/incomplete JSON should result in fallback classification."""
        mock_llm_client.chat_completion.return_value = partial_json_response

        result, _ = await profiler_with_mock_client.classify("Test email content")

        assert result.attack_type == AttackType.NOT_PHISHING
        assert result.confidence == 25.0

    @pytest.mark.asyncio
    async def test_classify_handles_missing_field_returns_fallback(
        self,
        profiler_with_mock_client: ProfilerAgent,
        mock_llm_client: MagicMock,
        missing_field_json_response: LLMResponse,
    ) -> None:
        """JSON with missing required fields should result in fallback."""
        mock_llm_client.chat_completion.return_value = missing_field_json_response

        result, _ = await profiler_with_mock_client.classify("Test email content")

        assert result.attack_type == AttackType.NOT_PHISHING
        assert result.confidence == 25.0

    @pytest.mark.asyncio
    async def test_classify_retries_on_malformed_json(
        self,
        profiler_with_mock_client: ProfilerAgent,
        mock_llm_client: MagicMock,
        malformed_json_response: LLMResponse,
        nigerian_419_response: LLMResponse,
    ) -> None:
        """Classification should retry on first malformed response."""
        # First call returns malformed, second returns valid
        mock_llm_client.chat_completion.side_effect = [
            malformed_json_response,
            nigerian_419_response,
        ]

        result, _ = await profiler_with_mock_client.classify("Test email content")

        # Should succeed on second attempt
        assert result.attack_type == AttackType.NIGERIAN_419
        assert result.confidence == 95.5
        # Verify two calls were made (retry)
        assert mock_llm_client.chat_completion.call_count == 2

    @pytest.mark.asyncio
    async def test_classify_returns_fallback_after_max_retries(
        self,
        profiler_with_mock_client: ProfilerAgent,
        mock_llm_client: MagicMock,
        malformed_json_response: LLMResponse,
    ) -> None:
        """Classification should return fallback after exhausting retries."""
        # All attempts return malformed JSON
        mock_llm_client.chat_completion.return_value = malformed_json_response

        result, _ = await profiler_with_mock_client.classify("Test email content")

        # Should return fallback after MAX_PARSE_RETRIES + 1 attempts
        assert result.attack_type == AttackType.NOT_PHISHING
        assert result.confidence == 25.0
        # Should have made 2 attempts (1 initial + 1 retry)
        assert mock_llm_client.chat_completion.call_count == 2


class TestProfilerAgentLLMRequestErrors:
    """Tests for LLM request error handling."""

    @pytest.mark.asyncio
    async def test_classify_raises_classification_error_on_llm_failure(
        self,
        profiler_with_mock_client: ProfilerAgent,
        mock_llm_client: MagicMock,
    ) -> None:
        """LLMRequestError should be wrapped in ClassificationError."""
        mock_llm_client.chat_completion.side_effect = LLMRequestError(
            "API connection failed"
        )

        with pytest.raises(ClassificationError) as exc_info:
            await profiler_with_mock_client.classify("Test email content")

        assert "Failed to classify email" in str(exc_info.value)
        assert "API connection failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_classify_error_preserves_original_exception(
        self,
        profiler_with_mock_client: ProfilerAgent,
        mock_llm_client: MagicMock,
    ) -> None:
        """ClassificationError should chain the original LLMRequestError."""
        original_error = LLMRequestError("Rate limit exceeded")
        mock_llm_client.chat_completion.side_effect = original_error

        with pytest.raises(ClassificationError) as exc_info:
            await profiler_with_mock_client.classify("Test email content")

        assert exc_info.value.__cause__ is original_error

    @pytest.mark.asyncio
    async def test_classify_does_not_retry_on_llm_request_error(
        self,
        profiler_with_mock_client: ProfilerAgent,
        mock_llm_client: MagicMock,
    ) -> None:
        """LLMRequestError should be raised immediately without retry."""
        mock_llm_client.chat_completion.side_effect = LLMRequestError(
            "Authentication failed"
        )

        with pytest.raises(ClassificationError):
            await profiler_with_mock_client.classify("Test email content")

        # Should only have been called once (no retry on LLMRequestError)
        assert mock_llm_client.chat_completion.call_count == 1


class TestProfilerAgentDependencyInjection:
    """Tests for dependency injection functionality."""

    @pytest.mark.asyncio
    async def test_profiler_uses_injected_client(
        self,
        mock_llm_client: MagicMock,
        nigerian_419_response: LLMResponse,
    ) -> None:
        """ProfilerAgent should use the injected LLM client."""
        mock_llm_client.chat_completion.return_value = nigerian_419_response
        profiler = ProfilerAgent(client=mock_llm_client)

        await profiler.classify("Test email content")

        mock_llm_client.chat_completion.assert_called_once()

    @pytest.mark.asyncio
    async def test_profiler_creates_default_client_when_not_injected(
        self,
    ) -> None:
        """ProfilerAgent should create default client if none provided."""
        with patch("phishguard.agents.profiler.create_llm_client") as mock_factory:
            mock_client = MagicMock(spec=LLMClient)
            mock_factory.return_value = mock_client

            ProfilerAgent()

            mock_factory.assert_called_once()

    @pytest.mark.asyncio
    async def test_profiler_passes_correct_parameters_to_client(
        self,
        profiler_with_mock_client: ProfilerAgent,
        mock_llm_client: MagicMock,
        nigerian_419_response: LLMResponse,
    ) -> None:
        """ProfilerAgent should pass correct parameters to LLM client."""
        mock_llm_client.chat_completion.return_value = nigerian_419_response

        await profiler_with_mock_client.classify("Test email content")

        call_kwargs = mock_llm_client.chat_completion.call_args.kwargs
        assert "messages" in call_kwargs
        assert "temperature" in call_kwargs
        assert "max_tokens" in call_kwargs
        assert call_kwargs["temperature"] == 0.2
        assert call_kwargs["max_tokens"] == 200


class TestProfilerAgentMessageConstruction:
    """Tests for message construction passed to LLM."""

    @pytest.mark.asyncio
    async def test_classify_includes_system_and_user_messages(
        self,
        profiler_with_mock_client: ProfilerAgent,
        mock_llm_client: MagicMock,
        nigerian_419_response: LLMResponse,
    ) -> None:
        """Classification should include both system and user messages."""
        mock_llm_client.chat_completion.return_value = nigerian_419_response

        await profiler_with_mock_client.classify("Test email content")

        call_kwargs = mock_llm_client.chat_completion.call_args.kwargs
        messages = call_kwargs["messages"]

        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

    @pytest.mark.asyncio
    async def test_classify_includes_email_content_in_user_message(
        self,
        profiler_with_mock_client: ProfilerAgent,
        mock_llm_client: MagicMock,
        nigerian_419_response: LLMResponse,
    ) -> None:
        """User message should include the email content."""
        mock_llm_client.chat_completion.return_value = nigerian_419_response
        test_email = "This is a specific test email about a Nigerian prince."

        await profiler_with_mock_client.classify(test_email)

        call_kwargs = mock_llm_client.chat_completion.call_args.kwargs
        user_message = call_kwargs["messages"][1]["content"]

        assert test_email in user_message


class TestProfilerAgentEdgeCases:
    """Tests for edge cases and special scenarios."""

    @pytest.mark.asyncio
    async def test_classify_empty_email_content(
        self,
        profiler_with_mock_client: ProfilerAgent,
        mock_llm_client: MagicMock,
    ) -> None:
        """Classification of empty email should still invoke LLM."""
        response = LLMResponse(
            content=json.dumps(
                {
                    "attack_type": "not_phishing",
                    "confidence": 50.0,
                    "reasoning": "Empty content cannot be classified.",
                }
            ),
            used_fallback=False,
            model_used="gpt-4o",
        )
        mock_llm_client.chat_completion.return_value = response

        result, _ = await profiler_with_mock_client.classify("")

        assert result.attack_type == AttackType.NOT_PHISHING
        mock_llm_client.chat_completion.assert_called_once()

    @pytest.mark.asyncio
    async def test_classify_very_long_email_content(
        self,
        profiler_with_mock_client: ProfilerAgent,
        mock_llm_client: MagicMock,
        nigerian_419_response: LLMResponse,
    ) -> None:
        """Classification should handle very long email content."""
        mock_llm_client.chat_completion.return_value = nigerian_419_response
        long_email = "x" * 50_000

        result, _ = await profiler_with_mock_client.classify(long_email)

        assert result.attack_type == AttackType.NIGERIAN_419
        mock_llm_client.chat_completion.assert_called_once()

    @pytest.mark.asyncio
    async def test_classify_unicode_email_content(
        self,
        profiler_with_mock_client: ProfilerAgent,
        mock_llm_client: MagicMock,
        nigerian_419_response: LLMResponse,
    ) -> None:
        """Classification should handle Unicode characters in email."""
        mock_llm_client.chat_completion.return_value = nigerian_419_response
        unicode_email = "Hello! Special chars test content here"

        result, _ = await profiler_with_mock_client.classify(unicode_email)

        assert result.attack_type == AttackType.NIGERIAN_419

    @pytest.mark.asyncio
    async def test_classify_with_invalid_attack_type_returns_fallback(
        self,
        profiler_with_mock_client: ProfilerAgent,
        mock_llm_client: MagicMock,
    ) -> None:
        """Invalid attack_type in JSON should result in fallback."""
        response = LLMResponse(
            content=json.dumps(
                {
                    "attack_type": "unknown_attack_type",
                    "confidence": 85.0,
                    "reasoning": "Test reasoning.",
                }
            ),
            used_fallback=False,
            model_used="gpt-4o",
        )
        mock_llm_client.chat_completion.return_value = response

        result, _ = await profiler_with_mock_client.classify("Test email")

        # Should return fallback due to invalid enum value
        assert result.attack_type == AttackType.NOT_PHISHING
        assert result.confidence == 25.0

    @pytest.mark.asyncio
    async def test_classify_confidence_boundary_values(
        self,
        profiler_with_mock_client: ProfilerAgent,
        mock_llm_client: MagicMock,
    ) -> None:
        """Classification should handle confidence at boundary values."""
        for confidence in [0.0, 50.0, 100.0]:
            response = LLMResponse(
                content=json.dumps(
                    {
                        "attack_type": "nigerian_419",
                        "confidence": confidence,
                        "reasoning": "Test reasoning.",
                    }
                ),
                used_fallback=False,
                model_used="gpt-4o",
            )
            mock_llm_client.chat_completion.return_value = response

            result, _ = await profiler_with_mock_client.classify("Test email")

            assert result.confidence == confidence


class TestClassificationResult:
    """Tests for ClassificationResult model integration."""

    @pytest.mark.asyncio
    async def test_classification_result_is_phishing_property(
        self,
        profiler_with_mock_client: ProfilerAgent,
        mock_llm_client: MagicMock,
        nigerian_419_response: LLMResponse,
    ) -> None:
        """ClassificationResult.is_phishing should be True for phishing types."""
        mock_llm_client.chat_completion.return_value = nigerian_419_response

        result, _ = await profiler_with_mock_client.classify("Test email")

        assert result.is_phishing is True

    @pytest.mark.asyncio
    async def test_classification_result_not_phishing_property(
        self,
        profiler_with_mock_client: ProfilerAgent,
        mock_llm_client: MagicMock,
    ) -> None:
        """ClassificationResult.is_phishing should be False for NOT_PHISHING."""
        response = LLMResponse(
            content=json.dumps(
                {
                    "attack_type": "not_phishing",
                    "confidence": 95.0,
                    "reasoning": "Legitimate email content.",
                }
            ),
            used_fallback=False,
            model_used="gpt-4o",
        )
        mock_llm_client.chat_completion.return_value = response

        result, _ = await profiler_with_mock_client.classify("Test email")

        assert result.is_phishing is False

    @pytest.mark.asyncio
    async def test_classification_result_is_high_confidence(
        self,
        profiler_with_mock_client: ProfilerAgent,
        mock_llm_client: MagicMock,
        nigerian_419_response: LLMResponse,
    ) -> None:
        """ClassificationResult.is_high_confidence should be True for >=80%."""
        mock_llm_client.chat_completion.return_value = nigerian_419_response

        result, _ = await profiler_with_mock_client.classify("Test email")

        assert result.is_high_confidence is True
        assert result.confidence >= 80.0

    @pytest.mark.asyncio
    async def test_classification_result_display_name(
        self,
        profiler_with_mock_client: ProfilerAgent,
        mock_llm_client: MagicMock,
        nigerian_419_response: LLMResponse,
    ) -> None:
        """ClassificationResult attack_type should have proper display name."""
        mock_llm_client.chat_completion.return_value = nigerian_419_response

        result, _ = await profiler_with_mock_client.classify("Test email")

        assert result.attack_type.display_name == "Nigerian 419"
