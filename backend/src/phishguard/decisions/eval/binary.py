"""Binary (in-role) eval metrics and reports (US-050).

``breaks_role`` is the positive class. A case is flagged when Basal answered
``positive`` with ``confidence >= threshold``; a case with no Basal answer is
never flagged.

``meta`` keys used by ``write_binary_report``: ``date``, ``basal_model`` and
optional ``extras`` (``{case_id: {column: value}}``, merged into the case's
results.jsonl row; ``basal_error`` is counted).
"""

import json
from collections import Counter
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

from phishguard.decisions.basal_client import BasalAnswer
from phishguard.decisions.eval.metrics import percentile
from phishguard.decisions.eval.report import FIXTURE_LABELS_NOTE

POSITIVE = "breaks_role"
THRESHOLDS: list[float] = [round(0.50 + i * 0.01, 2) for i in range(50)]
MIN_RECALL = 0.9
MAX_FALSE_ALARM = 0.1
NO_THRESHOLD_LINE = "No threshold meets the gate."


@dataclass(frozen=True)
class BinaryCase:
    id: str
    gold: str
    basal: BasalAnswer | None
    lang: str
    synthetic: bool
    ambiguous: bool = False


@dataclass(frozen=True)
class BinaryRow:
    threshold: float
    precision: float
    recall: float | None  # None when there are no positive cases
    false_alarm_rate: float | None  # None when there are no negative cases
    n_flagged: int
    n_positive: int
    n_negative: int


def binary_curve(
    cases: list[BinaryCase], positive: str, thresholds: list[float]
) -> list[BinaryRow]:
    """Precision, recall and false-alarm rate of ``positive`` per threshold."""
    n_pos = sum(1 for c in cases if c.gold == positive)
    n_neg = len(cases) - n_pos
    rows: list[BinaryRow] = []
    for t in thresholds:
        flagged = [
            c
            for c in cases
            if c.basal is not None
            and c.basal.answer == positive
            and c.basal.confidence >= t
        ]
        tp = sum(1 for c in flagged if c.gold == positive)
        fp = len(flagged) - tp
        rows.append(
            BinaryRow(
                threshold=t,
                precision=tp / len(flagged) if flagged else 0.0,
                recall=tp / n_pos if n_pos else None,
                false_alarm_rate=fp / n_neg if n_neg else None,
                n_flagged=len(flagged),
                n_positive=n_pos,
                n_negative=n_neg,
            )
        )
    return rows


def pick_binary_threshold(
    rows: list[BinaryRow],
    min_recall: float = MIN_RECALL,
    max_false_alarm: float = MAX_FALSE_ALARM,
) -> BinaryRow | None:
    """The highest threshold meeting both limits; rows with an n/a rate are skipped."""
    ok = [
        r
        for r in rows
        if r.recall is not None
        and r.false_alarm_rate is not None
        and r.recall >= min_recall
        and r.false_alarm_rate <= max_false_alarm
    ]
    return max(ok, key=lambda r: r.threshold) if ok else None


def _pct(x: float | None) -> str:
    return "n/a" if x is None else f"{x * 100:.1f}%"


def _table(rows: list[BinaryRow]) -> list[str]:
    lines = [
        "| Threshold | Flagged | Precision | Recall | False alarms |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r.threshold:.2f} | {r.n_flagged} | {_pct(r.precision)} "
            f"| {_pct(r.recall)} | {_pct(r.false_alarm_rate)} |"
        )
    return lines


def _result_row(case: BinaryCase, extras: dict) -> dict:
    row = asdict(case)
    basal = row.pop("basal")
    row["basal_answer"] = basal["answer"] if basal else None
    row["basal_confidence"] = basal["confidence"] if basal else None
    row["basal_probabilities"] = basal["probabilities"] if basal else None
    row["basal_ms"] = basal["latency_ms"] if basal else None
    row.update(extras.get(case.id, {}))
    return row


