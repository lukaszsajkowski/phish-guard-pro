"""LLM provider adapters behind LLMClient.

Each adapter talks to one SDK and translates its errors into the
provider-neutral exceptions below, so LLMClient's retry and fallback
logic does not depend on any vendor SDK.
"""

import logging
from typing import NamedTuple, Protocol

import anthropic
from openai import (
    APIConnectionError,
    APIStatusError,
    AsyncOpenAI,
    AuthenticationError,
    BadRequestError,
    RateLimitError,
)

logger = logging.getLogger(__name__)


class Completion(NamedTuple):
    """Content and token usage of a single completion."""

    content: str
    prompt_tokens: int
    completion_tokens: int


class ProviderError(Exception):
    """Base class for provider-neutral LLM errors."""


class ProviderAuthError(ProviderError):
    """The provider rejected the credentials."""


class ProviderRateLimitError(ProviderError):
    """The provider rate-limited the request (HTTP 429)."""


class ProviderConnectionError(ProviderError):
    """The provider could not be reached."""


class ProviderServerError(ProviderError):
    """The provider failed with a 5xx status."""

    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


class ProviderClientError(ProviderError):
    """The provider rejected the request with a non-retriable 4xx status."""

    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


class ProviderEmptyResponseError(ProviderError):
    """The provider returned no usable content."""


class ChatProvider(Protocol):
    """A chat-completion backend used by LLMClient."""

    async def complete(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int | None,
    ) -> Completion: ...

    async def close(self) -> None: ...


def _int_or_zero(value: object) -> int:
    return value if isinstance(value, int) else 0


def _is_temperature_rejection(error: BadRequestError) -> bool:
    body = error.body if isinstance(error.body, dict) else {}
    details = body.get("error", body) if isinstance(body, dict) else {}
    param = details.get("param") if isinstance(details, dict) else None
    return param == "temperature" or "temperature" in str(error).lower()


class OpenAICompatibleProvider:
    """OpenAI Chat Completions API, also used for OpenAI-compatible servers
    such as Ollama (via ``base_url``)."""

    def __init__(
        self,
        api_key: str,
        timeout_seconds: float,
        base_url: str | None = None,
    ) -> None:
        self._client = AsyncOpenAI(
            api_key=api_key, timeout=timeout_seconds, base_url=base_url
        )
        self._no_temperature_models: set[str] = set()

    async def complete(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int | None,
    ) -> Completion:
        kwargs: dict = {"model": model, "messages": messages}
        if model not in self._no_temperature_models:
            kwargs["temperature"] = temperature
        if max_tokens is not None:
            kwargs["max_completion_tokens"] = max_tokens

        try:
            try:
                response = await self._client.chat.completions.create(**kwargs)
            except BadRequestError as e:
                if "temperature" not in kwargs or not _is_temperature_rejection(e):
                    raise
                logger.info("Model %s rejects temperature; omitting it", model)
                self._no_temperature_models.add(model)
                kwargs.pop("temperature")
                response = await self._client.chat.completions.create(**kwargs)
        except AuthenticationError as e:
            raise ProviderAuthError(str(e)) from e
        except RateLimitError as e:
            raise ProviderRateLimitError(str(e)) from e
        except APIConnectionError as e:
            raise ProviderConnectionError(str(e)) from e
        except APIStatusError as e:
            if e.status_code >= 500:
                raise ProviderServerError(str(e), e.status_code) from e
            raise ProviderClientError(str(e), e.status_code) from e

        if not response.choices:
            raise ProviderEmptyResponseError("No completion choices returned")
        content = response.choices[0].message.content
        if content is None:
            raise ProviderEmptyResponseError("Completion returned None content")

        usage = getattr(response, "usage", None)
        return Completion(
            content=content,
            prompt_tokens=_int_or_zero(getattr(usage, "prompt_tokens", 0)),
            completion_tokens=_int_or_zero(getattr(usage, "completion_tokens", 0)),
        )

    async def close(self) -> None:
        await self._client.close()


ANTHROPIC_DEFAULT_MAX_TOKENS = 1024

# Ollama ignores the key, but the OpenAI SDK requires a non-empty one.
OLLAMA_PLACEHOLDER_API_KEY = "ollama"


class AnthropicProvider:
    """Anthropic Messages API.

    System messages are moved to the ``system`` parameter. ``temperature``
    is not sent: the Messages API in the current SDK no longer accepts it.
    """

    def __init__(self, api_key: str, timeout_seconds: float) -> None:
        self._client = anthropic.AsyncAnthropic(
            api_key=api_key, timeout=timeout_seconds
        )

    async def complete(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int | None,
    ) -> Completion:
        system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
        chat = [
            {"role": m["role"], "content": m["content"]}
            for m in messages
            if m["role"] != "system"
        ]
        kwargs: dict = {
            "model": model,
            "messages": chat,
            "max_tokens": max_tokens or ANTHROPIC_DEFAULT_MAX_TOKENS,
        }
        if system:
            kwargs["system"] = system

        a = anthropic
        try:
            response = await self._client.messages.create(**kwargs)
        except a.AuthenticationError as e:
            raise ProviderAuthError(str(e)) from e
        except a.RateLimitError as e:
            raise ProviderRateLimitError(str(e)) from e
        except a.APIConnectionError as e:
            raise ProviderConnectionError(str(e)) from e
        except a.APIStatusError as e:
            if e.status_code >= 500:
                raise ProviderServerError(str(e), e.status_code) from e
            raise ProviderClientError(str(e), e.status_code) from e

        content = "".join(
            block.text for block in response.content if block.type == "text"
        )
        if not content:
            raise ProviderEmptyResponseError("Completion returned no text content")
        usage = getattr(response, "usage", None)
        return Completion(
            content=content,
            prompt_tokens=_int_or_zero(getattr(usage, "input_tokens", 0)),
            completion_tokens=_int_or_zero(getattr(usage, "output_tokens", 0)),
        )

    async def close(self) -> None:
        await self._client.close()


def build_provider(
    provider: str,
    api_key: str,
    timeout_seconds: float,
    ollama_base_url: str,
) -> ChatProvider:
    """Create the adapter for a configured provider name."""
    if provider == "anthropic":
        return AnthropicProvider(api_key=api_key, timeout_seconds=timeout_seconds)
    if provider == "ollama":
        return OpenAICompatibleProvider(
            api_key=api_key or OLLAMA_PLACEHOLDER_API_KEY,
            timeout_seconds=timeout_seconds,
            base_url=ollama_base_url,
        )
    return OpenAICompatibleProvider(api_key=api_key, timeout_seconds=timeout_seconds)
