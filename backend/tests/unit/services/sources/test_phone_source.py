"""Unit tests for PhoneNumberSource (US-037).

Local phonenumbers parsing requires no mocking.
NumVerify HTTP calls are mocked via httpx.MockTransport.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import patch

import httpx
import pytest

from phishguard.services.enrichment_service import EnrichmentSource
from phishguard.services.sources.phone_source import (
    PhoneNumberSource,
    _derive_reputation,
    _parse_locally,
    _unknown_payload,
)

# ---------------------------------------------------------------------------
# Test data
# ---------------------------------------------------------------------------

# Valid international phone numbers for testing
VOIP_NUMBER = "+12025551234"  # US number — phonenumbers may return FIXED_LINE_OR_MOBILE
MOBILE_NUMBER_PL = "+48501234567"  # Polish mobile
MOBILE_NUMBER_US = "+16505551234"  # US mobile
LANDLINE_UK = "+441234567890"  # UK landline
INVALID_NUMBER = "not-a-phone-number"
INVALID_SHORT = "+1"

NUMVERIFY_MOBILE_RESPONSE: dict[str, Any] = {
    "valid": True,
    "number": "48501234567",
    "local_format": "501234567",
    "international_format": "+48501234567",
    "country_prefix": "+48",
    "country_code": "PL",
    "country_name": "Poland",
    "location": "Poland",
    "carrier": "Play",
    "line_type": "mobile",
}

NUMVERIFY_VOIP_RESPONSE: dict[str, Any] = {
    "valid": True,
    "number": "12025551234",
    "local_format": "2025551234",
    "international_format": "+12025551234",
    "country_prefix": "+1",
    "country_code": "US",
    "country_name": "United States of America",
    "location": "Washington DC",
    "carrier": "VoIP Provider",
    "line_type": "voip",
}

NUMVERIFY_INVALID_RESPONSE: dict[str, Any] = {
    "valid": False,
    "number": "123",
}


# ---------------------------------------------------------------------------
# Helper to build a mock httpx transport
# ---------------------------------------------------------------------------


def _mock_transport(
    response_data: dict[str, Any], status_code: int = 200
) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=status_code,
            content=json.dumps(response_data).encode(),
            headers={"content-type": "application/json"},
        )

    return httpx.MockTransport(handler)


# ---------------------------------------------------------------------------
# Unit tests: _derive_reputation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "line_type, expected",
    [
        ("voip", "suspicious"),
        ("mobile", "clean"),
        ("landline", "clean"),
        ("unknown", "unknown"),
        ("other", "clean"),
    ],
)
def test_derive_reputation(line_type: str, expected: str) -> None:
    assert _derive_reputation(line_type) == expected


# ---------------------------------------------------------------------------
# Unit tests: _parse_locally
# ---------------------------------------------------------------------------


def test_parse_locally_invalid_returns_none() -> None:
    assert _parse_locally(INVALID_NUMBER) is None


def test_parse_locally_too_short_returns_none() -> None:
    assert _parse_locally(INVALID_SHORT) is None


def test_parse_locally_valid_mobile_pl() -> None:
    result = _parse_locally(MOBILE_NUMBER_PL)
    assert result is not None
    assert result["country_code"] == "PL"
    assert result["line_type"] in {"mobile", "unknown"}
    assert result["local_parse"] is True
    assert "reputation" in result


def test_parse_locally_valid_returns_country() -> None:
    result = _parse_locally(MOBILE_NUMBER_PL)
    assert result is not None
    assert result["country"] is not None
    assert "Poland" in result["country"]


def test_parse_locally_unknown_payload_structure() -> None:
    payload = _unknown_payload(reason="test")
    assert payload["reputation"] == "unknown"
    assert payload["line_type"] == "unknown"
    assert payload["error"] == "test"
    assert payload["local_parse"] is False


# ---------------------------------------------------------------------------
# Protocol compliance
# ---------------------------------------------------------------------------


def test_phone_source_satisfies_protocol() -> None:
    source = PhoneNumberSource(api_key="")
    assert isinstance(source, EnrichmentSource)
    assert "phone" in source.ioc_types
    assert source.name == "phonenumbers"
    assert source.rate_limit.requests_per_minute > 0
    assert source.rate_limit.requests_per_day > 0


# ---------------------------------------------------------------------------
# enrich() — local parsing only (no API key)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_enrich_valid_mobile_no_api_key() -> None:
    source = PhoneNumberSource(api_key="")
    result = await source.enrich("phone", MOBILE_NUMBER_PL)

    assert result["country_code"] == "PL"
    assert result["line_type"] in {"mobile", "unknown"}
    assert result["local_parse"] is True
    assert result["reputation"] in {"clean", "unknown", "suspicious"}


@pytest.mark.asyncio
async def test_enrich_invalid_number_raises() -> None:
    source = PhoneNumberSource(api_key="")
    with pytest.raises(ValueError, match="Invalid phone number"):
        await source.enrich("phone", INVALID_NUMBER)


@pytest.mark.asyncio
async def test_enrich_invalid_short_number_raises() -> None:
    source = PhoneNumberSource(api_key="")
    with pytest.raises(ValueError):
        await source.enrich("phone", INVALID_SHORT)


# ---------------------------------------------------------------------------
# enrich() — with NumVerify API key (mocked HTTP)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_enrich_with_numverify_mobile() -> None:
    transport = _mock_transport(NUMVERIFY_MOBILE_RESPONSE)
    async with httpx.AsyncClient(transport=transport) as client:
        source = PhoneNumberSource(api_key="test-key", http_client=client)
        result = await source.enrich("phone", MOBILE_NUMBER_PL)

    assert result["country_code"] == "PL"
    assert result["line_type"] == "mobile"
    assert result["carrier"] == "Play"
    assert result["reputation"] == "clean"
    assert result["numverify_valid"] is True


@pytest.mark.asyncio
async def test_enrich_with_numverify_voip_flagged_suspicious() -> None:
    transport = _mock_transport(NUMVERIFY_VOIP_RESPONSE)
    async with httpx.AsyncClient(transport=transport) as client:
        source = PhoneNumberSource(api_key="test-key", http_client=client)
        result = await source.enrich("phone", MOBILE_NUMBER_US)

    assert result["line_type"] == "voip"
    assert result["reputation"] == "suspicious"
    assert result["numverify_valid"] is True


@pytest.mark.asyncio
async def test_enrich_numverify_says_invalid_falls_back_to_local() -> None:
    transport = _mock_transport(NUMVERIFY_INVALID_RESPONSE)
    async with httpx.AsyncClient(transport=transport) as client:
        source = PhoneNumberSource(api_key="test-key", http_client=client)
        result = await source.enrich("phone", MOBILE_NUMBER_PL)

    # Falls back to local result with numverify_valid=False
    assert result["numverify_valid"] is False
    assert result["local_parse"] is True


@pytest.mark.asyncio
async def test_enrich_numverify_http_error_falls_back_to_local() -> None:
    def error_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=500, content=b"Internal Server Error")

    transport = httpx.MockTransport(error_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        source = PhoneNumberSource(api_key="test-key", http_client=client)
        result = await source.enrich("phone", MOBILE_NUMBER_PL)

    # Falls back gracefully to local parse result
    assert result["local_parse"] is True
    assert "reputation" in result


@pytest.mark.asyncio
async def test_enrich_numverify_network_error_falls_back_to_local() -> None:
    def network_error_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused")

    transport = httpx.MockTransport(network_error_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        source = PhoneNumberSource(api_key="test-key", http_client=client)
        result = await source.enrich("phone", MOBILE_NUMBER_PL)

    assert result["local_parse"] is True
    assert result["country_code"] == "PL"


# ---------------------------------------------------------------------------
# VoIP suspicion — AC: "VoIP lines flagged as higher suspicion"
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_voip_line_type_via_numverify_is_suspicious() -> None:
    transport = _mock_transport(NUMVERIFY_VOIP_RESPONSE)
    async with httpx.AsyncClient(transport=transport) as client:
        source = PhoneNumberSource(api_key="test-key", http_client=client)
        result = await source.enrich("phone", MOBILE_NUMBER_US)

    assert result["line_type"] == "voip"
    assert result["reputation"] == "suspicious"


# ---------------------------------------------------------------------------
# No external call for basic metadata — AC: "No external call required"
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_external_call_without_api_key() -> None:
    """Verify that without api_key no HTTP request is made."""
    call_count = 0

    def counting_handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(200, json=NUMVERIFY_MOBILE_RESPONSE)

    transport = httpx.MockTransport(counting_handler)
    # Even though we pass a client, no api_key means no call
    async with httpx.AsyncClient(transport=transport) as client:
        source = PhoneNumberSource(api_key="", http_client=client)
        result = await source.enrich("phone", MOBILE_NUMBER_PL)

    assert call_count == 0
    assert result["local_parse"] is True
