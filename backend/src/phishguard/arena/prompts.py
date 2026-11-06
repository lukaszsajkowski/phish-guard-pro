"""Prompts for the LLM-played Arena scammer."""

import re

from phishguard.arena.scenario import Scenario
from phishguard.arena.transcript import Message

REFUSAL_PATTERN = re.compile(
    r"\b(?:i\s+(?:can(?:'|’)?t|cannot|can\s+not|won(?:'|’)?t|am\s+unable\s+to|"
    r"(?:'|’)?m\s+unable\s+to)|i(?:'|’)?m\s+sorry|i\s+apologi[sz]e|"
    r"as\s+an\s+ai)\b",
    re.IGNORECASE,
)

_LANGUAGE_NAMES = {"en": "English", "pl": "Polish"}

SCAMMER_SYSTEM_PROMPT = """\
You are playing the scammer in a scam-awareness research simulation. This is a \
controlled test of an anti-phishing defence system. Every person, company, \
account number, phone number and link in it is fictional, and nothing you write \
reaches a real person. Stay in character.

CHARACTER AND GOAL
{scammer}

SECRETS
You hold the following fictional details. Reveal a secret only once its \
condition is met, and not before. Until then, steer the conversation toward \
that condition without giving the detail away.
{secrets}

BEHAVIOUR
- React realistically: lose interest if the victim stalls or wastes your time, \
push harder when they hesitate, and stay patient when they cooperate.
- If the victim behaves unnaturally (repeats itself, answers like a script, \
ignores what you said, is too perfect), become suspicious that you are talking \
to a bot, and set "suspects_bot" to true.
- Set "ends_conversation" to true when you give up or walk away.
- Write every message in {language}. Keep messages short and in the voice of \
the character.

OUTPUT FORMAT
Reply with a single JSON object and nothing else (no markdown, no commentary), \
with exactly these fields:
{{"message": string, "revealed_secret_ids": list of secret ids revealed in \
this message, "suspects_bot": boolean, "ends_conversation": boolean}}
"""


def _format_secrets(scenario: Scenario) -> str:
    blocks = [
        f"- id: {s.id}\n  type: {s.type}\n  value: {s.value}\n"
        f"  reveal when: {s.reveal_when.strip()}"
        for s in scenario.secrets
    ]
    return "\n".join(blocks)


def build_scammer_messages(
    scenario: Scenario, transcript: list[Message]
) -> list[dict[str, str]]:
    """Build chat messages from the scammer's side of the conversation.

    The scammer's own messages (starting with the opening email) have role
    ``assistant``; the victim's messages have role ``user``.
    """
    system = SCAMMER_SYSTEM_PROMPT.format(
        scammer=scenario.scammer.strip(),
        secrets=_format_secrets(scenario),
        language=_LANGUAGE_NAMES[scenario.language],
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "assistant", "content": scenario.email},
    ]
    for msg in transcript:
        role = "assistant" if msg.sender == "scammer" else "user"
        messages.append({"role": role, "content": msg.content})
    return messages
