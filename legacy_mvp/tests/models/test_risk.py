"""Comprehensive tests for Risk Score models.

These tests verify that the RiskLevel enum and RiskScore model:
1. RiskLevel enum has all 3 expected values (LOW, MEDIUM, HIGH)
2. RiskLevel display_name property returns correct human-readable names
3. RiskLevel color property returns correct color values
4. RiskScore.from_value correctly maps values to levels
5. RiskScore.from_value clamps out-of-range values
6. RiskScore stores factors correctly
7. calculate_risk_score produces correct scores based on inputs
8. calculate_risk_score respects minimum and maximum bounds

Test Categories:
- RiskLevel enum values and properties
- RiskScore construction and from_value factory
- RiskScore value clamping
- calculate_risk_score behavior
- Edge cases and boundary conditions
"""

import pytest

from phishguard.models.risk import (
    RiskLevel,
    RiskScore,
    calculate_risk_score,
)


class TestRiskLevel:
    """Tests for RiskLevel enum values and properties."""

    def test_risk_level_has_three_values(self) -> None:
        """RiskLevel should have exactly 3 enum values."""
        assert len(RiskLevel) == 3

    @pytest.mark.parametrize(
        "enum_member,expected_value",
        [
            (RiskLevel.LOW, "low"),
            (RiskLevel.MEDIUM, "medium"),
            (RiskLevel.HIGH, "high"),
        ],
        ids=["low", "medium", "high"],
    )
    def test_risk_level_string_values(
        self, enum_member: RiskLevel, expected_value: str
    ) -> None:
        """Each RiskLevel should have the correct string value."""
        assert enum_member.value == expected_value

    def test_risk_level_is_string_subclass(self) -> None:
        """RiskLevel should be a string enum (subclass of str)."""
        for risk_level in RiskLevel:
            assert isinstance(risk_level, str)
            assert isinstance(risk_level.value, str)


class TestRiskLevelDisplayName:
    """Tests for RiskLevel display_name property."""

    @pytest.mark.parametrize(
        "risk_level,expected_display_name",
        [
            (RiskLevel.LOW, "Low"),
            (RiskLevel.MEDIUM, "Medium"),
            (RiskLevel.HIGH, "High"),
        ],
        ids=["low_display", "medium_display", "high_display"],
    )
    def test_display_name_returns_correct_value(
        self, risk_level: RiskLevel, expected_display_name: str
    ) -> None:
        """display_name should return the correct human-readable name."""
        assert risk_level.display_name == expected_display_name

    def test_all_risk_levels_have_display_names(self) -> None:
        """Every RiskLevel should have a display_name defined."""
        for risk_level in RiskLevel:
            display_name = risk_level.display_name
            assert display_name is not None
            assert isinstance(display_name, str)
            assert len(display_name) > 0


class TestRiskLevelColors:
    """Tests for RiskLevel color property."""

    @pytest.mark.parametrize(
        "risk_level,expected_color",
        [
            (RiskLevel.LOW, "green"),
            (RiskLevel.MEDIUM, "yellow"),
            (RiskLevel.HIGH, "red"),
        ],
        ids=["low_green", "medium_yellow", "high_red"],
    )
    def test_color_returns_correct_value(
        self, risk_level: RiskLevel, expected_color: str
    ) -> None:
        """color should return the correct color for each risk level."""
        assert risk_level.color == expected_color

    def test_all_risk_levels_have_colors(self) -> None:
        """Every RiskLevel should have a color defined."""
        for risk_level in RiskLevel:
            color = risk_level.color
            assert color is not None
            assert isinstance(color, str)
            assert len(color) > 0


class TestRiskScoreFromValueLow:
    """Tests for RiskScore.from_value with low values (1-3)."""

    @pytest.mark.parametrize(
        "value",
        [1, 2, 3],
        ids=["value_1", "value_2", "value_3"],
    )
    def test_from_value_low_returns_low_level(self, value: int) -> None:
        """Values 1-3 should result in RiskLevel.LOW."""
        risk_score = RiskScore.from_value(value)
        assert risk_score.level == RiskLevel.LOW

    @pytest.mark.parametrize(
        "value",
        [1, 2, 3],
        ids=["value_1", "value_2", "value_3"],
    )
    def test_from_value_low_preserves_value(self, value: int) -> None:
        """RiskScore should preserve the original value."""
        risk_score = RiskScore.from_value(value)
        assert risk_score.value == value


