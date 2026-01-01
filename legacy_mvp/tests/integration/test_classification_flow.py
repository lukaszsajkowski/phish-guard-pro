"""Integration tests for the Classification Flow in PhishGuard.

This module tests the complete classification pipeline:
Email Input -> Profiler Agent -> Classification Result -> Session State Update

Test Categories:
- Full flow with mocked LLM responses
- Session stage transitions (INPUT -> ANALYZING -> CLASSIFIED)
- Classification result storage in session state
- Fallback model flag propagation
- Phishing vs legitimate email detection

All tests mock the LLM client to ensure:
- Tests are fast and deterministic
- No external API calls are made
- Controlled test scenarios with predictable outputs
"""

from __future__ import annotations

import json
import time
from unittest.mock import AsyncMock, MagicMock

import pytest
from faker import Faker

from phishguard.agents import ProfilerAgent
from phishguard.llm import LLMClient, LLMClientConfig, LLMResponse
from phishguard.models import (
    AttackType,
    SessionStage,
    SessionState,
    create_initial_session_state,
)

# Seed Faker for reproducibility
fake = Faker()
Faker.seed(42)


# -----------------------------------------------------------------------------
# Test Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def mock_llm_client() -> MagicMock:
    """Create a mock LLM client for testing.

    Returns:
        A MagicMock configured to act as an LLMClient.
    """
    mock_client = MagicMock(spec=LLMClient)
    mock_client.config = LLMClientConfig()
    return mock_client


@pytest.fixture
def nigerian_419_email() -> str:
    """Generate a sample Nigerian 419 phishing email.

    Returns:
        Email content typical of a 419 advance-fee fraud.
    """
    return """
    Dear Friend,

    I am Prince Abubakar from Nigeria. I have $45,000,000 USD that I need
    to transfer out of my country urgently. I am seeking a trustworthy
    foreign partner to help me move these funds.

    In return for your assistance, I will give you 30% of the total amount.
    Please reply with your full name, bank account details, and phone number.

    God bless you.

    Prince Abubakar
    """


@pytest.fixture
def ceo_fraud_email() -> str:
    """Generate a sample CEO fraud / BEC phishing email.

    Returns:
        Email content typical of business email compromise.
    """
    return """
    Hi,

    I need you to process an urgent wire transfer of $50,000 to a new vendor.
    I'm in a meeting and can't call right now, but this needs to happen today.

    Use this account:
    Bank: First National Bank
    Account: 12345678
    Routing: 987654321

    Do not discuss this with anyone else. Keep it confidential.

    Thanks,
    John Smith
    CEO
    """


@pytest.fixture
def legitimate_email() -> str:
    """Generate a legitimate (non-phishing) email.

    Returns:
        Email content that should be classified as NOT_PHISHING.
    """
    return """
    Hi Team,

    Just a reminder that our weekly standup meeting is tomorrow at 10 AM.
    Please come prepared with your updates and any blockers you're facing.

    See you there!

    Best,
    Sarah
    """


@pytest.fixture
def mock_nigerian_419_response() -> str:
    """Create a mock LLM response for Nigerian 419 classification.

    Returns:
        JSON string representing the classification result.
    """
    return json.dumps(
        {
            "attack_type": "nigerian_419",
            "confidence": 95.5,
            "reasoning": (
                "Email exhibits classic 419 scam indicators: claims to be a Nigerian "
                "prince, mentions large sum of money ($45M), requests personal banking "
                "details, promises percentage of funds in return for assistance."
            ),
        }
    )


@pytest.fixture
def mock_ceo_fraud_response() -> str:
    """Create a mock LLM response for CEO fraud classification.

    Returns:
        JSON string representing the classification result.
    """
    return json.dumps(
        {
            "attack_type": "ceo_fraud",
            "confidence": 92.0,
            "reasoning": (
                "Email impersonates a CEO requesting urgent wire transfer. Contains "
                "typical BEC indicators: urgency, request for confidentiality, "
                "direct bank account details, pressure to act immediately."
            ),
        }
    )


@pytest.fixture
def mock_not_phishing_response() -> str:
    """Create a mock LLM response for legitimate email classification.

    Returns:
        JSON string representing the classification result.
    """
    return json.dumps(
        {
            "attack_type": "not_phishing",
            "confidence": 88.0,
            "reasoning": (
                "Email is a routine meeting reminder. No suspicious indicators: "
                "no financial requests, no urgency pressure, no external links, "
                "no request for sensitive information."
            ),
        }
    )


# -----------------------------------------------------------------------------
# Test: Full Classification Flow Stores Result in Session
# -----------------------------------------------------------------------------


