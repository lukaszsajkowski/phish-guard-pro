"""Demo scenario models for pre-loaded demonstration scenarios.

This module contains Pydantic models for representing demo scenarios
that can be browsed step-by-step without making API calls (US-019).
"""

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, computed_field

from phishguard.models.classification import AttackType, ClassificationResult
from phishguard.models.conversation import MessageSender
from phishguard.models.ioc import ExtractedIOC
from phishguard.models.persona import PersonaProfile
from phishguard.models.thinking import AgentThinking


class DemoScenarioType(str, Enum):
    """Available demo scenario types.

    These correspond to the most common phishing attack types
    that are used for demonstration purposes (FR-034).

    Attributes:
        NIGERIAN_419: Classic advance-fee fraud scenario.
        CEO_FRAUD: Business email compromise scenario.
        CRYPTO_INVESTMENT: Cryptocurrency scam scenario.
    """

    NIGERIAN_419 = "nigerian_419"
    """Classic Nigerian 419 advance-fee fraud demonstration."""

    CEO_FRAUD = "ceo_fraud"
    """CEO fraud / business email compromise demonstration."""

    CRYPTO_INVESTMENT = "crypto_investment"
    """Cryptocurrency investment scam demonstration."""

    @property
    def display_name(self) -> str:
        """Get human-readable name for the scenario type."""
        names = {
            DemoScenarioType.NIGERIAN_419: "Nigerian 419 Scam",
            DemoScenarioType.CEO_FRAUD: "CEO Fraud",
            DemoScenarioType.CRYPTO_INVESTMENT: "Crypto Investment Scam",
        }
        return names.get(self, self.value)

    @property
    def description(self) -> str:
        """Get a brief description of the scenario."""
        descriptions = {
            DemoScenarioType.NIGERIAN_419: (
                "A classic advance-fee fraud where a supposed foreign "
                "dignitary needs help transferring millions."
            ),
            DemoScenarioType.CEO_FRAUD: (
                "A business email compromise where the 'CEO' urgently "
                "requests a wire transfer for a confidential deal."
            ),
            DemoScenarioType.CRYPTO_INVESTMENT: (
                "A cryptocurrency investment scam promising guaranteed "
                "high returns with a 'revolutionary trading bot'."
            ),
        }
        return descriptions.get(self, "")

    @property
    def icon(self) -> str:
        """Get icon for the scenario type."""
        icons = {
            DemoScenarioType.NIGERIAN_419: "\U0001f4b0",  # Money bag
            DemoScenarioType.CEO_FRAUD: "\U0001f454",  # Necktie (business)
            DemoScenarioType.CRYPTO_INVESTMENT: "\U000020bf",  # Bitcoin
        }
        return icons.get(self, "\U0001f4e7")  # Envelope default


class DemoMessage(BaseModel):
    """A single message in a demo scenario.

    Represents one exchange in the demo conversation, including
    the sender, content, and optional agent thinking for bot messages.

    Attributes:
        sender: Who sent the message (BOT or SCAMMER).
        content: The message content.
        thinking: Agent thinking for bot messages (optional).
        iocs_in_message: IOCs that should be extracted from this message.
    """

    model_config = ConfigDict(
        frozen=True,
        validate_assignment=True,
    )

    sender: MessageSender = Field(
        ...,
        description="Who sent this message.",
    )
    content: str = Field(
        ...,
        description="The message content.",
        min_length=1,
    )
    thinking: AgentThinking | None = Field(
        default=None,
        description="Agent thinking for bot messages.",
    )
    iocs_in_message: tuple[ExtractedIOC, ...] = Field(
        default_factory=tuple,
        description="IOCs that should be extracted when this message is shown.",
    )

    @property
    def is_bot_message(self) -> bool:
        """Check if this is a bot message."""
        return self.sender == MessageSender.BOT

    @property
    def is_scammer_message(self) -> bool:
        """Check if this is a scammer message."""
        return self.sender == MessageSender.SCAMMER


class DemoScenario(BaseModel):
    """A complete demo scenario for step-by-step browsing.

    Contains all pre-defined data for a demonstration scenario,
    including the phishing email, classification, persona, and
    all conversation exchanges.

    Attributes:
        scenario_type: The type of demo scenario.
        email_content: The initial phishing email content.
        classification: Pre-defined classification result.
        persona: Pre-defined victim persona.
        messages: Sequence of demo messages to display.
        created_at: Timestamp for the demo session.
    """

    model_config = ConfigDict(
        frozen=True,
        validate_assignment=True,
    )

    scenario_type: DemoScenarioType = Field(
        ...,
        description="The type of demo scenario.",
    )
    email_content: str = Field(
        ...,
        description="The initial phishing email content.",
        min_length=1,
    )
    classification: ClassificationResult = Field(
        ...,
        description="Pre-defined classification result for the email.",
    )
    persona: PersonaProfile = Field(
        ...,
        description="Pre-defined victim persona for the conversation.",
    )
    messages: tuple[DemoMessage, ...] = Field(
        ...,
        description="Sequence of demo messages in order.",
        min_length=1,
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when the demo scenario was created.",
    )

    @computed_field
    @property
    def total_steps(self) -> int:
        """Get the total number of steps in the demo.

        Each message is one step.

        Returns:
            Total number of messages in the scenario.
        """
        return len(self.messages)

    @computed_field
    @property
    def total_iocs(self) -> int:
        """Get the total number of IOCs in the scenario.

        Returns:
            Total count of IOCs across all messages.
        """
        return sum(len(msg.iocs_in_message) for msg in self.messages)

    def get_messages_up_to_step(self, step: int) -> tuple[DemoMessage, ...]:
        """Get all messages up to and including the given step.

        Args:
            step: The current step index (0-based).

        Returns:
            Tuple of messages from step 0 to step (inclusive).
        """
        return self.messages[: step + 1]

    def get_iocs_up_to_step(self, step: int) -> list[ExtractedIOC]:
        """Get all IOCs extracted up to and including the given step.

        Args:
            step: The current step index (0-based).

        Returns:
            List of all IOCs from messages up to the given step.
        """
        iocs: list[ExtractedIOC] = []
        for msg in self.messages[: step + 1]:
            iocs.extend(msg.iocs_in_message)
        return iocs

    def get_current_thinking(self, step: int) -> AgentThinking | None:
        """Get the agent thinking for the current step if it's a bot message.

        Args:
            step: The current step index (0-based).

        Returns:
            AgentThinking if current message is from bot and has thinking,
            None otherwise.
        """
        if step < 0 or step >= len(self.messages):
            return None
        msg = self.messages[step]
        return msg.thinking if msg.is_bot_message else None

    def can_advance(self, current_step: int) -> bool:
        """Check if there's a next step available.

        Args:
            current_step: The current step index (0-based).

        Returns:
            True if there's another step after current_step.
        """
        return current_step < len(self.messages) - 1

    @property
    def attack_type(self) -> AttackType:
        """Get the attack type from the classification."""
        return self.classification.attack_type
