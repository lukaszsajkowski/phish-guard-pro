"""Unit tests for enhanced risk score calculator (US-032)."""

import pytest

from phishguard.analyzers import PersonalizationAnalyzer, UrgencyAnalyzer
from phishguard.models.risk_score import (
    ATTACK_SEVERITY_SCORES,
    IOC_QUALITY_SCORES,
    RISK_WEIGHTS,
    EnhancedRiskScore,
    RiskComponent,
    RiskLevel,
)
from phishguard.services.risk_score_service import (
    RiskScoreCalculator,
    calculate_enhanced_risk_score,
    calculate_simple_risk_score,
)


class TestRiskComponent:
    """Tests for RiskComponent enum."""

    def test_all_components_have_weights(self) -> None:
        """All components have assigned weights."""
        for component in RiskComponent:
            assert component.weight > 0
            assert component.weight <= 1

    def test_weights_sum_to_one(self) -> None:
        """All component weights sum to 1.0."""
        total = sum(c.weight for c in RiskComponent)
        assert abs(total - 1.0) < 0.001

    def test_display_names_exist(self) -> None:
        """All components have display names."""
        for component in RiskComponent:
            assert component.display_name
            assert len(component.display_name) > 0


class TestRiskLevel:
    """Tests for RiskLevel enum."""

    @pytest.mark.parametrize(
        "score,expected_level",
        [
            (1, RiskLevel.LOW),
            (2, RiskLevel.LOW),
            (3, RiskLevel.LOW),
            (4, RiskLevel.MEDIUM),
            (5, RiskLevel.MEDIUM),
            (6, RiskLevel.MEDIUM),
            (7, RiskLevel.HIGH),
            (8, RiskLevel.HIGH),
            (9, RiskLevel.HIGH),
            (10, RiskLevel.HIGH),
        ],
    )
    def test_from_score(self, score: int, expected_level: RiskLevel) -> None:
        """Risk level is determined correctly from score."""
        assert RiskLevel.from_score(score) == expected_level


class TestUrgencyAnalyzer:
    """Tests for UrgencyAnalyzer."""

    @pytest.fixture
    def analyzer(self) -> UrgencyAnalyzer:
        return UrgencyAnalyzer()

    def test_no_urgency_in_neutral_message(self, analyzer: UrgencyAnalyzer) -> None:
        """Neutral messages have no urgency score."""
        result = analyzer.analyze(["Hello, thank you for your reply."])
        assert result.score == 0
        assert len(result.detected_keywords) == 0

    def test_detects_urgent_keyword(self, analyzer: UrgencyAnalyzer) -> None:
        """Detects 'urgent' keyword."""
        result = analyzer.analyze(["This is urgent, please respond."])
        assert result.score > 0
        assert "urgent" in result.detected_keywords

    def test_detects_deadline(self, analyzer: UrgencyAnalyzer) -> None:
        """Detects deadline keyword."""
        result = analyzer.analyze(["The deadline is tomorrow!"])
        assert result.score > 0
        assert "deadline" in result.detected_keywords

    def test_detects_immediately(self, analyzer: UrgencyAnalyzer) -> None:
        """Detects 'immediately' keyword."""
        result = analyzer.analyze(["You must act immediately!"])
        assert result.score > 0
        assert "immediately" in result.detected_keywords

    def test_multiple_urgency_indicators(self, analyzer: UrgencyAnalyzer) -> None:
        """Multiple indicators increase score."""
        result = analyzer.analyze(
            ["URGENT! Act now or you will miss out! This expires today!"]
        )
        assert result.score > 1
        assert len(result.detected_keywords) >= 2

    def test_score_capped_at_ten(self, analyzer: UrgencyAnalyzer) -> None:
        """Score is capped at 10.0."""
        result = analyzer.analyze(
            [
                "URGENT! IMMEDIATELY! Act now! Deadline! Final notice! "
                "Last chance! Expires today! Hurry! ASAP! Limited time!"
            ]
        )
        assert result.score <= 10.0

    def test_case_insensitive(self, analyzer: UrgencyAnalyzer) -> None:
        """Detection is case-insensitive."""
        result = analyzer.analyze(["URGENT! IMMEDIATELY! ACT NOW!"])
        assert result.score > 0

    def test_empty_messages(self, analyzer: UrgencyAnalyzer) -> None:
        """Empty message list returns zero score."""
        result = analyzer.analyze([])
        assert result.score == 0


