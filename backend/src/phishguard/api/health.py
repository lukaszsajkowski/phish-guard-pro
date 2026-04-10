"""Health check endpoint for monitoring and load balancer probes."""

from datetime import UTC, datetime

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict:
    """
    Health check endpoint.

    Returns:
        dict: Health status with timestamp and version.
    """
    from phishguard import __version__

    return {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "version": __version__,
    }
