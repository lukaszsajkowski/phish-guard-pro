"""Tests for the Arena report (hand-built results folder, no LLM)."""

import re
from pathlib import Path

import pytest

from phishguard.arena.metrics import summarise
from phishguard.arena.records import ConversationRecord, TurnRecord
from phishguard.arena.report import render_chart, render_markdown, select_excerpt
from phishguard.arena.runner import RunMeta
from phishguard.arena.scammer import ScammerTurn
from phishguard.arena.scenario import load_scenario
from phishguard.arena.setup import ScenarioSetup
from phishguard.arena.victims import VictimReply
from phishguard.llm import UsageEntry

SCENARIOS_DIR = Path(__file__).resolve().parents[4] / "evals" / "scenarios"
EN = "en-ceo_fraud-easy"
PL = "pl-blik-easy"
RESULTS_REL = "evals/results/2026-11-06"


def _usage(prompt: int) -> UsageEntry:
    return UsageEntry(
        model="gpt-6-luna", prompt_tokens=prompt, completion_tokens=200, latency_ms=50
    )


def _turn(index, reveals=(), suspects=False):
    scammer = (
        None
        if index == 0
        else ScammerTurn(
            message=f"scammer says {index}",
            revealed_secret_ids=[],
            suspects_bot=suspects,
            ends_conversation=False,
        )
    )
    return TurnRecord(
        index=index,
        scammer=scammer,
        detected_reveals=list(reveals),
        unmasking_detected=False,
        victim=VictimReply(
            content=f"victim says {index}",
            extracted_iocs=[],
            regenerations=0,
            is_safe=True,
        ),
    )


def _record(sid, system, rep, reveal_turn=None, secret_id=None, suspects=False):
    turns = [
        _turn(i, [secret_id] if i == reveal_turn else [], suspects and i == 2)
        for i in range(6)
    ]
    return ConversationRecord(
        scenario_id=sid,
        scenario_hash="h",
        system=system,
        repetition=rep,
        status="completed",
        status_reason=None,
        end_reason="turn_limit",
        turns=turns,
        victim_usage=[_usage(1000 if system == "phishguard" else 400)],
        scammer_usage=[_usage(500)],
        started_at="2026-11-06T00:00:00Z",
        duration_ms=1,
    )


# (scenario, system, rep) -> (reveal turn, secret id, suspects bot)
PLAN = {
    (EN, "phishguard", 0): (3, "escrow_account", False),
    (EN, "phishguard", 1): (2, "escrow_account", True),
    (PL, "phishguard", 0): (2, "konto_weryfikacja", False),
    (PL, "phishguard", 1): (None, None, False),
    (EN, "baseline", 0): (4, "escrow_account", False),
    (EN, "baseline", 1): (None, None, True),
    (PL, "baseline", 0): (None, None, False),
    (PL, "baseline", 1): (5, "konto_weryfikacja", False),
}


def build_results(
    root: Path,
    drop_baseline: int = 0,
    invalid: int = 0,
    systems: tuple[str, ...] = ("phishguard", "baseline"),
    no_reveals: bool = False,
) -> Path:
    """Write 2 scenarios x 2 systems x 2 repetitions."""
    meta = RunMeta(
        date="2026-11-06",
        commit="abc1234",
        model="gpt-6-luna",
        repetitions=2,
        systems=list(systems),
        scenario_ids=[EN, PL],
    )
    (root / "conversations").mkdir(parents=True)
    (root / "setup").mkdir()
    (root / "run.json").write_text(meta.model_dump_json(), encoding="utf-8")
    for sid in (EN, PL):
        setup = ScenarioSetup(
            scenario_id=sid,
            classification={"attack_type": "ceo_fraud"},
            usage=[_usage(300)],
        )
        (root / "setup" / f"{sid}.json").write_text(
            setup.model_dump_json(), encoding="utf-8"
        )
    dropped = invalid_left = 0
    for (sid, system, rep), (turn, secret, suspects) in sorted(PLAN.items()):
        if system not in systems:
            continue
        if no_reveals:
            turn, secret = None, None
        if system == "baseline" and dropped < drop_baseline:
            dropped += 1
            continue
        rec = _record(sid, system, rep, turn, secret, suspects)
        if invalid_left < invalid:
            invalid_left += 1
            rec = rec.model_copy(update={"status": "invalid", "end_reason": "invalid"})
        path = root / "conversations" / f"{sid}__{system}__r{rep}.json"
        path.write_text(rec.model_dump_json(), encoding="utf-8")
    return root


@pytest.fixture
def scenarios():
    return {s: load_scenario(SCENARIOS_DIR / f"{s}.yaml") for s in (EN, PL)}


def render(results: Path, scenarios, excerpt_override=None) -> str:
    summary = summarise(results, scenarios)
    excerpt = select_excerpt(results, excerpt_override)
    return render_markdown(
        summary,
        summary.meta,
        excerpt,
        "evals/chart.png",
        RESULTS_REL,
        excerpt_override,
    )


def test_report_starts_with_headline_table(tmp_path, scenarios):
    text = render(build_results(tmp_path / "r"), scenarios)

    table = [ln for ln in text.splitlines() if ln.startswith("|")][:4]
    header = table[0]
    for col in (
        "Secrets extracted",
        "Turns to first secret",
        "Bot detected",
        "Cost / conversation",
    ):
        assert col in header
    assert "| PhishGuard |" in table[2]
    assert "| Baseline (plain LLM) |" in table[3]
    assert "(" in table[2] and "–" in table[2]
    # The table is the first thing after the title block.
    assert text.index("Secrets extracted") < text.index("chart.png")


