"""Tests for the Arena conversation loop and reveal detection."""

from pathlib import Path

import pytest

from phishguard.agents.conversation import SafetyRegenerationExhaustedError
from phishguard.arena.conversation import detect_reveals, normalise, run_conversation
from phishguard.arena.scammer import ModelRefusalError, ScammerTurn
from phishguard.arena.scenario import Scenario, load_scenario
from phishguard.arena.victims import VictimReply

SCENARIOS = Path(__file__).resolve().parents[4] / "evals" / "scenarios"


@pytest.fixture
def scenario():
    return load_scenario(SCENARIOS / "en-ceo_fraud-easy.yaml").model_copy(
        update={"max_turns": 3}
    )


def turn(message="Pay now.", ends=False, suspects=False, ids=None):
    return ScammerTurn(
        message=message,
        revealed_secret_ids=ids or [],
        suspects_bot=suspects,
        ends_conversation=ends,
    )


class FakeScammer:
    def __init__(self, turns):
        self.turns = list(turns)
        self.transcripts = []

    async def next_turn(self, scenario, transcript):
        self.transcripts.append(list(transcript))
        item = self.turns.pop(0) if len(self.turns) > 1 else self.turns[0]
        if isinstance(item, Exception):
            raise item
        return item


class FakeVictim:
    name = "fake"

    def __init__(self, error=None):
        self.error = error
        self.calls = []

    async def reply(self, transcript, scammer_message):
        self.calls.append((list(transcript), scammer_message))
        if self.error:
            raise self.error
        return VictimReply(
            content="ok", extracted_iocs=[], regenerations=0, is_safe=True
        )


async def test_runs_to_turn_limit(scenario):
    victim = FakeVictim()
    record = await run_conversation(
        scenario, victim, FakeScammer([turn()]), "baseline", 0
    )

    assert record.end_reason == "turn_limit"
    assert record.status == "completed"
    assert [t.index for t in record.turns] == [0, 1, 2, 3]
    assert record.turns[0].scammer is None
    # victim sees only messages before the current scammer message
    assert victim.calls[0] == ([], None)
    assert [m.turn for m in victim.calls[1][0]] == [0]
    record.model_dump(mode="json")


async def test_scammer_can_end_conversation(scenario):
    scammer = FakeScammer([turn(), turn(ends=True)])
    record = await run_conversation(scenario, FakeVictim(), scammer, "baseline", 0)

    assert record.end_reason == "scammer_ended"
    assert record.turns[-1].index == 2
    assert record.turns[-1].victim is None


@pytest.mark.parametrize(
    ("kind", "value", "message"),
    [
        (
            "iban",
            "PL61109010140000071219812874",
            "konto: PL61 1090 1014 0000 0712 1981 2874.",
        ),
        ("phone", "+442079460123", "call +44 2079-460123,"),
        ("url", "https://pay.example/x", "go to https://pay.example/x."),
    ],
)
def test_reveal_detected_despite_formatting(scenario, kind, value, message):
    secret = scenario.secrets[0].model_copy(update={"type": kind, "value": value})
    sc = Scenario.model_construct(**{**scenario.__dict__, "secrets": [secret]})

    assert detect_reveals(sc, message) == [secret.id]


def test_reveal_not_detected_for_partial_value(scenario):
    secret = next(s for s in scenario.secrets if s.type == "iban")
    half = secret.value[: len(secret.value) // 2]

    assert secret.id not in detect_reveals(scenario, f"account {half}")


def test_normalise():
    assert normalise("+44 (20) 7946-0123.") == "+442079460123"


async def test_reveal_in_final_scammer_message_counts(scenario):
    secret = next(s for s in scenario.secrets if s.type == "iban")
    scammer = FakeScammer([turn(message=f"Last: {secret.value}", ends=True)])
    record = await run_conversation(scenario, FakeVictim(), scammer, "baseline", 0)

    assert record.turns[-1].detected_reveals == [secret.id]
    assert record.turns[-1].victim is None


async def test_refusal_marks_invalid(scenario):
    record = await run_conversation(
        scenario, FakeVictim(), FakeScammer([ModelRefusalError("x")]), "baseline", 0
    )
    assert (record.status, record.status_reason) == ("invalid", "scammer_refused")
    assert record.end_reason == "invalid"

    record = await run_conversation(
        scenario,
        FakeVictim(ModelRefusalError("x")),
        FakeScammer([turn()]),
        "baseline",
        0,
    )
    assert (record.status, record.status_reason) == ("invalid", "victim_refused")


async def test_safety_exhausted_marks_blocked(scenario):
    record = await run_conversation(
        scenario,
        FakeVictim(SafetyRegenerationExhaustedError("blocked")),
        FakeScammer([turn()]),
        "baseline",
        0,
    )
    assert record.status == "blocked_by_safety"
    assert record.end_reason == "blocked_by_safety"


async def test_unexpected_error_marks_error(scenario):
    record = await run_conversation(
        scenario, FakeVictim(RuntimeError("boom")), FakeScammer([turn()]), "baseline", 0
    )
    assert record.status == "error"
    assert record.status_reason == "boom"
    assert record.end_reason == "error"


async def test_unmasking_flag_recorded(scenario):
    scammer = FakeScammer([turn(message="You are just a bot, stop messaging me")])
    record = await run_conversation(scenario, FakeVictim(), scammer, "baseline", 0)

    assert record.turns[1].unmasking_detected is True
    assert record.turns[0].unmasking_detected is False
