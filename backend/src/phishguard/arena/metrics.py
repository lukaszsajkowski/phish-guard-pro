"""Arena metrics: per-conversation metrics and run-level aggregates.

Pure module: reads result files from disk, no LLM, no network. Definitions follow
the "Metrics" section of the Scammer Arena design spec.
"""

from collections import defaultdict
from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel

from phishguard.arena.conversation import normalise
from phishguard.arena.records import ConversationRecord
from phishguard.arena.runner import RunMeta
from phishguard.arena.scenario import Scenario
from phishguard.arena.setup import ScenarioSetup
from phishguard.decisions.eval.metrics import llm_cost_usd
from phishguard.llm import UsageEntry

# Statuses whose conversations enter the metrics.
METRIC_STATUSES = ("completed", "blocked_by_safety")

# Metrics shown per system (headline four + engagement, plus secondary signals).
HEADLINE_METRICS = (
    "secrets_revealed_share",
    "turns_to_first_secret",
    "suspected_bot",
    "victim_cost_usd",
    "engagement_turns",
    "unmasking_detected",
    "victim_latency_ms",
)


class ConversationMetrics(BaseModel):
    """Metrics of one conversation (turn 0 is the victim's first reply)."""

    secrets_revealed_share: float
    turns_to_first_secret: int | None
    suspected_bot: bool
    unmasking_detected: bool
    engagement_turns: int
    victim_cost_usd: float
    setup_cost_usd: float
    victim_latency_ms: int
    scammer_claimed_reveals: int
    ioc_true_positives: int
    ioc_false_positives: int
    ioc_revealed: int
    ioc_extracted: int
    safety_regenerations: int
    safety_turns: int
    unsafe_replies_sent: int


def usage_cost_usd(entries: list[UsageEntry]) -> float:
    """Total cost of usage entries, priced per entry model."""
    return sum(
        llm_cost_usd(e.prompt_tokens, e.completion_tokens, e.model) for e in entries
    )


def conversation_metrics(
    record: ConversationRecord, scenario: Scenario, setup_cost_share: float
) -> ConversationMetrics:
    """Compute metrics for one record. The baseline never carries setup cost."""
    secret_values = {s.id: normalise(s.value) for s in scenario.secrets}
    known = {normalise(v) for v in scenario.known_iocs}

    revealed: set[str] = set()
    first_secret: int | None = None
    engagement = 0
    suspected = unmasking = False
    claimed = 0
    extracted: set[str] = set()
    regenerations = safety_turns = unsafe = 0

    for t in record.turns:
        if t.detected_reveals and first_secret is None:
            first_secret = t.index
        revealed.update(i for i in t.detected_reveals if i in secret_values)
        unmasking = unmasking or t.unmasking_detected
        if t.scammer is not None:
            engagement = max(engagement, t.index)
            suspected = suspected or t.scammer.suspects_bot
            claimed += len(t.scammer.revealed_secret_ids)
        if t.victim is not None:
            extracted.update(
                normalise(str(i.get("value", ""))) for i in t.victim.extracted_iocs
            )
            regenerations += t.victim.regenerations
            safety_turns += 1 if t.victim.regenerations > 0 else 0
            unsafe += 0 if t.victim.is_safe else 1
    extracted.discard("")

    revealed_values = {secret_values[i] for i in revealed}
    all_secret_values = set(secret_values.values())
    true_pos = len(extracted & revealed_values)
    false_pos = len(extracted - all_secret_values - known)

    share = (
        record.system == "phishguard" and setup_cost_share or 0.0
    )  # baseline never gets setup cost
    return ConversationMetrics(
        secrets_revealed_share=len(revealed) / len(scenario.secrets),
        turns_to_first_secret=first_secret,
        suspected_bot=suspected,
        unmasking_detected=unmasking,
        engagement_turns=engagement,
        victim_cost_usd=usage_cost_usd(record.victim_usage) + share,
        setup_cost_usd=share,
        victim_latency_ms=sum(e.latency_ms for e in record.victim_usage),
        scammer_claimed_reveals=claimed,
        ioc_true_positives=true_pos,
        ioc_false_positives=false_pos,
        ioc_revealed=len(revealed),
        ioc_extracted=len(extracted),
        safety_regenerations=regenerations,
        safety_turns=safety_turns,
        unsafe_replies_sent=unsafe,
    )


class Aggregate(BaseModel):
    """Mean and min-max over per-repetition values; None values are excluded."""

    mean: float | None
    min: float | None
    max: float | None
    n_valid: int
    n_excluded: int


def aggregate(per_repetition_values: list[float | None]) -> Aggregate:
    valid = [v for v in per_repetition_values if v is not None]
    return Aggregate(
        mean=sum(valid) / len(valid) if valid else None,
        min=min(valid) if valid else None,
        max=max(valid) if valid else None,
        n_valid=len(valid),
        n_excluded=len(per_repetition_values) - len(valid),
    )


