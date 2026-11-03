"""Profiler eval CLI (US-053): compare Basal with the LLM on attack-type labels.

Usage:
    python -m phishguard.decisions.eval profiler \
        --source supabase|fixtures|decisions|all --out DIR [--limit N]
    python -m phishguard.decisions.eval in-role-samples \
        --out FILE [--per-type N]   # real replies for the in-role eval set (US-050)

Needs ``BASAL_URL`` (e.g. ``http://127.0.0.1:8011/v1/systemone``) for every
source except ``decisions``, and ``OPENAI_API_KEY`` for the LLM side. A missing
key or a failing call is recorded per case; the run does not stop. Nothing is
written to Supabase (the LLM is called with ``session_id=None``).
"""

import argparse
import asyncio
import json
import sys
import time
from collections import Counter
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path
from typing import Any, Protocol

from phishguard.agents.prompts.profiler_basal import (
    ATTACK_TYPE_CRITERIA,
    PROFILER_BASAL_INSTRUCTIONS,
)
from phishguard.core import get_settings
from phishguard.decisions.basal_client import BasalAnswer, BasalClient
from phishguard.decisions.eval.metrics import EvalCase
from phishguard.decisions.eval.report import write_report
from phishguard.decisions.eval.sources import (
    FIXTURES_PATH,
    load_decision_cases,
    load_fixture_inputs,
    load_supabase_inputs,
)
from phishguard.llm.client import LLMResponse

CONCURRENCY = 4


@dataclass(frozen=True)
class EvalInput:
    id: str
    source: str
    email: str
    reference: str
    reviewed: bool = True
    ambiguous: bool = False
    stored_attack_type: str | None = None


class _Basal(Protocol):
    async def ask_choice(
        self, state: str, instructions: str, criteria: dict[str, str]
    ) -> BasalAnswer: ...


class _Profiler(Protocol):
    async def classify_with_llm(
        self, email_content: str, session_id: str | None = None, *, on_usage: Any
    ) -> Any: ...


def _err(e: BaseException) -> str:
    return f"{type(e).__name__}: {e}"


async def _run_one(
    item: EvalInput,
    basal_client: _Basal,
    profiler: _Profiler | None,
    profiler_error: str | None,
    sem: asyncio.Semaphore,
) -> tuple[EvalCase, dict]:
    extra: dict[str, Any] = {}
    if item.source == "supabase":
        extra["stored_attack_type"] = item.stored_attack_type
    async with sem:
        basal: BasalAnswer | None = None
        try:
            basal = await basal_client.ask_choice(
                item.email, PROFILER_BASAL_INSTRUCTIONS, ATTACK_TYPE_CRITERIA
            )
        except Exception as e:  # recorded per case, never stops the run
            extra["basal_error"] = _err(e)

        llm_answer: str | None = None
        llm_ms: int | None = None
        usages: list[LLMResponse] = []
        if profiler is None:
            extra["llm_error"] = profiler_error or "LLM client unavailable"
        else:
            start = time.perf_counter()
            try:
                result = await profiler.classify_with_llm(
                    item.email, session_id=None, on_usage=usages.append
                )
                llm_answer = result.attack_type.value
                llm_ms = int((time.perf_counter() - start) * 1000)
            except Exception as e:  # recorded per case, never stops the run
                extra["llm_error"] = _err(e)

    if usages:
        # Price the case at the model that answered last (fallback if used).
        extra["llm_model"] = usages[-1].model_used
    case = EvalCase(
        id=item.id,
        source=item.source,
        reference=item.reference,
        basal=basal,
        llm_answer=llm_answer,
        llm_ms=llm_ms,
        llm_prompt_tokens=sum(u.prompt_tokens for u in usages),
        llm_completion_tokens=sum(u.completion_tokens for u in usages),
        reviewed=item.reviewed,
        ambiguous=item.ambiguous,
    )
    return case, extra


