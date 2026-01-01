"""Risk scoring models for PhishGuard Intel Dashboard.

This module contains Pydantic models and enums for representing
risk scores calculated from phishing engagement metrics.
"""

from enum import Enum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field


class RiskLevel(str, Enum):
    """Risk level categories for phishing engagement assessment.

    The risk level is determined by the overall risk score, which combines
    attack confidence, IOC extraction results, and conversation engagement.

    Attributes:
        LOW: Low risk (score 1-3) - minimal threat indicators.
        MEDIUM: Medium risk (score 4-6) - moderate threat indicators.
        HIGH: High risk (score 7-10) - significant threat indicators.
    """

    LOW = "low"
    """Low risk level (score 1-3)."""

    MEDIUM = "medium"
    """Medium risk level (score 4-6)."""

    HIGH = "high"
    """High risk level (score 7-10)."""

    @property
    def display_name(self) -> str:
        """Return a human-readable display name for the risk level.

        Returns:
            A capitalized string suitable for UI display.

        Example:
            >>> RiskLevel.LOW.display_name
            'Low'
            >>> RiskLevel.HIGH.display_name
            'High'
        """
        return self.value.capitalize()

    @property
    def color(self) -> str:
        """Return the color associated with this risk level.

        Returns:
            A color name string for UI styling.

        Example:
            >>> RiskLevel.LOW.color
            'green'
            >>> RiskLevel.HIGH.color
            'red'
        """
        colors: dict[RiskLevel, str] = {
            RiskLevel.LOW: "green",
            RiskLevel.MEDIUM: "yellow",
            RiskLevel.HIGH: "red",
        }
        return colors[self]


class RiskScore(BaseModel):
    """Risk score assessment for a phishing engagement session.

    This model encapsulates the calculated risk score along with
    the factors that contributed to the assessment.

    Attributes:
        value: Numeric risk score from 1 (lowest) to 10 (highest).
        level: Categorical risk level derived from the score.
        factors: Contributing factors that increased the score.

    Example:
        >>> score = RiskScore.from_value(
        ...     value=7,
        ...     factors=("High attack confidence (85%)", "Multiple IOCs extracted")
        ... )
        >>> score.level
        <RiskLevel.HIGH: 'high'>
        >>> score.level.color
        'red'
    """

    model_config = ConfigDict(
        frozen=True,
        validate_assignment=True,
        use_enum_values=False,
    )

    value: int = Field(
        ...,
        description="Numeric risk score from 1 to 10.",
        ge=1,
        le=10,
        json_schema_extra={
            "examples": [3, 5, 8],
        },
    )
    level: RiskLevel = Field(
        ...,
        description="Categorical risk level derived from the score.",
    )
    factors: tuple[str, ...] = Field(
        default=(),
        description="Contributing factors that increased the risk score.",
        json_schema_extra={
            "examples": [
                ("High attack confidence (92%)", "5+ IOCs extracted"),
                ("Medium attack confidence (65%)", "Active conversation"),
            ],
        },
    )

    @classmethod
    def from_value(cls, value: int, factors: tuple[str, ...] = ()) -> Self:
        """Create a RiskScore from a numeric value with automatic level assignment.

        The value is automatically clamped to the valid range of 1-10.
        The risk level is determined as follows:
        - 1-3: LOW
        - 4-6: MEDIUM
        - 7-10: HIGH

        Args:
            value: The numeric risk score (will be clamped to 1-10).
            factors: Contributing factors that increased the score.

        Returns:
            A new RiskScore instance with the appropriate level.

        Example:
            >>> score = RiskScore.from_value(8, ("High confidence attack",))
            >>> score.level
            <RiskLevel.HIGH: 'high'>
            >>> score = RiskScore.from_value(15)  # Clamped to 10
            >>> score.value
            10
        """
        clamped_value = max(1, min(10, value))

        if clamped_value <= 3:
            level = RiskLevel.LOW
        elif clamped_value <= 6:
            level = RiskLevel.MEDIUM
        else:
            level = RiskLevel.HIGH

        return cls(value=clamped_value, level=level, factors=factors)


def calculate_risk_score(
    attack_confidence: float,
    ioc_count: int,
    high_value_ioc_count: int,
    turn_count: int,
) -> RiskScore:
    """Calculate risk score from engagement metrics.

    The risk score is computed using a weighted formula that considers:
    - Attack classification confidence
    - Total number of IOCs extracted
    - Number of high-value IOCs (BTC wallets, IBANs)
    - Conversation engagement depth (turn count)

    Scoring breakdown:
    - Base score: 1
    - Attack confidence: +3 (>=80%), +2 (>=50%), +1 (>=30%)
    - IOC count: +3 (>=5), +2 (>=3), +1 (>=1)
    - High-value IOCs: +2 (>=2), +1 (>=1)
    - Conversation turns: +2 (>=10), +1 (>=5)

    Args:
        attack_confidence: Classification confidence as percentage (0-100).
        ioc_count: Total number of IOCs extracted from conversation.
        high_value_ioc_count: Number of high-value IOCs (BTC wallets, IBANs).
        turn_count: Number of conversation exchanges.

    Returns:
        RiskScore with calculated value, level, and contributing factors.

    Example:
        >>> score = calculate_risk_score(
        ...     attack_confidence=85.0,
        ...     ioc_count=4,
        ...     high_value_ioc_count=2,
        ...     turn_count=8
        ... )
        >>> score.value
        9
        >>> score.level
        <RiskLevel.HIGH: 'high'>
    """
    score = 1
    factors: list[str] = []

    # Attack confidence contribution
    if attack_confidence >= 80:
        score += 3
        factors.append(f"High attack confidence ({attack_confidence:.0f}%)")
    elif attack_confidence >= 50:
        score += 2
        factors.append(f"Medium attack confidence ({attack_confidence:.0f}%)")
    elif attack_confidence >= 30:
        score += 1
        factors.append(f"Low attack confidence ({attack_confidence:.0f}%)")

    # IOC count contribution
    if ioc_count >= 5:
        score += 3
        factors.append(f"Multiple IOCs extracted ({ioc_count})")
    elif ioc_count >= 3:
        score += 2
        factors.append(f"Several IOCs extracted ({ioc_count})")
    elif ioc_count >= 1:
        score += 1
        factors.append(f"IOC extracted ({ioc_count})")

    # High-value IOC contribution
    if high_value_ioc_count >= 2:
        score += 2
        factors.append(f"Multiple high-value IOCs ({high_value_ioc_count})")
    elif high_value_ioc_count >= 1:
        score += 1
        factors.append(f"High-value IOC found ({high_value_ioc_count})")

    # Conversation engagement contribution
    if turn_count >= 10:
        score += 2
        factors.append(f"Deep conversation engagement ({turn_count} turns)")
    elif turn_count >= 5:
        score += 1
        factors.append(f"Active conversation ({turn_count} turns)")

    return RiskScore.from_value(score, tuple(factors))
