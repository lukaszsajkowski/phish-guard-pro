"""Unit tests for ProfilerAgent."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

from phishguard.agents.profiler import ProfilerAgent, ClassificationError
from phishguard.models.classification import AttackType, ClassificationResult

@pytest.fixture
def mock_llm_chain():
    """Mock LangChain LLM."""
    with patch("phishguard.agents.profiler.ChatOpenAI") as mock:
        instance = mock.return_value
        instance.ainvoke = AsyncMock()
        yield instance

@pytest.fixture
def profiler(mock_llm_chain):
    """Create a ProfilerAgent instance."""
    return ProfilerAgent()

@pytest.mark.asyncio
async def test_classify_success(profiler, mock_llm_chain):
    """Test successful classification."""
    # Mock LLM response
    mock_response_content = json.dumps({
        "attack_type": "nigerian_419",
        "confidence": 95.0,
        "reasoning": "Classic 419 scam"
    })
    mock_llm_chain.ainvoke.return_value = AIMessage(content=mock_response_content)

    result = await profiler.classify("Suspicious email content")

    assert isinstance(result, ClassificationResult)
    assert result.attack_type == AttackType.NIGERIAN_419
    assert result.confidence == 95.0
    assert result.reasoning == "Classic 419 scam"
    assert result.classification_time_ms >= 0

@pytest.mark.asyncio
async def test_classify_malformed_json_retry(profiler, mock_llm_chain):
    """Test retry logic on malformed JSON."""
    # First fail, then succeed
    mock_llm_chain.ainvoke.side_effect = [
        AIMessage(content="Not JSON"),
        AIMessage(content=json.dumps({
            "attack_type": "ceo_fraud",
            "confidence": 88.0,
            "reasoning": "CEO fraud"
        }))
    ]

    result = await profiler.classify("Suspicious email")

    assert result.attack_type == AttackType.CEO_FRAUD
    assert mock_llm_chain.ainvoke.call_count == 2

@pytest.mark.asyncio
async def test_classify_fallback_after_failures(profiler, mock_llm_chain):
    """Test fallback after max retries."""
    # Always fail
    mock_llm_chain.ainvoke.return_value = AIMessage(content="Not JSON")

    result = await profiler.classify("Suspicious email")

    assert result.attack_type == AttackType.NOT_PHISHING
    assert result.confidence == 25.0
    assert "parsing failure" in result.reasoning

@pytest.mark.asyncio
async def test_classify_handles_markdown_wrapping(profiler, mock_llm_chain):
    """Test handling of markdown code blocks in response."""
    json_content = json.dumps({
        "attack_type": "lottery_prize",
        "confidence": 92.0,
        "reasoning": "Lottery scam"
    })
    wrapped_content = f"```json\n{json_content}\n```"
    mock_llm_chain.ainvoke.return_value = AIMessage(content=wrapped_content)

    result = await profiler.classify("Suspicious email")

    assert result.attack_type == AttackType.LOTTERY_PRIZE
