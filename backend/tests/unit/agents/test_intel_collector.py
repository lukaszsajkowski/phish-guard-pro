"""Unit tests for IntelCollector IOC extraction."""

import pytest

from phishguard.agents.intel_collector import IntelCollector, ExtractionResult
from phishguard.models.ioc import IOCType


class TestIntelCollector:
    """Test cases for IntelCollector."""

    @pytest.fixture
    def collector(self) -> IntelCollector:
        """Create IntelCollector instance."""
        return IntelCollector()

    def test_extract_btc_bech32_wallet(self, collector: IntelCollector) -> None:
        """Test extraction of Bech32 BTC wallet addresses."""
        text = "Send money to bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh please"
        result = collector.extract(text, message_index=0)

        assert result.has_iocs
        assert len(result.iocs) == 1
        assert result.iocs[0].ioc_type == IOCType.BTC_WALLET
        assert result.iocs[0].value == "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"
        assert result.iocs[0].is_high_value

    def test_extract_btc_legacy_wallet(self, collector: IntelCollector) -> None:
        """Test extraction of legacy (1/3 prefix) BTC wallet addresses."""
        text = "Transfer funds to 1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2"
        result = collector.extract(text, message_index=1)

        assert result.has_iocs
        assert len(result.iocs) == 1
        assert result.iocs[0].ioc_type == IOCType.BTC_WALLET

    def test_extract_iban(self, collector: IntelCollector) -> None:
        """Test extraction of IBAN numbers."""
        text = "Please wire money to DE89370400440532013000"
        result = collector.extract(text, message_index=2)

        assert result.has_iocs
        assert len(result.iocs) == 1
        assert result.iocs[0].ioc_type == IOCType.IBAN
        assert result.iocs[0].value == "DE89370400440532013000"
        assert result.iocs[0].is_high_value

    def test_extract_phone_number(self, collector: IntelCollector) -> None:
        """Test extraction of phone numbers."""
        text = "Call me at +1-555-123-4567 for details"
        result = collector.extract(text, message_index=3)

        assert result.has_iocs
        assert len(result.iocs) == 1
        assert result.iocs[0].ioc_type == IOCType.PHONE

    def test_extract_url(self, collector: IntelCollector) -> None:
        """Test extraction of URLs."""
        text = "Click here: https://scam-site.com/payment to continue"
        result = collector.extract(text, message_index=4)

        assert result.has_iocs
        assert len(result.iocs) == 1
        assert result.iocs[0].ioc_type == IOCType.URL
        assert "scam-site.com" in result.iocs[0].value

    def test_extract_multiple_iocs(self, collector: IntelCollector) -> None:
        """Test extraction of multiple IOC types from single message."""
        text = """
        Send BTC to bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh
        Or wire to IBAN GB82WEST12345698765432
        Call +44 20 7123 4567 if you have questions
        More info at https://example-scam.com/details
        """
        result = collector.extract(text, message_index=5)

        assert result.has_iocs
        assert len(result.iocs) == 4
        assert result.high_value_count == 2  # BTC + IBAN

        ioc_types = {ioc.ioc_type for ioc in result.iocs}
        assert IOCType.BTC_WALLET in ioc_types
        assert IOCType.IBAN in ioc_types
        assert IOCType.PHONE in ioc_types
        assert IOCType.URL in ioc_types

    def test_no_iocs_in_clean_text(self, collector: IntelCollector) -> None:
        """Test that clean text returns no IOCs."""
        text = "Hello, I am interested in your proposal. Please tell me more."
        result = collector.extract(text, message_index=6)

        assert not result.has_iocs
        assert len(result.iocs) == 0

    def test_context_extraction(self, collector: IntelCollector) -> None:
        """Test that context is included with extracted IOCs."""
        text = "Please send payment to bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh immediately"
        result = collector.extract(text, message_index=7)

        assert result.has_iocs
        assert result.iocs[0].context is not None
        assert "payment" in result.iocs[0].context

    def test_extraction_time_ms(self, collector: IntelCollector) -> None:
        """Test that extraction time is recorded."""
        text = "Some text with bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"
        result = collector.extract(text, message_index=8)

        assert result.extraction_time_ms >= 0

    def test_message_index_preserved(self, collector: IntelCollector) -> None:
        """Test that message index is preserved in results."""
        text = "Call +1-555-123-4567"
        result = collector.extract(text, message_index=42)

        assert result.message_index == 42
        assert result.iocs[0].message_index == 42

    def test_deduplication(self, collector: IntelCollector) -> None:
        """Test that duplicate IOCs are deduplicated."""
        text = """
        Send to bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh
        and confirm at bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh
        """
        result = collector.extract(text, message_index=9)

        assert len(result.iocs) == 1  # Only one, not two

    def test_invalid_iban_country_rejected(self, collector: IntelCollector) -> None:
        """Test that invalid IBAN country codes are rejected."""
        text = "Send to XX12345678901234567890"  # XX is not valid
        result = collector.extract(text, message_index=10)

        # Should not match as IBAN
        assert not any(ioc.ioc_type == IOCType.IBAN for ioc in result.iocs)
