"""IOC (Indicator of Compromise) API endpoints for PhishGuard."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from phishguard.api.dependencies import get_current_user_id
from phishguard.services import session_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ioc", tags=["ioc"])


class IOCResponse(BaseModel):
    """Response model for a single IOC."""

    id: str = Field(..., description="The IOC's unique ID")
    type: str = Field(..., description="IOC type: btc, iban, phone, url")
    value: str = Field(..., description="The extracted IOC value")
    confidence: float = Field(..., description="Confidence score (0.0-1.0)")
    created_at: str = Field(..., description="When the IOC was extracted")
    is_high_value: bool = Field(..., description="Whether this is a high-value IOC")


class SessionIOCsResponse(BaseModel):
    """Response model for session IOCs."""

    session_id: str = Field(..., description="The session ID")
    iocs: list[IOCResponse] = Field(default_factory=list, description="List of IOCs")
    total_count: int = Field(..., description="Total number of IOCs")
    high_value_count: int = Field(..., description="Number of high-value IOCs")


@router.get(
    "/session/{session_id}",
    response_model=SessionIOCsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get session IOCs",
    description="Retrieve all IOCs extracted for a session. Requires authentication.",
)
async def get_session_iocs(
    session_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> SessionIOCsResponse:
    """
    Retrieve all IOCs for a session.

    Args:
        session_id: The session's UUID.
        user_id: The authenticated user's ID (from JWT).

    Returns:
        SessionIOCsResponse with list of IOCs.

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

    # Retrieve IOCs
    iocs_data = await session_service.get_session_iocs(session_id)

    # Transform to response format
    iocs = []
    high_value_count = 0

    for ioc in iocs_data:
        ioc_type = ioc.get("type", "")
        is_high_value = ioc_type in ("btc", "iban")

        if is_high_value:
            high_value_count += 1

        iocs.append(
            IOCResponse(
                id=ioc.get("id", ""),
                type=ioc_type,
                value=ioc.get("value", ""),
                confidence=ioc.get("confidence", 0.0),
                created_at=ioc.get("created_at", ""),
                is_high_value=is_high_value,
            )
        )

    logger.info(
        "Retrieved %d IOCs for session %s (user %s)",
        len(iocs),
        session_id,
        user_id,
    )

    return SessionIOCsResponse(
        session_id=session_id,
        iocs=iocs,
        total_count=len(iocs),
        high_value_count=high_value_count,
    )
