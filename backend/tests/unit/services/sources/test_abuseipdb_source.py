"""Unit tests for AbuseIPDBSource (US-036).

All HTTP calls are mocked via ``httpx.MockTransport`` — no real network
traffic is generated.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from phishguard.services.enrichment_service import EnrichmentSource
from phishguard.services.sources.abuseipdb_source import (
    AbuseIPDBSource,
    _build_payload,
    _derive_reputation,
)

# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------

TEST_IP = "185.220.101.1"
ABUSEIPDB_API_KEY = "test-abuseipdb-api-key"

ABUSEIPDB_MALICIOUS_RESPONSE: dict[str, Any] = {
    "data": {
        "ipAddress": TEST_IP,
        "isPublic": True,
        "ipVersion": 4,
        "isWhitelisted": False,
        "abuseConfidenceScore": 85,
        "countryCode": "DE",
        "usageType": "Data Center/Web Hosting/Transit",
        "isp": "Hetzner Online GmbH",
        "domain": "hetzner.com",
        "hostnames": [],
        "isTor": True,
        "totalReports": 42,
        "numDistinctUsers": 15,
        "lastReportedAt": "2026-04-10T12:00:00+00:00",
    }
}

ABUSEIPDB_CLEAN_RESPONSE: dict[str, Any] = {
    "data": {
        "ipAddress": "8.8.8.8",
        "isPublic": True,
        "ipVersion": 4,
        "isWhitelisted": True,
        "abuseConfidenceScore": 0,
        "countryCode": "US",
        "usageType": "Content Delivery Network",
        "isp": "Google LLC",
        "domain": "google.com",
        "hostnames": ["dns.google"],
        "isTor": False,
        "totalReports": 0,
        "numDistinctUsers": 0,
        "lastReportedAt": None,
    }
}

ABUSEIPDB_SUSPICIOUS_RESPONSE: dict[str, Any] = {
    "data": {
        "ipAddress": "203.0.113.50",
        "isPublic": True,
        "ipVersion": 4,
        "isWhitelisted": False,
        "abuseConfidenceScore": 30,
        "countryCode": "CN",
        "usageType": "Fixed Line ISP",
        "isp": "China Telecom",
        "domain": "chinatelecom.com.cn",
        "hostnames": [],
        "isTor": False,
        "totalReports": 5,
        "numDistinctUsers": 3,
        "lastReportedAt": "2026-03-20T08:30:00+00:00",
    }
}


def _make_transport(
    *,
    check_response: httpx.Response | Exception | None = None,
) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path

        if "/api/v2/check" in path:
            if isinstance(check_response, Exception):
                raise check_response
            if check_response is not None:
                return check_response
            return httpx.Response(200, json=ABUSEIPDB_MALICIOUS_RESPONSE)

        return httpx.Response(404, text="Not Found")

    return httpx.MockTransport(handler)


def _make_source(
    transport: httpx.MockTransport,
    api_key: str = ABUSEIPDB_API_KEY,
) -> AbuseIPDBSource:
    client = httpx.AsyncClient(transport=transport)
    return AbuseIPDBSource(api_key=api_key, http_client=client)


# ---------------------------------------------------------------------------
# Helper unit tests
# ---------------------------------------------------------------------------


class TestDeriveReputation:
    def test_malicious(self) -> None:
        assert _derive_reputation(75) == "malicious"
        assert _derive_reputation(100) == "malicious"
        assert _derive_reputation(85) == "malicious"

    def test_suspicious(self) -> None:
        assert _derive_reputation(25) == "suspicious"
        assert _derive_reputation(50) == "suspicious"
        assert _derive_reputation(74) == "suspicious"

    def test_clean(self) -> None:
        assert _derive_reputation(0) == "clean"
        assert _derive_reputation(10) == "clean"
        assert _derive_reputation(24) == "clean"


class TestBuildPayload:
    def test_malicious_payload(self) -> None:
        result = _build_payload(ABUSEIPDB_MALICIOUS_RESPONSE)
        assert result["abuse_confidence_score"] == 85
        assert result["total_reports"] == 42
        assert result["country_code"] == "DE"
        assert result["isp"] == "Hetzner Online GmbH"
        assert result["domain"] == "hetzner.com"
        assert result["is_tor"] is True
        assert result["reputation"] == "malicious"
        assert "error" not in result

    def test_clean_payload(self) -> None:
        result = _build_payload(ABUSEIPDB_CLEAN_RESPONSE)
        assert result["abuse_confidence_score"] == 0
        assert result["total_reports"] == 0
        assert result["country_code"] == "US"
        assert result["isp"] == "Google LLC"
        assert result["is_tor"] is False
        assert result["reputation"] == "clean"
        assert "error" not in result

    def test_suspicious_payload(self) -> None:
        result = _build_payload(ABUSEIPDB_SUSPICIOUS_RESPONSE)
        assert result["abuse_confidence_score"] == 30
        assert result["total_reports"] == 5
        assert result["country_code"] == "CN"
        assert result["reputation"] == "suspicious"
        assert "error" not in result


# ---------------------------------------------------------------------------
# Full enrichment — happy path (malicious IP)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_enrich_ip_malicious() -> None:
    transport = _make_transport()
    source = _make_source(transport)

    result = await source.enrich("ip", TEST_IP)

    assert result["abuse_confidence_score"] == 85
    assert result["total_reports"] == 42
    assert result["country_code"] == "DE"
    assert result["isp"] == "Hetzner Online GmbH"
    assert result["domain"] == "hetzner.com"
    assert result["is_tor"] is True
    assert result["reputation"] == "malicious"
    assert "error" not in result


# ---------------------------------------------------------------------------
# Full enrichment — clean IP
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_enrich_ip_clean() -> None:
    transport = _make_transport(
        check_response=httpx.Response(200, json=ABUSEIPDB_CLEAN_RESPONSE),
    )
    source = _make_source(transport)

    result = await source.enrich("ip", "8.8.8.8")

    assert result["abuse_confidence_score"] == 0
    assert result["total_reports"] == 0
    assert result["reputation"] == "clean"


# ---------------------------------------------------------------------------
# Full enrichment — suspicious IP
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_enrich_ip_suspicious() -> None:
    transport = _make_transport(
        check_response=httpx.Response(200, json=ABUSEIPDB_SUSPICIOUS_RESPONSE),
    )
    source = _make_source(transport)

    result = await source.enrich("ip", "203.0.113.50")

    assert result["abuse_confidence_score"] == 30
    assert result["total_reports"] == 5
    assert result["reputation"] == "suspicious"


# ---------------------------------------------------------------------------
# No API key — returns unknown without HTTP call
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_enrich_no_api_key() -> None:
    transport = _make_transport()
    source = _make_source(transport, api_key="")

    result = await source.enrich("ip", TEST_IP)

    assert result["reputation"] == "unknown"
    assert result["error"] == "no_api_key_configured"
    assert result["abuse_confidence_score"] == 0
    assert result["total_reports"] == 0


# ---------------------------------------------------------------------------
# HTTP errors — raise so EnrichmentService wraps graceful fallback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_enrich_http_error_raises() -> None:
    transport = _make_transport(
        check_response=httpx.Response(500, text="Internal Server Error"),
    )
    source = _make_source(transport)

    with pytest.raises(httpx.HTTPStatusError):
        await source.enrich("ip", TEST_IP)


@pytest.mark.asyncio
async def test_enrich_connect_error_raises() -> None:
    transport = _make_transport(
        check_response=httpx.ConnectError("AbuseIPDB down"),
    )
    source = _make_source(transport)

    with pytest.raises(httpx.ConnectError):
        await source.enrich("ip", TEST_IP)


@pytest.mark.asyncio
async def test_enrich_rate_limit_429_raises() -> None:
    transport = _make_transport(
        check_response=httpx.Response(429, text="Too Many Requests"),
    )
    source = _make_source(transport)

    with pytest.raises(httpx.HTTPStatusError):
        await source.enrich("ip", TEST_IP)


# ---------------------------------------------------------------------------
# Protocol compliance
# ---------------------------------------------------------------------------


class TestProtocolCompliance:
    def test_has_required_attributes(self) -> None:
        source = AbuseIPDBSource(api_key="k")
        assert source.name == "abuseipdb"
        assert source.ioc_types == {"ip"}
        assert source.rate_limit.requests_per_minute == 60
        assert source.rate_limit.requests_per_day == 1000

    def test_satisfies_enrichment_source_protocol(self) -> None:
        source = AbuseIPDBSource(api_key="k")
        assert isinstance(source, EnrichmentSource)


# ---------------------------------------------------------------------------
# Quota endpoint (integration via TestClient)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_quota_endpoint_includes_abuseipdb() -> None:
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient

    from phishguard.api.routers import enrichment as enrichment_mod

    # Reset singleton
    enrichment_mod._enrichment_service = None

    app = FastAPI()
    app.include_router(enrichment_mod.router, prefix="/api")

    # Override auth dependency
    app.dependency_overrides[enrichment_mod.get_current_user_id] = lambda: "test-user"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/enrichment/quota")

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 3  # btc_mempool + virustotal + abuseipdb

    source_names = {item["source"] for item in data}
    assert "abuseipdb" in source_names

    abuseipdb_quota = next(item for item in data if item["source"] == "abuseipdb")
    assert abuseipdb_quota["limit_per_minute"] == 60
    assert abuseipdb_quota["limit_per_day"] == 1000
    assert abuseipdb_quota["requests_used_minute"] == 0
    assert abuseipdb_quota["requests_used_day"] == 0
    assert abuseipdb_quota["available_day"] == 1000

    # Cleanup
    enrichment_mod._enrichment_service = None
