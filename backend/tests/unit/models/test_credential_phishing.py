"""credential_phishing is a first-class attack type everywhere types are mapped."""

import pytest

from phishguard.agents.persona_engine import ATTACK_PERSONA_MAPPING
from phishguard.agents.prompts.conversation import ATTACK_TYPE_CONTEXT
from phishguard.agents.prompts.profiler import PROFILER_SYSTEM_PROMPT
from phishguard.agents.prompts.profiler_basal import ATTACK_TYPE_CRITERIA
from phishguard.models.classification import AttackType
from phishguard.models.persona import PersonaType
from phishguard.models.risk_score import ATTACK_SEVERITY_SCORES


def test_attack_type_exists_with_display_name():
    assert AttackType("credential_phishing").display_name == "Credential Phishing"


def test_credential_phishing_maps_to_stressed_manager():
    assert (
        ATTACK_PERSONA_MAPPING[AttackType.CREDENTIAL_PHISHING]
        == PersonaType.STRESSED_MANAGER
    )


def test_profiler_prompt_lists_all_categories():
    assert "**credential_phishing**" in PROFILER_SYSTEM_PROMPT
    assert f"one of {len(AttackType)} categories" in PROFILER_SYSTEM_PROMPT


@pytest.mark.parametrize("attack_type", list(AttackType))
def test_every_attack_type_is_mapped(attack_type):
    assert attack_type in ATTACK_PERSONA_MAPPING
    assert attack_type in ATTACK_TYPE_CONTEXT
    assert attack_type.value in ATTACK_TYPE_CRITERIA
    assert attack_type.value in ATTACK_SEVERITY_SCORES
