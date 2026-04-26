"""Foundation for IOC enrichment (US-033).

Source-agnostic orchestrator that routes an ``(ioc_type, value)`` pair to a
registered enrichment source, with read-through cache, per-source rate
limiting, graceful fallback on source errors, and structured logging.

Concrete sources (Blockchain.com, VirusTotal, AbuseIPDB, phonenumbers) are
implemented in US-034 through US-037; this module stays unaware of them.
"""

from __future__ import annotations

import hashlib
import logging
import time
from collections import deque
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal, Protocol, runtime_checkable

import httpx
from pydantic import BaseModel
from supabase import Client

from phishguard.services.session_service import _get_supabase_client

logger = logging.getLogger(__name__)

EnrichmentStatus = Literal["ok", "unavailable", "rate_limited", "error"]


# Default per-type TTLs
# AC: "Result cache with per-type TTL (URLs: 24h, domains: 7d, others: configurable)"
DEFAULT_CACHE_TTL: dict[str, timedelta] = {
    "url": timedelta(hours=24),
    "domain": timedelta(days=7),
    "btc": timedelta(hours=12),
    "ip": timedelta(hours=6),
    "phone": timedelta(days=30),
}
DEFAULT_FALLBACK_TTL = timedelta(hours=12)


@dataclass(frozen=True)
class RateLimitConfig:
    """Per-source rate limit configuration."""

    requests_per_minute: int = 60
    requests_per_day: int = 10_000


class EnrichmentResult(BaseModel):
    """Result of a single enrichment call."""

    status: EnrichmentStatus
    source: str
    ioc_type: str
    value: str
    payload: dict[str, Any] | None = None
    fetched_at: datetime
    cached: bool = False
    latency_ms: int = 0


@runtime_checkable
class EnrichmentSource(Protocol):
    """Protocol every concrete enrichment source must satisfy.

    Concrete sources (US-034+) implement ``enrich`` to call external APIs.
    On success the source returns a payload dict; on failure it raises — the
    ``EnrichmentService`` wraps the raise into a graceful fallback result.
    """

    name: str
    ioc_types: set[str]
    rate_limit: RateLimitConfig

    async def enrich(self, ioc_type: str, value: str) -> dict[str, Any]:
        """Fetch enrichment data. Return payload on success, raise on failure."""
        ...


class InMemoryRateLimiter:
    """Per-process sliding-window rate limiter.

    NOTE: In-memory only. When PhishGuard goes multi-instance, swap this for a
    Redis-backed limiter. Tracked as a follow-up to US-033 — the foundation
    story deliberately keeps this simple.
    """

    def __init__(self) -> None:
        self._minute_windows: dict[str, deque[float]] = {}
        self._day_windows: dict[str, deque[float]] = {}

    def check(self, source_name: str, config: RateLimitConfig) -> bool:
        """Return True and record the call if allowed; False if rate-limited."""
        now = time.monotonic()
        minute_cutoff = now - 60
        day_cutoff = now - 86400

        minute_window = self._minute_windows.setdefault(source_name, deque())
        day_window = self._day_windows.setdefault(source_name, deque())

        while minute_window and minute_window[0] < minute_cutoff:
            minute_window.popleft()
        while day_window and day_window[0] < day_cutoff:
            day_window.popleft()

        if len(minute_window) >= config.requests_per_minute:
            return False
        if len(day_window) >= config.requests_per_day:
            return False

        minute_window.append(now)
        day_window.append(now)
        return True

    def get_usage(self, source_name: str) -> tuple[int, int]:
        """Return ``(minute_count, day_count)`` for *source_name*.

        Prunes expired entries before counting so the numbers reflect the
        current sliding window — same semantics as ``check`` but read-only.
        """
        now = time.monotonic()
        minute_cutoff = now - 60
        day_cutoff = now - 86400

        minute_window = self._minute_windows.get(source_name, deque())
        day_window = self._day_windows.get(source_name, deque())

        while minute_window and minute_window[0] < minute_cutoff:
            minute_window.popleft()
        while day_window and day_window[0] < day_cutoff:
            day_window.popleft()

        return len(minute_window), len(day_window)


