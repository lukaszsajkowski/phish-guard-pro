"""Session service for persisting analysis sessions to Supabase.

This module provides functions to create and manage phishing analysis
sessions and their associated messages in the database.
"""

import logging
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from supabase import Client, create_client

from phishguard.core import get_settings
from phishguard.models.classification import AttackType, ClassificationResult
from phishguard.models.risk_score import EnhancedRiskScore
from phishguard.services.risk_score_service import (
    calculate_enhanced_risk_score,
    calculate_simple_risk_score,
)

logger = logging.getLogger(__name__)


def _get_supabase_client() -> Client:
    """Get a Supabase client with service role key for database operations."""
    settings = get_settings()
    return create_client(
        settings.supabase_url,
        settings.supabase_service_role_key,
    )


async def create_session(
    user_id: str,
    email_content: str,
) -> str:
    """Create a new analysis session.

    Args:
        user_id: The authenticated user's UUID.
        email_content: The original email content being analyzed.

    Returns:
        The created session's UUID as a string.

    Raises:
        Exception: If session creation fails.
    """
    supabase = _get_supabase_client()

    # Create the session
    session_data = {
        "user_id": user_id,
        "title": _generate_session_title(email_content),
        "status": "active",
    }

    result = supabase.table("sessions").insert(session_data).execute()

    if not result.data or len(result.data) == 0:
        raise Exception("Failed to create session")

    session_id = result.data[0]["id"]
    logger.info("Created session %s for user %s", session_id, user_id)

    # Store the original email as the first message
    await add_message(
        session_id=session_id,
        role="user",
        content=email_content,
        metadata={"type": "original_email"},
    )

    return session_id


