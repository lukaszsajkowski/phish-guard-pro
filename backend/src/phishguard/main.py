"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from phishguard.api.auth import router as auth_router
from phishguard.api.health import router as health_router
from phishguard.api.routers.analysis import router as analysis_router
from phishguard.core import get_settings


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

    # Include routers
    app.include_router(health_router, prefix="/api")
    app.include_router(auth_router, prefix="/api")
    app.include_router(analysis_router, prefix="/api/v1")

    return app


app = create_app()
