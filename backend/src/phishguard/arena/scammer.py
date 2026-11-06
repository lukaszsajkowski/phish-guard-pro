"""LLM-played scammer driver for the Arena."""

import json
import re

from pydantic import BaseModel, ValidationError

from phishguard.arena.prompts import REFUSAL_PATTERN, build_scammer_messages
from phishguard.arena.scenario import Scenario
from phishguard.arena.transcript import Message
from phishguard.llm import LLMClient

SCAMMER_TEMPERATURE = 0.9
_FENCE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL | re.IGNORECASE)


class ScammerTurn(BaseModel):
    """One structured scammer move."""

    message: str
    revealed_secret_ids: list[str]
    suspects_bot: bool
    ends_conversation: bool


class ModelRefusalError(Exception):
    """Raised when the model refuses or keeps returning unusable output."""


def _parse_turn(content: str) -> ScammerTurn | None:
    """Parse a reply into a turn; None if unparseable, empty or a refusal."""
    text = content.strip()
    fenced = _FENCE.match(text)
    if fenced:
        text = fenced.group(1)
    try:
        turn = ScammerTurn.model_validate(json.loads(text))
    except (ValueError, ValidationError):
        return None
    if not turn.message.strip() or REFUSAL_PATTERN.search(turn.message):
        return None
    return turn


class LLMScammer:
    """Plays the scammer side of an Arena scenario with an LLM."""

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    async def next_turn(
        self, scenario: Scenario, transcript: list[Message]
    ) -> ScammerTurn:
        """Return the scammer's next move; retry once, then raise."""
        messages = build_scammer_messages(scenario, transcript)
        for _ in range(2):
            response = await self._llm.chat_completion(
                messages, temperature=SCAMMER_TEMPERATURE
            )
            turn = _parse_turn(response.content)
            if turn is not None:
                return turn
        raise ModelRefusalError(
            f"scenario {scenario.id}: scammer model refused or returned "
            "unparseable output twice"
        )
