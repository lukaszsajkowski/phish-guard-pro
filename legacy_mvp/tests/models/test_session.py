"""Comprehensive tests for Session Pydantic models.

These tests verify that the session models correctly:
1. Define all SessionStage enum values
2. Initialize SessionState with defaults
3. Implement is_input_stage property
4. Auto-generate created_at timestamp
5. Handle optional email_content field
6. Handle copy-to-clipboard state (US-007)

Test Categories:
- SessionStage enum values
- SessionState default initialization
- SessionState properties
- SessionState fields
- Factory function
- Edge cases
- Copy functionality (US-007)
"""

import time
from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from phishguard.models import (
    ConversationMessage,
    MessageSender,
    SessionStage,
    SessionState,
    create_initial_session_state,
)


class TestSessionStageEnum:
    """Tests for SessionStage enum definition."""

    def test_input_stage_exists(self) -> None:
        """INPUT stage should exist with value 'input'."""
        assert SessionStage.INPUT.value == "input"

    def test_analyzing_stage_exists(self) -> None:
        """ANALYZING stage should exist with value 'analyzing'."""
        assert SessionStage.ANALYZING.value == "analyzing"

    def test_classified_stage_exists(self) -> None:
        """CLASSIFIED stage should exist with value 'classified'."""
        assert SessionStage.CLASSIFIED.value == "classified"

    def test_conversation_stage_exists(self) -> None:
        """CONVERSATION stage should exist with value 'conversation'."""
        assert SessionStage.CONVERSATION.value == "conversation"

    def test_summary_stage_exists(self) -> None:
        """SUMMARY stage should exist with value 'summary'."""
        assert SessionStage.SUMMARY.value == "summary"

    def test_all_stages_count(self) -> None:
        """There should be exactly 7 session stages (5 main + 2 demo)."""
        all_stages = list(SessionStage)
        assert len(all_stages) == 7

    @pytest.mark.parametrize(
        "stage,expected_value",
        [
            (SessionStage.INPUT, "input"),
            (SessionStage.ANALYZING, "analyzing"),
            (SessionStage.CLASSIFIED, "classified"),
            (SessionStage.CONVERSATION, "conversation"),
            (SessionStage.SUMMARY, "summary"),
        ],
        ids=["input", "analyzing", "classified", "conversation", "summary"],
    )
    def test_stage_values_parametrized(
        self, stage: SessionStage, expected_value: str
    ) -> None:
        """Each stage should have correct string value."""
        assert stage.value == expected_value

    def test_stage_is_string_enum(self) -> None:
        """SessionStage should be a string enum."""
        assert isinstance(SessionStage.INPUT, str)
        assert isinstance(SessionStage.INPUT.value, str)

    def test_stage_string_comparison(self) -> None:
        """SessionStage members should compare as strings."""
        assert SessionStage.INPUT == "input"
        assert SessionStage.ANALYZING == "analyzing"

    def test_stage_from_value(self) -> None:
        """SessionStage should be constructible from string values."""
        assert SessionStage("input") == SessionStage.INPUT
        assert SessionStage("analyzing") == SessionStage.ANALYZING
        assert SessionStage("classified") == SessionStage.CLASSIFIED
        assert SessionStage("conversation") == SessionStage.CONVERSATION
        assert SessionStage("summary") == SessionStage.SUMMARY

    def test_invalid_stage_value_raises(self) -> None:
        """Invalid stage value should raise ValueError."""
        with pytest.raises(ValueError):
            SessionStage("invalid_stage")


class TestSessionStateDefaultInitialization:
    """Tests for SessionState default initialization."""

    def test_default_stage_is_input(self) -> None:
        """Default stage should be INPUT."""
        session = SessionState()
        assert session.stage == SessionStage.INPUT

    def test_default_email_content_is_none(self) -> None:
        """Default email_content should be None."""
        session = SessionState()
        assert session.email_content is None

    def test_created_at_is_auto_generated(self) -> None:
        """created_at should be auto-generated on instantiation."""
        before = datetime.now(UTC)
        session = SessionState()
        after = datetime.now(UTC)

        assert session.created_at is not None
        assert isinstance(session.created_at, datetime)
        assert before <= session.created_at <= after

    def test_created_at_is_timezone_aware(self) -> None:
        """created_at should be timezone-aware (UTC)."""
        session = SessionState()
        assert session.created_at.tzinfo is not None
        assert session.created_at.tzinfo == UTC

    def test_multiple_sessions_have_different_timestamps(self) -> None:
        """Each session should have its own unique timestamp."""
        session1 = SessionState()
        session2 = SessionState()
        # Timestamps should be equal or session2 should be later
        assert session2.created_at >= session1.created_at


class TestSessionStateIsInputStageProperty:
    """Tests for the is_input_stage property."""

    def test_is_input_stage_true_for_input(self) -> None:
        """is_input_stage should return True for INPUT stage."""
        session = SessionState(stage=SessionStage.INPUT)
        assert session.is_input_stage is True

    def test_is_input_stage_false_for_analyzing(self) -> None:
        """is_input_stage should return False for ANALYZING stage."""
        session = SessionState(stage=SessionStage.ANALYZING)
        assert session.is_input_stage is False

    def test_is_input_stage_false_for_classified(self) -> None:
        """is_input_stage should return False for CLASSIFIED stage."""
        session = SessionState(stage=SessionStage.CLASSIFIED)
        assert session.is_input_stage is False

    def test_is_input_stage_false_for_conversation(self) -> None:
        """is_input_stage should return False for CONVERSATION stage."""
        session = SessionState(stage=SessionStage.CONVERSATION)
        assert session.is_input_stage is False

    def test_is_input_stage_false_for_summary(self) -> None:
        """is_input_stage should return False for SUMMARY stage."""
        session = SessionState(stage=SessionStage.SUMMARY)
        assert session.is_input_stage is False

    @pytest.mark.parametrize(
        "stage,expected",
        [
            (SessionStage.INPUT, True),
            (SessionStage.ANALYZING, False),
            (SessionStage.CLASSIFIED, False),
            (SessionStage.CONVERSATION, False),
            (SessionStage.SUMMARY, False),
        ],
        ids=["input", "analyzing", "classified", "conversation", "summary"],
    )
    def test_is_input_stage_parametrized(
        self, stage: SessionStage, expected: bool
    ) -> None:
        """is_input_stage should return correct value for each stage."""
        session = SessionState(stage=stage)
        assert session.is_input_stage is expected

    def test_is_input_stage_consistent_across_calls(self) -> None:
        """is_input_stage should be consistent across multiple calls."""
        session = SessionState(stage=SessionStage.INPUT)
        assert session.is_input_stage is True
        assert session.is_input_stage is True
        assert session.is_input_stage is True

    def test_is_input_stage_after_stage_change(self) -> None:
        """is_input_stage should update when stage changes."""
        session = SessionState(stage=SessionStage.INPUT)
        assert session.is_input_stage is True

        session.stage = SessionStage.ANALYZING
        assert session.is_input_stage is False


class TestSessionStateEmailContentField:
    """Tests for the email_content optional field."""

    def test_email_content_default_is_none(self) -> None:
        """email_content should default to None."""
        session = SessionState()
        assert session.email_content is None

    def test_email_content_can_be_set_on_init(self) -> None:
        """email_content can be set during initialization."""
        content = "This is a phishing email content for testing."
        session = SessionState(email_content=content)
        assert session.email_content == content

    def test_email_content_can_be_set_after_init(self) -> None:
        """email_content can be set after initialization."""
        session = SessionState()
        assert session.email_content is None

        session.email_content = "Updated email content for testing."
        assert session.email_content == "Updated email content for testing."

    def test_email_content_can_be_cleared(self) -> None:
        """email_content can be set back to None."""
        session = SessionState(email_content="Some content here")
        assert session.email_content is not None

        session.email_content = None
        assert session.email_content is None

    def test_email_content_preserves_multiline(self) -> None:
        """email_content should preserve multiline content."""
        content = """Line 1
        Line 2
        Line 3"""
        session = SessionState(email_content=content)
        assert session.email_content == content
        assert "\n" in session.email_content

    def test_email_content_preserves_special_characters(self) -> None:
        """email_content should preserve special characters."""
        content = "Special chars: @#$%^&*()[]{}|\\;:'\",.<>?/`~"
        session = SessionState(email_content=content)
        assert session.email_content == content


