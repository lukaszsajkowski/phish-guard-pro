"""Retry utilities with exponential backoff for external API calls.

This module provides decorators and utilities for handling transient failures
in LLM and external API calls. Implements FR-037 from the PRD:
- Retry with exponential backoff (max 3 attempts)
- User-friendly error messages
- Graceful degradation

Requirements: US-022 (API Error Handling)
"""

import asyncio
import functools
import logging
from collections.abc import Callable
from typing import Any, ParamSpec, TypeVar

from openai import RateLimitError as OpenAIRateLimitError
from openai import APIError as OpenAIAPIError
from openai import APIConnectionError as OpenAIConnectionError

logger = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")

# Retryable exceptions - transient errors that may succeed on retry
RETRYABLE_EXCEPTIONS = (
    OpenAIRateLimitError,
    OpenAIConnectionError,
    asyncio.TimeoutError,
    ConnectionError,
)

# Non-retryable OpenAI exceptions - immediately fail
NON_RETRYABLE_EXCEPTIONS = (
    OpenAIAPIError,  # Typically 4xx errors like bad requests
)


class RetryExhaustedError(Exception):
    """Raised when all retry attempts have been exhausted.
    
    Attributes:
        message: User-friendly error message.
        original_error: The underlying exception that caused the retry failure.
        attempts: Number of retry attempts made.
    """

    def __init__(
        self,
        message: str,
        original_error: Exception | None = None,
        attempts: int = 0,
    ):
        super().__init__(message)
        self.message = message
        self.original_error = original_error
        self.attempts = attempts


class RateLimitError(Exception):
    """Raised when API rate limit is hit.
    
    Attributes:
        message: User-friendly error message.
        retry_after: Suggested wait time in seconds before retry.
    """

    def __init__(self, message: str, retry_after: int | None = None):
        super().__init__(message)
        self.message = message
        self.retry_after = retry_after


def retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator for async functions with retry logic and exponential backoff.
    
    Retries the decorated function on transient errors (connection issues,
    rate limits, timeouts) up to max_attempts times. Uses exponential backoff
    to avoid overwhelming the API.
    
    Args:
        max_attempts: Maximum number of attempts (default 3).
        base_delay: Initial delay in seconds (default 1.0).
        max_delay: Maximum delay cap in seconds (default 10.0).
    
    Returns:
        Decorated function with retry logic.
    
    Raises:
        RetryExhaustedError: After all attempts fail.
        RateLimitError: On rate limit with retry_after hint.
        
    Example:
        @retry_with_backoff(max_attempts=3, base_delay=1.0)
        async def call_llm(prompt: str) -> str:
            return await openai_client.chat.completions.create(...)
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            last_exception: Exception | None = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                    
                except OpenAIRateLimitError as e:
                    # Extract retry-after if available
                    retry_after = getattr(e, "retry_after", None)
                    if retry_after is None:
                        # Default to exponential backoff if not provided
                        retry_after = min(base_delay * (2 ** (attempt - 1)), max_delay)
                    
                    if attempt < max_attempts:
                        logger.warning(
                            "Rate limit hit on attempt %d/%d for %s, "
                            "waiting %.1f seconds...",
                            attempt,
                            max_attempts,
                            func.__name__,
                            retry_after,
                        )
                        await asyncio.sleep(retry_after)
                        last_exception = e
                    else:
                        # Last attempt - raise as RateLimitError
                        raise RateLimitError(
                            "The AI service is currently busy. Please try again in a moment.",
                            retry_after=int(retry_after) if retry_after else 30,
                        ) from e
                
                except NON_RETRYABLE_EXCEPTIONS as e:
                    # Don't retry on non-retryable errors (e.g., bad request)
                    logger.error(
                        "Non-retryable error in %s: %s",
                        func.__name__,
                        str(e),
                    )
                    raise RetryExhaustedError(
                        "Request failed. Please check your input and try again.",
                        original_error=e,
                        attempts=attempt,
                    ) from e
                
                except RETRYABLE_EXCEPTIONS as e:
                    last_exception = e
                    
                    if attempt < max_attempts:
                        delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                        logger.warning(
                            "Transient error on attempt %d/%d for %s: %s. "
                            "Retrying in %.1f seconds...",
                            attempt,
                            max_attempts,
                            func.__name__,
                            type(e).__name__,
                            delay,
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            "All %d attempts exhausted for %s. Last error: %s",
                            max_attempts,
                            func.__name__,
                            str(e),
                        )
                
                except Exception as e:
                    # Unexpected exception - log and raise immediately
                    logger.error(
                        "Unexpected error in %s on attempt %d: %s",
                        func.__name__,
                        attempt,
                        str(e),
                        exc_info=True,
                    )
                    raise RetryExhaustedError(
                        "An unexpected error occurred. Please try again.",
                        original_error=e,
                        attempts=attempt,
                    ) from e
            
            # All retries exhausted
            raise RetryExhaustedError(
                "Unable to connect to the AI service after multiple attempts. "
                "Please try again later.",
                original_error=last_exception,
                attempts=max_attempts,
            )
        
        return wrapper  # type: ignore
    
    return decorator
