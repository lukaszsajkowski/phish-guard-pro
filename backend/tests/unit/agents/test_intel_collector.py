"""Unit tests for IntelCollector IOC extraction."""

import pytest

from phishguard.agents.intel_collector import IntelCollector
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
        text = (
            "Please send payment to bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh "
            "immediately"
        )
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


class TestIPExtraction:
    """Test cases for IPv4/IPv6 extraction (US-036)."""

    @pytest.fixture
    def collector(self) -> IntelCollector:
        """Create IntelCollector instance."""
        return IntelCollector()

    def test_extract_ipv4(self, collector: IntelCollector) -> None:
        """Test extraction of a public IPv4 address."""
        text = "The attacker's server is at 185.220.101.1 in Germany"
        result = collector.extract(text, message_index=0)

        assert result.has_iocs
        ip_iocs = [ioc for ioc in result.iocs if ioc.ioc_type == IOCType.IP]
        assert len(ip_iocs) == 1
        assert ip_iocs[0].value == "185.220.101.1"

    def test_extract_ipv6(self, collector: IntelCollector) -> None:
        """Test extraction of an IPv6 address."""
        text = "Also reachable at 2001:0db8:85a3:0000:0000:8a2e:0370:7334 via IPv6"
        result = collector.extract(text, message_index=0)

        assert result.has_iocs
        ip_iocs = [ioc for ioc in result.iocs if ioc.ioc_type == IOCType.IP]
        assert len(ip_iocs) == 1
        assert "2001:0db8:85a3" in ip_iocs[0].value

    def test_private_ipv4_loopback_excluded(self, collector: IntelCollector) -> None:
        """Test that loopback addresses (127.x.x.x) are NOT extracted."""
        text = "Test on 127.0.0.1 localhost"
        result = collector.extract(text, message_index=0)

        ip_iocs = [ioc for ioc in result.iocs if ioc.ioc_type == IOCType.IP]
        assert len(ip_iocs) == 0

    def test_private_ipv4_class_a_excluded(self, collector: IntelCollector) -> None:
        """Test that 10.x.x.x private addresses are NOT extracted."""
        text = "Internal server at 10.0.1.50"
        result = collector.extract(text, message_index=0)

        ip_iocs = [ioc for ioc in result.iocs if ioc.ioc_type == IOCType.IP]
        assert len(ip_iocs) == 0

    def test_private_ipv4_class_b_excluded(self, collector: IntelCollector) -> None:
        """Test that 172.16-31.x.x private addresses are NOT extracted."""
        text = "Internal server at 172.16.0.1"
        result = collector.extract(text, message_index=0)

        ip_iocs = [ioc for ioc in result.iocs if ioc.ioc_type == IOCType.IP]
        assert len(ip_iocs) == 0

    def test_private_ipv4_class_c_excluded(self, collector: IntelCollector) -> None:
        """Test that 192.168.x.x private addresses are NOT extracted."""
        text = "Router at 192.168.1.1"
        result = collector.extract(text, message_index=0)

        ip_iocs = [ioc for ioc in result.iocs if ioc.ioc_type == IOCType.IP]
        assert len(ip_iocs) == 0

    def test_private_ipv4_link_local_excluded(self, collector: IntelCollector) -> None:
        """Test that 169.254.x.x link-local addresses are NOT extracted."""
        text = "APIPA address 169.254.1.100"
        result = collector.extract(text, message_index=0)

        ip_iocs = [ioc for ioc in result.iocs if ioc.ioc_type == IOCType.IP]
        assert len(ip_iocs) == 0

    def test_ip_inside_url_not_double_extracted(
        self, collector: IntelCollector
    ) -> None:
        """Test that an IP in a URL is NOT also extracted as a standalone IOC."""
        text = "Visit http://93.184.216.34/login for details"
        result = collector.extract(text, message_index=0)

        url_iocs = [ioc for ioc in result.iocs if ioc.ioc_type == IOCType.URL]
        ip_iocs = [ioc for ioc in result.iocs if ioc.ioc_type == IOCType.IP]

        assert len(url_iocs) == 1
        assert len(ip_iocs) == 0  # IP inside URL should be excluded

    def test_multiple_ips_extracted(self, collector: IntelCollector) -> None:
        """Test extraction of multiple IPs from a single message."""
        text = "C2 servers: 45.33.32.156 and 104.244.42.1"
        result = collector.extract(text, message_index=0)

        ip_iocs = [ioc for ioc in result.iocs if ioc.ioc_type == IOCType.IP]
        assert len(ip_iocs) == 2
        values = {ioc.value for ioc in ip_iocs}
        assert "45.33.32.156" in values
        assert "104.244.42.1" in values

    def test_ip_with_other_ioc_types(self, collector: IntelCollector) -> None:
        """Test that IPs are extracted alongside other IOC types."""
        text = """
        C2 at 185.220.101.1
        Payment to bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh
        """
        result = collector.extract(text, message_index=0)

        ioc_types = {ioc.ioc_type for ioc in result.iocs}
        assert IOCType.IP in ioc_types
        assert IOCType.BTC_WALLET in ioc_types

    def test_ip_not_high_value(self, collector: IntelCollector) -> None:
        """Test that IP IOCs are NOT marked as high value."""
        text = "Server at 185.220.101.1"
        result = collector.extract(text, message_index=0)

        ip_iocs = [ioc for ioc in result.iocs if ioc.ioc_type == IOCType.IP]
        assert len(ip_iocs) == 1
        assert not ip_iocs[0].is_high_value

    def test_public_172_range_not_excluded(self, collector: IntelCollector) -> None:
        """Test that 172.x addresses outside 172.16-31 range ARE extracted."""
        text = "Server at 172.32.0.1"
        result = collector.extract(text, message_index=0)

        ip_iocs = [ioc for ioc in result.iocs if ioc.ioc_type == IOCType.IP]
        assert len(ip_iocs) == 1
        assert ip_iocs[0].value == "172.32.0.1"