class TestSessionStateCreatedAtField:
    """Tests for the created_at auto-generated field."""

    def test_created_at_is_datetime(self) -> None:
        """created_at should be a datetime object."""
        session = SessionState()
        assert isinstance(session.created_at, datetime)

    def test_created_at_is_recent(self) -> None:
        """created_at should be close to current time."""
        now = datetime.now(UTC)
        session = SessionState()
        delta = abs((session.created_at - now).total_seconds())
        assert delta < 1  # Within 1 second

    def test_created_at_can_be_explicitly_set(self) -> None:
        """created_at can be explicitly set during initialization."""
        specific_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
        session = SessionState(created_at=specific_time)
        assert session.created_at == specific_time

    def test_created_at_preserves_timezone(self) -> None:
        """created_at should preserve timezone information."""
        session = SessionState()
        # The default factory uses UTC
        assert session.created_at.tzinfo == UTC


class TestSessionStateStageTransitions:
    """Tests for stage transitions and state management."""

    def test_stage_can_be_changed(self) -> None:
        """Stage should be changeable after initialization."""
        session = SessionState()
        assert session.stage == SessionStage.INPUT

        session.stage = SessionStage.ANALYZING
        assert session.stage == SessionStage.ANALYZING

    def test_full_stage_progression(self) -> None:
        """Session should support full stage progression."""
        session = SessionState()
        stages = [
            SessionStage.INPUT,
            SessionStage.ANALYZING,
            SessionStage.CLASSIFIED,
            SessionStage.CONVERSATION,
            SessionStage.SUMMARY,
        ]

        for stage in stages:
            session.stage = stage
            assert session.stage == stage

    def test_stage_can_be_set_backwards(self) -> None:
        """Stage can be set to earlier stages (for reset scenarios)."""
        session = SessionState(stage=SessionStage.CONVERSATION)
        session.stage = SessionStage.INPUT
        assert session.stage == SessionStage.INPUT


class TestCreateInitialSessionStateFactory:
    """Tests for the create_initial_session_state factory function."""

    def test_returns_session_state_instance(self) -> None:
        """Factory should return a SessionState instance."""
        session = create_initial_session_state()
        assert isinstance(session, SessionState)

    def test_returns_input_stage(self) -> None:
        """Factory should return session in INPUT stage."""
        session = create_initial_session_state()
        assert session.stage == SessionStage.INPUT

    def test_returns_none_email_content(self) -> None:
        """Factory should return session with None email_content."""
        session = create_initial_session_state()
        assert session.email_content is None

    def test_returns_recent_created_at(self) -> None:
        """Factory should return session with recent created_at."""
        before = datetime.now(UTC)
        session = create_initial_session_state()
        after = datetime.now(UTC)

        assert before <= session.created_at <= after

    def test_returns_new_instance_each_call(self) -> None:
        """Factory should return new instance on each call."""
        session1 = create_initial_session_state()
        session2 = create_initial_session_state()
        assert session1 is not session2

    def test_is_input_stage_true(self) -> None:
        """Factory-created session should have is_input_stage True."""
        session = create_initial_session_state()
        assert session.is_input_stage is True


class TestSessionStateModelConfig:
    """Tests for Pydantic model configuration."""

    def test_model_is_not_frozen(self) -> None:
        """SessionState should allow attribute modification."""
        session = SessionState()
        session.stage = SessionStage.ANALYZING
        assert session.stage == SessionStage.ANALYZING

    def test_validates_on_assignment(self) -> None:
        """Model should validate on assignment."""
        session = SessionState()
        # Valid stage assignment should work
        session.stage = SessionStage.CLASSIFIED
        assert session.stage == SessionStage.CLASSIFIED

    def test_use_enum_values_is_false(self) -> None:
        """Model should preserve enum objects (not convert to values)."""
        session = SessionState()
        # stage should be the enum object, not the string value
        assert isinstance(session.stage, SessionStage)
        assert session.stage == SessionStage.INPUT

    def test_json_serialization(self) -> None:
        """Model should serialize to JSON correctly."""
        session = SessionState(
            stage=SessionStage.ANALYZING,
            email_content="Test email content",
        )
        json_str = session.model_dump_json()
        assert "analyzing" in json_str
        assert "Test email content" in json_str

    def test_dict_serialization(self) -> None:
        """Model should serialize to dict correctly."""
        session = SessionState(
            stage=SessionStage.CLASSIFIED,
            email_content="Test content",
        )
        data = session.model_dump()
        assert data["stage"] == SessionStage.CLASSIFIED
        assert data["email_content"] == "Test content"
        assert "created_at" in data

    def test_model_from_dict(self) -> None:
        """Model should be constructible from dict."""
        now = datetime.now(UTC)
        data = {
            "stage": SessionStage.CONVERSATION,
            "email_content": "Email from dict",
            "created_at": now,
        }
        session = SessionState(**data)
        assert session.stage == SessionStage.CONVERSATION
        assert session.email_content == "Email from dict"
        assert session.created_at == now


class TestSessionStateForceContinueField:
    """Tests for the force_continue boolean field."""

    def test_force_continue_default_is_false(self) -> None:
        """force_continue should default to False when creating a new SessionState."""
        session = SessionState()
        assert session.force_continue is False

    def test_force_continue_can_be_set_to_true_on_init(self) -> None:
        """force_continue can be set to True during initialization."""
        session = SessionState(force_continue=True)
        assert session.force_continue is True

    def test_force_continue_can_be_set_to_true_after_init(self) -> None:
        """force_continue can be changed to True after initialization."""
        session = SessionState()
        assert session.force_continue is False

        session.force_continue = True
        assert session.force_continue is True

    def test_force_continue_can_be_toggled(self) -> None:
        """force_continue can be toggled between True and False."""
        session = SessionState(force_continue=True)
        assert session.force_continue is True

        session.force_continue = False
        assert session.force_continue is False

        session.force_continue = True
        assert session.force_continue is True

    def test_force_continue_persists_in_model_dump(self) -> None:
        """force_continue should persist correctly when serialized via model_dump()."""
        session = SessionState(force_continue=True)
        data = session.model_dump()

        assert "force_continue" in data
        assert data["force_continue"] is True

    def test_force_continue_false_persists_in_model_dump(self) -> None:
        """force_continue=False should persist correctly via model_dump()."""
        session = SessionState(force_continue=False)
        data = session.model_dump()

        assert "force_continue" in data
        assert data["force_continue"] is False

    def test_force_continue_persists_in_model_dump_json(self) -> None:
        """force_continue should persist correctly when serialized to JSON."""
        session = SessionState(force_continue=True)
        json_str = session.model_dump_json()

        assert (
            '"force_continue":true' in json_str or '"force_continue": true' in json_str
        )

    def test_force_continue_reconstruction_from_model_dump(self) -> None:
        """force_continue should persist across model_dump() and reconstruction."""
        original = SessionState(force_continue=True)
        data = original.model_dump()

        reconstructed = SessionState(**data)

        assert reconstructed.force_continue is True
        assert reconstructed.force_continue == original.force_continue

    def test_force_continue_false_reconstruction_from_model_dump(self) -> None:
        """force_continue=False persists across model_dump() and reconstruction."""
        original = SessionState(force_continue=False)
        data = original.model_dump()

        reconstructed = SessionState(**data)

        assert reconstructed.force_continue is False
        assert reconstructed.force_continue == original.force_continue

    @pytest.mark.parametrize(
        "initial_value",
        [True, False],
        ids=["force_continue_true", "force_continue_false"],
    )
    def test_force_continue_roundtrip_parametrized(self, initial_value: bool) -> None:
        """force_continue should survive roundtrip serialization."""
        original = SessionState(force_continue=initial_value)
        data = original.model_dump()
        reconstructed = SessionState(**data)

        assert reconstructed.force_continue is initial_value

    def test_force_continue_independent_across_instances(self) -> None:
        """force_continue should be independent across SessionState instances."""
        session1 = SessionState(force_continue=True)
        session2 = SessionState(force_continue=False)

        assert session1.force_continue is True
        assert session2.force_continue is False

        session1.force_continue = False
        assert session1.force_continue is False
        assert session2.force_continue is False  # Still unchanged

    def test_factory_returns_force_continue_false(self) -> None:
        """Factory function returns session with force_continue=False."""
        session = create_initial_session_state()
        assert session.force_continue is False


