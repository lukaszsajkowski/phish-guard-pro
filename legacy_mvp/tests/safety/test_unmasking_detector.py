"""Comprehensive unit tests for the UnmaskingDetector.

These tests verify that the UnmaskingDetector correctly:
1. Detects various unmasking phrases indicating the scammer realized it's a bot
2. Returns appropriate confidence levels
3. Handles edge cases gracefully
4. Avoids false positives on legitimate messages

Test Categories:
- Direct bot accusations
- Time wasting accusations
- Conversation termination signals
- Report/block threats
- Edge cases and false positives
- UnmaskingResult model

Requirements: FR-028, FR-029, US-014
"""

import pytest

from phishguard.safety.unmasking_detector import (
    UnmaskingDetector,
    UnmaskingResult,
    detect_unmasking,
)

# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def detector() -> UnmaskingDetector:
    """Create a UnmaskingDetector instance for testing."""
    return UnmaskingDetector()


# -----------------------------------------------------------------------------
# Test Classes
# -----------------------------------------------------------------------------


class TestUnmaskingResultModel:
    """Tests for the UnmaskingResult dataclass."""

    def test_result_with_no_unmasking(self) -> None:
        """UnmaskingResult should represent no unmasking detected."""
        result = UnmaskingResult(is_unmasked=False)
        assert result.is_unmasked is False
        assert result.matched_phrases == []
        assert result.confidence == 0.0
        assert result.phrase_count == 0

    def test_result_with_unmasking_detected(self) -> None:
        """UnmaskingResult should store matched phrases."""
        result = UnmaskingResult(
            is_unmasked=True,
            matched_phrases=["you're a bot", "stop wasting my time"],
            confidence=0.85,
        )
        assert result.is_unmasked is True
        assert len(result.matched_phrases) == 2
        assert result.confidence == 0.85
        assert result.phrase_count == 2

    def test_result_is_frozen(self) -> None:
        """UnmaskingResult should be immutable."""
        result = UnmaskingResult(is_unmasked=True, matched_phrases=["test"])
        with pytest.raises(AttributeError):
            result.is_unmasked = False  # type: ignore


class TestUnmaskingDetectorDirectBotAccusations:
    """Tests for detecting direct bot accusations."""

    @pytest.mark.parametrize(
        "message",
        [
            "You're a bot!",
            "you are a bot",
            "this is a bot",
            "You're a robot",
            "this is automated",
            "You're AI",
            "You're artificial",
        ],
        ids=[
            "youre_bot",
            "you_are_bot",
            "this_is_bot",
            "youre_robot",
            "automated",
            "you_are_ai",
            "artificial",
        ],
    )
    def test_detects_direct_bot_accusations(
        self, detector: UnmaskingDetector, message: str
    ) -> None:
        """Detector should detect direct bot accusations."""
        result = detector.detect(message)
        assert result.is_unmasked is True
        assert len(result.matched_phrases) >= 1

    @pytest.mark.parametrize(
        "message",
        [
            "You're a scam",
            "this is fake",
            "You're fraud",
            "This is just a scam",
        ],
        ids=["youre_scam", "this_fake", "youre_fraud", "just_a_scam"],
    )
    def test_detects_scam_fake_accusations(
        self, detector: UnmaskingDetector, message: str
    ) -> None:
        """Detector should detect scam/fake accusations."""
        result = detector.detect(message)
        assert result.is_unmasked is True
        assert len(result.matched_phrases) >= 1

    def test_detects_explicit_unmasking(self, detector: UnmaskingDetector) -> None:
        """Detector should detect explicit 'I know' statements."""
        result = detector.detect("I know you're a bot")
        assert result.is_unmasked is True

        result = detector.detect("I know this is fake")
        assert result.is_unmasked is True

        result = detector.detect("I know you are automated")
        assert result.is_unmasked is True