async def run_inputs(
    inputs: list[EvalInput],
    basal_client: _Basal,
    profiler: _Profiler | None,
    *,
    profiler_error: str | None = None,
) -> tuple[list[EvalCase], dict[str, dict]]:
    """Ask Basal and the LLM about every input, at most 4 cases at a time."""
    sem = asyncio.Semaphore(CONCURRENCY)
    results = await asyncio.gather(
        *(_run_one(i, basal_client, profiler, profiler_error, sem) for i in inputs)
    )
    cases = [c for c, _ in results]
    extras = {c.id: e for c, e in results if e}
    return cases, extras


def split_supabase_reference(
    cases: list[EvalCase],
) -> tuple[list[EvalCase], list[EvalCase]]:
    """Set each Supabase case's reference to its fresh LLM answer.

    Returns ``(scored, unscored)``. A Supabase case whose LLM call failed has no
    reference: it goes to ``unscored`` (written to results.jsonl, kept out of
    the metrics). Other sources pass through unchanged.
    """
    scored: list[EvalCase] = []
    unscored: list[EvalCase] = []
    for c in cases:
        if c.source != "supabase":
            scored.append(c)
        elif c.llm_answer is None:
            unscored.append(c)
        else:
            scored.append(replace(c, reference=c.llm_answer))
    return scored, unscored


def _build_profiler() -> tuple[_Profiler | None, str | None]:
    from phishguard.agents.profiler import ProfilerAgent

    try:
        return ProfilerAgent(), None
    except Exception as e:
        return None, _err(e)


async def _profiler_eval(args: argparse.Namespace) -> int:
    settings = get_settings()
    sources = ["supabase", "fixtures"] if args.source == "all" else [args.source]
    inputs: list[EvalInput] = []
    notes: list[str] = []

    if "supabase" in sources:
        rows = await load_supabase_inputs(args.limit)
        print(f"Usable Supabase sessions (with original email): {len(rows)}")
        # Reference is filled in after the fresh LLM call (see below).
        inputs += [
            EvalInput(sid, "supabase", email, "", stored_attack_type=stored)
            for sid, email, stored in rows
        ]
    if "fixtures" in sources:
        rows_f = load_fixture_inputs(Path(args.fixtures))
        if args.limit is not None:
            rows_f = rows_f[: args.limit]
        print(f"Fixture cases: {len(rows_f)}")
        inputs += [
            EvalInput(fid, "fixtures", email, gold, reviewed, ambiguous)
            for fid, email, gold, reviewed, ambiguous in rows_f
        ]

    cases: list[EvalCase] = []
    unscored: list[EvalCase] = []
    extras: dict[str, dict] = {}
    if args.source == "decisions":
        cases = load_decision_cases()
        if args.limit is not None:
            cases = cases[: args.limit]
        print(f"Usable shadow decisions (Basal and LLM answered): {len(cases)}")
    elif inputs:
        if not settings.basal_url:
            print("BASAL_URL is not set.", file=sys.stderr)
            return 2
        profiler, profiler_error = _build_profiler()
        if profiler_error:
            print(f"LLM unavailable, recorded per case: {profiler_error}")
            notes.append(f"LLM unavailable for this run: {profiler_error}")
        basal_client = BasalClient(settings.basal_url, settings.basal_timeout_s)
        cases, extras = await run_inputs(
            inputs, basal_client, profiler, profiler_error=profiler_error
        )
        cases, unscored = split_supabase_reference(cases)

    meta = {
        "date": date.today().isoformat(),
        "basal_model": settings.basal_model or "n/a (BASAL_MODEL not set)",
        "llm_model": settings.openai_primary_model,
        "sources": sources,
        "notes": notes,
        "extras": extras,
    }
    out = Path(args.out)
    write_report(cases, out, meta, unscored=unscored)
    n_basal_err = sum(1 for e in extras.values() if "basal_error" in e)
    n_llm_err = sum(1 for e in extras.values() if "llm_error" in e)
    print(
        f"Cases: {len(cases)} scored, {len(unscored)} unscored; "
        f"Basal errors: {n_basal_err}; LLM errors: {n_llm_err}"
    )
    print(f"Wrote {out / 'results.jsonl'}, {out / 'report.md'}, ")
    print(f"      {out / 'coverage_vs_error.png'}")
    return 0


