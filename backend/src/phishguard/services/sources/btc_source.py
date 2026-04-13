"""BTC wallet enrichment source (US-034).

Enriches Bitcoin wallet addresses with on-chain data from mempool.space
(primary) / Blockstream.info (fallback) and community abuse reports from
bitcoinabuse.com.

On-chain API
------------
Both mempool.space and Blockstream.info expose the same Esplora REST API:
    GET /api/address/{address}
No authentication required.  Response includes funded/spent tx counts and
chain/mempool stats in satoshis.

Abuse reports API
-----------------
bitcoinabuse.com provides a free lookup:
    GET /api/reports/check?address={addr}&api_token={key}
Requires a free API key (env var ``BITCOINABUSE_API_KEY``).

Reputation labels
-----------------
- ``malicious``  — >=3 abuse reports
- ``suspicious`` — 1-2 abuse reports
- ``unknown``    — 0 reports, API error, or invalid address
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any

import httpx

from phishguard.services.enrichment_service import RateLimitConfig

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# BTC address validation
# ---------------------------------------------------------------------------

# Legacy P2PKH (1...) — 25-34 chars base58
_RE_P2PKH = re.compile(r"^1[1-9A-HJ-NP-Za-km-z]{24,33}$")
# Legacy P2SH (3...) — 34 chars base58
_RE_P2SH = re.compile(r"^3[1-9A-HJ-NP-Za-km-z]{24,33}$")
# Bech32 / Bech32m (bc1...) — 42 or 62 chars lowercase alnum
_RE_BECH32 = re.compile(r"^bc1[a-zA-HJ-NP-Za-km-z0-9]{25,71}$")

_SATOSHIS_PER_BTC = 100_000_000

# Reputation thresholds
_MALICIOUS_THRESHOLD = 3
_SUSPICIOUS_THRESHOLD = 1

# HTTP settings
_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


def _is_valid_btc_address(address: str) -> bool:
    """Lightweight format check — NOT full checksum validation."""
    return bool(
        _RE_P2PKH.match(address) or _RE_P2SH.match(address) or _RE_BECH32.match(address)
    )


def _derive_reputation(report_count: int) -> str:
    """Map abuse-report count to a human-readable reputation label."""
    if report_count >= _MALICIOUS_THRESHOLD:
        return "malicious"
    if report_count >= _SUSPICIOUS_THRESHOLD:
        return "suspicious"
    return "unknown"


# ---------------------------------------------------------------------------
# On-chain helpers
# ---------------------------------------------------------------------------


async def _fetch_onchain(
    client: httpx.AsyncClient,
    address: str,
) -> dict[str, Any]:
    """Call mempool.space; on failure fall back to Blockstream.info.

    Both expose the same Esplora ``/api/address/{address}`` shape.
    """
    urls = [
        f"https://mempool.space/api/address/{address}",
        f"https://blockstream.info/api/address/{address}",
    ]

    last_exc: BaseException | None = None
    for url in urls:
        try:
            resp = await client.get(url, timeout=_TIMEOUT)
            resp.raise_for_status()
            return resp.json()  # type: ignore[no-any-return]
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            last_exc = exc
            logger.warning(
                "btc_onchain_fetch_failed",
                extra={"url": url, "error": str(exc)},
            )

    # Both sources failed — propagate to caller
    raise httpx.HTTPStatusError(
        f"All on-chain sources failed: {last_exc}",
        request=httpx.Request("GET", urls[-1]),
        response=httpx.Response(502),
    )


def _parse_onchain(data: dict[str, Any]) -> dict[str, Any]:
    """Extract balance, tx_count, first_seen, last_activity from Esplora payload."""
    chain = data.get("chain_stats", {})
    mempool = data.get("mempool_stats", {})

    funded_sats = chain.get("funded_txo_sum", 0) + mempool.get("funded_txo_sum", 0)
    spent_sats = chain.get("spent_txo_sum", 0) + mempool.get("spent_txo_sum", 0)
    balance_sats = funded_sats - spent_sats

    tx_count = chain.get("tx_count", 0) + mempool.get("tx_count", 0)

    return {
        "balance_btc": round(balance_sats / _SATOSHIS_PER_BTC, 8),
        "balance_sats": balance_sats,
        "tx_count": tx_count,
        # Esplora does not provide first_seen / last_activity timestamps
        # directly; we note them as unavailable at this layer.  A future
        # enhancement (US-034-followup) could query /api/address/{addr}/txs
        # and inspect the first/last tx block times.
        "first_seen": None,
        "last_activity": None,
    }


# ---------------------------------------------------------------------------
# Abuse-report helpers
# ---------------------------------------------------------------------------


async def _fetch_abuse_reports(
    client: httpx.AsyncClient,
    address: str,
    api_key: str,
) -> dict[str, Any]:
    """Query bitcoinabuse.com for community reports on *address*."""
    url = "https://www.bitcoinabuse.com/api/reports/check"
    params = {"address": address, "api_token": api_key}

    resp = await client.get(url, params=params, timeout=_TIMEOUT)
    resp.raise_for_status()
    return resp.json()  # type: ignore[no-any-return]


def _parse_abuse(data: Any) -> dict[str, Any]:
    """Normalise bitcoinabuse response into a flat payload slice."""
    if isinstance(data, dict):
        count = int(data.get("count", 0))
        recent = data.get("recent", None)
        most_recent_category = None
        if isinstance(recent, list) and recent:
            most_recent_category = recent[0].get("abuse_type_other") or recent[0].get(
                "abuse_type"
            )
        elif isinstance(recent, dict):
            most_recent_category = recent.get("abuse_type_other") or recent.get(
                "abuse_type"
            )
        return {
            "report_count": count,
            "most_recent_category": most_recent_category,
            "reputation": _derive_reputation(count),
        }

    # Unexpected shape — treat as zero reports
    return {
        "report_count": 0,
        "most_recent_category": None,
        "reputation": "unknown",
    }


# ---------------------------------------------------------------------------
# EnrichmentSource implementation
# ---------------------------------------------------------------------------


class BtcEnrichmentSource:
    """Enrichment source for BTC wallets.

    Satisfies the ``EnrichmentSource`` protocol defined in
    ``phishguard.services.enrichment_service``.
    """

    name: str = "btc_mempool"
    ioc_types: set[str] = {"btc"}
    rate_limit: RateLimitConfig = RateLimitConfig(
        requests_per_minute=30,
        requests_per_day=5_000,
    )

    def __init__(
        self,
        *,
        bitcoinabuse_api_key: str | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._bitcoinabuse_api_key = bitcoinabuse_api_key or os.environ.get(
            "BITCOINABUSE_API_KEY", ""
        )
        # Allow injection for testing; otherwise create a shared client
        self._external_client = http_client

    async def _get_client(self) -> httpx.AsyncClient:
        if self._external_client is not None:
            return self._external_client
        # Lazy-create a module-level client to benefit from connection pooling.
        # In production, the lifespan hook should pass a managed client.
        return httpx.AsyncClient()

    async def enrich(self, ioc_type: str, value: str) -> dict[str, Any]:
        """Enrich a BTC address with on-chain data and abuse reports.

        Returns a combined payload dict on success.
        Raises on unrecoverable on-chain failure so the ``EnrichmentService``
        can wrap the error into ``status="unavailable"``.

        Invalid addresses are *not* raised — we return a payload with
        ``reputation: "unknown"`` and an ``error`` key, per AC.
        """
        address = value.strip()

        if not _is_valid_btc_address(address):
            return {
                "balance_btc": None,
                "balance_sats": None,
                "tx_count": None,
                "first_seen": None,
                "last_activity": None,
                "report_count": 0,
                "most_recent_category": None,
                "reputation": "unknown",
                "error": "invalid_btc_address",
            }

        client = await self._get_client()
        owns_client = self._external_client is None
        try:
            return await self._do_enrich(client, address)
        finally:
            if owns_client:
                await client.aclose()

    async def _do_enrich(
        self,
        client: httpx.AsyncClient,
        address: str,
    ) -> dict[str, Any]:
        # On-chain data (raises on total failure — both sources down)
        raw_onchain = await _fetch_onchain(client, address)
        payload = _parse_onchain(raw_onchain)

        # Abuse reports — best-effort; failure degrades to "unknown"
        abuse_payload: dict[str, Any]
        if self._bitcoinabuse_api_key:
            try:
                raw_abuse = await _fetch_abuse_reports(
                    client, address, self._bitcoinabuse_api_key
                )
                abuse_payload = _parse_abuse(raw_abuse)
            except (httpx.HTTPError, httpx.TimeoutException, Exception) as exc:  # noqa: BLE001
                logger.warning(
                    "btc_abuse_fetch_failed",
                    extra={"error": str(exc)},
                )
                abuse_payload = {
                    "report_count": 0,
                    "most_recent_category": None,
                    "reputation": "unknown",
                }
        else:
            # No API key configured — skip abuse lookup
            abuse_payload = {
                "report_count": 0,
                "most_recent_category": None,
                "reputation": "unknown",
            }

        payload.update(abuse_payload)
        return payload
