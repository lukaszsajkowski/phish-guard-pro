"""Unit tests for retry decorator with exponential backoff.

Tests the @retry_with_backoff decorator for proper retry behavior,
exponential backoff timing, and error handling.

Requirements: US-022 (API Error Handling)
"""

from unittest.mock import AsyncMock, patch

import pytest
from openai import RateLimitError as OpenAIRateLimitError

from phishguard.core.retry import (
    RateLimitError,
    RetryExhaustedError,
    retry_with_backoff,
)


class TestRetryWithBackoff:
    """Tests for the @retry_with_backoff decorator."""

    @pytest.mark.asyncio
    async def test_succeeds_on_first_attempt(self):
        """Function succeeds immediately without retry."""
        # Arrange
        mock_func = AsyncMock(return_value="success")
        decorated = retry_with_backoff(max_attempts=3)(mock_func)

        # Act
        result = await decorated()

        # Assert
        assert result == "success"
        assert mock_func.call_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_connection_error(self):
        """Function retries on connection errors."""
        # Arrange
        mock_func = AsyncMock(
            side_effect=[
                ConnectionError("Connection refused"),
                "success",
            ]
        )
        decorated = retry_with_backoff(max_attempts=3, base_delay=0.01)(mock_func)

        # Act
        result = await decorated()

        # Assert
        assert result == "success"
        assert mock_func.call_count == 2

    @pytest.mark.asyncio
    async def test_retries_on_timeout_error(self):
        """Function retries on timeout errors."""
        # Arrange
        mock_func = AsyncMock(
            side_effect=[
                TimeoutError(),
                TimeoutError(),
                "success",
            ]
        )
        decorated = retry_with_backoff(max_attempts=3, base_delay=0.01)(mock_func)

        # Act
        result = await decorated()

        # Assert
        assert result == "success"
        assert mock_func.call_count == 3

    @pytest.mark.asyncio
    async def test_raises_retry_exhausted_after_max_attempts(self):
        """Raises RetryExhaustedError after all attempts fail."""
        # Arrange
        mock_func = AsyncMock(side_effect=ConnectionError("Connection refused"))
        decorated = retry_with_backoff(max_attempts=3, base_delay=0.01)(mock_func)

        # Act & Assert
        with pytest.raises(RetryExhaustedError) as exc_info:
            await decorated()

        assert "multiple attempts" in exc_info.value.message.lower()
        assert exc_info.value.attempts == 3
        assert isinstance(exc_info.value.original_error, ConnectionError)
        assert mock_func.call_count == 3

    @pytest.mark.asyncio
    async def test_rate_limit_error_converts_to_custom_error(self):
        """Rate limits raise RateLimitError after max attempts."""
        # Arrange - use simple retry decorator and mock rate limit behavior
        call_count = 0

        # Create a mock response object for OpenAI's RateLimitError
        from unittest.mock import MagicMock

        mock_response = MagicMock()
        mock_response.request = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {"retry-after": "30"}

        @retry_with_backoff(max_attempts=3, base_delay=0.01)
        async def rate_limited_func():
            nonlocal call_count
            call_count += 1
            # Simulate rate limit by throwing OpenAI RateLimitError
            raise OpenAIRateLimitError(
                message="Rate limit exceeded",
                response=mock_response,
                body=None,
            )

        # Act & Assert
        with pytest.raises(RateLimitError) as exc_info:
            await rate_limited_func()

        assert "busy" in exc_info.value.message.lower()
        assert exc_info.value.retry_after is not None
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self):
        """Verifies exponential backoff increases delay between retries."""
        # Arrange
        delays = []

        async def mock_sleep(delay):
            delays.append(delay)
            # Don't actually sleep in tests

        mock_func = AsyncMock(
            side_effect=[
                ConnectionError("1"),
                ConnectionError("2"),
                "success",
            ]
        )
        decorated = retry_with_backoff(max_attempts=3, base_delay=1.0, max_delay=10.0)(
            mock_func
        )

        # Act
        with patch("phishguard.core.retry.asyncio.sleep", mock_sleep):
            result = await decorated()

        # Assert
        assert result == "success"
        assert len(delays) == 2  # Two retries = two sleeps
        assert delays[0] == 1.0  # base_delay * 2^0
        assert delays[1] == 2.0  # base_delay * 2^1

    @pytest.mark.asyncio
    async def test_max_delay_cap(self):
        """Verifies delay is capped at max_delay."""
        # Arrange
        delays = []

        async def mock_sleep(delay):
            delays.append(delay)

        mock_func = AsyncMock(side_effect=ConnectionError("error"))
        decorated = retry_with_backoff(
            max_attempts=5,
            base_delay=5.0,  # Would grow to 20, 40, etc.
            max_delay=10.0,  # But should be capped
        )(mock_func)

        # Act
        with patch("phishguard.core.retry.asyncio.sleep", mock_sleep):
            try:
                await decorated()
            except RetryExhaustedError:
                pass

        # Assert - all delays should be <= max_delay
        for delay in delays:
            assert delay <= 10.0

    @pytest.mark.asyncio
    async def test_does_not_retry_on_unexpected_errors(self):
        """Unexpected exceptions raise immediately without retry."""
        # Arrange
        mock_func = AsyncMock(side_effect=ValueError("Invalid input"))
        decorated = retry_with_backoff(max_attempts=3)(mock_func)

        # Act & Assert
        with pytest.raises(RetryExhaustedError) as exc_info:
            await decorated()

        # Should fail immediately on first attempt
        assert exc_info.value.attempts == 1
        assert isinstance(exc_info.value.original_error, ValueError)
        assert mock_func.call_count == 1

    @pytest.mark.asyncio
    async def test_preserves_function_return_value(self):
        """Decorated function returns correct value on success."""
        # Arrange
        expected = {"data": [1, 2, 3], "status": "ok"}
        mock_func = AsyncMock(return_value=expected)
        decorated = retry_with_backoff()(mock_func)

        # Act
        result = await decorated()

        # Assert
        assert result == expected

    @pytest.mark.asyncio
    async def test_retry_with_connection_error_succeeds_after_retry(self):
        """Retries on connection errors and succeeds."""
        # Arrange - using function-level retry to avoid mock issues
        call_count = 0

        @retry_with_backoff(max_attempts=3, base_delay=0.01)
        async def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Connection refused")
            return "success"

        # Act
        result = await flaky_func()

        # Assert
        assert result == "success"
        assert call_count == 2


class TestRetryExhaustedError:
    """Tests for RetryExhaustedError exception."""

    def test_error_contains_message(self):
        """Error message is accessible."""
        error = RetryExhaustedError("Test message")
        assert error.message == "Test message"
        assert str(error) == "Test message"

    def test_error_contains_original_error(self):
        """Original error is preserved."""
        original = ValueError("Original")
        error = RetryExhaustedError("Test", original_error=original, attempts=3)
        assert error.original_error is original
        assert error.attempts == 3


class TestRateLimitError:
    """Tests for RateLimitError exception."""

    def test_error_with_retry_after(self):
        """Rate limit error includes retry_after hint."""
        error = RateLimitError("Busy", retry_after=30)
        assert error.message == "Busy"
        assert error.retry_after == 30

    def test_error_without_retry_after(self):
        """Rate limit error works without retry_after."""
        error = RateLimitError("Busy")
        assert error.retry_after is None
