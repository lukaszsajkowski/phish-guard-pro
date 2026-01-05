"""API Dependencies for authentication and authorization.

This module provides FastAPI dependencies for validating JWT tokens
and extracting user information from authenticated requests.
"""

import logging
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from supabase import create_client

from phishguard.core import Settings, get_settings

logger = logging.getLogger(__name__)


async def get_current_user_id(
    authorization: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
) -> str:
    """Extract and validate user ID from JWT token.

    Validates the JWT token from the Authorization header using Supabase
    and returns the user's ID.

    Args:
        authorization: The Authorization header value (Bearer token).
        settings: Application settings with Supabase credentials.

    Returns:
        The authenticated user's UUID as a string.

    Raises:
        HTTPException: 401 if token is missing, invalid, or expired.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract token from "Bearer <token>" format
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]

    try:
        # Use Supabase client to verify the token
        supabase = create_client(
            settings.supabase_url,
            settings.supabase_anon_key,
        )

        # Get user from token - this validates the JWT
        response = supabase.auth.get_user(token)

        if response.user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return response.user.id

    except HTTPException:
        raise
    except Exception as e:
        logger.warning("Token validation failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token validation failed",
            headers={"WWW-Authenticate": "Bearer"},
        )
