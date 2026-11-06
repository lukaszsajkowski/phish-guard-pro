"""Conversation loop between one victim and the LLM scammer."""

import time
from datetime import UTC, datetime

from phishguard.agents.conversation import SafetyRegenerationExhaustedError
from phishguard.arena.records import ConversationRecord, TurnRecord
from phishguard.arena.scammer import LLMScammer, ModelRefusalError, ScammerTurn
from phishguard.arena.scenario import Scenario
from phishguard.arena.transcript import Message
from phishguard.arena.victims import Victim, VictimReply
from phishguard.llm import UsageEntry, track_usage
from phishguard.safety import detect_unmasking

_DROPPED = str.maketrans("", "", "-()")


def normalise(text: str) -> str:
    """Lowercase, drop whitespace, '-', '(' and ')', strip trailing punctuation."""
    compact = "".join(text.lower().split()).translate(_DROPPED)
    return compact.rstrip(".,;:!?")


def detect_reveals(scenario: Scenario, message: str) -> list[str]:
    """Ids of secrets whose normalised value appears in the normalised message."""
    haystack = normalise(message)
    return [s.id for s in scenario.secrets if normalise(s.value) in haystack]


class _Stop(Exception):
    """Internal: carries the outcome that ends the loop."""

    def __init__(self, status: str, reason: str | None, end_reason: str) -> None:
        self.status, self.reason, self.end_reason = status, reason, end_reason


async def run_conversation(
    scenario: Scenario,
    victim: Victim,
    scammer: LLMScammer,
    system: str,
    repetition: int,
) -> ConversationRecord:
    """Run one full conversation and return its record (never raises)."""
    started_at = datetime.now(UTC).isoformat()
    t0 = time.monotonic()
    turns: list[TurnRecord] = []
    victim_usage: list[UsageEntry] = []
    scammer_usage: list[UsageEntry] = []
    transcript: list[Message] = []
    status, reason, end_reason = "completed", None, "turn_limit"

    async def victim_call(before: list[Message], text: str | None) -> VictimReply:
        try:
            with track_usage() as log:
                return await victim.reply(before, text)
        except ModelRefusalError:
            raise _Stop("invalid", "victim_refused", "invalid") from None
        finally:
            victim_usage.extend(log.entries)

    async def scammer_call() -> ScammerTurn:
        try:
            with track_usage() as log:
                return await scammer.next_turn(scenario, list(transcript))
        except ModelRefusalError:
            raise _Stop("invalid", "scammer_refused", "invalid") from None
        finally:
            scammer_usage.extend(log.entries)

    try:
        try:
            reply = await victim_call([], None)
            turns.append(
                TurnRecord(
                    index=0,
                    scammer=None,
                    detected_reveals=[],
                    unmasking_detected=False,
                    victim=reply,
                )
            )
            transcript.append(Message(sender="victim", content=reply.content, turn=0))

            for n in range(1, scenario.max_turns + 1):
                move = await scammer_call()
                record = TurnRecord(
                    index=n,
                    scammer=move,
                    detected_reveals=detect_reveals(scenario, move.message),
                    unmasking_detected=detect_unmasking(move.message).is_unmasked,
                    victim=None,
                )
                turns.append(record)
                if move.ends_conversation:
                    end_reason = "scammer_ended"
                    break
                before = list(transcript)
                transcript.append(
                    Message(sender="scammer", content=move.message, turn=n)
                )
                record.victim = await victim_call(before, move.message)
                transcript.append(
                    Message(sender="victim", content=record.victim.content, turn=n)
                )
        except SafetyRegenerationExhaustedError:
            raise _Stop("blocked_by_safety", None, "blocked_by_safety") from None
        except _Stop:
            raise
        except Exception as exc:  # noqa: BLE001 - harness must always return a record
            raise _Stop("error", str(exc), "error") from exc
    except _Stop as stop:
        status, reason, end_reason = stop.status, stop.reason, stop.end_reason

    return ConversationRecord(
        scenario_id=scenario.id,
        scenario_hash=scenario.content_hash,
        system=system,  # type: ignore[arg-type]
        repetition=repetition,
        status=status,  # type: ignore[arg-type]
        status_reason=reason,
        end_reason=end_reason,  # type: ignore[arg-type]
        turns=turns,
        victim_usage=victim_usage,
        scammer_usage=scammer_usage,
        started_at=started_at,
        duration_ms=int((time.monotonic() - t0) * 1000),
    )
