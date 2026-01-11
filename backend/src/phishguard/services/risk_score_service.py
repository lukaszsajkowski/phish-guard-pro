"""Enhanced Risk Score Calculator service.

Implements the multi-dimensional risk score calculation as defined
in US-032. Calculates risk from 6 weighted components.
"""

from typing import Any

from phishguard.analyzers import PersonalizationAnalyzer, UrgencyAnalyzer
from phishguard.models.risk_score import (
    ATTACK_SEVERITY_SCORES,
    IOC_QUALITY_SCORES,
    RISK_WEIGHTS,
    EnhancedRiskScore,
    RiskComponent,
    RiskComponentScore,
    RiskLevel,
)


class RiskScoreCalculator:
    """Calculator for the enhanced multi-dimensional risk score.

    Combines 6 weighted components to produce a final risk score
    on a 1-10 scale with full breakdown and explanations.
    """

    def __init__(self) -> None:
        """Initialize the calculator with analyzers."""
        self._urgency_analyzer = UrgencyAnalyzer()
        self._personalization_analyzer = PersonalizationAnalyzer()

    def calculate(
        self,
        attack_type: str,
        iocs: list[dict[str, Any]],
        scammer_messages: list[str] | None = None,
        victim_name: str | None = None,
        victim_first_name: str | None = None,
    ) -> EnhancedRiskScore:
        """Calculate the enhanced risk score with full breakdown.

        Args:
            attack_type: The classified attack type (e.g., 'ceo_fraud').
            iocs: List of extracted IOCs with 'type' field.
            scammer_messages: List of scammer message texts (optional).
            victim_name: Full name of victim persona (optional).
            victim_first_name: First name of victim persona (optional).

        Returns:
            EnhancedRiskScore with total score and component breakdown.
        """
        scammer_messages = scammer_messages or []

        # Calculate each component
        components = [
            self._calculate_attack_severity(attack_type),
            self._calculate_ioc_quality(iocs),
            self._calculate_ioc_quantity(iocs),
            self._calculate_scammer_engagement(scammer_messages),
            self._calculate_urgency_tactics(scammer_messages),
            self._calculate_personalization(
                scammer_messages, victim_name, victim_first_name
            ),
        ]

        # Calculate total score
        # Each component is 0-10, weights sum to 1.0
        # So weighted sum is directly on 0-10 scale
        raw_weighted_sum = sum(c.weighted_score for c in components)

        # Ensure minimum of 1.0, cap at 10.0
        total_score = max(1.0, min(10.0, raw_weighted_sum))
        total_score = round(total_score, 1)

        risk_level = RiskLevel.from_score(total_score)

        return EnhancedRiskScore(
            total_score=total_score,
            risk_level=risk_level,
            components=components,
        )

    def _calculate_attack_severity(self, attack_type: str) -> RiskComponentScore:
        """Calculate attack severity component.

        CEO Fraud and Crypto = 10, Nigerian 419 = 8, etc.
        """
        component = RiskComponent.ATTACK_SEVERITY
        weight = RISK_WEIGHTS[component]

        raw_score = float(ATTACK_SEVERITY_SCORES.get(attack_type, 5))

        # Generate explanation
        if raw_score >= 9:
            severity_label = "Critical severity"
        elif raw_score >= 7:
            severity_label = "High severity"
        elif raw_score >= 4:
            severity_label = "Moderate severity"
        else:
            severity_label = "Low severity"
        attack_display = attack_type.replace("_", " ").title()

        return RiskComponentScore(
            component=component,
            raw_score=raw_score,
            weight=weight,
            weighted_score=round(raw_score * weight, 3),
            explanation=f"{severity_label} attack: {attack_display}",
        )

    def _calculate_ioc_quality(self, iocs: list[dict[str, Any]]) -> RiskComponentScore:
        """Calculate IOC quality component.

        BTC wallet = 8, IBAN = 8, phone = 5, URL = 3.
        Score is based on the highest-quality IOC found.
        """
        component = RiskComponent.IOC_QUALITY
        weight = RISK_WEIGHTS[component]

        if not iocs:
            return RiskComponentScore(
                component=component,
                raw_score=0.0,
                weight=weight,
                weighted_score=0.0,
                explanation="No IOCs extracted yet.",
            )

        # Get unique IOC types and their quality scores
        ioc_types = set()
        for ioc in iocs:
            ioc_type = ioc.get("type", "")
            if ioc_type:
                ioc_types.add(ioc_type)

        # Use highest quality IOC score (0-10 scale)
        max_quality = max(IOC_QUALITY_SCORES.get(t, 0) for t in ioc_types) if ioc_types else 0
        # Bonus for multiple high-value IOC types (up to +2)
        high_value_count = sum(1 for t in ioc_types if IOC_QUALITY_SCORES.get(t, 0) >= 8)
        bonus = min(high_value_count - 1, 2) if high_value_count > 1 else 0
        raw_score = min(float(max_quality + bonus), 10.0)

        # Generate explanation
        high_value = [t for t in ioc_types if IOC_QUALITY_SCORES.get(t, 0) >= 8]
        if high_value:
            high_value_str = ", ".join(t.upper() for t in high_value)
            explanation = f"High-value IOCs: {high_value_str}"
        elif ioc_types:
            explanation = f"{len(ioc_types)} IOC type(s) detected."
        else:
            explanation = "No valuable IOCs detected."

        return RiskComponentScore(
            component=component,
            raw_score=raw_score,
            weight=weight,
            weighted_score=round(raw_score * weight, 3),
            explanation=explanation,
        )

    def _calculate_ioc_quantity(self, iocs: list[dict[str, Any]]) -> RiskComponentScore:
        """Calculate IOC quantity component.

        +2 per IOC, max 10 points (5 IOCs for max).
        """
        component = RiskComponent.IOC_QUANTITY
        weight = RISK_WEIGHTS[component]

        ioc_count = len(iocs)

        # +2 per IOC, max 10 (5 IOCs for max score)
        raw_score = min(float(ioc_count * 2), 10.0)

        # Generate explanation
        if ioc_count == 0:
            explanation = "No IOCs extracted yet."
        elif ioc_count == 1:
            explanation = "1 IOC extracted."
        elif ioc_count >= 5:
            explanation = f"{ioc_count} IOCs extracted (maximum score)."
        else:
            explanation = f"{ioc_count} IOCs extracted."

        return RiskComponentScore(
            component=component,
            raw_score=raw_score,
            weight=weight,
            weighted_score=round(raw_score * weight, 3),
            explanation=explanation,
        )

    def _calculate_scammer_engagement(
        self, messages: list[str]
    ) -> RiskComponentScore:
        """Calculate scammer engagement component.

        Based on message count and average message length. Scale 0-10.
        """
        component = RiskComponent.SCAMMER_ENGAGEMENT
        weight = RISK_WEIGHTS[component]

        if not messages:
            return RiskComponentScore(
                component=component,
                raw_score=0.0,
                weight=weight,
                weighted_score=0.0,
                explanation="No scammer messages yet.",
            )

        message_count = len(messages)
        total_length = sum(len(m) for m in messages)
        avg_length = total_length / message_count if message_count > 0 else 0

        # Score based on message count (up to 5 points)
        # 1 message = 1, 2 = 2, 3 = 3, 4 = 4, 5+ = 5
        count_score = min(message_count, 5)

        # Score based on average length (up to 5 points)
        # <50 chars = 1, 50-100 = 2, 100-200 = 3, 200-300 = 4, 300+ = 5
        if avg_length < 50:
            length_score = 1
        elif avg_length < 100:
            length_score = 2
        elif avg_length < 200:
            length_score = 3
        elif avg_length < 300:
            length_score = 4
        else:
            length_score = 5

        raw_score = float(count_score + length_score)
        raw_score = min(raw_score, 10.0)

        # Generate explanation
        avg_len = int(avg_length)
        if raw_score <= 3:
            explanation = f"Low engagement: {message_count} short message(s)."
        elif raw_score <= 5:
            explanation = f"Moderate engagement: {message_count} msg(s), {avg_len} avg."
        elif raw_score <= 7:
            explanation = f"Good engagement: {message_count} msg(s), {avg_len} avg."
        else:
            explanation = f"High engagement: {message_count} detailed message(s)."

        return RiskComponentScore(
            component=component,
            raw_score=round(raw_score, 2),
            weight=weight,
            weighted_score=round(raw_score * weight, 3),
            explanation=explanation,
        )

    def _calculate_urgency_tactics(
        self, messages: list[str]
    ) -> RiskComponentScore:
        """Calculate urgency tactics component.

        Detection of pressure keywords like 'urgent', 'deadline', etc.
        """
        component = RiskComponent.URGENCY_TACTICS
        weight = RISK_WEIGHTS[component]

        result = self._urgency_analyzer.analyze(messages)

        return RiskComponentScore(
            component=component,
            raw_score=result.score,
            weight=weight,
            weighted_score=round(result.score * weight, 3),
            explanation=result.explanation,
        )

    def _calculate_personalization(
        self,
        messages: list[str],
        victim_name: str | None,
        victim_first_name: str | None,
    ) -> RiskComponentScore:
        """Calculate personalization component.

        Scammer uses victim's name or references context.
        """
        component = RiskComponent.PERSONALIZATION
        weight = RISK_WEIGHTS[component]

        result = self._personalization_analyzer.analyze(
            messages, victim_name, victim_first_name
        )

        return RiskComponentScore(
            component=component,
            raw_score=result.score,
            weight=weight,
            weighted_score=round(result.score * weight, 3),
            explanation=result.explanation,
        )


