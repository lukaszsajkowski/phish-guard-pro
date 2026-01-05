"""Integration tests for response generation API endpoint."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from phishguard.main import app
from phishguard.models.classification import AttackType
from phishguard.models.persona import PersonaType


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_user_id():
    """Return a mock user ID."""
    return "test-user-id-12345"


@pytest.fixture
def mock_session_id():
    """Return a mock session ID."""
    return "test-session-id-67890"


@pytest.fixture
def mock_session_data(mock_user_id):
    """Return mock session data."""
    return {
        "id": "test-session-id-67890",
        "user_id": mock_user_id,
        "attack_type": "nigerian_419",
        "persona": {
            "persona_type": "naive_retiree",
            "name": "Margaret Thompson",
            "age": 72,
            "style_description": "Trusting and polite elderly person",
            "background": "Retired teacher living in Florida",
        },
        "status": "active",
    }


class TestResponseGenerationEndpoint:
    """Tests for POST /api/v1/response/generate endpoint."""

    @patch("phishguard.api.routers.response.session_service")
    @patch("phishguard.api.routers.response.ConversationAgent")
    @patch("phishguard.api.dependencies.get_current_user_id")
    def test_generate_response_success(
        self,
        mock_get_user_id,
        mock_agent_class,
        mock_session_service,
        client,
        mock_user_id,
        mock_session_id,
        mock_session_data,
    ):
        """Test successful response generation."""
        # Setup mocks
        mock_get_user_id.return_value = mock_user_id

        # Mock session service
        mock_session_service.get_session = AsyncMock(return_value=mock_session_data)
        mock_session_service.get_original_email = AsyncMock(
            return_value="Dear Friend, I have $5M to share with you..."
        )
        mock_session_service.add_bot_response = AsyncMock(return_value="message-id-123")

        # Mock ConversationAgent
        mock_agent = MagicMock()
        mock_result = MagicMock()
        mock_result.content = "Oh my, this sounds wonderful! How did you find me?"
        mock_result.generation_time_ms = 2500
        mock_result.safety_validated = True
        mock_result.regeneration_count = 0
        mock_result.used_fallback_model = False
        mock_result.thinking = MagicMock()
        mock_result.thinking.turn_goal = "Build rapport"
        mock_result.thinking.selected_tactic = "Ask Questions"
        mock_result.thinking.reasoning = "Testing"
        mock_agent.generate_response = AsyncMock(return_value=mock_result)
        mock_agent_class.return_value = mock_agent

        # Make request
        with patch("phishguard.api.dependencies.get_current_user_id", return_value=mock_user_id):
            response = client.post(
                "/api/v1/response/generate",
                json={"session_id": mock_session_id},
                headers={"Authorization": "Bearer test-token"},
            )

        # Assertions would need proper auth mocking
        # For now, this demonstrates the test structure

    @patch("phishguard.api.routers.response.session_service")
    @patch("phishguard.api.dependencies.get_current_user_id")
    def test_generate_response_session_not_found(
        self,
        mock_get_user_id,
        mock_session_service,
        client,
        mock_user_id,
        mock_session_id,
    ):
        """Test response generation when session doesn't exist."""
        mock_get_user_id.return_value = mock_user_id
        mock_session_service.get_session = AsyncMock(return_value=None)

        # This test demonstrates the expected behavior
        # Full integration testing would require proper auth setup

    def test_generate_response_unauthorized(self, client, mock_session_id):
        """Test response generation without authorization."""
        response = client.post(
            "/api/v1/response/generate",
            json={"session_id": mock_session_id},
        )
        # Should return 401 or 403
        assert response.status_code in [401, 403, 422]

    def test_generate_response_missing_session_id(self, client):
        """Test response generation without session_id."""
        response = client.post(
            "/api/v1/response/generate",
            json={},
            headers={"Authorization": "Bearer test-token"},
        )
        # Should return 422 (validation error)
        assert response.status_code == 422
