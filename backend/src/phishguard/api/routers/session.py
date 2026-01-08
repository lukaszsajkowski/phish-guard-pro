"""Session management API endpoints for PhishGuard.

Provides endpoints for ending sessions, viewing summaries, and exporting data.
Requirements: US-016, US-017, US-018, US-019, US-020
"""

import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field

from phishguard.api.dependencies import get_current_user_id
from phishguard.services import session_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/session", tags=["session"])


class EndSessionRequest(BaseModel):
    """Request model for ending a session."""

    reason: str = Field(
        default="manual",
        description="Reason for ending: 'manual', 'unmasking', or 'limit'",
    )


class EndSessionResponse(BaseModel):
    """Response model for session end."""

    session_id: str = Field(..., description="The session ID")
    status: str = Field(..., description="Session status (archived)")
    message: str = Field(..., description="Confirmation message")


class SessionSummaryResponse(BaseModel):
    """Response model for session summary."""

    session_id: str
    exchange_count: int
    session_start: str
    session_end: str
    attack_type: str
    attack_type_display: str
    attack_confidence: float
    iocs: list[dict]
    total_responses: int
    duration_seconds: float
    formatted_duration: str
    risk_score: int
    high_value_ioc_count: int


class SessionRestoreResponse(BaseModel):
    """Response model for session restoration (US-031)."""

    session_id: str
    status: str
    attack_type: str
    attack_type_display: str
    confidence: float
    persona: dict | None
    original_email: str | None  # Original email content for input field restoration
    messages: list[dict]
    iocs: list[dict]
    turn_count: int
    turn_limit: int
    is_at_limit: bool


@router.get(
    "/{session_id}/restore",
    response_model=SessionRestoreResponse,
    status_code=status.HTTP_200_OK,
)
async def restore_session(
    session_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> SessionRestoreResponse:
    """Restore a session's complete state for page refresh persistence.

    Per US-031, allows the frontend to restore full conversation state
    after browser refresh by fetching all session data in one call.

    Args:
        session_id: The session to restore.
        user_id: The authenticated user's ID (from JWT).

    Returns:
        SessionRestoreResponse with complete session state.

    Raises:
        HTTPException: If session not found or not authorized.
    """
    from phishguard.models.classification import AttackType

    # Verify session exists and belongs to user
    session = await session_service.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    if session.get("user_id") != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this session",
        )

    # Get all session data
    messages = await session_service.get_session_messages(session_id)
    iocs = await session_service.get_session_iocs(session_id)
    session_info = await session_service.get_session_info(session_id)

    # Get attack type display name
    attack_type = session.get("attack_type", "unknown")
    try:
        attack_type_enum = AttackType(attack_type)
        attack_type_display = attack_type_enum.display_name
    except ValueError:
        attack_type_display = attack_type.replace("_", " ").title()

    # Convert messages to frontend format
    # Also extract original email for restoration
    original_email = None
    formatted_messages = []
    for msg in messages:
        metadata = msg.get("metadata", {})
        if metadata.get("type") == "original_email":
            original_email = msg.get("content", "")
            continue

        role = msg.get("role", "")
        if role == "assistant":
            sender = "bot"
        elif role == "scammer":
            sender = "scammer"
        else:
            continue  # Skip unknown roles

        formatted_messages.append({
            "id": msg.get("id", ""),
            "sender": sender,
            "content": msg.get("content", ""),
            "timestamp": msg.get("created_at", ""),
            "thinking": metadata.get("thinking"),
        })

    # Format IOCs for frontend
    formatted_iocs = []
    for ioc in iocs:
        ioc_type = ioc.get("type", "")
        is_high_value = ioc_type in ("btc", "iban", "btc_wallet")
        formatted_iocs.append({
            "id": ioc.get("id", ""),
            "type": ioc_type,
            "value": ioc.get("value", ""),
            "is_high_value": is_high_value,
            "created_at": ioc.get("created_at", ""),
        })

    # Get confidence from session (US-031 fix)
    confidence = session.get("attack_confidence", 0.0) or 0.0

    logger.info(
        "Restored session %s for user %s: %d messages, %d IOCs",
        session_id,
        user_id,
        len(formatted_messages),
        len(formatted_iocs),
    )

    return SessionRestoreResponse(
        session_id=session_id,
        status=session.get("status", "active"),
        attack_type=attack_type,
        attack_type_display=attack_type_display,
        confidence=confidence,
        persona=session.get("persona"),
        original_email=original_email,
        messages=formatted_messages,
        iocs=formatted_iocs,
        turn_count=session_info["turn_count"],
        turn_limit=session_info["turn_limit"],
        is_at_limit=session_info["is_at_limit"],
    )


