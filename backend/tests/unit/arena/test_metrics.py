"""Tests for Arena metrics (hand-built records with known answers)."""

import json
from pathlib import Path

import pytest

from phishguard.arena.metrics import (
    Aggregate,
    aggregate,
    conversation_metrics,
    summarise,
    within_noise,
)
from phishguard.arena.records import ConversationRecord, TurnRecord
from phishguard.arena.runner import RunMeta
from phishguard.arena.scammer import ScammerTurn
from phishguard.arena.scenario import Scenario, Secret, load_scenario
from phishguard.arena.setup import ScenarioSetup
from phishguard.arena.victims import VictimReply
from phishguard.decisions.eval.metrics import llm_cost_usd
from phishguard.llm import UsageEntry

SCENARIOS = Path(__file__).resolve().parents[4] / "evals" / "scenarios"
IBAN = "DE11573267298484571525"
PHONE = "+12025550143"
URL = "https://pay.example/x"


@pytest.fixture
def scenario() -> Scenario:
    base = load_scenario(SCENARIOS / "en-ceo_fraud-easy.yaml")
    third = Secret(id="pay_link", type="url", value=URL, reveal_when="asked")
    return base.model_copy(
        update={"secrets": [*base.secrets, third], "known_iocs": ["+12025550199"]}
    )


def usage(prompt=1000, completion=500, latency=100):
    return UsageEntry(
        model="gpt-6-luna",
        prompt_tokens=prompt,
        completion_tokens=completion,
        latency_ms=latency,
    )


def reply(iocs=None, regenerations=0, is_safe=True):
    return VictimReply(
        content="ok",
        extracted_iocs=iocs or [],
        regenerations=regenerations,
        is_safe=is_safe,
    )


def turn(index, reveals=None, iocs=None, suspects=False, unmask=False, **kw):
    scammer = (
        None
        if index == 0
        else ScammerTurn(
            message="m",
            revealed_secret_ids=[],
            suspects_bot=suspects,
            ends_conversation=False,
        )
    )
    return TurnRecord(
        index=index,
        scammer=scammer,
        detected_reveals=reveals or [],
        unmasking_detected=unmask,
        victim=reply(iocs, **kw),
    )


def record(
    turns,
    system="phishguard",
    status="completed",
    scenario_id="en-ceo_fraud-easy",
    repetition=0,
    victim_usage=None,
):
    return ConversationRecord(
        scenario_id=scenario_id,
        scenario_hash="h",
        system=system,
        repetition=repetition,
        status=status,
        status_reason=None,
        end_reason="turn_limit" if status == "completed" else status,
        turns=turns,
        victim_usage=[usage()] if victim_usage is None else victim_usage,
        scammer_usage=[usage()],
        started_at="2026-11-06T00:00:00Z",
        duration_ms=1,
    )


def test_share_and_turns_to_first_secret(scenario):
    rec = record(
        [
            turn(0),
            turn(1),
            turn(2, reveals=["escrow_account"]),
            turn(3),
            turn(4),
            turn(5, reveals=["assistant_phone"]),
        ]
    )
    m = conversation_metrics(rec, scenario, 0.0)
    assert m.secrets_revealed_share == pytest.approx(2 / 3)
    assert m.turns_to_first_secret == 2
    assert m.engagement_turns == 5


def test_no_reveal_gives_none_turns(scenario):
    m = conversation_metrics(record([turn(0), turn(1)]), scenario, 0.0)
    assert m.secrets_revealed_share == 0.0
    assert m.turns_to_first_secret is None


def test_flags_and_safety_counters(scenario):
    rec = record(
        [
            turn(0),
            turn(1, suspects=True, regenerations=2),
            turn(2, unmask=True, regenerations=1, is_safe=False),
        ]
    )
    m = conversation_metrics(rec, scenario, 0.0)
    assert m.suspected_bot and m.unmasking_detected
    assert (m.safety_regenerations, m.safety_turns, m.unsafe_replies_sent) == (3, 2, 1)
    assert m.victim_latency_ms == 100


