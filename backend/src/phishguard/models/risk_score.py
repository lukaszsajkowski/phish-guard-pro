"""Enhanced Risk Score models for PhishGuard.

This module contains Pydantic models for the multi-dimensional
risk score system as defined in US-032.
"""

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RiskComponent(str, Enum):
    """The 6 components of the enhanced risk score.

    Each component contributes a weighted portion to the final
    risk score (1-10 scale).
    """

    ATTACK_SEVERITY = "attack_severity"
    """Attack type severity (25% weight). CEO Fraud/Crypto=4, Nigerian 419=3, etc."""

    IOC_QUALITY = "ioc_quality"
    """Quality of extracted IOCs (25% weight). BTC=3, IBAN=3, phone=2, URL=1."""

    IOC_QUANTITY = "ioc_quantity"
    """Number of IOCs extracted (15% weight). +0.5 per IOC, max 1.5 points."""

    SCAMMER_ENGAGEMENT = "scammer_engagement"
    """Scammer engagement level (15% weight). Based on response length/frequency."""

    URGENCY_TACTICS = "urgency_tactics"
    """Use of urgency/pressure tactics (10% weight). Keyword detection."""

    PERSONALIZATION = "personalization"
    """Personalization level (10% weight). Name usage, context references."""

    @property
    def weight(self) -> float:
        """Get the weight for this component."""
        weights = {
            RiskComponent.ATTACK_SEVERITY: 0.25,
            RiskComponent.IOC_QUALITY: 0.25,
            RiskComponent.IOC_QUANTITY: 0.15,
            RiskComponent.SCAMMER_ENGAGEMENT: 0.15,
            RiskComponent.URGENCY_TACTICS: 0.10,
            RiskComponent.PERSONALIZATION: 0.10,
        }
        return weights[self]

    @property
    def display_name(self) -> str:
        """Get human-readable display name."""
        names = {
            RiskComponent.ATTACK_SEVERITY: "Attack Severity",
            RiskComponent.IOC_QUALITY: "IOC Quality",
            RiskComponent.IOC_QUANTITY: "IOC Quantity",
            RiskComponent.SCAMMER_ENGAGEMENT: "Scammer Engagement",
            RiskComponent.URGENCY_TACTICS: "Urgency Tactics",
            RiskComponent.PERSONALIZATION: "Personalization",
        }
        return names[self]


class RiskLevel(str, Enum):
    """Risk level classification based on total score."""

    LOW = "low"
    """Score 1-3: Low risk."""

    MEDIUM = "medium"
    """Score 4-6: Medium risk."""

    HIGH = "high"
    """Score 7-10: High risk."""

    @classmethod
    def from_score(cls, score: float) -> "RiskLevel":
        """Determine risk level from numerical score."""
        if score <= 3:
            return cls.LOW
        if score <= 6:
            return cls.MEDIUM
        return cls.HIGH


class RiskComponentScore(BaseModel):
    """Score for a single risk component.

    Contains the raw score, weight, weighted contribution,
    and human-readable explanation.
    """

    model_config = ConfigDict(
        frozen=True,
        validate_assignment=True,
        use_enum_values=False,
    )

    component: RiskComponent = Field(
        ...,
        description="The risk component being scored.",
    )
    raw_score: float = Field(
        ...,
        description="Raw score for this component (0-10 scale).",
        ge=0.0,
        le=10.0,
    )
    weight: float = Field(
        ...,
        description="Weight of this component (0-1).",
        ge=0.0,
        le=1.0,
    )
    weighted_score: float = Field(
        ...,
        description="Weighted contribution to total score.",
        ge=0.0,
    )
    explanation: str = Field(
        ...,
        description="Human-readable explanation of the score.",
        min_length=1,
    )

    @property
    def percentage_contribution(self) -> float:
        """Get percentage contribution (weight as percentage)."""
        return self.weight * 100


class EnhancedRiskScore(BaseModel):
    """Complete enhanced risk score with all component breakdowns.

    The total score is calculated as a weighted sum of all components,
    normalized to a 1-10 scale.
    """

    model_config = ConfigDict(
        frozen=True,
        validate_assignment=True,
        use_enum_values=False,
    )

    total_score: float = Field(
        ...,
        description="Final risk score (1-10 scale).",
        ge=1.0,
        le=10.0,
    )
    risk_level: RiskLevel = Field(
        ...,
        description="Risk level classification (low/medium/high).",
    )
    components: list[RiskComponentScore] = Field(
        ...,
        description="Individual component scores and explanations.",
        min_length=6,
        max_length=6,
    )
    calculation_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this score was calculated.",
    )

    @model_validator(mode="after")
    def validate_all_components_present(self) -> "EnhancedRiskScore":
        """Ensure all 6 components are present."""
        component_types = {c.component for c in self.components}
        expected = set(RiskComponent)
        if component_types != expected:
            missing = expected - component_types
            raise ValueError(f"Missing risk components: {missing}")
        return self

    @model_validator(mode="after")
    def validate_weights_sum(self) -> "EnhancedRiskScore":
        """Ensure all weights sum to 1.0."""
        total_weight = sum(c.weight for c in self.components)
        if abs(total_weight - 1.0) > 0.001:
            raise ValueError(f"Component weights must sum to 1.0, got {total_weight}")
        return self

    def get_component(self, component: RiskComponent) -> RiskComponentScore:
        """Get a specific component's score."""
        for c in self.components:
            if c.component == component:
                return c
        raise ValueError(f"Component {component} not found")

    @property
    def top_contributors(self) -> list[RiskComponentScore]:
        """Get components sorted by weighted contribution (highest first)."""
        return sorted(self.components, key=lambda c: c.weighted_score, reverse=True)


# Weight constants for easy access
RISK_WEIGHTS = {
    RiskComponent.ATTACK_SEVERITY: 0.25,
    RiskComponent.IOC_QUALITY: 0.25,
    RiskComponent.IOC_QUANTITY: 0.15,
    RiskComponent.SCAMMER_ENGAGEMENT: 0.15,
    RiskComponent.URGENCY_TACTICS: 0.10,
    RiskComponent.PERSONALIZATION: 0.10,
}

# Attack severity scores (0-10 scale)
ATTACK_SEVERITY_SCORES = {
    "ceo_fraud": 10,
    "crypto_investment": 10,
    "nigerian_419": 8,
    "fake_invoice": 8,
    "romance_scam": 7,
    "tech_support": 5,
    "lottery_prize": 5,
    "delivery_scam": 4,
    "not_phishing": 2,
}

# IOC quality scores (per IOC type, 0-10 scale)
IOC_QUALITY_SCORES = {
    "btc_wallet": 8,
    "btc": 8,
    "iban": 8,
    "phone": 5,
    "url": 3,
}