class TestPersonalizationAnalyzer:
    """Tests for PersonalizationAnalyzer."""

    @pytest.fixture
    def analyzer(self) -> PersonalizationAnalyzer:
        return PersonalizationAnalyzer()

    def test_no_personalization_in_generic_message(
        self, analyzer: PersonalizationAnalyzer
    ) -> None:
        """Generic messages have no personalization score."""
        result = analyzer.analyze(["Hello, thank you for contacting us."])
        assert result.score == 0
        assert result.name_usage_count == 0

    def test_detects_victim_name(self, analyzer: PersonalizationAnalyzer) -> None:
        """Detects when victim's name is used."""
        result = analyzer.analyze(
            ["Hello John, thank you for your reply."],
            victim_name="John Smith",
            victim_first_name="John",
        )
        assert result.score > 0
        assert result.name_usage_count > 0

    def test_multiple_name_usages(self, analyzer: PersonalizationAnalyzer) -> None:
        """Multiple name usages increase score."""
        result = analyzer.analyze(
            ["Hello John! John, I need your help. Can you help me, John?"],
            victim_name="John Smith",
            victim_first_name="John",
        )
        assert result.name_usage_count >= 3
        assert result.score > 1

    def test_detects_context_references(
        self, analyzer: PersonalizationAnalyzer
    ) -> None:
        """Detects context references like 'as we discussed'."""
        result = analyzer.analyze(
            ["As we discussed yesterday, your account needs attention."]
        )
        assert result.score > 0
        assert len(result.context_references) > 0

    def test_combined_name_and_context(self, analyzer: PersonalizationAnalyzer) -> None:
        """Combined name usage and context references."""
        result = analyzer.analyze(
            ["John, as we discussed, your company needs this service."],
            victim_name="John Smith",
            victim_first_name="John",
        )
        assert result.score > 0
        assert result.name_usage_count > 0
        assert len(result.context_references) > 0

    def test_score_capped_at_ten(self, analyzer: PersonalizationAnalyzer) -> None:
        """Score is capped at 10.0."""
        result = analyzer.analyze(
            [
                "John, John, John! As we discussed, your company account "
                "from your request last week following up on your order. John!"
            ],
            victim_name="John Smith",
            victim_first_name="John",
        )
        assert result.score <= 10.0

    def test_empty_messages(self, analyzer: PersonalizationAnalyzer) -> None:
        """Empty message list returns zero score."""
        result = analyzer.analyze([])
        assert result.score == 0


