"""OpenAI LLM client wrapper for PhishGuard.

This module provides an async OpenAI client wrapper with automatic retry logic,
fallback model support, and proper error handling.
"""

import asyncio
import logging
import os
from typing import Final

from openai import (
    APIConnectionError,
    AsyncOpenAI,
    AuthenticationError,
    RateLimitError,
)
from openai._exceptions import APIStatusError
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

DEFAULT_PRIMARY_MODEL: Final[str] = "gpt-4o"
DEFAULT_FALLBACK_MODEL: Final[str] = "gpt-4o-mini"
DEFAULT_TIMEOUT_SECONDS: Final[float] = 30.0
DEFAULT_MAX_RETRIES: Final[int] = 3
DEFAULT_BASE_DELAY_SECONDS: Final[float] = 1.0


class LLMClientConfig(BaseModel):
    """Configuration for the LLM client."""

    model_config = ConfigDict(frozen=True)

    primary_model: str = Field(default=DEFAULT_PRIMARY_MODEL)
    fallback_model: str = Field(default=DEFAULT_FALLBACK_MODEL)
    timeout_seconds: float = Field(default=DEFAULT_TIMEOUT_SECONDS, ge=1.0, le=300.0)
    max_retries: int = Field(default=DEFAULT_MAX_RETRIES, ge=1, le=10)
    base_delay_seconds: float = Field(default=DEFAULT_BASE_DELAY_SECONDS, ge=0.1)


class LLMResponse(BaseModel):
    """Response from an LLM chat completion request."""

    model_config = ConfigDict(frozen=True)

    content: str = Field(..., description="The text content of the LLM response.")
    used_fallback: bool = Field(default=False)
    model_used: str = Field(..., description="The model that generated the response.")


class LLMClientError(Exception):
    """Base exception for LLM client errors."""


class LLMConfigurationError(LLMClientError):
    """Raised when the LLM client is misconfigured."""


class LLMRequestError(LLMClientError):
    """Raised when an LLM request fails after all retries."""


class LLMClient:
    """Async OpenAI client wrapper with retry logic and fallback support."""

    def __init__(
        self,
        config: LLMClientConfig | None = None,
        api_key: str | None = None,
    ) -> None:
        """Initialize the LLM client.

        Args:
            config: Optional client configuration.
            api_key: Optional API key. Falls back to OPENAI_API_KEY env var.

        Raises:
            LLMConfigurationError: If no API key is available.
        """
        self._config = config or LLMClientConfig()

        resolved_api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not resolved_api_key:
            raise LLMConfigurationError(
                "OpenAI API key not provided. Set OPENAI_API_KEY environment "
                "variable or pass api_key parameter."
            )

        self._client = AsyncOpenAI(
            api_key=resolved_api_key,
            timeout=self._config.timeout_seconds,
        )

    @property
    def config(self) -> LLMClientConfig:
        """Get the client configuration."""
        return self._config

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Generate a chat completion with automatic retry and fallback.

        Args:
            messages: List of message dictionaries with 'role' and 'content'.
            model: Optional model override.
            temperature: Sampling temperature (0.0-2.0).
            max_tokens: Maximum tokens in the response.

        Returns:
            LLMResponse containing the completion content and metadata.

        Raises:
            LLMConfigurationError: If authentication fails.
            LLMRequestError: If the request fails after all retries.
        """
        target_model = model or self._config.primary_model
        use_fallback_on_failure = target_model == self._config.primary_model

        try:
            content = await self._attempt_with_retries(
                messages=messages,
                model=target_model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return LLMResponse(
                content=content,
                used_fallback=False,
                model_used=target_model,
            )
        except (RateLimitError, APIStatusError) as e:
            if not use_fallback_on_failure:
                raise LLMRequestError(f"Request failed: {e}") from e

            if isinstance(e, APIStatusError) and e.status_code < 500:
                raise LLMRequestError(f"Client error: {e}") from e

            logger.warning(
                "Primary model %s failed, falling back to %s",
                target_model,
                self._config.fallback_model,
            )

        try:
            content = await self._attempt_with_retries(
                messages=messages,
                model=self._config.fallback_model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return LLMResponse(
                content=content,
                used_fallback=True,
                model_used=self._config.fallback_model,
            )
        except Exception as e:
            raise LLMRequestError(f"Both models failed: {e}") from e

    async def _attempt_with_retries(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int | None,
    ) -> str:
        """Attempt completion with exponential backoff retries."""
        last_exception: Exception | None = None

        for attempt in range(self._config.max_retries):
            try:
                return await self._make_request(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            except AuthenticationError as e:
                raise LLMConfigurationError("Invalid OpenAI API key.") from e
            except APIConnectionError as e:
                last_exception = e
                logger.warning("Connection error attempt %d: %s", attempt + 1, e)
            except RateLimitError as e:
                last_exception = e
                logger.warning("Rate limit attempt %d: %s", attempt + 1, e)
            except APIStatusError as e:
                if e.status_code >= 500:
                    last_exception = e
                    logger.warning(
                        "Server error %d attempt %d", e.status_code, attempt + 1
                    )
                else:
                    raise

            if attempt < self._config.max_retries - 1:
                delay = self._config.base_delay_seconds * (2**attempt)
                await asyncio.sleep(delay)

        if last_exception:
            raise last_exception
        raise LLMRequestError("All retry attempts failed")

    async def _make_request(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int | None,
    ) -> str:
        """Make a single completion request."""
        kwargs: dict = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens

        response = await self._client.chat.completions.create(**kwargs)

        if not response.choices:
            raise LLMRequestError("No completion choices returned")

        content = response.choices[0].message.content
        if content is None:
            raise LLMRequestError("Completion returned None content")

        return content

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.close()

    async def __aenter__(self) -> "LLMClient":
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()


def create_llm_client(
    primary_model: str = DEFAULT_PRIMARY_MODEL,
    fallback_model: str = DEFAULT_FALLBACK_MODEL,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    api_key: str | None = None,
) -> LLMClient:
    """Factory function to create an LLM client."""
    config = LLMClientConfig(
        primary_model=primary_model,
        fallback_model=fallback_model,
        timeout_seconds=timeout_seconds,
    )
    return LLMClient(config=config, api_key=api_key)