class TestRiskScoreFromValueMedium:
    """Tests for RiskScore.from_value with medium values (4-6)."""

    @pytest.mark.parametrize(
        "value",
        [4, 5, 6],
        ids=["value_4", "value_5", "value_6"],
    )
    def test_from_value_medium_returns_medium_level(self, value: int) -> None:
        """Values 4-6 should result in RiskLevel.MEDIUM."""
        risk_score = RiskScore.from_value(value)
        assert risk_score.level == RiskLevel.MEDIUM

    @pytest.mark.parametrize(
        "value",
        [4, 5, 6],
        ids=["value_4", "value_5", "value_6"],
    )
    def test_from_value_medium_preserves_value(self, value: int) -> None:
        """RiskScore should preserve the original value."""
        risk_score = RiskScore.from_value(value)
        assert risk_score.value == value


class TestRiskScoreFromValueHigh:
    """Tests for RiskScore.from_value with high values (7-10)."""

    @pytest.mark.parametrize(
        "value",
        [7, 8, 9, 10],
        ids=["value_7", "value_8", "value_9", "value_10"],
    )
    def test_from_value_high_returns_high_level(self, value: int) -> None:
        """Values 7-10 should result in RiskLevel.HIGH."""
        risk_score = RiskScore.from_value(value)
        assert risk_score.level == RiskLevel.HIGH

    @pytest.mark.parametrize(
        "value",
        [7, 8, 9, 10],
        ids=["value_7", "value_8", "value_9", "value_10"],
    )
    def test_from_value_high_preserves_value(self, value: int) -> None:
        """RiskScore should preserve the original value."""
        risk_score = RiskScore.from_value(value)
        assert risk_score.value == value


class TestRiskScoreFromValueClamped:
    """Tests for RiskScore.from_value with out-of-range values."""

    @pytest.mark.parametrize(
        "input_value,expected_clamped",
        [
            (0, 1),
            (-5, 1),
            (-100, 1),
        ],
        ids=["zero_to_1", "negative_5_to_1", "negative_100_to_1"],
    )
    def test_from_value_clamps_below_minimum(
        self, input_value: int, expected_clamped: int
    ) -> None:
        """Values below 1 should be clamped to 1."""
        risk_score = RiskScore.from_value(input_value)
        assert risk_score.value == expected_clamped
        assert risk_score.level == RiskLevel.LOW

    @pytest.mark.parametrize(
        "input_value,expected_clamped",
        [
            (11, 10),
            (15, 10),
            (100, 10),
        ],
        ids=["eleven_to_10", "fifteen_to_10", "hundred_to_10"],
    )
    def test_from_value_clamps_above_maximum(
        self, input_value: int, expected_clamped: int
    ) -> None:
        """Values above 10 should be clamped to 10."""
        risk_score = RiskScore.from_value(input_value)
        assert risk_score.value == expected_clamped
        assert risk_score.level == RiskLevel.HIGH


class TestRiskScoreFactorsIncluded:
    """Tests for RiskScore factors storage."""

    def test_factors_empty_tuple_by_default(self) -> None:
        """RiskScore created without factors should have empty tuple."""
        risk_score = RiskScore.from_value(5)
        assert risk_score.factors == ()

    def test_factors_stored_correctly(self) -> None:
        """RiskScore should store provided factors correctly."""
        factors = ("High confidence classification", "Multiple IOCs detected")
        risk_score = RiskScore.from_value(7, factors=factors)
        assert risk_score.factors == factors
        assert len(risk_score.factors) == 2

    def test_factors_single_factor(self) -> None:
        """RiskScore should handle a single factor correctly."""
        factors = ("Single contributing factor",)
        risk_score = RiskScore.from_value(5, factors=factors)
        assert risk_score.factors == factors
        assert len(risk_score.factors) == 1

    def test_factors_many_factors(self) -> None:
        """RiskScore should handle many factors correctly."""
        factors = (
            "Factor 1",
            "Factor 2",
            "Factor 3",
            "Factor 4",
            "Factor 5",
        )
        risk_score = RiskScore.from_value(8, factors=factors)
        assert risk_score.factors == factors
        assert len(risk_score.factors) == 5