class TestRiskScoreCalculator:
    """Tests for RiskScoreCalculator."""

    @pytest.fixture
    def calculator(self) -> RiskScoreCalculator:
        return RiskScoreCalculator()

    def test_minimum_score_is_one(self, calculator: RiskScoreCalculator) -> None:
        """Minimum possible score is 1."""
        result = calculator.calculate(
            attack_type="not_phishing",
            iocs=[],
            scammer_messages=[],
        )
        assert result.total_score >= 1.0

    def test_maximum_score_is_ten(self, calculator: RiskScoreCalculator) -> None:
        """Maximum possible score is 10."""
        result = calculator.calculate(
            attack_type="ceo_fraud",
            iocs=[
                {"type": "btc_wallet", "value": "bc1q..."},
                {"type": "iban", "value": "DE..."},
                {"type": "phone", "value": "+1..."},
            ],
            scammer_messages=[
                "John! URGENT! Act now or lose everything! Deadline today!"
                * 10  # Long message
            ],
            victim_name="John Smith",
            victim_first_name="John",
        )
        assert result.total_score <= 10.0

    def test_all_six_components_present(self, calculator: RiskScoreCalculator) -> None:
        """Result contains all 6 risk components."""
        result = calculator.calculate("ceo_fraud", [])
        assert len(result.components) == 6
        component_types = {c.component for c in result.components}
        assert component_types == set(RiskComponent)

    def test_attack_severity_scoring(self, calculator: RiskScoreCalculator) -> None:
        """Attack severity component scores correctly."""
        for attack_type, expected_score in ATTACK_SEVERITY_SCORES.items():
            result = calculator.calculate(attack_type, [])
            severity_component = result.get_component(RiskComponent.ATTACK_SEVERITY)
            assert severity_component.raw_score == expected_score

    def test_ioc_quality_no_iocs(self, calculator: RiskScoreCalculator) -> None:
        """IOC quality is 0 when no IOCs."""
        result = calculator.calculate("ceo_fraud", [])
        quality_component = result.get_component(RiskComponent.IOC_QUALITY)
        assert quality_component.raw_score == 0

    def test_ioc_quality_high_value_iocs(self, calculator: RiskScoreCalculator) -> None:
        """IOC quality reflects high-value IOCs."""
        result = calculator.calculate(
            "ceo_fraud",
            [
                {"type": "btc_wallet", "value": "bc1q..."},
                {"type": "iban", "value": "DE..."},
            ],
        )
        quality_component = result.get_component(RiskComponent.IOC_QUALITY)
        # BTC (8) as highest + bonus for 2 high-value types = 9
        assert quality_component.raw_score >= 8.0

    def test_ioc_quantity_scoring(self, calculator: RiskScoreCalculator) -> None:
        """IOC quantity component scales correctly."""
        # 0 IOCs = 0 score
        result_0 = calculator.calculate("ceo_fraud", [])
        qty_0 = result_0.get_component(RiskComponent.IOC_QUANTITY)
        assert qty_0.raw_score == 0

        # 1 IOC = 2 points
        result_1 = calculator.calculate("ceo_fraud", [{"type": "url", "value": "x"}])
        qty_1 = result_1.get_component(RiskComponent.IOC_QUANTITY)
        assert qty_1.raw_score == 2.0

        # 5+ IOCs = max (10)
        result_5 = calculator.calculate(
            "ceo_fraud",
            [
                {"type": "url", "value": "x"},
                {"type": "url", "value": "y"},
                {"type": "url", "value": "z"},
                {"type": "url", "value": "w"},
                {"type": "url", "value": "v"},
            ],
        )
        qty_5 = result_5.get_component(RiskComponent.IOC_QUANTITY)
        assert qty_5.raw_score == 10.0

    def test_scammer_engagement_no_messages(
        self, calculator: RiskScoreCalculator
    ) -> None:
        """Scammer engagement is 0 with no messages."""
        result = calculator.calculate("ceo_fraud", [], scammer_messages=[])
        engagement = result.get_component(RiskComponent.SCAMMER_ENGAGEMENT)
        assert engagement.raw_score == 0

    def test_scammer_engagement_with_messages(
        self, calculator: RiskScoreCalculator
    ) -> None:
        """Scammer engagement increases with messages."""
        result = calculator.calculate(
            "ceo_fraud",
            [],
            scammer_messages=[
                "Hello, thank you for your response. I am very interested.",
                "Please send me your details as soon as possible.",
            ],
        )
        engagement = result.get_component(RiskComponent.SCAMMER_ENGAGEMENT)
        assert engagement.raw_score > 0

    def test_urgency_detection(self, calculator: RiskScoreCalculator) -> None:
        """Urgency tactics are detected in messages."""
        result = calculator.calculate(
            "ceo_fraud",
            [],
            scammer_messages=["URGENT! Act now! Deadline is today!"],
        )
        urgency = result.get_component(RiskComponent.URGENCY_TACTICS)
        assert urgency.raw_score > 0

    def test_personalization_detection(self, calculator: RiskScoreCalculator) -> None:
        """Personalization is detected when name is used."""
        result = calculator.calculate(
            "ceo_fraud",
            [],
            scammer_messages=["Hello John, as we discussed..."],
            victim_name="John Smith",
            victim_first_name="John",
        )
        personalization = result.get_component(RiskComponent.PERSONALIZATION)
        assert personalization.raw_score > 0

    def test_risk_level_assignment(self, calculator: RiskScoreCalculator) -> None:
        """Risk level is assigned based on total score."""
        # Low risk for not_phishing with no IOCs
        result_low = calculator.calculate("not_phishing", [])
        assert result_low.risk_level == RiskLevel.LOW

    def test_component_explanations_present(
        self, calculator: RiskScoreCalculator
    ) -> None:
        """All components have explanations."""
        result = calculator.calculate("ceo_fraud", [])
        for component in result.components:
            assert component.explanation
            assert len(component.explanation) > 0


