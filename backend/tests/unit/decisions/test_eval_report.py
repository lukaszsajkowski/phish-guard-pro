"""Tests for the eval report writer and input sources (US-053)."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from phishguard.agents.profiler import ClassificationError
from phishguard.decisions.basal_client import BasalAnswer, BasalUnavailableError
from phishguard.decisions.eval.__main__ import EvalInput, run_inputs
from phishguard.decisions.eval.metrics import EvalCase
from phishguard.decisions.eval.report import GATE1_WARNING, write_report
from phishguard.decisions.eval.sources import (
    load_decision_cases,
    load_fixture_inputs,
)
from phishguard.llm.client import LLMResponse
from phishguard.models.classification import AttackType

META = {
    "date": "2026-11-02",
    "basal_model": "basal-test",
    "llm_model": "gpt-4o",
    "sources": ["fixtures"],
}


def _basal(answer: str, conf: float) -> BasalAnswer:
    return BasalAnswer(
        answer=answer, probabilities={answer: conf}, confidence=conf, latency_ms=20
    )


def _case(
    cid: str,
    ref: str,
    basal: BasalAnswer | None,
    llm: str | None,
    *,
    reviewed: bool = True,
    ambiguous: bool = False,
) -> EvalCase:
    return EvalCase(
        id=cid,
        source="fixtures",
        reference=ref,
        basal=basal,
        llm_answer=llm,
        llm_ms=900 if llm else None,
        llm_prompt_tokens=1000 if llm else 0,
        llm_completion_tokens=50 if llm else 0,
        reviewed=reviewed,
        ambiguous=ambiguous,
    )


def _four_cases(reviewed: bool = True) -> list[EvalCase]:
    return [
        _case("a", "ceo_fraud", _basal("ceo_fraud", 0.95), "ceo_fraud"),
        _case("b", "fake_invoice", _basal("fake_invoice", 0.90), "fake_invoice"),
        _case("c", "not_phishing", _basal("ceo_fraud", 0.60), "not_phishing"),
        _case("d", "romance_scam", None, None, reviewed=reviewed),
    ]


def _report(tmp_path: Path, cases: list[EvalCase], meta: dict | None = None) -> str:
    write_report(cases, tmp_path, meta or META)
    return (tmp_path / "report.md").read_text()


def test_write_report_creates_files(tmp_path: Path) -> None:
    text = _report(tmp_path, _four_cases())

    assert (tmp_path / "results.jsonl").exists()
    assert (tmp_path / "report.md").exists()
    assert (tmp_path / "coverage_vs_error.png").stat().st_size > 0
    assert "| 0.90 |" in text
    rows = [
        json.loads(line)
        for line in (tmp_path / "results.jsonl").read_text().splitlines()
    ]
    assert [r["id"] for r in rows] == ["a", "b", "c", "d"]


def test_report_counts_confidence_at_threshold_as_covered(tmp_path: Path) -> None:
    cases = [
        _case("x", "ceo_fraud", _basal("ceo_fraud", 0.90), "ceo_fraud"),
        _case("y", "fake_invoice", _basal("fake_invoice", 0.50), "fake_invoice"),
    ]
    text = _report(tmp_path, cases)

    assert "| 0.90 | 1/2 |" in text
    assert "| 0.91 | 0/2 |" in text


def test_report_warns_on_unreviewed(tmp_path: Path) -> None:
    text = _report(tmp_path, _four_cases(reviewed=False))

    assert text.splitlines()[0] == GATE1_WARNING
    assert GATE1_WARNING == (
        "**⚠ Fixture labels not reviewed — this result does not pass gate 1.**"
    )


def test_report_no_warning_when_all_reviewed(tmp_path: Path) -> None:
    text = _report(tmp_path, _four_cases())

    assert "Fixture labels not reviewed" not in text
    assert (
        "Fixture labels: agreement of two blind Claude reviewers, not expert review."
        in text
    )


def test_report_ignores_unreviewed_ambiguous_case_for_warning(tmp_path: Path) -> None:
    cases = _four_cases()[:3] + [
        _case("amb", "ceo_fraud", None, None, reviewed=False, ambiguous=True)
    ]
    text = _report(tmp_path, cases)

    assert "Fixture labels not reviewed" not in text


def test_report_lists_ambiguous_separately_and_excludes_from_gate(
    tmp_path: Path,
) -> None:
    cases = [
        _case("ok", "ceo_fraud", _basal("ceo_fraud", 0.95), "ceo_fraud"),
        _case(
            "amb",
            "fake_invoice",
            _basal("ceo_fraud", 0.97),
            "ceo_fraud",
            ambiguous=True,
        ),
    ]
    text = _report(tmp_path, cases)

    # Gate table only has the non-ambiguous case.
    assert "| 0.90 | 1/1 |" in text
    assert "## Ambiguous cases (excluded from gate metrics)" in text
    assert "| amb |" in text
    ids = [
        json.loads(line)["id"]
        for line in (tmp_path / "results.jsonl").read_text().splitlines()
    ]
    assert "amb" in ids


def test_report_states_skipped_counts_and_guards_empty_latency(
    tmp_path: Path,
) -> None:
    cases = [_case("d", "romance_scam", None, None)]
    text = _report(tmp_path, cases)

    assert "skipped (no answer): 1" in text
    assert "| Basal | n/a | n/a |" in text
    assert "| LLM | n/a | n/a |" in text


def test_report_prices_each_case_at_its_model(tmp_path: Path) -> None:
    cases = [
        _case("a", "ceo_fraud", _basal("ceo_fraud", 0.95), "ceo_fraud"),
        _case("b", "ceo_fraud", _basal("ceo_fraud", 0.95), "ceo_fraud"),
    ]
    meta = {**META, "extras": {"b": {"llm_model": "gpt-4o-mini"}}}
    text = _report(tmp_path, cases, meta)

    # a: 1000*2.5/1e6 + 50*10/1e6 = 0.003; b: 1000*0.15/1e6 + 50*0.6/1e6 = 0.00018
    # per 1000 classifications: (0.003 + 0.00018) / 2 * 1000 = 1.59
    assert "$1.59" in text


def test_load_fixture_inputs(tmp_path: Path) -> None:
    path = tmp_path / "f.jsonl"
    path.write_text(
        json.dumps(
            {
                "id": "x",
                "gold": "ceo_fraud",
                "reviewed": False,
                "ambiguous": True,
                "email": "hi",
            }
        )
        + "\n\n"
    )

    assert load_fixture_inputs(path) == [("x", "hi", "ceo_fraud", False, True)]


def _query_returning(rows: list[dict]) -> MagicMock:
    query = MagicMock()
    for name in ("select", "eq", "order", "limit", "range"):
        getattr(query, name).return_value = query
    query.execute.return_value.data = rows
    client = MagicMock()
    client.table.return_value = query
    return client


def test_load_decision_cases_filters_incomplete_rows() -> None:
    base = {
        "node": "profiler.attack_type",
        "mode": "shadow",
        "basal_probabilities": {"ceo_fraud": 0.8, "fake_invoice": 0.2},
        "basal_confidence": 0.8,
        "basal_ms": 30,
        "llm_ms": 700,
    }
    rows = [
        {**base, "id": "ok", "basal_answer": "ceo_fraud", "llm_answer": "fake_invoice"},
        {**base, "id": "no-basal", "basal_answer": None, "llm_answer": "ceo_fraud"},
        {**base, "id": "no-llm", "basal_answer": "ceo_fraud", "llm_answer": None},
        {**base, "id": "llm-empty", "basal_answer": "ceo_fraud", "llm_answer": ""},
    ]
    client = _query_returning(rows)

    with patch(
        "phishguard.decisions.eval.sources._get_supabase_client",
        return_value=client,
    ):
        cases = load_decision_cases()

    assert [c.id for c in cases] == ["ok"]
    case = cases[0]
    assert case.source == "decisions"
    assert case.reference == "fake_invoice"
    assert case.llm_answer == "fake_invoice"
    assert case.basal is not None
    assert case.basal.answer == "ceo_fraud"
    assert case.basal.confidence == 0.8
    client.table.assert_called_with("decisions")


class _FakeBasal:
    async def ask_choice(self, state, instructions, criteria):
        if state == "basal-down":
            raise BasalUnavailableError("down")
        return _basal("ceo_fraud", 0.93)


class _FakeProfiler:
    async def classify_with_llm(self, email_content, session_id=None, *, on_usage):
        assert session_id is None
        if email_content == "llm-down":
            raise ClassificationError("boom")
        on_usage(
            LLMResponse(
                content="{}",
                model_used="gpt-4o-mini",
                prompt_tokens=100,
                completion_tokens=10,
            )
        )
        return MagicMock(attack_type=AttackType.CEO_FRAUD)


async def test_run_inputs_records_errors_per_case() -> None:
    inputs = [
        EvalInput("ok", "fixtures", "fine", "ceo_fraud"),
        EvalInput("b", "fixtures", "basal-down", "ceo_fraud"),
        EvalInput("l", "fixtures", "llm-down", "ceo_fraud", reviewed=False),
    ]

    cases, extras = await run_inputs(inputs, _FakeBasal(), _FakeProfiler())

    by_id = {c.id: c for c in cases}
    assert by_id["ok"].basal is not None
    assert by_id["ok"].llm_answer == "ceo_fraud"
    assert by_id["ok"].llm_prompt_tokens == 100
    assert extras["ok"]["llm_model"] == "gpt-4o-mini"
    assert by_id["b"].basal is None
    assert "down" in extras["b"]["basal_error"]
    assert by_id["l"].llm_answer is None
    assert by_id["l"].llm_ms is None
    assert "boom" in extras["l"]["llm_error"]
    assert by_id["l"].reviewed is False


async def test_run_inputs_without_profiler_records_llm_error() -> None:
    inputs = [EvalInput("ok", "fixtures", "fine", "ceo_fraud")]

    cases, extras = await run_inputs(
        inputs, _FakeBasal(), None, profiler_error="no key"
    )

    assert cases[0].llm_answer is None
    assert extras["ok"]["llm_error"] == "no key"
