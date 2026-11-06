"""LLM client module for PhishGuard.

This module provides the LLM client with automatic retry logic
and fallback model support for graceful degradation (US-023, FR-039).
"""

from phishguard.llm.client import (
    DEFAULT_TIMEOUT_SECONDS,
    PROVIDER_DEFAULT_MODELS,
    LLMClient,
    LLMClientConfig,
    LLMClientError,
    LLMConfigurationError,
    LLMRequestError,
    LLMResponse,
    create_llm_client,
)
from phishguard.llm.usage import UsageEntry, UsageLog, track_usage

__all__ = [
    "LLMClient",
    "LLMClientConfig",
    "LLMClientError",
    "LLMConfigurationError",
    "LLMRequestError",
    "LLMResponse",
    "PROVIDER_DEFAULT_MODELS",
    "UsageEntry",
    "UsageLog",
    "track_usage",
    "create_llm_client",
    "DEFAULT_TIMEOUT_SECONDS",
]
