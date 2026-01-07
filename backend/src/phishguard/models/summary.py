"""Session summary models for PhishGuard.

This module contains Pydantic models for representing session summaries
including metrics, IOCs, and safety scores for end-of-session reports.
Requirements: US-018
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field


class IOCSummary(BaseModel):
    """Summary of a single IOC for the session summary.

    Attributes:
        id: Unique identifier for the IOC.
        ioc_type: Type of IOC (btc_wallet, iban, phone, url).
        value: The extracted IOC value.
        is_high_value: Whether this is a high-value IOC.
        timestamp: When the IOC was extracted.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., description="IOC unique identifier.")
    ioc_type: str = Field(..., description="Type of IOC.")
    value: str = Field(..., description="The extracted value.")
    is_high_value: bool = Field(..., description="Whether high-value (financial).")
    timestamp: datetime = Field(..., description="Extraction timestamp.")


class SessionSummary(BaseModel):
    """Summary of a completed PhishGuard session.

    This model encapsulates all data needed for the session summary report
    as defined in US-018.

    Attributes:
        session_id: Unique identifier for the session.
        exchange_count: Number of message exchanges in the conversation.
        session_start: When the session was created.
        session_end: When the session was ended.
        attack_type: The detected attack type from classification.
        attack_type_display: Human-readable attack type name.
        attack_confidence: Confidence percentage of the classification.
        iocs: All IOCs extracted during the session.
        total_responses: Total number of bot responses generated.
        safe_responses: Number of responses that passed safety validation.
    """

    model_config = ConfigDict(
        frozen=True,
        validate_assignment=True,
    )

    session_id: str = Field(
        ...,
        description="Unique identifier for the session.",
    )
    exchange_count: int = Field(
        ...,
        description="Number of message exchanges in the conversation.",
        ge=0,
    )
    session_start: datetime = Field(
        ...,
        description="Timestamp when the session was created.",
    )
    session_end: datetime = Field(
        ...,
        description="Timestamp when the session was ended.",
    )
    attack_type: str = Field(
        ...,
        description="The detected attack type from classification.",
    )
    attack_type_display: str = Field(
        ...,
        description="Human-readable attack type name.",
    )
    attack_confidence: float = Field(
        ...,
        description="Confidence percentage of the classification.",
        ge=0.0,
        le=100.0,
    )
    iocs: list[IOCSummary] = Field(
        default_factory=list,
        description="All IOCs extracted during the session.",
    )
    total_responses: int = Field(
        0,
        description="Total number of bot responses generated.",
        ge=0,
    )
    safe_responses: int = Field(
        0,
        description="Number of responses that passed safety validation on first try.",
        ge=0,
    )

    @computed_field
    @property
    def duration_seconds(self) -> float:
        """Calculate session duration in seconds.

        Returns:
            Duration of the session in seconds.
        """
        delta = self.session_end - self.session_start
        return delta.total_seconds()

    @computed_field
    @property
    def formatted_duration(self) -> str:
        """Get human-readable duration string.

        Returns:
            Duration formatted as "Xm Ys" or "Xs" for short sessions.
        """
        total_seconds = int(self.duration_seconds)
        minutes = total_seconds // 60
        seconds = total_seconds % 60

        if minutes > 0:
            return f"{minutes}m {seconds}s"
        return f"{seconds}s"

    @computed_field
    @property
    def high_value_ioc_count(self) -> int:
        """Count of high-value IOCs (BTC wallets, IBANs).

        Returns:
            Number of high-value IOCs extracted.
        """
        return sum(1 for ioc in self.iocs if ioc.is_high_value)

    @computed_field
    @property
    def safety_score(self) -> float:
        """Calculate the safety score as percentage of safe responses.

        Safety Score = (safe_responses / total_responses) * 100
        Returns 100.0 if no responses were generated.

        Returns:
            Safety score as percentage (0-100).
        """
        if self.total_responses == 0:
            return 100.0
        return round((self.safe_responses / self.total_responses) * 100.0, 1)

    @computed_field
    @property
    def formatted_safety_score(self) -> str:
        """Get formatted safety score string.

        Returns:
            Safety score formatted as "X.X%".
        """
        return f"{self.safety_score:.1f}%"

    @property
    def ioc_count(self) -> int:
        """Total number of IOCs extracted.

        Returns:
            Total IOC count.
        """
        return len(self.iocs)