class TestClassificationFlowStoresResultInSession:
    """Test that the classification flow correctly stores results in session state."""

    @pytest.mark.asyncio
    async def test_classification_flow_stores_result_in_session(
        self,
        mock_llm_client: MagicMock,
        nigerian_419_email: str,
        mock_nigerian_419_response: str,
    ) -> None:
        """Test that classification result is properly stored in session state.

        This test verifies the complete flow:
        1. Session starts with email content
        2. Profiler classifies the email
        3. Result is stored in session
        4. Session reflects classified state
        """
        # Arrange: Create session and set up mock
        session = create_initial_session_state()
        session.email_content = nigerian_419_email

        mock_llm_client.chat_completion = AsyncMock(
            return_value=LLMResponse(
                content=mock_nigerian_419_response,
                used_fallback=False,
                model_used="gpt-4o",
            )
        )

        # Act: Run classification
        profiler = ProfilerAgent(client=mock_llm_client)
        result, used_fallback = await profiler.classify(session.email_content)

        # Update session state
        session.classification_result = result
        session.used_fallback_model = used_fallback
        session.stage = SessionStage.CLASSIFIED

        # Assert: Verify session state is correctly updated
        assert session.is_classified is True
        assert session.classification_result is not None
        assert session.classification_result.attack_type == AttackType.NIGERIAN_419
        assert session.classification_result.confidence == 95.5
        assert session.stage == SessionStage.CLASSIFIED
        assert session.used_fallback_model is False

    @pytest.mark.asyncio
    async def test_classification_result_has_all_required_fields(
        self,
        mock_llm_client: MagicMock,
        ceo_fraud_email: str,
        mock_ceo_fraud_response: str,
    ) -> None:
        """Test that classification result contains all required fields."""
        # Arrange
        session = SessionState(email_content=ceo_fraud_email)

        mock_llm_client.chat_completion = AsyncMock(
            return_value=LLMResponse(
                content=mock_ceo_fraud_response,
                used_fallback=False,
                model_used="gpt-4o",
            )
        )

        # Act
        profiler = ProfilerAgent(client=mock_llm_client)
        result, _ = await profiler.classify(session.email_content)
        session.classification_result = result

        # Assert: All fields are populated
        assert session.classification_result.attack_type is not None
        assert session.classification_result.confidence >= 0.0
        assert session.classification_result.confidence <= 100.0
        assert len(session.classification_result.reasoning) > 0
        assert session.classification_result.classification_time_ms >= 0


# -----------------------------------------------------------------------------
# Test: Session Stage Transitions
# -----------------------------------------------------------------------------


class TestClassificationFlowUpdatesSessionStage:
    """Test that session stage transitions correctly during classification."""

    @pytest.mark.asyncio
    async def test_session_starts_in_input_stage(self) -> None:
        """Test that new sessions start in INPUT stage."""
        session = create_initial_session_state()

        assert session.stage == SessionStage.INPUT
        assert session.is_input_stage is True
        assert session.classification_result is None

    @pytest.mark.asyncio
    async def test_stage_transitions_to_analyzing(self) -> None:
        """Test transition from INPUT to ANALYZING stage."""
        session = create_initial_session_state()
        session.email_content = "Some phishing email content..."

        # Simulate start of analysis
        session.stage = SessionStage.ANALYZING

        assert session.stage == SessionStage.ANALYZING
        assert session.is_input_stage is False
        assert session.email_content is not None

    @pytest.mark.asyncio
    async def test_stage_transitions_to_classified_after_analysis(
        self,
        mock_llm_client: MagicMock,
        nigerian_419_email: str,
        mock_nigerian_419_response: str,
    ) -> None:
        """Test full stage progression: INPUT -> ANALYZING -> CLASSIFIED."""
        # Arrange
        session = create_initial_session_state()
        session.email_content = nigerian_419_email

        mock_llm_client.chat_completion = AsyncMock(
            return_value=LLMResponse(
                content=mock_nigerian_419_response,
                used_fallback=False,
                model_used="gpt-4o",
            )
        )

        # Initial state
        assert session.stage == SessionStage.INPUT

        # Transition to ANALYZING
        session.stage = SessionStage.ANALYZING
        assert session.stage == SessionStage.ANALYZING

        # Perform classification
        profiler = ProfilerAgent(client=mock_llm_client)
        result, used_fallback = await profiler.classify(session.email_content)

        # Transition to CLASSIFIED
        session.classification_result = result
        session.used_fallback_model = used_fallback
        session.stage = SessionStage.CLASSIFIED

        assert session.stage == SessionStage.CLASSIFIED
        assert session.is_classified is True

    @pytest.mark.asyncio
    async def test_is_classified_false_before_classification(self) -> None:
        """Test that is_classified returns False before classification."""
        session = create_initial_session_state()
        session.email_content = "Some email content"
        session.stage = SessionStage.ANALYZING

        assert session.is_classified is False
        assert session.classification_result is None

    @pytest.mark.asyncio
    async def test_is_classified_true_after_classification(
        self,
        mock_llm_client: MagicMock,
        legitimate_email: str,
        mock_not_phishing_response: str,
    ) -> None:
        """Test that is_classified returns True after classification."""
        # Arrange
        session = SessionState(email_content=legitimate_email)

        mock_llm_client.chat_completion = AsyncMock(
            return_value=LLMResponse(
                content=mock_not_phishing_response,
                used_fallback=False,
                model_used="gpt-4o",
            )
        )

        # Act
        profiler = ProfilerAgent(client=mock_llm_client)
        result, _ = await profiler.classify(session.email_content)
        session.classification_result = result

        # Assert
        assert session.is_classified is True


# -----------------------------------------------------------------------------
# Test: Phishing Detection
# -----------------------------------------------------------------------------


