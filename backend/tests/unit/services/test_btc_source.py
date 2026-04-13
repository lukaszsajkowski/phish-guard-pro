"""Unit tests for BtcEnrichmentSource (US-034).

All HTTP calls are mocked via ``httpx.MockTransport`` — no real network
traffic is generated.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from phishguard.services.sources.btc_source import (
    BtcEnrichmentSource,
    _derive_reputation,
    _is_valid_btc_address,
    _parse_onchain,
)

# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------

VALID_BECH32 = "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"
VALID_P2PKH = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
VALID_P2SH = "3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy"
INVALID_ADDRESS = "notabitcoinaddress"

ESPLORA_RESPONSE: dict[str, Any] = {
    "address": VALID_BECH32,
    "chain_stats": {
        "funded_txo_count": 5,
        "funded_txo_sum": 500_000_000,  # 5 BTC
        "spent_txo_count": 3,
        "spent_txo_sum": 200_000_000,  # 2 BTC
        "tx_count": 8,
    },
    "mempool_stats": {
        "funded_txo_count": 0,
        "funded_txo_sum": 0,
        "spent_txo_count": 0,
        "spent_txo_sum": 0,
        "tx_count": 0,
    },
}

ABUSE_RESPONSE_MALICIOUS: dict[str, Any] = {
    "address": VALID_BECH32,
    "count": 5,
    "recent": [
        {"abuse_type": "ransomware", "abuse_type_other": None},
        {"abuse_type": "sextortion", "abuse_type_other": None},
    ],
}

ABUSE_RESPONSE_SUSPICIOUS: dict[str, Any] = {
    "address": VALID_BECH32,
    "count": 1,
    "recent": [{"abuse_type": "other", "abuse_type_other": "phishing"}],
}

ABUSE_RESPONSE_CLEAN: dict[str, Any] = {
    "address": VALID_BECH32,
    "count": 0,
    "recent": [],
}


def _make_transport(
    *,
    mempool_response: httpx.Response | Exception | None = None,
    blockstream_response: httpx.Response | Exception | None = None,
    abuse_response: httpx.Response | Exception | None = None,
) -> httpx.MockTransport:
    """Build a MockTransport that routes by URL host."""

    def handler(request: httpx.Request) -> httpx.Response:
        host = request.url.host

        if host == "mempool.space":
            if isinstance(mempool_response, Exception):
                raise mempool_response
            if mempool_response is not None:
                return mempool_response
            # Default: success
            return httpx.Response(200, json=ESPLORA_RESPONSE)

        if host == "blockstream.info":
            if isinstance(blockstream_response, Exception):
                raise blockstream_response
            if blockstream_response is not None:
                return blockstream_response
            return httpx.Response(200, json=ESPLORA_RESPONSE)

        if host == "www.bitcoinabuse.com":
            if isinstance(abuse_response, Exception):
                raise abuse_response
            if abuse_response is not None:
                return abuse_response
            return httpx.Response(200, json=ABUSE_RESPONSE_CLEAN)

        return httpx.Response(404, text="Not Found")

    return httpx.MockTransport(handler)


def _make_source(
    transport: httpx.MockTransport,
    api_key: str = "test-key",
) -> BtcEnrichmentSource:
    client = httpx.AsyncClient(transport=transport)
    return BtcEnrichmentSource(
        bitcoinabuse_api_key=api_key,
        http_client=client,
    )


# ---------------------------------------------------------------------------
# Address validation
# ---------------------------------------------------------------------------


class TestBtcAddressValidation:
    def test_valid_bech32(self) -> None:
        assert _is_valid_btc_address(VALID_BECH32) is True

    def test_valid_p2pkh(self) -> None:
        assert _is_valid_btc_address(VALID_P2PKH) is True

    def test_valid_p2sh(self) -> None:
        assert _is_valid_btc_address(VALID_P2SH) is True

    def test_invalid_address(self) -> None:
        assert _is_valid_btc_address(INVALID_ADDRESS) is False

    def test_empty_string(self) -> None:
        assert _is_valid_btc_address("") is False


# ---------------------------------------------------------------------------
# Reputation derivation
# ---------------------------------------------------------------------------


class TestReputationDerivation:
    def test_malicious_threshold(self) -> None:
        assert _derive_reputation(3) == "malicious"
        assert _derive_reputation(100) == "malicious"

    def test_suspicious_threshold(self) -> None:
        assert _derive_reputation(1) == "suspicious"
        assert _derive_reputation(2) == "suspicious"

    def test_unknown_zero(self) -> None:
        assert _derive_reputation(0) == "unknown"


# ---------------------------------------------------------------------------
# On-chain parsing
# ---------------------------------------------------------------------------


class TestParseOnchain:
    def test_balance_calculation(self) -> None:
        result = _parse_onchain(ESPLORA_RESPONSE)
        # 500M - 200M sats = 300M sats = 3.0 BTC
        assert result["balance_btc"] == 3.0
        assert result["balance_sats"] == 300_000_000
        assert result["tx_count"] == 8

    def test_empty_stats(self) -> None:
        result = _parse_onchain({"chain_stats": {}, "mempool_stats": {}})
        assert result["balance_btc"] == 0.0
        assert result["tx_count"] == 0


# ---------------------------------------------------------------------------
# Full enrichment — happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_enrich_valid_address_with_clean_reputation() -> None:
    transport = _make_transport()
    source = _make_source(transport)

    result = await source.enrich("btc", VALID_BECH32)

    assert result["balance_btc"] == 3.0
    assert result["tx_count"] == 8
    assert result["reputation"] == "unknown"
    assert result["report_count"] == 0
    assert "error" not in result


@pytest.mark.asyncio
async def test_enrich_valid_address_with_malicious_reputation() -> None:
    transport = _make_transport(
        abuse_response=httpx.Response(200, json=ABUSE_RESPONSE_MALICIOUS),
    )
    source = _make_source(transport)

    result = await source.enrich("btc", VALID_BECH32)

    assert result["balance_btc"] == 3.0
    assert result["reputation"] == "malicious"
    assert result["report_count"] == 5
    assert result["most_recent_category"] == "ransomware"


@pytest.mark.asyncio
async def test_enrich_valid_address_with_suspicious_reputation() -> None:
    transport = _make_transport(
        abuse_response=httpx.Response(200, json=ABUSE_RESPONSE_SUSPICIOUS),
    )
    source = _make_source(transport)

    result = await source.enrich("btc", VALID_BECH32)

    assert result["reputation"] == "suspicious"
    assert result["report_count"] == 1
    assert result["most_recent_category"] == "phishing"


# ---------------------------------------------------------------------------
# Invalid address
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_enrich_invalid_address_returns_unknown_no_raise() -> None:
    """AC: Error when wallet invalid -> reputation: 'unknown'."""
    transport = _make_transport()
    source = _make_source(transport)

    result = await source.enrich("btc", INVALID_ADDRESS)

    assert result["reputation"] == "unknown"
    assert result["error"] == "invalid_btc_address"
    assert result["balance_btc"] is None


# ---------------------------------------------------------------------------
# Fallback: mempool.space fails -> Blockstream.info
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fallback_to_blockstream_when_mempool_fails() -> None:
    """AC: Blockstream.info configured as on-chain fallback."""
    transport = _make_transport(
        mempool_response=httpx.ConnectError("mempool down"),
        blockstream_response=httpx.Response(200, json=ESPLORA_RESPONSE),
    )
    source = _make_source(transport)

    result = await source.enrich("btc", VALID_BECH32)

    assert result["balance_btc"] == 3.0
    assert result["tx_count"] == 8
    assert "error" not in result


@pytest.mark.asyncio
async def test_both_onchain_sources_fail_raises() -> None:
    """When both mempool.space and Blockstream.info fail, enrich() raises.

    The EnrichmentService wraps this into status='unavailable'.
    """
    transport = _make_transport(
        mempool_response=httpx.ConnectError("mempool down"),
        blockstream_response=httpx.ConnectError("blockstream down"),
    )
    source = _make_source(transport)

    with pytest.raises(httpx.HTTPStatusError):
        await source.enrich("btc", VALID_BECH32)


# ---------------------------------------------------------------------------
# Abuse API failure — graceful degradation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_abuse_api_failure_still_returns_onchain_data() -> None:
    """AC: abuse failure -> on-chain data with reputation: unknown."""
    transport = _make_transport(
        abuse_response=httpx.ConnectError("bitcoinabuse down"),
    )
    source = _make_source(transport)

    result = await source.enrich("btc", VALID_BECH32)

    # On-chain data present
    assert result["balance_btc"] == 3.0
    assert result["tx_count"] == 8
    # Abuse gracefully degraded
    assert result["reputation"] == "unknown"
    assert result["report_count"] == 0


@pytest.mark.asyncio
async def test_abuse_api_500_still_returns_onchain_data() -> None:
    transport = _make_transport(
        abuse_response=httpx.Response(500, text="Internal Server Error"),
    )
    source = _make_source(transport)

    result = await source.enrich("btc", VALID_BECH32)

    assert result["balance_btc"] == 3.0
    assert result["reputation"] == "unknown"


# ---------------------------------------------------------------------------
# No API key configured — skip abuse lookup
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_api_key_skips_abuse_lookup() -> None:
    transport = _make_transport()
    source = _make_source(transport, api_key="")

    result = await source.enrich("btc", VALID_BECH32)

    assert result["balance_btc"] == 3.0
    assert result["reputation"] == "unknown"
    assert result["report_count"] == 0


# ---------------------------------------------------------------------------
# Protocol compliance
# ---------------------------------------------------------------------------


class TestProtocolCompliance:
    def test_has_required_attributes(self) -> None:
        source = BtcEnrichmentSource(bitcoinabuse_api_key="k")
        assert source.name == "btc_mempool"
        assert source.ioc_types == {"btc"}
        assert source.rate_limit.requests_per_minute == 30
        assert source.rate_limit.requests_per_day == 5_000

    def test_satisfies_enrichment_source_protocol(self) -> None:
        from phishguard.services.enrichment_service import EnrichmentSource

        source = BtcEnrichmentSource(bitcoinabuse_api_key="k")
        assert isinstance(source, EnrichmentSource)
