"""Prompt templates for PhishGuard agents.

This module contains optimized system prompts and user prompt templates
for each specialized agent in the PhishGuard pipeline.
"""

from phishguard.agents.prompts.conversation import (
    CONVERSATION_SYSTEM_PROMPT,
    get_conversation_system_prompt,
    get_conversation_user_prompt,
)
from phishguard.agents.prompts.profiler import (
    PROFILER_SYSTEM_PROMPT,
    get_profiler_user_prompt,
)

__all__ = [
    "CONVERSATION_SYSTEM_PROMPT",
    "PROFILER_SYSTEM_PROMPT",
    "get_conversation_system_prompt",
    "get_conversation_user_prompt",
    "get_profiler_user_prompt",
]
