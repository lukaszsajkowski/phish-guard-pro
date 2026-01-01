"""LLM client module for PhishGuard."""

from phishguard.llm.client import (
    DEFAULT_FALLBACK_MODEL,
    DEFAULT_PRIMARY_MODEL,
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
    "DEFAULT_PRIMARY_MODEL",
    "DEFAULT_FALLBACK_MODEL",
    "DEFAULT_TIMEOUT_SECONDS",
]
