"""The initial (/analyze) graph classifies, extracts IOCs and picks a persona."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from phishguard.agents.conversation import ResponseGenerationError
from phishguard.models.classification import AttackType, ClassificationResult


@pytest.mark.asyncio
async def test_initial_graph_does_not_fail_when_reply_generation_fails():
    from phishguard.orchestrator import nodes
    from phishguard.orchestrator.graph import create_phishguard_graph

    profiler = MagicMock()
    profiler.classify = AsyncMock(
        return_value=ClassificationResult(
            attack_type=AttackType.NIGERIAN_419,
            confidence=90.0,
            reasoning="r",
            classification_time_ms=1,
        )
    )
    agent = MagicMock()
    agent.generate_response = AsyncMock(
        side_effect=ResponseGenerationError("Safety violations: ssn")
    )

    with (
        patch.object(nodes, "ProfilerAgent", return_value=profiler),
        patch.object(nodes, "ConversationAgent", return_value=agent),
    ):
        state = await create_phishguard_graph().ainvoke(
            {"email_content": "Dear friend, send $500 to claim", "session_id": "s-1"}
        )

    assert state["classification"]["attack_type"] == "nigerian_419"
    assert state["persona"]["name"]
    assert not state.get("error")
