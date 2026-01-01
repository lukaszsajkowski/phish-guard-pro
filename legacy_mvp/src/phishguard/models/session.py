"""Session state models for managing Streamlit application flow.

This module provides data models for tracking the current stage of the
PhishGuard application and persisting session data across Streamlit reruns.
"""

from __future__ import annotations

import random
import time
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from phishguard.models.classification import ClassificationResult
from phishguard.models.conversation import ConversationMessage
from phishguard.models.demo import DemoScenario
from phishguard.models.ioc import ExtractedIOC
from phishguard.models.persona import PersonaProfile
from phishguard.models.risk import RiskScore, calculate_risk_score
from phishguard.models.thinking import AgentThinking

if TYPE_CHECKING:
    from phishguard.models.summary import SessionSummary


class SessionStage(str, Enum):
    """Application flow stages for the PhishGuard session.

    The session progresses through these stages linearly:
    INPUT -> ANALYZING -> CLASSIFIED -> CONVERSATION -> SUMMARY

    Demo mode has its own flow:
    INPUT -> DEMO_SELECT -> DEMO
    """

    INPUT = "input"
    """Initial stage where user pastes suspicious email content."""

    ANALYZING = "analyzing"
    """Processing stage while agents classify the email."""

    CLASSIFIED = "classified"
    """Email has been classified, ready to start conversation."""

    CONVERSATION = "conversation"
    """Active conversation with the scammer."""

    SUMMARY = "summary"
    """Session complete, displaying extracted IOCs and summary."""

    DEMO_SELECT = "demo_select"
    """Demo mode: selecting which scenario to view."""

    DEMO = "demo"
    """Demo mode: browsing a pre-loaded scenario step by step."""


