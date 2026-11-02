"""Persistence of Basal decisions and LLM usage.

Writes never raise: a failed write logs a warning and the caller continues.
Decision rows never contain email text.
"""

import logging
from dataclasses import asdict, dataclass

from phishguard.services.session_service import _get_supabase_client

logger = logging.getLogger(__name__)


@dataclass
class DecisionRecord:
    """One routed closed-question decision."""

    session_id: str
    node: str
    mode: str
    options: list[str]
    threshold: float
    final_answer: str
    source: str
    basal_answer: str | None = None
    basal_probabilities: dict[str, float] | None = None
    basal_confidence: float | None = None
    basal_ms: int | None = None
    basal_model: str | None = None
    skip_reason: str | None = None
    llm_answer: str | None = None
    llm_model: str | None = None
    llm_ms: int | None = None


async def record_decision(record: DecisionRecord) -> None:
    """Insert a row into `decisions`; swallow any error."""
    try:
        client = _get_supabase_client()
        client.table("decisions").insert(asdict(record)).execute()
    except Exception as exc:
        logger.warning("Failed to record decision: %s", exc)


async def record_llm_usage(
    session_id: str | None,
    agent: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    latency_ms: int,
) -> None:
    """Insert a row into `llm_usage`; swallow any error."""
    try:
        client = _get_supabase_client()
        client.table("llm_usage").insert(
            {
                "session_id": session_id,
                "agent": agent,
                "model": model,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "latency_ms": latency_ms,
            }
        ).execute()
    except Exception as exc:
        logger.warning("Failed to record LLM usage: %s", exc)
