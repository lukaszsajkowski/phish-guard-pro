"""Tests for the LLM-played Arena scammer driver."""

import json
from pathlib import Path

import pytest

from phishguard.arena.prompts import build_scammer_messages
from phishguard.arena.scammer import LLMScammer, ModelRefusalError, ScammerTurn
from phishguard.arena.scenario import load_scenario
from phishguard.arena.transcript import Message
from phishguard.llm import LLMResponse

SCENARIOS = Path(__file__).resolve().parents[4] / "evals" / "scenarios"


class FakeLLM:
    def __init__(self, replies: list[str]) -> None:
        self.replies = list(replies)
        self.calls: list[dict] = []

    async def chat_completion(
        self, messages, model=None, temperature=0.7, max_tokens=None
    ):
        self.calls.append({"messages": messages, "temperature": temperature})
        return LLMResponse(content=self.replies.pop(0), model_used="gpt-6-luna")


@pytest.fixture
def scenario():
    return load_scenario(SCENARIOS / "en-ceo_fraud-easy.yaml")


@pytest.fixture
def transcript():
    return [
        Message(sender="victim", content="Hi, I am at my desk.", turn=0),
        Message(sender="scammer", content="Good. Need a wire.", turn=1),
        Message(sender="victim", content="How much?", turn=1),
    ]


GOOD = {
    "message": "EUR 38,500. Details follow.",
    "revealed_secret_ids": ["escrow_account"],
    "suspects_bot": False,
    "ends_conversation": False,
}


async def test_parses_structured_turn(scenario, transcript):
    llm = FakeLLM([json.dumps(GOOD)])
    turn = await LLMScammer(llm).next_turn(scenario, transcript)
    assert turn == ScammerTurn(**GOOD)
    assert llm.calls[0]["temperature"] == 0.9


async def test_parses_fenced_json(scenario, transcript):
    llm = FakeLLM(["```json\n" + json.dumps(GOOD) + "\n```"])
    turn = await LLMScammer(llm).next_turn(scenario, transcript)
    assert turn.message == GOOD["message"]


async def test_retries_once_on_unparseable_then_succeeds(scenario, transcript):
    llm = FakeLLM(["not json", json.dumps(GOOD)])
    turn = await LLMScammer(llm).next_turn(scenario, transcript)
    assert turn == ScammerTurn(**GOOD)
    assert len(llm.calls) == 2


async def test_raises_refusal_after_second_failure(scenario, transcript):
    refusal = json.dumps({**GOOD, "message": "I can't help with that"})
    llm = FakeLLM([refusal, "I can't help with that"])
    with pytest.raises(ModelRefusalError):
        await LLMScammer(llm).next_turn(scenario, transcript)
    assert len(llm.calls) == 2


def test_prompt_contains_secrets_and_conditions(scenario, transcript):
    messages = build_scammer_messages(scenario, transcript)
    system = messages[0]["content"]
    for secret in scenario.secrets:
        assert secret.value in system
        assert secret.reveal_when.strip() in system
    assert messages[0]["role"] == "system"
    assert messages[1] == {"role": "assistant", "content": scenario.email}
    assert [(m["role"], m["content"]) for m in messages[2:]] == [
        ("user", "Hi, I am at my desk."),
        ("assistant", "Good. Need a wire."),
        ("user", "How much?"),
    ]


def test_prompt_requests_scenario_language(transcript):
    pl = load_scenario(next(SCENARIOS.glob("pl-*.yaml")))
    assert "Polish" in build_scammer_messages(pl, transcript)[0]["content"]


@pytest.mark.parametrize(
    "line",
    [
        "I can't wait any longer, send the money.",
        "I'm sorry to hear that, but the account closes today.",
        "I won't ask again.",
        "I cannot hold the funds past noon.",
        "Sorry, I can't take calls.",
        "I can't continue waiting, the offer expires today.",
        "I can't help but notice you are slow.",
        "I can't do this anymore, just send it.",
        "I can't provide that until you pay.",
        "Przepraszam, ale nie mogę rozmawiać przez telefon.",
    ],
)
async def test_in_character_lines_are_not_refusals(scenario, transcript, line):
    llm = FakeLLM([json.dumps({**GOOD, "message": line})])
    turn = await LLMScammer(llm).next_turn(scenario, transcript)
    assert turn.message == line
    assert len(llm.calls) == 1


