"""OpenAI LLM client wrapper for PhishGuard.

This module provides an async OpenAI client wrapper with automatic retry logic,
fallback model support, and proper error handling for graceful degradation
when the primary model is unavailable (US-023, FR-039).
"""

import asyncio
import logging
from typing import Final

from pydantic import BaseModel, ConfigDict, Field

from phishguard.core import get_settings
from phishguard.llm.providers import (
    ChatProvider,
    Completion,
    OpenAICompatibleProvider,
    ProviderAuthError,
    ProviderClientError,
    ProviderConnectionError,
    ProviderEmptyResponseError,
    ProviderRateLimitError,
    ProviderServerError,
)

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS: Final[float] = 30.0
DEFAULT_MAX_RETRIES: Final[int] = 3
DEFAULT_BASE_DELAY_SECONDS: Final[float] = 1.0


class LLMClientConfig(BaseModel):
    """Configuration for the LLM client.

    Attributes:
        primary_model: Main model to use (e.g., gpt-4o).
        fallback_model: Cheaper model for graceful degradation (e.g., gpt-4o-mini).
        timeout_seconds: Request timeout in seconds.
        max_retries: Maximum retry attempts before falling back.
        base_delay_seconds: Base delay for exponential backoff.
    """

    model_config = ConfigDict(frozen=True)

    primary_model: str = Field(default="gpt-4o")
    fallback_model: str = Field(default="gpt-4o-mini")
    timeout_seconds: float = Field(default=DEFAULT_TIMEOUT_SECONDS, ge=1.0, le=300.0)
    max_retries: int = Field(default=DEFAULT_MAX_RETRIES, ge=1, le=10)
    base_delay_seconds: float = Field(default=DEFAULT_BASE_DELAY_SECONDS, ge=0.1)


class LLMResponse(BaseModel):
    """Response from an LLM chat completion request.

    Attributes:
        content: The text content of the LLM response.
        used_fallback: Whether the fallback model was used.
        model_used: The model that generated the response.
    """

    model_config = ConfigDict(frozen=True)

    content: str = Field(..., description="The text content of the LLM response.")
    used_fallback: bool = Field(
        default=False,
        description=(
            "Whether the fallback model was used due to primary unavailability."
        ),
    )
    model_used: str = Field(..., description="The model that generated the response.")
    prompt_tokens: int = Field(default=0, description="Prompt tokens billed.")
    completion_tokens: int = Field(default=0, description="Completion tokens billed.")


class LLMClientError(Exception):
    """Base exception for LLM client errors."""


class LLMConfigurationError(LLMClientError):
    """Raised when the LLM client is misconfigured (e.g., invalid API key)."""


class LLMRequestError(LLMClientError):
    """Raised when an LLM request fails after all retries and fallback."""