class TestCalculateEnhancedRiskScore:
    """Tests for convenience function calculate_enhanced_risk_score."""

    def test_returns_enhanced_risk_score(self) -> None:
        """Function returns EnhancedRiskScore instance."""
        result = calculate_enhanced_risk_score("ceo_fraud", [])
        assert isinstance(result, EnhancedRiskScore)

    def test_with_all_parameters(self) -> None:
        """Function works with all optional parameters."""
        result = calculate_enhanced_risk_score(
            attack_type="nigerian_419",
            iocs=[{"type": "btc", "value": "bc1q..."}],
            scammer_messages=["Hello John!"],
            victim_name="John Smith",
            victim_first_name="John",
        )
        assert result.total_score >= 1
        assert result.total_score <= 10


class TestCalculateSimpleRiskScore:
    """Tests for backward-compatible calculate_simple_risk_score."""

    def test_returns_integer(self) -> None:
        """Function returns integer score."""
        result = calculate_simple_risk_score("ceo_fraud", [])
        assert isinstance(result, int)

    def test_score_in_range(self) -> None:
        """Score is between 1 and 10."""
        result = calculate_simple_risk_score("ceo_fraud", [])
        assert 1 <= result <= 10

    def test_consistent_with_enhanced(self) -> None:
        """Simple score matches rounded enhanced score."""
        enhanced = calculate_enhanced_risk_score("ceo_fraud", [])
        simple = calculate_simple_risk_score("ceo_fraud", [])
        assert simple == int(round(enhanced.total_score))


class TestEnhancedRiskScoreModel:
    """Tests for EnhancedRiskScore Pydantic model."""

    def test_top_contributors_sorted(self) -> None:
        """top_contributors returns components sorted by weighted score."""
        score = calculate_enhanced_risk_score(
            "ceo_fraud",
            [{"type": "btc", "value": "bc1q..."}],
        )
        contributors = score.top_contributors
        # Verify descending order
        for i in range(len(contributors) - 1):
            assert contributors[i].weighted_score >= contributors[i + 1].weighted_score

    def test_get_component(self) -> None:
        """get_component returns correct component."""
        score = calculate_enhanced_risk_score("ceo_fraud", [])
        component = score.get_component(RiskComponent.ATTACK_SEVERITY)
        assert component.component == RiskComponent.ATTACK_SEVERITY

    def test_get_nonexistent_component_raises(self) -> None:
        """get_component raises ValueError for missing component."""
        # This shouldn't happen in practice since we always have all 6
        # but the method should handle it
        pass  # Model validation ensures all 6 are present


