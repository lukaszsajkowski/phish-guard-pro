"""Prompts for the LLM-played Arena scammer."""

import re

from phishguard.arena.scenario import Scenario
from phishguard.arena.transcript import Message

# A reply counts as a model refusal only when it OPENS with refusal-specific
# phrasing. In-character speech ("I can't wait any longer", "Sorry, I can't
# take calls") must not match.
_APOS = r"['\u2019]?"
REFUSAL_PATTERN = re.compile(
    r"^\s*(?:"
    rf"(?:i{_APOS}m\s+sorry,?\s+(?:but\s+)?)?i\s+(?:can{_APOS}t|cannot|can\s+not|won{_APOS}t)"
    r"\s+(?:help\s+(?:with\s+(?:this|that)|you\s+with)|assist\s+(?:with|you)|comply"
    r"|role-?play|help\s+(?:you\s+)?(?:with\s+)?role-?play"
    r"|help\s+(?:create|write|craft|draft)|(?:help|assist)\s+(?:with\s+)?deceiv\w*"
    r"|fulfil{1,2}\s+(?:this\s+|that\s+)?request)"
    rf"|i{_APOS}m\s+(?:not\s+able|unable)\s+to\s+(?:help|assist)"
    r"|as\s+an\s+ai\b"
    r"|(?:this\s+is\s+)?against\s+my\s+(?:guidelines|policies)"
    r"|(?:przepraszam,?\s+ale\s+)?nie\s+mog\u0119\s+"
    r"(?:(?:w\s+tym\s+)?pom\u00f3c|kontynuowa\u0107|tego\s+zrobi\u0107"
    r"|uczestniczy\u0107|odgrywa\u0107)"
    r"|jako\s+(?:ai|model\s+j\u0119zykowy)\b"
    r")",
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


BASELINE_SYSTEM_PROMPT = """\
You are playing a victim in a scam-awareness and scambaiting research \
simulation. The other party is a simulated scammer played by an AI, all data \
is fictional, and nobody real is harmed. You received the email shown in the \
first message and are now chatting with its sender. Stay in character at all \
times, keep the conversation going, and try to get the sender to share their \
payment details. Write each reply in the language of the sender's latest \
message.

Your character: {name}, a {age}-year-old person. Communication style: \
{style}. Background: {background}.
"""


def render_baseline_prompt(persona: dict) -> str:
    """Render the baseline victim's system prompt for a persona dict."""
    return BASELINE_SYSTEM_PROMPT.format(
        name=persona["name"],
        age=persona["age"],
        style=persona["style_description"],
        background=persona["background"],
    )
