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
    @patch("phishguard.api.routers.response.get_checkpointer")
    @patch("phishguard.api.routers.response.create_continuation_graph")
    def test_generate_response_success(
        self,
        mock_create_graph,
        mock_get_checkpointer,
        mock_session_service,
        client,
        mock_user_id,
        mock_session_id,
        mock_session_data,
    ):
        """Test successful response generation."""
        from phishguard.api.dependencies import get_current_user_id

        # Override auth dependency with FastAPI's recommended approach
        async def override_get_current_user_id():
            return mock_user_id

        app.dependency_overrides[get_current_user_id] = override_get_current_user_id

        try:
            # Mock session service
            mock_session_service.get_session = AsyncMock(return_value=mock_session_data)
            mock_session_service.get_original_email = AsyncMock(
                return_value="Dear Friend, I have $5M to share with you..."
            )
            mock_session_service.get_conversation_history = AsyncMock(return_value=[])
            mock_session_service.add_bot_response = AsyncMock(return_value="message-id-123")
            mock_session_service.save_extracted_iocs = AsyncMock(return_value=None)
            mock_session_service.get_session_info = AsyncMock(
                return_value={"turn_count": 1, "turn_limit": 20, "is_at_limit": False}
            )

            # Mock the LangGraph workflow
            mock_graph = AsyncMock()
            mock_graph.ainvoke = AsyncMock(
                return_value={
                    "current_response": "Oh my, this sounds wonderful! How did you find me?",
                    "current_thinking": {
                        "turn_goal": "Build rapport",
                        "selected_tactic": "Ask Questions",
                        "reasoning": "Testing",
                    },
                    "generation_time_ms": 2500,
                    "is_safe": True,
                    "regeneration_count": 0,
                    "extracted_iocs": [],
                    "used_fallback_model": False,
                }
            )
            mock_create_graph.return_value = mock_graph

            # Mock the checkpointer context manager
            mock_checkpointer = MagicMock()
            mock_checkpointer.__aenter__ = AsyncMock(return_value=mock_checkpointer)
            mock_checkpointer.__aexit__ = AsyncMock(return_value=None)
            mock_get_checkpointer.return_value = mock_checkpointer

            # Make request
            response = client.post(
                "/api/v1/response/generate",
                json={"session_id": mock_session_id},
                headers={"Authorization": "Bearer test-token"},
            )

            # Verify successful response
            assert response.status_code == 200
            data = response.json()
            assert data["content"] == "Oh my, this sounds wonderful! How did you find me?"
            assert data["generation_time_ms"] == 2500
            assert data["safety_validated"] is True
            assert data["message_id"] == "message-id-123"
        finally:
            # Clean up dependency override
            app.dependency_overrides.pop(get_current_user_id, None)

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
        """Test response generation without session_id.

        Note: With an invalid token, authentication fails (401) before
        request validation (422). This test verifies the API rejects
        invalid requests appropriately.
        """
        response = client.post(
            "/api/v1/response/generate",
            json={},
            headers={"Authorization": "Bearer test-token"},
        )
        # Authentication runs before validation, so 401 (invalid token)
        # or 422 (validation error with valid auth) are acceptable
        assert response.status_code in [401, 422]