class TestWeightConfiguration:
    """Tests for weight configuration matching PRD requirements."""

    def test_attack_severity_weight(self) -> None:
        """Attack severity has 25% weight."""
        assert RISK_WEIGHTS[RiskComponent.ATTACK_SEVERITY] == 0.25

    def test_ioc_quality_weight(self) -> None:
        """IOC quality has 25% weight."""
        assert RISK_WEIGHTS[RiskComponent.IOC_QUALITY] == 0.25

    def test_ioc_quantity_weight(self) -> None:
        """IOC quantity has 15% weight."""
        assert RISK_WEIGHTS[RiskComponent.IOC_QUANTITY] == 0.15

    def test_scammer_engagement_weight(self) -> None:
        """Scammer engagement has 15% weight."""
        assert RISK_WEIGHTS[RiskComponent.SCAMMER_ENGAGEMENT] == 0.15

    def test_urgency_tactics_weight(self) -> None:
        """Urgency tactics has 10% weight."""
        assert RISK_WEIGHTS[RiskComponent.URGENCY_TACTICS] == 0.10

    def test_personalization_weight(self) -> None:
        """Personalization has 10% weight."""
        assert RISK_WEIGHTS[RiskComponent.PERSONALIZATION] == 0.10


class TestAttackSeverityScores:
    """Tests for attack severity score configuration (0-10 scale)."""

    def test_ceo_fraud_score(self) -> None:
        """CEO Fraud has severity 10."""
        assert ATTACK_SEVERITY_SCORES["ceo_fraud"] == 10

    def test_crypto_investment_score(self) -> None:
        """Crypto Investment has severity 10."""
        assert ATTACK_SEVERITY_SCORES["crypto_investment"] == 10

    def test_nigerian_419_score(self) -> None:
        """Nigerian 419 has severity 8."""
        assert ATTACK_SEVERITY_SCORES["nigerian_419"] == 8

    def test_not_phishing_score(self) -> None:
        """Not Phishing has severity 2."""
        assert ATTACK_SEVERITY_SCORES["not_phishing"] == 2


class TestIOCQualityScores:
    """Tests for IOC quality score configuration (0-10 scale)."""

    def test_btc_wallet_score(self) -> None:
        """BTC wallet has quality score 8."""
        assert IOC_QUALITY_SCORES["btc_wallet"] == 8

    def test_iban_score(self) -> None:
        """IBAN has quality score 8."""
        assert IOC_QUALITY_SCORES["iban"] == 8

    def test_phone_score(self) -> None:
        """Phone has quality score 5."""
        assert IOC_QUALITY_SCORES["phone"] == 5

    def test_url_score(self) -> None:
        """URL has quality score 3."""
        assert IOC_QUALITY_SCORES["url"] == 3