class TestClassificationFlowHandlesPhishingDetection:
    """Test classification of phishing emails."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "attack_type,confidence",
        [
            (AttackType.NIGERIAN_419, 95.0),
            (AttackType.CEO_FRAUD, 92.0),
            (AttackType.FAKE_INVOICE, 88.5),
            (AttackType.ROMANCE_SCAM, 85.0),
            (AttackType.TECH_SUPPORT, 90.0),
            (AttackType.LOTTERY_PRIZE, 93.5),
            (AttackType.CRYPTO_INVESTMENT, 87.0),
            (AttackType.DELIVERY_SCAM, 91.0),
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
        ],
    )
    async def test_classification_identifies_phishing_types(
        self,
        mock_llm_client: MagicMock,
        attack_type: AttackType,
        confidence: float,
    ) -> None:
        """Test that all phishing attack types are correctly identified."""
        # Arrange
        email_content = f"Sample email for {attack_type.display_name} testing"
        mock_response = json.dumps(
            {
                "attack_type": attack_type.value,
                "confidence": confidence,
                "reasoning": f"Characteristics of {attack_type.display_name}.",
            }
        )

        mock_llm_client.chat_completion = AsyncMock(
            return_value=LLMResponse(
                content=mock_response,
                used_fallback=False,
                model_used="gpt-4o",
            )
        )

        # Act
        profiler = ProfilerAgent(client=mock_llm_client)
        result, _ = await profiler.classify(email_content)

        # Assert
        assert result.attack_type == attack_type
        assert result.confidence == confidence
        assert result.is_phishing is True

    @pytest.mark.asyncio
    async def test_classification_result_is_phishing_property(
        self,
        mock_llm_client: MagicMock,
        nigerian_419_email: str,
        mock_nigerian_419_response: str,
    ) -> None:
        """Test that is_phishing property correctly identifies phishing."""
        # Arrange
        mock_llm_client.chat_completion = AsyncMock(
            return_value=LLMResponse(
                content=mock_nigerian_419_response,
                used_fallback=False,
                model_used="gpt-4o",
            )
        )

        # Act
        profiler = ProfilerAgent(client=mock_llm_client)
        result, _ = await profiler.classify(nigerian_419_email)

        # Assert
        assert result.is_phishing is True
        assert result.attack_type != AttackType.NOT_PHISHING

    @pytest.mark.asyncio
    async def test_high_confidence_classification(
        self,
        mock_llm_client: MagicMock,
    ) -> None:
        """Test that high confidence (>=80%) is correctly identified."""
        # Arrange
        mock_response = json.dumps(
            {
                "attack_type": "crypto_investment",
                "confidence": 95.0,
                "reasoning": "High confidence phishing detection.",
            }
        )

        mock_llm_client.chat_completion = AsyncMock(
            return_value=LLMResponse(
                content=mock_response,
                used_fallback=False,
                model_used="gpt-4o",
            )
        )

        # Act
        profiler = ProfilerAgent(client=mock_llm_client)
        result, _ = await profiler.classify("Sample crypto scam email")

        # Assert
        assert result.is_high_confidence is True
        assert result.confidence >= 80.0


# -----------------------------------------------------------------------------
# Test: Legitimate Email (Not Phishing)
# -----------------------------------------------------------------------------


class TestClassificationFlowHandlesNotPhishing:
    """Test classification of legitimate (non-phishing) emails."""

    @pytest.mark.asyncio
    async def test_legitimate_email_classified_as_not_phishing(
        self,
        mock_llm_client: MagicMock,
        legitimate_email: str,
        mock_not_phishing_response: str,
    ) -> None:
        """Test that legitimate emails are correctly classified as NOT_PHISHING."""
        # Arrange
        session = SessionState(email_content=legitimate_email)

        mock_llm_client.chat_completion = AsyncMock(
            return_value=LLMResponse(
                content=mock_not_phishing_response,
                used_fallback=False,
                model_used="gpt-4o",
            )
        )

        # Act
        profiler = ProfilerAgent(client=mock_llm_client)
        result, _ = await profiler.classify(session.email_content)
        session.classification_result = result
        session.stage = SessionStage.CLASSIFIED

        # Assert
        assert session.is_classified is True
        assert result.attack_type == AttackType.NOT_PHISHING
        assert result.is_phishing is False

    @pytest.mark.asyncio
    async def test_not_phishing_result_properties(
        self,
        mock_llm_client: MagicMock,
        legitimate_email: str,
        mock_not_phishing_response: str,
    ) -> None:
        """Test that NOT_PHISHING classification has correct properties."""
        # Arrange
        mock_llm_client.chat_completion = AsyncMock(
            return_value=LLMResponse(
                content=mock_not_phishing_response,
                used_fallback=False,
                model_used="gpt-4o",
            )
        )

        # Act
        profiler = ProfilerAgent(client=mock_llm_client)
        result, _ = await profiler.classify(legitimate_email)

        # Assert
        assert result.attack_type == AttackType.NOT_PHISHING
        assert result.attack_type.display_name == "Not Phishing"
        assert result.is_phishing is False
        assert len(result.reasoning) > 0

    @pytest.mark.asyncio
    async def test_low_confidence_not_phishing(
        self,
        mock_llm_client: MagicMock,
    ) -> None:
        """Test NOT_PHISHING with low confidence (uncertain classification)."""
        # Arrange
        mock_response = json.dumps(
            {
                "attack_type": "not_phishing",
                "confidence": 55.0,
                "reasoning": "Email appears legitimate, some elements ambiguous.",
            }
        )

        mock_llm_client.chat_completion = AsyncMock(
            return_value=LLMResponse(
                content=mock_response,
                used_fallback=False,
                model_used="gpt-4o",
            )
        )

        # Act
        profiler = ProfilerAgent(client=mock_llm_client)
        result, _ = await profiler.classify("Ambiguous email content")

        # Assert
        assert result.attack_type == AttackType.NOT_PHISHING
        assert result.is_high_confidence is False
        assert result.confidence < 80.0


# -----------------------------------------------------------------------------
# Test: Fallback Model Flag Propagation
# -----------------------------------------------------------------------------


class TestClassificationFlowPropagatesFallbackFlag:
    """Test that fallback model usage is correctly propagated to session state."""

    @pytest.mark.asyncio
    async def test_primary_model_used_fallback_flag_false(
        self,
        mock_llm_client: MagicMock,
        nigerian_419_email: str,
        mock_nigerian_419_response: str,
    ) -> None:
        """Test that used_fallback is False when primary model succeeds."""
        # Arrange
        session = SessionState(email_content=nigerian_419_email)

        mock_llm_client.chat_completion = AsyncMock(
            return_value=LLMResponse(
                content=mock_nigerian_419_response,
                used_fallback=False,
                model_used="gpt-4o",
            )
        )

        # Act
        profiler = ProfilerAgent(client=mock_llm_client)
        result, used_fallback = await profiler.classify(session.email_content)

        session.classification_result = result
        session.used_fallback_model = used_fallback
        session.stage = SessionStage.CLASSIFIED

        # Assert
        assert used_fallback is False
        assert session.used_fallback_model is False

    @pytest.mark.asyncio
    async def test_fallback_model_used_flag_true(
        self,
        mock_llm_client: MagicMock,
        nigerian_419_email: str,
        mock_nigerian_419_response: str,
    ) -> None:
        """Test that used_fallback is True when fallback model is used."""
        # Arrange
        session = SessionState(email_content=nigerian_419_email)

        # Simulate fallback model being used
        mock_llm_client.chat_completion = AsyncMock(
            return_value=LLMResponse(
                content=mock_nigerian_419_response,
                used_fallback=True,
                model_used="gpt-4o-mini",
            )
        )

        # Act
        profiler = ProfilerAgent(client=mock_llm_client)
        result, used_fallback = await profiler.classify(session.email_content)

        session.classification_result = result
        session.used_fallback_model = used_fallback
        session.stage = SessionStage.CLASSIFIED

        # Assert
        assert used_fallback is True
        assert session.used_fallback_model is True

    @pytest.mark.asyncio
    async def test_session_default_fallback_flag_is_false(self) -> None:
        """Test that session starts with used_fallback_model as False."""
        session = create_initial_session_state()

        assert session.used_fallback_model is False

    @pytest.mark.asyncio
    async def test_fallback_flag_persists_in_session(
        self,
        mock_llm_client: MagicMock,
        ceo_fraud_email: str,
        mock_ceo_fraud_response: str,
    ) -> None:
        """Test that fallback flag is preserved after multiple operations."""
        # Arrange
        session = SessionState(email_content=ceo_fraud_email)

        mock_llm_client.chat_completion = AsyncMock(
            return_value=LLMResponse(
                content=mock_ceo_fraud_response,
                used_fallback=True,
                model_used="gpt-4o-mini",
            )
        )

        # Act
        profiler = ProfilerAgent(client=mock_llm_client)
        result, used_fallback = await profiler.classify(session.email_content)

        session.classification_result = result
        session.used_fallback_model = used_fallback
        session.stage = SessionStage.CLASSIFIED

        # Simulate further state changes
        session.stage = SessionStage.CONVERSATION

        # Assert: Fallback flag should still be True
        assert session.used_fallback_model is True


# -----------------------------------------------------------------------------
# Test: Classification Performance
# -----------------------------------------------------------------------------


class TestClassificationPerformance:
    """Test that classification completes within reasonable time limits."""

    @pytest.mark.asyncio
    async def test_classification_completes_quickly_with_mock(
        self,
        mock_llm_client: MagicMock,
        nigerian_419_email: str,
        mock_nigerian_419_response: str,
    ) -> None:
        """Test that mocked classification is fast (<100ms for mocked calls)."""
        # Arrange
        mock_llm_client.chat_completion = AsyncMock(
            return_value=LLMResponse(
                content=mock_nigerian_419_response,
                used_fallback=False,
                model_used="gpt-4o",
            )
        )

        # Act
        profiler = ProfilerAgent(client=mock_llm_client)
        start_time = time.perf_counter()
        result, _ = await profiler.classify(nigerian_419_email)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Assert: Mocked call should be very fast
        assert elapsed_ms < 100  # 100ms for mocked call
        assert result.classification_time_ms >= 0

    @pytest.mark.asyncio
    async def test_classification_time_recorded_in_result(
        self,
        mock_llm_client: MagicMock,
        ceo_fraud_email: str,
        mock_ceo_fraud_response: str,
    ) -> None:
        """Test that classification time is recorded in the result."""
        # Arrange
        mock_llm_client.chat_completion = AsyncMock(
            return_value=LLMResponse(
                content=mock_ceo_fraud_response,
                used_fallback=False,
                model_used="gpt-4o",
            )
        )

        # Act
        profiler = ProfilerAgent(client=mock_llm_client)
        result, _ = await profiler.classify(ceo_fraud_email)

        # Assert
        assert result.classification_time_ms >= 0
        assert isinstance(result.classification_time_ms, int)


# -----------------------------------------------------------------------------
# Test: Edge Cases and Error Handling
# -----------------------------------------------------------------------------


class TestClassificationFlowEdgeCases:
    """Test edge cases and error scenarios in the classification flow."""

    @pytest.mark.asyncio
    async def test_empty_email_content_is_handled(
        self,
        mock_llm_client: MagicMock,
        mock_not_phishing_response: str,
    ) -> None:
        """Test classification of empty email content."""
        # Arrange
        mock_llm_client.chat_completion = AsyncMock(
            return_value=LLMResponse(
                content=mock_not_phishing_response,
                used_fallback=False,
                model_used="gpt-4o",
            )
        )

        # Act
        profiler = ProfilerAgent(client=mock_llm_client)
        result, _ = await profiler.classify("")

        # Assert: Should still produce a result
        assert result is not None
        assert result.attack_type is not None

    @pytest.mark.asyncio
    async def test_very_long_email_content(
        self,
        mock_llm_client: MagicMock,
        mock_nigerian_419_response: str,
    ) -> None:
        """Test classification of very long email content."""
        # Arrange
        long_email = "This is a phishing email. " * 1000  # ~27KB of text

        mock_llm_client.chat_completion = AsyncMock(
            return_value=LLMResponse(
                content=mock_nigerian_419_response,
                used_fallback=False,
                model_used="gpt-4o",
            )
        )

        # Act
        profiler = ProfilerAgent(client=mock_llm_client)
        result, _ = await profiler.classify(long_email)

        # Assert
        assert result is not None
        assert result.attack_type == AttackType.NIGERIAN_419

    @pytest.mark.asyncio
    async def test_email_with_special_characters(
        self,
        mock_llm_client: MagicMock,
        mock_ceo_fraud_response: str,
    ) -> None:
        """Test classification of email with special characters."""
        # Arrange
        special_email = """
        Subject: URGENT! $$$ Wire Transfer !!!

        <script>alert('xss')</script>

        Please send money to: bank@evil.com
        Amount: $50,000 (FIFTY THOUSAND USD)

        Regards,
        "The CEO" <ceo@company.com>
        """

        mock_llm_client.chat_completion = AsyncMock(
            return_value=LLMResponse(
                content=mock_ceo_fraud_response,
                used_fallback=False,
                model_used="gpt-4o",
            )
        )

        # Act
        profiler = ProfilerAgent(client=mock_llm_client)
        result, _ = await profiler.classify(special_email)

        # Assert
        assert result is not None
        assert result.attack_type == AttackType.CEO_FRAUD

    @pytest.mark.asyncio
    async def test_classification_with_unicode_content(
        self,
        mock_llm_client: MagicMock,
        mock_nigerian_419_response: str,
    ) -> None:
        """Test classification of email with unicode characters."""
        # Arrange
        unicode_email = """
        Dear Friend,

        I am writing about important matter.
        Please send your details.

        Best regards
        """

        mock_llm_client.chat_completion = AsyncMock(
            return_value=LLMResponse(
                content=mock_nigerian_419_response,
                used_fallback=False,
                model_used="gpt-4o",
            )
        )

        # Act
        profiler = ProfilerAgent(client=mock_llm_client)
        result, _ = await profiler.classify(unicode_email)

        # Assert
        assert result is not None

    @pytest.mark.asyncio
    async def test_llm_response_with_markdown_code_block(
        self,
        mock_llm_client: MagicMock,
    ) -> None:
        """Test handling of LLM response wrapped in markdown code block."""
        # Arrange: LLM sometimes wraps JSON in markdown code blocks
        markdown_response = """```json
{
    "attack_type": "lottery_prize",
    "confidence": 91.0,
    "reasoning": "Email claims user won a lottery they never entered."
}
```"""

        mock_llm_client.chat_completion = AsyncMock(
            return_value=LLMResponse(
                content=markdown_response,
                used_fallback=False,
                model_used="gpt-4o",
            )
        )

        # Act
        profiler = ProfilerAgent(client=mock_llm_client)
        result, _ = await profiler.classify("You've won the lottery!")

        # Assert: Should handle markdown wrapper correctly
        assert result.attack_type == AttackType.LOTTERY_PRIZE
        assert result.confidence == 91.0

    @pytest.mark.asyncio
    async def test_malformed_llm_response_returns_fallback(
        self,
        mock_llm_client: MagicMock,
    ) -> None:
        """Test that malformed LLM response triggers fallback classification."""
        # Arrange: Return invalid JSON
        mock_llm_client.chat_completion = AsyncMock(
            return_value=LLMResponse(
                content="This is not valid JSON at all!",
                used_fallback=False,
                model_used="gpt-4o",
            )
        )

        # Act
        profiler = ProfilerAgent(client=mock_llm_client)
        result, _ = await profiler.classify("Some email content")

        # Assert: Should return fallback classification
        assert result.attack_type == AttackType.NOT_PHISHING
        assert result.confidence == 25.0  # Low confidence fallback
        assert "parsing failure" in result.reasoning.lower()

    @pytest.mark.asyncio
    async def test_session_state_independent_of_classification_order(
        self,
        mock_llm_client: MagicMock,
        mock_nigerian_419_response: str,
        mock_ceo_fraud_response: str,
    ) -> None:
        """Test that multiple sessions are independent."""
        # Arrange
        session1 = SessionState(email_content="Nigerian prince email")
        session2 = SessionState(email_content="CEO fraud email")

        mock_llm_client.chat_completion = AsyncMock(
            side_effect=[
                LLMResponse(
                    content=mock_nigerian_419_response,
                    used_fallback=False,
                    model_used="gpt-4o",
                ),
                LLMResponse(
                    content=mock_ceo_fraud_response,
                    used_fallback=True,
                    model_used="gpt-4o-mini",
                ),
            ]
        )

        profiler = ProfilerAgent(client=mock_llm_client)

        # Act
        result1, fallback1 = await profiler.classify(session1.email_content)
        session1.classification_result = result1
        session1.used_fallback_model = fallback1

        result2, fallback2 = await profiler.classify(session2.email_content)
        session2.classification_result = result2
        session2.used_fallback_model = fallback2

        # Assert: Sessions should be independent
        assert session1.classification_result.attack_type == AttackType.NIGERIAN_419
        assert session2.classification_result.attack_type == AttackType.CEO_FRAUD
        assert session1.used_fallback_model is False
        assert session2.used_fallback_model is True


# -----------------------------------------------------------------------------
# Test: LLM Client Call Verification
# -----------------------------------------------------------------------------


class TestLLMClientInteraction:
    """Test that the profiler correctly interacts with the LLM client."""

    @pytest.mark.asyncio
    async def test_llm_client_called_with_correct_parameters(
        self,
        mock_llm_client: MagicMock,
        nigerian_419_email: str,
        mock_nigerian_419_response: str,
    ) -> None:
        """Test that LLM client is called with expected parameters."""
        # Arrange
        mock_llm_client.chat_completion = AsyncMock(
            return_value=LLMResponse(
                content=mock_nigerian_419_response,
                used_fallback=False,
                model_used="gpt-4o",
            )
        )

        # Act
        profiler = ProfilerAgent(client=mock_llm_client)
        await profiler.classify(nigerian_419_email)

        # Assert
        mock_llm_client.chat_completion.assert_called_once()
        call_kwargs = mock_llm_client.chat_completion.call_args.kwargs

        assert "messages" in call_kwargs
        assert "temperature" in call_kwargs
        assert "max_tokens" in call_kwargs
        assert call_kwargs["temperature"] == 0.2  # Low temp for classification
        assert call_kwargs["max_tokens"] == 200

    @pytest.mark.asyncio
    async def test_llm_messages_contain_system_and_user_prompts(
        self,
        mock_llm_client: MagicMock,
        nigerian_419_email: str,
        mock_nigerian_419_response: str,
    ) -> None:
        """Test that LLM is called with system and user messages."""
        # Arrange
        mock_llm_client.chat_completion = AsyncMock(
            return_value=LLMResponse(
                content=mock_nigerian_419_response,
                used_fallback=False,
                model_used="gpt-4o",
            )
        )

        # Act
        profiler = ProfilerAgent(client=mock_llm_client)
        await profiler.classify(nigerian_419_email)

        # Assert
        call_kwargs = mock_llm_client.chat_completion.call_args.kwargs
        messages = call_kwargs["messages"]

        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert nigerian_419_email in messages[1]["content"]

    @pytest.mark.asyncio
    async def test_llm_client_only_called_once_on_success(
        self,
        mock_llm_client: MagicMock,
        nigerian_419_email: str,
        mock_nigerian_419_response: str,
    ) -> None:
        """Test that LLM is called exactly once when response is valid."""
        # Arrange
        mock_llm_client.chat_completion = AsyncMock(
            return_value=LLMResponse(
                content=mock_nigerian_419_response,
                used_fallback=False,
                model_used="gpt-4o",
            )
        )

        # Act
        profiler = ProfilerAgent(client=mock_llm_client)
        await profiler.classify(nigerian_419_email)

        # Assert
        assert mock_llm_client.chat_completion.call_count == 1


# -----------------------------------------------------------------------------
# Test: NOT_PHISHING Flow (US-003)
# -----------------------------------------------------------------------------


class TestNotPhishingFlow:
    """Integration tests for the NOT_PHISHING classification flow (US-003).

    These tests verify the complete behavior when an email is classified as
    NOT_PHISHING, including:
    - The is_phishing property returns False
    - The attack_type is AttackType.NOT_PHISHING
    - Session state handles force_continue flag correctly
    - Stage transitions work with force_continue
    """

    @pytest.mark.asyncio
    async def test_not_phishing_classification_has_correct_attack_type(
        self,
        mock_llm_client: MagicMock,
        legitimate_email: str,
        mock_not_phishing_response: str,
    ) -> None:
        """Test that NOT_PHISHING emails have attack_type == AttackType.NOT_PHISHING."""
        # Arrange
        session = create_initial_session_state()
        session.email_content = legitimate_email

        mock_llm_client.chat_completion = AsyncMock(
            return_value=LLMResponse(
                content=mock_not_phishing_response,
                used_fallback=False,
                model_used="gpt-4o",
            )
        )

        # Act
        profiler = ProfilerAgent(client=mock_llm_client)
        result, used_fallback = await profiler.classify(session.email_content)

        session.classification_result = result
        session.used_fallback_model = used_fallback
        session.stage = SessionStage.CLASSIFIED

        # Assert
        assert session.classification_result.attack_type == AttackType.NOT_PHISHING

    @pytest.mark.asyncio
    async def test_not_phishing_classification_is_phishing_returns_false(
        self,
        mock_llm_client: MagicMock,
        legitimate_email: str,
        mock_not_phishing_response: str,
    ) -> None:
        """Test that NOT_PHISHING classification has is_phishing property = False."""
        # Arrange
        session = create_initial_session_state()
        session.email_content = legitimate_email

        mock_llm_client.chat_completion = AsyncMock(
            return_value=LLMResponse(
                content=mock_not_phishing_response,
                used_fallback=False,
                model_used="gpt-4o",
            )
        )

        # Act
        profiler = ProfilerAgent(client=mock_llm_client)
        result, _ = await profiler.classify(session.email_content)

        session.classification_result = result
        session.stage = SessionStage.CLASSIFIED

        # Assert
        assert session.classification_result.is_phishing is False
        assert session.classification_result.attack_type == AttackType.NOT_PHISHING


# -----------------------------------------------------------------------------
# Test: Force Continue Flow (US-003)
# -----------------------------------------------------------------------------


class TestForceContinueFlow:
    """Integration tests for the force_continue flow (US-003).

    These tests verify that:
    - SessionState starts with force_continue = False
    - Setting force_continue = True changes the session state correctly
    - Stage can transition from CLASSIFIED to CONVERSATION when force_continue is True
    """

    @pytest.mark.asyncio
    async def test_session_starts_with_force_continue_false(self) -> None:
        """Test that new session state has force_continue = False."""
        session = create_initial_session_state()

        assert session.force_continue is False

    @pytest.mark.asyncio
    async def test_force_continue_can_be_set_to_true(self) -> None:
        """Test that force_continue can be changed to True."""
        session = create_initial_session_state()
        assert session.force_continue is False

        session.force_continue = True

        assert session.force_continue is True

    @pytest.mark.asyncio
    async def test_force_continue_enables_classified_to_conversation_transition(
        self,
        mock_llm_client: MagicMock,
        legitimate_email: str,
        mock_not_phishing_response: str,
    ) -> None:
        """Test CLASSIFIED to CONVERSATION transition when force_continue is True.

        This simulates the user clicking "Continue anyway" for a non-phishing email.
        """
        # Arrange: Create session and classify as NOT_PHISHING
        session = create_initial_session_state()
        session.email_content = legitimate_email

        mock_llm_client.chat_completion = AsyncMock(
            return_value=LLMResponse(
                content=mock_not_phishing_response,
                used_fallback=False,
                model_used="gpt-4o",
            )
        )

        profiler = ProfilerAgent(client=mock_llm_client)
        result, _ = await profiler.classify(session.email_content)

        session.classification_result = result
        session.stage = SessionStage.CLASSIFIED

        # Verify NOT_PHISHING classification
        assert session.classification_result.attack_type == AttackType.NOT_PHISHING
        assert session.classification_result.is_phishing is False
        assert session.stage == SessionStage.CLASSIFIED

        # Act: User clicks "Continue anyway"
        session.force_continue = True

        # Assert: force_continue is True and can transition to CONVERSATION
        assert session.force_continue is True

        # Transition to CONVERSATION stage
        session.stage = SessionStage.CONVERSATION

        assert session.stage == SessionStage.CONVERSATION
        assert session.force_continue is True

    @pytest.mark.asyncio
    async def test_force_continue_remains_true_across_stage_transitions(
        self,
        mock_llm_client: MagicMock,
        legitimate_email: str,
        mock_not_phishing_response: str,
    ) -> None:
        """Test that force_continue remains True across stage transitions."""
        # Arrange
        session = create_initial_session_state()
        session.email_content = legitimate_email

        mock_llm_client.chat_completion = AsyncMock(
            return_value=LLMResponse(
                content=mock_not_phishing_response,
                used_fallback=False,
                model_used="gpt-4o",
            )
        )

        profiler = ProfilerAgent(client=mock_llm_client)
        result, _ = await profiler.classify(session.email_content)

        session.classification_result = result
        session.stage = SessionStage.CLASSIFIED

        # Act: Set force_continue and transition through stages
        session.force_continue = True
        session.stage = SessionStage.CONVERSATION

        # Assert: force_continue persists
        assert session.force_continue is True
        assert session.stage == SessionStage.CONVERSATION

        # Transition to SUMMARY stage
        session.stage = SessionStage.SUMMARY

        # Assert: force_continue still persists
        assert session.force_continue is True
        assert session.stage == SessionStage.SUMMARY

    @pytest.mark.asyncio
    async def test_phishing_email_does_not_require_force_continue(
        self,
        mock_llm_client: MagicMock,
        nigerian_419_email: str,
        mock_nigerian_419_response: str,
    ) -> None:
        """Test that phishing emails can proceed without force_continue."""
        # Arrange
        session = create_initial_session_state()
        session.email_content = nigerian_419_email

        mock_llm_client.chat_completion = AsyncMock(
            return_value=LLMResponse(
                content=mock_nigerian_419_response,
                used_fallback=False,
                model_used="gpt-4o",
            )
        )

        profiler = ProfilerAgent(client=mock_llm_client)
        result, _ = await profiler.classify(session.email_content)

        session.classification_result = result
        session.stage = SessionStage.CLASSIFIED

        # Assert: Phishing classification
        assert session.classification_result.is_phishing is True
        assert session.force_continue is False

        # Act: Can transition to CONVERSATION without force_continue
        session.stage = SessionStage.CONVERSATION

        assert session.stage == SessionStage.CONVERSATION
        assert session.force_continue is False


# -----------------------------------------------------------------------------
# Test: Reset Flow (US-003)
# -----------------------------------------------------------------------------


class TestResetFlow:
    """Integration tests for the session reset flow (US-003).

    These tests verify that:
    - Creating a new session state returns to initial values
    - force_continue is reset to False on new session
    - All other fields are properly reset
    """

    @pytest.mark.asyncio
    async def test_new_session_resets_force_continue_to_false(self) -> None:
        """Test that creating a new session resets force_continue to False."""
        # Arrange: Create a session with force_continue = True
        old_session = SessionState(force_continue=True)
        old_session.stage = SessionStage.CONVERSATION

        assert old_session.force_continue is True
        assert old_session.stage == SessionStage.CONVERSATION

        # Act: Create a new session (simulating reset)
        new_session = create_initial_session_state()

        # Assert: New session has initial values
        assert new_session.force_continue is False
        assert new_session.stage == SessionStage.INPUT
        assert new_session.email_content is None
        assert new_session.classification_result is None
        assert new_session.used_fallback_model is False

    @pytest.mark.asyncio
    async def test_new_session_is_independent_of_old_session(
        self,
        mock_llm_client: MagicMock,
        legitimate_email: str,
        mock_not_phishing_response: str,
    ) -> None:
        """Test that a new session is completely independent of an old session."""
        # Arrange: Create and configure an old session
        mock_llm_client.chat_completion = AsyncMock(
            return_value=LLMResponse(
                content=mock_not_phishing_response,
                used_fallback=False,
                model_used="gpt-4o",
            )
        )

        old_session = create_initial_session_state()
        old_session.email_content = legitimate_email

        profiler = ProfilerAgent(client=mock_llm_client)
        result, _ = await profiler.classify(old_session.email_content)

        old_session.classification_result = result
        old_session.stage = SessionStage.CLASSIFIED
        old_session.force_continue = True
        old_session.used_fallback_model = True

        # Verify old session state
        assert old_session.force_continue is True
        assert old_session.stage == SessionStage.CLASSIFIED
        assert old_session.classification_result is not None
        assert old_session.used_fallback_model is True

        # Act: Create a completely new session
        new_session = create_initial_session_state()

        # Assert: New session is in initial state
        assert new_session.force_continue is False
        assert new_session.stage == SessionStage.INPUT
        assert new_session.email_content is None
        assert new_session.classification_result is None
        assert new_session.used_fallback_model is False
        assert new_session.is_input_stage is True
        assert new_session.is_classified is False

        # Assert: Old session is unchanged
        assert old_session.force_continue is True
        assert old_session.stage == SessionStage.CLASSIFIED

    @pytest.mark.asyncio
    async def test_multiple_resets_always_return_initial_values(self) -> None:
        """Test that multiple session creates always return consistent values."""
        sessions = [create_initial_session_state() for _ in range(5)]

        for i, session in enumerate(sessions):
            assert session.force_continue is False, (
                f"Session {i} force_continue should be False"
            )
            assert session.stage == SessionStage.INPUT, (
                f"Session {i} stage should be INPUT"
            )
            assert session.email_content is None, (
                f"Session {i} email_content should be None"
            )
            assert session.classification_result is None, (
                f"Session {i} classification_result should be None"
            )
            assert session.used_fallback_model is False, (
                f"Session {i} used_fallback_model should be False"
            )
            assert session.is_input_stage is True, (
                f"Session {i} is_input_stage should be True"
            )
            assert session.is_classified is False, (
                f"Session {i} is_classified should be False"
            )

    @pytest.mark.asyncio
    async def test_reset_after_full_session_cycle(
        self,
        mock_llm_client: MagicMock,
        nigerian_419_email: str,
        mock_nigerian_419_response: str,
    ) -> None:
        """Test reset after completing a full session cycle."""
        # Arrange: Complete a full session cycle
        mock_llm_client.chat_completion = AsyncMock(
            return_value=LLMResponse(
                content=mock_nigerian_419_response,
                used_fallback=True,
                model_used="gpt-4o-mini",
            )
        )

        old_session = create_initial_session_state()
        old_session.email_content = nigerian_419_email

        profiler = ProfilerAgent(client=mock_llm_client)
        result, fallback = await profiler.classify(old_session.email_content)

        old_session.classification_result = result
        old_session.used_fallback_model = fallback
        old_session.stage = SessionStage.CLASSIFIED
        old_session.stage = SessionStage.CONVERSATION
        old_session.stage = SessionStage.SUMMARY

        # Verify old session reached final state
        assert old_session.stage == SessionStage.SUMMARY
        assert old_session.used_fallback_model is True
        assert old_session.classification_result.attack_type == AttackType.NIGERIAN_419

        # Act: Create new session (reset)
        new_session = create_initial_session_state()

        # Assert: New session is clean
        assert new_session.stage == SessionStage.INPUT
        assert new_session.force_continue is False
        assert new_session.email_content is None
        assert new_session.classification_result is None
        assert new_session.used_fallback_model is False
