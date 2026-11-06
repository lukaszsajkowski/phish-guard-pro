"""Detect LLM responses whose token budget was exhausted before any output."""

import logging

from phishguard.llm.client import LLMResponse

logger = logging.getLogger(__name__)


def warn_if_budget_exhausted(
    response: LLMResponse, *, agent: str, max_tokens: int
) -> None:
    """Log a WARNING when a response is empty and hit the completion cap.

    Reasoning models spend hidden reasoning tokens against the same cap as the
    visible output, so a cap that is too low yields empty content.
    """
    if response.content.strip() == "" and response.completion_tokens >= max_tokens:
        logger.warning(
            "%s: response empty: token budget exhausted, likely by reasoning "
            "(model=%s, completion_tokens=%d, max_tokens=%d)",
            agent,
            response.model_used,
            response.completion_tokens,
            max_tokens,
        )