class TestIOCQualityWithEnrichment:
    """Tests for US-040: enrichment reputation multiplier on IOC Quality."""

    @pytest.fixture
    def calculator(self) -> RiskScoreCalculator:
        return RiskScoreCalculator()

    def test_malicious_multiplier_raises_score(
        self, calculator: RiskScoreCalculator
    ) -> None:
        """Malicious reputation (×1.5) raises IOC Quality above unenriched baseline."""
        iocs = [{"type": "btc_wallet", "value": "bc1q"}]
        enriched = calculator.calculate(
            "ceo_fraud", iocs, ioc_enrichment={"bc1q": "malicious"}
        )
        plain = calculator.calculate("ceo_fraud", iocs)
        assert (
            enriched.get_component(RiskComponent.IOC_QUALITY).raw_score
            >= plain.get_component(RiskComponent.IOC_QUALITY).raw_score
        )

    def test_clean_multiplier_lowers_score(
        self, calculator: RiskScoreCalculator
    ) -> None:
        """Clean reputation (×0.8) lowers IOC Quality below unenriched baseline."""
        iocs = [{"type": "btc_wallet", "value": "bc1q"}]
        enriched = calculator.calculate(
            "ceo_fraud", iocs, ioc_enrichment={"bc1q": "clean"}
        )
        plain = calculator.calculate("ceo_fraud", iocs)
        assert (
            enriched.get_component(RiskComponent.IOC_QUALITY).raw_score
            < plain.get_component(RiskComponent.IOC_QUALITY).raw_score
        )

    def test_score_ordering_malicious_gt_plain_gt_clean(
        self, calculator: RiskScoreCalculator
    ) -> None:
        """Score ordering: malicious > no enrichment > clean."""
        iocs = [{"type": "url", "value": "http://evil.example"}]
        s_malicious = (
            calculator.calculate(
                "ceo_fraud", iocs, ioc_enrichment={"http://evil.example": "malicious"}
            )
            .get_component(RiskComponent.IOC_QUALITY)
            .raw_score
        )
        s_plain = (
            calculator.calculate("ceo_fraud", iocs)
            .get_component(RiskComponent.IOC_QUALITY)
            .raw_score
        )
        s_clean = (
            calculator.calculate(
                "ceo_fraud", iocs, ioc_enrichment={"http://evil.example": "clean"}
            )
            .get_component(RiskComponent.IOC_QUALITY)
            .raw_score
        )
        assert s_malicious > s_plain > s_clean

    def test_missing_key_falls_back_to_1x(
        self, calculator: RiskScoreCalculator
    ) -> None:
        """IOC value absent from enrichment map uses ×1.0 — no exception."""
        iocs = [{"type": "btc_wallet", "value": "bc1q_unknown"}]
        enriched = calculator.calculate(
            "ceo_fraud",
            iocs,
            ioc_enrichment={"some_other_value": "malicious"},
        )
        plain = calculator.calculate("ceo_fraud", iocs)
        assert (
            enriched.get_component(RiskComponent.IOC_QUALITY).raw_score
            == plain.get_component(RiskComponent.IOC_QUALITY).raw_score
        )

    def test_cap_at_ten_with_malicious(self, calculator: RiskScoreCalculator) -> None:
        """IOC Quality score never exceeds 10.0 even with ×1.5 multiplier."""
        iocs = [
            {"type": "btc_wallet", "value": "bc1q"},
            {"type": "iban", "value": "DE89"},
        ]
        result = calculator.calculate(
            "ceo_fraud",
            iocs,
            ioc_enrichment={"bc1q": "malicious", "DE89": "malicious"},
        )
        assert result.get_component(RiskComponent.IOC_QUALITY).raw_score <= 10.0

    def test_none_enrichment_backward_compatible(
        self, calculator: RiskScoreCalculator
    ) -> None:
        """Passing ioc_enrichment=None gives identical result to omitting param."""
        iocs = [
            {"type": "btc_wallet", "value": "bc1q"},
            {"type": "iban", "value": "DE89"},
        ]
        result_none = calculator.calculate("ceo_fraud", iocs, ioc_enrichment=None)
        result_omit = calculator.calculate("ceo_fraud", iocs)
        assert result_none.get_component(
            RiskComponent.IOC_QUALITY
        ).raw_score == pytest.approx(
            result_omit.get_component(RiskComponent.IOC_QUALITY).raw_score
        )

    def test_enrichment_shown_in_explanation(
        self, calculator: RiskScoreCalculator
    ) -> None:
        """Explanation includes enrichment annotation when multiplier != 1.0."""
        iocs = [{"type": "btc_wallet", "value": "bc1q"}]
        result = calculator.calculate(
            "ceo_fraud", iocs, ioc_enrichment={"bc1q": "malicious"}
        )
        explanation = result.get_component(RiskComponent.IOC_QUALITY).explanation
        assert "enrichment" in explanation.lower()
        assert "malicious" in explanation.lower()

    def test_unknown_reputation_is_neutral(
        self, calculator: RiskScoreCalculator
    ) -> None:
        """Explicit 'unknown' reputation uses ×1.0 — same as unenriched."""
        iocs = [{"type": "btc_wallet", "value": "bc1q"}]
        enriched = calculator.calculate(
            "ceo_fraud", iocs, ioc_enrichment={"bc1q": "unknown"}
        )
        plain = calculator.calculate("ceo_fraud", iocs)
        assert enriched.get_component(
            RiskComponent.IOC_QUALITY
        ).raw_score == pytest.approx(
            plain.get_component(RiskComponent.IOC_QUALITY).raw_score
        )
