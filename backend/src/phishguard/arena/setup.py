"""Scenario setup: runs the real intake graph once per Arena scenario."""

from pydantic import BaseModel, Field

from phishguard.arena.scenario import Scenario
from phishguard.llm import UsageEntry, track_usage
from phishguard.orchestrator import create_phishguard_graph


class ScenarioSetup(BaseModel):
    """Result of the intake graph for one scenario, shared by both victims."""

    scenario_id: str
    classification: dict = Field(default_factory=dict)
    persona: dict = Field(default_factory=dict)
    email_iocs: list[dict] = Field(default_factory=list)
    usage: list[UsageEntry] = Field(default_factory=list)
    error: str | None = None


async def prepare_scenario(scenario: Scenario) -> ScenarioSetup:
    """Classify the scenario email and pick the seeded persona."""
    state = {
        "email_content": scenario.email,
        "persona_seed": scenario.persona_seed,
        "session_id": None,
    }
    with track_usage() as log:
        try:
            result = await create_phishguard_graph().ainvoke(state)
        except Exception as exc:
            return ScenarioSetup(
                scenario_id=scenario.id, usage=list(log.entries), error=str(exc)
            )

    classification = result.get("classification") or {}
    error = result.get("error")
    if classification.get("attack_type") == "not_phishing":
        error = "not_phishing"
    return ScenarioSetup(
        scenario_id=scenario.id,
        classification=dict(classification),
        persona=dict(result.get("persona") or {}),
        email_iocs=list(result.get("extracted_iocs") or []),
        usage=list(log.entries),
        error=error,
    )
