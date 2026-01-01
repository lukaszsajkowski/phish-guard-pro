"""Authentication API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from supabase import create_client, AuthApiError

from phishguard.core import Settings, get_settings


router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    """Request model for user registration."""

    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(
        ...,
        min_length=8,
        description="Password (minimum 8 characters)",
    )


class RegisterResponse(BaseModel):
    """Response model for successful registration."""

    success: bool = True
    message: str = "Registration successful. Please log in."


def get_supabase_client(settings: Annotated[Settings, Depends(get_settings)]):
    """Get Supabase client instance."""
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Invalid request (password too short)"},
        409: {"description": "Email already registered"},
    },
)
async def register(
    request: RegisterRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> RegisterResponse:
    """
    Register a new user account.

    Creates a new user in Supabase Auth with the provided email and password.
    Password must be at least 8 characters long.
    """
    try:
        supabase = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key,
        )

        # Use Supabase Admin API to create user
        response = supabase.auth.admin.create_user(
            {
                "email": request.email,
                "password": request.password,
                "email_confirm": True,  # Auto-confirm for MVP
            }
        )

        if response.user is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user",
            )

        return RegisterResponse()

    except AuthApiError as e:
        error_message = str(e).lower()
        if "already registered" in error_message or "already exists" in error_message:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}",
        )
