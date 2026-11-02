"""decision_source flows from the Profiler to the session row and back (US-049)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from phishguard.models.classification import AttackType, ClassificationResult


def _result(source: str = "basal") -> ClassificationResult:
    return ClassificationResult(
        attack_type=AttackType.ROMANCE_SCAM,
        confidence=94.0,
        reasoning="Classified locally by Basal: Romance Scam (p=0.94).",
        classification_time_ms=120,
        decision_source=source,
    )


def test_classification_result_defaults_to_llm():
    result = ClassificationResult(
        attack_type=AttackType.CEO_FRAUD,
        confidence=80.0,
        reasoning="r",
        classification_time_ms=1,
    )

    assert result.decision_source == "llm"


def test_classification_result_rejects_unknown_source():
    with pytest.raises(ValueError):
        _result("gpt")


@pytest.mark.asyncio
async def test_classify_email_node_passes_session_and_copies_source():
    from phishguard.orchestrator import nodes

    profiler = MagicMock()
    profiler.classify = AsyncMock(return_value=_result("basal"))
    with patch.object(nodes, "ProfilerAgent", return_value=profiler):
        update = await nodes.classify_email(
            {"email_content": "Hello dear", "session_id": "s-1"}
        )

    profiler.classify.assert_awaited_once_with("Hello dear", session_id="s-1")
    assert update["classification"]["decision_source"] == "basal"
    assert update["classification"]["attack_type"] == "romance_scam"


@pytest.mark.asyncio
async def test_update_session_classification_writes_decision_source():
    client = MagicMock()
    table = client.table.return_value
    table.update.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": "s-1"}]
    )
    with patch(
        "phishguard.services.session_service._get_supabase_client",
        return_value=client,
    ):
        from phishguard.services.session_service import update_session_classification

        await update_session_classification("s-1", _result("basal_low_confidence"))

    written = table.update.call_args_list[0].args[0]
    assert "decision_source" not in written
    assert written["attack_confidence"] == 94.0
    second = table.update.call_args_list[1].args[0]
    assert second == {"decision_source": "basal_low_confidence"}


@pytest.mark.asyncio
async def test_decision_source_write_failure_does_not_raise():
    client = MagicMock()
    table = client.table.return_value
    main_exec = MagicMock(data=[{"id": "s-1"}])
    table.update.return_value.eq.return_value.execute.side_effect = [
        main_exec,
        Exception("column decision_source does not exist"),
    ]
    with patch(
        "phishguard.services.session_service._get_supabase_client",
        return_value=client,
    ):
        from phishguard.services.session_service import update_session_classification

        await update_session_classification("s-1", _result("basal"))

    assert table.update.call_count == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("stored", ["basal", None])
async def test_restore_returns_decision_source(stored):
    from phishguard.api.routers import session as session_router

    row = {
        "id": "s-1",
        "user_id": "u-1",
        "attack_type": "romance_scam",
        "attack_confidence": 94.0,
        "persona": None,
        "status": "active",
        "decision_source": stored,
    }
    svc = session_router.session_service
    with (
        patch.object(svc, "get_session", AsyncMock(return_value=row)),
        patch.object(svc, "get_session_messages", AsyncMock(return_value=[])),
        patch.object(svc, "get_session_iocs", AsyncMock(return_value=[])),
        patch.object(
            svc,
            "get_session_info",
            AsyncMock(
                return_value={"turn_count": 0, "turn_limit": 20, "is_at_limit": False}
            ),
        ),
    ):
        response = await session_router.restore_session("s-1", "u-1")

    assert response.decision_source == stored
    assert response.confidence == 94.0


@pytest.mark.asyncio
async def test_classification_router_carries_decision_source():
    from phishguard.api.routers import classification as router

    graph = MagicMock()
    graph.ainvoke = AsyncMock(
        return_value={
            "classification": {
                "attack_type": "romance_scam",
                "confidence": 94.0,
                "reasoning": "Classified locally by Basal: Romance Scam (p=0.94).",
                "classification_time_ms": 120,
                "decision_source": "basal",
            },
            "persona": None,
            "extracted_iocs": [],
        }
    )
    checkpointer = MagicMock()
    checkpointer.__aenter__ = AsyncMock(return_value=MagicMock())
    checkpointer.__aexit__ = AsyncMock(return_value=None)
    update = AsyncMock()
    with (
        patch.object(
            router.session_service, "create_session", AsyncMock(return_value="s-1")
        ),
        patch.object(router.session_service, "update_session_classification", update),
        patch.object(router, "create_phishguard_graph", return_value=graph),
        patch.object(router, "get_checkpointer", return_value=checkpointer),
    ):
        result = await router.classify_email(
            router.ClassificationRequest(email_content="Hello dear"), "u-1"
        )

    assert result.decision_source == "basal"
    assert update.await_args.kwargs["classification_result"].decision_source == (
        "basal"
    )
