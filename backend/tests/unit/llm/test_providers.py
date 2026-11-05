"""Unit tests for LLM provider adapters (phase 0, task 0.4)."""

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from openai import (
    APIConnectionError,
    APIStatusError,
    AuthenticationError,
    BadRequestError,
    RateLimitError,
)

from phishguard.llm.providers import (
    Completion,
    OpenAICompatibleProvider,
    ProviderAuthError,
    ProviderClientError,
    ProviderConnectionError,
    ProviderRateLimitError,
    ProviderServerError,
)

MESSAGES = [{"role": "user", "content": "Hello"}]
_REQUEST = httpx.Request("POST", "https://api.example.test/v1/chat/completions")


def _response(status: int) -> httpx.Response:
    return httpx.Response(status, request=_REQUEST)


def _ok(content: str = "Hi") -> MagicMock:
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = content
    resp.usage.prompt_tokens = 3
    resp.usage.completion_tokens = 2
    return resp


def _temperature_rejected() -> BadRequestError:
    return BadRequestError(
        "Unsupported parameter: 'temperature' is not supported with this model.",
        response=_response(400),
        body={
            "error": {
                "message": "Unsupported parameter: 'temperature'",
                "param": "temperature",
                "code": "unsupported_parameter",
            }
        },
    )


@pytest.fixture
def provider() -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(api_key="test-key", timeout_seconds=5.0)


def _mock_create(provider: OpenAICompatibleProvider, **kwargs) -> AsyncMock:
    mock = AsyncMock(**kwargs)
    provider._client.chat.completions.create = mock
    return mock


async def test_openai_returns_completion_with_usage(provider):
    _mock_create(provider, return_value=_ok("Hi"))
    result = await provider.complete(MESSAGES, "gpt-x", 0.7, None)
    assert result == Completion("Hi", 3, 2)


async def test_openai_rate_limit_maps_to_provider_rate_limit(provider):
    _mock_create(
        provider,
        side_effect=RateLimitError("slow down", response=_response(429), body=None),
    )
    with pytest.raises(ProviderRateLimitError):
        await provider.complete(MESSAGES, "gpt-x", 0.7, None)


async def test_openai_5xx_maps_to_server_error(provider):
    _mock_create(
        provider,
        side_effect=APIStatusError("down", response=_response(503), body=None),
    )
    with pytest.raises(ProviderServerError) as exc_info:
        await provider.complete(MESSAGES, "gpt-x", 0.7, None)
    assert exc_info.value.status_code == 503


async def test_openai_4xx_maps_to_client_error(provider):
    _mock_create(
        provider,
        side_effect=BadRequestError("bad", response=_response(400), body=None),
    )
    with pytest.raises(ProviderClientError) as exc_info:
        await provider.complete(MESSAGES, "gpt-x", 0.7, None)
    assert exc_info.value.status_code == 400


async def test_openai_connection_error_maps(provider):
    _mock_create(provider, side_effect=APIConnectionError(request=_REQUEST))
    with pytest.raises(ProviderConnectionError):
        await provider.complete(MESSAGES, "gpt-x", 0.7, None)


async def test_openai_auth_error_maps(provider):
    _mock_create(
        provider,
        side_effect=AuthenticationError("nope", response=_response(401), body=None),
    )
    with pytest.raises(ProviderAuthError):
        await provider.complete(MESSAGES, "gpt-x", 0.7, None)


async def test_temperature_dropped_after_unsupported_error(provider):
    create = _mock_create(provider, side_effect=[_temperature_rejected(), _ok("Hi")])
    result = await provider.complete(MESSAGES, "gpt-reasoning", 0.7, None)
    assert result.content == "Hi"
    assert "temperature" in create.call_args_list[0].kwargs
    assert "temperature" not in create.call_args_list[1].kwargs


async def test_temperature_omission_is_remembered_per_model(provider):
    create = _mock_create(
        provider, side_effect=[_temperature_rejected(), _ok(), _ok(), _ok()]
    )
    await provider.complete(MESSAGES, "gpt-reasoning", 0.7, None)
    await provider.complete(MESSAGES, "gpt-reasoning", 0.7, None)
    await provider.complete(MESSAGES, "gpt-other", 0.7, None)
    assert create.call_count == 4
    assert "temperature" not in create.call_args_list[2].kwargs
    assert create.call_args_list[3].kwargs["temperature"] == 0.7


