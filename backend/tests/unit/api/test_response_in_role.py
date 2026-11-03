"""Unit tests for the Basal in-role warning on the response endpoints (US-050)."""

from collections.abc import Iterator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from phishguard.api.dependencies import get_current_user_id
from phishguard.main import app
from phishguard.models.in_role import InRoleWarning

USER_ID = "test-user-123"
ROUTER = "phishguard.api.routers.response"
WARNING = InRoleWarning(message="Breaks role", confidence=0.87)

PERSONA = {
    "persona_type": "naive_retiree",
    "name": "Margaret",
    "age": 72,
    "style_description": "Trusting",
    "background": "Retired teacher",
}


def _session(persona: dict | None = PERSONA) -> dict:
    return {
        "user_id": USER_ID,
        "attack_type": "nigerian_419",
        "persona": persona,
        "confidence": 0.9,
        "reasoning": "r",
    }


@pytest.fixture
def client() -> Iterator[TestClient]:
    app.dependency_overrides[get_current_user_id] = lambda: USER_ID
    yield TestClient(app)
    app.dependency_overrides.pop(get_current_user_id, None)


@pytest.fixture
def check() -> Iterator[AsyncMock]:
    with patch(f"{ROUTER}.check_in_role", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture
def generate_mocks() -> Iterator[dict]:
    """Patch everything /generate touches except check_in_role."""

    @asynccontextmanager
    async def fake_checkpointer():
        yield MagicMock()

    graph = MagicMock()
    graph.ainvoke = AsyncMock(
        return_value={
            "current_response": "Oh dear, tell me more!",
            "generation_time_ms": 12,
            "is_safe": True,
            "regeneration_count": 0,
            "extracted_iocs": [],
        }
    )
    svc = f"{ROUTER}.session_service"
    with (
        patch(f"{svc}.get_session", new_callable=AsyncMock) as get_session,
        patch(f"{svc}.get_original_email", new_callable=AsyncMock) as get_email,
        patch(f"{svc}.get_conversation_history", new_callable=AsyncMock) as history,
        patch(f"{svc}.add_bot_response", new_callable=AsyncMock) as add_bot,
        patch(f"{svc}.get_session_info", new_callable=AsyncMock) as info,
        patch(f"{ROUTER}.create_continuation_graph", return_value=graph),
        patch(f"{ROUTER}.get_checkpointer", fake_checkpointer),
    ):
        get_session.return_value = _session()
        get_email.return_value = "email body"
        history.return_value = []
        add_bot.return_value = "bot-msg-1"
        info.return_value = {"turn_count": 1, "turn_limit": 20, "is_at_limit": False}
        yield {"get_session": get_session, "graph": graph}


@pytest.fixture
def validate_mocks() -> Iterator[dict]:
    svc = f"{ROUTER}.session_service"
    with (
        patch(f"{svc}.get_session", new_callable=AsyncMock) as get_session,
        patch(f"{svc}.update_message_content", new_callable=AsyncMock),
    ):
        get_session.return_value = _session()
        yield {"get_session": get_session}


GENERATE_BODY = {"session_id": "sess-1"}
VALIDATE_BODY = {
    "content": "Hello, this sounds wonderful!",
    "session_id": "sess-1",
    "message_id": "msg-9",
}


class TestGenerateInRole:
    def test_returns_warning_from_check(
        self, client: TestClient, check: AsyncMock, generate_mocks: dict
    ) -> None:
        check.return_value = WARNING

        response = client.post("/api/v1/response/generate", json=GENERATE_BODY)

        assert response.status_code == 200
        assert response.json()["in_role_warning"] == {
            "message": "Breaks role",
            "confidence": 0.87,
        }
        args = check.await_args.args
        assert args[0].name == "Margaret"
        assert args[1:] == ("Oh dear, tell me more!", "sess-1", "bot-msg-1")

    def test_iocs_saved_before_in_role_check(
        self, client: TestClient, check: AsyncMock, generate_mocks: dict
    ) -> None:
        generate_mocks["graph"].ainvoke.return_value = {
            "current_response": "Oh dear!",
            "generation_time_ms": 12,
            "is_safe": True,
            "regeneration_count": 0,
            "extracted_iocs": [{"type": "url", "value": "http://x.test"}],
        }
        order: list[str] = []
        check.side_effect = lambda *a, **k: order.append("check")
        with patch(
            f"{ROUTER}.session_service.save_extracted_iocs",
            new_callable=AsyncMock,
        ) as save:
            save.side_effect = lambda *a, **k: order.append("save")

            response = client.post("/api/v1/response/generate", json=GENERATE_BODY)

        assert response.status_code == 200
        assert order == ["save", "check"]

    def test_no_warning_when_check_returns_none(
        self, client: TestClient, check: AsyncMock, generate_mocks: dict
    ) -> None:
        check.return_value = None

        response = client.post("/api/v1/response/generate", json=GENERATE_BODY)

        assert response.status_code == 200
        assert response.json()["in_role_warning"] is None

    def test_missing_persona_still_400(
        self, client: TestClient, check: AsyncMock, generate_mocks: dict
    ) -> None:
        generate_mocks["get_session"].return_value = _session(persona=None)

        response = client.post("/api/v1/response/generate", json=GENERATE_BODY)

        assert response.status_code == 400
        check.assert_not_awaited()

    def test_unparsable_persona_still_500(
        self, client: TestClient, check: AsyncMock, generate_mocks: dict
    ) -> None:
        generate_mocks["get_session"].return_value = _session(persona={"name": "x"})

        response = client.post("/api/v1/response/generate", json=GENERATE_BODY)

        assert response.status_code == 500
        check.assert_not_awaited()


class TestValidateInRole:
    def test_safe_content_returns_warning(
        self, client: TestClient, check: AsyncMock, validate_mocks: dict
    ) -> None:
        check.return_value = WARNING

        response = client.post("/api/v1/response/validate", json=VALIDATE_BODY)

        assert response.status_code == 200
        data = response.json()
        assert data["is_safe"] is True
        assert data["in_role_warning"] == {"message": "Breaks role", "confidence": 0.87}
        args = check.await_args.args
        assert args[1:] == (VALIDATE_BODY["content"], "sess-1", "msg-9")

    def test_edit_to_in_role_clears_warning(
        self, client: TestClient, check: AsyncMock, validate_mocks: dict
    ) -> None:
        check.side_effect = [WARNING, None]

        first = client.post("/api/v1/response/validate", json=VALIDATE_BODY)
        second = client.post("/api/v1/response/validate", json=VALIDATE_BODY)

        assert first.json()["in_role_warning"] is not None
        assert second.json()["in_role_warning"] is None

    def test_pii_violation_skips_check(
        self, client: TestClient, check: AsyncMock, validate_mocks: dict
    ) -> None:
        body = {**VALIDATE_BODY, "content": "My SSN is 234-56-7890"}

        response = client.post("/api/v1/response/validate", json=body)

        assert response.status_code == 200
        data = response.json()
        assert data["is_safe"] is False
        assert data["violations"]
        assert data["in_role_warning"] is None
        check.assert_not_awaited()

    def test_no_persona_returns_null_warning(
        self, client: TestClient, check: AsyncMock, validate_mocks: dict
    ) -> None:
        validate_mocks["get_session"].return_value = _session(persona=None)

        response = client.post("/api/v1/response/validate", json=VALIDATE_BODY)

        assert response.status_code == 200
        assert response.json()["in_role_warning"] is None
        check.assert_not_awaited()