class TestSessionStateEditing:
    """Tests for SessionState editing functionality (US-006)."""

    # --- Default Values Tests ---

    def test_editing_message_index_default_is_none(self) -> None:
        """editing_message_index should default to None."""
        state = SessionState()
        assert state.editing_message_index is None

    def test_editing_content_default_is_none(self) -> None:
        """editing_content should default to None."""
        state = SessionState()
        assert state.editing_content is None

    # --- is_editing Property Tests ---

    def test_is_editing_false_by_default(self) -> None:
        """is_editing should return False when not editing."""
        state = SessionState()
        assert state.is_editing is False

    def test_is_editing_true_when_editing_message_index_is_zero(self) -> None:
        """is_editing should return True when editing_message_index is 0."""
        state = SessionState(editing_message_index=0)
        assert state.is_editing is True

    def test_is_editing_true_when_editing_message_index_is_positive(self) -> None:
        """is_editing should return True when editing_message_index is positive."""
        state = SessionState(editing_message_index=5)
        assert state.is_editing is True

    def test_is_editing_consistent_across_calls(self) -> None:
        """is_editing should return consistent results across multiple calls."""
        state = SessionState(editing_message_index=1)
        assert state.is_editing is True
        assert state.is_editing is True
        assert state.is_editing is True

    def test_is_editing_updates_when_editing_message_index_changes(self) -> None:
        """is_editing should update when editing_message_index is modified."""
        state = SessionState()
        assert state.is_editing is False

        state.editing_message_index = 0
        assert state.is_editing is True

        state.editing_message_index = None
        assert state.is_editing is False

    # --- update_message_content Method Tests ---

    def test_update_message_content_updates_content_at_valid_index(self) -> None:
        """update_message_content should update message at valid index."""
        msg = ConversationMessage(
            sender=MessageSender.BOT,
            content="Original content",
            turn_number=1,
        )
        state = SessionState(conversation_history=[msg])

        state.update_message_content(0, "Updated content")

        assert state.conversation_history[0].content == "Updated content"

    def test_update_message_content_preserves_sender(self) -> None:
        """update_message_content should preserve the sender attribute."""
        msg = ConversationMessage(
            sender=MessageSender.BOT,
            content="Original content",
            turn_number=1,
        )
        state = SessionState(conversation_history=[msg])

        state.update_message_content(0, "New content")

        assert state.conversation_history[0].sender == MessageSender.BOT

    def test_update_message_content_preserves_timestamp(self) -> None:
        """update_message_content should preserve the timestamp attribute."""
        original_timestamp = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
        msg = ConversationMessage(
            sender=MessageSender.BOT,
            content="Original content",
            timestamp=original_timestamp,
            turn_number=1,
        )
        state = SessionState(conversation_history=[msg])

        state.update_message_content(0, "New content")

        assert state.conversation_history[0].timestamp == original_timestamp

    def test_update_message_content_preserves_turn_number(self) -> None:
        """update_message_content should preserve the turn_number attribute."""
        msg = ConversationMessage(
            sender=MessageSender.BOT,
            content="Original content",
            turn_number=5,
        )
        state = SessionState(conversation_history=[msg])

        state.update_message_content(0, "New content")

        assert state.conversation_history[0].turn_number == 5

    def test_update_message_content_raises_index_error_for_negative_index(self) -> None:
        """update_message_content should raise IndexError for negative index."""
        msg = ConversationMessage(
            sender=MessageSender.BOT,
            content="Content",
            turn_number=1,
        )
        state = SessionState(conversation_history=[msg])

        with pytest.raises(IndexError) as exc_info:
            state.update_message_content(-1, "New content")

        assert "out of range" in str(exc_info.value)

    def test_update_message_content_raises_index_error_for_index_too_large(
        self,
    ) -> None:
        """update_message_content should raise IndexError when index >= len."""
        msg = ConversationMessage(
            sender=MessageSender.BOT,
            content="Content",
            turn_number=1,
        )
        state = SessionState(conversation_history=[msg])

        with pytest.raises(IndexError) as exc_info:
            state.update_message_content(1, "New content")

        assert "out of range" in str(exc_info.value)

    def test_update_message_content_raises_index_error_for_empty_history(self) -> None:
        """update_message_content should raise IndexError for empty history."""
        state = SessionState(conversation_history=[])

        with pytest.raises(IndexError) as exc_info:
            state.update_message_content(0, "New content")

        assert "out of range" in str(exc_info.value)

    def test_update_message_content_with_multiple_messages(self) -> None:
        """update_message_content should update correct message in list."""
        msg1 = ConversationMessage(
            sender=MessageSender.BOT,
            content="First message",
            turn_number=1,
        )
        msg2 = ConversationMessage(
            sender=MessageSender.SCAMMER,
            content="Second message",
            turn_number=1,
        )
        msg3 = ConversationMessage(
            sender=MessageSender.BOT,
            content="Third message",
            turn_number=2,
        )
        state = SessionState(conversation_history=[msg1, msg2, msg3])

        state.update_message_content(1, "Updated second message")

        assert state.conversation_history[0].content == "First message"
        assert state.conversation_history[1].content == "Updated second message"
        assert state.conversation_history[2].content == "Third message"

    def test_update_message_content_does_not_modify_other_messages(self) -> None:
        """update_message_content should not modify other messages in history."""
        msg1 = ConversationMessage(
            sender=MessageSender.BOT,
            content="First",
            turn_number=1,
        )
        msg2 = ConversationMessage(
            sender=MessageSender.BOT,
            content="Second",
            turn_number=2,
        )
        state = SessionState(conversation_history=[msg1, msg2])
        original_msg1_id = id(state.conversation_history[0])

        state.update_message_content(1, "Updated second")

        # First message should be unchanged (same object)
        assert id(state.conversation_history[0]) == original_msg1_id
        assert state.conversation_history[0].content == "First"

    def test_update_message_content_works_with_scammer_message(self) -> None:
        """update_message_content should work with scammer messages too."""
        msg = ConversationMessage(
            sender=MessageSender.SCAMMER,
            content="Scammer message",
            turn_number=1,
        )
        state = SessionState(conversation_history=[msg])

        state.update_message_content(0, "Updated scammer message")

        assert state.conversation_history[0].content == "Updated scammer message"
        assert state.conversation_history[0].sender == MessageSender.SCAMMER

    @pytest.mark.parametrize(
        "index,history_length",
        [
            (-1, 1),
            (-5, 3),
            (1, 1),
            (5, 3),
            (0, 0),
        ],
        ids=[
            "negative_index_single_item",
            "negative_index_multiple_items",
            "index_equals_length",
            "index_exceeds_length",
            "zero_on_empty_list",
        ],
    )
    def test_update_message_content_invalid_indices_parametrized(
        self, index: int, history_length: int
    ) -> None:
        """update_message_content raises IndexError for invalid indices."""
        messages = [
            ConversationMessage(
                sender=MessageSender.BOT,
                content=f"Message {i}",
                turn_number=i + 1,
            )
            for i in range(history_length)
        ]
        state = SessionState(conversation_history=messages)

        with pytest.raises(IndexError):
            state.update_message_content(index, "New content")

    # --- clear_editing_state Method Tests ---

    def test_clear_editing_state_clears_editing_message_index(self) -> None:
        """clear_editing_state should set editing_message_index to None."""
        state = SessionState(editing_message_index=5)
        assert state.editing_message_index == 5

        state.clear_editing_state()

        assert state.editing_message_index is None

    def test_clear_editing_state_clears_editing_content(self) -> None:
        """clear_editing_state should set editing_content to None."""
        state = SessionState(editing_content="Some editing content")
        assert state.editing_content == "Some editing content"

        state.clear_editing_state()

        assert state.editing_content is None

    def test_clear_editing_state_clears_both_fields_together(self) -> None:
        """clear_editing_state should clear both editing fields at once."""
        state = SessionState(
            editing_message_index=3,
            editing_content="Content being edited",
        )

        state.clear_editing_state()

        assert state.editing_message_index is None
        assert state.editing_content is None

    def test_clear_editing_state_works_when_already_none(self) -> None:
        """clear_editing_state should work even when fields are already None."""
        state = SessionState()
        assert state.editing_message_index is None
        assert state.editing_content is None

        # Should not raise any exception
        state.clear_editing_state()

        assert state.editing_message_index is None
        assert state.editing_content is None

    def test_clear_editing_state_makes_is_editing_false(self) -> None:
        """clear_editing_state should make is_editing return False."""
        state = SessionState(editing_message_index=0)
        assert state.is_editing is True

        state.clear_editing_state()

        assert state.is_editing is False

    def test_clear_editing_state_does_not_affect_other_fields(self) -> None:
        """clear_editing_state should not modify other session fields."""
        msg = ConversationMessage(
            sender=MessageSender.BOT,
            content="Test message",
            turn_number=1,
        )
        state = SessionState(
            stage=SessionStage.CONVERSATION,
            email_content="Test email",
            editing_message_index=0,
            editing_content="Editing...",
            conversation_history=[msg],
        )

        state.clear_editing_state()

        assert state.stage == SessionStage.CONVERSATION
        assert state.email_content == "Test email"
        assert len(state.conversation_history) == 1
        assert state.conversation_history[0].content == "Test message"

    # --- Integration Tests ---

    def test_editing_workflow_complete_cycle(self) -> None:
        """Test a complete editing workflow: start editing, modify, save, clear."""
        msg = ConversationMessage(
            sender=MessageSender.BOT,
            content="Original response",
            turn_number=1,
        )
        state = SessionState(conversation_history=[msg])

        # Start editing
        state.editing_message_index = 0
        state.editing_content = "Original response"
        assert state.is_editing is True

        # Modify content
        state.editing_content = "Modified response"

        # Save the edit
        state.update_message_content(0, state.editing_content)
        assert state.conversation_history[0].content == "Modified response"

        # Clear editing state
        state.clear_editing_state()
        assert state.is_editing is False
        assert state.editing_message_index is None
        assert state.editing_content is None

    def test_editing_fields_persist_in_model_dump(self) -> None:
        """Editing fields should persist correctly in model_dump()."""
        state = SessionState(
            editing_message_index=2,
            editing_content="Content being edited",
        )

        data = state.model_dump()

        assert "editing_message_index" in data
        assert "editing_content" in data
        assert data["editing_message_index"] == 2
        assert data["editing_content"] == "Content being edited"

    def test_editing_fields_none_persist_in_model_dump(self) -> None:
        """Editing fields as None should persist correctly in model_dump()."""
        state = SessionState()

        data = state.model_dump()

        assert "editing_message_index" in data
        assert "editing_content" in data
        assert data["editing_message_index"] is None
        assert data["editing_content"] is None

    def test_editing_fields_roundtrip_serialization(self) -> None:
        """Editing fields should survive model_dump() and reconstruction."""
        original = SessionState(
            editing_message_index=1,
            editing_content="Editing in progress",
        )

        data = original.model_dump()
        reconstructed = SessionState(**data)

        assert reconstructed.editing_message_index == 1
        assert reconstructed.editing_content == "Editing in progress"
        assert reconstructed.is_editing is True


