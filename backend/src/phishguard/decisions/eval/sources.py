"""Input sources for the profiler eval (US-053).

All Supabase access here is read-only.
"""

import asyncio
import json
from pathlib import Path

from phishguard.decisions.basal_client import BasalAnswer
from phishguard.decisions.eval.metrics import EvalCase
from phishguard.services.session_service import (
    _get_supabase_client,
    get_original_email,
)

PROFILER_NODE = "profiler.attack_type"

# backend/tests/fixtures/eval/profiler_emails.jsonl
FIXTURES_PATH = (
    Path(__file__).resolve().parents[4]
    / "tests"
    / "fixtures"
    / "eval"
    / "profiler_emails.jsonl"
)


def load_fixture_inputs(path: Path) -> list[tuple[str, str, str, bool, bool]]:
    """Read fixture rows as ``(id, email, gold, reviewed, ambiguous)``."""
    inputs: list[tuple[str, str, str, bool, bool]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        inputs.append(
            (
                row["id"],
                row["email"],
                row["gold"],
                bool(row.get("reviewed", False)),
                bool(row.get("ambiguous", False)),
            )
        )
    return inputs


def _list_sessions(limit: int | None) -> list[dict]:
    client = _get_supabase_client()
    query = (
        client.table("sessions")
        .select("id, attack_type")
        .order("created_at", desc=True)
    )
    if limit is not None:
        query = query.limit(limit)
    return query.execute().data or []


async def load_supabase_inputs(
    limit: int | None,
) -> list[tuple[str, str, str | None]]:
    """Sessions with an original email as ``(session_id, email, attack_type)``.

    ``limit`` caps the number of sessions read (newest first). Sessions with no
    original email are dropped.
    """
    sessions = await asyncio.to_thread(_list_sessions, limit)
    inputs: list[tuple[str, str, str | None]] = []
    for s in sessions:
        email = await get_original_email(s["id"])
        if email and email.strip():
            inputs.append((s["id"], email, s.get("attack_type")))
    return inputs


def load_decision_cases() -> list[EvalCase]:
    """Shadow-mode profiler decisions where both Basal and the LLM answered.

    The LLM answer is the reference. Rows with a null or empty ``llm_answer``
    (LLM failures) or a null ``basal_answer`` are skipped. No model is called.
    """
    client = _get_supabase_client()
    rows = (
        client.table("decisions")
        .select("*")
        .eq("node", PROFILER_NODE)
        .eq("mode", "shadow")
        .order("created_at")
        .execute()
        .data
        or []
    )
    cases: list[EvalCase] = []
    for r in rows:
        if not r.get("basal_answer") or not r.get("llm_answer"):
            continue
        confidence = r.get("basal_confidence")
        if confidence is None:
            continue
        basal = BasalAnswer(
            answer=r["basal_answer"],
            probabilities={
                k: float(v) for k, v in (r.get("basal_probabilities") or {}).items()
            },
            confidence=float(confidence),
            latency_ms=int(r.get("basal_ms") or 0),
        )
        cases.append(
            EvalCase(
                id=str(r["id"]),
                source="decisions",
                reference=r["llm_answer"],
                basal=basal,
                llm_answer=r["llm_answer"],
                llm_ms=r.get("llm_ms"),
                llm_prompt_tokens=0,
                llm_completion_tokens=0,
            )
        )
    return cases
