"""Export functionality for PhishGuard sessions.

This module provides functions to export session data to JSON and CSV formats
as defined in US-017 and US-018.
"""

from __future__ import annotations

import csv
import io
import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from phishguard.models.ioc import ExtractedIOC
    from phishguard.models.session import SessionState


def generate_filename(prefix: str, extension: str) -> str:
    """Generate a timestamped filename for export.

    Args:
        prefix: The filename prefix (e.g., "phishguard_session").
        extension: The file extension without dot (e.g., "json").

    Returns:
        Filename with timestamp in format: prefix_YYYYMMDD_HHMMSS.extension

    Example:
        >>> generate_filename("phishguard_session", "json")
        'phishguard_session_20250129_143022.json'
    """
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.{extension}"


def export_session_json(session_state: SessionState) -> str:
    """Export full session data to JSON format.

    Creates a JSON string containing:
    - Session metadata (timestamps, attack type, confidence)
    - Full conversation history
    - All extracted IOCs

    Args:
        session_state: The session state to export.

    Returns:
        JSON string containing the full session export.

    Raises:
        ValueError: If session has not been classified.
    """
    if session_state.classification_result is None:
        raise ValueError("Cannot export: session not classified")

    # Build session metadata
    metadata = {
        "session_id": session_state.faker_seed,  # Use faker seed as session ID
        "created_at": session_state.created_at.isoformat(),
        "ended_at": (
            session_state.ended_at.isoformat() if session_state.ended_at else None
        ),
        "attack_type": session_state.classification_result.attack_type.value,
        "attack_type_display": (
            session_state.classification_result.attack_type.display_name
        ),
        "attack_confidence": session_state.classification_result.confidence,
        "classification_reasoning": session_state.classification_result.reasoning,
        "used_fallback_model": session_state.used_fallback_model,
        "turn_count": session_state.turn_count,
        "turn_limit": session_state.turn_limit,
        "limit_extended_count": session_state.limit_extended_count,
    }

    # Build persona data
    persona_data = None
    if session_state.persona_profile:
        persona = session_state.persona_profile
        persona_data = {
            "name": persona.name,
            "age": persona.age,
            "persona_type": persona.persona_type.value,
            "persona_type_display": persona.persona_type.display_name,
            "background": persona.background,
            "style_description": persona.style_description,
        }

    # Build conversation history
    messages = []
    for msg in session_state.conversation_history:
        messages.append(
            {
                "sender": msg.sender.value,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
                "turn_number": msg.turn_number,
            }
        )

    # Build IOC list
    iocs = []
    for ioc in session_state.extracted_iocs:
        iocs.append(
            {
                "type": ioc.ioc_type.value,
                "type_display": ioc.ioc_type.display_name,
                "value": ioc.value,
                "timestamp": ioc.timestamp.isoformat(),
                "context": ioc.context,
                "message_index": ioc.message_index,
                "is_high_value": ioc.is_high_value,
            }
        )

    # Build summary stats
    summary_stats = {
        "total_iocs": len(session_state.extracted_iocs),
        "high_value_iocs": session_state.high_value_ioc_count,
        "total_messages": len(session_state.conversation_history),
        "bot_messages": sum(
            1 for m in session_state.conversation_history if m.is_bot_message
        ),
        "scammer_messages": sum(
            1 for m in session_state.conversation_history if not m.is_bot_message
        ),
    }

    # Combine all data
    export_data = {
        "phishguard_export_version": "1.0",
        "exported_at": datetime.now(UTC).isoformat(),
        "metadata": metadata,
        "persona": persona_data,
        "original_email": session_state.email_content,
        "conversation_history": messages,
        "extracted_iocs": iocs,
        "summary_stats": summary_stats,
    }

    return json.dumps(export_data, indent=2, ensure_ascii=False)


def export_iocs_csv(iocs: list[ExtractedIOC]) -> str:
    """Export IOCs to CSV format.

    Creates a CSV string with columns:
    - ioc_type: Type of IOC (btc_wallet, iban, phone, url)
    - value: The extracted IOC value
    - timestamp: When the IOC was extracted
    - context: Surrounding text (if available)
    - message_index: Index of message where IOC was found
    - is_high_value: Whether the IOC is high-value (financial)

    Args:
        iocs: List of extracted IOCs to export.

    Returns:
        CSV string containing all IOCs.
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(
        [
            "ioc_type",
            "ioc_type_display",
            "value",
            "timestamp",
            "context",
            "message_index",
            "is_high_value",
        ]
    )

    # Write IOC rows
    for ioc in iocs:
        writer.writerow(
            [
                ioc.ioc_type.value,
                ioc.ioc_type.display_name,
                ioc.value,
                ioc.timestamp.isoformat(),
                ioc.context or "",
                ioc.message_index,
                "true" if ioc.is_high_value else "false",
            ]
        )

    return output.getvalue()


def get_json_filename() -> str:
    """Get the standard JSON export filename.

    Returns:
        Filename in format: phishguard_session_YYYYMMDD_HHMMSS.json
    """
    return generate_filename("phishguard_session", "json")


def get_csv_filename() -> str:
    """Get the standard CSV export filename.

    Returns:
        Filename in format: phishguard_iocs_YYYYMMDD_HHMMSS.csv
    """
    return generate_filename("phishguard_iocs", "csv")