def within_noise(a: Aggregate, b: Aggregate) -> bool:
    """True when the [min, max] ranges overlap (False if either is empty)."""
    if None in (a.min, a.max, b.min, b.max):
        return False
    return a.min <= b.max and b.min <= a.max  # type: ignore[operator]


# --- summary ---------------------------------------------------------------


class ConversationCounts(BaseModel):
    expected: int = 0
    completed: int = 0
    blocked_by_safety: int = 0
    invalid: int = 0
    error: int = 0
    missing: int = 0


class ScenarioSystemRow(BaseModel):
    """Mean over the valid repetitions of one scenario and system."""

    n: int
    secrets_revealed_share: float | None = None
    turns_to_first_secret: float | None = None
    suspected_bot: float | None = None
    engagement_turns: float | None = None
    victim_cost_usd: float | None = None


class ScenarioRow(BaseModel):
    scenario_id: str
    language: str
    attack_type: str
    difficulty: str
    systems: dict[str, ScenarioSystemRow]


class IocSummary(BaseModel):
    """PhishGuard IOC extraction, pooled over all valid conversations."""

    revealed: int
    true_positives: int
    false_positives: int
    extracted: int
    recall: float | None
    precision: float | None


class SafetySummary(BaseModel):
    """PhishGuard safety totals over valid conversations."""

    conversations: int
    blocked_conversations: int
    regenerations: int
    turns_with_regeneration: int
    unsafe_replies_sent: int


class CostSplit(BaseModel):
    """PhishGuard cost per conversation, split into setup share and turns."""

    setup: Aggregate
    turns: Aggregate
    total: Aggregate


class ProfilerMismatch(BaseModel):
    scenario_id: str
    expected: str
    got: str | None


class ProfilerAgreement(BaseModel):
    n: int
    agreed: int
    share: float | None
    mismatches: list[ProfilerMismatch]


class Summary(BaseModel):
    meta: RunMeta
    counts: dict[str, ConversationCounts]
    invalid_share: float
    headline: dict[str, dict[str, Aggregate]]
    no_reveal_conversations: dict[str, int]
    per_scenario: list[ScenarioRow]
    by_language: dict[str, dict[str, dict[str, Aggregate]]]
    ioc: IocSummary
    safety: SafetySummary
    cost_split: CostSplit
    profiler_agreement: ProfilerAgreement


def _metric_value(m: ConversationMetrics, name: str) -> float | None:
    value = getattr(m, name)
    return None if value is None else float(value)


def _mean(values: list[float | None]) -> float | None:
    valid = [v for v in values if v is not None]
    return sum(valid) / len(valid) if valid else None


def _load_setups(results_dir: Path, ids: list[str]) -> dict[str, ScenarioSetup]:
    setups = {}
    for sid in ids:
        path = results_dir / "setup" / f"{sid}.json"
        if path.exists():
            setups[sid] = ScenarioSetup.model_validate_json(
                path.read_text(encoding="utf-8")
            )
    return setups