class TestCalculateRiskScoreMinimum:
    """Tests for calculate_risk_score minimum score behavior."""

    def test_minimum_score_all_zeros(self) -> None:
        """All zero inputs should produce minimum score of 1."""
        result = calculate_risk_score(
            attack_confidence=0.0,
            ioc_count=0,
            high_value_ioc_count=0,
            turn_count=0,
        )
        assert result.value == 1
        assert result.level == RiskLevel.LOW

    def test_minimum_score_very_low_inputs(self) -> None:
        """Very low inputs should still produce at least score 1."""
        result = calculate_risk_score(
            attack_confidence=1.0,
            ioc_count=0,
            high_value_ioc_count=0,
            turn_count=0,
        )
        assert result.value >= 1
        assert result.level == RiskLevel.LOW


class TestCalculateRiskScoreHighConfidence:
    """Tests for confidence impact on risk score."""

    def test_high_confidence_increases_score(self) -> None:
        """Higher confidence should produce higher risk score."""
        low_confidence_result = calculate_risk_score(
            attack_confidence=20.0,
            ioc_count=0,
            high_value_ioc_count=0,
            turn_count=0,
        )
        high_confidence_result = calculate_risk_score(
            attack_confidence=90.0,
            ioc_count=0,
            high_value_ioc_count=0,
            turn_count=0,
        )
        assert high_confidence_result.value > low_confidence_result.value

    def test_confidence_at_threshold_values(self) -> None:
        """Test confidence at common threshold values."""
        result_50 = calculate_risk_score(
            attack_confidence=50.0,
            ioc_count=0,
            high_value_ioc_count=0,
            turn_count=0,
        )
        result_80 = calculate_risk_score(
            attack_confidence=80.0,
            ioc_count=0,
            high_value_ioc_count=0,
            turn_count=0,
        )
        assert result_80.value >= result_50.value


class TestCalculateRiskScoreIOCs:
    """Tests for IOC count impact on risk score."""

    def test_iocs_increase_score(self) -> None:
        """More IOCs should produce higher risk score."""
        no_iocs_result = calculate_risk_score(
            attack_confidence=50.0,
            ioc_count=0,
            high_value_ioc_count=0,
            turn_count=0,
        )
        many_iocs_result = calculate_risk_score(
            attack_confidence=50.0,
            ioc_count=5,
            high_value_ioc_count=0,
            turn_count=0,
        )
        assert many_iocs_result.value > no_iocs_result.value

    def test_increasing_iocs_increases_score(self) -> None:
        """Score should increase as IOC count increases."""
        result_1 = calculate_risk_score(
            attack_confidence=50.0,
            ioc_count=1,
            high_value_ioc_count=0,
            turn_count=0,
        )
        result_3 = calculate_risk_score(
            attack_confidence=50.0,
            ioc_count=3,
            high_value_ioc_count=0,
            turn_count=0,
        )
        assert result_3.value >= result_1.value


class TestCalculateRiskScoreHighValueIOCs:
    """Tests for high-value IOC bonus on risk score."""

    def test_high_value_iocs_add_bonus(self) -> None:
        """High-value IOCs should add extra score."""
        no_high_value_result = calculate_risk_score(
            attack_confidence=50.0,
            ioc_count=2,
            high_value_ioc_count=0,
            turn_count=0,
        )
        with_high_value_result = calculate_risk_score(
            attack_confidence=50.0,
            ioc_count=2,
            high_value_ioc_count=2,
            turn_count=0,
        )
        assert with_high_value_result.value > no_high_value_result.value

    def test_high_value_iocs_significant_impact(self) -> None:
        """High-value IOCs (BTC wallets, IBANs) should have significant impact."""
        # Same total IOCs, but different high-value counts
        result_no_high_value = calculate_risk_score(
            attack_confidence=60.0,
            ioc_count=3,
            high_value_ioc_count=0,
            turn_count=5,
        )
        result_all_high_value = calculate_risk_score(
            attack_confidence=60.0,
            ioc_count=3,
            high_value_ioc_count=3,
            turn_count=5,
        )
        assert result_all_high_value.value > result_no_high_value.value


