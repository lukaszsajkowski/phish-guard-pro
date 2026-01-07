"""Unit tests for the UnmaskingDetector module."""

import pytest

from phishguard.safety.unmasking_detector import (
    UnmaskingDetector,
    UnmaskingResult,
    detect_unmasking,
)


class TestUnmaskingResult:
    """Tests for UnmaskingResult dataclass."""

    def test_empty_result(self) -> None:
        """Test creating an empty result."""
        result = UnmaskingResult(is_unmasked=False)
        assert result.is_unmasked is False
        assert result.matched_phrases == []
        assert result.confidence == 0.0
        assert result.phrase_count == 0

    def test_unmasked_result(self) -> None:
        """Test creating an unmasked result."""
        result = UnmaskingResult(
            is_unmasked=True,
            matched_phrases=["you're a bot", "stop messaging me"],
            confidence=0.85,
        )
        assert result.is_unmasked is True
        assert len(result.matched_phrases) == 2
        assert result.confidence == 0.85
        assert result.phrase_count == 2


class TestUnmaskingDetector:
    """Tests for UnmaskingDetector class."""

    @pytest.fixture
    def detector(self) -> UnmaskingDetector:
        """Create detector instance."""
        return UnmaskingDetector()

    # -------------------------
    # High confidence patterns
    # -------------------------

    @pytest.mark.parametrize(
        "message",
        [
            "you're a bot",
            "You are a bot",
            "This is a bot",
            "I know you're a bot",
            "you're a robot",
            "this is artificial",
            "you are automated",
        ],
    )
    def test_direct_bot_accusations(
        self, detector: UnmaskingDetector, message: str
    ) -> None:
        """Test detection of direct bot accusations (high confidence)."""
        result = detector.detect(message)
        assert result.is_unmasked is True
        assert result.confidence >= 0.3
        assert len(result.matched_phrases) >= 1

    @pytest.mark.parametrize(
        "message",
        [
            "this is a scam",
            "you're a scammer",
            "this is fake",
            "I know this is fake",
            "this is fraud",
        ],
    )
    def test_scam_fake_accusations(
        self, detector: UnmaskingDetector, message: str
    ) -> None:
        """Test detection of scam/fake accusations."""
        result = detector.detect(message)
        assert result.is_unmasked is True
        assert len(result.matched_phrases) >= 1

    @pytest.mark.parametrize(
        "message",
        [
            "I'm done with you",
            "I am done talking to you",
            "We're finished with this",
            "stop messaging me",
            "stop contacting me",
            "don't email me again",
            "do not contact me anymore",
        ],
    )
    def test_conversation_termination(
        self, detector: UnmaskingDetector, message: str
    ) -> None:
        """Test detection of conversation termination phrases."""
        result = detector.detect(message)
        assert result.is_unmasked is True

    # -------------------------
    # Medium confidence patterns
    # -------------------------

    @pytest.mark.parametrize(
        "message",
        [
            "you're wasting my time",
            "stop wasting my time",
            "this is wasting my time",
        ],
    )
    def test_time_wasting_accusations(
        self, detector: UnmaskingDetector, message: str
    ) -> None:
        """Test detection of time wasting accusations."""
        result = detector.detect(message)
        assert result.is_unmasked is True

    @pytest.mark.parametrize(
        "message",
        [
            "I'll report you",
            "I'm going to block you",
            "I will flag this",
            "reported you to the police",
            "I've blocked your number",
        ],
    )
    def test_report_block_threats(
        self, detector: UnmaskingDetector, message: str
    ) -> None:
        """Test detection of report/block threats."""
        result = detector.detect(message)
        assert result.is_unmasked is True

    # -------------------------
    # Non-matching messages
    # -------------------------

    @pytest.mark.parametrize(
        "message",
        [
            "Hello, how are you?",
            "I'm interested in your offer",
            "Please send more information",
            "What is the next step?",
            "Thank you for the email",
            "I will consider this",
            "",
            "   ",
        ],
    )
    def test_normal_messages_not_detected(
        self, detector: UnmaskingDetector, message: str
    ) -> None:
        """Test that normal messages are not detected as unmasking."""
        result = detector.detect(message)
        assert result.is_unmasked is False

    # -------------------------
    # Edge cases
    # -------------------------

    def test_empty_message(self, detector: UnmaskingDetector) -> None:
        """Test handling of empty message."""
        result = detector.detect("")
        assert result.is_unmasked is False
        assert result.matched_phrases == []
        assert result.confidence == 0.0

    def test_whitespace_only(self, detector: UnmaskingDetector) -> None:
        """Test handling of whitespace-only message."""
        result = detector.detect("   \n\t  ")
        assert result.is_unmasked is False

    def test_multiple_patterns(self, detector: UnmaskingDetector) -> None:
        """Test message matching multiple patterns."""
        message = "You're a bot! Stop messaging me! I'm going to report you!"
        result = detector.detect(message)
        assert result.is_unmasked is True
        assert len(result.matched_phrases) >= 2
        assert result.confidence > 0.5  # Higher confidence for multiple matches

    def test_case_insensitivity(self, detector: UnmaskingDetector) -> None:
        """Test that detection is case-insensitive."""
        result1 = detector.detect("YOU'RE A BOT")
        result2 = detector.detect("you're a bot")
        assert result1.is_unmasked is True
        assert result2.is_unmasked is True


class TestDetectUnmaskingFunction:
    """Tests for the convenience function."""

    def test_convenience_function(self) -> None:
        """Test that convenience function works correctly."""
        result = detect_unmasking("you're a bot")
        assert isinstance(result, UnmaskingResult)
        assert result.is_unmasked is True

    def test_convenience_function_no_match(self) -> None:
        """Test convenience function with non-matching message."""
        result = detect_unmasking("Hello there")
        assert isinstance(result, UnmaskingResult)
        assert result.is_unmasked is False
