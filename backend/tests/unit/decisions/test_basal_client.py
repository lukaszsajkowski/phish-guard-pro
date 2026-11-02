"""Unit tests for the Basal HTTP client and Basal settings."""

import json

import httpx
import pytest

from phishguard.core import Settings
from phishguard.decisions.basal_client import BasalClient, BasalUnavailableError

CRITERIA = {"romance_scam": "Romance scam", "nigerian_419": "Advance fee"}


def _client(handler) -> BasalClient:
    return BasalClient(
        url="http://basal.test/ask",
        timeout_s=1.0,
        transport=httpx.MockTransport(handler),
    )


def _ok(choice: str = "romance_scam") -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "answers": {
                "q": {
                    "type": "choice",
                    "choice": choice,
                    "probabilities": {"romance_scam": 0.94, "nigerian_419": 0.06},
                    "confidence": 0.94,
                }
            }
        },
    )


async def test_ask_choice_parses_answer():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return _ok()

    answer = await _client(handler).ask_choice("email text", "classify", CRITERIA)

    assert answer.answer == "romance_scam"
    assert answer.confidence == 0.94
    assert answer.probabilities == {"romance_scam": 0.94, "nigerian_419": 0.06}
    assert answer.latency_ms >= 0
    assert captured["state"] == "email text"
    q = captured["questions"]["q"]
    assert q["type"] == "choice"
    assert q["option_keys"] == "hide"
    assert q["instructions"] == "classify"
    assert q["criteria"] == CRITERIA


async def test_ask_choice_raises_on_5xx():
    client = _client(lambda r: httpx.Response(503))
    with pytest.raises(BasalUnavailableError) as exc:
        await client.ask_choice("s", "i", CRITERIA)
    assert exc.value.is_timeout is False


async def test_ask_choice_raises_on_timeout():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    with pytest.raises(BasalUnavailableError) as exc:
        await _client(handler).ask_choice("s", "i", CRITERIA)
    assert exc.value.is_timeout is True


async def test_ask_choice_raises_on_missing_answer_key():
    client = _client(lambda r: httpx.Response(200, json={"answers": {}}))
    with pytest.raises(BasalUnavailableError):
        await client.ask_choice("s", "i", CRITERIA)


async def test_ask_choice_raises_when_choice_not_in_criteria():
    client = _client(lambda r: _ok("other"))
    with pytest.raises(BasalUnavailableError):
        await client.ask_choice("s", "i", CRITERIA)


def test_settings_threshold_for_node():
    s = Settings(basal_threshold=0.9, basal_threshold_profiler=0.95)
    assert s.basal_threshold_for("profiler.attack_type") == 0.95
    assert s.basal_threshold_for("other.node") == 0.9


def test_settings_threshold_profiler_falls_back_to_default():
    s = Settings(basal_threshold=0.9, basal_threshold_profiler=None)
    assert s.basal_threshold_for("profiler.attack_type") == 0.9


def test_effective_mode_off_without_url():
    assert Settings(basal_url="", basal_mode="live").basal_effective_mode == "off"


def test_effective_mode_follows_mode_with_url():
    s = Settings(basal_url="http://basal.test", basal_mode="shadow")
    assert s.basal_effective_mode == "shadow"


@pytest.mark.parametrize("bad_choice", [["x"], {"a": 1}, 5, None])
async def test_ask_choice_raises_on_non_string_choice(bad_choice):
    client = _client(lambda r: _ok(bad_choice))
    with pytest.raises(BasalUnavailableError):
        await client.ask_choice("s", "i", CRITERIA)


def _resp(confidence, probabilities=None) -> httpx.Response:
    body = {
        "answers": {
            "q": {
                "type": "choice",
                "choice": "romance_scam",
                "probabilities": probabilities or {"romance_scam": 0.9},
                "confidence": confidence,
            }
        }
    }
    # json.dumps (unlike httpx json=) emits NaN, as a sloppy server would.
    return httpx.Response(200, content=json.dumps(body).encode())


@pytest.mark.parametrize("confidence", [94.0, float("nan"), -0.1, 1.01])
async def test_out_of_range_confidence_is_unavailable(confidence):
    with pytest.raises(BasalUnavailableError):
        await _client(lambda r: _resp(confidence)).ask_choice("t", "i", CRITERIA)


@pytest.mark.parametrize("bad", [94.0, float("nan"), -0.1])
async def test_out_of_range_probability_is_unavailable(bad):
    handler = lambda r: _resp(0.9, {"romance_scam": 0.9, "nigerian_419": bad})  # noqa: E731
    with pytest.raises(BasalUnavailableError):
        await _client(handler).ask_choice("t", "i", CRITERIA)


@pytest.mark.parametrize("edge", [0.0, 1.0])
async def test_boundary_confidence_is_accepted(edge):
    answer = await _client(lambda r: _resp(edge)).ask_choice("t", "i", CRITERIA)
    assert answer.confidence == edge


def test_basal_thresholds_must_be_within_unit_interval():
    from pydantic import ValidationError

    for kwargs in (
        {"basal_threshold": 90},
        {"basal_threshold": -0.1},
        {"basal_threshold_profiler": 90},
    ):
        with pytest.raises(ValidationError):
            Settings(**kwargs)