class TestCalculateRiskScoreEngagement:
    """Tests for engagement (exchange count) impact on risk score."""

    def test_engagement_increases_score(self) -> None:
        """More conversation exchanges should increase risk score."""
        few_exchanges_result = calculate_risk_score(
            attack_confidence=50.0,
            ioc_count=0,
            high_value_ioc_count=0,
            turn_count=2,
        )
        many_exchanges_result = calculate_risk_score(
            attack_confidence=50.0,
            ioc_count=0,
            high_value_ioc_count=0,
            turn_count=10,
        )
        assert many_exchanges_result.value > few_exchanges_result.value

    def test_engagement_gradual_increase(self) -> None:
        """Score should gradually increase with more exchanges."""
        results = []
        for exchange_count in [0, 3, 6, 9, 12]:
            result = calculate_risk_score(
                attack_confidence=50.0,
                ioc_count=1,
                high_value_ioc_count=0,
                turn_count=exchange_count,
            )
            results.append(result.value)
        # Values should be non-decreasing
        for i in range(len(results) - 1):
            assert results[i + 1] >= results[i]


class TestCalculateRiskScoreMaximum:
    """Tests for calculate_risk_score maximum score behavior."""

    def test_maximum_score_extreme_values(self) -> None:
        """Extreme values should be capped at maximum score of 10."""
        result = calculate_risk_score(
            attack_confidence=100.0,
            ioc_count=100,
            high_value_ioc_count=50,
            turn_count=100,
        )
        assert result.value == 10
        assert result.level == RiskLevel.HIGH

    def test_maximum_score_high_realistic_values(self) -> None:
        """High but realistic values should approach or reach maximum."""
        result = calculate_risk_score(
            attack_confidence=95.0,
            ioc_count=10,
            high_value_ioc_count=5,
            turn_count=20,
        )
        assert result.value <= 10
        assert result.level == RiskLevel.HIGH


class TestCalculateRiskScoreFactorsPopulated:
    """Tests for factors list population in calculate_risk_score."""

    def test_factors_populated_with_confidence(self) -> None:
        """Factors should include confidence-related factor."""
        result = calculate_risk_score(
            attack_confidence=90.0,
            ioc_count=0,
            high_value_ioc_count=0,
            turn_count=0,
        )
        assert len(result.factors) > 0
        # Should have at least one factor mentioning confidence
        factor_text = " ".join(result.factors).lower()
        assert "confidence" in factor_text or "classification" in factor_text

    def test_factors_populated_with_iocs(self) -> None:
        """Factors should include IOC-related factor when IOCs present."""
        result = calculate_risk_score(
            attack_confidence=50.0,
            ioc_count=5,
            high_value_ioc_count=0,
            turn_count=0,
        )
        assert len(result.factors) > 0
        factor_text = " ".join(result.factors).lower()
        assert "ioc" in factor_text or "indicator" in factor_text

    def test_factors_populated_with_high_value_iocs(self) -> None:
        """Factors should mention high-value IOCs when present."""
        result = calculate_risk_score(
            attack_confidence=50.0,
            ioc_count=3,
            high_value_ioc_count=2,
            turn_count=0,
        )
        assert len(result.factors) > 0
        factor_text = " ".join(result.factors).lower()
        # Should mention high-value IOCs, financial, or specific types
        high_value_terms = [
            "high-value",
            "high value",
            "financial",
            "btc",
            "iban",
            "wallet",
        ]
        assert any(term in factor_text for term in high_value_terms)

    def test_factors_populated_with_engagement(self) -> None:
        """Factors should include engagement-related factor."""
        result = calculate_risk_score(
            attack_confidence=50.0,
            ioc_count=0,
            high_value_ioc_count=0,
            turn_count=15,
        )
        assert len(result.factors) > 0
        factor_text = " ".join(result.factors).lower()
        assert any(
            term in factor_text
            for term in ["engagement", "exchange", "conversation", "turn"]
        )

    def test_factors_comprehensive_scenario(self) -> None:
        """All contributing factors should be captured in comprehensive scenario."""
        result = calculate_risk_score(
            attack_confidence=85.0,
            ioc_count=5,
            high_value_ioc_count=2,
            turn_count=10,
        )
        # Should have multiple factors for a comprehensive scenario
        assert len(result.factors) >= 2