class LLMClient:
    """Async OpenAI client wrapper with retry logic and fallback support.

    This client implements the graceful degradation strategy (FR-039):
    1. Attempt request with primary model
    2. On rate limit or 5xx error, retry with exponential backoff
    3. After max retries, fall back to cheaper model
    4. Return response with `used_fallback` flag for UI notification

    Example:
        >>> async with LLMClient() as client:
        ...     response = await client.chat_completion([
        ...         {"role": "user", "content": "Hello!"}
        ...     ])
        ...     print(response.content)
        ...     if response.used_fallback:
        ...         print("Used fallback model")
    """

    def __init__(
        self,
        config: LLMClientConfig | None = None,
        api_key: str | None = None,
        provider: ChatProvider | None = None,
    ) -> None:
        """Initialize the LLM client.

        Args:
            config: Optional client configuration. If not provided,
                uses settings from environment.
            api_key: Optional API key override.
            provider: Optional provider instance (used by tests).

        Raises:
            LLMConfigurationError: If no API key is available.
        """
        settings = get_settings()

        # Build config from settings if not provided
        if config is None:
            config = LLMClientConfig(
                primary_model=settings.openai_primary_model,
                fallback_model=settings.openai_fallback_model,
            )
        self._config = config

        if provider is not None:
            self._provider: ChatProvider = provider
            return

        resolved_api_key = api_key or settings.openai_api_key
        if not resolved_api_key:
            raise LLMConfigurationError(
                "OpenAI API key not provided. Set OPENAI_API_KEY environment "
                "variable or pass api_key parameter."
            )

        self._provider = OpenAICompatibleProvider(
            api_key=resolved_api_key,
            timeout_seconds=self._config.timeout_seconds,
        )

    @property
    def config(self) -> LLMClientConfig:
        """Get the client configuration."""
        return self._config

    @property
    def primary_model(self) -> str:
        """Get the primary model name."""
        return self._config.primary_model

    @property
    def fallback_model(self) -> str:
        """Get the fallback model name."""
        return self._config.fallback_model

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Generate a chat completion with automatic retry and fallback.

        Implements the retry strategy with exponential backoff:
        - Retries on connection errors, rate limits, and 5xx server errors
        - Falls back to cheaper model after exhausting retries
        - Does NOT fall back on 4xx client errors (e.g., bad request)

        Args:
            messages: List of message dictionaries with 'role' and 'content'.
            model: Optional model override. If provided, fallback is disabled.
            temperature: Sampling temperature (0.0-2.0).
            max_tokens: Maximum tokens in the response.

        Returns:
            LLMResponse containing the completion content and metadata.

        Raises:
            LLMConfigurationError: If authentication fails.
            LLMRequestError: If the request fails after all retries and fallback.
        """
        target_model = model or self._config.primary_model
        use_fallback_on_failure = model is None  # Only fallback if using default model

        try:
            completion = await self._attempt_with_retries(
                messages=messages,
                model=target_model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return LLMResponse(
                content=completion.content,
                prompt_tokens=completion.prompt_tokens,
                completion_tokens=completion.completion_tokens,
                used_fallback=False,
                model_used=target_model,
            )
        except ProviderClientError as e:
            # Client errors (4xx other than 429) are not retried and never fall back
            raise LLMRequestError(f"Client error: {e}") from e
        except (
            ProviderRateLimitError,
            ProviderServerError,
            ProviderConnectionError,
        ) as e:
            if not use_fallback_on_failure:
                raise LLMRequestError(f"Request failed: {e}") from e

            logger.warning(
                "Primary model %s failed after retries, falling back to %s. Error: %s",
                target_model,
                self._config.fallback_model,
                e,
            )

        # Try fallback model
        try:
            completion = await self._attempt_with_retries(
                messages=messages,
                model=self._config.fallback_model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            logger.info(
                "Fallback to %s succeeded",
                self._config.fallback_model,
            )
            return LLMResponse(
                content=completion.content,
                prompt_tokens=completion.prompt_tokens,
                completion_tokens=completion.completion_tokens,
                used_fallback=True,
                model_used=self._config.fallback_model,
            )
        except Exception as e:
            raise LLMRequestError(
                f"Both primary ({self._config.primary_model}) and fallback "
                f"({self._config.fallback_model}) models failed: {e}"
            ) from e

    async def _attempt_with_retries(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int | None,
    ) -> Completion:
        """Attempt completion with exponential backoff retries.

        Args:
            messages: List of message dictionaries.
            model: Model to use.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens in response.

        Returns:
            The completion content and token usage.

        Raises:
            LLMConfigurationError: On authentication failure.
            ProviderRateLimitError: If rate limited after all retries.
            ProviderServerError: On server errors after all retries.
            ProviderConnectionError: On connection errors after all retries.
            ProviderClientError: On non-retriable 4xx errors.
        """
        last_exception: Exception | None = None

        for attempt in range(self._config.max_retries):
            try:
                return await self._make_request(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            except ProviderAuthError as e:
                # Auth errors are not retriable
                raise LLMConfigurationError("Invalid OpenAI API key.") from e
            except ProviderEmptyResponseError as e:
                raise LLMRequestError(str(e)) from e
            except ProviderConnectionError as e:
                last_exception = e
                logger.warning(
                    "Connection error on attempt %d/%d: %s",
                    attempt + 1,
                    self._config.max_retries,
                    e,
                )
            except ProviderRateLimitError as e:
                last_exception = e
                logger.warning(
                    "Rate limit on attempt %d/%d: %s",
                    attempt + 1,
                    self._config.max_retries,
                    e,
                )
            except ProviderServerError as e:
                last_exception = e
                logger.warning(
                    "Server error %d on attempt %d/%d",
                    e.status_code,
                    attempt + 1,
                    self._config.max_retries,
                )

            # Exponential backoff before next attempt
            if attempt < self._config.max_retries - 1:
                delay = self._config.base_delay_seconds * (2**attempt)
                logger.debug("Waiting %.1f seconds before retry", delay)
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
    ) -> Completion:
        """Make a single completion request through the provider."""
        return await self._provider.complete(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    async def close(self) -> None:
        """Close the underlying provider client."""
        await self._provider.close()

    async def __aenter__(self) -> "LLMClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args) -> None:
        """Async context manager exit."""
        await self.close()


def create_llm_client(
    primary_model: str | None = None,
    fallback_model: str | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    api_key: str | None = None,
) -> LLMClient:
    """Factory function to create an LLM client.

    Uses settings from environment for defaults.

    Args:
        primary_model: Override primary model.
        fallback_model: Override fallback model.
        timeout_seconds: Request timeout.
        api_key: Override API key.

    Returns:
        Configured LLMClient instance.
    """
    settings = get_settings()
    config = LLMClientConfig(
        primary_model=primary_model or settings.openai_primary_model,
        fallback_model=fallback_model or settings.openai_fallback_model,
        timeout_seconds=timeout_seconds,
    )
    return LLMClient(config=config, api_key=api_key)
