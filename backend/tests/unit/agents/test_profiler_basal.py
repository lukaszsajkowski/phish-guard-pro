"""Tests for the Profiler on the Basal decision cascade (US-049)."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from phishguard.agents.profiler import (
    PROFILER_NODE,
    ClassificationError,
    ClassificationParseError,
    ProfilerAgent,
    build_basal_reasoning,
)
from phishguard.agents.prompts.profiler_basal import (
    ATTACK_TYPE_CRITERIA,
    PROFILER_BASAL_INSTRUCTIONS,
)
from phishguard.decisions import Decision, DecisionService
from phishguard.decisions.basal_client import BasalAnswer
from phishguard.llm import LLMRequestError, LLMResponse
from phishguard.models.classification import AttackType, ClassificationResult

ROMANCE = BasalAnswer(
    answer="romance_scam",
    probabilities={
        "romance_scam": 0.94,
        "nigerian_419": 0.03,
        "ceo_fraud": 0.02,
        "not_phishing": 0.01,
    },
    confidence=0.94,
    latency_ms=120,
)


def _llm_client(*responses: LLMResponse | Exception) -> MagicMock:
    client = MagicMock()
    client.primary_model = "gpt-4o"
    client.fallback_model = "gpt-4o-mini"
    client.chat_completion = AsyncMock(side_effect=list(responses))
    return client


def _response(
    content: str,
    *,
    used_fallback: bool = False,
    model: str = "gpt-4o",
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
) -> LLMResponse:
    return LLMResponse(
        content=content,
        used_fallback=used_fallback,
        model_used=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )


def _valid(attack_type: str = "ceo_fraud", confidence: float = 88.0) -> str:
    return json.dumps(
        {"attack_type": attack_type, "confidence": confidence, "reasoning": "r"}
    )


def _off_service() -> DecisionService:
    return DecisionService(
        basal=None, mode="off", threshold_for=lambda n: 0.9, recorder=None
    )


class FakeDecisionService:
    """Returns a preset decision, or runs the LLM call like off/shadow mode."""

    def __init__(self, decision: Decision | None = None) -> None:
        self._decision = decision
        self.calls: list[dict] = []

    async def decide_choice(
        self, question, state, session_id, llm_call, llm_answer, llm_model
    ):
        self.calls.append(
            {
                "question": question,
                "state": state,
                "session_id": session_id,
                "llm_answer": llm_answer,
                "llm_model": llm_model,
            }
        )
        if self._decision is not None:
            return self._decision
        result = await llm_call()
        return Decision("llm", llm_answer(result), None, result)


class TestBasalDecisions:
    @pytest.mark.asyncio
    async def test_basal_decision_maps_to_result(self):
        service = FakeDecisionService(Decision("basal", "romance_scam", ROMANCE, None))
        agent = ProfilerAgent(llm_client=_llm_client(), decision_service=service)

        result = await agent.classify("Hello dear", session_id="s-1")

        assert result.attack_type == AttackType.ROMANCE_SCAM
        assert result.confidence == 94.0
        assert result.decision_source == "basal"
        assert result.reasoning == (
            "Classified locally by Basal: Romance Scam (p=0.94). "
            "Runner-up: Nigerian 419 (p=0.03)."
        )
        assert result.used_fallback_model is False
        assert result.classification_time_ms >= 0

    @pytest.mark.asyncio
    async def test_low_confidence_fallback_source(self):
        low = BasalAnswer(
            "delivery_scam", {"delivery_scam": 0.6234, "fake_invoice": 0.3}, 0.6234, 50
        )
        service = FakeDecisionService(
            Decision("basal_low_confidence", "delivery_scam", low, None)
        )
        agent = ProfilerAgent(llm_client=_llm_client(), decision_service=service)

        result = await agent.classify("Your parcel", session_id="s-1")

        assert result.attack_type == AttackType.DELIVERY_SCAM
        assert result.confidence == 62.34
        assert result.decision_source == "basal_low_confidence"
        assert result.reasoning.startswith(
            "Classified locally by Basal: Delivery Scam (p=0.62)."
        )

    @pytest.mark.asyncio
    async def test_llm_decision_keeps_llm_result(self):
        service = FakeDecisionService()
        agent = ProfilerAgent(
            llm_client=_llm_client(_response(_valid())), decision_service=service
        )

        result = await agent.classify("Pay now", session_id="s-1")

        assert result.attack_type == AttackType.CEO_FRAUD
        assert result.confidence == 88.0
        assert result.decision_source == "llm"

    @pytest.mark.asyncio
    async def test_parse_error_without_basal_returns_legacy_fallback(self):
        service = FakeDecisionService()
        agent = ProfilerAgent(
            llm_client=_llm_client(_response("nope"), _response("still nope")),
            decision_service=service,
        )

        result = await agent.classify("???")

        assert result.attack_type == AttackType.NOT_PHISHING
        assert result.confidence == 25.0
        assert result.decision_source == "llm"
        assert "parsing failure" in result.reasoning

    @pytest.mark.asyncio
    async def test_llm_request_error_raises_classification_error(self):
        service = FakeDecisionService()
        agent = ProfilerAgent(
            llm_client=_llm_client(LLMRequestError("down")), decision_service=service
        )

        with pytest.raises(ClassificationError) as exc_info:
            await agent.classify("Pay now")

        assert not isinstance(exc_info.value, ClassificationParseError)
        assert "down" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_question_passed_to_service(self):
        service = FakeDecisionService()
        agent = ProfilerAgent(
            llm_client=_llm_client(_response(_valid())), decision_service=service
        )

        await agent.classify("Pay now", session_id="s-9")

        call = service.calls[0]
        assert call["question"].node == PROFILER_NODE == "profiler.attack_type"
        assert call["question"].instructions == PROFILER_BASAL_INSTRUCTIONS
        assert call["question"].criteria == ATTACK_TYPE_CRITERIA
        assert call["state"] == "Pay now"
        assert call["session_id"] == "s-9"

    @pytest.mark.asyncio
    async def test_llm_model_reflects_fallback_usage(self):
        service = FakeDecisionService()
        agent = ProfilerAgent(
            llm_client=_llm_client(_response(_valid())), decision_service=service
        )
        await agent.classify("Pay now")
        llm_model = service.calls[0]["llm_model"]

        def make(fallback: bool) -> ClassificationResult:
            return ClassificationResult(
                attack_type=AttackType.CEO_FRAUD,
                confidence=80.0,
                reasoning="r",
                classification_time_ms=1,
                used_fallback_model=fallback,
            )

        assert llm_model(make(False)) == "gpt-4o"
        assert llm_model(make(True)) == "gpt-4o-mini"

    @pytest.mark.asyncio
    async def test_default_decision_service_is_off_without_basal_url(self):
        settings = MagicMock(basal_effective_mode="off")
        with (
            patch("phishguard.agents.profiler.create_llm_client") as llm,
            patch("phishguard.decisions.cascade.get_settings", return_value=settings),
        ):
            llm.return_value = _llm_client(_response(_valid()))
            agent = ProfilerAgent()

        result = await agent.classify("Pay now")

        assert result.decision_source == "llm"
        assert result.attack_type == AttackType.CEO_FRAUD


class TestCriteria:
    def test_criteria_cover_all_attack_types(self):
        assert set(ATTACK_TYPE_CRITERIA) == {t.value for t in AttackType}

    def test_criteria_descriptions_are_non_empty(self):
        assert all(desc.strip() for desc in ATTACK_TYPE_CRITERIA.values())

    def test_build_basal_reasoning_without_runner_up(self):
        answer = BasalAnswer("not_phishing", {"not_phishing": 1.0}, 1.0, 5)

        assert build_basal_reasoning(answer) == (
            "Classified locally by Basal: Not Phishing (p=1.00)."
        )


class TestUsageRecording:
    @pytest.mark.asyncio
    async def test_classify_records_profiler_usage_with_session(self):
        client = _llm_client(
            _response(_valid(), prompt_tokens=300, completion_tokens=40)
        )
        agent = ProfilerAgent(llm_client=client, decision_service=_off_service())

        with patch(
            "phishguard.agents.profiler.record_llm_usage", new_callable=AsyncMock
        ) as rec:
            await agent.classify("Pay now", session_id="s-1")

        rec.assert_awaited_once()
        args = rec.await_args.args
        assert args[:5] == ("s-1", "profiler", "gpt-4o", 300, 40)
        assert isinstance(args[5], int)

    @pytest.mark.asyncio
    async def test_classify_without_session_skips_usage(self):
        client = _llm_client(_response(_valid()))
        agent = ProfilerAgent(llm_client=client, decision_service=_off_service())

        with patch(
            "phishguard.agents.profiler.record_llm_usage", new_callable=AsyncMock
        ) as rec:
            await agent.classify("Pay now")

        rec.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_usage_recorded_for_each_parse_attempt(self):
        client = _llm_client(_response("bad"), _response(_valid()))
        agent = ProfilerAgent(llm_client=client, decision_service=_off_service())

        with patch(
            "phishguard.agents.profiler.record_llm_usage", new_callable=AsyncMock
        ) as rec:
            await agent.classify("Pay now", session_id="s-1")

        assert rec.await_count == 2

    @pytest.mark.asyncio
    async def test_classify_with_llm_calls_on_usage_per_response(self):
        first = _response("bad", prompt_tokens=10, completion_tokens=1)
        second = _response(_valid(), prompt_tokens=20, completion_tokens=2)
        agent = ProfilerAgent(
            llm_client=_llm_client(first, second), decision_service=_off_service()
        )
        seen: list[LLMResponse] = []

        result = await agent.classify_with_llm("Pay now", on_usage=seen.append)

        assert seen == [first, second]
        assert result.attack_type == AttackType.CEO_FRAUD


class TestClassifyWithLLM:
    @pytest.mark.asyncio
    async def test_raises_parse_error_after_retries(self):
        agent = ProfilerAgent(
            llm_client=_llm_client(_response("bad"), _response("bad")),
            decision_service=_off_service(),
        )

        with pytest.raises(ClassificationParseError):
            await agent.classify_with_llm("Pay now")

    def test_parse_error_is_classification_error(self):
        assert issubclass(ClassificationParseError, ClassificationError)


class TestFixRound1:
    def test_runner_up_ignores_stray_probability_keys(self):
        answer = BasalAnswer(
            "romance_scam",
            {"romance_scam": 0.90, "other": 0.08, "nigerian_419": 0.02},
            0.90,
            5,
        )

        assert build_basal_reasoning(answer) == (
            "Classified locally by Basal: Romance Scam (p=0.90). "
            "Runner-up: Nigerian 419 (p=0.02)."
        )

    def test_runner_up_omitted_when_only_stray_keys(self):
        answer = BasalAnswer("ceo_fraud", {"ceo_fraud": 0.9, "bogus": 0.1}, 0.9, 5)

        assert build_basal_reasoning(answer) == (
            "Classified locally by Basal: CEO Fraud (p=0.90)."
        )

    @pytest.mark.asyncio
    async def test_classify_survives_stray_probability_key(self):
        stray = BasalAnswer(
            "romance_scam", {"romance_scam": 0.91, "zzz_unknown": 0.09}, 0.91, 5
        )
        service = FakeDecisionService(Decision("basal", "romance_scam", stray, None))
        agent = ProfilerAgent(llm_client=_llm_client(), decision_service=service)

        result = await agent.classify("Hello dear")

        assert result.attack_type == AttackType.ROMANCE_SCAM
        assert result.decision_source == "basal"

    @pytest.mark.asyncio
    async def test_raising_on_usage_does_not_cause_fallback(self):
        client = _llm_client(_response(_valid()))
        agent = ProfilerAgent(llm_client=client, decision_service=_off_service())

        def boom(_: LLMResponse) -> None:
            raise RuntimeError("buggy callback")

        result = await agent.classify_with_llm("Pay now", on_usage=boom)

        assert result.attack_type == AttackType.CEO_FRAUD
        assert client.chat_completion.await_count == 1


def test_basal_timeout_default_is_30s(monkeypatch):
    from phishguard.core import Settings

    monkeypatch.delenv("BASAL_TIMEOUT_S", raising=False)

    assert Settings(_env_file=None).basal_timeout_s == 30.0
