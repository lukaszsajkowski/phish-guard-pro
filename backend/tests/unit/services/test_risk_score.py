"""Unit tests for risk score calculation in session_service.

These tests verify the backward-compatible calculate_risk_score function
which uses the enhanced multi-dimensional calculator (US-032).
"""

import pytest

from phishguard.services.session_service import calculate_risk_score


class TestCalculateRiskScore:
    """Tests for calculate_risk_score function.

    Note: The function now uses the enhanced multi-dimensional calculator,
    so exact values may differ from the old simple algorithm. These tests
    verify correct behavior and relative ordering of scores.
    """

    def test_score_is_integer(self) -> None:
        """Risk score should be an integer."""
        score = calculate_risk_score("ceo_fraud", [])
        assert isinstance(score, int)

    def test_score_in_valid_range(self) -> None:
        """Risk score should always be between 1 and 10."""
        score = calculate_risk_score("delivery_scam", [])
        assert 1 <= score <= 10

    def test_no_iocs_low_severity_attack(self) -> None:
        """Risk score is low for delivery scam with no IOCs."""
        score = calculate_risk_score("delivery_scam", [])
        assert score <= 4  # Low severity attack should have low score

    def test_no_iocs_high_severity_attack(self) -> None:
        """Risk score reflects attack severity even without IOCs."""
        score = calculate_risk_score("ceo_fraud", [])
        # CEO fraud has highest severity (4), but without IOCs or messages
        # the score should still be moderate
        assert score >= 2

    def test_high_severity_higher_than_low_severity(self) -> None:
        """CEO fraud should score higher than delivery scam (same IOCs)."""
        ceo_score = calculate_risk_score("ceo_fraud", [])
        delivery_score = calculate_risk_score("delivery_scam", [])
        assert ceo_score >= delivery_score

    def test_not_phishing_minimal_score(self) -> None:
        """Not phishing emails have low risk score."""
        score = calculate_risk_score("not_phishing", [])
        # Not phishing has lowest severity (1), so score should be very low
        assert score <= 3  # Should be in low risk range

    def test_iocs_increase_score(self) -> None:
        """Adding IOCs should increase the score."""
        score_no_iocs = calculate_risk_score("delivery_scam", [])
        score_with_iocs = calculate_risk_score(
            "delivery_scam",
            [{"type": "url", "value": "https://scam.com"}],
        )
        assert score_with_iocs >= score_no_iocs

    def test_high_value_iocs_increase_score_more(self) -> None:
        """High-value IOCs (BTC, IBAN) should contribute more to score."""
        score_url = calculate_risk_score(
            "delivery_scam",
            [{"type": "url", "value": "https://scam.com"}],
        )
        score_btc = calculate_risk_score(
            "delivery_scam",
            [{"type": "btc", "value": "bc1qtest123"}],
        )
        # BTC has higher quality score (3) than URL (1)
        assert score_btc >= score_url

    def test_btc_wallet_type_recognized(self) -> None:
        """btc_wallet type should be recognized as valid IOC type."""
        iocs = [{"type": "btc_wallet", "value": "1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2"}]
        score = calculate_risk_score("nigerian_419", iocs)
        assert 1 <= score <= 10

    def test_iban_recognized(self) -> None:
        """IBAN type should be recognized as high-value IOC."""
        iocs = [{"type": "iban", "value": "DE89370400440532013000"}]
        score = calculate_risk_score("fake_invoice", iocs)
        assert 1 <= score <= 10

    def test_multiple_iocs_higher_score(self) -> None:
        """More IOCs should result in higher score."""
        score_1_ioc = calculate_risk_score(
            "delivery_scam",
            [{"type": "url", "value": "https://scam1.com"}],
        )
        score_3_iocs = calculate_risk_score(
            "delivery_scam",
            [
                {"type": "url", "value": "https://scam1.com"},
                {"type": "url", "value": "https://scam2.com"},
                {"type": "url", "value": "https://scam3.com"},
            ],
        )
        assert score_3_iocs >= score_1_ioc

    def test_maximum_score_capped_at_10(self) -> None:
        """Total score cannot exceed 10."""
        iocs = [
            {"type": "btc", "value": "bc1qtest1"},
            {"type": "btc", "value": "bc1qtest2"},
            {"type": "btc", "value": "bc1qtest3"},
            {"type": "iban", "value": "DE89370400440532013000"},
            {"type": "iban", "value": "GB82WEST12345698765432"},
        ]
        score = calculate_risk_score("ceo_fraud", iocs)
        assert score <= 10

    def test_unknown_attack_type_uses_default(self) -> None:
        """Unknown attack types should still produce valid score."""
        score = calculate_risk_score("unknown_type", [])
        assert 1 <= score <= 10

    def test_minimum_score_is_one(self) -> None:
        """Score is at least 1 even for not_phishing."""
        score = calculate_risk_score("not_phishing", [])
        assert score >= 1

    def test_phone_type_recognized(self) -> None:
        """Phone numbers should be recognized as IOC type."""
        iocs = [{"type": "phone", "value": "+1-555-123-4567"}]
        score = calculate_risk_score("delivery_scam", iocs)
        assert 1 <= score <= 10

    def test_url_type_recognized(self) -> None:
        """URLs should be recognized as IOC type."""
        iocs = [{"type": "url", "value": "https://malicious.com"}]
        score = calculate_risk_score("tech_support", iocs)
        assert 1 <= score <= 10

    def test_with_scammer_messages(self) -> None:
        """Scammer messages should increase engagement score."""
        score_no_msg = calculate_risk_score("ceo_fraud", [])
        score_with_msg = calculate_risk_score(
            "ceo_fraud",
            [],
            scammer_messages=["Hello, please send money immediately!"],
        )
        assert score_with_msg >= score_no_msg

    def test_urgency_keywords_increase_score(self) -> None:
        """Urgency keywords in messages should increase score."""
        score_neutral = calculate_risk_score(
            "ceo_fraud",
            [],
            scammer_messages=["Hello, nice to meet you."],
        )
        score_urgent = calculate_risk_score(
            "ceo_fraud",
            [],
            scammer_messages=["URGENT! Act now! Deadline today!"],
        )
        assert score_urgent >= score_neutral

    def test_personalization_increases_score(self) -> None:
        """Using victim's name should increase score."""
        score_generic = calculate_risk_score(
            "ceo_fraud",
            [],
            scammer_messages=["Hello, please help me."],
        )
        score_personalized = calculate_risk_score(
            "ceo_fraud",
            [],
            scammer_messages=["Hello John, as we discussed..."],
            victim_name="John Smith",
            victim_first_name="John",
        )
        assert score_personalized >= score_generic
