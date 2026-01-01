"""Unit tests for conversation models.

These tests verify that the conversation Pydantic models work correctly:
1. ConversationMessage creation and properties
2. ResponseGenerationResult creation and properties
3. MessageSender enum values
"""

from datetime import UTC, datetime

import pytest

from phishguard.models import (
    AgentThinking,
    ConversationMessage,
    MessageSender,
    ResponseGenerationResult,
)


class TestMessageSenderEnum:
    """Tests for MessageSender enum."""

    def test_bot_value(self) -> None:
        """BOT should have value 'bot'."""
        assert MessageSender.BOT.value == "bot"

    def test_scammer_value(self) -> None:
        """SCAMMER should have value 'scammer'."""
        assert MessageSender.SCAMMER.value == "scammer"


class TestConversationMessage:
    """Tests for ConversationMessage model."""

    def test_create_bot_message(self) -> None:
        """Should create a valid bot message."""
        msg = ConversationMessage(
            sender=MessageSender.BOT,
            content="Hello, this is a test response.",
            turn_number=1,
        )

        assert msg.sender == MessageSender.BOT
        assert msg.content == "Hello, this is a test response."
        assert msg.turn_number == 1

    def test_create_scammer_message(self) -> None:
        """Should create a valid scammer message."""
        msg = ConversationMessage(
            sender=MessageSender.SCAMMER,
            content="Dear friend, I have money for you.",
            turn_number=1,
        )

        assert msg.sender == MessageSender.SCAMMER
        assert msg.content == "Dear friend, I have money for you."

    def test_auto_generates_timestamp(self) -> None:
        """Should auto-generate timestamp if not provided."""
        msg = ConversationMessage(
            sender=MessageSender.BOT,
            content="Test",
            turn_number=1,
        )

        assert msg.timestamp is not None
        assert isinstance(msg.timestamp, datetime)

    def test_custom_timestamp(self) -> None:
        """Should accept custom timestamp."""
        custom_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)
        msg = ConversationMessage(
            sender=MessageSender.BOT,
            content="Test",
            turn_number=1,
            timestamp=custom_time,
        )

        assert msg.timestamp == custom_time

    def test_is_bot_message_property(self) -> None:
        """is_bot_message should return True for bot messages."""
        bot_msg = ConversationMessage(
            sender=MessageSender.BOT,
            content="Test",
            turn_number=1,
        )
        scammer_msg = ConversationMessage(
            sender=MessageSender.SCAMMER,
            content="Test",
            turn_number=1,
        )

        assert bot_msg.is_bot_message is True
        assert scammer_msg.is_bot_message is False

    def test_is_scammer_message_property(self) -> None:
        """is_scammer_message should return True for scammer messages."""
        bot_msg = ConversationMessage(
            sender=MessageSender.BOT,
            content="Test",
            turn_number=1,
        )
        scammer_msg = ConversationMessage(
            sender=MessageSender.SCAMMER,
            content="Test",
            turn_number=1,
        )

        assert bot_msg.is_scammer_message is False
        assert scammer_msg.is_scammer_message is True

    def test_message_is_frozen(self) -> None:
        """ConversationMessage should be immutable."""
        msg = ConversationMessage(
            sender=MessageSender.BOT,
            content="Test",
            turn_number=1,
        )

        with pytest.raises((TypeError, ValueError)):
            msg.content = "Modified"

    def test_turn_number_validation(self) -> None:
        """turn_number must be >= 1."""
        with pytest.raises(ValueError):
            ConversationMessage(
                sender=MessageSender.BOT,
                content="Test",
                turn_number=0,
            )

    def test_content_min_length_validation(self) -> None:
        """content must have at least 1 character."""
        with pytest.raises(ValueError):
            ConversationMessage(
                sender=MessageSender.BOT,
                content="",
                turn_number=1,
            )


