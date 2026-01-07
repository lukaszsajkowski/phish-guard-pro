"""LLM client module for PhishGuard.

This module provides the LLM client with automatic retry logic
and fallback model support for graceful degradation (US-023, FR-039).
"""

from phishguard.llm.client import (
    DEFAULT_TIMEOUT_SECONDS,
    LLMClient,
    LLMClientConfig,
    LLMClientError,
    LLMConfigurationError,
    LLMRequestError,
    LLMResponse,
    create_llm_client,
)

__all__ = [
    "LLMClient",
    "LLMClientConfig",
    "LLMClientError",
    "LLMConfigurationError",
    "LLMRequestError",
    "LLMResponse",
    "create_llm_client",
    "DEFAULT_TIMEOUT_SECONDS",
]
