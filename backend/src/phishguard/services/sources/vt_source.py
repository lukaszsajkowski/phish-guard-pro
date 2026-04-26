"""VirusTotal URL/domain enrichment source (US-035).

Enriches URL and domain IOCs with VirusTotal API v3 reputation data:
detection score, categories, domain age, and a derived reputation label.

API endpoints
-------------
- URL:    ``GET /api/v3/urls/{url_id}`` where ``url_id`` is the
          base64url-encoded URL (no padding).  Falls back to
          ``POST /api/v3/urls`` when the URL is unknown (404).
- Domain: ``GET /api/v3/domains/{domain}``

Authentication: ``x-apikey: <VIRUSTOTAL_API_KEY>`` header.

Rate limits (free tier): 4 req/min, 500 req/day.
"""

from __future__ import annotations

import base64
import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from phishguard.core import get_settings
from phishguard.services.enrichment_service import RateLimitConfig

logger = logging.getLogger(__name__)

_VT_BASE = "https://www.virustotal.com/api/v3"
_TIMEOUT = httpx.Timeout(15.0, connect=5.0)


def _make_url_id(url: str) -> str:
    """Encode a URL into the VirusTotal URL identifier (base64url, no padding)."""
    return base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")


def _derive_reputation(malicious: int, suspicious: int) -> str:
    if malicious > 0:
        return "malicious"
    if suspicious > 0:
        return "suspicious"
    return "clean"


def _parse_analysis_stats(attrs: dict[str, Any]) -> dict[str, Any]:
    """Extract detection score fields from VT ``attributes``."""
    stats = attrs.get("last_analysis_stats", {})
    malicious = int(stats.get("malicious", 0))
    suspicious_count = int(stats.get("suspicious", 0))
    undetected = int(stats.get("undetected", 0))
    harmless = int(stats.get("harmless", 0))
    total = malicious + suspicious_count + undetected + harmless

    return {
        "detection_score": f"{malicious}/{total}",
        "malicious": malicious,
        "suspicious": suspicious_count,
        "total_engines": total,
    }


def _parse_categories(attrs: dict[str, Any]) -> list[str]:
    """Collect unique category labels from the vendor-keyed dict."""
    raw = attrs.get("categories", {})
    if isinstance(raw, dict):
        return sorted(set(raw.values()))
    return []


def _parse_domain_age(attrs: dict[str, Any]) -> int | None:
    """Return domain age in days from ``creation_date`` (Unix timestamp)."""
    creation_ts = attrs.get("creation_date")
    if creation_ts is None:
        return None
    try:
        created = datetime.fromtimestamp(int(creation_ts), tz=UTC)
        return (datetime.now(UTC) - created).days
    except (ValueError, TypeError, OSError):
        return None


def _parse_last_analysis_date(attrs: dict[str, Any]) -> str | None:
    """Return ISO date string from ``last_analysis_date`` (Unix timestamp)."""
    ts = attrs.get("last_analysis_date")
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(int(ts), tz=UTC).date().isoformat()
    except (ValueError, TypeError, OSError):
        return None


def _build_payload(data: dict[str, Any], *, is_domain: bool) -> dict[str, Any]:
    """Build the normalised enrichment payload from a VT API response."""
    attrs = data.get("data", {}).get("attributes", {})

    stats = _parse_analysis_stats(attrs)
    categories = _parse_categories(attrs)
    domain_age = _parse_domain_age(attrs) if is_domain else None
    last_analysis = _parse_last_analysis_date(attrs)
    reputation = _derive_reputation(stats["malicious"], stats["suspicious"])

    return {
        **stats,
        "categories": categories,
        "domain_age_days": domain_age,
        "reputation": reputation,
        "last_analysis_date": last_analysis,
    }


def _unknown_payload(*, reason: str = "error") -> dict[str, Any]:
    return {
        "detection_score": "0/0",
        "malicious": 0,
        "suspicious": 0,
        "total_engines": 0,
        "categories": [],
        "domain_age_days": None,
        "reputation": "unknown",
        "last_analysis_date": None,
        "error": reason,
    }


class VirusTotalSource:
    """Enrichment source for URL and domain IOCs via VirusTotal API v3.

    Satisfies the ``EnrichmentSource`` protocol defined in
    ``phishguard.services.enrichment_service``.
    """

    name: str = "virustotal"
    ioc_types: set[str] = {"url", "domain"}
    rate_limit: RateLimitConfig = RateLimitConfig(
        requests_per_minute=4,
        requests_per_day=500,
    )

    def __init__(
        self,
        *,
        api_key: str | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        # Use provided key verbatim (including "") so callers can disable the
        # source in tests by passing api_key="".  Only fall back to settings
        # when the caller explicitly passes None (the default).
        self._api_key = (
            api_key if api_key is not None else get_settings().virustotal_api_key
        )
        self._external_client = http_client

    def _headers(self) -> dict[str, str]:
        return {"x-apikey": self._api_key}

    async def _get_client(self) -> httpx.AsyncClient:
        if self._external_client is not None:
            return self._external_client
        return httpx.AsyncClient()

    async def enrich(self, ioc_type: str, value: str) -> dict[str, Any]:
        if not self._api_key:
            return _unknown_payload(reason="no_api_key_configured")

        client = await self._get_client()
        owns_client = self._external_client is None
        try:
            if ioc_type == "url":
                return await self._enrich_url(client, value)
            return await self._enrich_domain(client, value)
        finally:
            if owns_client:
                await client.aclose()

    async def _enrich_url(self, client: httpx.AsyncClient, url: str) -> dict[str, Any]:
        url_id = _make_url_id(url)
        resp = await client.get(
            f"{_VT_BASE}/urls/{url_id}",
            headers=self._headers(),
            timeout=_TIMEOUT,
        )

        if resp.status_code == 404:
            # URL not yet known to VT — submit it and return pending/unknown
            await client.post(
                f"{_VT_BASE}/urls",
                headers=self._headers(),
                content=f"url={url}",
                timeout=_TIMEOUT,
            )
            return _unknown_payload(reason="queued_for_analysis")

        resp.raise_for_status()
        return _build_payload(resp.json(), is_domain=False)

    async def _enrich_domain(
        self, client: httpx.AsyncClient, domain: str
    ) -> dict[str, Any]:
        resp = await client.get(
            f"{_VT_BASE}/domains/{domain}",
            headers=self._headers(),
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        return _build_payload(resp.json(), is_domain=True)