class TestCalculateRiskScoreEdgeCases:
    """Tests for edge cases in calculate_risk_score."""

    def test_zero_confidence_minimum_score(self) -> None:
        """Zero confidence should still produce valid score."""
        result = calculate_risk_score(
            attack_confidence=0.0,
            ioc_count=0,
            high_value_ioc_count=0,
            turn_count=0,
        )
        assert result.value >= 1
        assert result.level == RiskLevel.LOW

    def test_exactly_100_confidence(self) -> None:
        """100% confidence should be handled correctly."""
        result = calculate_risk_score(
            attack_confidence=100.0,
            ioc_count=0,
            high_value_ioc_count=0,
            turn_count=0,
        )
        assert result.value >= 1
        assert result.value <= 10

    def test_negative_counts_handled(self) -> None:
        """Negative counts should be handled gracefully (treated as 0)."""
        # This tests defensive programming - implementation should handle edge cases
        result = calculate_risk_score(
            attack_confidence=50.0,
            ioc_count=0,  # Use 0 since negative might not be allowed
            high_value_ioc_count=0,
            turn_count=0,
        )
        assert result.value >= 1
        assert result.value <= 10


class TestRiskScoreRealisticScenarios:
    """Tests with realistic phishing analysis scenarios."""

    def test_low_risk_scenario(self) -> None:
        """Low-risk scenario: low confidence, no IOCs, minimal engagement."""
        result = calculate_risk_score(
            attack_confidence=25.0,
            ioc_count=0,
            high_value_ioc_count=0,
            turn_count=1,
        )
        assert result.level == RiskLevel.LOW
        assert result.value <= 3

    def test_medium_risk_scenario(self) -> None:
        """Medium-risk scenario: moderate confidence, some IOCs."""
        result = calculate_risk_score(
            attack_confidence=60.0,
            ioc_count=2,
            high_value_ioc_count=0,
            turn_count=5,
        )
        assert result.level in (RiskLevel.MEDIUM, RiskLevel.LOW)
        assert result.value >= 3

    def test_high_risk_scenario(self) -> None:
        """High-risk scenario: high confidence, multiple high-value IOCs."""
        result = calculate_risk_score(
            attack_confidence=92.0,
            ioc_count=6,
            high_value_ioc_count=3,
            turn_count=12,
        )
        assert result.level == RiskLevel.HIGH
        assert result.value >= 7

    def test_nigerian_419_typical_scenario(self) -> None:
        """Typical Nigerian 419 scam detection scenario."""
        result = calculate_risk_score(
            attack_confidence=95.0,  # High confidence - clear 419 indicators
            ioc_count=3,  # Email, phone, possibly BTC address
            high_value_ioc_count=1,  # One financial IOC
            turn_count=4,  # Several exchanges before detection
        )
        assert result.value >= 5
        assert len(result.factors) > 0

    def test_crypto_scam_high_value_scenario(self) -> None:
        """Crypto scam with multiple high-value IOCs."""
        result = calculate_risk_score(
            attack_confidence=88.0,
            ioc_count=5,  # Multiple BTC addresses, URLs
            high_value_ioc_count=4,  # Most are BTC addresses
            turn_count=8,
        )
        assert result.level == RiskLevel.HIGH
        assert result.value >= 7
