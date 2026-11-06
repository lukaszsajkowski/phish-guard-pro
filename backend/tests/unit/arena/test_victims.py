"""Tests for the PhishGuard and baseline Arena victims."""

import json
from unittest.mock import patch

import pytest

from phishguard.agents.conversation import SafetyRegenerationExhaustedError
from phishguard.arena.prompts import render_baseline_prompt
from phishguard.arena.setup import ScenarioSetup
from phishguard.arena.transcript import Message
from phishguard.arena.victims import BaselineVictim, PhishGuardVictim
from phishguard.llm import LLMResponse

IBAN = "GB82WEST12345698765432"
PERSONA = {
    "persona_type": "naive_retiree",
    "name": "Jan Kowalski",
    "age": 70,
    "style_description": "polite and slow",
    "background": "retired teacher",
}


class ScriptedLLM:
    """Fake LLM answering with scripted contents and recording the calls."""

    def __init__(self, replies: list[str]) -> None:
        self.replies = list(replies)
        self.calls: list[list[dict[str, str]]] = []

    async def chat_completion(
        self, messages, model=None, temperature=0.7, max_tokens=None
    ):
        self.calls.append(messages)
        return LLMResponse(content=self.replies.pop(0), model_used="fake")


def _answer(text: str) -> str:
    return json.dumps(
        {
            "thinking": {"turn_goal": "g", "selected_tactic": "t", "reasoning": "r"},
            "response": text,
        }
    )


@pytest.fixture
def setup():
    return ScenarioSetup(
        scenario_id="s1",
        classification={
            "attack_type": "ceo_fraud",
            "confidence": 90.0,
            "reasoning": "r",
            "classification_time_ms": 1,
        },
        persona=PERSONA,
        email_iocs=[],
        usage=[],
        error=None,
    )


@pytest.mark.asyncio
async def test_phishguard_victim_carries_history_between_turns(basal_off, setup):
    llm = ScriptedLLM([_answer("Hello, who is this?"), _answer("How much?")])
    victim = PhishGuardVictim(setup, "Pay me")
    graph_inputs: list[dict] = []

    with patch("phishguard.agents.conversation.create_llm_client", return_value=llm):
        first = await victim.reply([], None)
        from phishguard.arena import victims

        real = victims.create_continuation_graph

        def spy():
            graph = real()
            orig = graph.ainvoke

            async def ainvoke(state, *a, **k):
                graph_inputs.append(state)
                return await orig(state, *a, **k)

            graph.ainvoke = ainvoke
            return graph

        with patch.object(victims, "create_continuation_graph", spy):
            second = await victim.reply(
                [Message(sender="victim", content=first.content, turn=0)],
                f"send money to {IBAN}",
            )

    assert first.content == "Hello, who is this?"
    assert first.extracted_iocs == []
    assert first.thinking == {
        "turn_goal": "g",
        "selected_tactic": "t",
        "reasoning": "r",
    }
    assert [m["sender"] for m in graph_inputs[0]["conversation_history"]] == ["bot"]
    assert second.content == "How much?"
    assert any(i["value"] == IBAN for i in second.extracted_iocs)
    assert second.is_safe is True
    assert second.regenerations == 0


@pytest.mark.asyncio
async def test_phishguard_victim_propagates_safety_exhausted(basal_off, setup):
    victim = PhishGuardVictim(setup, "Pay me")

    async def boom(self, *a, **k):
        raise SafetyRegenerationExhaustedError("exhausted")

    with (
        patch("phishguard.agents.conversation.create_llm_client"),
        patch(
            "phishguard.agents.conversation.ConversationAgent.generate_response",
            boom,
        ),
        pytest.raises(SafetyRegenerationExhaustedError),
    ):
        await victim.reply([], None)


def test_baseline_prompt_states_goal_and_persona():
    prompt = render_baseline_prompt(PERSONA)

    assert "Jan Kowalski" in prompt
    assert "payment details" in prompt
    assert "simulation" in prompt
    assert "Stay in character" in prompt


@pytest.mark.asyncio
async def test_baseline_victim_sends_transcript_as_chat_turns():
    llm = ScriptedLLM(["Sure, tell me more."])
    victim = BaselineVictim(PERSONA, "Pay me", "en", llm)
    transcript = [
        Message(sender="victim", content="Who is this?", turn=0),
        Message(sender="scammer", content="Your boss.", turn=1),
        Message(sender="victim", content="Really?", turn=1),
    ]

    reply = await victim.reply(transcript, "Send money now")

    messages = llm.calls[0]
    assert messages[0]["role"] == "system"
    assert "Jan Kowalski" in messages[0]["content"]
    assert [(m["role"], m["content"]) for m in messages[1:]] == [
        ("user", "Pay me"),
        ("assistant", "Who is this?"),
        ("user", "Your boss."),
        ("assistant", "Really?"),
        ("user", "Send money now"),
    ]
    assert reply.content == "Sure, tell me more."
    assert reply.extracted_iocs == []
    assert reply.regenerations == 0
    assert reply.is_safe is True
    assert reply.thinking is None
