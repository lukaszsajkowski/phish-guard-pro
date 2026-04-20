"""Unit tests for VirusTotalSource (US-035).

All HTTP calls are mocked via ``httpx.MockTransport`` — no real network
traffic is generated.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from phishguard.services.enrichment_service import EnrichmentSource
from phishguard.services.sources.vt_source import (
    VirusTotalSource,
    _build_payload,
    _derive_reputation,
    _make_url_id,
)

# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------

TEST_URL = "http://evil.example.com/phish"
TEST_DOMAIN = "evil.example.com"
VT_API_KEY = "test-vt-api-key"

VT_URL_RESPONSE: dict[str, Any] = {
    "data": {
        "type": "url",
        "id": "some-id",
        "attributes": {
            "last_analysis_stats": {
                "malicious": 3,
                "suspicious": 1,
                "undetected": 60,
                "harmless": 8,
            },
            "categories": {
                "Forcepoint ThreatSeeker": "phishing",
                "sophos": "malware",
                "BitDefender": "phishing",
            },
            "last_analysis_date": 1744243200,  # 2025-04-10 00:00:00 UTC
        },
    }
}

VT_DOMAIN_RESPONSE: dict[str, Any] = {
    "data": {
        "type": "domain",
        "id": TEST_DOMAIN,
        "attributes": {
            "last_analysis_stats": {
                "malicious": 5,
                "suspicious": 0,
                "undetected": 55,
                "harmless": 12,
            },
            "categories": {
                "Forcepoint ThreatSeeker": "phishing",
                "sophos": "malware",
                "Webroot": "phishing",
            },
            "creation_date": 1740787200,  # 2025-03-01 00:00:00 UTC
            "last_analysis_date": 1744243200,
        },
    }
}

VT_CLEAN_RESPONSE: dict[str, Any] = {
    "data": {
        "type": "url",
        "id": "clean-id",
        "attributes": {
            "last_analysis_stats": {
                "malicious": 0,
                "suspicious": 0,
                "undetected": 65,
                "harmless": 7,
            },
            "categories": {},
            "last_analysis_date": 1744243200,
        },
    }
}

VT_SUSPICIOUS_ONLY_RESPONSE: dict[str, Any] = {
    "data": {
        "type": "url",
        "id": "susp-id",
        "attributes": {
            "last_analysis_stats": {
                "malicious": 0,
                "suspicious": 2,
                "undetected": 63,
                "harmless": 7,
            },
            "categories": {"sophos": "suspicious"},
            "last_analysis_date": 1744243200,
        },
    }
}


def _make_transport(
    *,
    url_get_response: httpx.Response | Exception | None = None,
    url_post_response: httpx.Response | Exception | None = None,
    domain_response: httpx.Response | Exception | None = None,
) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path

        if request.method == "GET" and "/api/v3/urls/" in path:
            if isinstance(url_get_response, Exception):
                raise url_get_response
            if url_get_response is not None:
                return url_get_response
            return httpx.Response(200, json=VT_URL_RESPONSE)

        if request.method == "POST" and path == "/api/v3/urls":
            if isinstance(url_post_response, Exception):
                raise url_post_response
            if url_post_response is not None:
                return url_post_response
            return httpx.Response(200, json={"data": {"id": "analysis-id"}})

        if "/api/v3/domains/" in path:
            if isinstance(domain_response, Exception):
                raise domain_response
            if domain_response is not None:
                return domain_response
            return httpx.Response(200, json=VT_DOMAIN_RESPONSE)

        return httpx.Response(404, text="Not Found")

    return httpx.MockTransport(handler)


def _make_source(
    transport: httpx.MockTransport,
    api_key: str = VT_API_KEY,
) -> VirusTotalSource:
    client = httpx.AsyncClient(transport=transport)
    return VirusTotalSource(api_key=api_key, http_client=client)


# ---------------------------------------------------------------------------
# Helper unit tests
# ---------------------------------------------------------------------------


class TestMakeUrlId:
    def test_encodes_url_to_base64url_no_padding(self) -> None:
        url_id = _make_url_id("http://example.com")
        assert "=" not in url_id
        assert isinstance(url_id, str)
        assert len(url_id) > 0

    def test_different_urls_produce_different_ids(self) -> None:
        assert _make_url_id("http://a.com") != _make_url_id("http://b.com")


class TestDeriveReputation:
    def test_malicious(self) -> None:
        assert _derive_reputation(3, 0) == "malicious"
        assert _derive_reputation(1, 5) == "malicious"

    def test_suspicious(self) -> None:
        assert _derive_reputation(0, 1) == "suspicious"
        assert _derive_reputation(0, 10) == "suspicious"

    def test_clean(self) -> None:
        assert _derive_reputation(0, 0) == "clean"


class TestBuildPayload:
    def test_url_payload(self) -> None:
        result = _build_payload(VT_URL_RESPONSE, is_domain=False)
        assert result["detection_score"] == "3/72"
        assert result["malicious"] == 3
        assert result["suspicious"] == 1
        assert result["total_engines"] == 72
        assert "malware" in result["categories"]
        assert "phishing" in result["categories"]
        assert result["domain_age_days"] is None
        assert result["reputation"] == "malicious"

    def test_domain_payload_with_age(self) -> None:
        result = _build_payload(VT_DOMAIN_RESPONSE, is_domain=True)
        assert result["detection_score"] == "5/72"
        assert result["domain_age_days"] is not None
        assert result["domain_age_days"] > 0
        assert result["reputation"] == "malicious"


# ---------------------------------------------------------------------------
# Full enrichment — URL happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_enrich_url_success() -> None:
    transport = _make_transport()
    source = _make_source(transport)

    result = await source.enrich("url", TEST_URL)

    assert result["detection_score"] == "3/72"
    assert result["malicious"] == 3
    assert result["suspicious"] == 1
    assert result["total_engines"] == 72
    assert "phishing" in result["categories"]
    assert "malware" in result["categories"]
    assert result["domain_age_days"] is None
    assert result["reputation"] == "malicious"
    assert result["last_analysis_date"] is not None
    assert "error" not in result


@pytest.mark.asyncio
async def test_enrich_url_clean() -> None:
    transport = _make_transport(
        url_get_response=httpx.Response(200, json=VT_CLEAN_RESPONSE),
    )
    source = _make_source(transport)

    result = await source.enrich("url", TEST_URL)

    assert result["malicious"] == 0
    assert result["suspicious"] == 0
    assert result["reputation"] == "clean"


@pytest.mark.asyncio
async def test_enrich_url_suspicious_only() -> None:
    transport = _make_transport(
        url_get_response=httpx.Response(200, json=VT_SUSPICIOUS_ONLY_RESPONSE),
    )
    source = _make_source(transport)

    result = await source.enrich("url", TEST_URL)

    assert result["malicious"] == 0
    assert result["suspicious"] == 2
    assert result["reputation"] == "suspicious"


# ---------------------------------------------------------------------------
# Full enrichment — domain happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_enrich_domain_success() -> None:
    transport = _make_transport()
    source = _make_source(transport)

    result = await source.enrich("domain", TEST_DOMAIN)

    assert result["detection_score"] == "5/72"
    assert result["malicious"] == 5
    assert result["total_engines"] == 72
    assert "phishing" in result["categories"]
    assert result["domain_age_days"] is not None
    assert result["domain_age_days"] > 0
    assert result["reputation"] == "malicious"
    assert result["last_analysis_date"] is not None
    assert "error" not in result


# ---------------------------------------------------------------------------
# No API key — returns unknown without HTTP call
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_enrich_no_api_key() -> None:
    transport = _make_transport()
    source = _make_source(transport, api_key="")

    result = await source.enrich("url", TEST_URL)

    assert result["reputation"] == "unknown"
    assert result["error"] == "no_api_key_configured"
    assert result["detection_score"] == "0/0"
    assert result["malicious"] == 0
    assert result["total_engines"] == 0


@pytest.mark.asyncio
async def test_enrich_domain_no_api_key() -> None:
    transport = _make_transport()
    source = _make_source(transport, api_key="")

    result = await source.enrich("domain", TEST_DOMAIN)

    assert result["reputation"] == "unknown"
    assert result["error"] == "no_api_key_configured"


# ---------------------------------------------------------------------------
# URL unknown to VT (404 on GET → POST queued)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_enrich_url_404_then_post() -> None:
    transport = _make_transport(
        url_get_response=httpx.Response(404, text="Not Found"),
        url_post_response=httpx.Response(200, json={"data": {"id": "queued-123"}}),
    )
    source = _make_source(transport)

    result = await source.enrich("url", TEST_URL)

    assert result["reputation"] == "unknown"
    assert result["error"] == "queued_for_analysis"


# ---------------------------------------------------------------------------
# HTTP errors — raise so EnrichmentService wraps graceful fallback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_enrich_url_http_error_raises() -> None:
    transport = _make_transport(
        url_get_response=httpx.Response(500, text="Internal Server Error"),
    )
    source = _make_source(transport)

    with pytest.raises(httpx.HTTPStatusError):
        await source.enrich("url", TEST_URL)


@pytest.mark.asyncio
async def test_enrich_domain_http_error_raises() -> None:
    transport = _make_transport(
        domain_response=httpx.Response(500, text="Internal Server Error"),
    )
    source = _make_source(transport)

    with pytest.raises(httpx.HTTPStatusError):
        await source.enrich("domain", TEST_DOMAIN)


@pytest.mark.asyncio
async def test_enrich_url_connect_error_raises() -> None:
    transport = _make_transport(
        url_get_response=httpx.ConnectError("VT down"),
    )
    source = _make_source(transport)

    with pytest.raises(httpx.ConnectError):
        await source.enrich("url", TEST_URL)


# ---------------------------------------------------------------------------
# Protocol compliance
# ---------------------------------------------------------------------------


class TestProtocolCompliance:
    def test_has_required_attributes(self) -> None:
        source = VirusTotalSource(api_key="k")
        assert source.name == "virustotal"
        assert source.ioc_types == {"url", "domain"}
        assert source.rate_limit.requests_per_minute == 4
        assert source.rate_limit.requests_per_day == 500

    def test_satisfies_enrichment_source_protocol(self) -> None:
        source = VirusTotalSource(api_key="k")
        assert isinstance(source, EnrichmentSource)


# ---------------------------------------------------------------------------
# Quota endpoint (integration via TestClient)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_quota_endpoint() -> None:
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
    assert len(data) >= 2  # btc_mempool + virustotal

    source_names = {item["source"] for item in data}
    assert "virustotal" in source_names
    assert "btc_mempool" in source_names

    vt_quota = next(item for item in data if item["source"] == "virustotal")
    assert vt_quota["limit_per_minute"] == 4
    assert vt_quota["limit_per_day"] == 500
    assert vt_quota["requests_used_minute"] == 0
    assert vt_quota["requests_used_day"] == 0
    assert vt_quota["available_day"] == 500

    # Cleanup
    enrichment_mod._enrichment_service = None


# ---------------------------------------------------------------------------
# InMemoryRateLimiter.get_usage
# ---------------------------------------------------------------------------


class TestRateLimiterGetUsage:
    def test_get_usage_empty(self) -> None:
        from phishguard.services.enrichment_service import InMemoryRateLimiter

        limiter = InMemoryRateLimiter()
        minute, day = limiter.get_usage("virustotal")
        assert minute == 0
        assert day == 0

    def test_get_usage_after_check(self) -> None:
        from phishguard.services.enrichment_service import (
            InMemoryRateLimiter,
            RateLimitConfig,
        )

        limiter = InMemoryRateLimiter()
        config = RateLimitConfig(requests_per_minute=10, requests_per_day=100)

        limiter.check("virustotal", config)
        limiter.check("virustotal", config)

        minute, day = limiter.get_usage("virustotal")
        assert minute == 2
        assert day == 2

    def test_get_usage_does_not_affect_other_sources(self) -> None:
        from phishguard.services.enrichment_service import (
            InMemoryRateLimiter,
            RateLimitConfig,
        )

        limiter = InMemoryRateLimiter()
        config = RateLimitConfig(requests_per_minute=10, requests_per_day=100)

        limiter.check("virustotal", config)

        minute, day = limiter.get_usage("btc_mempool")
        assert minute == 0
        assert day == 0
