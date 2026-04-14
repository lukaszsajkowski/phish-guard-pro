"""Enrichment API endpoints for PhishGuard (US-034+).

Exposes IOC enrichment results via the ``EnrichmentService``.
"""

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from phishguard.api.dependencies import get_current_user_id
from phishguard.services.enrichment_service import EnrichmentResult, EnrichmentService
from phishguard.services.sources.btc_source import BtcEnrichmentSource

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
        _enrichment_service = EnrichmentService(sources=[btc_source])
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


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/{ioc_type}/{value}",
    response_model=EnrichmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Enrich an IOC value",
    description=(
        "Look up enrichment data for an IOC. Currently supports ioc_type='btc' "
        "(Bitcoin wallet enrichment via mempool.space + bitcoinabuse)."
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
        ioc_type: The IOC type (e.g. ``btc``, ``url``, ``phone``).
        value: The raw IOC value to enrich.
        user_id: Authenticated user (from JWT).
        refresh: Whether to bypass cache and fetch fresh data.

    Returns:
        EnrichmentResponse with source-specific payload.
    """
    allowed_types = {"btc"}  # Expand as US-035..US-037 land
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
