"""Classification models for phishing email analysis.

This module contains Pydantic models and enums for representing
the results of phishing email classification by the Profiler Agent.
"""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from phishguard.models.persona import PersonaProfile


class AttackType(str, Enum):
    """Categories of phishing attacks that PhishGuard can identify.

    The Profiler Agent classifies incoming emails into one of these
    categories to determine the appropriate persona and conversation
    strategy for engagement.

    Attributes:
        NIGERIAN_419: Classic advance-fee fraud scheme.
        CEO_FRAUD: Business email compromise targeting executives.
        FAKE_INVOICE: Fraudulent invoice or payment requests.
        ROMANCE_SCAM: Emotional manipulation for financial gain.
        TECH_SUPPORT: Fake technical support scams.
        LOTTERY_PRIZE: Fake lottery or prize notifications.
        CRYPTO_INVESTMENT: Cryptocurrency investment fraud.
        DELIVERY_SCAM: Fake delivery or shipping notifications.
        NOT_PHISHING: Content determined to be legitimate.
    """

    NIGERIAN_419 = "nigerian_419"
    """Classic advance-fee fraud scheme (419 scam)."""

    CEO_FRAUD = "ceo_fraud"
    """Business email compromise impersonating executives."""

    FAKE_INVOICE = "fake_invoice"
    """Fraudulent invoice or payment request."""

    ROMANCE_SCAM = "romance_scam"
    """Emotional manipulation scam for financial gain."""

    TECH_SUPPORT = "tech_support"
    """Fake technical support or security alert scam."""

    LOTTERY_PRIZE = "lottery_prize"
    """Fake lottery win or prize notification."""

    CRYPTO_INVESTMENT = "crypto_investment"
    """Cryptocurrency or investment fraud scheme."""

    DELIVERY_SCAM = "delivery_scam"
    """Fake delivery, shipping, or customs notification."""

    NOT_PHISHING = "not_phishing"
    """Content determined to be legitimate (not a phishing attempt)."""

    @property
    def display_name(self) -> str:
        """Return a human-readable display name for the attack type.

        Returns:
            A formatted string suitable for UI display.

        Example:
            >>> AttackType.NIGERIAN_419.display_name
            'Nigerian 419'
            >>> AttackType.CEO_FRAUD.display_name
            'CEO Fraud'
        """
        display_names: dict[AttackType, str] = {
            AttackType.NIGERIAN_419: "Nigerian 419",
            AttackType.CEO_FRAUD: "CEO Fraud",
            AttackType.FAKE_INVOICE: "Fake Invoice",
            AttackType.ROMANCE_SCAM: "Romance Scam",
            AttackType.TECH_SUPPORT: "Tech Support",
            AttackType.LOTTERY_PRIZE: "Lottery/Prize",
            AttackType.CRYPTO_INVESTMENT: "Crypto Investment",
            AttackType.DELIVERY_SCAM: "Delivery Scam",
            AttackType.NOT_PHISHING: "Not Phishing",
        }
        return display_names[self]


class ClassificationResult(BaseModel):
    """Result of phishing email classification by the Profiler Agent.

    This model encapsulates the output of the classification process,
    including the detected attack type, confidence level, reasoning,
    performance metrics, and the suggested victim persona.

    Attributes:
        attack_type: The identified category of phishing attack.
        confidence: Classification confidence as a percentage (0-100).
        reasoning: Human-readable explanation for the classification.
        classification_time_ms: Time taken to classify in milliseconds.
        persona: The suggested victim persona for engagement (optional).
        used_fallback_model: Whether fallback LLM was used (US-023).

    Example:
        >>> result = ClassificationResult(
        ...     attack_type=AttackType.NIGERIAN_419,
        ...     confidence=95.5,
        ...     reasoning="Email contains classic 419 indicators: "
        ...               "foreign prince, large sum of money, advance fee request.",
        ...     classification_time_ms=1250
        ... )
        >>> result.attack_type.display_name
        'Nigerian 419'
    """

    model_config = ConfigDict(
        frozen=True,
        validate_assignment=True,
        use_enum_values=False,
    )

    attack_type: AttackType = Field(
        ...,
        description="The identified category of phishing attack.",
    )
    confidence: float = Field(
        ...,
        description="Classification confidence as a percentage (0-100).",
        ge=0.0,
        le=100.0,
        json_schema_extra={
            "examples": [85.5, 95.0, 72.3],
        },
    )
    reasoning: str = Field(
        ...,
        description="Human-readable explanation for the classification decision.",
        min_length=1,
        json_schema_extra={
            "examples": [
                "Email contains classic 419 indicators: foreign dignitary, "
                "large inheritance, request for personal banking details.",
                "Message impersonates CEO requesting urgent wire transfer "
                "to unfamiliar account with pressure tactics.",
            ],
        },
    )
    classification_time_ms: int = Field(
        ...,
        description="Time taken to perform classification in milliseconds.",
        ge=0,
        json_schema_extra={
            "examples": [1250, 3500, 890],
        },
    )
    persona: PersonaProfile | None = Field(
        default=None,
        description="The suggested victim persona for engagement.",
    )
    session_id: str | None = Field(
        default=None,
        description="The database session ID for this classification.",
    )
    used_fallback_model: bool = Field(
        default=False,
        description="Whether the fallback LLM model was used (US-023).",
    )

    @field_validator("confidence", mode="after")
    @classmethod
    def validate_confidence_precision(cls, value: float) -> float:
        """Round confidence to reasonable precision.

        Args:
            value: The confidence value after initial validation.

        Returns:
            Confidence rounded to 2 decimal places.
        """
        return round(value, 2)

    @property
    def is_phishing(self) -> bool:
        """Check if the classification indicates a phishing attempt.

        Returns:
            True if the email is classified as phishing, False if legitimate.
        """
        return self.attack_type != AttackType.NOT_PHISHING

    @property
    def is_high_confidence(self) -> bool:
        """Check if the classification has high confidence (>=80%).

        Returns:
            True if confidence is 80% or higher, False otherwise.
        """
        return self.confidence >= 80.0

    @property
    def is_low_confidence_not_phishing(self) -> bool:
        """Check if classified as NOT_PHISHING with low confidence.

        This property is used by the UI to determine when to show a warning
        that the classification may be uncertain and manual review is recommended.

        Returns:
            True if attack_type is NOT_PHISHING and confidence is below 30%,
            False otherwise (including all phishing attack types).
        """
        return self.attack_type == AttackType.NOT_PHISHING and self.confidence < 30.0