class TestResponseGenerationResult:
    """Tests for ResponseGenerationResult model."""

    def test_create_result(self) -> None:
        """Should create a valid result."""
        result = ResponseGenerationResult(
            content="Generated response text",
            generation_time_ms=2500,
            safety_validated=True,
            regeneration_count=0,
            used_fallback_model=False,
        )

        assert result.content == "Generated response text"
        assert result.generation_time_ms == 2500
        assert result.safety_validated is True
        assert result.regeneration_count == 0
        assert result.used_fallback_model is False

    def test_generation_time_seconds_property(self) -> None:
        """generation_time_seconds should convert ms to seconds."""
        result = ResponseGenerationResult(
            content="Test",
            generation_time_ms=3500,
        )

        assert result.generation_time_seconds == 3.5

    def test_generation_time_seconds_zero(self) -> None:
        """generation_time_seconds should handle 0ms."""
        result = ResponseGenerationResult(
            content="Test",
            generation_time_ms=0,
        )

        assert result.generation_time_seconds == 0.0

    def test_was_regenerated_false(self) -> None:
        """was_regenerated should be False when regeneration_count is 0."""
        result = ResponseGenerationResult(
            content="Test",
            generation_time_ms=1000,
            regeneration_count=0,
        )

        assert result.was_regenerated is False

    def test_was_regenerated_true(self) -> None:
        """was_regenerated should be True when regeneration_count > 0."""
        result = ResponseGenerationResult(
            content="Test",
            generation_time_ms=1000,
            regeneration_count=2,
        )

        assert result.was_regenerated is True

    def test_default_values(self) -> None:
        """Should have sensible defaults."""
        result = ResponseGenerationResult(
            content="Test",
            generation_time_ms=1000,
        )

        assert result.safety_validated is True
        assert result.regeneration_count == 0
        assert result.used_fallback_model is False

    def test_result_is_frozen(self) -> None:
        """ResponseGenerationResult should be immutable."""
        result = ResponseGenerationResult(
            content="Test",
            generation_time_ms=1000,
        )

        with pytest.raises((TypeError, ValueError)):
            result.content = "Modified"

    def test_content_min_length_validation(self) -> None:
        """content must have at least 1 character."""
        with pytest.raises(ValueError):
            ResponseGenerationResult(
                content="",
                generation_time_ms=1000,
            )

    def test_generation_time_non_negative(self) -> None:
        """generation_time_ms must be >= 0."""
        with pytest.raises(ValueError):
            ResponseGenerationResult(
                content="Test",
                generation_time_ms=-100,
            )

    def test_regeneration_count_non_negative(self) -> None:
        """regeneration_count must be >= 0."""
        with pytest.raises(ValueError):
            ResponseGenerationResult(
                content="Test",
                generation_time_ms=1000,
                regeneration_count=-1,
            )

    def test_thinking_default_none(self) -> None:
        """thinking should default to None."""
        result = ResponseGenerationResult(
            content="Test",
            generation_time_ms=1000,
        )

        assert result.thinking is None
        assert result.has_thinking is False

    def test_thinking_with_agent_thinking(self) -> None:
        """Should accept AgentThinking instance."""
        thinking = AgentThinking(
            turn_goal="Extract payment details",
            selected_tactic="Ask Questions",
            reasoning="Scammer mentioned wire transfer.",
        )
        result = ResponseGenerationResult(
            content="Test response",
            generation_time_ms=1500,
            thinking=thinking,
        )

        assert result.thinking is not None
        assert result.has_thinking is True
        assert result.thinking.turn_goal == "Extract payment details"
        assert result.thinking.selected_tactic == "Ask Questions"

    def test_has_thinking_property(self) -> None:
        """has_thinking should correctly reflect thinking presence."""
        result_without = ResponseGenerationResult(
            content="Test",
            generation_time_ms=1000,
            thinking=None,
        )
        thinking = AgentThinking(
            turn_goal="Test",
            selected_tactic="Test",
            reasoning="Test",
        )
        result_with = ResponseGenerationResult(
            content="Test",
            generation_time_ms=1000,
            thinking=thinking,
        )

        assert result_without.has_thinking is False
        assert result_with.has_thinking is True