async def add_message(
    session_id: str,
    role: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> str:
    """Add a message to a session.

    Args:
        session_id: The session's UUID.
        role: Message role ('user', 'assistant', or 'scammer').
        content: The message content.
        metadata: Optional metadata about the message.

    Returns:
        The created message's UUID as a string.

    Raises:
        Exception: If message creation fails.
    """
    supabase = _get_supabase_client()

    message_data = {
        "session_id": session_id,
        "role": role,
        "content": content,
        "metadata": metadata or {},
    }

    result = supabase.table("messages").insert(message_data).execute()

    if not result.data or len(result.data) == 0:
        raise Exception("Failed to create message")

    message_id = result.data[0]["id"]
    logger.debug("Added message %s to session %s", message_id, session_id)

    return message_id


async def update_session_classification(
    session_id: str,
    classification_result: ClassificationResult,
) -> None:
    """Update a session with classification results.

    Args:
        session_id: The session's UUID.
        classification_result: The classification result to store.

    Raises:
        Exception: If update fails.
    """
    supabase = _get_supabase_client()

    update_data: dict[str, Any] = {
        "attack_type": classification_result.attack_type.value,
        "attack_confidence": classification_result.confidence,  # For US-031
    }

    # Add persona if present
    if classification_result.persona:
        update_data["persona"] = {
            "persona_type": classification_result.persona.persona_type.value,
            "name": classification_result.persona.name,
            "age": classification_result.persona.age,
            "style_description": classification_result.persona.style_description,
            "background": classification_result.persona.background,
        }

    result = (
        supabase.table("sessions").update(update_data).eq("id", session_id).execute()
    )

    if not result.data or len(result.data) == 0:
        raise Exception("Failed to update session")

    logger.info(
        "Updated session %s with attack_type=%s confidence=%s",
        session_id,
        classification_result.attack_type.value,
        classification_result.confidence,
    )


def _generate_session_title(email_content: str, max_length: int = 50) -> str:
    """Generate a session title from email content.

    Args:
        email_content: The email content.
        max_length: Maximum title length.

    Returns:
        A truncated, cleaned title.
    """
    # Take first line or first N characters
    first_line = email_content.split("\n")[0].strip()

    if len(first_line) <= max_length:
        return first_line

    return first_line[: max_length - 3] + "..."


async def get_session(session_id: str) -> dict[str, Any] | None:
    """Retrieve a session by its ID.

    Args:
        session_id: The session's UUID.

    Returns:
        Session data as a dict, or None if not found.
    """
    supabase = _get_supabase_client()

    result = supabase.table("sessions").select("*").eq("id", session_id).execute()

    if not result.data or len(result.data) == 0:
        return None

    return result.data[0]


async def get_session_messages(session_id: str) -> list[dict[str, Any]]:
    """Retrieve all messages for a session.

    Args:
        session_id: The session's UUID.

    Returns:
        List of message dicts, ordered by creation time.
    """
    supabase = _get_supabase_client()

    result = (
        supabase.table("messages")
        .select("*")
        .eq("session_id", session_id)
        .order("created_at", desc=False)
        .execute()
    )

    return result.data if result.data else []


async def get_original_email(session_id: str) -> str | None:
    """Retrieve the original email content for a session.

    Args:
        session_id: The session's UUID.

    Returns:
        The original email content, or None if not found.
    """
    supabase = _get_supabase_client()

    result = (
        supabase.table("messages")
        .select("content")
        .eq("session_id", session_id)
        .eq("role", "user")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    if not result.data or len(result.data) == 0:
        return None

    return result.data[0]["content"]


async def add_bot_response(
    session_id: str,
    content: str,
    thinking: dict[str, Any] | None = None,
    generation_time_ms: int = 0,
) -> str:
    """Add a bot-generated response to a session.

    Args:
        session_id: The session's UUID.
        content: The response content.
        thinking: Optional agent thinking metadata.
        generation_time_ms: Time taken to generate the response.

    Returns:
        The created message's UUID as a string.
    """
    metadata: dict[str, Any] = {
        "type": "bot_response",
        "generation_time_ms": generation_time_ms,
    }

    if thinking:
        metadata["thinking"] = thinking

    return await add_message(
        session_id=session_id,
        role="assistant",
        content=content,
        metadata=metadata,
    )


async def update_message_content(
    message_id: str,
    new_content: str,
) -> None:
    """Update an existing message's content.

    Used when a user edits a generated response (US-008).

    Args:
        message_id: The message's UUID.
        new_content: The new content to save.

    Raises:
        Exception: If update fails or message not found.
    """
    supabase = _get_supabase_client()

    # Update the message content
    result = (
        supabase.table("messages")
        .update({"content": new_content})
        .eq("id", message_id)
        .execute()
    )

    if not result.data or len(result.data) == 0:
        raise Exception(f"Failed to update message {message_id}")

    logger.info("Updated message %s content", message_id)


async def add_scammer_message(
    session_id: str,
    content: str,
) -> str:
    """Add a scammer message to a session.

    Used when a user pastes a scammer's response (US-010).

    Args:
        session_id: The session's UUID.
        content: The scammer's message content.

    Returns:
        The created message's UUID as a string.
    """
    metadata: dict[str, Any] = {
        "type": "scammer_message",
    }

    return await add_message(
        session_id=session_id,
        role="scammer",
        content=content,
        metadata=metadata,
    )


async def get_conversation_history(session_id: str) -> list[dict[str, Any]]:
    """Retrieve conversation history for a session (excluding original email).

    Returns messages in chronological order, formatted for the ConversationAgent.

    Args:
        session_id: The session's UUID.

    Returns:
        List of message dicts with 'sender' and 'content' keys.
    """
    messages = await get_session_messages(session_id)

    # Filter out the original email and format for conversation
    history = []
    for msg in messages:
        metadata = msg.get("metadata", {})
        if metadata.get("type") == "original_email":
            continue

        # Map database roles to conversation sender types
        role = msg.get("role", "")
        if role == "assistant":
            sender = "bot"
        elif role == "scammer":
            sender = "scammer"
        else:
            continue  # Skip unknown roles

        history.append(
            {
                "sender": sender,
                "content": msg.get("content", ""),
            }
        )

    return history


async def save_extracted_iocs(
    session_id: str,
    iocs: list[dict[str, Any]],
) -> list[str]:
    """Save extracted IOCs to the ioc_extracted table.

    Args:
        session_id: The session's UUID.
        iocs: List of IOC dicts with keys: type, value, context, is_high_value.

    Returns:
        List of created IOC UUIDs.

    Raises:
        Exception: If IOC insertion fails.
    """
    if not iocs:
        return []

    supabase = _get_supabase_client()

    # Prepare IOC records for insertion
    ioc_records = []
    for ioc in iocs:
        # Map backend IOCType values to database values
        ioc_type = ioc.get("type", "")
        if ioc_type == "btc_wallet":
            ioc_type = "btc"

        ioc_records.append(
            {
                "session_id": session_id,
                "type": ioc_type,
                "value": ioc.get("value", ""),
                "confidence": 1.0 if ioc.get("is_high_value", False) else 0.8,
            }
        )

    result = supabase.table("ioc_extracted").insert(ioc_records).execute()

    if not result.data:
        raise Exception("Failed to save IOCs")

    ioc_ids = [record["id"] for record in result.data]
    logger.info(
        "Saved %d IOCs to session %s: %s",
        len(ioc_ids),
        session_id,
        [r["type"] for r in ioc_records],
    )

    return ioc_ids


async def get_session_iocs(session_id: str) -> list[dict[str, Any]]:
    """Retrieve all IOCs for a session.

    Args:
        session_id: The session's UUID.

    Returns:
        List of IOC dicts ordered by creation time.
    """
    supabase = _get_supabase_client()

    result = (
        supabase.table("ioc_extracted")
        .select("*")
        .eq("session_id", session_id)
        .order("created_at", desc=False)
        .execute()
    )

    return result.data if result.data else []


def calculate_risk_score(
    attack_type: str,
    iocs: list[dict[str, Any]],
    scammer_messages: list[str] | None = None,
    victim_name: str | None = None,
    victim_first_name: str | None = None,
) -> int:
    """Calculate risk score (1-10) using the enhanced multi-dimensional calculator.

    Uses 6 weighted components (US-032):
    - Attack Severity (25%): CEO Fraud=4, Crypto=4, etc.
    - IOC Quality (25%): BTC=3, IBAN=3, phone=2, URL=1
    - IOC Quantity (15%): +0.5 per IOC, max 1.5 points
    - Scammer Engagement (15%): Response length and frequency
    - Urgency Tactics (10%): Pressure keywords detection
    - Personalization (10%): Name usage and context references

    Args:
        attack_type: The classified attack type.
        iocs: List of extracted IOCs.
        scammer_messages: Optional list of scammer message texts.
        victim_name: Optional full name of victim persona.
        victim_first_name: Optional first name of victim persona.

    Returns:
        Risk score from 1 to 10.
    """
    return calculate_simple_risk_score(
        attack_type=attack_type,
        iocs=iocs,
        scammer_messages=scammer_messages,
        victim_name=victim_name,
        victim_first_name=victim_first_name,
    )


async def get_session_enhanced_risk_score(
    session_id: str,
) -> EnhancedRiskScore:
    """Calculate enhanced risk score with full breakdown for a session.

    Retrieves all necessary data from the session and calculates
    the multi-dimensional risk score with component breakdown.

    Args:
        session_id: The session's UUID.

    Returns:
        EnhancedRiskScore with total score and component breakdown.
    """
    # Get session data
    session = await get_session(session_id)
    if not session:
        raise Exception(f"Session {session_id} not found")

    # Get attack type
    attack_type = session.get("attack_type", "unknown")

    # Get persona info for personalization detection
    persona = session.get("persona", {})
    victim_name = persona.get("name") if persona else None
    victim_first_name = None
    if victim_name:
        parts = victim_name.split()
        victim_first_name = parts[0] if len(parts) > 1 else victim_name

    # Get IOCs
    iocs = await get_session_iocs(session_id)

    # US-040: Build enrichment map (ioc_value → best reputation label).
    # Queries ioc_enrichment for all IOC IDs in this session, picks the most
    # severe reputation across all sources per IOC.
    ioc_enrichment_map: dict[str, str] | None = None
    ioc_ids = [ioc["id"] for ioc in iocs if ioc.get("id")]
    if ioc_ids:
        try:
            supabase = _get_supabase_client()
            enrich_resp = (
                supabase.table("ioc_enrichment")
                .select("ioc_id, payload")
                .in_("ioc_id", ioc_ids)
                .eq("status", "ok")
                .execute()
            )
            enrich_rows = enrich_resp.data or []

            # Severity ranking — higher number wins when multiple sources disagree
            _SEVERITY: dict[str, int] = {
                "malicious": 3,
                "suspicious": 2,
                "clean": 1,
                "unknown": 0,
            }
            id_to_rep: dict[str, str] = {}
            for row in enrich_rows:
                iid = row.get("ioc_id")
                rep = (row.get("payload") or {}).get("reputation", "unknown")
                if _SEVERITY.get(rep, 0) > _SEVERITY.get(id_to_rep.get(iid, ""), 0):
                    id_to_rep[iid] = rep

            if id_to_rep:
                ioc_enrichment_map = {
                    ioc["value"]: id_to_rep[ioc["id"]]
                    for ioc in iocs
                    if ioc.get("id") in id_to_rep and ioc.get("value")
                }
        except Exception:  # noqa: BLE001 - enrichment failures must not block risk score
            pass

    # Get scammer messages
    messages = await get_session_messages(session_id)
    scammer_messages = [
        msg.get("content", "") for msg in messages if msg.get("role") == "scammer"
    ]

    return calculate_enhanced_risk_score(
        attack_type=attack_type,
        iocs=iocs,
        scammer_messages=scammer_messages,
        victim_name=victim_name,
        victim_first_name=victim_first_name,
        ioc_enrichment=ioc_enrichment_map,
    )


async def get_session_timeline(session_id: str) -> list[dict[str, Any]]:
    """Retrieve timeline events for a session.

    Returns IOC extraction events with timestamps.

    Args:
        session_id: The session's UUID.

    Returns:
        List of timeline event dicts ordered by timestamp.
    """
    iocs = await get_session_iocs(session_id)

    timeline_events = []
    for ioc in iocs:
        ioc_type = ioc.get("type", "")
        is_high_value = ioc_type in ("btc", "iban")
        ioc_val = ioc.get("value", "")[:20]
        desc = f"Extracted {ioc_type.upper()}: {ioc_val}..."

        timeline_events.append(
            {
                "timestamp": ioc.get("created_at", ""),
                "event_type": "ioc_extracted",
                "description": desc,
                "ioc_id": ioc.get("id"),
                "is_high_value": is_high_value,
            }
        )

    return timeline_events


async def get_turn_count(session_id: str) -> int:
    """Get the current turn count for a session.

    A turn is counted as a bot (assistant) response. The first response
    counts as turn 1.

    Args:
        session_id: The session's UUID.

    Returns:
        Current turn count (1-based), or 0 if no bot responses yet.
    """
    supabase = _get_supabase_client()

    result = (
        supabase.table("messages")
        .select("id", count="exact")
        .eq("session_id", session_id)
        .eq("role", "assistant")
        .execute()
    )

    return result.count if result.count else 0


async def get_session_limit(session_id: str) -> int:
    """Get the turn limit for a session.

    Args:
        session_id: The session's UUID.

    Returns:
        Turn limit (default 20, can be extended).
    """
    session = await get_session(session_id)
    if not session:
        return 20

    return session.get("turn_limit", 20)


async def extend_session_limit(session_id: str, additional_turns: int = 10) -> int:
    """Extend the session's turn limit.

    Per US-015, clicking "Continue (+10 turns)" extends the limit.

    Args:
        session_id: The session's UUID.
        additional_turns: Number of turns to add (default 10).

    Returns:
        The new turn limit.

    Raises:
        Exception: If update fails.
    """
    supabase = _get_supabase_client()

    # Get current limit
    current_limit = await get_session_limit(session_id)
    new_limit = current_limit + additional_turns

    result = (
        supabase.table("sessions")
        .update({"turn_limit": new_limit})
        .eq("id", session_id)
        .execute()
    )

    if not result.data or len(result.data) == 0:
        raise Exception(f"Failed to extend limit for session {session_id}")

    logger.info(
        "Extended session %s limit from %d to %d",
        session_id,
        current_limit,
        new_limit,
    )

    return new_limit


async def get_session_info(session_id: str) -> dict[str, Any]:
    """Get session info including turn count and limit.

    Args:
        session_id: The session's UUID.

    Returns:
        Dict with turn_count, turn_limit, and is_at_limit.
    """
    turn_count = await get_turn_count(session_id)
    turn_limit = await get_session_limit(session_id)

    return {
        "turn_count": turn_count,
        "turn_limit": turn_limit,
        "is_at_limit": turn_count >= turn_limit,
    }


async def end_session(session_id: str) -> None:
    """Mark a session as ended/archived.

    Used when user manually ends session (US-017) or unmasking is detected (US-016).

    Args:
        session_id: The session's UUID.

    Raises:
        Exception: If update fails.
    """
    from datetime import UTC, datetime

    supabase = _get_supabase_client()

    result = (
        supabase.table("sessions")
        .update(
            {
                "status": "archived",
                "ended_at": datetime.now(UTC).isoformat(),
            }
        )
        .eq("id", session_id)
        .execute()
    )

    if not result.data or len(result.data) == 0:
        raise Exception(f"Failed to end session {session_id}")

    logger.info("Ended session %s", session_id)


async def get_session_summary(session_id: str) -> dict[str, Any]:
    """Generate a session summary for the final report (US-018).

    Args:
        session_id: The session's UUID.

    Returns:
        Dict containing all summary data.

    Raises:
        Exception: If session not found.
    """
    from datetime import UTC, datetime

    session = await get_session(session_id)
    if not session:
        raise Exception(f"Session {session_id} not found")

    # Get all messages for counting
    messages = await get_session_messages(session_id)

    # Count exchanges (bot responses)
    bot_messages = [m for m in messages if m.get("role") == "assistant"]
    exchange_count = len(bot_messages)

    # Count safe responses (those that didn't require regeneration)
    safe_responses = sum(
        1 for m in bot_messages if m.get("metadata", {}).get("safety_validated", True)
    )

    # Get IOCs
    iocs = await get_session_iocs(session_id)

    # Get attack type display name
    attack_type = session.get("attack_type", "unknown")
    try:
        attack_type_enum = AttackType(attack_type)
        attack_type_display = attack_type_enum.display_name
    except ValueError:
        attack_type_display = attack_type.replace("_", " ").title()

    # Get confidence from first classification message metadata
    attack_confidence = 0.0
    for msg in messages:
        metadata = msg.get("metadata", {})
        if metadata.get("type") == "original_email":
            break

    # Build IOC summary list
    ioc_summaries = []
    for ioc in iocs:
        ioc_type = ioc.get("type", "")
        is_high_value = ioc_type in ("btc", "iban", "btc_wallet")
        ioc_summaries.append(
            {
                "id": ioc.get("id", ""),
                "ioc_type": ioc_type,
                "value": ioc.get("value", ""),
                "is_high_value": is_high_value,
                "timestamp": ioc.get("created_at", ""),
            }
        )

    return {
        "session_id": session_id,
        "exchange_count": exchange_count,
        "session_start": session.get("created_at", ""),
        "session_end": session.get("ended_at") or datetime.now(UTC).isoformat(),
        "attack_type": attack_type,
        "attack_type_display": attack_type_display,
        "attack_confidence": attack_confidence,
        "iocs": ioc_summaries,
        "total_responses": exchange_count,
        "safe_responses": safe_responses,
    }


def _derive_threat_score(ioc_type: str, payload: dict[str, Any]) -> int:
    """Derive a 0-100 threat score from an enrichment payload.

    Uses the same heuristics as the frontend ``deriveThreatAssessment`` so
    exported values match what the user sees in the UI.
    """
    if ioc_type == "btc":
        reputation = payload.get("reputation", "unknown")
        report_count = int(payload.get("report_count") or 0)
        if reputation == "malicious":
            return min(100, 70 + round((report_count / 20) * 30))
        if reputation == "suspicious":
            return min(69, 40 + report_count * 10)
        tx_count = int(payload.get("tx_count") or 0)
        return 15 if tx_count > 0 else 5
    if ioc_type == "ip":
        return int(payload.get("abuse_confidence_score") or 0)
    rep = payload.get("reputation", "unknown")
    if rep == "malicious":
        return 90
    if rep == "suspicious":
        return 50
    if rep == "clean":
        return 10
    return 0


def _fetch_iocs_enrichment(ioc_ids: list[str]) -> dict[str, dict[str, Any]]:
    """Fetch enrichment summary for a list of IOC IDs (US-039).

    Returns a map from ``ioc_id`` to ``{threat_score, reputation, source}``.
    Only ``status="ok"`` rows are considered.  When multiple sources enriched
    the same IOC the most severe reputation wins.
    """
    if not ioc_ids:
        return {}
    _SEVERITY: dict[str, int] = {
        "malicious": 3,
        "suspicious": 2,
        "clean": 1,
        "unknown": 0,
    }
    try:
        supabase = _get_supabase_client()
        rows: list[dict[str, Any]] = (
            supabase.table("ioc_enrichment")
            .select("ioc_id, source, ioc_type, status, payload")
            .in_("ioc_id", ioc_ids)
            .eq("status", "ok")
            .execute()
        ).data or []
        result: dict[str, dict[str, Any]] = {}
        for row in rows:
            iid: str | None = row.get("ioc_id")
            if not iid:
                continue
            payload: dict[str, Any] = row.get("payload") or {}
            reputation: str = payload.get("reputation", "unknown")
            threat_score = _derive_threat_score(row.get("ioc_type", ""), payload)
            existing = result.get(iid)
            if existing is None or _SEVERITY.get(reputation, 0) > _SEVERITY.get(
                existing["reputation"], 0
            ):
                result[iid] = {
                    "threat_score": threat_score,
                    "reputation": reputation,
                    "source": row.get("source", ""),
                }
        return result
    except Exception:  # noqa: BLE001 - enrichment failures must not block export
        return {}


async def export_session_json(session_id: str) -> dict[str, Any]:
    """Export full session data to JSON format (US-019, US-039).

    Creates a dict containing:
    - Session metadata
    - Full conversation history
    - All extracted IOCs with optional enrichment data

    Args:
        session_id: The session's UUID.

    Returns:
        Dict containing the full session export.
    """
    from datetime import UTC, datetime

    session = await get_session(session_id)
    if not session:
        raise Exception(f"Session {session_id} not found")

    messages = await get_session_messages(session_id)
    iocs = await get_session_iocs(session_id)
    summary = await get_session_summary(session_id)

    # US-039: attach enrichment data to each IOC
    ioc_ids = [ioc["id"] for ioc in iocs if ioc.get("id")]
    enrichment_by_id = _fetch_iocs_enrichment(ioc_ids)

    # Build conversation history
    conversation_history = []
    for i, msg in enumerate(messages):
        metadata = msg.get("metadata", {})
        if metadata.get("type") == "original_email":
            continue
        conversation_history.append(
            {
                "sender": msg.get("role", ""),
                "content": msg.get("content", ""),
                "timestamp": msg.get("created_at", ""),
                "turn_number": i,
            }
        )

    # Get original email
    original_email = None
    for msg in messages:
        if msg.get("metadata", {}).get("type") == "original_email":
            original_email = msg.get("content", "")
            break

    return {
        "phishguard_export_version": "1.0",
        "exported_at": datetime.now(UTC).isoformat(),
        "metadata": {
            "session_id": session_id,
            "created_at": session.get("created_at", ""),
            "ended_at": session.get("ended_at", ""),
            "attack_type": session.get("attack_type", ""),
            "turn_count": summary.get("exchange_count", 0),
            "turn_limit": session.get("turn_limit", 20),
        },
        "persona": session.get("persona"),
        "original_email": original_email,
        "conversation_history": conversation_history,
        "extracted_iocs": [
            {
                **ioc,
                "enrichment": enrichment_by_id.get(ioc.get("id", "")),
            }
            for ioc in iocs
        ],
        "summary_stats": {
            "total_iocs": len(iocs),
            "high_value_iocs": sum(
                1 for ioc in iocs if ioc.get("type") in ("btc", "iban", "btc_wallet")
            ),
            "total_messages": len(conversation_history),
            "bot_messages": sum(
                1 for m in conversation_history if m.get("sender") == "assistant"
            ),
            "scammer_messages": sum(
                1 for m in conversation_history if m.get("sender") == "scammer"
            ),
        },
    }


def _stix_pattern(ioc_type: str, value: str) -> str:
    """Build a STIX pattern for a supported IOC value."""
    escaped = value.replace("\\", "\\\\").replace("'", "\\'")
    if ioc_type == "ip":
        return f"[ipv4-addr:value = '{escaped}']"
    if ioc_type == "url":
        return f"[url:value = '{escaped}']"
    return f"[x-phishguard-ioc:value = '{escaped}']"


async def export_session_stix(session_id: str) -> dict[str, Any]:
    """Export extracted IOCs as a STIX 2.1 bundle.

    The bundle intentionally contains only indicator objects so it can be
    imported by threat intelligence tooling without exposing full conversation
    contents.
    """
    from datetime import UTC, datetime

    session = await get_session(session_id)
    if not session:
        raise Exception(f"Session {session_id} not found")

    iocs = await get_session_iocs(session_id)
    exported_at = (
        datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )
    bundle_id = f"bundle--{uuid5(NAMESPACE_URL, f'phishguard:{session_id}:bundle')}"

    indicators = []
    for ioc in iocs:
        ioc_type = ioc.get("type", "")
        value = ioc.get("value", "")
        if not value:
            continue

        created_at = ioc.get("created_at") or exported_at
        indicator_key = f"phishguard:{session_id}:{ioc_type}:{value}"
        indicator_id = f"indicator--{uuid5(NAMESPACE_URL, indicator_key)}"
        indicators.append(
            {
                "type": "indicator",
                "spec_version": "2.1",
                "id": indicator_id,
                "created": created_at,
                "modified": exported_at,
                "name": f"PhishGuard {ioc_type.upper()} IOC",
                "description": f"IOC extracted from PhishGuard session {session_id}",
                "indicator_types": ["malicious-activity"],
                "pattern": _stix_pattern(ioc_type, value),
                "pattern_type": "stix",
                "valid_from": created_at,
                "confidence": int(round(float(ioc.get("confidence", 1.0)) * 100)),
                "labels": ["phishing", "phishguard", ioc_type],
                "x_phishguard_ioc_type": ioc_type,
            }
        )

    return {
        "type": "bundle",
        "id": bundle_id,
        "objects": indicators,
    }


def export_iocs_csv(
    iocs: list[dict[str, Any]],
    enrichment_by_id: dict[str, dict[str, Any]] | None = None,
) -> str:
    """Export IOCs to CSV format (US-020, US-039).

    Args:
        iocs: List of IOC dicts from get_session_iocs.
        enrichment_by_id: Optional map from ioc_id to enrichment summary
            ``{threat_score, reputation, source}``.  Unenriched IOCs get
            empty strings in those columns.

    Returns:
        CSV string with headers and data.
    """
    import csv
    import io

    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(
        [
            "ioc_type",
            "value",
            "timestamp",
            "confidence",
            "is_high_value",
            "threat_score",
            "reputation",
            "source",
        ]
    )

    enrichment_map: dict[str, dict[str, Any]] = enrichment_by_id or {}

    # Write IOC rows
    for ioc in iocs:
        ioc_type = ioc.get("type", "")
        is_high_value = ioc_type in ("btc", "iban", "btc_wallet")
        enrich = enrichment_map.get(ioc.get("id", "")) or {}
        writer.writerow(
            [
                ioc_type,
                ioc.get("value", ""),
                ioc.get("created_at", ""),
                ioc.get("confidence", 0.0),
                "true" if is_high_value else "false",
                enrich.get("threat_score", ""),
                enrich.get("reputation", ""),
                enrich.get("source", ""),
            ]
        )

    return output.getvalue()


def generate_export_filename(prefix: str, extension: str) -> str:
    """Generate a timestamped filename for export.

    Args:
        prefix: The filename prefix (e.g., "phishguard_session").
        extension: The file extension without dot (e.g., "json").

    Returns:
        Filename with timestamp in format: prefix_YYYYMMDD_HHMMSS.extension
    """
    from datetime import UTC, datetime

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.{extension}"


async def get_user_sessions(
    user_id: str,
    page: int = 1,
    per_page: int = 20,
    attack_type: str | None = None,
    min_risk: int | None = None,
    search: str | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """Retrieve paginated sessions for a user with turn counts and risk scores.

    Fetches sessions ordered by creation time (descending) with pagination,
    enriched with turn counts from the messages table and calculated risk scores.

    Args:
        user_id: The authenticated user's UUID.
        page: Page number (1-indexed). Defaults to 1.
        per_page: Number of sessions per page. Defaults to 20.

    Returns:
        A tuple of (sessions_list, total_count) where sessions_list contains
        dicts with session data, turn_count, and risk_score.

    Raises:
        ValueError: If page or per_page is invalid.
    """
    if page < 1:
        raise ValueError("Page must be >= 1")
    if per_page < 1 or per_page > 100:
        raise ValueError("per_page must be between 1 and 100")
    if min_risk is not None and (min_risk < 1 or min_risk > 10):
        raise ValueError("min_risk must be between 1 and 10")

    supabase = _get_supabase_client()

    # Calculate offset for pagination
    offset = (page - 1) * per_page

    has_filters = bool(attack_type or min_risk is not None or search)

    query = supabase.table("sessions").select("*", count="exact").eq("user_id", user_id)
    if attack_type:
        query = query.eq("attack_type", attack_type)
    if search:
        clean_search = search.strip()
        if clean_search:
            query = query.or_(
                f"title.ilike.%{clean_search}%,attack_type.ilike.%{clean_search}%"
            )

    query = query.order("created_at", desc=True)
    if not has_filters:
        query = query.range(offset, offset + per_page - 1)

    result = query.execute()

    sessions = result.data if result.data else []

    # Enrich sessions with turn counts and risk scores
    enriched_sessions = []
    for session in sessions:
        session_id = session.get("id", "")

        # Get turn count (assistant messages)
        turn_count_result = (
            supabase.table("messages")
            .select("id", count="exact")
            .eq("session_id", session_id)
            .eq("role", "assistant")
            .execute()
        )
        turn_count = turn_count_result.count if turn_count_result.count else 0

        # Get IOCs for risk score calculation
        iocs_result = (
            supabase.table("ioc_extracted")
            .select("type")
            .eq("session_id", session_id)
            .execute()
        )
        iocs = iocs_result.data if iocs_result.data else []

        # Get scammer messages for enhanced risk calculation
        scammer_msg_result = (
            supabase.table("messages")
            .select("content")
            .eq("session_id", session_id)
            .eq("role", "scammer")
            .execute()
        )
        scammer_messages = [
            m.get("content", "") for m in (scammer_msg_result.data or [])
        ]

        # Get persona for personalization detection
        persona = session.get("persona", {})
        victim_name = persona.get("name") if persona else None
        victim_first_name = None
        if victim_name:
            victim_first_name = (
                victim_name.split()[0] if " " in victim_name else victim_name
            )

        # Calculate risk score using enhanced calculator
        attack_type = session.get("attack_type", "unknown")
        risk_score = calculate_risk_score(
            attack_type=attack_type,
            iocs=iocs,
            scammer_messages=scammer_messages,
            victim_name=victim_name,
            victim_first_name=victim_first_name,
        )

        enriched_sessions.append(
            {
                **session,
                "turn_count": turn_count,
                "risk_score": risk_score,
            }
        )

    if min_risk is not None:
        enriched_sessions = [
            session
            for session in enriched_sessions
            if session.get("risk_score", 1) >= min_risk
        ]

    total_count = (
        len(enriched_sessions) if has_filters else (result.count if result.count else 0)
    )
    if has_filters:
        enriched_sessions = enriched_sessions[offset : offset + per_page]

    logger.debug(
        "Retrieved %d sessions for user %s (page %d, total %d)",
        len(enriched_sessions),
        user_id,
        page,
        total_count,
    )

    return enriched_sessions, total_count