def test_setup_cost_added_for_phishguard_only(scenario):
    turns = [turn(0), turn(1)]
    base = conversation_metrics(record(turns, system="baseline"), scenario, 0.0)
    pg = conversation_metrics(record(turns), scenario, 0.003)
    assert base.victim_cost_usd == pytest.approx(llm_cost_usd(1000, 500, "gpt-6-luna"))
    assert pg.victim_cost_usd == pytest.approx(base.victim_cost_usd + 0.003)
    assert pg.setup_cost_usd == 0.003
    # The baseline never carries setup cost, even if one is passed in.
    assert (
        conversation_metrics(
            record(turns, system="baseline"), scenario, 0.003
        ).victim_cost_usd
        == base.victim_cost_usd
    )


def test_ioc_precision_counts_known_iocs_as_not_false(scenario):
    iocs = [
        {"type": "iban", "value": "DE11 5732 6729 8484 5715 25"},  # revealed secret
        {"type": "phone", "value": "+1 202 555 0199"},  # known IOC
        {"type": "phone", "value": "+1 202 555 0001"},  # false positive
    ]
    rec = record([turn(0), turn(1, reveals=["escrow_account"], iocs=iocs)])
    m = conversation_metrics(rec, scenario, 0.0)
    assert m.ioc_revealed == 1
    assert m.ioc_true_positives == 1
    assert m.ioc_false_positives == 1
    assert m.ioc_extracted == 3


def test_ioc_values_are_deduplicated_across_turns(scenario):
    ioc = {"type": "iban", "value": IBAN}
    rec = record(
        [
            turn(0),
            turn(1, reveals=["escrow_account"], iocs=[ioc]),
            turn(2, iocs=[ioc]),
        ]
    )
    m = conversation_metrics(rec, scenario, 0.0)
    assert (m.ioc_true_positives, m.ioc_extracted) == (1, 1)


def test_aggregate_excludes_none_and_reports_min_max():
    agg = aggregate([0.5, None, 0.7])
    assert agg.mean == pytest.approx(0.6)
    assert (agg.min, agg.max) == (0.5, 0.7)
    assert (agg.n_valid, agg.n_excluded) == (2, 1)


def test_aggregate_all_none():
    agg = aggregate([None, None])
    assert agg.mean is None and agg.n_valid == 0 and agg.n_excluded == 2


def test_within_noise_overlap_rule():
    def agg(lo, hi):
        return Aggregate(mean=(lo + hi) / 2, min=lo, max=hi, n_valid=3, n_excluded=0)

    assert within_noise(agg(0.4, 0.6), agg(0.55, 0.8))
    assert not within_noise(agg(0.4, 0.5), agg(0.6, 0.8))
    assert not within_noise(aggregate([None]), agg(0.1, 0.2))


# --- summarise -----------------------------------------------------------


def write(results: Path, meta: RunMeta, setups, records):
    (results / "setup").mkdir(parents=True)
    (results / "conversations").mkdir()
    (results / "run.json").write_text(meta.model_dump_json())
    for s in setups:
        (results / "setup" / f"{s.scenario_id}.json").write_text(s.model_dump_json())
    for r in records:
        name = f"{r.scenario_id}__{r.system}__r{r.repetition}.json"
        (results / "conversations" / name).write_text(r.model_dump_json())