class SessionState(BaseModel):
    """Manages the application flow state for a PhishGuard session.

    This model persists across Streamlit reruns and tracks which stage
    the user is currently in, along with the sanitized email content
    being analyzed.

    Attributes:
        stage: Current stage in the application flow.
        email_content: The sanitized email content being analyzed, if any.
        classification_result: Result from Profiler Agent classification.
        persona_profile: The selected victim persona for conversation.
        faker_seed: Seed for Faker to ensure consistent persona generation.
        used_fallback_model: Whether the fallback LLM was used.
        force_continue: Whether user chose to continue with a non-phishing email.
        created_at: Timestamp when the session was created.
    """

    model_config = ConfigDict(
        frozen=False,
        validate_assignment=True,
        use_enum_values=False,
        arbitrary_types_allowed=True,
    )

    stage: SessionStage = Field(
        default=SessionStage.INPUT,
        description="Current stage in the application flow.",
    )
    email_content: str | None = Field(
        default=None,
        description="The sanitized email content being analyzed.",
    )
    classification_result: ClassificationResult | None = Field(
        default=None,
        description="Result from Profiler Agent classification.",
    )
    persona_profile: PersonaProfile | None = Field(
        default=None,
        description="The selected victim persona for conversation engagement.",
    )
    faker_seed: int = Field(
        default_factory=lambda: random.randint(0, 2**31 - 1),
        description="Seed for Faker library to ensure consistent persona names.",
    )
    used_fallback_model: bool = Field(
        default=False,
        description="Whether the fallback LLM model was used for classification.",
    )
    force_continue: bool = Field(
        default=False,
        description="True when user clicks 'Continue anyway' for non-phishing.",
    )
    conversation_history: list[ConversationMessage] = Field(
        default_factory=list,
        description="List of all messages in the conversation.",
    )
    current_response: str | None = Field(
        default=None,
        description="The most recently generated bot response.",
    )
    is_generating: bool = Field(
        default=False,
        description="True while a response is being generated.",
    )
    generation_error: str | None = Field(
        default=None,
        description="Error message from the last generation attempt, if any.",
    )
    current_thinking: AgentThinking | None = Field(
        default=None,
        description="The most recent agent thinking/reasoning for display in UI.",
    )
    editing_message_index: int | None = Field(
        default=None,
        description=(
            "Index of the message in conversation_history being edited, "
            "or None if not editing."
        ),
    )
    editing_content: str | None = Field(
        default=None,
        description="Temporary content storage for the message being edited.",
    )
    copied_message_index: int | None = Field(
        default=None,
        description="Index of the message that was just copied to clipboard.",
    )
    copy_timestamp: float | None = Field(
        default=None,
        description="Unix timestamp when the copy occurred, for auto-dismiss timing.",
    )
    extracted_iocs: list[ExtractedIOC] = Field(
        default_factory=list,
        description="List of IOCs extracted from scammer messages.",
    )
    # Session limit fields (US-013)
    turn_limit: int = Field(
        default=20,
        description="Soft limit on conversation turns (default 20 per PRD FR-025).",
        ge=1,
    )
    limit_extended_count: int = Field(
        default=0,
        description="Number of times the turn limit has been extended.",
        ge=0,
    )
    # Bot unmasking detection fields (US-014)
    unmasking_detected: bool = Field(
        default=False,
        description="True if scammer appears to have unmasked the bot.",
    )
    unmasking_phrases: list[str] = Field(
        default_factory=list,
        description="List of phrases that triggered unmasking detection.",
    )
    unmasking_dismissed: bool = Field(
        default=False,
        description="True if user dismissed unmasking warning with 'Continue anyway'.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when the session was created.",
    )
    # Session end fields (US-015, US-016)
    ended_at: datetime | None = Field(
        default=None,
        description="Timestamp when the session was ended.",
    )
    show_end_confirmation: bool = Field(
        default=False,
        description="True to show the end session confirmation modal.",
    )
    # Demo mode fields (US-019)
    is_demo_mode: bool = Field(
        default=False,
        description="True when in demo mode (browsing pre-loaded scenarios).",
    )
    demo_scenario: DemoScenario | None = Field(
        default=None,
        description="The currently loaded demo scenario, if any.",
    )
    demo_step_index: int = Field(
        default=-1,
        description="Current step index in demo mode (-1 = not started, 0+ = viewing).",
    )
    # New session confirmation (US-023)
    show_new_session_confirmation: bool = Field(
        default=False,
        description="True to show the new session confirmation modal.",
    )

    @property
    def is_input_stage(self) -> bool:
        """Check if the session is in the initial input stage.

        Returns:
            True if the session is in the INPUT stage, False otherwise.
        """
        return self.stage == SessionStage.INPUT

    @property
    def is_classified(self) -> bool:
        """Check if the email has been classified.

        Returns:
            True if classification_result is available, False otherwise.
        """
        return self.classification_result is not None

    @property
    def has_persona(self) -> bool:
        """Check if a persona has been selected for this session.

        Returns:
            True if persona_profile is available, False otherwise.
        """
        return self.persona_profile is not None

    @property
    def has_first_response(self) -> bool:
        """Check if the first response has been generated.

        Returns:
            True if at least one bot message exists in history.
        """
        return any(msg.is_bot_message for msg in self.conversation_history)

    @property
    def turn_count(self) -> int:
        """Get the current conversation turn number.

        A turn is counted when both bot and scammer have exchanged messages.
        The first response counts as turn 1.

        Returns:
            Current turn number (1-based).
        """
        bot_messages = sum(1 for msg in self.conversation_history if msg.is_bot_message)
        return max(1, bot_messages)

    @property
    def can_generate_response(self) -> bool:
        """Check if the system is ready to generate a response.

        Returns:
            True if classification and persona are ready and not currently generating.
        """
        return self.is_classified and self.has_persona and not self.is_generating

    @property
    def is_editing(self) -> bool:
        """Check if a message is currently being edited.

        Returns:
            True if a message is being edited, False otherwise.
        """
        return self.editing_message_index is not None

    @property
    def has_thinking(self) -> bool:
        """Check if agent thinking data is available.

        Returns:
            True if current_thinking is available, False otherwise.
        """
        return self.current_thinking is not None

    @property
    def awaiting_scammer_response(self) -> bool:
        """Check if the system is waiting for user to paste scammer response.

        The scammer response field should be visible when:
        - First bot response has been generated
        - Not currently generating a new response
        - The last message in history is from the bot

        Returns:
            True if awaiting scammer response, False otherwise.
        """
        if not self.has_first_response:
            return False
        if self.is_generating:
            return False
        if not self.conversation_history:
            return False
        # Last message should be from the bot
        return self.conversation_history[-1].is_bot_message

    @property
    def high_value_ioc_count(self) -> int:
        """Count of high-value IOCs (BTC wallets, IBANs).

        Returns:
            Number of high-value IOCs extracted.
        """
        return sum(1 for ioc in self.extracted_iocs if ioc.is_high_value)

    @property
    def is_at_limit(self) -> bool:
        """Check if the conversation has reached the turn limit.

        Returns:
            True if turn_count >= turn_limit, False otherwise.
        """
        return self.turn_count >= self.turn_limit

    @property
    def should_show_limit_warning(self) -> bool:
        """Check if the limit warning should be displayed.

        The warning is shown when the limit is reached and user hasn't
        yet chosen to extend or end the session.

        Returns:
            True if limit warning should be shown, False otherwise.
        """
        return self.is_at_limit and self.awaiting_scammer_response

    @property
    def should_show_unmasking_warning(self) -> bool:
        """Check if the unmasking warning should be displayed.

        The warning is shown when unmasking is detected and user hasn't
        dismissed it with 'Continue anyway'.

        Returns:
            True if unmasking warning should be shown, False otherwise.
        """
        return self.unmasking_detected and not self.unmasking_dismissed

    @property
    def turn_counter_color(self) -> str:
        """Get the color for the turn counter display.

        Per US-025:
        - Default color (no special marking) for turns 1-14
        - Yellow after turn 15
        - Red after turn 20

        Returns:
            Color name: 'default', 'yellow', or 'red'.
        """
        if self.turn_count >= 20:
            return "red"
        elif self.turn_count >= 15:
            return "yellow"
        return "default"

    @property
    def turn_counter_display(self) -> str:
        """Get the formatted turn counter string for display.

        Per US-025:
        - Format: "Turn X/20" for turns 1-20
        - Format: "Turn X/20+" for turns > 20

        Returns:
            Formatted turn counter string.
        """
        if self.turn_count > 20:
            return f"Turn {self.turn_count}/20+"
        return f"Turn {self.turn_count}/20"

    @property
    def risk_score(self) -> RiskScore:
        """Calculate the current risk score based on session data.

        The risk score is computed using attack confidence, IOC counts,
        and conversation engagement metrics.

        Returns:
            RiskScore with value 1-10, level, and contributing factors.
        """
        attack_confidence = (
            self.classification_result.confidence
            if self.classification_result
            else 0.0
        )

        return calculate_risk_score(
            attack_confidence=attack_confidence,
            ioc_count=len(self.extracted_iocs),
            high_value_ioc_count=self.high_value_ioc_count,
            turn_count=self.turn_count,
        )

    def add_iocs(self, iocs: list[ExtractedIOC]) -> None:
        """Add extracted IOCs to the session, avoiding duplicates.

        Args:
            iocs: List of IOCs to add.
        """
        existing_values = {ioc.value.lower() for ioc in self.extracted_iocs}
        for ioc in iocs:
            if ioc.value.lower() not in existing_values:
                self.extracted_iocs.append(ioc)
                existing_values.add(ioc.value.lower())

    def update_message_content(self, index: int, new_content: str) -> None:
        """Update a message's content in the conversation history.

        Since ConversationMessage is frozen, this creates a new message with
        updated content and replaces the old one in the history.

        Args:
            index: Index of the message to update.
            new_content: The new content for the message.

        Raises:
            IndexError: If index is out of range.
        """
        if index < 0 or index >= len(self.conversation_history):
            raise IndexError(f"Message index {index} out of range")

        old_message = self.conversation_history[index]
        # Create new message with updated content
        new_message = ConversationMessage(
            sender=old_message.sender,
            content=new_content,
            timestamp=old_message.timestamp,
            turn_number=old_message.turn_number,
        )
        # Replace in list
        self.conversation_history[index] = new_message

    def clear_editing_state(self) -> None:
        """Clear all editing-related state."""
        self.editing_message_index = None
        self.editing_content = None

    def should_show_copy_confirmation(self, index: int) -> bool:
        """Check if copy confirmation should be shown for a message.

        Returns True if:
        - This message was just copied (index matches)
        - Less than 2 seconds have passed since copy

        Args:
            index: The message index to check.

        Returns:
            True if confirmation should be displayed, False otherwise.
        """
        if self.copied_message_index != index:
            return False
        if self.copy_timestamp is None:
            return False
        return (time.time() - self.copy_timestamp) < 2.0

    def clear_copy_state(self) -> None:
        """Clear all copy-related state."""
        self.copied_message_index = None
        self.copy_timestamp = None

    def extend_limit(self, additional_turns: int = 10) -> None:
        """Extend the conversation turn limit.

        Per US-013, clicking "Continue (+10 turns)" extends the limit.

        Args:
            additional_turns: Number of turns to add (default 10).
        """
        self.turn_limit += additional_turns
        self.limit_extended_count += 1

    def set_unmasking_detected(self, phrases: list[str]) -> None:
        """Mark the session as having detected bot unmasking.

        Args:
            phrases: List of phrases that triggered unmasking detection.
        """
        self.unmasking_detected = True
        self.unmasking_phrases = phrases

    def dismiss_unmasking_warning(self) -> None:
        """Dismiss the unmasking warning (user clicked 'Continue anyway')."""
        self.unmasking_dismissed = True

    def clear_unmasking_state(self) -> None:
        """Clear all unmasking-related state."""
        self.unmasking_detected = False
        self.unmasking_phrases = []
        self.unmasking_dismissed = False

    def end_session(self) -> None:
        """End the session and set the ended_at timestamp.

        This method is called when the user confirms ending the session.
        """
        self.ended_at = datetime.now(UTC)
        self.show_end_confirmation = False
        self.stage = SessionStage.SUMMARY

    def generate_summary(self) -> SessionSummary:
        """Generate a summary of the completed session.

        This method creates a SessionSummary with all metrics needed
        for the session report (US-016).

        Returns:
            SessionSummary with session metrics, IOCs, and safety score.

        Raises:
            ValueError: If session has not been classified or has no end time.
        """
        # Import here to avoid circular import
        from phishguard.models.summary import SessionSummary

        if self.classification_result is None:
            raise ValueError("Cannot generate summary: session not classified")

        # Use current time if ended_at not set (shouldn't happen normally)
        end_time = self.ended_at or datetime.now(UTC)

        # Count bot messages for exchange count
        bot_message_count = sum(
            1 for msg in self.conversation_history if msg.is_bot_message
        )

        # All responses that made it to history passed safety validation
        # (Conversation Agent regenerates on unsafe content)
        total_responses = bot_message_count
        safe_responses = bot_message_count  # All responses in history are safe

        return SessionSummary(
            exchange_count=bot_message_count,
            session_start=self.created_at,
            session_end=end_time,
            attack_type=self.classification_result.attack_type,
            attack_confidence=self.classification_result.confidence,
            iocs=tuple(self.extracted_iocs),
            total_responses=total_responses,
            safe_responses=safe_responses,
        )

    # Demo mode methods (US-019)
    def start_demo(self, scenario: DemoScenario) -> None:
        """Start demo mode with the given scenario.

        Sets up the session for demo viewing by loading the scenario
        and transitioning to the DEMO stage.

        Args:
            scenario: The demo scenario to load.
        """
        self.is_demo_mode = True
        self.demo_scenario = scenario
        self.demo_step_index = -1  # Not started yet
        self.stage = SessionStage.DEMO

        # Pre-populate session data from the scenario
        self.email_content = scenario.email_content
        self.classification_result = scenario.classification
        self.persona_profile = scenario.persona

    def advance_demo_step(self) -> bool:
        """Advance to the next step in the demo.

        Returns:
            True if advanced successfully, False if already at the end.
        """
        if not self.is_demo_mode or self.demo_scenario is None:
            return False

        if self.demo_step_index < self.demo_scenario.total_steps - 1:
            self.demo_step_index += 1

            # Update IOCs from the scenario up to current step
            self.extracted_iocs = list(
                self.demo_scenario.get_iocs_up_to_step(self.demo_step_index)
            )

            # Update current thinking if this is a bot message
            self.current_thinking = self.demo_scenario.get_current_thinking(
                self.demo_step_index
            )

            return True
        return False

    def can_advance_demo(self) -> bool:
        """Check if the demo can advance to the next step.

        Returns:
            True if there's a next step available.
        """
        if not self.is_demo_mode or self.demo_scenario is None:
            return False
        return self.demo_scenario.can_advance(self.demo_step_index)

    @property
    def demo_turn_count(self) -> int:
        """Get the current demo turn count for display.

        Returns:
            Number of complete exchanges shown so far (1-based).
        """
        if not self.is_demo_mode or self.demo_scenario is None:
            return 0
        # Count bot messages up to current step
        bot_count = sum(
            1
            for i, msg in enumerate(self.demo_scenario.messages)
            if i <= self.demo_step_index and msg.is_bot_message
        )
        return max(1, bot_count)

    @property
    def demo_total_steps(self) -> int:
        """Get the total number of steps in the current demo.

        Returns:
            Total steps if in demo mode, 0 otherwise.
        """
        if self.demo_scenario is None:
            return 0
        return self.demo_scenario.total_steps

    def exit_demo(self) -> None:
        """Exit demo mode and return to the start screen.

        Clears all demo-related state and resets the session.
        """
        self.is_demo_mode = False
        self.demo_scenario = None
        self.demo_step_index = -1
        self.stage = SessionStage.INPUT

        # Clear populated demo data
        self.email_content = None
        self.classification_result = None
        self.persona_profile = None
        self.extracted_iocs = []
        self.current_thinking = None

    def reset(self) -> None:
        """Reset all fields to their default values for a new session.

        This method is called when the user confirms starting a new session
        (US-023). It clears all session data and returns to the INPUT stage.
        """
        # Core session data
        self.email_content = None
        self.stage = SessionStage.INPUT
        self.classification_result = None
        self.persona_profile = None
        self.conversation_history = []
        self.extracted_iocs = []

        # Generation state
        self.current_response = None
        self.is_generating = False
        self.generation_error = None
        self.current_thinking = None

        # Editing state
        self.editing_message_index = None
        self.editing_content = None
        self.copied_message_index = None
        self.copy_timestamp = None

        # Session control flags
        self.used_fallback_model = False
        self.force_continue = False

        # Turn limit fields
        self.turn_limit = 20
        self.limit_extended_count = 0

        # Unmasking detection fields
        self.unmasking_detected = False
        self.unmasking_phrases = []
        self.unmasking_dismissed = False

        # Session end fields
        self.ended_at = None
        self.show_end_confirmation = False

        # Demo mode fields
        self.is_demo_mode = False
        self.demo_scenario = None
        self.demo_step_index = -1

        # New session confirmation
        self.show_new_session_confirmation = False

        # Generate new faker seed for fresh persona generation
        self.faker_seed = random.randint(0, 2**31 - 1)

        # Update created_at to mark new session start
        self.created_at = datetime.now(UTC)


def create_initial_session_state() -> SessionState:
    """Create a new session state with default values.

    This factory function provides a clean initial state for new
    PhishGuard sessions.

    Returns:
        A new SessionState instance in the INPUT stage.
    """
    return SessionState()