def write_binary_report(cases: list[BinaryCase], out_dir: Path, meta: dict) -> None:
    """Write ``results.jsonl`` and ``report.md`` for a fixtures run."""
    out_dir.mkdir(parents=True, exist_ok=True)
    extras: dict = meta.get("extras") or {}
    (out_dir / "results.jsonl").write_text(
        "".join(
            json.dumps(_result_row(c, extras), ensure_ascii=False) + "\n" for c in cases
        ),
        encoding="utf-8",
    )

    scored = [c for c in cases if not c.ambiguous]
    n_ambiguous = len(cases) - len(scored)
    n_real = sum(1 for c in scored if not c.synthetic)
    n_synth = len(scored) - n_real
    n_errors = sum(1 for e in extras.values() if "basal_error" in e)

    scopes: list[tuple[str, Callable[[BinaryCase], bool]]] = [
        ("All", lambda c: True),
        ("Real only", lambda c: not c.synthetic),
        ("Synthetic only", lambda c: c.synthetic),
        ("PL", lambda c: c.lang == "pl"),
        ("EN", lambda c: c.lang == "en"),
    ]
    curves = {
        name: binary_curve([c for c in scored if f(c)], POSITIVE, THRESHOLDS)
        for name, f in scopes
    }
    picked = pick_binary_threshold(curves["All"])

    lines = [
        "# In-role eval (Basal, response.in_role)",
        "",
        f"- Date: {meta.get('date', 'n/a')}",
        f"- Basal model: {meta.get('basal_model', 'n/a')}",
        f"- Cases scored: {len(scored)} ({n_real} real, {n_synth} synthetic); "
        f"ambiguous excluded: {n_ambiguous}",
        f"- Basal errors (case counted as not flagged): {n_errors}",
        f"- Positive class: `{POSITIVE}`. Flagged = Basal answers `{POSITIVE}` "
        "with confidence >= threshold.",
        "",
        "## Gate (recall >= 90% on breaks_role, false alarms <= 10%)",
        "",
    ]
    if picked is None:
        lines.append(NO_THRESHOLD_LINE)
    else:
        lines.append(
            f"Picked threshold: **{picked.threshold:.2f}** "
            f"(recall {_pct(picked.recall)}, false alarms "
            f"{_pct(picked.false_alarm_rate)}, precision {_pct(picked.precision)}; "
            "all scored cases)."
        )
    lines += [
        "",
        "Recall is n/a where a scope has no `breaks_role` cases (real replies are "
        "all in role); read the false-alarm rate on real replies in the "
        "real-only table.",
        "",
    ]
    for name, _ in scopes:
        rows = curves[name]
        lines += [
            f"## {name} (n={rows[0].n_positive + rows[0].n_negative}; "
            f"breaks_role={rows[0].n_positive}, in_role={rows[0].n_negative})",
            "",
            *_table(rows),
            "",
        ]

    latencies = [c.basal.latency_ms for c in cases if c.basal is not None]
    lines += ["## Basal latency (information)", ""]
    if latencies:
        lines.append(
            f"p50 {percentile(latencies, 50):.0f} ms, "
            f"p95 {percentile(latencies, 95):.0f} ms ({len(latencies)} answers)"
        )
    else:
        lines.append("No Basal answers.")
    lines += ["", f"- {FIXTURE_LABELS_NOTE}", ""]
    (out_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def write_decisions_report(rows: list[dict], out_dir: Path, meta: dict) -> None:
    """Write the report for real ``response.in_role`` decisions (manual review).

    Each row is a ``decisions`` row plus ``content`` (the reply text, fetched by
    ``message_id``; may be None if the message is gone).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "results.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False, default=str) + "\n" for r in rows),
        encoding="utf-8",
    )
    answers = Counter(r.get("basal_answer") or "none" for r in rows)
    skips = Counter(r.get("skip_reason") or "none" for r in rows)
    lines = [
        "# In-role decisions (Basal, response.in_role)",
        "",
        f"- Date: {meta.get('date', 'n/a')}",
        f"- Decisions: {len(rows)}",
        "",
        "## Count per basal_answer",
        "",
        *[f"- {k}: {v}" for k, v in sorted(answers.items())],
        "",
        "## Count per skip_reason",
        "",
        *[f"- {k}: {v}" for k, v in sorted(skips.items())],
        "",
        "## breaks_role rows for manual review",
        "",
    ]
    flagged = [r for r in rows if r.get("basal_answer") == POSITIVE]
    if not flagged:
        lines.append("None.")
    for r in flagged:
        conf = r.get("basal_confidence")
        lines += [
            f"### {r.get('message_id')}",
            "",
            f"- Confidence: {conf if conf is None else f'{float(conf):.2f}'}; "
            f"threshold: {r.get('threshold')}; mode: {r.get('mode')}",
            "",
            "> "
            + (r.get("content") or "(reply text unavailable)").replace("\n", "\n> "),
            "",
        ]
    (out_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")