def _hash_value(value: str) -> str:
    """Stable short hash for cache keys and log lines.

    Raw IOC values may contain PII (phone numbers, URLs with account tokens).
    Hashing before logging/caching ensures those values never hit logs or
    indexes in plain form.
    """
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


class EnrichmentService:
    """Source-agnostic IOC enrichment orchestrator.

    Responsibilities:
    - Route ``(ioc_type, value)`` to the appropriate registered source
    - Read-through cache against ``ioc_enrichment`` with per-type TTL
    - Per-source rate limiting (in-memory sliding window)
    - Graceful fallback on source failure → ``status="unavailable"``
    - Structured logging: one INFO record per call with source, latency, cache hit
    """

    def __init__(
        self,
        sources: Iterable[EnrichmentSource],
        *,
        supabase_client_factory: Callable[[], Client] = _get_supabase_client,
        cache_ttl: dict[str, timedelta] | None = None,
        fallback_ttl: timedelta = DEFAULT_FALLBACK_TTL,
        rate_limiter: InMemoryRateLimiter | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._sources_by_type: dict[str, EnrichmentSource] = {}
        for src in sources:
            for ioc_type in src.ioc_types:
                # First source registered for a type wins — US-033 has no
                # multi-source fan-out; that's a future story concern.
                self._sources_by_type.setdefault(ioc_type, src)
        self._supabase_factory = supabase_client_factory
        self._cache_ttl = cache_ttl if cache_ttl is not None else DEFAULT_CACHE_TTL
        self._fallback_ttl = fallback_ttl
        self._rate_limiter = rate_limiter or InMemoryRateLimiter()
        self._clock = clock

    def _ttl_for(self, ioc_type: str) -> timedelta:
        return self._cache_ttl.get(ioc_type, self._fallback_ttl)

    async def enrich(
        self,
        ioc_type: str,
        value: str,
        *,
        ioc_id: str | None = None,
        force_refresh: bool = False,
    ) -> EnrichmentResult:
        """Enrich a single IOC.

        Args:
            ioc_type: Canonical IOC type (e.g. ``"url"``, ``"btc"``, ``"phone"``).
            value: The raw IOC value. Never logged in plain form.
            ioc_id: Optional FK into ``ioc_extracted``. When provided, the cache
                write links the enrichment row to the session's IOC; when not,
                the row is stored as a server-internal cache entry (RLS keeps
                it invisible to end users).
            force_refresh: If True, bypass the cache and fetch fresh data from
                the source.

        Returns:
            ``EnrichmentResult`` with ``status`` in ``{ok, unavailable,
            rate_limited, error}`` and ``cached`` flagging cache hits.
        """
        start = time.monotonic()
        value_hash = _hash_value(value)

        source = self._sources_by_type.get(ioc_type)
        if source is None:
            result = EnrichmentResult(
                status="unavailable",
                source="none",
                ioc_type=ioc_type,
                value=value,
                payload={"reason": "no_source_registered"},
                fetched_at=self._clock(),
                cached=False,
                latency_ms=int((time.monotonic() - start) * 1000),
            )
            self._log(result, value_hash, cache_hit=False)
            return result

        # Cache read-through
        if not force_refresh:
            cached_row = self._read_cache(source.name, ioc_type, value_hash)
            if cached_row is not None:
                fetched_at = _parse_timestamp(cached_row.get("fetched_at"))
                if (
                    fetched_at is not None
                    and self._clock() - fetched_at <= self._ttl_for(ioc_type)
                ):
                    result = EnrichmentResult(
                        status=cached_row.get("status", "ok"),
                        source=source.name,
                        ioc_type=ioc_type,
                        value=value,
                        payload=cached_row.get("payload"),
                        fetched_at=fetched_at,
                        cached=True,
                        latency_ms=int((time.monotonic() - start) * 1000),
                    )
                    self._log(result, value_hash, cache_hit=True)
                    return result

        # Rate limit check
        if not self._rate_limiter.check(source.name, source.rate_limit):
            result = EnrichmentResult(
                status="rate_limited",
                source=source.name,
                ioc_type=ioc_type,
                value=value,
                payload={"reason": "rate_limit_exceeded"},
                fetched_at=self._clock(),
                cached=False,
                latency_ms=int((time.monotonic() - start) * 1000),
            )
            self._log(result, value_hash, cache_hit=False)
            return result

        # Source call with graceful fallback
        status: EnrichmentStatus
        try:
            payload: dict[str, Any] | None = await source.enrich(ioc_type, value)
            status = "ok"
        except (TimeoutError, httpx.HTTPError) as exc:
            payload = {"reason": "source_error", "error": exc.__class__.__name__}
            status = "unavailable"
        except Exception as exc:  # noqa: BLE001 - graceful fallback on source misbehavior
            payload = {"reason": "source_exception", "error": exc.__class__.__name__}
            status = "unavailable"

        fetched_at_now = self._clock()
        result = EnrichmentResult(
            status=status,
            source=source.name,
            ioc_type=ioc_type,
            value=value,
            payload=payload,
            fetched_at=fetched_at_now,
            cached=False,
            latency_ms=int((time.monotonic() - start) * 1000),
        )

        # Cache write — skipped for rate_limited (never reaches here) but done
        # even for unavailable results so we don't hammer a broken source.
        self._write_cache(
            source_name=source.name,
            ioc_type=ioc_type,
            value_hash=value_hash,
            status=status,
            payload=payload,
            fetched_at=fetched_at_now,
            ioc_id=ioc_id,
        )

        self._log(result, value_hash, cache_hit=False)
        return result

    def _read_cache(
        self,
        source_name: str,
        ioc_type: str,
        value_hash: str,
    ) -> dict[str, Any] | None:
        try:
            client = self._supabase_factory()
            resp = (
                client.table("ioc_enrichment")
                .select("status, payload, fetched_at")
                .eq("source", source_name)
                .eq("ioc_type", ioc_type)
                .eq("value_hash", value_hash)
                .order("fetched_at", desc=True)
                .limit(1)
                .execute()
            )
            if resp.data:
                return resp.data[0]
        except Exception as exc:  # noqa: BLE001 - cache failures must not block enrichment
            logger.warning(
                "enrichment_cache_read_failed",
                extra={"error_class": exc.__class__.__name__},
            )
        return None

    def _write_cache(
        self,
        *,
        source_name: str,
        ioc_type: str,
        value_hash: str,
        status: EnrichmentStatus,
        payload: dict[str, Any] | None,
        fetched_at: datetime,
        ioc_id: str | None,
    ) -> None:
        row: dict[str, Any] = {
            "source": source_name,
            "ioc_type": ioc_type,
            "value_hash": value_hash,
            "status": status,
            "payload": payload or {},
            "fetched_at": fetched_at.isoformat(),
        }
        if ioc_id is not None:
            row["ioc_id"] = ioc_id
        try:
            client = self._supabase_factory()
            (
                client.table("ioc_enrichment")
                .upsert(row, on_conflict="source,ioc_type,value_hash")
                .execute()
            )
        except Exception as exc:  # noqa: BLE001 - cache failures must not block enrichment
            logger.warning(
                "enrichment_cache_write_failed",
                extra={"error_class": exc.__class__.__name__},
            )

    def _log(
        self,
        result: EnrichmentResult,
        value_hash: str,
        *,
        cache_hit: bool,
    ) -> None:
        """Emit one INFO record per enrich call.

        Raw IOC value is NEVER included — only its hash — so PII-adjacent
        data (phone numbers, tokenized URLs) cannot leak via logs.
        """
        logger.info(
            "enrichment_call",
            extra={
                "source": result.source,
                "ioc_type": result.ioc_type,
                "value_hash": value_hash,
                "status": result.status,
                "cached": result.cached,
                "cache_hit": cache_hit,
                "latency_ms": result.latency_ms,
            },
        )


def _parse_timestamp(raw: Any) -> datetime | None:
    """Parse a Supabase timestamp (str or datetime) into an aware datetime."""
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw if raw.tzinfo is not None else raw.replace(tzinfo=UTC)
    if isinstance(raw, str):
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None