@router.post(
    "/{session_id}/end",
    response_model=EndSessionResponse,
    status_code=status.HTTP_200_OK,
)
async def end_session(
    session_id: str,
    request: EndSessionRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> EndSessionResponse:
    """End a session and mark it as archived.

    Per US-017, user can manually end session at any time.
    Also used when unmasking is detected (US-016).

    Args:
        session_id: The session to end.
        request: The request body with reason.
        user_id: The authenticated user's ID (from JWT).

    Returns:
        EndSessionResponse with confirmation.

    Raises:
        HTTPException: If session not found or not authorized.
    """
    # Verify session exists and belongs to user
    session = await session_service.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    if session.get("user_id") != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to end this session",
        )

    # End the session
    await session_service.end_session(session_id)

    logger.info(
        "Session %s ended by user %s, reason: %s",
        session_id,
        user_id,
        request.reason,
    )

    return EndSessionResponse(
        session_id=session_id,
        status="archived",
        message=f"Session ended successfully ({request.reason})",
    )


@router.get(
    "/{session_id}/summary",
    response_model=SessionSummaryResponse,
    status_code=status.HTTP_200_OK,
)
async def get_session_summary(
    session_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> SessionSummaryResponse:
    """Get session summary for the final report.

    Per US-018, displays metrics and collected IOCs.

    Args:
        session_id: The session to summarize.
        user_id: The authenticated user's ID (from JWT).

    Returns:
        SessionSummaryResponse with all summary data.

    Raises:
        HTTPException: If session not found or not authorized.
    """
    # Verify session exists and belongs to user
    session = await session_service.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    if session.get("user_id") != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this session",
        )

    # Get summary data
    summary = await session_service.get_session_summary(session_id)

    # Calculate computed fields
    from datetime import datetime

    try:
        start = datetime.fromisoformat(summary["session_start"].replace("Z", "+00:00"))
        end = datetime.fromisoformat(summary["session_end"].replace("Z", "+00:00"))
        duration_seconds = (end - start).total_seconds()
    except (ValueError, KeyError):
        duration_seconds = 0.0

    # Format duration
    total_seconds = int(duration_seconds)
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    formatted_duration = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"

    # Count high-value IOCs
    high_value_ioc_count = sum(
        1 for ioc in summary.get("iocs", [])
        if ioc.get("is_high_value", False)
    )

    # Calculate risk score (1-10)
    risk_score = session_service.calculate_risk_score(
        summary["attack_type"],
        summary["iocs"],
    )

    return SessionSummaryResponse(
        session_id=summary["session_id"],
        exchange_count=summary["exchange_count"],
        session_start=summary["session_start"],
        session_end=summary["session_end"],
        attack_type=summary["attack_type"],
        attack_type_display=summary["attack_type_display"],
        attack_confidence=summary["attack_confidence"],
        iocs=summary["iocs"],
        total_responses=summary.get("total_responses", 0),
        duration_seconds=duration_seconds,
        formatted_duration=formatted_duration,
        risk_score=risk_score,
        high_value_ioc_count=high_value_ioc_count,
    )


@router.get("/{session_id}/export/json")
async def export_session_json(
    session_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> Response:
    """Export full session data as JSON file.

    Per US-019, exports conversation history and IOCs.

    Args:
        session_id: The session to export.
        user_id: The authenticated user's ID (from JWT).

    Returns:
        JSON file download response.

    Raises:
        HTTPException: If session not found or not authorized.
    """
    # Verify session exists and belongs to user
    session = await session_service.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    if session.get("user_id") != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to export this session",
        )

    # Get export data
    export_data = await session_service.export_session_json(session_id)
    filename = session_service.generate_export_filename("phishguard_session", "json")

    return Response(
        content=json.dumps(export_data, indent=2, ensure_ascii=False),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get("/{session_id}/export/csv")
async def export_iocs_csv(
    session_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> Response:
    """Export IOCs as CSV file.

    Per US-020, exports IOCs for import into security tools.

    Args:
        session_id: The session to export IOCs from.
        user_id: The authenticated user's ID (from JWT).

    Returns:
        CSV file download response.

    Raises:
        HTTPException: If session not found or not authorized.
    """
    # Verify session exists and belongs to user
    session = await session_service.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    if session.get("user_id") != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to export this session",
        )

    # Get IOCs and export to CSV
    iocs = await session_service.get_session_iocs(session_id)
    csv_content = session_service.export_iocs_csv(iocs)
    filename = session_service.generate_export_filename("phishguard_iocs", "csv")

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
