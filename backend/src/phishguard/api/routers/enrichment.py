"""Enrichment API endpoints for PhishGuard (US-034+).

Exposes IOC enrichment results via the ``EnrichmentService``.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from phishguard.api.dependencies import get_current_user_id
from phishguard.services.enrichment_service import EnrichmentResult, EnrichmentService
from phishguard.services.sources.abuseipdb_source import AbuseIPDBSource
from phishguard.services.sources.btc_source import BtcEnrichmentSource
from phishguard.services.sources.phone_source import PhoneNumberSource
from phishguard.services.sources.vt_source import VirusTotalSource

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/enrichment", tags=["enrichment"])

# ---------------------------------------------------------------------------
# Module-level singleton — instantiated once at import time.
# A future refactoring may move this into a FastAPI dependency / lifespan.
# ---------------------------------------------------------------------------

_enrichment_service: EnrichmentService | None = None


def _get_enrichment_service() -> EnrichmentService:
    global _enrichment_service  # noqa: PLW0603
    if _enrichment_service is None:
        btc_source = BtcEnrichmentSource()
        vt_source = VirusTotalSource()
        abuseipdb_source = AbuseIPDBSource()
        phone_source = PhoneNumberSource()
        _enrichment_service = EnrichmentService(
            sources=[btc_source, vt_source, abuseipdb_source, phone_source],
        )
    return _enrichment_service


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class EnrichmentResponse(BaseModel):
    """Public API response for an enrichment request."""

    status: str = Field(..., description="ok | unavailable | rate_limited | error")
    source: str = Field(..., description="Name of the enrichment source used")
    ioc_type: str = Field(..., description="IOC type that was enriched")
    payload: dict[str, Any] | None = Field(
        None, description="Enrichment data (source-specific)"
    )
    cached: bool = Field(False, description="Whether the result came from cache")
    latency_ms: int = Field(0, description="Round-trip time in milliseconds")


class QuotaResponse(BaseModel):
    """Rate-limit quota status for an enrichment source."""

    source: str
    requests_used_minute: int
    requests_used_day: int
    limit_per_minute: int
    limit_per_day: int
    available_day: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/quota",
    response_model=list[QuotaResponse],
    status_code=status.HTTP_200_OK,
    summary="Get enrichment source rate-limit quota",
    description=(
        "Returns current rate-limit usage for all registered enrichment sources."
    ),
)
async def get_enrichment_quota(
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> list[QuotaResponse]:
    svc = _get_enrichment_service()
    limiter = svc._rate_limiter

    seen: set[str] = set()
    results: list[QuotaResponse] = []
    for source in svc._sources_by_type.values():
        if source.name in seen:
            continue
        seen.add(source.name)
        minute_used, day_used = limiter.get_usage(source.name)
        results.append(
            QuotaResponse(
                source=source.name,
                requests_used_minute=minute_used,
                requests_used_day=day_used,
                limit_per_minute=source.rate_limit.requests_per_minute,
                limit_per_day=source.rate_limit.requests_per_day,
                available_day=max(0, source.rate_limit.requests_per_day - day_used),
            )
        )
    return results


@router.get(
    "/{ioc_type}/{value:path}",
    response_model=EnrichmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Enrich an IOC value",
    description=(
        "Look up enrichment data for an IOC. Supports ioc_type='btc' "
        "(Bitcoin wallet), 'url' and 'domain' (VirusTotal), 'ip' (AbuseIPDB)."
    ),
)
async def enrich_ioc(
    ioc_type: str,
    value: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
    refresh: bool = False,
) -> EnrichmentResponse:
    """Enrich a single IOC value.

    Args:
        ioc_type: The IOC type (e.g. ``btc``, ``url``, ``domain``).
        value: The raw IOC value to enrich.
        user_id: Authenticated user (from JWT).
        refresh: Whether to bypass cache and fetch fresh data.

    Returns:
        EnrichmentResponse with source-specific payload.
    """
    allowed_types = {"btc", "url", "domain", "ip", "phone"}
    if ioc_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported IOC type: {ioc_type}. "
                f"Supported: {', '.join(sorted(allowed_types))}"
            ),
        )

    svc = _get_enrichment_service()
    result: EnrichmentResult = await svc.enrich(ioc_type, value, force_refresh=refresh)

    logger.info(
        "Enrichment request by user %s for %s (status=%s, cached=%s, refresh=%s)",
        user_id,
        ioc_type,
        result.status,
        result.cached,
        refresh,
    )

    return EnrichmentResponse(
        status=result.status,
        source=result.source,
        ioc_type=result.ioc_type,
        payload=result.payload,
        cached=result.cached,
        latency_ms=result.latency_ms,
    )
