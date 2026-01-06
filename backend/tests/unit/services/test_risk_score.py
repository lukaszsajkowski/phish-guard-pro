"""Unit tests for risk score calculation in session_service."""

import pytest

from phishguard.services.session_service import calculate_risk_score


class TestCalculateRiskScore:
    """Tests for calculate_risk_score function."""

    def test_no_iocs_low_severity_attack(self) -> None:
        """Risk score is low for delivery scam with no IOCs."""
        score = calculate_risk_score("delivery_scam", [])
        assert score == 2  # Base score only

    def test_no_iocs_high_severity_attack(self) -> None:
        """Risk score reflects attack severity even without IOCs."""
        score = calculate_risk_score("ceo_fraud", [])
        assert score == 4  # Base score for CEO fraud

    def test_not_phishing_minimal_score(self) -> None:
        """Not phishing emails have minimum risk score."""
        score = calculate_risk_score("not_phishing", [])
        assert score == 1

    def test_single_low_value_ioc(self) -> None:
        """One low-value IOC adds to score."""
        iocs = [{"type": "url", "value": "https://scam.com"}]
        score = calculate_risk_score("delivery_scam", iocs)
        assert score == 3  # 2 (base) + 1 (IOC count)

    def test_single_high_value_ioc(self) -> None:
        """High-value IOC adds both IOC count and high-value bonus."""
        iocs = [{"type": "btc", "value": "bc1qtest123"}]
        score = calculate_risk_score("delivery_scam", iocs)
        assert score == 4  # 2 (base) + 1 (IOC count) + 1 (high value)

    def test_btc_wallet_type_is_high_value(self) -> None:
        """btc_wallet type is recognized as high-value."""
        iocs = [{"type": "btc_wallet", "value": "1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2"}]
        score = calculate_risk_score("nigerian_419", iocs)
        assert score == 5  # 3 (base) + 1 (IOC count) + 1 (high value)

    def test_iban_is_high_value(self) -> None:
        """IBAN is recognized as high-value IOC."""
        iocs = [{"type": "iban", "value": "DE89370400440532013000"}]
        score = calculate_risk_score("fake_invoice", iocs)
        assert score == 5  # 3 (base) + 1 (IOC count) + 1 (high value)

    def test_multiple_iocs_capped(self) -> None:
        """IOC count contribution is capped at 3."""
        iocs = [
            {"type": "url", "value": "https://scam1.com"},
            {"type": "url", "value": "https://scam2.com"},
            {"type": "url", "value": "https://scam3.com"},
            {"type": "url", "value": "https://scam4.com"},
            {"type": "url", "value": "https://scam5.com"},
        ]
        score = calculate_risk_score("delivery_scam", iocs)
        assert score == 5  # 2 (base) + 3 (capped IOC count)

    def test_multiple_high_value_iocs_capped(self) -> None:
        """High-value IOC contribution is capped at 3."""
        iocs = [
            {"type": "btc", "value": "bc1qtest1"},
            {"type": "btc", "value": "bc1qtest2"},
            {"type": "iban", "value": "DE89370400440532013000"},
            {"type": "iban", "value": "GB82WEST12345698765432"},
        ]
        score = calculate_risk_score("crypto_investment", iocs)
        # 4 (base) + 3 (capped IOC count) + 3 (capped high value) = 10
        assert score == 10

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
        assert score == 10  # Capped at maximum

    def test_mixed_iocs(self) -> None:
        """Mixed high and low value IOCs are counted correctly."""
        iocs = [
            {"type": "btc", "value": "bc1qtest1"},
            {"type": "phone", "value": "+1-555-123-4567"},
            {"type": "url", "value": "https://scam.com"},
        ]
        score = calculate_risk_score("nigerian_419", iocs)
        # 3 (base) + 3 (IOC count) + 1 (1 high value BTC) = 7
        assert score == 7

    def test_unknown_attack_type_uses_default(self) -> None:
        """Unknown attack types use default base score."""
        iocs = []
        score = calculate_risk_score("unknown_type", iocs)
        assert score == 2  # Default base score

    def test_minimum_score_is_one(self) -> None:
        """Score is at least 1 even for not_phishing."""
        score = calculate_risk_score("not_phishing", [])
        assert score >= 1

    def test_phone_is_not_high_value(self) -> None:
        """Phone numbers are not high-value IOCs."""
        iocs = [{"type": "phone", "value": "+1-555-123-4567"}]
        score = calculate_risk_score("delivery_scam", iocs)
        assert score == 3  # 2 (base) + 1 (IOC count), no high-value bonus

    def test_url_is_not_high_value(self) -> None:
        """URLs are not high-value IOCs."""
        iocs = [{"type": "url", "value": "https://malicious.com"}]
        score = calculate_risk_score("tech_support", iocs)
        assert score == 3  # 2 (base) + 1 (IOC count), no high-value bonus
