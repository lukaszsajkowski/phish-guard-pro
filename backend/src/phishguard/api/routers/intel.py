"""Intel Dashboard API endpoints for PhishGuard.

Provides unified endpoint for retrieving complete Intel Dashboard data
including attack type, IOCs, risk score, and timeline.
"""

import logging
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from phishguard.api.dependencies import get_current_user_id
from phishguard.services import session_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/intel", tags=["intel"])


class TimelineEvent(BaseModel):
    """A single timeline event."""

    timestamp: str = Field(..., description="When the event occurred")
    event_type: str = Field(..., description="Type of event: ioc_extracted")
    description: str = Field(..., description="Human-readable event description")
    ioc_id: str | None = Field(None, description="Associated IOC ID if applicable")
    is_high_value: bool = Field(False, description="Whether this is a high-value event")


class IOCItem(BaseModel):
    """A single IOC in the dashboard."""

    id: str = Field(..., description="IOC unique ID")
    type: str = Field(..., description="IOC type: btc, iban, phone, url")
    value: str = Field(..., description="The extracted value")
    is_high_value: bool = Field(..., description="Whether this is high-value")
    created_at: str = Field(..., description="Extraction timestamp")


class RiskComponentScoreResponse(BaseModel):
    """Score for a single risk component (US-032)."""

    component: str = Field(..., description="Component identifier")
    raw_score: float = Field(..., description="Raw score (0-4 scale)")
    weight: float = Field(..., description="Weight of this component (0-1)")
    weighted_score: float = Field(..., description="Weighted contribution to total")
    explanation: str = Field(..., description="Human-readable explanation")


class RiskScoreBreakdown(BaseModel):
    """Enhanced risk score breakdown with all components (US-032)."""

    total_score: float = Field(..., description="Final risk score (1-10)")
    risk_level: Literal["low", "medium", "high"] = Field(
        ..., description="Risk level classification"
    )
    components: list[RiskComponentScoreResponse] = Field(
        ..., description="Individual component scores"
    )


class IntelDashboardResponse(BaseModel):
    """Complete Intel Dashboard data response."""

    session_id: str = Field(..., description="Session ID")

    # Section 1: Attack Type
    attack_type: str = Field(..., description="Classified attack type")
    confidence: float = Field(..., description="Classification confidence (0-100)")

    # Section 2: Collected IOCs
    iocs: list[IOCItem] = Field(default_factory=list, description="Extracted IOCs")
    total_iocs: int = Field(..., description="Total IOC count")
    high_value_count: int = Field(..., description="High-value IOC count")

    # Section 3: Risk Score (US-032: Enhanced with breakdown)
    risk_score: int = Field(..., description="Risk score from 1-10", ge=1, le=10)
    risk_score_breakdown: RiskScoreBreakdown | None = Field(
        None, description="Detailed breakdown of risk score components (US-032)"
    )

    # Section 4: Timeline
    timeline: list[TimelineEvent] = Field(
        default_factory=list, description="Chronological extraction events"
    )


@router.get(
    "/dashboard/{session_id}",
    response_model=IntelDashboardResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Intel Dashboard data",
    description="Retrieve complete Intel Dashboard data for a session including "
    "attack type, IOCs, risk score, and timeline.",
)
async def get_intel_dashboard(
    session_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> IntelDashboardResponse:
    """
    Retrieve complete Intel Dashboard data for a session.

    Args:
        session_id: The session's UUID.
        user_id: The authenticated user's ID (from JWT).

    Returns:
        IntelDashboardResponse with all 4 dashboard sections.

    Raises:
        HTTPException: If session not found or not authorized.
    """
    # Verify session exists and user owns it
    session = await session_service.get_session(session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    if session.get("user_id") != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this session",
        )

    # Get attack type and confidence from session
    attack_type = session.get("attack_type", "unknown")

    # Confidence is stored in metadata or we default to 0
    # For now, we'll retrieve it from classification if available
    # TODO: Store confidence in session table
    confidence = 0.0

    # Get IOCs
    iocs_data = await session_service.get_session_iocs(session_id)

    # Transform IOCs to response format
    iocs = []
    high_value_count = 0

    for ioc in iocs_data:
        ioc_type = ioc.get("type", "")
        is_high_value = ioc_type in ("btc", "iban")

        if is_high_value:
            high_value_count += 1

        iocs.append(
            IOCItem(
                id=ioc.get("id", ""),
                type=ioc_type,
                value=ioc.get("value", ""),
                is_high_value=is_high_value,
                created_at=ioc.get("created_at", ""),
            )
        )

    # Calculate enhanced risk score with breakdown (US-032)
    enhanced_score = await session_service.get_session_enhanced_risk_score(session_id)
    risk_score = int(round(enhanced_score.total_score))

    # Build breakdown response
    risk_score_breakdown = RiskScoreBreakdown(
        total_score=enhanced_score.total_score,
        risk_level=enhanced_score.risk_level.value,
        components=[
            RiskComponentScoreResponse(
                component=c.component.value,
                raw_score=c.raw_score,
                weight=c.weight,
                weighted_score=c.weighted_score,
                explanation=c.explanation,
            )
            for c in enhanced_score.components
        ],
    )

    # Get timeline
    timeline_data = await session_service.get_session_timeline(session_id)
    timeline = [
        TimelineEvent(
            timestamp=event.get("timestamp", ""),
            event_type=event.get("event_type", ""),
            description=event.get("description", ""),
            ioc_id=event.get("ioc_id"),
            is_high_value=event.get("is_high_value", False),
        )
        for event in timeline_data
    ]

    logger.info(
        "Retrieved Intel Dashboard for session %s (user %s): "
        "%d IOCs, risk_score=%d",
        session_id,
        user_id,
        len(iocs),
        risk_score,
    )

    return IntelDashboardResponse(
        session_id=session_id,
        attack_type=attack_type,
        confidence=confidence,
        iocs=iocs,
        total_iocs=len(iocs),
        high_value_count=high_value_count,
        risk_score=risk_score,
        risk_score_breakdown=risk_score_breakdown,
        timeline=timeline,
    )
