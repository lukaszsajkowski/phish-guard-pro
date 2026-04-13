"""FastAPI application entry point."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from phishguard.api.auth import router as auth_router
from phishguard.api.health import router as health_router
from phishguard.api.routers.analysis import router as analysis_router
from phishguard.api.routers.classification import router as classification_router
from phishguard.api.routers.enrichment import router as enrichment_router
from phishguard.api.routers.intel import router as intel_router
from phishguard.api.routers.ioc import router as ioc_router
from phishguard.api.routers.response import router as response_router
from phishguard.api.routers.session import router as session_router
from phishguard.core import get_settings
from phishguard.core.retry import RateLimitError, RetryExhaustedError
from phishguard.models.error_models import (
    ApiErrorResponse,
    ErrorCode,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan handler for startup/shutdown events."""
    # Startup
    settings = get_settings()
    if settings.debug:
        print("🛡️ PhishGuard Pro API starting in DEBUG mode")
    yield
    # Shutdown
    print("🛡️ PhishGuard Pro API shutting down")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="PhishGuard Pro API",
        description="AI-Powered Phishing Defense - Backend API",
        version="0.1.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handlers for graceful error responses (US-022)
    @app.exception_handler(RetryExhaustedError)
    async def retry_exhausted_handler(
        request: Request, exc: RetryExhaustedError
    ) -> JSONResponse:
        """Handle RetryExhaustedError with 503 Service Unavailable."""
        logger.error(
            "Retry exhausted for %s %s: %s (attempts: %d)",
            request.method,
            request.url.path,
            exc.message,
            exc.attempts,
        )
        error_response = ApiErrorResponse(
            error=exc.message,
            error_code=ErrorCode.SERVICE_UNAVAILABLE,
            should_retry=True,
            details=str(exc.original_error) if settings.debug else None,
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=error_response.model_dump(exclude_none=True),
        )

    @app.exception_handler(RateLimitError)
    async def rate_limit_handler(request: Request, exc: RateLimitError) -> JSONResponse:
        """Handle RateLimitError with 429 Too Many Requests."""
        logger.warning(
            "Rate limit hit for %s %s: %s",
            request.method,
            request.url.path,
            exc.message,
        )
        error_response = ApiErrorResponse(
            error=exc.message,
            error_code=ErrorCode.RATE_LIMIT,
            retry_after=exc.retry_after,
            should_retry=True,
        )
        headers = {"Retry-After": str(exc.retry_after)} if exc.retry_after else {}
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content=error_response.model_dump(exclude_none=True),
            headers=headers,
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Handle unexpected exceptions with 500 Internal Server Error.

        Prevents stack traces from reaching the client (US-022).
        """
        logger.error(
            "Unexpected error for %s %s: %s",
            request.method,
            request.url.path,
            str(exc),
            exc_info=True,
        )
        error_response = ApiErrorResponse(
            error="An unexpected error occurred. Please try again.",
            error_code=ErrorCode.INTERNAL_ERROR,
            should_retry=True,
            details=str(exc) if settings.debug else None,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response.model_dump(exclude_none=True),
        )

    # Include routers
    app.include_router(health_router, prefix="/api")
    app.include_router(auth_router, prefix="/api")
    app.include_router(analysis_router, prefix="/api/v1")
    app.include_router(classification_router, prefix="/api/v1")
    app.include_router(response_router, prefix="/api/v1")
    app.include_router(session_router, prefix="/api/v1")
    app.include_router(ioc_router, prefix="/api/v1")
    app.include_router(enrichment_router, prefix="/api/v1")
    app.include_router(intel_router, prefix="/api/v1")

    return app


app = create_app()
