"""Tests for Arena scenario setup (real intake graph, fake LLM)."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from phishguard.arena.scenario import load_scenario
from phishguard.arena.setup import prepare_scenario
from phishguard.llm import LLMClient, LLMClientConfig
from phishguard.llm.providers import Completion

SCENARIOS = Path(__file__).resolve().parents[4] / "evals" / "scenarios"


class FakeProvider:
    def __init__(self, attack_type: str) -> None:
        self.attack_type = attack_type

    async def complete(self, messages, model, temperature, max_tokens):
        content = json.dumps(
            {"attack_type": self.attack_type, "confidence": 90, "reasoning": "r"}
        )
        return Completion(content, 10, 5)

    async def close(self) -> None:
        return None


def _client(attack_type: str) -> LLMClient:
    return LLMClient(LLMClientConfig(), api_key="x", provider=FakeProvider(attack_type))


@pytest.fixture
def scenario():
    return load_scenario(SCENARIOS / "en-ceo_fraud-easy.yaml")


@pytest.mark.asyncio
async def test_prepare_scenario_returns_seeded_persona(basal_off, scenario):
    with patch(
        "phishguard.agents.profiler.create_llm_client",
        side_effect=lambda: _client("ceo_fraud"),
    ):
        first = await prepare_scenario(scenario)
        second = await prepare_scenario(scenario)

    assert first.error is None
    assert first.scenario_id == scenario.id
    assert first.classification["attack_type"] == "ceo_fraud"
    assert first.persona["name"]
    assert first.persona == second.persona
    assert len(first.usage) >= 1


@pytest.mark.asyncio
async def test_prepare_scenario_not_phishing_sets_error(basal_off, scenario):
    with patch(
        "phishguard.agents.profiler.create_llm_client",
        side_effect=lambda: _client("not_phishing"),
    ):
        setup = await prepare_scenario(scenario)

    assert setup.error == "not_phishing"


@pytest.mark.asyncio
async def test_prepare_scenario_exception_sets_error(basal_off, scenario):
    def boom():
        raise RuntimeError("no llm")

    with patch("phishguard.agents.profiler.create_llm_client", side_effect=boom):
        setup = await prepare_scenario(scenario)

    assert setup.error == "no llm"
