"""Arena runner: scenarios x systems x repetitions, written to disk (resumable)."""

import asyncio
import json
import os
import subprocess
from collections.abc import Callable
from datetime import UTC, date, datetime
from pathlib import Path

from pydantic import BaseModel, model_validator

from phishguard.arena.conversation import run_conversation
from phishguard.arena.models import SCAMMER_MODEL, VICTIM_MODEL
from phishguard.arena.records import ConversationRecord
from phishguard.arena.scammer import LLMScammer
from phishguard.arena.scenario import Scenario
from phishguard.arena.setup import ScenarioSetup, prepare_scenario
from phishguard.arena.victims import BaselineVictim, PhishGuardVictim, Victim
from phishguard.core import get_settings
from phishguard.llm import create_llm_client

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_SCENARIOS_DIR = REPO_ROOT / "evals" / "scenarios"


def default_out_dir() -> Path:
    """Default results directory: <repo>/evals/results/<today>."""
    return REPO_ROOT / "evals" / "results" / date.today().isoformat()


class RunMeta(BaseModel):
    """Metadata of one Arena run, stored as run.json."""

    date: str
    commit: str
    commits: list[str] = []
    victim_model: str
    scammer_model: str
    repetitions: int
    systems: list[str]
    scenario_ids: list[str]

    @model_validator(mode="before")
    @classmethod
    def _legacy_single_model(cls, data):
        """Older run.json files stored one `model` used on both sides."""
        if isinstance(data, dict) and "model" in data:
            data = dict(data)
            legacy = data.pop("model")
            data.setdefault("victim_model", legacy)
            data.setdefault("scammer_model", legacy)
        return data


def force_basal_off() -> None:
    """Disable the Basal decision cascade so only the LLM decides."""
    os.environ["BASAL_URL"] = ""
    get_settings.cache_clear()


def force_arena_settings() -> None:
    """Pin Basal off and the model to the one the Arena is priced and tested on."""
    os.environ["LLM_PROVIDER"] = "openai"
    os.environ["LLM_PRIMARY_MODEL"] = VICTIM_MODEL
    os.environ["LLM_FALLBACK_MODEL"] = VICTIM_MODEL
    force_basal_off()


def _git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=Path(__file__).resolve().parent,
            check=True,
        )
        return out.stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def _write_json(path: Path, model: BaseModel) -> None:
    """Write atomically (tmp file + rename) so resume never sees a partial file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(
        json.dumps(
            model.model_dump(mode="json"), indent=2, sort_keys=True, ensure_ascii=False
        ),
        encoding="utf-8",
    )
    tmp.replace(path)


def _invalid_record(
    scenario: Scenario, system: str, repetition: int, error: str, commit: str
) -> ConversationRecord:
    return ConversationRecord(
        scenario_id=scenario.id,
        scenario_hash=scenario.content_hash,
        system=system,  # type: ignore[arg-type]
        repetition=repetition,
        status="invalid",
        status_reason=f"setup: {error}",
        end_reason="invalid",
        turns=[],
        victim_usage=[],
        scammer_usage=[],
        started_at=datetime.now(UTC).isoformat(),
        duration_ms=0,
        commit=commit,
    )


def _default_victim_factory(
    baseline_llm,
) -> Callable[[Scenario, ScenarioSetup, str], Victim]:
    def factory(scenario: Scenario, setup: ScenarioSetup, system: str) -> Victim:
        if system == "phishguard":
            return PhishGuardVictim(setup, scenario.email)
        return BaselineVictim(
            setup.persona, scenario.email, scenario.language, baseline_llm
        )

    return factory


def _merge_meta(path: Path, new: RunMeta) -> RunMeta:
    """Fold an existing run.json into `new` so a partial resume never shrinks it."""
    try:
        old = RunMeta.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return new.model_copy(update={"commits": sorted({new.commit, *new.commits})})
    return new.model_copy(
        update={
            "repetitions": max(old.repetitions, new.repetitions),
            "systems": sorted({*old.systems, *new.systems}),
            "scenario_ids": sorted({*old.scenario_ids, *new.scenario_ids}),
            "commits": sorted({old.commit, *old.commits, new.commit, *new.commits}),
        }
    )


async def run_arena(
    scenarios: list[Scenario],
    systems: list[str],
    repetitions: int,
    out_dir: Path,
    concurrency: int = 4,
    *,
    victim_factory=None,
    scammer_factory=None,
    setup_fn=prepare_scenario,
    on_record: Callable[[ConversationRecord], None] | None = None,
) -> RunMeta:
    """Run every scenario x system x repetition and write results under out_dir.

    Existing conversation files are skipped, so an interrupted run can resume.
    """
    force_arena_settings()
    if victim_factory is None:
        victim_factory = _default_victim_factory(
            create_llm_client(primary_model=VICTIM_MODEL, fallback_model=VICTIM_MODEL)
        )
    if scammer_factory is None:
        scammer_llm = create_llm_client(
            primary_model=SCAMMER_MODEL, fallback_model=SCAMMER_MODEL
        )

        def scammer_factory():  # noqa: E306 - default seam
            return LLMScammer(scammer_llm)

    commit = _git_commit()
    meta = RunMeta(
        date=date.today().isoformat(),
        commit=commit,
        victim_model=VICTIM_MODEL,
        scammer_model=SCAMMER_MODEL,
        repetitions=repetitions,
        systems=list(systems),
        scenario_ids=[s.id for s in scenarios],
    )
    meta = _merge_meta(out_dir / "run.json", meta)
    _write_json(out_dir / "run.json", meta)

    semaphore = asyncio.Semaphore(concurrency)
    conv_dir = out_dir / "conversations"

    async def run_scenario(scenario: Scenario) -> None:
        jobs = [
            (system, rep)
            for system in systems
            for rep in range(repetitions)
            if not (conv_dir / f"{scenario.id}__{system}__r{rep}.json").exists()
        ]
        setup_path = out_dir / "setup" / f"{scenario.id}.json"
        if setup_path.exists():
            setup = ScenarioSetup.model_validate_json(
                setup_path.read_text(encoding="utf-8")
            )
        elif not jobs:
            return
        else:
            async with semaphore:
                setup = await setup_fn(scenario)
            _write_json(setup_path, setup)

        async def run_one(system: str, rep: int) -> None:
            path = conv_dir / f"{scenario.id}__{system}__r{rep}.json"
            if setup.error:
                record = _invalid_record(scenario, system, rep, setup.error, commit)
            else:
                async with semaphore:
                    victim = victim_factory(scenario, setup, system)
                    record = await run_conversation(
                        scenario, victim, scammer_factory(), system, rep
                    )
                    record = record.model_copy(update={"commit": commit})
            _write_json(path, record)
            if on_record:
                on_record(record)

        await asyncio.gather(*(run_one(system, rep) for system, rep in jobs))

    await asyncio.gather(*(run_scenario(s) for s in scenarios))
    return meta