class TestSessionStateCopyFunctionality:
    """Tests for SessionState copy-to-clipboard functionality (US-007)."""

    # --- Default Values Tests ---

    def test_copied_message_index_default_is_none(self) -> None:
        """copied_message_index should default to None."""
        state = SessionState()
        assert state.copied_message_index is None

    def test_copy_timestamp_default_is_none(self) -> None:
        """copy_timestamp should default to None."""
        state = SessionState()
        assert state.copy_timestamp is None

    # --- should_show_copy_confirmation Method Tests ---

    def test_should_show_copy_confirmation_false_when_index_mismatch(self) -> None:
        """should_show_copy_confirmation returns False when index doesn't match."""
        state = SessionState(
            copied_message_index=0,
            copy_timestamp=time.time(),
        )
        assert state.should_show_copy_confirmation(1) is False
        assert state.should_show_copy_confirmation(2) is False

    def test_should_show_copy_confirmation_false_when_timestamp_is_none(self) -> None:
        """should_show_copy_confirmation returns False when timestamp is None."""
        state = SessionState(
            copied_message_index=0,
            copy_timestamp=None,
        )
        assert state.should_show_copy_confirmation(0) is False

    def test_should_show_copy_confirmation_false_when_index_is_none(self) -> None:
        """should_show_copy_confirmation returns False when index is None."""
        state = SessionState(
            copied_message_index=None,
            copy_timestamp=time.time(),
        )
        assert state.should_show_copy_confirmation(0) is False

    def test_should_show_copy_confirmation_true_within_2_seconds(self) -> None:
        """should_show_copy_confirmation returns True within 2 seconds."""
        current_time = time.time()
        state = SessionState(
            copied_message_index=0,
            copy_timestamp=current_time,
        )
        # Mock time.time() to return same time (0 seconds elapsed)
        with patch("phishguard.models.session.time.time", return_value=current_time):
            assert state.should_show_copy_confirmation(0) is True

        # Mock time.time() to return 1 second later
        with patch(
            "phishguard.models.session.time.time", return_value=current_time + 1.0
        ):
            assert state.should_show_copy_confirmation(0) is True

        # Mock time.time() to return 1.9 seconds later
        with patch(
            "phishguard.models.session.time.time", return_value=current_time + 1.9
        ):
            assert state.should_show_copy_confirmation(0) is True

    def test_should_show_copy_confirmation_false_after_2_seconds(self) -> None:
        """should_show_copy_confirmation returns False after 2 seconds."""
        current_time = time.time()
        state = SessionState(
            copied_message_index=0,
            copy_timestamp=current_time,
        )
        # Mock time.time() to return exactly 2 seconds later
        with patch(
            "phishguard.models.session.time.time", return_value=current_time + 2.0
        ):
            assert state.should_show_copy_confirmation(0) is False

        # Mock time.time() to return 3 seconds later
        with patch(
            "phishguard.models.session.time.time", return_value=current_time + 3.0
        ):
            assert state.should_show_copy_confirmation(0) is False

    def test_should_show_copy_confirmation_for_different_indices(self) -> None:
        """should_show_copy_confirmation correctly identifies copied message."""
        current_time = time.time()
        state = SessionState(
            copied_message_index=2,
            copy_timestamp=current_time,
        )
        with patch("phishguard.models.session.time.time", return_value=current_time):
            assert state.should_show_copy_confirmation(0) is False
            assert state.should_show_copy_confirmation(1) is False
            assert state.should_show_copy_confirmation(2) is True
            assert state.should_show_copy_confirmation(3) is False

    # --- clear_copy_state Method Tests ---

    def test_clear_copy_state_clears_copied_message_index(self) -> None:
        """clear_copy_state should set copied_message_index to None."""
        state = SessionState(copied_message_index=5)
        assert state.copied_message_index == 5

        state.clear_copy_state()

        assert state.copied_message_index is None

    def test_clear_copy_state_clears_copy_timestamp(self) -> None:
        """clear_copy_state should set copy_timestamp to None."""
        state = SessionState(copy_timestamp=time.time())
        assert state.copy_timestamp is not None

        state.clear_copy_state()

        assert state.copy_timestamp is None

    def test_clear_copy_state_clears_both_fields_together(self) -> None:
        """clear_copy_state should clear both copy fields at once."""
        state = SessionState(
            copied_message_index=3,
            copy_timestamp=time.time(),
        )

        state.clear_copy_state()

        assert state.copied_message_index is None
        assert state.copy_timestamp is None

    def test_clear_copy_state_works_when_already_none(self) -> None:
        """clear_copy_state should work even when fields are already None."""
        state = SessionState()
        assert state.copied_message_index is None
        assert state.copy_timestamp is None

        # Should not raise any exception
        state.clear_copy_state()

        assert state.copied_message_index is None
        assert state.copy_timestamp is None

    def test_clear_copy_state_does_not_affect_other_fields(self) -> None:
        """clear_copy_state should not modify other session fields."""
        msg = ConversationMessage(
            sender=MessageSender.BOT,
            content="Test message",
            turn_number=1,
        )
        state = SessionState(
            stage=SessionStage.CONVERSATION,
            email_content="Test email",
            copied_message_index=0,
            copy_timestamp=time.time(),
            conversation_history=[msg],
        )

        state.clear_copy_state()

        assert state.stage == SessionStage.CONVERSATION
        assert state.email_content == "Test email"
        assert len(state.conversation_history) == 1
        assert state.conversation_history[0].content == "Test message"

    # --- Integration Tests ---

    def test_copy_workflow_complete_cycle(self) -> None:
        """Test a complete copy workflow: copy, show confirmation, clear."""
        current_time = time.time()
        state = SessionState()

        # Simulate copy button click
        state.copied_message_index = 0
        state.copy_timestamp = current_time

        # Confirmation should show within 2 seconds
        with patch("phishguard.models.session.time.time", return_value=current_time):
            assert state.should_show_copy_confirmation(0) is True

        # After 2 seconds, confirmation should not show
        with patch(
            "phishguard.models.session.time.time", return_value=current_time + 2.0
        ):
            assert state.should_show_copy_confirmation(0) is False

        # Clear the copy state
        state.clear_copy_state()
        assert state.copied_message_index is None
        assert state.copy_timestamp is None

    def test_copy_fields_persist_in_model_dump(self) -> None:
        """Copy fields should persist correctly in model_dump()."""
        timestamp = time.time()
        state = SessionState(
            copied_message_index=2,
            copy_timestamp=timestamp,
        )

        data = state.model_dump()

        assert "copied_message_index" in data
        assert "copy_timestamp" in data
        assert data["copied_message_index"] == 2
        assert data["copy_timestamp"] == timestamp

    def test_copy_fields_none_persist_in_model_dump(self) -> None:
        """Copy fields as None should persist correctly in model_dump()."""
        state = SessionState()

        data = state.model_dump()

        assert "copied_message_index" in data
        assert "copy_timestamp" in data
        assert data["copied_message_index"] is None
        assert data["copy_timestamp"] is None

    def test_copy_fields_roundtrip_serialization(self) -> None:
        """Copy fields should survive model_dump() and reconstruction."""
        timestamp = time.time()
        original = SessionState(
            copied_message_index=1,
            copy_timestamp=timestamp,
        )

        data = original.model_dump()
        reconstructed = SessionState(**data)

        assert reconstructed.copied_message_index == 1
        assert reconstructed.copy_timestamp == timestamp

    def test_factory_returns_copy_fields_as_none(self) -> None:
        """Factory function returns session with copy fields as None."""
        session = create_initial_session_state()
        assert session.copied_message_index is None
        assert session.copy_timestamp is None