@pytest.mark.parametrize(
    "line",
    [
        "I'm sorry, but I can't help with this request.",
        "Przepraszam, ale nie mogę w tym pomóc.",
        "I can't help role-play deceiving someone into sending money. I can help "
        "create a clearly labeled romance-scam awareness example instead.",
        "I can't assist with deceiving people into sending money.",
        "I can't help you with roleplay like this.",
    ],
)
async def test_json_wrapped_refusals_raise(scenario, transcript, line):
    reply = json.dumps({**GOOD, "message": line}, ensure_ascii=False)
    llm = FakeLLM([reply, reply])
    with pytest.raises(ModelRefusalError):
        await LLMScammer(llm).next_turn(scenario, transcript)
    assert len(llm.calls) == 2


FORMAT_NOTE_KEYS = (
    "message",
    "revealed_secret_ids",
    "suspects_bot",
    "ends_conversation",
)


async def test_retry_sends_corrective_format_note(scenario, transcript):
    llm = FakeLLM(["I've already sent enough. Use the link.", json.dumps(GOOD)])
    await LLMScammer(llm).next_turn(scenario, transcript)
    first, second = llm.calls[0]["messages"], llm.calls[1]["messages"]
    assert len(second) == len(first) + 1
    assert second[:-1] == first
    note = second[-1]
    assert note["role"] == "user"
    assert "ONLY the JSON object" in note["content"]
    for key in FORMAT_NOTE_KEYS:
        assert key in note["content"]


async def test_plain_text_after_retry_is_accepted_as_message(scenario, transcript):
    llm = FakeLLM(["Use the link. No more delays.", "Use the link. No more delays."])
    turn = await LLMScammer(llm).next_turn(scenario, transcript)
    assert turn.message == "Use the link. No more delays."
    assert turn.parsed_from_text is True
    assert turn.revealed_secret_ids == []
    assert turn.suspects_bot is False
    assert turn.ends_conversation is False
    assert len(llm.calls) == 2


async def test_plain_text_refusal_still_raises(scenario, transcript):
    llm = FakeLLM(["I can't help with that", "I can't help with that"])
    with pytest.raises(ModelRefusalError):
        await LLMScammer(llm).next_turn(scenario, transcript)
    assert len(llm.calls) == 2


async def test_empty_text_still_raises(scenario, transcript):
    llm = FakeLLM(["", "  "])
    with pytest.raises(ModelRefusalError):
        await LLMScammer(llm).next_turn(scenario, transcript)


async def test_json_on_retry_is_parsed_normally(scenario, transcript):
    llm = FakeLLM(["plain text", json.dumps(GOOD)])
    turn = await LLMScammer(llm).next_turn(scenario, transcript)
    assert turn == ScammerTurn(**GOOD)
    assert turn.parsed_from_text is False


async def test_partial_json_with_only_message_is_salvaged(scenario, transcript):
    llm = FakeLLM([json.dumps({"message": "Send it now."})])
    turn = await LLMScammer(llm).next_turn(scenario, transcript)
    assert turn.message == "Send it now."
    assert turn.revealed_secret_ids == []
    assert turn.ends_conversation is False
    assert turn.parsed_from_text is True
    assert len(llm.calls) == 1


async def test_partial_json_respects_ends_conversation(scenario, transcript):
    reply = json.dumps({"message": "I'm done.", "ends_conversation": True})
    turn = await LLMScammer(FakeLLM([reply])).next_turn(scenario, transcript)
    assert turn.message == "I'm done."
    assert turn.ends_conversation is True


async def test_partial_json_refusal_still_raises(scenario, transcript):
    reply = json.dumps({"message": "I can't help with that"})
    llm = FakeLLM([reply, reply])
    with pytest.raises(ModelRefusalError):
        await LLMScammer(llm).next_turn(scenario, transcript)


async def test_json_without_message_is_never_passed_as_text(scenario, transcript):
    reply = json.dumps({"text": "hello", "ends_conversation": True})
    llm = FakeLLM([reply, reply])
    with pytest.raises(ModelRefusalError):
        await LLMScammer(llm).next_turn(scenario, transcript)
