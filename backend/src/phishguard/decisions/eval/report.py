"""Writes the profiler eval output: results.jsonl, report.md, coverage_vs_error.png.

``meta`` keys used: ``date``, ``basal_model``, ``llm_model``, ``sources``,
optional ``notes`` (list of str) and ``extras`` (``{case_id: {column: value}}``,
merged into the case's results.jsonl row; ``extras[id]["llm_model"]`` sets the
model a case is priced at, ``basal_error`` / ``llm_error`` are counted).
"""

import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Literal

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from phishguard.decisions.eval.metrics import (  # noqa: E402
    EvalCase,
    ThresholdRow,
    confidence_buckets,
    confusion_matrix,
    llm_cost_usd,
    percentile,
    pick_threshold,
    threshold_curve,
)

THRESHOLDS: list[float] = [round(0.50 + i * 0.01, 2) for i in range(50)]
MAX_ERROR = 0.02
GATE1_WARNING = "**⚠ Fixture labels not reviewed — this result does not pass gate 1.**"
FIXTURE_LABELS_NOTE = (
    "Fixture labels: agreement of two blind Claude reviewers, not expert review."
)

_BLUE = "#2a78d6"
_ORANGE = "#eb6834"
_MUTED = "#6b6a63"


def _pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def _scopes(cases: list[EvalCase]) -> list[tuple[str, list[EvalCase]]]:
    sources = list(dict.fromkeys(c.source for c in cases))
    scopes = [(s, [c for c in cases if c.source == s]) for s in sources]
    if len(sources) > 1:
        scopes.append(("combined", cases))
    return scopes


def _result_row(case: EvalCase, extras: dict) -> dict:
    row = asdict(case)
    basal = row.pop("basal")
    row["basal_answer"] = basal["answer"] if basal else None
    row["basal_confidence"] = basal["confidence"] if basal else None
    row["basal_probabilities"] = basal["probabilities"] if basal else None
    row["basal_ms"] = basal["latency_ms"] if basal else None
    row.update(extras.get(case.id, {}))
    return row


def _threshold_table(rows: list[ThresholdRow]) -> list[str]:
    lines = [
        "| Threshold | Covered | Coverage | Basal error | Cascade agreement |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r.threshold:.2f} | {r.n_basal}/{r.n_total} | {_pct(r.coverage)} "
            f"| {_pct(r.basal_error)} | {_pct(r.cascade_agreement)} |"
        )
    return lines


def _confusion_section(
    scope: str, cases: list[EvalCase], use: Literal["basal", "llm"]
) -> list[str]:
    matrix = confusion_matrix(cases, use)
    answered = sum(sum(row.values()) for row in matrix.values())
    side = "Basal" if use == "basal" else "LLM"
    lines = [
        f"### {scope}: {side} vs reference",
        "",
        f"Rows = reference, columns = {side} answer. "
        f"Cases: {answered} counted, skipped (no answer): {len(cases) - answered}.",
        "",
    ]
    if not matrix:
        return [*lines, "No answers.", ""]
    predicted = sorted({p for row in matrix.values() for p in row})
    lines.append("| reference \\ predicted | " + " | ".join(predicted) + " |")
    lines.append("|---" * (len(predicted) + 1) + "|")
    for ref in sorted(matrix):
        cells = [str(matrix[ref].get(p, 0)) for p in predicted]
        lines.append(f"| {ref} | " + " | ".join(cells) + " |")
    return [*lines, ""]


def _latency_row(name: str, values: list[int]) -> str:
    if not values:
        return f"| {name} | n/a | n/a | 0 |"
    return (
        f"| {name} | {percentile(values, 50):.0f} | {percentile(values, 95):.0f} "
        f"| {len(values)} |"
    )