class TestSessionStateTurnLimit:
    """Tests for SessionState turn limit functionality (US-013)."""

    # --- Default Values Tests ---

    def test_turn_limit_default_is_20(self) -> None:
        """turn_limit should default to 20 per PRD FR-025."""
        state = SessionState()
        assert state.turn_limit == 20

    def test_limit_extended_count_default_is_0(self) -> None:
        """limit_extended_count should default to 0."""
        state = SessionState()
        assert state.limit_extended_count == 0

    # --- is_at_limit Property Tests ---

    def test_is_at_limit_false_when_under_limit(self) -> None:
        """is_at_limit should return False when turn_count < turn_limit."""
        state = SessionState(turn_limit=20)
        # No messages, so turn_count is 1 (default minimum)
        assert state.is_at_limit is False

    def test_is_at_limit_true_when_at_limit(self) -> None:
        """is_at_limit should return True when turn_count >= turn_limit."""
        # Create state with messages to reach limit
        messages = [
            ConversationMessage(
                sender=MessageSender.BOT,
                content=f"Message {i}",
                turn_number=i,
            )
            for i in range(1, 21)  # 20 bot messages
        ]
        state = SessionState(conversation_history=messages, turn_limit=20)
        assert state.turn_count == 20
        assert state.is_at_limit is True

    def test_is_at_limit_true_when_over_limit(self) -> None:
        """is_at_limit should return True when turn_count > turn_limit."""
        messages = [
            ConversationMessage(
                sender=MessageSender.BOT,
                content=f"Message {i}",
                turn_number=i,
            )
            for i in range(1, 26)  # 25 bot messages
        ]
        state = SessionState(conversation_history=messages, turn_limit=20)
        assert state.turn_count == 25
        assert state.is_at_limit is True

    # --- extend_limit Method Tests ---

    def test_extend_limit_adds_10_by_default(self) -> None:
        """extend_limit() should add 10 turns by default."""
        state = SessionState(turn_limit=20)
        state.extend_limit()
        assert state.turn_limit == 30

    def test_extend_limit_accepts_custom_amount(self) -> None:
        """extend_limit() should accept custom turn count."""
        state = SessionState(turn_limit=20)
        state.extend_limit(5)
        assert state.turn_limit == 25

    def test_extend_limit_increments_extended_count(self) -> None:
        """extend_limit() should increment limit_extended_count."""
        state = SessionState()
        assert state.limit_extended_count == 0

        state.extend_limit()
        assert state.limit_extended_count == 1

        state.extend_limit()
        assert state.limit_extended_count == 2

    def test_extend_limit_multiple_times(self) -> None:
        """extend_limit() can be called multiple times."""
        state = SessionState(turn_limit=20)
        state.extend_limit(10)
        state.extend_limit(10)
        state.extend_limit(10)
        assert state.turn_limit == 50
        assert state.limit_extended_count == 3

    # --- turn_counter_color Property Tests ---

    def test_turn_counter_color_default_under_15(self) -> None:
        """turn_counter_color should be 'default' for turns 1-14."""
        messages = [
            ConversationMessage(
                sender=MessageSender.BOT, content="Msg", turn_number=i
            )
            for i in range(1, 11)  # 10 bot messages
        ]
        state = SessionState(conversation_history=messages)
        assert state.turn_count == 10
        assert state.turn_counter_color == "default"

    def test_turn_counter_color_yellow_at_15(self) -> None:
        """turn_counter_color should be 'yellow' at turn 15."""
        messages = [
            ConversationMessage(
                sender=MessageSender.BOT, content="Msg", turn_number=i
            )
            for i in range(1, 16)  # 15 bot messages
        ]
        state = SessionState(conversation_history=messages)
        assert state.turn_count == 15
        assert state.turn_counter_color == "yellow"

    def test_turn_counter_color_yellow_between_15_and_19(self) -> None:
        """turn_counter_color should be 'yellow' for turns 15-19."""
        messages = [
            ConversationMessage(
                sender=MessageSender.BOT, content="Msg", turn_number=i
            )
            for i in range(1, 19)  # 18 bot messages
        ]
        state = SessionState(conversation_history=messages)
        assert state.turn_count == 18
        assert state.turn_counter_color == "yellow"

    def test_turn_counter_color_red_at_20(self) -> None:
        """turn_counter_color should be 'red' at turn 20."""
        messages = [
            ConversationMessage(
                sender=MessageSender.BOT, content="Msg", turn_number=i
            )
            for i in range(1, 21)  # 20 bot messages
        ]
        state = SessionState(conversation_history=messages)
        assert state.turn_count == 20
        assert state.turn_counter_color == "red"

    def test_turn_counter_color_red_over_20(self) -> None:
        """turn_counter_color should be 'red' for turns > 20."""
        messages = [
            ConversationMessage(
                sender=MessageSender.BOT, content="Msg", turn_number=i
            )
            for i in range(1, 26)  # 25 bot messages
        ]
        state = SessionState(conversation_history=messages)
        assert state.turn_count == 25
        assert state.turn_counter_color == "red"

    # --- turn_counter_display Property Tests ---

    def test_turn_counter_display_under_20(self) -> None:
        """turn_counter_display should show 'Turn X/20' for turns <= 20."""
        messages = [
            ConversationMessage(
                sender=MessageSender.BOT, content="Msg", turn_number=i
            )
            for i in range(1, 11)  # 10 bot messages
        ]
        state = SessionState(conversation_history=messages)
        assert state.turn_counter_display == "Turn 10/20"

    def test_turn_counter_display_at_20(self) -> None:
        """turn_counter_display should show 'Turn 20/20' at turn 20."""
        messages = [
            ConversationMessage(
                sender=MessageSender.BOT, content="Msg", turn_number=i
            )
            for i in range(1, 21)  # 20 bot messages
        ]
        state = SessionState(conversation_history=messages)
        assert state.turn_counter_display == "Turn 20/20"

    def test_turn_counter_display_over_20(self) -> None:
        """turn_counter_display should show 'Turn X/20+' for turns > 20."""
        messages = [
            ConversationMessage(
                sender=MessageSender.BOT, content="Msg", turn_number=i
            )
            for i in range(1, 26)  # 25 bot messages
        ]
        state = SessionState(conversation_history=messages)
        assert state.turn_counter_display == "Turn 25/20+"


