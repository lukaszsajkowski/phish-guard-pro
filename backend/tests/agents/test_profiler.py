"""Unit tests for ProfilerAgent."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from phishguard.agents.profiler import ProfilerAgent, ClassificationError
from phishguard.llm import LLMResponse, LLMRequestError
from phishguard.models.classification import AttackType, ClassificationResult


@pytest.fixture
def mock_llm_client():
    """Create a mock LLMClient."""
    mock_client = MagicMock()
    mock_client.chat_completion = AsyncMock()
    return mock_client


@pytest.fixture
def profiler(mock_llm_client):
    """Create a ProfilerAgent instance with mocked LLM client."""
    return ProfilerAgent(llm_client=mock_llm_client)


@pytest.mark.asyncio
async def test_classify_success(profiler, mock_llm_client):
    """Test successful classification."""
    # Mock LLM response
    mock_response_content = json.dumps({
        "attack_type": "nigerian_419",
        "confidence": 95.0,
        "reasoning": "Classic 419 scam"
    })
    mock_llm_client.chat_completion.return_value = LLMResponse(
        content=mock_response_content,
        used_fallback=False,
        model_used="gpt-4o",
    )

    result = await profiler.classify("Suspicious email content")

    assert isinstance(result, ClassificationResult)
    assert result.attack_type == AttackType.NIGERIAN_419
    assert result.confidence == 95.0
    assert result.reasoning == "Classic 419 scam"
    assert result.classification_time_ms >= 0


@pytest.mark.asyncio
async def test_classify_malformed_json_retry(profiler, mock_llm_client):
    """Test retry logic on malformed JSON."""
    # First fail with invalid JSON, then succeed
    mock_llm_client.chat_completion.side_effect = [
        LLMResponse(content="Not JSON", used_fallback=False, model_used="gpt-4o"),
        LLMResponse(
            content=json.dumps({
                "attack_type": "ceo_fraud",
                "confidence": 88.0,
                "reasoning": "CEO fraud"
            }),
            used_fallback=False,
            model_used="gpt-4o",
        ),
    ]

    result = await profiler.classify("Suspicious email")

    assert result.attack_type == AttackType.CEO_FRAUD
    assert mock_llm_client.chat_completion.call_count == 2


@pytest.mark.asyncio
async def test_classify_fallback_after_failures(profiler, mock_llm_client):
    """Test fallback after max retries."""
    # Always return invalid JSON
    mock_llm_client.chat_completion.return_value = LLMResponse(
        content="Not JSON",
        used_fallback=False,
        model_used="gpt-4o",
    )

    result = await profiler.classify("Suspicious email")

    assert result.attack_type == AttackType.NOT_PHISHING
    assert result.confidence == 25.0
    assert "parsing failure" in result.reasoning


@pytest.mark.asyncio
async def test_classify_handles_markdown_wrapping(profiler, mock_llm_client):
    """Test handling of markdown code blocks in response."""
    json_content = json.dumps({
        "attack_type": "lottery_prize",
        "confidence": 92.0,
        "reasoning": "Lottery scam"
    })
    wrapped_content = f"```json\n{json_content}\n```"
    mock_llm_client.chat_completion.return_value = LLMResponse(
        content=wrapped_content,
        used_fallback=False,
        model_used="gpt-4o",
    )

    result = await profiler.classify("Suspicious email")

    assert result.attack_type == AttackType.LOTTERY_PRIZE


@pytest.mark.asyncio
async def test_classify_raises_on_llm_error(profiler, mock_llm_client):
    """Test that LLM request errors are converted to ClassificationError."""
    mock_llm_client.chat_completion.side_effect = LLMRequestError("API error")

    with pytest.raises(ClassificationError) as exc_info:
        await profiler.classify("Suspicious email")

    assert "API error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_classify_tracks_fallback_model(profiler, mock_llm_client):
    """Test that fallback model usage is tracked."""
    mock_llm_client.chat_completion.return_value = LLMResponse(
        content=json.dumps({
            "attack_type": "romance_scam",
            "confidence": 85.0,
            "reasoning": "Romance scam pattern"
        }),
        used_fallback=True,
        model_used="gpt-4o-mini",
    )

    result = await profiler.classify("Suspicious email")

    assert result.attack_type == AttackType.ROMANCE_SCAM
    assert result.used_fallback_model is True