def _cost_lines(cases: list[EvalCase], meta: dict, extras: dict) -> list[str]:
    total = 0.0
    priced = 0
    models: Counter[str] = Counter()
    unknown: set[str] = set()
    for c in cases:
        if c.llm_prompt_tokens == 0 and c.llm_completion_tokens == 0:
            continue
        model = extras.get(c.id, {}).get("llm_model") or meta.get("llm_model", "")
        try:
            total += llm_cost_usd(c.llm_prompt_tokens, c.llm_completion_tokens, model)
        except KeyError:
            unknown.add(model)
            continue
        priced += 1
        models[model] += 1
    if priced == 0:
        lines = ["- Cost per 1000 classifications: n/a (no priced LLM calls)"]
    else:
        per_model = ", ".join(f"{m}: {n}" for m, n in sorted(models.items()))
        lines = [
            f"- Cost per 1000 classifications: ${total / priced * 1000:.2f} "
            f"(from {priced} cases; models: {per_model})",
            "- Includes parse retries. Prices from `PRICES_PER_MTOK`; verify "
            "against current OpenAI list prices.",
        ]
    if unknown:
        lines.append(f"- Not priced (unknown model): {', '.join(sorted(unknown))}")
    return lines


def _plot(rows: list[ThresholdRow], picked: ThresholdRow | None, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=150)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.spines["left"].set_color(_MUTED)
    ax.spines["bottom"].set_color(_MUTED)
    ax.tick_params(colors=_MUTED)
    ax.grid(axis="y", color="#e4e3dd", linewidth=0.8)
    ax.set_axisbelow(True)
    if rows and rows[0].n_total:
        xs = [r.threshold for r in rows]
        cov = [r.coverage * 100 for r in rows]
        err = [r.basal_error * 100 for r in rows]
        ax.plot(xs, cov, color=_BLUE, linewidth=2, label="Coverage")
        ax.plot(xs, err, color=_ORANGE, linewidth=2, label="Basal error")
        ax.axhline(MAX_ERROR * 100, color=_MUTED, linewidth=1, linestyle="--")
        if picked is not None:
            ax.axvline(picked.threshold, color=_MUTED, linewidth=1, linestyle=":")
            ax.text(
                picked.threshold,
                102,
                f" picked {picked.threshold:.2f}",
                color=_MUTED,
                ha="left",
                fontsize=8,
            )
        ax.legend(loc="center left", frameon=False)
    else:
        ax.text(0.5, 0.5, "No gate cases", ha="center", transform=ax.transAxes)
    ax.set_xlim(0.50, 1.0)
    ax.set_ylim(0, 105)
    ax.set_xlabel("Basal confidence threshold")
    ax.set_ylabel("% of cases")
    ax.set_title("Profiler: Basal coverage vs error (gate cases)", loc="left")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def write_report(
    cases: list[EvalCase],
    out_dir: Path,
    meta: dict,
    *,
    unscored: list[EvalCase] | None = None,
) -> None:
    """Write results.jsonl, report.md and coverage_vs_error.png into ``out_dir``.

    ``unscored`` cases (no reference, e.g. a Supabase case whose LLM call failed)
    are written to results.jsonl with ``scored: false`` and counted in the meta
    block, but are left out of every metric.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    extras: dict = meta.get("extras", {})
    unscored = unscored or []

    with (out_dir / "results.jsonl").open("w", encoding="utf-8") as f:
        for c, scored in [(c, True) for c in cases] + [(c, False) for c in unscored]:
            row = {**_result_row(c, extras), "scored": scored}
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    gate = [c for c in cases if not c.ambiguous]
    ambiguous = [c for c in cases if c.ambiguous]
    scopes = _scopes(gate)
    curves = {name: threshold_curve(sc, THRESHOLDS) for name, sc in scopes}
    combined_rows = curves[scopes[-1][0]] if scopes else []
    combined_pick = pick_threshold(combined_rows, MAX_ERROR)

    lines: list[str] = []
    if any(c.source == "fixtures" and not c.reviewed for c in gate):
        lines += [GATE1_WARNING, ""]

    per_source = Counter(c.source for c in cases)
    amb_per_source = Counter(c.source for c in ambiguous)
    basal_errors = sum(1 for e in extras.values() if e.get("basal_error"))
    llm_errors = sum(1 for e in extras.values() if e.get("llm_error"))
    lines += [
        "# Profiler eval: Basal vs LLM",
        "",
        "## Meta",
        "",
        f"- Date: {meta.get('date', 'n/a')}",
        f"- Basal model: {meta.get('basal_model') or 'n/a'}",
        f"- LLM model: {meta.get('llm_model') or 'n/a'}",
        f"- Sources: {', '.join(meta.get('sources', [])) or 'n/a'}",
        "- Cases per source: "
        + (
            ", ".join(
                f"{s}={n} (ambiguous: {amb_per_source[s]})"
                for s, n in per_source.items()
            )
            or "none"
        ),
        f"- Errors: Basal {basal_errors}, LLM {llm_errors}",
    ]
    if unscored:
        lines.append(
            f"- Unscored (no LLM answer, so no reference): {len(unscored)}; "
            "rows in results.jsonl with `scored: false`"
        )
    if "fixtures" in meta.get("sources", []) or "fixtures" in per_source:
        lines.append(f"- {FIXTURE_LABELS_NOTE}")
    lines += [f"- Note: {n}" for n in meta.get("notes", [])]
    lines += [
        "",
        f"Gate metrics exclude ambiguous cases. Basal decides when confidence >= "
        f"threshold. Picked threshold = lowest with Basal error <= "
        f"{_pct(MAX_ERROR)} and at least one covered case.",
        "",
        "## Picked threshold",
        "",
        "| Scope | Threshold | Covered | Coverage | Basal error | Cascade agreement |",
        "|---|---|---|---|---|---|",
    ]
    for name, _ in scopes:
        p = pick_threshold(curves[name], MAX_ERROR)
        if p is None:
            lines.append(f"| {name} | none | n/a | n/a | n/a | n/a |")
        else:
            lines.append(
                f"| {name} | {p.threshold:.2f} | {p.n_basal}/{p.n_total} "
                f"| {_pct(p.coverage)} | {_pct(p.basal_error)} "
                f"| {_pct(p.cascade_agreement)} |"
            )
    lines.append("")

    for name, _ in scopes:
        lines += [f"## Threshold table: {name}", "", *_threshold_table(curves[name])]
        lines.append("")

    lines += ["## Confusion matrices", ""]
    for name, sc in scopes:
        lines += _confusion_section(name, sc, "basal")
        lines += _confusion_section(name, sc, "llm")

    basal_ms = [c.basal.latency_ms for c in cases if c.basal is not None]
    llm_ms = [c.llm_ms for c in cases if c.llm_ms is not None]
    lines += [
        "## Latency (all cases, ms)",
        "",
        "| Side | p50 | p95 | n |",
        "|---|---|---|---|",
        _latency_row("Basal", basal_ms),
        _latency_row("LLM", llm_ms),
        "",
        "## LLM cost",
        "",
        *_cost_lines(cases, meta, extras),
        "",
        "## Basal confidence buckets (all cases)",
        "",
        "| Bucket | Cases |",
        "|---|---|",
    ]
    lines += [f"| {b} | {n} |" for b, n in confidence_buckets(cases).items()]
    lines += ["", "## Ambiguous cases (excluded from gate metrics)", ""]
    if ambiguous:
        lines += [
            "| Id | Source | Reference | Basal | Basal p | LLM |",
            "|---|---|---|---|---|---|",
        ]
        for c in ambiguous:
            b = c.basal
            lines.append(
                f"| {c.id} | {c.source} | {c.reference} "
                f"| {b.answer if b else 'n/a'} "
                f"| {f'{b.confidence:.2f}' if b else 'n/a'} "
                f"| {c.llm_answer or 'n/a'} |"
            )
    else:
        lines.append("None.")
    lines.append("")

    (out_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")
    _plot(combined_rows, combined_pick, out_dir / "coverage_vs_error.png")