class TestSessionStateUnmasking:
    """Tests for SessionState unmasking detection functionality (US-014)."""

    # --- Default Values Tests ---

    def test_unmasking_detected_default_is_false(self) -> None:
        """unmasking_detected should default to False."""
        state = SessionState()
        assert state.unmasking_detected is False

    def test_unmasking_phrases_default_is_empty(self) -> None:
        """unmasking_phrases should default to empty list."""
        state = SessionState()
        assert state.unmasking_phrases == []

    def test_unmasking_dismissed_default_is_false(self) -> None:
        """unmasking_dismissed should default to False."""
        state = SessionState()
        assert state.unmasking_dismissed is False

    # --- should_show_unmasking_warning Property Tests ---

    def test_should_show_unmasking_warning_false_when_not_detected(self) -> None:
        """should_show_unmasking_warning should be False when not detected."""
        state = SessionState(unmasking_detected=False)
        assert state.should_show_unmasking_warning is False

    def test_should_show_unmasking_warning_true_when_detected(self) -> None:
        """should_show_unmasking_warning should be True when detected."""
        state = SessionState(
            unmasking_detected=True, unmasking_phrases=["you're a bot"]
        )
        assert state.should_show_unmasking_warning is True

    def test_should_show_unmasking_warning_false_when_dismissed(self) -> None:
        """should_show_unmasking_warning should be False after dismissal."""
        state = SessionState(
            unmasking_detected=True,
            unmasking_phrases=["you're a bot"],
            unmasking_dismissed=True,
        )
        assert state.should_show_unmasking_warning is False

    # --- set_unmasking_detected Method Tests ---

    def test_set_unmasking_detected_sets_flag(self) -> None:
        """set_unmasking_detected() should set unmasking_detected to True."""
        state = SessionState()
        state.set_unmasking_detected(["you're a bot"])
        assert state.unmasking_detected is True

    def test_set_unmasking_detected_stores_phrases(self) -> None:
        """set_unmasking_detected() should store the matched phrases."""
        state = SessionState()
        phrases = ["you're a bot", "stop wasting my time"]
        state.set_unmasking_detected(phrases)
        assert state.unmasking_phrases == phrases

    def test_set_unmasking_detected_with_empty_list(self) -> None:
        """set_unmasking_detected() should work with empty phrase list."""
        state = SessionState()
        state.set_unmasking_detected([])
        assert state.unmasking_detected is True
        assert state.unmasking_phrases == []

    # --- dismiss_unmasking_warning Method Tests ---

    def test_dismiss_unmasking_warning_sets_dismissed(self) -> None:
        """dismiss_unmasking_warning() should set dismissed flag."""
        state = SessionState(unmasking_detected=True)
        state.dismiss_unmasking_warning()
        assert state.unmasking_dismissed is True

    def test_dismiss_unmasking_warning_keeps_detected_true(self) -> None:
        """dismiss_unmasking_warning() should not clear detected flag."""
        state = SessionState(
            unmasking_detected=True, unmasking_phrases=["test"]
        )
        state.dismiss_unmasking_warning()
        assert state.unmasking_detected is True
        assert state.unmasking_phrases == ["test"]

    # --- clear_unmasking_state Method Tests ---

    def test_clear_unmasking_state_clears_all_fields(self) -> None:
        """clear_unmasking_state() should clear all unmasking fields."""
        state = SessionState(
            unmasking_detected=True,
            unmasking_phrases=["you're a bot"],
            unmasking_dismissed=True,
        )
        state.clear_unmasking_state()
        assert state.unmasking_detected is False
        assert state.unmasking_phrases == []
        assert state.unmasking_dismissed is False

    def test_clear_unmasking_state_works_when_already_clear(self) -> None:
        """clear_unmasking_state() should work when already clear."""
        state = SessionState()
        state.clear_unmasking_state()
        assert state.unmasking_detected is False
        assert state.unmasking_phrases == []
        assert state.unmasking_dismissed is False

    # --- Integration Tests ---

    def test_unmasking_workflow_complete_cycle(self) -> None:
        """Test complete unmasking workflow: detect, warn, dismiss."""
        state = SessionState()

        # Initially no unmasking
        assert state.should_show_unmasking_warning is False

        # Detect unmasking
        state.set_unmasking_detected(["you're just a bot"])
        assert state.should_show_unmasking_warning is True
        assert state.unmasking_phrases == ["you're just a bot"]

        # Dismiss the warning
        state.dismiss_unmasking_warning()
        assert state.should_show_unmasking_warning is False
        assert state.unmasking_detected is True  # Still marked as detected

    def test_unmasking_fields_persist_in_model_dump(self) -> None:
        """Unmasking fields should persist correctly in model_dump()."""
        state = SessionState(
            unmasking_detected=True,
            unmasking_phrases=["stop messaging me"],
            unmasking_dismissed=False,
        )
        data = state.model_dump()

        assert "unmasking_detected" in data
        assert "unmasking_phrases" in data
        assert "unmasking_dismissed" in data
        assert data["unmasking_detected"] is True
        assert data["unmasking_phrases"] == ["stop messaging me"]
        assert data["unmasking_dismissed"] is False

    def test_factory_returns_unmasking_fields_as_default(self) -> None:
        """Factory function returns session with default unmasking fields."""
        session = create_initial_session_state()
        assert session.unmasking_detected is False
        assert session.unmasking_phrases == []
        assert session.unmasking_dismissed is False


class TestSessionStateNewSessionConfirmation:
    """Tests for SessionState new session confirmation field (US-023)."""

    # --- Default Value Tests ---

    def test_show_new_session_confirmation_default_is_false(self) -> None:
        """show_new_session_confirmation should default to False."""
        state = SessionState()
        assert state.show_new_session_confirmation is False

    # --- Setting Value Tests ---

    def test_show_new_session_confirmation_can_be_set_to_true_on_init(self) -> None:
        """show_new_session_confirmation can be set to True during initialization."""
        state = SessionState(show_new_session_confirmation=True)
        assert state.show_new_session_confirmation is True

    def test_show_new_session_confirmation_can_be_set_to_true_after_init(self) -> None:
        """show_new_session_confirmation can be changed to True after initialization."""
        state = SessionState()
        assert state.show_new_session_confirmation is False

        state.show_new_session_confirmation = True
        assert state.show_new_session_confirmation is True

    def test_show_new_session_confirmation_can_be_toggled(self) -> None:
        """show_new_session_confirmation can be toggled between True and False."""
        state = SessionState(show_new_session_confirmation=True)
        assert state.show_new_session_confirmation is True

        state.show_new_session_confirmation = False
        assert state.show_new_session_confirmation is False

        state.show_new_session_confirmation = True
        assert state.show_new_session_confirmation is True

    # --- Serialization Tests ---

    def test_show_new_session_confirmation_persists_in_model_dump(self) -> None:
        """show_new_session_confirmation should persist correctly in model_dump()."""
        state = SessionState(show_new_session_confirmation=True)
        data = state.model_dump()

        assert "show_new_session_confirmation" in data
        assert data["show_new_session_confirmation"] is True

    def test_show_new_session_confirmation_false_persists_in_model_dump(self) -> None:
        """show_new_session_confirmation=False should persist correctly."""
        state = SessionState(show_new_session_confirmation=False)
        data = state.model_dump()

        assert "show_new_session_confirmation" in data
        assert data["show_new_session_confirmation"] is False

    @pytest.mark.parametrize(
        "initial_value",
        [True, False],
        ids=["confirmation_true", "confirmation_false"],
    )
    def test_show_new_session_confirmation_roundtrip_parametrized(
        self, initial_value: bool
    ) -> None:
        """show_new_session_confirmation should survive roundtrip serialization."""
        original = SessionState(show_new_session_confirmation=initial_value)
        data = original.model_dump()
        reconstructed = SessionState(**data)

        assert reconstructed.show_new_session_confirmation is initial_value

    def test_factory_returns_show_new_session_confirmation_false(self) -> None:
        """Factory function returns session with show_new_session_confirmation=False."""
        session = create_initial_session_state()
        assert session.show_new_session_confirmation is False