class TestUnmaskingDetectorConversationTermination:
    """Tests for detecting conversation termination signals."""

    @pytest.mark.parametrize(
        "message",
        [
            "I'm done with you",
            "I am done talking",
            "We're finished with this",
            "I'm done with this conversation",
        ],
        ids=["im_done_you", "i_am_done_talking", "were_finished", "done_conversation"],
    )
    def test_detects_done_finished_phrases(
        self, detector: UnmaskingDetector, message: str
    ) -> None:
        """Detector should detect 'done/finished' termination phrases."""
        result = detector.detect(message)
        assert result.is_unmasked is True

    @pytest.mark.parametrize(
        "message",
        [
            "Stop messaging me",
            "Stop contacting me",
            "Stop emailing me",
            "Stop texting me",
            "Stop bothering me",
        ],
        ids=[
            "stop_messaging",
            "stop_contacting",
            "stop_emailing",
            "stop_texting",
            "stop_bothering",
        ],
    )
    def test_detects_stop_contact_demands(
        self, detector: UnmaskingDetector, message: str
    ) -> None:
        """Detector should detect 'stop contacting me' demands."""
        result = detector.detect(message)
        assert result.is_unmasked is True

    @pytest.mark.parametrize(
        "message",
        [
            "Don't contact me again",
            "Do not message me anymore",
            "Don't email me again",
        ],
        ids=["dont_contact_again", "do_not_message_anymore", "dont_email_again"],
    )
    def test_detects_no_further_contact_demands(
        self, detector: UnmaskingDetector, message: str
    ) -> None:
        """Detector should detect 'don't contact me again' demands."""
        result = detector.detect(message)
        assert result.is_unmasked is True


class TestUnmaskingDetectorTimeWasting:
    """Tests for detecting time wasting accusations."""

    @pytest.mark.parametrize(
        "message",
        [
            "You're wasting my time",
            "You are just wasting time",
            "This is wasting my time",
            "Stop wasting my time",
            "Stop playing around",
            "Stop messing with me",
        ],
        ids=[
            "youre_wasting_time",
            "you_are_wasting",
            "this_wasting",
            "stop_wasting_time",
            "stop_playing",
            "stop_messing",
        ],
    )
    def test_detects_time_wasting_accusations(
        self, detector: UnmaskingDetector, message: str
    ) -> None:
        """Detector should detect time wasting accusations."""
        result = detector.detect(message)
        assert result.is_unmasked is True


class TestUnmaskingDetectorReportThreats:
    """Tests for detecting report/block threats."""

    @pytest.mark.parametrize(
        "message",
        [
            "I'll report you",
            "I will block you",
            "Going to flag this",
            "I reported you",
            "I blocked your number",
            "I flagged this email",
        ],
        ids=[
            "ill_report",
            "i_will_block",
            "going_to_flag",
            "i_reported",
            "i_blocked",
            "i_flagged",
        ],
    )
    def test_detects_report_block_threats(
        self, detector: UnmaskingDetector, message: str
    ) -> None:
        """Detector should detect report/block threats."""
        result = detector.detect(message)
        assert result.is_unmasked is True


class TestUnmaskingDetectorSuspicionPhrases:
    """Tests for detecting suspicion phrases."""

    @pytest.mark.parametrize(
        "message",
        [
            "I think you're a scam",
            "I believe this is fake",
            "I suspect you are a bot",
        ],
        ids=["i_think_scam", "i_believe_fake", "i_suspect_bot"],
    )
    def test_detects_suspicion_phrases(
        self, detector: UnmaskingDetector, message: str
    ) -> None:
        """Detector should detect suspicion expressions."""
        result = detector.detect(message)
        assert result.is_unmasked is True


class TestUnmaskingDetectorEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_message_not_unmasked(self, detector: UnmaskingDetector) -> None:
        """Empty message should not trigger unmasking."""
        result = detector.detect("")
        assert result.is_unmasked is False
        assert result.matched_phrases == []

    def test_whitespace_only_not_unmasked(self, detector: UnmaskingDetector) -> None:
        """Whitespace-only message should not trigger unmasking."""
        result = detector.detect("   \n\t   ")
        assert result.is_unmasked is False

    def test_case_insensitive_detection(self, detector: UnmaskingDetector) -> None:
        """Detection should be case insensitive."""
        result_lower = detector.detect("you're a bot")
        result_upper = detector.detect("YOU'RE A BOT")
        result_mixed = detector.detect("You're A Bot")

        assert result_lower.is_unmasked is True
        assert result_upper.is_unmasked is True
        assert result_mixed.is_unmasked is True

    def test_multiple_patterns_in_one_message(
        self, detector: UnmaskingDetector
    ) -> None:
        """Multiple unmasking patterns should all be detected."""
        message = "You're a bot! Stop messaging me! I'm done with this!"
        result = detector.detect(message)

        assert result.is_unmasked is True
        assert len(result.matched_phrases) >= 2
        # Higher confidence for multiple matches
        assert result.confidence > 0.5

    def test_long_message_with_unmasking(self, detector: UnmaskingDetector) -> None:
        """Long message containing unmasking phrase should be detected."""
        message = (
            "I have been thinking about this for a while and after careful "
            "consideration of all the evidence, I have come to the conclusion "
            "that you are just a bot and I am done talking to you."
        )
        result = detector.detect(message)
        assert result.is_unmasked is True


class TestUnmaskingDetectorFalsePositives:
    """Tests to ensure detector avoids false positives."""

    @pytest.mark.parametrize(
        "message",
        [
            "Hello, how are you today?",
            "Please send the money to this account",
            "I will contact you tomorrow",
            "The bot at work helped me today",
            "I'm done with dinner",
            "Stop the car please",
            "I reported to work early",
            "My friend blocked traffic",
        ],
        ids=[
            "normal_greeting",
            "scam_request",
            "future_contact",
            "unrelated_bot_mention",
            "done_with_dinner",
            "stop_the_car",
            "reported_to_work",
            "blocked_traffic",
        ],
    )
    def test_does_not_detect_false_positives(
        self, detector: UnmaskingDetector, message: str
    ) -> None:
        """Detector should not flag normal messages as unmasking."""
        result = detector.detect(message)
        assert result.is_unmasked is False

    def test_legitimate_email_not_flagged(self, detector: UnmaskingDetector) -> None:
        """Legitimate-looking email should not be flagged."""
        message = """
        Thank you for your interest in our service. I understand you have
        questions about the process. Please provide the following documents
        and I will proceed with your application. Contact me if you need
        any assistance.
        """
        result = detector.detect(message)
        assert result.is_unmasked is False


class TestUnmaskingDetectorConfidence:
    """Tests for confidence calculation."""

    def test_high_confidence_for_strong_pattern(
        self, detector: UnmaskingDetector
    ) -> None:
        """Strong patterns should have higher confidence."""
        result = detector.detect("I know you're a bot")
        assert result.confidence >= 0.4

    def test_multiple_patterns_increase_confidence(
        self, detector: UnmaskingDetector
    ) -> None:
        """Multiple matching patterns should increase confidence."""
        result_single = detector.detect("You're a bot")
        result_multiple = detector.detect(
            "You're a bot! Stop messaging me! I'm done!"
        )

        assert result_multiple.confidence >= result_single.confidence


class TestConvenienceFunction:
    """Tests for the module-level convenience function."""

    def test_detect_unmasking_function(self) -> None:
        """detect_unmasking() convenience function should work."""
        result = detect_unmasking("You're a bot!")
        assert result.is_unmasked is True
        assert isinstance(result, UnmaskingResult)

    def test_detect_unmasking_returns_not_unmasked_for_normal(self) -> None:
        """detect_unmasking() should return not unmasked for normal messages."""
        result = detect_unmasking("Hello, how are you?")
        assert result.is_unmasked is False


class TestUnmaskingDetectorProfaneDismissal:
    """Tests for profane dismissal detection."""

    @pytest.mark.parametrize(
        "message",
        [
            "f*** off",
            "screw you",
            "f*ck this",
        ],
        ids=["f_off", "screw_you", "f_this"],
    )
    def test_detects_profane_dismissal(
        self, detector: UnmaskingDetector, message: str
    ) -> None:
        """Detector should detect profane dismissals."""
        result = detector.detect(message)
        assert result.is_unmasked is True
