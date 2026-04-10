"""Unit tests for the LLM client module (US-023).

Tests the retry logic, fallback mechanism, and error handling
for graceful degradation when the primary model is unavailable.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openai import AuthenticationError, RateLimitError
from openai._exceptions import APIStatusError

from phishguard.llm.client import (
    LLMClient,
    LLMClientConfig,
    LLMConfigurationError,
    LLMRequestError,
    LLMResponse,
    create_llm_client,
)


@pytest.fixture
def mock_settings():
    """Mock application settings."""
    with patch("phishguard.llm.client.get_settings") as mock:
        settings = MagicMock()
        settings.openai_api_key = "test-api-key"
        settings.openai_primary_model = "gpt-4o"
        settings.openai_fallback_model = "gpt-4o-mini"
        mock.return_value = settings
        yield settings


@pytest.fixture
def client_config():
    """Test client configuration."""
    return LLMClientConfig(
        primary_model="gpt-4o",
        fallback_model="gpt-4o-mini",
        timeout_seconds=30.0,
        max_retries=2,
        base_delay_seconds=0.1,  # Minimum allowed value for fast testing
    )


class TestLLMClientConfig:
    """Tests for LLMClientConfig validation."""

    def test_default_values(self):
        """Test default configuration values."""
        config = LLMClientConfig()
        assert config.primary_model == "gpt-4o"
        assert config.fallback_model == "gpt-4o-mini"
        assert config.max_retries == 3
        assert config.timeout_seconds == 30.0

    def test_custom_values(self):
        """Test custom configuration values."""
        config = LLMClientConfig(
            primary_model="gpt-5",
            fallback_model="gpt-4-turbo",
            max_retries=5,
            timeout_seconds=60.0,
        )
        assert config.primary_model == "gpt-5"
        assert config.fallback_model == "gpt-4-turbo"
        assert config.max_retries == 5
        assert config.timeout_seconds == 60.0

    def test_config_is_frozen(self):
        """Test that config is immutable."""
        config = LLMClientConfig()
        with pytest.raises(Exception):  # Pydantic frozen model error
            config.primary_model = "different-model"


class TestLLMResponse:
    """Tests for LLMResponse model."""

    def test_basic_response(self):
        """Test creating a basic response."""
        response = LLMResponse(
            content="Hello, world!",
            used_fallback=False,
            model_used="gpt-4o",
        )
        assert response.content == "Hello, world!"
        assert response.used_fallback is False
        assert response.model_used == "gpt-4o"

    def test_fallback_response(self):
        """Test response when fallback was used."""
        response = LLMResponse(
            content="Hello from fallback",
            used_fallback=True,
            model_used="gpt-4o-mini",
        )
        assert response.used_fallback is True
        assert response.model_used == "gpt-4o-mini"


class TestLLMClient:
    """Tests for LLMClient functionality."""

    @pytest.mark.asyncio
    async def test_successful_completion(self, mock_settings, client_config):
        """Test successful chat completion with primary model."""
        client = LLMClient(config=client_config)

        # Mock the OpenAI client response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"

        with patch.object(
            client._client.chat.completions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            response = await client.chat_completion(
                messages=[{"role": "user", "content": "Hello"}]
            )

        assert response.content == "Test response"
        assert response.used_fallback is False
        assert response.model_used == "gpt-4o"

    @pytest.mark.asyncio
    async def test_fallback_on_rate_limit(self, mock_settings, client_config):
        """Test fallback to secondary model on rate limit error."""
        client = LLMClient(config=client_config)

        # First calls fail with rate limit, fallback succeeds
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Fallback response"

        call_count = 0

        async def mock_create(**kwargs):
            nonlocal call_count
            call_count += 1
            if kwargs.get("model") == client_config.primary_model:
                raise RateLimitError(
                    "Rate limit exceeded",
                    response=MagicMock(status_code=429),
                    body={"error": {"message": "Rate limit exceeded"}},
                )
            return mock_response

        with patch.object(
            client._client.chat.completions,
            "create",
            side_effect=mock_create,
        ):
            response = await client.chat_completion(
                messages=[{"role": "user", "content": "Hello"}]
            )

        assert response.content == "Fallback response"
        assert response.used_fallback is True
        assert response.model_used == "gpt-4o-mini"
        # Should have retried primary model then tried fallback
        assert call_count > 1

    @pytest.mark.asyncio
    async def test_fallback_on_server_error(self, mock_settings, client_config):
        """Test fallback on 5xx server errors."""
        client = LLMClient(config=client_config)

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Fallback response"

        async def mock_create(**kwargs):
            if kwargs.get("model") == client_config.primary_model:
                mock_resp = MagicMock()
                mock_resp.status_code = 503
                raise APIStatusError(
                    "Service unavailable",
                    response=mock_resp,
                    body={"error": {"message": "Service unavailable"}},
                )
            return mock_response

        with patch.object(
            client._client.chat.completions,
            "create",
            side_effect=mock_create,
        ):
            response = await client.chat_completion(
                messages=[{"role": "user", "content": "Hello"}]
            )

        assert response.used_fallback is True

    @pytest.mark.asyncio
    async def test_no_fallback_on_client_error(self, mock_settings, client_config):
        """Test that 4xx client errors don't trigger fallback."""
        client = LLMClient(config=client_config)

        mock_resp = MagicMock()
        mock_resp.status_code = 400

        with patch.object(
            client._client.chat.completions,
            "create",
            new_callable=AsyncMock,
            side_effect=APIStatusError(
                "Bad request",
                response=mock_resp,
                body={"error": {"message": "Bad request"}},
            ),
        ):
            with pytest.raises(LLMRequestError) as exc_info:
                await client.chat_completion(
                    messages=[{"role": "user", "content": "Hello"}]
                )

        assert "Client error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_auth_error_raises_config_error(self, mock_settings, client_config):
        """Test that authentication errors raise LLMConfigurationError."""
        client = LLMClient(config=client_config)

        with patch.object(
            client._client.chat.completions,
            "create",
            new_callable=AsyncMock,
            side_effect=AuthenticationError(
                "Invalid API key",
                response=MagicMock(),
                body={"error": {"message": "Invalid API key"}},
            ),
        ):
            with pytest.raises(LLMConfigurationError) as exc_info:
                await client.chat_completion(
                    messages=[{"role": "user", "content": "Hello"}]
                )

        assert "Invalid OpenAI API key" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_both_models_fail(self, mock_settings, client_config):
        """Test error when both primary and fallback models fail."""
        client = LLMClient(config=client_config)

        with patch.object(
            client._client.chat.completions,
            "create",
            new_callable=AsyncMock,
            side_effect=RateLimitError(
                "Rate limit exceeded",
                response=MagicMock(status_code=429),
                body={"error": {"message": "Rate limit exceeded"}},
            ),
        ):
            with pytest.raises(LLMRequestError) as exc_info:
                await client.chat_completion(
                    messages=[{"role": "user", "content": "Hello"}]
                )

        assert "Both primary" in str(exc_info.value)
        assert "fallback" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_explicit_model_disables_fallback(self, mock_settings, client_config):
        """Test that specifying a model explicitly disables fallback."""
        client = LLMClient(config=client_config)

        with patch.object(
            client._client.chat.completions,
            "create",
            new_callable=AsyncMock,
            side_effect=RateLimitError(
                "Rate limit exceeded",
                response=MagicMock(status_code=429),
                body={"error": {"message": "Rate limit exceeded"}},
            ),
        ):
            with pytest.raises(LLMRequestError):
                await client.chat_completion(
                    messages=[{"role": "user", "content": "Hello"}],
                    model="specific-model",  # Explicit model
                )


class TestCreateLLMClient:
    """Tests for the factory function."""

    def test_creates_client_with_defaults(self, mock_settings):
        """Test that factory creates client with default settings."""
        client = create_llm_client()
        assert client.primary_model == "gpt-4o"
        assert client.fallback_model == "gpt-4o-mini"

    def test_creates_client_with_overrides(self, mock_settings):
        """Test that factory accepts override parameters."""
        client = create_llm_client(
            primary_model="gpt-5",
            fallback_model="gpt-4-turbo",
        )
        assert client.primary_model == "gpt-5"
        assert client.fallback_model == "gpt-4-turbo"

    def test_raises_error_without_api_key(self):
        """Test that missing API key raises configuration error."""
        with patch("phishguard.llm.client.get_settings") as mock:
            mock.return_value = MagicMock(
                openai_api_key="",
                openai_primary_model="gpt-4o",
                openai_fallback_model="gpt-4o-mini",
            )
            with pytest.raises(LLMConfigurationError):
                LLMClient()
