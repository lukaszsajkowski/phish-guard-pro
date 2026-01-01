"""Unit tests for Classification models."""

import pytest
from phishguard.models.classification import AttackType, ClassificationResult

class TestAttackType:
    """Tests for AttackType enum."""

    def test_display_name_returns_correct_string(self):
        """Display name property should return human-readable string."""
        assert AttackType.NIGERIAN_419.display_name == "Nigerian 419"
        assert AttackType.CEO_FRAUD.display_name == "CEO Fraud"
        assert AttackType.NOT_PHISHING.display_name == "Not Phishing"

class TestClassificationResult:
    """Tests for ClassificationResult model."""

    def test_classification_result_validation(self):
        """Should validate and create correct ClassificationResult instance."""
        result = ClassificationResult(
            attack_type=AttackType.NIGERIAN_419,
            confidence=95.5555,
            reasoning="Test reasoning",
            classification_time_ms=100
        )
        
        assert result.attack_type == AttackType.NIGERIAN_419
        assert result.confidence == 95.56  # Rounded to 2 decimal places
        assert result.reasoning == "Test reasoning"
        assert result.classification_time_ms == 100

    def test_is_phishing_property(self):
        """is_phishing should return correct boolean."""
        phishing_result = ClassificationResult(
            attack_type=AttackType.CEO_FRAUD,
            confidence=90.0,
            reasoning="Phishing",
            classification_time_ms=100
        )
        assert phishing_result.is_phishing is True

        safe_result = ClassificationResult(
            attack_type=AttackType.NOT_PHISHING,
            confidence=90.0,
            reasoning="Safe",
            classification_time_ms=100
        )
        assert safe_result.is_phishing is False

    def test_is_high_confidence_property(self):
        """is_high_confidence should check threshold."""
        high_conf = ClassificationResult(
            attack_type=AttackType.CEO_FRAUD,
            confidence=80.0,
            reasoning="High",
            classification_time_ms=100
        )
        assert high_conf.is_high_confidence is True

        low_conf = ClassificationResult(
            attack_type=AttackType.CEO_FRAUD,
            confidence=79.9,
            reasoning="Low",
            classification_time_ms=100
        )
        assert low_conf.is_high_confidence is False

    def test_is_low_confidence_not_phishing_property(self):
        """Should identify uncertain not-phishing results."""
        uncertain_safe = ClassificationResult(
            attack_type=AttackType.NOT_PHISHING,
            confidence=29.9,
            reasoning="Uncertain",
            classification_time_ms=100
        )
        assert uncertain_safe.is_low_confidence_not_phishing is True

        certain_safe = ClassificationResult(
            attack_type=AttackType.NOT_PHISHING,
            confidence=30.0,
            reasoning="Certain",
            classification_time_ms=100
        )
        assert certain_safe.is_low_confidence_not_phishing is False

        uncertain_phish = ClassificationResult(
            attack_type=AttackType.CEO_FRAUD,
            confidence=20.0,
            reasoning="Uncertain Phish",
            classification_time_ms=100
        )
        assert uncertain_phish.is_low_confidence_not_phishing is False
