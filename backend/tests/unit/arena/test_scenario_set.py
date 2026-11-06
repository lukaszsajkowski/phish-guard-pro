"""Checks that the shipped Arena scenario set matches the spec."""

from collections import Counter
from pathlib import Path

import pytest

from phishguard.arena.scenario import Scenario, load_scenarios
from phishguard.models.classification import AttackType

SCENARIO_DIR = Path(__file__).resolve().parents[4] / "evals" / "scenarios"

EXPECTED_EN = {
    f"en-{t}-{d}"
    for t in (
        "nigerian_419",
        "ceo_fraud",
        "fake_invoice",
        "romance_scam",
        "tech_support",
        "lottery_prize",
        "crypto_investment",
        "credential_phishing",
    )
    for d in ("easy", "hard")
}
EXPECTED_PL = {
    f"pl-{k}-{d}"
    for k in ("parcel", "blik", "transfer", "crypto")
    for d in ("easy", "hard")
}


@pytest.fixture(scope="module")
def scenarios() -> list[Scenario]:
    return load_scenarios(SCENARIO_DIR)


def test_scenario_set_matches_spec(scenarios: list[Scenario]) -> None:
    # Arrange
    en = [s for s in scenarios if s.language == "en"]
    pl = [s for s in scenarios if s.language == "pl"]

    # Assert counts and ids
    assert len(scenarios) == 24
    assert len(en) == 16
    assert len(pl) == 8
    assert {s.id for s in scenarios} == EXPECTED_EN | EXPECTED_PL

    # Every English attack type appears exactly twice: once easy, once hard
    per_type = Counter((s.attack_type, s.difficulty) for s in en)
    expected_types = {t for t in AttackType if t != AttackType.NOT_PHISHING}
    english_types = {s.attack_type for s in en}
    assert len(english_types) == 8
    assert english_types <= expected_types
    for attack_type in english_types:
        assert per_type[(attack_type, "easy")] == 1
        assert per_type[(attack_type, "hard")] == 1

    # Secret type coverage
    secret_types = Counter(t for s in scenarios for t in {x.type for x in s.secrets})
    for secret_type in ("iban", "btc_wallet", "url", "phone"):
        assert secret_types[secret_type] >= 4, secret_type
    assert secret_types["iban"] >= 12

    # Hard scammers are written to be suspicious or wary (Polish stems for pl)
    markers = {
        "en": ("suspicious", "wary"),
        "pl": ("podejrzliw", "nieufn", "ostrożn"),
    }
    for s in scenarios:
        if s.difficulty == "hard":
            text = s.scammer.lower()
            assert any(m in text for m in markers[s.language]), s.id
