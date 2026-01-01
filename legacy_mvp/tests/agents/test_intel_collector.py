"""Tests for the IntelCollector module.

Tests IOC extraction patterns for:
- BTC wallet addresses (bech32 and legacy)
- IBAN numbers
- Phone numbers (various international formats)
- URLs (http/https)
"""

import pytest

from phishguard.agents.intel_collector import ExtractionResult, IntelCollector
from phishguard.models.ioc import IOCType


class TestIntelCollector:
    """Test suite for IntelCollector IOC extraction."""

    @pytest.fixture
    def collector(self) -> IntelCollector:
        """Create a fresh IntelCollector instance."""
        return IntelCollector()

    # =========================================================================
    # BTC Wallet Tests
    # =========================================================================

    @pytest.mark.parametrize(
        "btc_address",
        [
            # Bech32 (bc1) addresses
            "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
            "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq",
            "BC1QW508D6QEJXTDG4Y5R3ZARVARY0C5XW7KV8F3T4",  # uppercase
            # Legacy (1) addresses
            "1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2",
            "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
            # Legacy (3) addresses
            "3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy",
        ],
    )
    def test_extract_btc_wallet(
        self, collector: IntelCollector, btc_address: str
    ) -> None:
        """Test extraction of valid BTC wallet addresses."""
        text = f"Send payment to {btc_address} and confirm."
        result = collector.extract(text, message_index=0)

        assert result.has_iocs
        assert len(result.iocs) == 1
        assert result.iocs[0].ioc_type == IOCType.BTC_WALLET
        assert result.iocs[0].value.lower() == btc_address.lower()
        assert result.iocs[0].message_index == 0

    def test_extract_multiple_btc_wallets(self, collector: IntelCollector) -> None:
        """Test extraction of multiple BTC addresses in one message."""
        text = (
            "Primary: bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh "
            "Backup: 1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2"
        )
        result = collector.extract(text, message_index=0)

        assert len(result.iocs) == 2
        assert all(ioc.ioc_type == IOCType.BTC_WALLET for ioc in result.iocs)

    def test_btc_wallet_is_high_value(self, collector: IntelCollector) -> None:
        """Test that BTC wallets are marked as high-value IOCs."""
        text = "Send to bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"
        result = collector.extract(text, message_index=0)

        assert result.iocs[0].is_high_value
        assert result.high_value_count == 1

    # =========================================================================
    # IBAN Tests
    # =========================================================================

    @pytest.mark.parametrize(
        "iban",
        [
            "DE89370400440532013000",  # Germany
            "GB82WEST12345698765432",  # UK
            "FR7630006000011234567890189",  # France
            "PL61109010140000071219812874",  # Poland
            "NL91ABNA0417164300",  # Netherlands
        ],
    )
    def test_extract_iban(self, collector: IntelCollector, iban: str) -> None:
        """Test extraction of valid IBAN numbers."""
        text = f"Wire transfer to {iban} as soon as possible."
        result = collector.extract(text, message_index=0)

        assert result.has_iocs
        assert len(result.iocs) == 1
        assert result.iocs[0].ioc_type == IOCType.IBAN
        assert result.iocs[0].value.upper() == iban.upper()

    def test_iban_is_high_value(self, collector: IntelCollector) -> None:
        """Test that IBANs are marked as high-value IOCs."""
        text = "Send to DE89370400440532013000"
        result = collector.extract(text, message_index=0)

        assert result.iocs[0].is_high_value
        assert result.high_value_count == 1

    def test_invalid_iban_country_code_ignored(
        self, collector: IntelCollector
    ) -> None:
        """Test that invalid IBAN country codes are not extracted."""
        text = "Send to XX89370400440532013000"  # XX is not a valid country
        result = collector.extract(text, message_index=0)

        # Should not extract as IBAN
        assert not any(ioc.ioc_type == IOCType.IBAN for ioc in result.iocs)

    # =========================================================================
    # Phone Number Tests
    # =========================================================================

    @pytest.mark.parametrize(
        "phone",
        [
            "+1-555-123-4567",  # US international
            "+44 20 7123 4567",  # UK
            "+49 30 12345678",  # Germany
            "(555) 123-4567",  # US local
            "555-123-4567",  # US no area code prefix
            "+48123456789",  # Poland compact
        ],
    )
    def test_extract_phone_number(
        self, collector: IntelCollector, phone: str
    ) -> None:
        """Test extraction of valid phone numbers."""
        text = f"Call me at {phone} for details."
        result = collector.extract(text, message_index=0)

        assert result.has_iocs
        phone_iocs = [ioc for ioc in result.iocs if ioc.ioc_type == IOCType.PHONE]
        assert len(phone_iocs) >= 1

    def test_phone_not_high_value(self, collector: IntelCollector) -> None:
        """Test that phone numbers are not marked as high-value IOCs."""
        text = "Call me at +1-555-123-4567"
        result = collector.extract(text, message_index=0)

        phone_iocs = [ioc for ioc in result.iocs if ioc.ioc_type == IOCType.PHONE]
        if phone_iocs:
            assert not phone_iocs[0].is_high_value

    # =========================================================================
    # URL Tests
    # =========================================================================

    @pytest.mark.parametrize(
        "url",
        [
            "https://example.com",
            "http://malicious-site.com/phishing",
            "https://secure-payment.fake-bank.com/verify?id=123",
            "http://192.168.1.1/admin",
        ],
    )
    def test_extract_url(self, collector: IntelCollector, url: str) -> None:
        """Test extraction of valid URLs."""
        text = f"Click here: {url} to verify your account."
        result = collector.extract(text, message_index=0)

        assert result.has_iocs
        url_iocs = [ioc for ioc in result.iocs if ioc.ioc_type == IOCType.URL]
        assert len(url_iocs) == 1
        assert url in url_iocs[0].value

    def test_url_not_high_value(self, collector: IntelCollector) -> None:
        """Test that URLs are not marked as high-value IOCs."""
        text = "Visit https://example.com"
        result = collector.extract(text, message_index=0)

        url_iocs = [ioc for ioc in result.iocs if ioc.ioc_type == IOCType.URL]
        assert not url_iocs[0].is_high_value

    # =========================================================================
    # Mixed IOC Tests
    # =========================================================================

    def test_extract_mixed_iocs(self, collector: IntelCollector) -> None:
        """Test extraction of multiple IOC types from one message."""
        text = """
        Dear friend,

        Please send the payment to my Bitcoin wallet:
        bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh

        Or wire transfer to: DE89370400440532013000

        Call me at +1-555-123-4567 if you have questions.

        For more info: https://totally-legit-bank.com/verify

        Best regards
        """
        result = collector.extract(text, message_index=0)

        assert result.has_iocs

        # Check that we have multiple IOC types
        ioc_types = {ioc.ioc_type for ioc in result.iocs}
        assert IOCType.BTC_WALLET in ioc_types
        assert IOCType.IBAN in ioc_types
        assert IOCType.URL in ioc_types

    # =========================================================================
    # Edge Cases and Validation Tests
    # =========================================================================

    def test_empty_message(self, collector: IntelCollector) -> None:
        """Test extraction from empty message."""
        result = collector.extract("", message_index=0)
        assert not result.has_iocs
        assert len(result.iocs) == 0

    def test_no_iocs_in_message(self, collector: IntelCollector) -> None:
        """Test extraction from message without IOCs."""
        text = "Hello, I am a Nigerian prince and I need your help."
        result = collector.extract(text, message_index=0)
        assert not result.has_iocs

    def test_duplicate_iocs_deduplicated(self, collector: IntelCollector) -> None:
        """Test that duplicate IOCs are deduplicated."""
        btc = "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"
        text = f"Send to {btc}. Remember: {btc}. Again: {btc}."
        result = collector.extract(text, message_index=0)

        # Should only have one BTC wallet despite three mentions
        btc_iocs = [ioc for ioc in result.iocs if ioc.ioc_type == IOCType.BTC_WALLET]
        assert len(btc_iocs) == 1

    def test_context_included(self, collector: IntelCollector) -> None:
        """Test that surrounding context is included with IOC."""
        btc = "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"
        text = f"Please send funds to {btc} urgently."
        result = collector.extract(text, message_index=0)

        assert result.iocs[0].context is not None
        assert "send" in result.iocs[0].context.lower()

    def test_message_index_preserved(self, collector: IntelCollector) -> None:
        """Test that message index is correctly preserved in IOCs."""
        text = "Send to bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"
        result = collector.extract(text, message_index=5)

        assert result.message_index == 5
        assert result.iocs[0].message_index == 5

    def test_extraction_time_recorded(self, collector: IntelCollector) -> None:
        """Test that extraction time is recorded."""
        text = "Send to bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"
        result = collector.extract(text, message_index=0)

        assert result.extraction_time_ms >= 0