def test_report_contains_caveats_and_reproduce_section(tmp_path, scenarios):
    text = render(build_results(tmp_path / "r"), scenarios)

    assert "simulation is not production" in text
    assert "same model" in text
    assert "fictional" in text
    assert "uv run python -m phishguard.arena run" in text
    assert "uv run python -m phishguard.arena report" in text
    assert "OPENAI_API_KEY" in text
    assert "recruit" not in text.lower() and "portfolio" not in text.lower()
    assert f"{RESULTS_REL}/conversations/" in text


def test_excerpt_prefers_earliest_iban_reveal(tmp_path):
    results = build_results(tmp_path / "r")

    record, reveal_turn = select_excerpt(results, None)

    assert (record.scenario_id, record.repetition) == (EN, 1)
    assert record.system == "phishguard"
    assert reveal_turn == 2


def test_excerpt_override(tmp_path):
    results = build_results(tmp_path / "r")

    record, reveal_turn = select_excerpt(results, f"{PL}__phishguard__r0")

    assert record.scenario_id == PL
    assert reveal_turn == 2


def test_report_is_deterministic(tmp_path, scenarios):
    results = build_results(tmp_path / "r")

    assert render(results, scenarios) == render(results, scenarios)
    summary = summarise(results, scenarios)
    assert "33.3% (25.0%–41.7%)" in render(results, scenarios)  # 1 decimal
    assert "$0.0003 ($0.0003–$0.0003)" in render(results, scenarios)  # 4 decimals
    render_chart(summary, tmp_path / "a.png")
    render_chart(summary, tmp_path / "b.png")
    assert (tmp_path / "a.png").read_bytes() == (tmp_path / "b.png").read_bytes()
    assert (tmp_path / "a.png").read_bytes()[:4] == b"\x89PNG"


def test_report_renders_with_missing_conversations(tmp_path, scenarios):
    results = build_results(tmp_path / "r", drop_baseline=2)

    text = render(results, scenarios)

    assert re.search(r"Missing[^\n]*\b2\b", text)
    assert (
        "averaged over different scenario sets" in text
        and "PhishGuard 2 of 2 scenarios, Baseline (plain LLM) 1 of 2 scenarios" in text
    )


def test_invalid_share_warning(tmp_path, scenarios):
    results = build_results(tmp_path / "r", invalid=3)

    text = render(results, scenarios)

    first_table_line = next(
        i for i, ln in enumerate(text.splitlines()) if ln.startswith("|")
    )
    warning = [
        i for i, ln in enumerate(text.splitlines()) if ln.startswith("> **Warning")
    ]
    assert warning and warning[0] < first_table_line


def test_no_warning_when_few_invalid(tmp_path, scenarios):
    text = render(build_results(tmp_path / "r"), scenarios)

    assert "> **Warning" not in text


@pytest.mark.parametrize(
    "kwargs",
    [
        {"systems": ("baseline",)},
        {"systems": ("phishguard",), "no_reveals": True},
        {"no_reveals": True},
    ],
    ids=["baseline-only", "phishguard-no-reveals", "no-reveals"],
)
def test_report_renders_without_excerpt(tmp_path, scenarios, kwargs):
    results = build_results(tmp_path / "r", **kwargs)

    assert select_excerpt(results, None) is None
    text = render(results, scenarios)
    assert "No PhishGuard conversation with a revealed secret in this run." in text
    render_chart(summarise(results, scenarios), tmp_path / "c.png")


def test_report_renders_phishguard_only(tmp_path, scenarios):
    text = render(build_results(tmp_path / "r", systems=("phishguard",)), scenarios)

    assert "| PhishGuard |" in text
    assert "Baseline (plain LLM) |" not in text.split("## Caveats")[0]


def test_report_skips_corrupt_conversation(tmp_path, scenarios):
    results = build_results(tmp_path / "r")
    bad = results / "conversations" / f"{EN}__phishguard__r1.json"
    bad.write_text('{"scenario_id": "trunc', encoding="utf-8")

    record, turn = select_excerpt(results, None)
    text = render(results, scenarios)

    assert (record.scenario_id, record.repetition, turn) == (EN, 0, 3) or (
        record.scenario_id,
        record.repetition,
        turn,
    ) == (PL, 0, 2)
    assert (
        "Unreadable conversation files (corrupt or truncated, skipped): "
        f"1: `{bad.name}`" in text
    )


def test_excerpt_heading_and_labels_follow_selection(tmp_path, scenarios):
    results = build_results(tmp_path / "r")

    auto = render(results, scenarios)
    assert "## Example: the persona gets an IBAN" in auto
    assert "earliest IBAN reveal" in auto
    assert "**PhishGuard persona**" in auto

    manual = render(results, scenarios, f"{EN}__baseline__r0")
    assert "chosen by hand" in manual
    assert "**Baseline (plain LLM)**" in manual
    assert "the baseline victim gets an IBAN" in manual


def test_excerpt_ignores_invalid_conversations(tmp_path):
    results = build_results(tmp_path / "r")
    path = results / "conversations" / f"{EN}__phishguard__r1.json"
    rec = ConversationRecord.model_validate_json(path.read_text(encoding="utf-8"))
    path.write_text(
        rec.model_copy(update={"status": "invalid"}).model_dump_json(),
        encoding="utf-8",
    )

    chosen, _ = select_excerpt(results, None)

    assert (chosen.scenario_id, chosen.repetition) != (EN, 1)
    assert chosen.status == "completed"


def test_excerpt_override_without_reveal_is_an_error(tmp_path):
    results = build_results(tmp_path / "r")

    with pytest.raises(ValueError, match="no revealed secret"):
        select_excerpt(results, f"{PL}__phishguard__r1")
