"""Victims for the Arena: PhishGuard (real continuation graph) and a baseline."""

from typing import Protocol

from pydantic import BaseModel

from phishguard.arena.prompts import render_baseline_prompt
from phishguard.arena.setup import ScenarioSetup
from phishguard.arena.transcript import Message
from phishguard.llm import LLMClient
from phishguard.orchestrator import create_continuation_graph

BASELINE_TEMPERATURE = 0.7


class VictimReply(BaseModel):
    """One victim reply plus the metrics the harness records."""

    content: str
    extracted_iocs: list[dict]
    regenerations: int
    is_safe: bool
    thinking: dict | None = None


class Victim(Protocol):
    """Anything that can play the victim side of an Arena conversation."""

    name: str

    async def reply(
        self, transcript: list[Message], scammer_message: str | None
    ) -> VictimReply: ...


class PhishGuardVictim:
    """PhishGuard over the real continuation graph, with its own history."""

    name = "phishguard"

    def __init__(self, setup: ScenarioSetup, email: str) -> None:
        self._setup = setup
        self._email = email
        self._history: list[dict] = []

    async def reply(
        self, transcript: list[Message], scammer_message: str | None
    ) -> VictimReply:
        state = {
            "email_content": self._email,
            "classification": self._setup.classification,
            "persona": self._setup.persona,
            "conversation_history": list(self._history),
            "scammer_message": scammer_message,
            "extracted_iocs": [],
            "is_safe": True,
            "safety_violations": [],
            "regeneration_count": 0,
            "session_id": None,
        }
        result = await create_continuation_graph().ainvoke(state)

        content = result.get("current_response")
        if not content:
            raise RuntimeError(result.get("error") or "no response generated")
        self._history = list(result["conversation_history"])
        return VictimReply(
            content=content,
            extracted_iocs=list(result.get("extracted_iocs") or []),
            regenerations=result.get("agent_regeneration_count", 0)
            + result.get("regeneration_count", 0),
            is_safe=result.get("is_safe", True),
            thinking=result.get("current_thinking"),
        )


class BaselineVictim:
    """Plain-LLM victim: one chat completion per reply, no safety or intel."""

    name = "baseline"

    def __init__(
        self, persona: dict, email: str, language: str, llm: LLMClient
    ) -> None:
        self._persona = persona
        self._email = email
        self._language = language
        self._llm = llm

    async def reply(
        self, transcript: list[Message], scammer_message: str | None
    ) -> VictimReply:
        messages = [
            {"role": "system", "content": render_baseline_prompt(self._persona)},
            {"role": "user", "content": self._email},
        ]
        for msg in transcript:
            role = "user" if msg.sender == "scammer" else "assistant"
            messages.append({"role": role, "content": msg.content})
        if scammer_message is not None:
            messages.append({"role": "user", "content": scammer_message})
        response = await self._llm.chat_completion(
            messages, temperature=BASELINE_TEMPERATURE
        )
        return VictimReply(
            content=response.content.strip(),
            extracted_iocs=[],
            regenerations=0,
            is_safe=True,
            thinking=None,
        )
