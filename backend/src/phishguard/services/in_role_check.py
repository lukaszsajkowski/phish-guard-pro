"""Basal in-role check for generated replies (US-050).

Flags a reply that breaks the persona's role. The result is advisory only:
it never blocks or rewrites a reply, and any failure yields no warning.
"""

import logging

from phishguard.agents.prompts.in_role_basal import (
    IN_ROLE_CRITERIA,
    IN_ROLE_INSTRUCTIONS,
)
from phishguard.decisions import (
    ChoiceQuestion,
    DecisionService,
    create_decision_service,
)
from phishguard.models.in_role import IN_ROLE_WARNING_MESSAGE, InRoleWarning
from phishguard.models.persona import PersonaProfile

logger = logging.getLogger(__name__)

IN_ROLE_NODE = "response.in_role"

_service: DecisionService | None = None


def _get_service() -> DecisionService:
    """Return the process-wide in-role decision service, built on first use."""
    global _service
    if _service is None:
        _service = create_decision_service(node=IN_ROLE_NODE)
    return _service


def build_in_role_state(persona: PersonaProfile, content: str) -> str:
    """Build the text Basal judges: persona type, age, style and the reply.

    The persona's name and background are deliberately left out.
    """
    return (
        f"{persona.persona_type.display_name}, age {persona.age}\n"
        f"{persona.style_description}\n"
        "\n"
        f"Reply:\n{content}"
    )


async def check_in_role(
    persona: PersonaProfile,
    content: str,
    session_id: str,
    message_id: str,
    service: DecisionService | None = None,
) -> InRoleWarning | None:
    """Return a warning when Basal says the reply breaks the persona's role.

    Never raises: any failure is logged and treated as no warning.
    """
    try:
        service = service or _get_service()
        question = ChoiceQuestion(
            node=IN_ROLE_NODE,
            instructions=IN_ROLE_INSTRUCTIONS,
            criteria=IN_ROLE_CRITERIA,
        )
        decision = await service.decide_signal(
            question,
            build_in_role_state(persona, content),
            session_id=session_id,
            message_id=message_id,
            reference_kind=None,
            reference_answer=None,
        )
        if (
            decision.source == "basal"
            and decision.answer == "breaks_role"
            and decision.basal is not None
        ):
            return InRoleWarning(
                message=IN_ROLE_WARNING_MESSAGE,
                confidence=decision.basal.confidence,
            )
    except Exception:
        logger.warning("In-role check failed", exc_info=True)
    return None
