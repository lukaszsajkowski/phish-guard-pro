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
    parsed_from_text: bool = False


FORMAT_NOTE = (
    "Reply again with ONLY the JSON object "
    '{"message", "revealed_secret_ids", "suspects_bot", "ends_conversation"} '
    "- no other text. Stay in character."
)


class ModelRefusalError(Exception):
    """Raised when the model refuses or keeps returning unusable output."""


def _strip_fence(content: str) -> str:
    text = content.strip()
    fenced = _FENCE.match(text)
    return fenced.group(1).strip() if fenced else text


def _load_json_turn(content: str) -> ScammerTurn | None:
    """Parse a reply as the JSON turn; None when it is not valid turn JSON."""
    try:
        return ScammerTurn.model_validate(json.loads(_strip_fence(content)))
    except (ValueError, ValidationError):
        return None


def _is_refusal(text: str) -> bool:
    return not text.strip() or bool(REFUSAL_PATTERN.search(text))


class LLMScammer:
    """Plays the scammer side of an Arena scenario with an LLM."""

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    async def next_turn(
        self, scenario: Scenario, transcript: list[Message]
    ) -> ScammerTurn:
        """Return the scammer's next move.

        Retries once with a format reminder. If the model still answers in plain
        text that is not a refusal, that text becomes the message.
        """
        messages = build_scammer_messages(scenario, transcript)
        plain_text: str | None = None
        for attempt in range(2):
            request = (
                messages
                if attempt == 0
                else [*messages, {"role": "user", "content": FORMAT_NOTE}]
            )
            response = await self._llm.chat_completion(
                request, temperature=SCAMMER_TEMPERATURE
            )
            turn = _load_json_turn(response.content)
            if turn is None:
                plain_text = _strip_fence(response.content)
            elif not _is_refusal(turn.message):
                return turn
            else:
                plain_text = None
        if plain_text is not None and not _is_refusal(plain_text):
            return ScammerTurn(
                message=plain_text,
                revealed_secret_ids=[],
                suspects_bot=False,
                ends_conversation=False,
                parsed_from_text=True,
            )
        raise ModelRefusalError(
            f"scenario {scenario.id}: scammer model refused or returned "
            "unusable output twice"
        )
