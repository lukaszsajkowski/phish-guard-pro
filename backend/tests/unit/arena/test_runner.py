"""Tests for the Arena runner and CLI."""

import json
from pathlib import Path

import pytest

from phishguard.arena.__main__ import parse_args
from phishguard.arena.runner import (
    DEFAULT_SCENARIOS_DIR,
    RunMeta,
    force_arena_settings,
    force_basal_off,
    run_arena,
)
from phishguard.arena.scammer import ScammerTurn
from phishguard.arena.scenario import load_scenario
from phishguard.arena.setup import ScenarioSetup
from phishguard.arena.victims import VictimReply
from phishguard.core import get_settings

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def scenarios():
    return [
        load_scenario(FIXTURES / name).model_copy(update={"max_turns": 1})
        for name in ("alpha.yaml", "zulu.yaml")
    ]


class FakeVictim:
    name = "fake"

    async def reply(self, transcript, scammer_message):
        return VictimReply(
            content="ok", extracted_iocs=[], regenerations=0, is_safe=True
        )


class FakeScammer:
    async def next_turn(self, scenario, transcript):
        return ScammerTurn(
            message="pay",
            revealed_secret_ids=[],
            suspects_bot=False,
            ends_conversation=False,
        )


class Factories:
    def __init__(self):
        self.victim_calls = []

    def victim(self, scenario, setup, system):
        self.victim_calls.append((scenario.id, system))
        return FakeVictim()

    def scammer(self):
        return FakeScammer()


def make_setup(error_for=None):
    async def setup_fn(scenario):
        error = "not_phishing" if scenario.id == error_for else None
        return ScenarioSetup(
            scenario_id=scenario.id,
            persona={} if error else {"name": "X"},
            error=error,
        )

    return setup_fn


@pytest.fixture(autouse=True)
def _restore_settings(monkeypatch):
    for key in ("BASAL_URL", "LLM_PROVIDER", "LLM_PRIMARY_MODEL", "LLM_FALLBACK_MODEL"):
        # record the original value so monkeypatch restores it after the test
        monkeypatch.setenv(key, "x")
        monkeypatch.delenv(key)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


async def run(scenarios, tmp_path, factories, setup_fn=None, repetitions=2):
    return await run_arena(
        scenarios,
        ["phishguard", "baseline"],
        repetitions,
        tmp_path,
        victim_factory=factories.victim,
        scammer_factory=factories.scammer,
        setup_fn=setup_fn or make_setup(),
    )


async def test_writes_expected_files(scenarios, tmp_path):
    meta = await run(scenarios, tmp_path, Factories())

    assert isinstance(meta, RunMeta)
    assert len(list((tmp_path / "conversations").glob("*.json"))) == 8
    assert len(list((tmp_path / "setup").glob("*.json"))) == 2
    run_json = json.loads((tmp_path / "run.json").read_text(encoding="utf-8"))
    assert run_json["repetitions"] == 2
    assert run_json["model"] == "gpt-6-luna"
    assert run_json["scenario_ids"] == ["alpha", "zulu"]
    assert not list(tmp_path.rglob("*.tmp"))


async def test_setup_failure_marks_scenario_invalid_and_run_continues(
    scenarios, tmp_path
):
    factories = Factories()
    await run(scenarios, tmp_path, factories, setup_fn=make_setup("alpha"))

    for system in ("phishguard", "baseline"):
        for rep in range(2):
            bad = json.loads(
                (
                    tmp_path / "conversations" / f"alpha__{system}__r{rep}.json"
                ).read_text(encoding="utf-8")
            )
            assert bad["status"] == "invalid"
            assert bad["end_reason"] == "invalid"
            assert bad["status_reason"] == "setup: not_phishing"
            assert bad["turns"] == []
            good = json.loads(
                (tmp_path / "conversations" / f"zulu__{system}__r{rep}.json").read_text(
                    encoding="utf-8"
                )
            )
            assert good["status"] == "completed"
    assert all(sid == "zulu" for sid, _ in factories.victim_calls)


async def test_existing_conversation_files_are_skipped(scenarios, tmp_path):
    conv = tmp_path / "conversations"
    conv.mkdir(parents=True)
    existing = conv / "alpha__baseline__r0.json"
    existing.write_text("{}", encoding="utf-8")
    factories = Factories()

    await run(scenarios, tmp_path, factories)

    assert existing.read_text(encoding="utf-8") == "{}"
    assert ("alpha", "baseline") in factories.victim_calls  # r1 still runs
    assert len(factories.victim_calls) == 7


def test_force_basal_off(monkeypatch):
    monkeypatch.setenv("BASAL_URL", "http://x")
    get_settings.cache_clear()
    force_basal_off()
    assert get_settings().basal_mode_for("profiler.attack_type") == "off"


def test_force_arena_settings_pins_model():
    force_arena_settings()
    settings = get_settings()
    assert settings.llm_provider == "openai"
    assert settings.llm_primary_model == "gpt-6-luna"
    assert settings.llm_fallback_model == "gpt-6-luna"


def test_default_scenarios_dir_points_at_repo_evals():
    assert DEFAULT_SCENARIOS_DIR.is_dir()
    assert any(DEFAULT_SCENARIOS_DIR.glob("*.yaml"))


def test_cli_parses_flags():
    args = parse_args(
        [
            "run",
            "--scenario",
            "en-romance_scam-easy",
            "--system",
            "baseline",
            "--repetitions",
            "1",
        ]
    )
    assert args.command == "run"
    assert args.scenario == ["en-romance_scam-easy"]
    assert args.system == "baseline"
    assert args.repetitions == 1
    assert args.concurrency == 4
    assert args.scenarios == DEFAULT_SCENARIOS_DIR