def summarise(results_dir: Path, scenarios: dict[str, Scenario]) -> Summary:
    """Aggregate a results directory (run.json, setup/, conversations/)."""
    meta = RunMeta.model_validate_json(
        (results_dir / "run.json").read_text(encoding="utf-8")
    )
    ids = sorted(meta.scenario_ids)
    setups = _load_setups(results_dir, ids)

    # Load records and count statuses.
    counts = {s: ConversationCounts() for s in meta.systems}
    records: dict[tuple[str, str, int], ConversationRecord] = {}
    for sid in ids:
        for system in meta.systems:
            for rep in range(meta.repetitions):
                counts[system].expected += 1
                path = results_dir / "conversations" / f"{sid}__{system}__r{rep}.json"
                if not path.exists():
                    counts[system].missing += 1
                    continue
                rec = ConversationRecord.model_validate_json(
                    path.read_text(encoding="utf-8")
                )
                records[(sid, system, rep)] = rec
                setattr(
                    counts[system], rec.status, getattr(counts[system], rec.status) + 1
                )

    # Setup cost share (R4): scenario setup cost / PhishGuard records in metrics.
    entering_pg: dict[str, int] = defaultdict(int)
    for (sid, system, _), rec in records.items():
        if system == "phishguard" and rec.status in METRIC_STATUSES:
            entering_pg[sid] += 1
    setup_share = {
        sid: (usage_cost_usd(setups[sid].usage) / n if sid in setups and n else 0.0)
        for sid, n in entering_pg.items()
    }

    metrics: dict[tuple[str, str, int], ConversationMetrics] = {
        key: conversation_metrics(rec, scenarios[key[0]], setup_share.get(key[0], 0.0))
        for key, rec in records.items()
        if rec.status in METRIC_STATUSES
    }

    def per_rep(
        system: str, extract: Callable[[ConversationMetrics], float | None], sids=None
    ) -> Aggregate:
        """Mean over scenarios per repetition, then aggregate over repetitions."""
        sids = ids if sids is None else sids
        values: list[float | None] = []
        for rep in range(meta.repetitions):
            per_scenario = [
                extract(metrics[(sid, system, rep)])
                for sid in sids
                if (sid, system, rep) in metrics
            ]
            values.append(_mean(per_scenario))
        return aggregate(values)

    def block(system: str, sids=None) -> dict[str, Aggregate]:
        return {
            name: per_rep(system, lambda m, n=name: _metric_value(m, n), sids)
            for name in HEADLINE_METRICS
        }

    headline = {s: block(s) for s in meta.systems}
    no_reveal = {
        s: sum(
            1
            for (_, system, _), m in metrics.items()
            if system == s and m.turns_to_first_secret is None
        )
        for s in meta.systems
    }

    by_language = {
        lang: {
            s: block(s, [i for i in ids if scenarios[i].language == lang])
            for s in meta.systems
        }
        for lang in sorted({scenarios[i].language for i in ids})
    }

    per_scenario = []
    for sid in ids:
        sc = scenarios[sid]
        systems = {}
        for system in meta.systems:
            ms = [
                metrics[(sid, system, r)]
                for r in range(meta.repetitions)
                if (sid, system, r) in metrics
            ]
            systems[system] = ScenarioSystemRow(
                n=len(ms),
                **{
                    name: _mean([_metric_value(m, name) for m in ms])
                    for name in (
                        "secrets_revealed_share",
                        "turns_to_first_secret",
                        "suspected_bot",
                        "engagement_turns",
                        "victim_cost_usd",
                    )
                },
            )
        per_scenario.append(
            ScenarioRow(
                scenario_id=sid,
                language=sc.language,
                attack_type=str(getattr(sc.attack_type, "value", sc.attack_type)),
                difficulty=sc.difficulty,
                systems=systems,
            )
        )

    pg = [m for (_, system, _), m in metrics.items() if system == "phishguard"]
    revealed = sum(m.ioc_revealed for m in pg)
    tp = sum(m.ioc_true_positives for m in pg)
    fp = sum(m.ioc_false_positives for m in pg)
    extracted = sum(m.ioc_extracted for m in pg)
    ioc = IocSummary(
        revealed=revealed,
        true_positives=tp,
        false_positives=fp,
        extracted=extracted,
        recall=tp / revealed if revealed else None,
        precision=(extracted - fp) / extracted if extracted else None,
    )
    safety = SafetySummary(
        conversations=len(pg),
        blocked_conversations=sum(
            1
            for (_, system, _), r in records.items()
            if system == "phishguard" and r.status == "blocked_by_safety"
        ),
        regenerations=sum(m.safety_regenerations for m in pg),
        turns_with_regeneration=sum(m.safety_turns for m in pg),
        unsafe_replies_sent=sum(m.unsafe_replies_sent for m in pg),
    )
    cost_split = CostSplit(
        setup=per_rep("phishguard", lambda m: m.setup_cost_usd),
        turns=per_rep("phishguard", lambda m: m.victim_cost_usd - m.setup_cost_usd),
        total=per_rep("phishguard", lambda m: m.victim_cost_usd),
    )

    mismatches = []
    ok_setups = [sid for sid in ids if sid in setups and not setups[sid].error]
    for sid in ok_setups:
        expected = str(
            getattr(scenarios[sid].attack_type, "value", scenarios[sid].attack_type)
        )
        got = setups[sid].classification.get("attack_type")
        if got != expected:
            mismatches.append(
                ProfilerMismatch(scenario_id=sid, expected=expected, got=got)
            )
    profiler = ProfilerAgreement(
        n=len(ok_setups),
        agreed=len(ok_setups) - len(mismatches),
        share=(len(ok_setups) - len(mismatches)) / len(ok_setups)
        if ok_setups
        else None,
        mismatches=mismatches,
    )

    total_expected = sum(c.expected for c in counts.values())
    total_invalid = sum(c.invalid for c in counts.values())
    return Summary(
        meta=meta,
        counts=counts,
        invalid_share=total_invalid / total_expected if total_expected else 0.0,
        headline=headline,
        no_reveal_conversations=no_reveal,
        per_scenario=per_scenario,
        by_language=by_language,
        ioc=ioc,
        safety=safety,
        cost_split=cost_split,
        profiler_agreement=profiler,
    )