def _pick_in_role_sources(
    fixtures: Path, per_type: int
) -> list[tuple[str, str, str, str]]:
    """Pick ``(id, lang, attack_type, email)``, ``per_type`` per attack type.

    Reviewed, non-ambiguous, not ``not_phishing``; half pl and half en where
    the fixtures allow, topped up from the other language otherwise.
    """
    langs = {
        r["id"]: r["lang"]
        for r in map(json.loads, fixtures.read_text(encoding="utf-8").splitlines())
    }
    pools: dict[str, dict[str, list[tuple[str, str]]]] = {}
    for fid, email, gold, reviewed, ambiguous in load_fixture_inputs(fixtures):
        if gold == "not_phishing" or not reviewed or ambiguous:
            continue
        pools.setdefault(gold, {"pl": [], "en": []})[langs[fid]].append((fid, email))

    picks: list[tuple[str, str, str, str]] = []
    for gold in sorted(pools):
        pl, en = pools[gold]["pl"], pools[gold]["en"]
        n_pl = min(len(pl), per_type // 2)
        n_en = min(len(en), per_type - n_pl)
        n_pl = min(len(pl), per_type - n_en)
        chosen = [(f, "pl", e) for f, e in pl[:n_pl]] + [
            (f, "en", e) for f, e in en[:n_en]
        ]
        picks += [(f, lang, gold, e) for f, lang, e in chosen]
    return picks


async def _in_role_samples(args: argparse.Namespace) -> int:
    """Generate first replies with the real agent as in-role candidates.

    ``gold`` is the placeholder ``in_role`` until the blind label review.
    Nothing is written to Supabase (``session_id=None``).
    """
    from phishguard.agents.conversation import ConversationAgent
    from phishguard.agents.persona_engine import PersonaEngine
    from phishguard.models.classification import AttackType

    picks = _pick_in_role_sources(Path(args.fixtures), args.per_type)
    agent = ConversationAgent()
    engine = PersonaEngine()
    sem = asyncio.Semaphore(CONCURRENCY)

    async def one(fid: str, lang: str, gold: str, email: str) -> dict | None:
        attack = AttackType(gold)
        persona = engine.select_persona(attack)
        async with sem:
            try:
                result = await agent.generate_response(
                    persona=persona,
                    email_content=email,
                    attack_type=attack,
                    is_first_response=True,
                    session_id=None,
                )
            except Exception as e:  # recorded, the run goes on
                print(f"{fid}: {_err(e)}", file=sys.stderr)
                return None
        return {
            "id": f"real-{fid}",
            "lang": lang,
            "gold": "in_role",
            "synthetic": False,
            "persona": {
                "persona_type": persona.persona_type.value,
                "age": persona.age,
                "style_description": persona.style_description,
            },
            "response": result.content,
            "reviewed": False,
            "ambiguous": False,
            "review": None,
            "notes": f"real reply to {gold} email {fid}; gold is a placeholder",
        }

    rows = [r for r in await asyncio.gather(*(one(*p) for p in picks)) if r]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
        encoding="utf-8",
    )
    counts = Counter((p[2], p[1]) for p in picks)
    print(f"Wrote {len(rows)}/{len(picks)} rows to {out}")
    for (gold, lang), n in sorted(counts.items()):
        print(f"  {gold} {lang}: {n}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m phishguard.decisions.eval")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("profiler", help="Basal vs LLM on the Profiler attack type")
    p.add_argument(
        "--source",
        choices=["supabase", "fixtures", "decisions", "all"],
        required=True,
    )
    p.add_argument("--out", required=True, help="Output directory")
    p.add_argument("--limit", type=int, default=None, help="Max cases per source")
    p.add_argument("--fixtures", default=str(FIXTURES_PATH), help=argparse.SUPPRESS)
    r = sub.add_parser(
        "in-role-samples", help="Generate real replies for the in-role eval set"
    )
    r.add_argument("--out", required=True, help="Output JSONL file")
    r.add_argument("--per-type", type=int, default=8, help="Replies per attack type")
    r.add_argument("--fixtures", default=str(FIXTURES_PATH), help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.command == "in-role-samples":
        return asyncio.run(_in_role_samples(args))
    return asyncio.run(_profiler_eval(args))


if __name__ == "__main__":
    raise SystemExit(main())
