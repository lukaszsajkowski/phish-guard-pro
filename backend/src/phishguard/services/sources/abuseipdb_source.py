"""AbuseIPDB IP address enrichment source (US-036).

Enriches IP address IOCs with abuse history data from AbuseIPDB API v2:
abuse confidence score, total reports, country code, ISP, and a derived
reputation label.

API endpoint
------------
``GET https://api.abuseipdb.com/api/v2/check``

Authentication: ``Key: <ABUSEIPDB_API_KEY>`` header.

Rate limits (free tier): 1 000 requests/day.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from phishguard.core import get_settings
from phishguard.services.enrichment_service import RateLimitConfig

logger = logging.getLogger(__name__)

_ABUSEIPDB_BASE = "https://api.abuseipdb.com/api/v2"
_TIMEOUT = httpx.Timeout(15.0, connect=5.0)

# Reputation thresholds (based on AbuseIPDB confidence score 0-100)
_MALICIOUS_THRESHOLD = 75
_SUSPICIOUS_THRESHOLD = 25


def _derive_reputation(abuse_confidence_score: int) -> str:
    """Map AbuseIPDB confidence score to a human-readable reputation label."""
    if abuse_confidence_score >= _MALICIOUS_THRESHOLD:
        return "malicious"
    if abuse_confidence_score >= _SUSPICIOUS_THRESHOLD:
        return "suspicious"
    return "clean"


def _unknown_payload(*, reason: str = "error") -> dict[str, Any]:
    """Return a safe fallback payload when enrichment cannot proceed."""
    return {
        "abuse_confidence_score": 0,
        "total_reports": 0,
        "country_code": None,
        "isp": None,
        "domain": None,
        "is_tor": False,
        "reputation": "unknown",
        "error": reason,
    }


def _build_payload(data: dict[str, Any]) -> dict[str, Any]:
    """Build the normalised enrichment payload from an AbuseIPDB API response."""
    inner = data.get("data", {})

    abuse_confidence_score = int(inner.get("abuseConfidenceScore", 0))
    total_reports = int(inner.get("totalReports", 0))
    country_code = inner.get("countryCode")
    isp = inner.get("isp")
    domain = inner.get("domain")
    is_tor = bool(inner.get("isTor", False))
    reputation = _derive_reputation(abuse_confidence_score)

    return {
        "abuse_confidence_score": abuse_confidence_score,
        "total_reports": total_reports,
        "country_code": country_code,
        "isp": isp,
        "domain": domain,
        "is_tor": is_tor,
        "reputation": reputation,
    }


class AbuseIPDBSource:
    """Enrichment source for IP address IOCs via AbuseIPDB API v2.

    Satisfies the ``EnrichmentSource`` protocol defined in
    ``phishguard.services.enrichment_service``.
    """

    name: str = "abuseipdb"
    ioc_types: set[str] = {"ip"}
    rate_limit: RateLimitConfig = RateLimitConfig(
        requests_per_minute=60,
        requests_per_day=1000,
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
            api_key if api_key is not None else get_settings().abuseipdb_api_key
        )
        self._external_client = http_client

    def _headers(self) -> dict[str, str]:
        return {
            "Key": self._api_key,
            "Accept": "application/json",
        }

    async def _get_client(self) -> httpx.AsyncClient:
        if self._external_client is not None:
            return self._external_client
        return httpx.AsyncClient()

    async def enrich(self, ioc_type: str, value: str) -> dict[str, Any]:
        """Enrich an IP address with AbuseIPDB abuse history.

        Returns a payload dict on success.
        Raises on HTTP errors so the ``EnrichmentService`` can wrap them
        into a graceful fallback result.
        """
        if not self._api_key:
            return _unknown_payload(reason="no_api_key_configured")

        client = await self._get_client()
        owns_client = self._external_client is None
        try:
            resp = await client.get(
                f"{_ABUSEIPDB_BASE}/check",
                headers=self._headers(),
                params={
                    "ipAddress": value.strip(),
                    "maxAgeInDays": "90",
                    "verbose": "false",
                },
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()
            return _build_payload(resp.json())
        finally:
            if owns_client:
                await client.aclose()