# Singleton instance for convenience
_calculator: RiskScoreCalculator | None = None


def get_risk_calculator() -> RiskScoreCalculator:
    """Get the singleton risk calculator instance."""
    global _calculator
    if _calculator is None:
        _calculator = RiskScoreCalculator()
    return _calculator


def calculate_enhanced_risk_score(
    attack_type: str,
    iocs: list[dict[str, Any]],
    scammer_messages: list[str] | None = None,
    victim_name: str | None = None,
    victim_first_name: str | None = None,
) -> EnhancedRiskScore:
    """Convenience function to calculate enhanced risk score.

    Args:
        attack_type: The classified attack type.
        iocs: List of extracted IOCs.
        scammer_messages: List of scammer message texts.
        victim_name: Full name of victim persona.
        victim_first_name: First name of victim persona.

    Returns:
        EnhancedRiskScore with total score and breakdown.
    """
    calculator = get_risk_calculator()
    return calculator.calculate(
        attack_type=attack_type,
        iocs=iocs,
        scammer_messages=scammer_messages,
        victim_name=victim_name,
        victim_first_name=victim_first_name,
    )


def calculate_simple_risk_score(
    attack_type: str,
    iocs: list[dict[str, Any]],
    scammer_messages: list[str] | None = None,
    victim_name: str | None = None,
    victim_first_name: str | None = None,
) -> int:
    """Calculate risk score and return only the integer total.

    Backward-compatible function that returns just the score (1-10).

    Args:
        attack_type: The classified attack type.
        iocs: List of extracted IOCs.
        scammer_messages: List of scammer message texts.
        victim_name: Full name of victim persona.
        victim_first_name: First name of victim persona.

    Returns:
        Integer risk score from 1 to 10.
    """
    enhanced = calculate_enhanced_risk_score(
        attack_type=attack_type,
        iocs=iocs,
        scammer_messages=scammer_messages,
        victim_name=victim_name,
        victim_first_name=victim_first_name,
    )
    return int(round(enhanced.total_score))
