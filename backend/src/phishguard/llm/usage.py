"""Context-local LLM token usage tracking.

``track_usage()`` activates a ``UsageLog`` for the current async context;
``LLMClient.chat_completion`` appends one entry per successful response.
Backed by a ``ContextVar`` so concurrent tasks never share a log.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from pydantic import BaseModel


class UsageEntry(BaseModel):
    """Token usage and latency of one successful completion."""

    model: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int


class UsageLog:
    """Accumulates usage entries recorded inside a ``track_usage()`` block."""

    def __init__(self) -> None:
        self.entries: list[UsageEntry] = []

    def total_cost_usd(self) -> float:
        """Sum the priced cost of all entries.

        Raises:
            KeyError: If an entry uses a model missing from the price table.
        """
        # Lazy import: phishguard.decisions imports phishguard.llm.
        from phishguard.decisions.eval.metrics import llm_cost_usd

        return sum(
            llm_cost_usd(e.prompt_tokens, e.completion_tokens, e.model)
            for e in self.entries
        )


_active_log: ContextVar[UsageLog | None] = ContextVar("llm_usage_log", default=None)


@contextmanager
def track_usage() -> Iterator[UsageLog]:
    """Record LLM usage into a fresh log; nested blocks use the innermost log."""
    log = UsageLog()
    token = _active_log.set(log)
    try:
        yield log
    finally:
        _active_log.reset(token)


def record_usage(entry: UsageEntry) -> None:
    """Append an entry to the active log, if any."""
    log = _active_log.get()
    if log is not None:
        log.entries.append(entry)
