"""Pure metrics for comparing Basal with an LLM across confidence thresholds.

Ambiguous cases are NOT filtered here; callers pass the list they want scored.
"""

from dataclasses import dataclass
from typing import Literal

from phishguard.decisions.basal_client import BasalAnswer

# USD per 1M tokens as (input, output). OpenAI entries are last known list
# prices (2026-11-02) and MUST be checked against https://openai.com/api/pricing
# before the numbers are relied upon. Local Ollama models cost nothing.
# gpt-6-luna and gpt-5.4-mini prices provided by the project owner (2026-11-06).
# Not yet priced: claude-sonnet-5-5, claude-haiku-5-5. Cost reports
# for those models raise "Unknown model" until they are added here.
PRICES_PER_MTOK: dict[str, tuple[float, float]] = {
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-6-luna": (0.10, 0.50),
    "gpt-5.4-mini": (0.75, 4.50),
    "qwen3:8b": (0.0, 0.0),
    "qwen3:4b": (0.0, 0.0),
}


@dataclass(frozen=True)
class EvalCase:
    id: str
    source: str
    reference: str
    basal: BasalAnswer | None
    llm_answer: str | None
    llm_ms: int | None
    llm_prompt_tokens: int
    llm_completion_tokens: int
    reviewed: bool = True
    ambiguous: bool = False


@dataclass(frozen=True)
class ThresholdRow:
    threshold: float
    coverage: float
    basal_error: float
    cascade_agreement: float
    n_basal: int
    n_total: int


def _covered(case: EvalCase, t: float) -> bool:
    return case.basal is not None and case.basal.confidence >= t


def threshold_curve(
    cases: list[EvalCase], thresholds: list[float]
) -> list[ThresholdRow]:
    """Score Basal and the Basal-then-LLM cascade at each threshold.

    A case is covered when ``basal.confidence >= t`` (inclusive). Uncovered
    cases fall back to ``llm_answer``; if the LLM failed (``None``) the case
    counts as a disagreement in ``cascade_agreement``.
    """
    n_total = len(cases)
    rows: list[ThresholdRow] = []
    for t in thresholds:
        covered = [c for c in cases if _covered(c, t)]
        n_basal = len(covered)
        wrong = sum(1 for c in covered if c.basal and c.basal.answer != c.reference)
        agree = sum(
            1
            for c in cases
            if (c.basal.answer if _covered(c, t) and c.basal else c.llm_answer)
            == c.reference
        )
        rows.append(
            ThresholdRow(
                threshold=t,
                coverage=n_basal / n_total if n_total else 0.0,
                basal_error=wrong / n_basal if n_basal else 0.0,
                cascade_agreement=agree / n_total if n_total else 0.0,
                n_basal=n_basal,
                n_total=n_total,
            )
        )
    return rows


def pick_threshold(
    rows: list[ThresholdRow], max_error: float = 0.02
) -> ThresholdRow | None:
    """Lowest threshold with ``basal_error <= max_error`` and ``n_basal >= 1``."""
    ok = [r for r in rows if r.n_basal >= 1 and r.basal_error <= max_error]
    return min(ok, key=lambda r: r.threshold) if ok else None


def confusion_matrix(
    cases: list[EvalCase], use: Literal["basal", "llm"]
) -> dict[str, dict[str, int]]:
    """Counts as ``matrix[reference][predicted]``; cases with no answer are skipped."""
    matrix: dict[str, dict[str, int]] = {}
    for c in cases:
        predicted = (
            (c.basal.answer if c.basal else None) if use == "basal" else c.llm_answer
        )
        if predicted is None:
            continue
        row = matrix.setdefault(c.reference, {})
        row[predicted] = row.get(predicted, 0) + 1
    return matrix


def percentile(values: list[int], p: float) -> float:
    """Linear-interpolated percentile (p in 0..100) of a non-empty list."""
    if not values:
        raise ValueError("percentile of empty list")
    s = sorted(values)
    k = (len(s) - 1) * p / 100
    lo = int(k)
    hi = min(lo + 1, len(s) - 1)
    return float(s[lo] + (s[hi] - s[lo]) * (k - lo))


def confidence_buckets(cases: list[EvalCase]) -> dict[str, int]:
    """Histogram of Basal confidence; cases without a Basal answer are ignored."""
    buckets = {"<30": 0, "30-50": 0, "50-80": 0, ">=80": 0}
    for c in cases:
        if c.basal is None:
            continue
        p = c.basal.confidence
        if p < 0.30:
            buckets["<30"] += 1
        elif p < 0.50:
            buckets["30-50"] += 1
        elif p < 0.80:
            buckets["50-80"] += 1
        else:
            buckets[">=80"] += 1
    return buckets


def llm_cost_usd(prompt_tokens: int, completion_tokens: int, model: str) -> float:
    try:
        price_in, price_out = PRICES_PER_MTOK[model]
    except KeyError:
        raise KeyError(
            f"Unknown model {model!r}; known: {sorted(PRICES_PER_MTOK)}"
        ) from None
    return (prompt_tokens * price_in + completion_tokens * price_out) / 1_000_000
