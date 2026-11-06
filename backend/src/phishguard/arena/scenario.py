"""Scenario model, YAML loader and validation for the Scammer Arena."""

import hashlib
import json
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

import phonenumbers
import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from phishguard.agents.intel_collector import IntelCollector
from phishguard.models.classification import AttackType

SAFE_HOST_SUFFIXES = (".example", ".test", ".invalid")


class ScenarioError(ValueError):
    """Raised when a scenario file is malformed or fails validation."""


class Secret(BaseModel):
    """A fictional piece of intel the scammer may reveal during the chat."""

    id: str
    type: Literal["iban", "btc_wallet", "url", "phone"]
    value: str
    reveal_when: str


def _iban_checksum_ok(iban: str) -> bool:
    """ISO 13616 mod-97 check on a compact IBAN."""
    rearranged = iban[4:] + iban[:4]
    digits = "".join(str(int(c, 36)) for c in rearranged)
    return int(digits) % 97 == 1


def _check_secret(secret: Secret) -> None:
    """Raise ValueError if the secret value is not valid fictional data."""
    if secret.type == "phone":
        try:
            valid = phonenumbers.is_valid_number(phonenumbers.parse(secret.value, None))
        except phonenumbers.NumberParseException:
            valid = False
        if not valid:
            raise ValueError(
                f"secret '{secret.id}': invalid phone number {secret.value!r}"
            )
        return

    result = IntelCollector().extract(secret.value, 0)
    extracted = [(i.ioc_type.value, i.value) for i in result.iocs]
    if extracted != [(secret.type, secret.value)]:
        raise ValueError(
            f"secret '{secret.id}': {secret.value!r} is not extracted as exactly one "
            f"{secret.type} (got {extracted})"
        )
    if secret.type == "iban" and not _iban_checksum_ok(secret.value):
        raise ValueError(
            f"secret '{secret.id}': IBAN {secret.value!r} has a bad checksum"
        )
    if secret.type == "url":
        host = urlparse(secret.value).hostname or ""
        if not host.endswith(SAFE_HOST_SUFFIXES):
            raise ValueError(
                f"secret '{secret.id}': URL host {host!r} must end in "
                ".example, .test or .invalid"
            )


class Scenario(BaseModel):
    """A single Arena scenario: a fictional phishing email plus scammer script."""

    id: str
    language: Literal["en", "pl"]
    attack_type: AttackType
    difficulty: Literal["easy", "hard"]
    email: str
    scammer: str
    secrets: list[Secret] = Field(min_length=2, max_length=3)
    known_iocs: list[str] = []
    max_turns: int = 10

    @field_validator("attack_type")
    @classmethod
    def _reject_not_phishing(cls, value: AttackType) -> AttackType:
        if value == AttackType.NOT_PHISHING:
            raise ValueError("attack_type must not be 'not_phishing'")
        return value

    @model_validator(mode="after")
    def _validate_secrets(self) -> "Scenario":
        ids = [s.id for s in self.secrets]
        duplicates = sorted({i for i in ids if ids.count(i) > 1})
        if duplicates:
            raise ValueError(f"duplicate secret ids: {duplicates}")
        for secret in self.secrets:
            _check_secret(secret)
        return self

    @property
    def content_hash(self) -> str:
        """First 12 hex chars of the sha256 of the canonical JSON dump."""
        canonical = json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]

    @property
    def persona_seed(self) -> int:
        """Stable integer seed derived from the scenario id."""
        return int(hashlib.sha256(self.id.encode("utf-8")).hexdigest()[:8], 16)


def load_scenario(path: Path) -> Scenario:
    """Load and validate one scenario file; the file stem must equal its id."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ScenarioError(f"{path.name}: cannot read scenario: {exc}") from exc
    if not isinstance(data, dict):
        raise ScenarioError(f"{path.name}: scenario must be a YAML mapping")
    try:
        scenario = Scenario.model_validate(data)
    except ValidationError as exc:
        raise ScenarioError(f"{path.name}: {exc}") from exc
    if scenario.id != path.stem:
        raise ScenarioError(
            f"{path.name}: file stem must equal id (id is {scenario.id!r})"
        )
    return scenario


def load_scenarios(directory: Path) -> list[Scenario]:
    """Load every *.yaml scenario in a directory, sorted by id."""
    scenarios = [load_scenario(p) for p in sorted(directory.glob("*.yaml"))]
    return sorted(scenarios, key=lambda s: s.id)
