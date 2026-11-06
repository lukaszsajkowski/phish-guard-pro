"""Follow-up turns must answer the latest scammer message, not the first email."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from phishguard.core import get_settings
from phishguard.llm import LLMResponse

ORIGINAL = "ORIGINAL EMAIL TEXT"
NEW = "NEW SCAMMER TEXT"
_REPLY = (
    '{"thinking": {"turn_goal": "g", "selected_tactic": "t", "reasoning": "r"},'
    ' "response": "Oh my, tell me more."}'
)


@pytest.fixture(autouse=True)
def _basal_off(monkeypatch):
    monkeypatch.setenv("BASAL_URL", "")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _base_state(history):
    return {
        "session_id": None,
        "email_content": ORIGINAL,
        "scammer_message": NEW,
        "conversation_history": history,
        "persona": {
            "persona_type": "naive_retiree",
            "name": "Jane Doe",
            "age": 70,
            "style_description": "polite",
            "background": "retired teacher",
        },
        "classification": {"attack_type": "nigerian_419", "confidence": 90.0},
    }


def _fake_client():
    client = MagicMock()
    client.chat_completion = AsyncMock(
        return_value=LLMResponse(content=_REPLY, model_used="fake")
    )
    return client


def _user_prompt(client) -> str:
    messages = client.chat_completion.call_args.kwargs["messages"]
    return next(m["content"] for m in messages if m["role"] == "user")


def _block(prompt: str, tag: str) -> str:
    return prompt.split(f"<{tag}>")[1].split(f"</{tag}>")[0]


async def _run_follow_up():
    from phishguard.orchestrator.graph import create_continuation_graph

    client = _fake_client()
    history = [
        {"sender": "scammer", "content": "Earlier scammer note"},
        {"sender": "bot", "content": "Oh my, who are you?"},
    ]
    with patch("phishguard.agents.conversation.create_llm_client", return_value=client):
        await create_continuation_graph().ainvoke(_base_state(history))
    return _user_prompt(client)


@pytest.mark.asyncio
async def test_follow_up_prompt_shows_latest_scammer_message():
    prompt = await _run_follow_up()

    block = _block(prompt, "SCAMMER_MESSAGE")
    assert NEW in block
    assert ORIGINAL not in block


@pytest.mark.asyncio
async def test_follow_up_history_does_not_duplicate_latest_message():
    prompt = await _run_follow_up()

    assert prompt.count(NEW) == 1
    assert NEW not in _block(prompt, "CONVERSATION_HISTORY")


@pytest.mark.asyncio
async def test_first_response_still_uses_original_email():
    from phishguard.orchestrator.nodes import generate_response

    client = _fake_client()
    state = _base_state([])
    state["scammer_message"] = None
    with patch("phishguard.agents.conversation.create_llm_client", return_value=client):
        await generate_response(state)

    prompt = _user_prompt(client)
    assert ORIGINAL in _block(prompt, "SCAMMER_EMAIL")
    assert "<SCAMMER_MESSAGE>" not in prompt
