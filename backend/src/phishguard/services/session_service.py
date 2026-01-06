"""Session service for persisting analysis sessions to Supabase.

This module provides functions to create and manage phishing analysis
sessions and their associated messages in the database.
"""

import logging
from typing import Any
from uuid import UUID

from supabase import create_client, Client

from phishguard.core import get_settings
from phishguard.models.classification import AttackType, ClassificationResult

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

    result = supabase.table("sessions").update(update_data).eq("id", session_id).execute()

    if not result.data or len(result.data) == 0:
        raise Exception("Failed to update session")

    logger.info(
        "Updated session %s with attack_type=%s",
        session_id,
        classification_result.attack_type.value,
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

        history.append({
            "sender": sender,
            "content": msg.get("content", ""),
        })

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

        ioc_records.append({
            "session_id": session_id,
            "type": ioc_type,
            "value": ioc.get("value", ""),
            "confidence": 1.0 if ioc.get("is_high_value", False) else 0.8,
        })

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
) -> int:
    """Calculate risk score (1-10) based on attack type and IOCs.

    Risk score formula:
    - Base score from attack type severity (1-4)
    - +1 for each IOC extracted (up to +3)
    - +1 for each high-value IOC (BTC, IBAN) (up to +3)

    Args:
        attack_type: The classified attack type.
        iocs: List of extracted IOCs.

    Returns:
        Risk score from 1 to 10.
    """
    # Attack type severity mapping
    attack_severity = {
        "nigerian_419": 3,
        "ceo_fraud": 4,
        "fake_invoice": 3,
        "romance_scam": 3,
        "tech_support": 2,
        "lottery_prize": 2,
        "crypto_investment": 4,
        "delivery_scam": 2,
        "not_phishing": 1,
    }

    # Base score from attack type
    base_score = attack_severity.get(attack_type, 2)

    # Score from IOC count (up to +3)
    ioc_count_score = min(len(iocs), 3)

    # Score from high-value IOCs (up to +3)
    high_value_types = {"btc", "btc_wallet", "iban"}
    high_value_count = sum(
        1 for ioc in iocs if ioc.get("type", "") in high_value_types
    )
    high_value_score = min(high_value_count, 3)

    # Total score capped at 10
    total_score = min(base_score + ioc_count_score + high_value_score, 10)

    return max(total_score, 1)  # Ensure minimum of 1


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

        timeline_events.append({
            "timestamp": ioc.get("created_at", ""),
            "event_type": "ioc_extracted",
            "description": f"Extracted {ioc_type.upper()}: {ioc.get('value', '')[:20]}...",
            "ioc_id": ioc.get("id"),
            "is_high_value": is_high_value,
        })

    return timeline_events
