"""Tests for the auth endpoints."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from phishguard.main import app


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(app)


class TestRegisterEndpoint:
    """Tests for POST /api/auth/register."""

    def test_register_password_too_short_returns_422(self, client: TestClient) -> None:
        """Test that password shorter than 8 chars returns validation error."""
        response = client.post(
            "/api/auth/register",
            json={"email": "test@example.com", "password": "short"},
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_register_invalid_email_returns_422(self, client: TestClient) -> None:
        """Test that invalid email returns validation error."""
        response = client.post(
            "/api/auth/register",
            json={"email": "not-an-email", "password": "validpassword123"},
        )

        assert response.status_code == 422

    @patch("phishguard.api.auth.create_client")
    def test_register_success_returns_201(
        self, mock_create_client: MagicMock, client: TestClient
    ) -> None:
        """Test successful registration returns 201."""
        # Mock Supabase client and response
        mock_supabase = MagicMock()
        mock_create_client.return_value = mock_supabase
        mock_user = MagicMock()
        mock_user.id = "test-user-id"
        mock_supabase.auth.admin.create_user.return_value = MagicMock(user=mock_user)

        response = client.post(
            "/api/auth/register",
            json={"email": "test@example.com", "password": "validpassword123"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert "message" in data

    @patch("phishguard.api.auth.create_client")
    def test_register_duplicate_email_returns_409(
        self, mock_create_client: MagicMock, client: TestClient
    ) -> None:
        """Test that duplicate email returns 409 conflict."""
        from supabase import AuthApiError

        mock_supabase = MagicMock()
        mock_create_client.return_value = mock_supabase
        mock_supabase.auth.admin.create_user.side_effect = AuthApiError(
            "User already registered", status=400, code="user_already_exists"
        )

        response = client.post(
            "/api/auth/register",
            json={"email": "existing@example.com", "password": "validpassword123"},
        )

        assert response.status_code == 409
        data = response.json()
        assert "already exists" in data["detail"]
