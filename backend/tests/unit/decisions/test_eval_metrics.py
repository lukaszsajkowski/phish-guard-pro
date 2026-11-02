"""Tests for eval metrics (US-053) on a hand-computed 5-case set."""

import pytest

from phishguard.decisions.basal_client import BasalAnswer
from phishguard.decisions.eval.metrics import (
    EvalCase,
    confidence_buckets,
    confusion_matrix,
    llm_cost_usd,
    percentile,
    pick_threshold,
    threshold_curve,
)


def _basal(answer: str, conf: float) -> BasalAnswer:
    return BasalAnswer(
        answer=answer, probabilities={answer: conf}, confidence=conf, latency_ms=10
    )


def _case(cid, ref, basal, llm) -> EvalCase:
    return EvalCase(
        id=cid,
        source="s",
        reference=ref,
        basal=basal,
        llm_answer=llm,
        llm_ms=100 if llm else None,
        llm_prompt_tokens=1000,
        llm_completion_tokens=50,
    )


@pytest.fixture
def cases() -> list[EvalCase]:
    return [
        _case("1", "a", _basal("a", 0.95), "a"),  # covered, right
        _case("2", "b", _basal("b", 0.90), "b"),  # covered (inclusive), right
        _case("3", "a", _basal("b", 0.92), "a"),  # covered, Basal wrong
        _case("4", "c", _basal("c", 0.50), "c"),  # uncovered, LLM right
        _case("5", "a", None, "a"),  # no Basal, LLM right
    ]


def test_threshold_curve_at_0_9(cases):
    (row,) = threshold_curve(cases, [0.9])
    assert row.threshold == 0.9
    assert row.n_total == 5
    assert row.n_basal == 3
    assert row.coverage == pytest.approx(0.6)
    assert row.basal_error == pytest.approx(1 / 3)
    assert row.cascade_agreement == pytest.approx(0.8)


def test_threshold_curve_nothing_covered(cases):
    (row,) = threshold_curve(cases, [0.99])
    assert row.n_basal == 0
    assert row.coverage == 0.0
    assert row.basal_error == 0.0
    assert row.cascade_agreement == pytest.approx(1.0)  # LLM right on all


def test_cascade_counts_failed_llm_as_disagreement():
    c = [_case("1", "a", _basal("a", 0.1), None)]
    (row,) = threshold_curve(c, [0.9])
    assert row.cascade_agreement == 0.0


def test_threshold_curve_empty():
    (row,) = threshold_curve([], [0.9])
    assert row.n_total == 0
    assert row.coverage == 0.0
    assert row.cascade_agreement == 0.0


def test_pick_threshold(cases):
    rows = threshold_curve(cases, [0.5, 0.9, 0.93, 0.99])
    # t=0.5: covered 1,2,3,4 -> 1 wrong/4; t=0.9: 1/3; t=0.93: only case 1 -> 0
    picked = pick_threshold(rows, max_error=0.02)
    assert picked is not None
    assert picked.threshold == 0.93
    assert picked.n_basal == 1


def test_pick_threshold_none_qualifies(cases):
    rows = threshold_curve(cases, [0.5, 0.9, 0.99])
    # 0.99 has n_basal 0 (excluded); others have errors > 0.02
    assert pick_threshold(rows) is None


def test_confusion_matrix(cases):
    assert confusion_matrix(cases, "basal") == {
        "a": {"a": 1, "b": 1},
        "b": {"b": 1},
        "c": {"c": 1},
    }
    assert confusion_matrix(cases, "llm") == {
        "a": {"a": 3},
        "b": {"b": 1},
        "c": {"c": 1},
    }


def test_percentile():
    assert percentile([10, 20, 30, 40], 50) == 25.0
    assert percentile([10, 20, 30, 40], 0) == 10.0
    assert percentile([10, 20, 30, 40], 100) == 40.0
    assert percentile([7], 95) == 7.0


def test_confidence_buckets_edges():
    cs = [
        _case(str(i), "a", _basal("a", p), "a")
        for i, p in enumerate([0.29, 0.30, 0.49, 0.50, 0.79, 0.80, 1.0])
    ]
    cs.append(_case("x", "a", None, "a"))  # no Basal: ignored
    assert confidence_buckets(cs) == {"<30": 1, "30-50": 2, "50-80": 2, ">=80": 2}


def test_llm_cost_usd():
    assert llm_cost_usd(1_000_000, 1_000_000, "gpt-4o") == pytest.approx(12.5)
    assert llm_cost_usd(2000, 500, "gpt-4o-mini") == pytest.approx(0.0006)


def test_llm_cost_unknown_model():
    with pytest.raises(KeyError, match="gpt-5-unknown"):
        llm_cost_usd(1, 1, "gpt-5-unknown")