def test_invalid_conversations_excluded_and_counted(tmp_path, scenario):
    sid = scenario.id
    meta = RunMeta(
        date="2026-11-06",
        commit="abc",
        victim_model="gpt-6-luna",
        scammer_model="gpt-5.4-mini",
        repetitions=3,
        systems=["phishguard", "baseline"],
        scenario_ids=[sid],
    )
    setup = ScenarioSetup(
        scenario_id=sid,
        classification={"attack_type": scenario.attack_type.value},
        usage=[usage(2000, 0)],  # 2000 * 0.10 / 1e6 = 0.0002
    )
    full = [turn(0), turn(1, reveals=["escrow_account"]), turn(2)]
    records = [
        record(full, repetition=0),
        record(full, repetition=1, status="blocked_by_safety"),
        record([], repetition=2, status="invalid"),
        record(full, system="baseline", repetition=0),
        record([], system="baseline", repetition=1, status="error"),
    ]  # baseline r2 is missing
    write(tmp_path, meta, [setup], records)

    summary = summarise(tmp_path, {sid: scenario})

    pg = summary.counts["phishguard"]
    assert (pg.expected, pg.completed, pg.blocked_by_safety, pg.invalid) == (3, 1, 1, 1)
    bl = summary.counts["baseline"]
    assert (bl.completed, bl.error, bl.missing) == (1, 1, 1)

    share = summary.headline["phishguard"]["secrets_revealed_share"]
    assert share.n_valid == 2 and share.n_excluded == 1
    assert share.mean == pytest.approx(1 / 3)
    # Setup cost split across the 2 PhishGuard records that entered metrics.
    assert summary.cost_split.setup.mean == pytest.approx(0.0001)
    assert summary.safety.blocked_conversations == 1
    assert summary.profiler_agreement.n == 1 and summary.profiler_agreement.agreed == 1
    assert [r.scenario_id for r in summary.per_scenario] == [sid]
    assert (
        summary.by_language["en"]["phishguard"]["secrets_revealed_share"].n_valid == 2
    )


def test_summary_round_trips_json(tmp_path, scenario):
    sid = scenario.id
    meta = RunMeta(
        date="d",
        commit="c",
        victim_model="gpt-6-luna",
        scammer_model="gpt-5.4-mini",
        repetitions=1,
        systems=["phishguard"],
        scenario_ids=[sid],
    )
    write(tmp_path, meta, [], [record([turn(0), turn(1)])])
    summary = summarise(tmp_path, {sid: scenario})
    assert json.loads(summary.model_dump_json())["meta"]["commit"] == "c"
    assert summary.profiler_agreement.n == 0
    assert summary.profiler_agreement.share is None


def test_profiler_agreement_counts_mismatch_and_not_phishing(tmp_path, scenario):
    base = scenario
    s1 = base.model_copy(update={"id": "a-one", "attack_type": "romance_scam"})
    s2 = base.model_copy(update={"id": "b-two"})
    s3 = base.model_copy(update={"id": "c-three"})
    s4 = base.model_copy(update={"id": "d-four"})
    scenarios = {s.id: s for s in (s1, s2, s3, s4)}
    meta = RunMeta(
        date="d",
        commit="c",
        victim_model="gpt-6-luna",
        scammer_model="gpt-5.4-mini",
        repetitions=1,
        systems=["phishguard"],
        scenario_ids=sorted(scenarios),
    )
    setups = [
        ScenarioSetup(
            scenario_id="a-one", classification={"attack_type": "fake_invoice"}
        ),
        ScenarioSetup(
            scenario_id="b-two",
            classification={"attack_type": "not_phishing"},
            error="not_phishing",
        ),
        ScenarioSetup(
            scenario_id="c-three",
            classification={"attack_type": base.attack_type.value},
        ),
        ScenarioSetup(scenario_id="d-four", error="boom"),  # intake failure: excluded
    ]
    write(tmp_path, meta, setups, [])

    pa = summarise(tmp_path, scenarios).profiler_agreement

    assert (pa.n, pa.agreed) == (3, 1)
    assert pa.share == pytest.approx(1 / 3)
    assert [(m.scenario_id, m.expected, m.got) for m in pa.mismatches] == [
        ("a-one", "romance_scam", "fake_invoice"),
        ("b-two", base.attack_type.value, "not_phishing"),
    ]
