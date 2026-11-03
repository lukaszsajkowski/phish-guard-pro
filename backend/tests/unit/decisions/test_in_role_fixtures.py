"""Schema checks for the in-role eval samples (US-050)."""

import json
from pathlib import Path

import pytest

FIXTURE = Path(__file__).parents[2] / "fixtures" / "eval" / "in_role_responses.jsonl"
GOLD = {"in_role", "breaks_role"}


def _rows() -> list[dict]:
    return [
        json.loads(line) for line in FIXTURE.read_text().splitlines() if line.strip()
    ]


def test_in_role_fixtures_schema():
    rows = _rows()

    assert len({r["id"] for r in rows}) == len(rows)
    for r in rows:
        assert r["gold"] in GOLD
        assert r["lang"] in {"pl", "en"}
        assert isinstance(r["response"], str) and r["response"].strip()
        assert set(r["persona"]) == {"persona_type", "age", "style_description"}
    real = [r for r in rows if not r["synthetic"]]
    synth = [r for r in rows if r["synthetic"]]
    assert len(real) >= 60
    assert sum(r["gold"] == "breaks_role" for r in synth) >= 40
    assert sum(r["gold"] == "in_role" for r in synth) >= 10


@pytest.mark.xfail(strict=True, reason="pending blind review")
def test_in_role_fixtures_reviewed():
    rows = _rows()

    for r in rows:
        assert r["reviewed"] or r["ambiguous"], r["id"]
    assert sum(r["ambiguous"] for r in rows) <= 0.1 * len(rows)