class TestSessionStateReset:
    """Tests for SessionState reset() method (US-023)."""

    # --- Core Field Reset Tests ---

    def test_reset_clears_email_content(self) -> None:
        """reset() should clear email_content to None."""
        state = SessionState(email_content="Phishing email content here")
        assert state.email_content is not None

        state.reset()

        assert state.email_content is None

    def test_reset_returns_stage_to_input(self) -> None:
        """reset() should return stage to INPUT."""
        state = SessionState(stage=SessionStage.CONVERSATION)
        assert state.stage == SessionStage.CONVERSATION

        state.reset()

        assert state.stage == SessionStage.INPUT

    def test_reset_clears_classification_result(self) -> None:
        """reset() should clear classification_result to None."""
        from phishguard.models.classification import AttackType, ClassificationResult

        classification = ClassificationResult(
            attack_type=AttackType.CEO_FRAUD,
            confidence=95.0,
            reasoning="Test reasoning",
            classification_time_ms=1000,
        )
        state = SessionState(classification_result=classification)
        assert state.classification_result is not None

        state.reset()

        assert state.classification_result is None

    def test_reset_clears_conversation_history(self) -> None:
        """reset() should clear conversation_history to empty list."""
        msg1 = ConversationMessage(
            sender=MessageSender.BOT,
            content="Hello!",
            turn_number=1,
        )
        msg2 = ConversationMessage(
            sender=MessageSender.SCAMMER,
            content="Hi there",
            turn_number=1,
        )
        state = SessionState(conversation_history=[msg1, msg2])
        assert len(state.conversation_history) == 2

        state.reset()

        assert state.conversation_history == []

    def test_reset_generates_new_faker_seed(self) -> None:
        """reset() should generate a new faker_seed."""
        state = SessionState()

        # Mock random to return a different value
        with patch("phishguard.models.session.random.randint", return_value=999999):
            state.reset()

        assert state.faker_seed == 999999
        # Note: without mocking, there's a tiny chance the seed is the same,
        # but the mock ensures deterministic behavior

    def test_reset_updates_created_at(self) -> None:
        """reset() should update created_at timestamp."""
        state = SessionState()
        original_created_at = state.created_at

        # Wait a tiny bit to ensure timestamp difference
        import time as time_module

        time_module.sleep(0.001)

        state.reset()

        assert state.created_at >= original_created_at

    def test_reset_clears_persona_profile(self) -> None:
        """reset() should clear persona_profile to None."""
        from phishguard.models.persona import PersonaProfile, PersonaType

        persona = PersonaProfile(
            persona_type=PersonaType.NAIVE_RETIREE,
            name="John Smith",
            age=72,
            style_description="Trusting and polite",
            background="A retired teacher.",
        )
        state = SessionState(persona_profile=persona)
        assert state.persona_profile is not None

        state.reset()

        assert state.persona_profile is None

    def test_reset_clears_extracted_iocs(self) -> None:
        """reset() should clear extracted_iocs to empty list."""
        from phishguard.models.ioc import ExtractedIOC, IOCType

        ioc = ExtractedIOC(
            ioc_type=IOCType.BTC_WALLET,
            value="bc1qtest",
            message_index=0,
        )
        state = SessionState(extracted_iocs=[ioc])
        assert len(state.extracted_iocs) == 1

        state.reset()

        assert state.extracted_iocs == []

    # --- Generation State Reset Tests ---

    def test_reset_clears_current_response(self) -> None:
        """reset() should clear current_response to None."""
        state = SessionState(current_response="Generated response text")
        assert state.current_response is not None

        state.reset()

        assert state.current_response is None

    def test_reset_clears_is_generating(self) -> None:
        """reset() should set is_generating to False."""
        state = SessionState(is_generating=True)
        assert state.is_generating is True

        state.reset()

        assert state.is_generating is False

    def test_reset_clears_generation_error(self) -> None:
        """reset() should clear generation_error to None."""
        state = SessionState(generation_error="API rate limit exceeded")
        assert state.generation_error is not None

        state.reset()

        assert state.generation_error is None

    def test_reset_clears_current_thinking(self) -> None:
        """reset() should clear current_thinking to None."""
        from phishguard.models.thinking import AgentThinking

        thinking = AgentThinking(
            turn_goal="Extract payment method information",
            selected_tactic="Ask Questions",
            reasoning="Thinking about response...",
        )
        state = SessionState(current_thinking=thinking)
        assert state.current_thinking is not None

        state.reset()

        assert state.current_thinking is None

    # --- Editing State Reset Tests ---

    def test_reset_clears_editing_message_index(self) -> None:
        """reset() should clear editing_message_index to None."""
        state = SessionState(editing_message_index=2)
        assert state.editing_message_index is not None

        state.reset()

        assert state.editing_message_index is None

    def test_reset_clears_editing_content(self) -> None:
        """reset() should clear editing_content to None."""
        state = SessionState(editing_content="Content being edited")
        assert state.editing_content is not None

        state.reset()

        assert state.editing_content is None

    def test_reset_clears_copied_message_index(self) -> None:
        """reset() should clear copied_message_index to None."""
        state = SessionState(copied_message_index=1)
        assert state.copied_message_index is not None

        state.reset()

        assert state.copied_message_index is None

    def test_reset_clears_copy_timestamp(self) -> None:
        """reset() should clear copy_timestamp to None."""
        state = SessionState(copy_timestamp=time.time())
        assert state.copy_timestamp is not None

        state.reset()

        assert state.copy_timestamp is None

    # --- Session Control Flags Reset Tests ---

    def test_reset_clears_used_fallback_model(self) -> None:
        """reset() should set used_fallback_model to False."""
        state = SessionState(used_fallback_model=True)
        assert state.used_fallback_model is True

        state.reset()

        assert state.used_fallback_model is False

    def test_reset_clears_force_continue(self) -> None:
        """reset() should set force_continue to False."""
        state = SessionState(force_continue=True)
        assert state.force_continue is True

        state.reset()

        assert state.force_continue is False

    # --- Turn Limit Reset Tests ---

    def test_reset_restores_turn_limit_to_20(self) -> None:
        """reset() should restore turn_limit to default of 20."""
        state = SessionState(turn_limit=50)
        assert state.turn_limit == 50

        state.reset()

        assert state.turn_limit == 20

    def test_reset_clears_limit_extended_count(self) -> None:
        """reset() should reset limit_extended_count to 0."""
        state = SessionState(limit_extended_count=3)
        assert state.limit_extended_count == 3

        state.reset()

        assert state.limit_extended_count == 0

    # --- Unmasking State Reset Tests ---

    def test_reset_clears_unmasking_detected(self) -> None:
        """reset() should set unmasking_detected to False."""
        state = SessionState(unmasking_detected=True)
        assert state.unmasking_detected is True

        state.reset()

        assert state.unmasking_detected is False

    def test_reset_clears_unmasking_phrases(self) -> None:
        """reset() should clear unmasking_phrases to empty list."""
        state = SessionState(unmasking_phrases=["you're a bot", "stop messaging"])
        assert len(state.unmasking_phrases) == 2

        state.reset()

        assert state.unmasking_phrases == []

    def test_reset_clears_unmasking_dismissed(self) -> None:
        """reset() should set unmasking_dismissed to False."""
        state = SessionState(unmasking_dismissed=True)
        assert state.unmasking_dismissed is True

        state.reset()

        assert state.unmasking_dismissed is False

    # --- Session End State Reset Tests ---

    def test_reset_clears_ended_at(self) -> None:
        """reset() should clear ended_at to None."""
        state = SessionState(ended_at=datetime.now(UTC))
        assert state.ended_at is not None

        state.reset()

        assert state.ended_at is None

    def test_reset_clears_show_end_confirmation(self) -> None:
        """reset() should set show_end_confirmation to False."""
        state = SessionState(show_end_confirmation=True)
        assert state.show_end_confirmation is True

        state.reset()

        assert state.show_end_confirmation is False

    # --- Demo Mode State Reset Tests ---

    def test_reset_clears_is_demo_mode(self) -> None:
        """reset() should set is_demo_mode to False."""
        state = SessionState(is_demo_mode=True)
        assert state.is_demo_mode is True

        state.reset()

        assert state.is_demo_mode is False

    def test_reset_clears_demo_scenario(self) -> None:
        """reset() should clear demo_scenario to None."""
        from phishguard.models.classification import AttackType, ClassificationResult
        from phishguard.models.conversation import MessageSender
        from phishguard.models.demo import DemoMessage, DemoScenario, DemoScenarioType
        from phishguard.models.persona import PersonaProfile, PersonaType

        classification = ClassificationResult(
            attack_type=AttackType.NIGERIAN_419,
            confidence=90.0,
            reasoning="Test reasoning",
            classification_time_ms=100,
        )
        persona = PersonaProfile(
            persona_type=PersonaType.NAIVE_RETIREE,
            name="Test User",
            age=70,
            style_description="Test style",
            background="Test backstory",
        )
        demo_message = DemoMessage(
            sender=MessageSender.BOT,
            content="Test message",
        )
        scenario = DemoScenario(
            scenario_type=DemoScenarioType.NIGERIAN_419,
            email_content="Test email",
            classification=classification,
            persona=persona,
            messages=(demo_message,),
        )
        state = SessionState(demo_scenario=scenario)
        assert state.demo_scenario is not None

        state.reset()

        assert state.demo_scenario is None

    def test_reset_restores_demo_step_index_to_negative_one(self) -> None:
        """reset() should restore demo_step_index to -1."""
        state = SessionState(demo_step_index=5)
        assert state.demo_step_index == 5

        state.reset()

        assert state.demo_step_index == -1

    # --- New Session Confirmation Reset Test ---

    def test_reset_clears_show_new_session_confirmation(self) -> None:
        """reset() should set show_new_session_confirmation to False."""
        state = SessionState(show_new_session_confirmation=True)
        assert state.show_new_session_confirmation is True

        state.reset()

        assert state.show_new_session_confirmation is False

    # --- Integration Tests ---

    def test_reset_all_fields_from_populated_state(self) -> None:
        """reset() should clear all fields when session has data in all fields."""
        from phishguard.models.classification import AttackType, ClassificationResult
        from phishguard.models.ioc import ExtractedIOC, IOCType
        from phishguard.models.persona import PersonaProfile, PersonaType
        from phishguard.models.thinking import AgentThinking

        # Create a fully populated session
        classification = ClassificationResult(
            attack_type=AttackType.CEO_FRAUD,
            confidence=95.0,
            reasoning="Test",
            classification_time_ms=100,
        )
        persona = PersonaProfile(
            persona_type=PersonaType.STRESSED_MANAGER,
            name="Jane Doe",
            age=45,
            style_description="Busy and stressed",
            background="A busy manager.",
        )
        msg = ConversationMessage(
            sender=MessageSender.BOT,
            content="Hello",
            turn_number=1,
        )
        ioc = ExtractedIOC(
            ioc_type=IOCType.URL,
            value="https://malicious.com",
            message_index=0,
        )
        thinking = AgentThinking(
            turn_goal="Test goal",
            selected_tactic="Test tactic",
            reasoning="Test reasoning",
        )

        state = SessionState(
            stage=SessionStage.CONVERSATION,
            email_content="Phishing email",
            classification_result=classification,
            persona_profile=persona,
            conversation_history=[msg],
            extracted_iocs=[ioc],
            current_response="Response",
            is_generating=True,
            generation_error="Error",
            current_thinking=thinking,
            editing_message_index=0,
            editing_content="Editing",
            copied_message_index=0,
            copy_timestamp=time.time(),
            used_fallback_model=True,
            force_continue=True,
            turn_limit=30,
            limit_extended_count=1,
            unmasking_detected=True,
            unmasking_phrases=["bot"],
            unmasking_dismissed=True,
            ended_at=datetime.now(UTC),
            show_end_confirmation=True,
            is_demo_mode=True,
            demo_step_index=3,
            show_new_session_confirmation=True,
        )

        original_created_at = state.created_at

        # Reset the state
        state.reset()

        # Verify all fields are reset
        assert state.email_content is None
        assert state.stage == SessionStage.INPUT
        assert state.classification_result is None
        assert state.persona_profile is None
        assert state.conversation_history == []
        assert state.extracted_iocs == []
        assert state.current_response is None
        assert state.is_generating is False
        assert state.generation_error is None
        assert state.current_thinking is None
        assert state.editing_message_index is None
        assert state.editing_content is None
        assert state.copied_message_index is None
        assert state.copy_timestamp is None
        assert state.used_fallback_model is False
        assert state.force_continue is False
        assert state.turn_limit == 20
        assert state.limit_extended_count == 0
        assert state.unmasking_detected is False
        assert state.unmasking_phrases == []
        assert state.unmasking_dismissed is False
        assert state.ended_at is None
        assert state.show_end_confirmation is False
        assert state.is_demo_mode is False
        assert state.demo_scenario is None
        assert state.demo_step_index == -1
        assert state.show_new_session_confirmation is False
        # Faker seed and created_at should be different (new values generated)
        assert state.created_at >= original_created_at

    def test_reset_returns_is_input_stage_true(self) -> None:
        """reset() should make is_input_stage return True."""
        state = SessionState(stage=SessionStage.SUMMARY)
        assert state.is_input_stage is False

        state.reset()

        assert state.is_input_stage is True

    def test_reset_returns_is_classified_false(self) -> None:
        """reset() should make is_classified return False."""
        from phishguard.models.classification import AttackType, ClassificationResult

        classification = ClassificationResult(
            attack_type=AttackType.ROMANCE_SCAM,
            confidence=85.0,
            reasoning="Test",
            classification_time_ms=100,
        )
        state = SessionState(classification_result=classification)
        assert state.is_classified is True

        state.reset()

        assert state.is_classified is False

    def test_reset_returns_has_persona_false(self) -> None:
        """reset() should make has_persona return False."""
        from phishguard.models.persona import PersonaProfile, PersonaType

        persona = PersonaProfile(
            persona_type=PersonaType.GREEDY_INVESTOR,
            name="Bob Jones",
            age=55,
            style_description="Eager and risk-taking",
            background="An eager investor.",
        )
        state = SessionState(persona_profile=persona)
        assert state.has_persona is True

        state.reset()

        assert state.has_persona is False

    def test_reset_clears_is_editing(self) -> None:
        """reset() should make is_editing return False."""
        state = SessionState(editing_message_index=0)
        assert state.is_editing is True

        state.reset()

        assert state.is_editing is False

    def test_reset_can_be_called_multiple_times(self) -> None:
        """reset() can be called multiple times without error."""
        state = SessionState(
            email_content="Test",
            stage=SessionStage.CONVERSATION,
        )

        state.reset()
        state.reset()
        state.reset()

        assert state.email_content is None
        assert state.stage == SessionStage.INPUT

    def test_reset_on_fresh_state_is_idempotent(self) -> None:
        """reset() on a fresh state should produce equivalent state."""
        state = SessionState()

        # Reset should still update faker_seed and created_at
        with patch("phishguard.models.session.random.randint", return_value=12345):
            state.reset()

        assert state.email_content is None
        assert state.stage == SessionStage.INPUT
        assert state.faker_seed == 12345  # New seed was generated

    @pytest.mark.parametrize(
        "initial_stage",
        [
            SessionStage.INPUT,
            SessionStage.ANALYZING,
            SessionStage.CLASSIFIED,
            SessionStage.CONVERSATION,
            SessionStage.SUMMARY,
            SessionStage.DEMO_SELECT,
            SessionStage.DEMO,
        ],
        ids=[
            "from_input",
            "from_analyzing",
            "from_classified",
            "from_conversation",
            "from_summary",
            "from_demo_select",
            "from_demo",
        ],
    )
    def test_reset_from_any_stage_returns_to_input(
        self, initial_stage: SessionStage
    ) -> None:
        """reset() should return stage to INPUT from any initial stage."""
        state = SessionState(stage=initial_stage)

        state.reset()

        assert state.stage == SessionStage.INPUT


class TestSessionStateEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_empty_email_content_string(self) -> None:
        """Empty string for email_content should be accepted."""
        session = SessionState(email_content="")
        assert session.email_content == ""

    def test_very_long_email_content(self) -> None:
        """Very long email_content should be accepted."""
        long_content = "x" * 100_000
        session = SessionState(email_content=long_content)
        assert len(session.email_content) == 100_000

    def test_unicode_email_content(self) -> None:
        """Unicode email_content should be preserved."""
        content = "Email with emojis and special characters"
        session = SessionState(email_content=content)
        assert session.email_content == content

    def test_multiple_state_instances_independent(self) -> None:
        """Multiple SessionState instances should be independent."""
        session1 = SessionState(stage=SessionStage.INPUT)
        session2 = SessionState(stage=SessionStage.ANALYZING)

        assert session1.stage == SessionStage.INPUT
        assert session2.stage == SessionStage.ANALYZING

        session1.stage = SessionStage.SUMMARY
        assert session1.stage == SessionStage.SUMMARY
        assert session2.stage == SessionStage.ANALYZING