async def test_max_tokens_sent_as_max_completion_tokens(provider):
    create = _mock_create(provider, return_value=_ok())
    await provider.complete(MESSAGES, "gpt-x", 0.7, 100)
    assert create.call_args.kwargs["max_completion_tokens"] == 100
    assert "max_tokens" not in create.call_args.kwargs


def test_base_url_is_passed_to_sdk():
    provider = OpenAICompatibleProvider(
        api_key="ollama", timeout_seconds=5.0, base_url="http://localhost:11434/v1"
    )
    assert str(provider._client.base_url).startswith("http://localhost:11434/v1")


# ---------------------------------------------------------------------------
# Anthropic
# ---------------------------------------------------------------------------

import anthropic  # noqa: E402

from phishguard.llm.providers import (  # noqa: E402
    ANTHROPIC_DEFAULT_MAX_TOKENS,
    AnthropicProvider,
)


def _anthropic_ok(*texts: str, input_tokens: int = 10, output_tokens: int = 5):
    resp = MagicMock()
    resp.content = [MagicMock(type="text", text=t) for t in texts]
    resp.usage.input_tokens = input_tokens
    resp.usage.output_tokens = output_tokens
    return resp


@pytest.fixture
def anthropic_provider() -> AnthropicProvider:
    return AnthropicProvider(api_key="test-key", timeout_seconds=5.0)


def _mock_messages(provider: AnthropicProvider, **kwargs) -> AsyncMock:
    mock = AsyncMock(**kwargs)
    provider._client.messages.create = mock
    return mock


async def test_anthropic_system_messages_go_to_system_param(anthropic_provider):
    create = _mock_messages(anthropic_provider, return_value=_anthropic_ok("ok"))
    await anthropic_provider.complete(
        [
            {"role": "system", "content": "A"},
            {"role": "system", "content": "B"},
            {"role": "user", "content": "hi"},
        ],
        "claude-x",
        0.7,
        200,
    )
    kwargs = create.call_args.kwargs
    assert kwargs["system"] == "A\n\nB"
    assert kwargs["messages"] == [{"role": "user", "content": "hi"}]
    assert kwargs["max_tokens"] == 200
    assert "temperature" not in kwargs


async def test_anthropic_omits_system_when_absent(anthropic_provider):
    create = _mock_messages(anthropic_provider, return_value=_anthropic_ok("ok"))
    await anthropic_provider.complete(MESSAGES, "claude-x", 0.7, None)
    assert "system" not in create.call_args.kwargs


async def test_anthropic_default_max_tokens(anthropic_provider):
    create = _mock_messages(anthropic_provider, return_value=_anthropic_ok("ok"))
    await anthropic_provider.complete(MESSAGES, "claude-x", 0.7, None)
    assert create.call_args.kwargs["max_tokens"] == ANTHROPIC_DEFAULT_MAX_TOKENS == 1024


async def test_anthropic_joins_text_blocks_and_usage(anthropic_provider):
    _mock_messages(anthropic_provider, return_value=_anthropic_ok("a", "b"))
    result = await anthropic_provider.complete(MESSAGES, "claude-x", 0.7, None)
    assert result == Completion("ab", 10, 5)


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (
            anthropic.RateLimitError("slow", response=_response(429), body=None),
            ProviderRateLimitError,
        ),
        (
            anthropic.APIStatusError("overloaded", response=_response(529), body=None),
            ProviderServerError,
        ),
        (
            anthropic.BadRequestError("bad", response=_response(400), body=None),
            ProviderClientError,
        ),
        (anthropic.APIConnectionError(request=_REQUEST), ProviderConnectionError),
        (
            anthropic.AuthenticationError("nope", response=_response(401), body=None),
            ProviderAuthError,
        ),
    ],
)
async def test_anthropic_error_mapping(anthropic_provider, error, expected):
    _mock_messages(anthropic_provider, side_effect=error)
    with pytest.raises(expected):
        await anthropic_provider.complete(MESSAGES, "claude-x", 0.7, None)
