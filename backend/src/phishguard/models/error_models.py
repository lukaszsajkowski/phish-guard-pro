"""Standardized error response models for API error handling.

This module provides Pydantic models for consistent error responses across
all API endpoints. Ensures frontend receives predictable error structure.

Requirements: US-022 (API Error Handling)
"""

from enum import Enum

from pydantic import BaseModel, Field


class ErrorCode(str, Enum):
    """Machine-readable error codes for frontend handling."""
    
    # Transient errors - should retry
    API_ERROR = "API_ERROR"
    RATE_LIMIT = "RATE_LIMIT"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    TIMEOUT = "TIMEOUT"
    
    # Permanent errors - do not retry
    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    BAD_REQUEST = "BAD_REQUEST"
    
    # Internal errors
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ApiErrorResponse(BaseModel):
    """Standardized API error response model.
    
    This model ensures consistent error response structure across all endpoints.
    Frontend can rely on this format for error handling and display.
    """
    
    error: str = Field(
        ...,
        description="User-friendly error message suitable for display",
        examples=["Unable to connect to the AI service. Please try again."],
    )
    error_code: ErrorCode = Field(
        ...,
        description="Machine-readable error code for programmatic handling",
        examples=["API_ERROR"],
    )
    retry_after: int | None = Field(
        default=None,
        description="Seconds to wait before retry (for rate limits)",
        examples=[30],
    )
    should_retry: bool = Field(
        default=False,
        description="Whether client should attempt automatic retry",
    )
    details: str | None = Field(
        default=None,
        description="Additional technical details (only in debug mode)",
    )


# Pre-configured error responses for common scenarios
SERVICE_UNAVAILABLE_ERROR = ApiErrorResponse(
    error="Unable to connect to the AI service after multiple attempts. Please try again later.",
    error_code=ErrorCode.SERVICE_UNAVAILABLE,
    should_retry=True,
)

RATE_LIMIT_ERROR = ApiErrorResponse(
    error="The AI service is currently busy. Please try again in a moment.",
    error_code=ErrorCode.RATE_LIMIT,
    retry_after=30,
    should_retry=True,
)

INTERNAL_ERROR = ApiErrorResponse(
    error="An unexpected error occurred. Please try again.",
    error_code=ErrorCode.INTERNAL_ERROR,
    should_retry=True,
)

VALIDATION_ERROR = ApiErrorResponse(
    error="Invalid request. Please check your input.",
    error_code=ErrorCode.VALIDATION_ERROR,
    should_retry=False,
)