class TestExtractionResult:
    """Test ExtractionResult model properties."""

    def test_has_iocs_true(self) -> None:
        """Test has_iocs property when IOCs exist."""
        from phishguard.models.ioc import ExtractedIOC

        ioc = ExtractedIOC(
            ioc_type=IOCType.URL,
            value="https://example.com",
            message_index=0,
        )
        result = ExtractionResult(iocs=(ioc,), extraction_time_ms=10, message_index=0)
        assert result.has_iocs

    def test_has_iocs_false(self) -> None:
        """Test has_iocs property when no IOCs."""
        result = ExtractionResult(iocs=(), extraction_time_ms=10, message_index=0)
        assert not result.has_iocs

    def test_high_value_count(self) -> None:
        """Test high_value_count property."""
        from phishguard.models.ioc import ExtractedIOC

        iocs = (
            ExtractedIOC(
                ioc_type=IOCType.BTC_WALLET,
                value="bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
                message_index=0,
            ),
            ExtractedIOC(
                ioc_type=IOCType.IBAN,
                value="DE89370400440532013000",
                message_index=0,
            ),
            ExtractedIOC(
                ioc_type=IOCType.URL,
                value="https://example.com",
                message_index=0,
            ),
        )
        result = ExtractionResult(iocs=iocs, extraction_time_ms=10, message_index=0)

        # BTC and IBAN are high-value, URL is not
        assert result.high_value_count == 2
