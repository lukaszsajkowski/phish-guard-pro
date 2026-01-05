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

