"""Binary (in-role) eval metrics and report (US-050)."""

import pytest

from phishguard.decisions.basal_client import BasalAnswer
from phishguard.decisions.eval.binary import (
    BinaryCase,
    BinaryRow,
    binary_curve,
    pick_binary_threshold,
    write_binary_report,
)


def _basal(answer: str, conf: float) -> BasalAnswer:
    return BasalAnswer(
        answer=answer,
        probabilities={answer: conf},
        confidence=conf,
        latency_ms=100,
    )


def _case(
    cid: str, gold: str, answer: str | None, conf: float = 0.0, lang: str = "en"
) -> BinaryCase:
    basal = _basal(answer, conf) if answer else None
    return BinaryCase(id=cid, gold=gold, basal=basal, lang=lang, synthetic=False)


@pytest.fixture
def six_cases() -> list[BinaryCase]:
    return [
        _case("p1", "breaks_role", "breaks_role", 0.95),
        _case("p2", "breaks_role", "breaks_role", 0.85),
        _case("p3", "breaks_role", "in_role", 0.9),  # missed
        _case("n1", "in_role", "breaks_role", 0.9),  # false alarm
        _case("n2", "in_role", "in_role", 0.95),
        _case("n3", "in_role", "breaks_role", 0.6),  # below 0.8
    ]


def test_binary_curve_hand_computed(six_cases):
    # Arrange / Act
    (row,) = binary_curve(six_cases, "breaks_role", [0.8])

    # Assert: flagged = p1, p2, n1
    assert row.n_flagged == 3
    assert row.n_positive == 3
    assert row.n_negative == 3
    assert row.precision == pytest.approx(2 / 3)
    assert row.recall == pytest.approx(2 / 3)
    assert row.false_alarm_rate == pytest.approx(1 / 3)


def test_threshold_is_inclusive():
    cases = [_case("p", "breaks_role", "breaks_role", 0.8)]
    (row,) = binary_curve(cases, "breaks_role", [0.8])
    assert row.n_flagged == 1


def test_case_without_basal_is_not_flagged():
    cases = [
        _case("p1", "breaks_role", None),
        _case("p2", "breaks_role", "breaks_role", 0.9),
    ]
    (row,) = binary_curve(cases, "breaks_role", [0.5])
    assert row.n_flagged == 1
    assert row.recall == pytest.approx(0.5)


def test_precision_zero_when_nothing_flagged():
    cases = [_case("p1", "breaks_role", "in_role", 0.9)]
    (row,) = binary_curve(cases, "breaks_role", [0.9])
    assert row.n_flagged == 0
    assert row.precision == 0.0
    assert row.recall == 0.0


def test_recall_none_without_positives():
    cases = [_case("n1", "in_role", "breaks_role", 0.9)]
    (row,) = binary_curve(cases, "breaks_role", [0.5])
    assert row.n_positive == 0
    assert row.recall is None
    assert row.false_alarm_rate == pytest.approx(1.0)


def test_false_alarm_none_without_negatives():
    cases = [_case("p1", "breaks_role", "breaks_role", 0.9)]
    (row,) = binary_curve(cases, "breaks_role", [0.5])
    assert row.n_negative == 0
    assert row.false_alarm_rate is None
    assert row.recall == pytest.approx(1.0)


def test_pick_returns_highest_threshold_meeting_gate(six_cases):
    rows = binary_curve(six_cases, "breaks_role", [0.5, 0.6, 0.8, 0.9])
    # recall is at most 2/3 everywhere: nothing meets the default 0.9 gate
    assert pick_binary_threshold(rows) is None
    picked = pick_binary_threshold(rows, min_recall=0.6, max_false_alarm=0.4)
    # 0.9: flagged p1, n1 -> recall 1/3 fails; 0.8: recall 2/3, fa 1/3 passes
    assert picked is not None
    assert picked.threshold == 0.8


def test_pick_skips_rows_with_none():
    rows = [
        BinaryRow(0.5, 0.0, None, 0.0, 0, 0, 3),
        BinaryRow(0.6, 1.0, 1.0, None, 3, 3, 0),
    ]
    assert pick_binary_threshold(rows) is None


def test_write_binary_report_failing_set(tmp_path, six_cases):
    meta = {"date": "2026-11-03", "basal_model": "m", "extras": {}}
    write_binary_report(six_cases, tmp_path, meta)

    assert (tmp_path / "results.jsonl").exists()
    report = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "| 0.80 |" in report
    assert "No threshold meets the gate." in report


def test_write_binary_report_renders_na_for_real_only(tmp_path):
    cases = [
        _case("n1", "in_role", "in_role", 0.9),
        _case("n2", "in_role", "breaks_role", 0.9),
    ]
    write_binary_report(cases, tmp_path, {"date": "d", "basal_model": "m"})
    report = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "n/a" in report
