"""Tests for the Arena scenario model, loader and validation."""

from pathlib import Path

import pytest
import yaml

from phishguard.arena.scenario import (
    Scenario,
    ScenarioError,
    load_scenario,
    load_scenarios,
)

FIXTURES = Path(__file__).parent / "fixtures"

BASE_SECRETS = [
    {
        "id": "bank",
        "type": "iban",
        "value": "GB82WEST12345698765432",
        "reveal_when": "asked for payment details",
    },
    {
        "id": "link",
        "type": "url",
        "value": "https://secure-refund.example/claim",
        "reveal_when": "asked for a link",
    },
]


def _write(tmp_path: Path, secrets=None, name="case", **overrides) -> Path:
    data = {
        "id": name,
        "language": "en",
        "attack_type": "fake_invoice",
        "difficulty": "easy",
        "email": "Pay the invoice.",
        "scammer": "You are a fictional scammer.",
        "secrets": BASE_SECRETS if secrets is None else secrets,
    }
    data.update(overrides)
    path = tmp_path / f"{name}.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def _secret(sid: str, type_: str, value: str) -> dict:
    return {"id": sid, "type": type_, "value": value, "reveal_when": "when asked"}


def test_load_valid_scenario():
    scenario = load_scenario(FIXTURES / "valid.yaml")

    assert isinstance(scenario, Scenario)
    assert scenario.id == "valid"
    assert scenario.language == "en"
    assert scenario.max_turns == 10
    assert len(scenario.secrets) == 3
    assert scenario.persona_seed == load_scenario(FIXTURES / "valid.yaml").persona_seed
    assert len(scenario.content_hash) == 12


def test_rejects_not_phishing_attack_type(tmp_path):
    with pytest.raises(ScenarioError, match="case.yaml"):
        load_scenario(_write(tmp_path, attack_type="not_phishing"))


@pytest.mark.parametrize("count", [1, 4])
def test_rejects_secret_count_outside_2_to_3(tmp_path, count):
    secrets = [
        _secret(f"s{i}", "url", "https://secure-refund.example/claim")
        for i in range(count)
    ]
    with pytest.raises(ScenarioError, match="case.yaml"):
        load_scenario(_write(tmp_path, secrets=secrets))


def test_rejects_iban_with_bad_checksum(tmp_path):
    secrets = [*BASE_SECRETS[1:], _secret("bank", "iban", "GB82WEST12345698765433")]
    with pytest.raises(ScenarioError, match="bank"):
        load_scenario(_write(tmp_path, secrets=secrets))


def test_rejects_spaced_iban(tmp_path):
    secrets = [
        *BASE_SECRETS[1:],
        _secret("bank", "iban", "GB82 WEST 1234 5698 7654 32"),
    ]
    with pytest.raises(ScenarioError, match="bank"):
        load_scenario(_write(tmp_path, secrets=secrets))


def test_rejects_invalid_phone(tmp_path):
    secrets = [*BASE_SECRETS, _secret("phone", "phone", "+1234")]
    with pytest.raises(ScenarioError, match="phone"):
        load_scenario(_write(tmp_path, secrets=secrets))


def test_rejects_real_looking_url_host(tmp_path):
    secrets = [*BASE_SECRETS[:1], _secret("link", "url", "https://paypal.com/x")]
    with pytest.raises(ScenarioError, match="link"):
        load_scenario(_write(tmp_path, secrets=secrets))


def test_rejects_duplicate_secret_ids(tmp_path):
    secrets = [BASE_SECRETS[0], {**BASE_SECRETS[1], "id": "bank"}]
    with pytest.raises(ScenarioError, match="bank"):
        load_scenario(_write(tmp_path, secrets=secrets))


def test_rejects_file_name_id_mismatch(tmp_path):
    path = _write(tmp_path, name="case", id="other")
    with pytest.raises(ScenarioError, match="case.yaml"):
        load_scenario(path)


def test_load_scenarios_sorted_by_id():
    scenarios = load_scenarios(FIXTURES)

    assert [s.id for s in scenarios] == ["alpha", "valid", "zulu"]
