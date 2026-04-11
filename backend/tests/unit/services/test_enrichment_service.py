"""Unit tests for EnrichmentService (US-033).

The foundation story has no concrete HTTP source yet, so "mocked HTTP clients"
at this layer means mocked ``EnrichmentSource`` doubles — real HTTP mocking
lands in US-034+ when concrete sources are implemented.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import MagicMock

import httpx
import pytest

from phishguard.services.enrichment_service import (
    EnrichmentResult,
    EnrichmentService,
    RateLimitConfig,
)

FROZEN_NOW = datetime(2026, 4, 11, 12, 0, 0, tzinfo=UTC)


def _frozen_clock() -> datetime:
    return FROZEN_NOW


class FakeSource:
    """Minimal EnrichmentSource double — no real I/O."""

    def __init__(
        self,
        *,
        name: str = "fake",
        ioc_types: set[str] | None = None,
        payload: dict[str, Any] | None = None,
        rate_limit: RateLimitConfig | None = None,
        raises: Exception | None = None,
    ) -> None:
        self.name = name
        self.ioc_types = ioc_types or {"url"}
        self.rate_limit = rate_limit or RateLimitConfig(
            requests_per_minute=10,
            requests_per_day=100,
        )
        self._payload = (
            payload if payload is not None else {"detections": 3, "engines": 80}
        )
        self._raises = raises
        self.call_count = 0

    async def enrich(self, ioc_type: str, value: str) -> dict[str, Any]:
        self.call_count += 1
        if self._raises is not None:
            raise self._raises
        return dict(self._payload)


def _make_supabase_mock(cache_row: dict[str, Any] | None = None) -> MagicMock:
    """Build a chainable MagicMock Supabase client for select/upsert."""
    client = MagicMock()
    table = MagicMock()
    client.table.return_value = table

    # Select chain: table.select().eq().eq().eq().order().limit().execute()
    select_chain = MagicMock()
    table.select.return_value = select_chain
    select_chain.eq.return_value = select_chain
    select_chain.order.return_value = select_chain
    select_chain.limit.return_value = select_chain
    select_chain.execute.return_value = MagicMock(
        data=[cache_row] if cache_row is not None else []
    )

    # Upsert chain: table.upsert().execute()
    upsert_chain = MagicMock()
    table.upsert.return_value = upsert_chain
    upsert_chain.execute.return_value = MagicMock(data=[{"id": "row-1"}])

    return client


@pytest.mark.asyncio
async def test_cache_miss_calls_source_and_writes_cache() -> None:
    fake = FakeSource()
    client = _make_supabase_mock(cache_row=None)

    svc = EnrichmentService(
        sources=[fake],
        supabase_client_factory=lambda: client,
        clock=_frozen_clock,
    )

    result = await svc.enrich("url", "http://evil.example.com")

    assert isinstance(result, EnrichmentResult)
    assert result.status == "ok"
    assert result.source == "fake"
    assert result.cached is False
    assert result.payload == {"detections": 3, "engines": 80}
    assert fake.call_count == 1

    # Cache write happened with expected shape
    upsert_mock = client.table.return_value.upsert
    upsert_mock.assert_called_once()
    row = upsert_mock.call_args[0][0]
    assert row["source"] == "fake"
    assert row["status"] == "ok"
    assert row["ioc_type"] == "url"
    assert row["payload"] == {"detections": 3, "engines": 80}
    # value_hash must be present and NOT contain the raw value
    assert "value_hash" in row
    assert "evil.example.com" not in row["value_hash"]


@pytest.mark.asyncio
async def test_cache_hit_returns_cached_and_skips_source() -> None:
    fake = FakeSource()
    cached_row = {
        "status": "ok",
        "payload": {"detections": 1},
        "fetched_at": FROZEN_NOW.isoformat(),
    }
    client = _make_supabase_mock(cache_row=cached_row)

    svc = EnrichmentService(
        sources=[fake],
        supabase_client_factory=lambda: client,
        clock=_frozen_clock,
    )

    result = await svc.enrich("url", "http://evil.example.com")

    assert result.cached is True
    assert result.status == "ok"
    assert result.payload == {"detections": 1}
    assert fake.call_count == 0
    client.table.return_value.upsert.assert_not_called()


@pytest.mark.asyncio
async def test_expired_cache_row_is_ignored_and_source_recalled() -> None:
    fake = FakeSource()
    # Default TTL for "url" is 24h; make the cache row 25h old
    stale_row = {
        "status": "ok",
        "payload": {"detections": 0},
        "fetched_at": (FROZEN_NOW - timedelta(hours=25)).isoformat(),
    }
    client = _make_supabase_mock(cache_row=stale_row)

    svc = EnrichmentService(
        sources=[fake],
        supabase_client_factory=lambda: client,
        clock=_frozen_clock,
    )

    result = await svc.enrich("url", "http://evil.example.com")

    assert result.cached is False
    assert fake.call_count == 1


@pytest.mark.asyncio
async def test_source_http_error_returns_unavailable() -> None:
    fake = FakeSource(raises=httpx.ConnectError("boom"))
    client = _make_supabase_mock(cache_row=None)

    svc = EnrichmentService(
        sources=[fake],
        supabase_client_factory=lambda: client,
        clock=_frozen_clock,
    )

    result = await svc.enrich("url", "http://evil.example.com")

    assert result.status == "unavailable"
    assert result.payload is not None
    assert result.payload["reason"] == "source_error"
    assert result.payload["error"] == "ConnectError"
    assert fake.call_count == 1


@pytest.mark.asyncio
async def test_rate_limit_exhausted_returns_rate_limited_without_source_call() -> None:
    fake = FakeSource(
        rate_limit=RateLimitConfig(requests_per_minute=1, requests_per_day=10),
    )
    client = _make_supabase_mock(cache_row=None)

    svc = EnrichmentService(
        sources=[fake],
        supabase_client_factory=lambda: client,
        clock=_frozen_clock,
    )

    first = await svc.enrich("url", "http://a.example.com")
    assert first.status == "ok"

    # Second call with a different value (so cache miss) must be rate-limited
    second = await svc.enrich("url", "http://b.example.com")
    assert second.status == "rate_limited"
    assert second.payload is not None
    assert second.payload["reason"] == "rate_limit_exceeded"
    assert fake.call_count == 1  # Only the first call reached the source


@pytest.mark.asyncio
async def test_unknown_ioc_type_returns_unavailable_with_reason() -> None:
    fake = FakeSource(ioc_types={"url"})
    client = _make_supabase_mock(cache_row=None)

    svc = EnrichmentService(
        sources=[fake],
        supabase_client_factory=lambda: client,
        clock=_frozen_clock,
    )

    result = await svc.enrich("btc", "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh")

    assert result.status == "unavailable"
    assert result.source == "none"
    assert result.payload is not None
    assert result.payload["reason"] == "no_source_registered"
    assert fake.call_count == 0


@pytest.mark.asyncio
async def test_enrich_logs_one_info_line_per_call_with_required_fields(
    caplog: pytest.LogCaptureFixture,
) -> None:
    fake = FakeSource()
    client = _make_supabase_mock(cache_row=None)

    svc = EnrichmentService(
        sources=[fake],
        supabase_client_factory=lambda: client,
        clock=_frozen_clock,
    )

    caplog.clear()
    with caplog.at_level(logging.INFO, logger="phishguard.services.enrichment_service"):
        await svc.enrich("url", "http://evil.example.com")

    enrichment_records = [
        r for r in caplog.records if r.getMessage() == "enrichment_call"
    ]
    assert len(enrichment_records) == 1
    record = enrichment_records[0]
    assert record.source == "fake"  # type: ignore[attr-defined]
    assert record.ioc_type == "url"  # type: ignore[attr-defined]
    assert record.status == "ok"  # type: ignore[attr-defined]
    assert record.cached is False  # type: ignore[attr-defined]
    assert record.cache_hit is False  # type: ignore[attr-defined]
    assert isinstance(record.latency_ms, int)  # type: ignore[attr-defined]
    assert hasattr(record, "value_hash")
    # Raw value must NOT leak into the log record
    assert "evil.example.com" not in str(record.value_hash)  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_raw_pii_value_never_leaks_into_logs(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """PII-safety: a raw IOC value must never appear in any log record."""
    fake = FakeSource(ioc_types={"phone"})
    client = _make_supabase_mock(cache_row=None)

    svc = EnrichmentService(
        sources=[fake],
        supabase_client_factory=lambda: client,
        clock=_frozen_clock,
    )

    sensitive = "+48 500 123 456"
    caplog.clear()
    with caplog.at_level(logging.INFO):
        await svc.enrich("phone", sensitive)

    for record in caplog.records:
        assert sensitive not in record.getMessage()
        # Also check every attribute value on the record for leakage
        for attr_name, attr_val in vars(record).items():
            if attr_name.startswith("_"):
                continue
            assert sensitive not in str(attr_val), (
                f"Raw PII leaked into log attribute: {attr_name}"
            )
