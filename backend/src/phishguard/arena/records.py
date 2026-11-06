"""Conversation record types written by the Arena harness."""

from typing import Literal

from pydantic import BaseModel

from phishguard.arena.scammer import ScammerTurn
from phishguard.arena.victims import VictimReply
from phishguard.llm import UsageEntry


class TurnRecord(BaseModel):
    """One turn: the scammer move (None at turn 0) and the victim reply."""

    index: int
    scammer: ScammerTurn | None
    detected_reveals: list[str]
    unmasking_detected: bool
    victim: VictimReply | None


class ConversationRecord(BaseModel):
    """Full outcome of one scenario run against one system."""

    scenario_id: str
    scenario_hash: str
    system: Literal["phishguard", "baseline"]
    repetition: int
    status: Literal["completed", "invalid", "error", "blocked_by_safety"]
    status_reason: str | None
    end_reason: Literal[
        "turn_limit", "scammer_ended", "blocked_by_safety", "invalid", "error"
    ]
    turns: list[TurnRecord]
    victim_usage: list[UsageEntry]
    scammer_usage: list[UsageEntry]
    started_at: str
    duration_ms: int
    commit: str | None = None
