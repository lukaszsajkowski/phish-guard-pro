"""Schema checks for the profiler eval fixtures (US-053)."""

import json
from collections import Counter
from pathlib import Path

from phishguard.models.classification import AttackType

FIXTURE = Path(__file__).parents[2] / "fixtures" / "eval" / "profiler_emails.jsonl"
KEYS = {"id", "lang", "gold", "reviewed", "ambiguous", "email", "notes", "review"}


def _rows() -> list[dict]:
    return [
        json.loads(line) for line in FIXTURE.read_text().splitlines() if line.strip()
    ]


def test_fixtures_schema():
    rows = _rows()
    valid = {a.value for a in AttackType}

    assert 90 <= len(rows) <= 110
    assert len({r["id"] for r in rows}) == len(rows)
    for r in rows:
        assert set(r) == KEYS
        assert r["gold"] in valid
        assert r["lang"] in {"pl", "en"}
        assert isinstance(r["email"], str) and r["email"].strip()
    counts = Counter(r["gold"] for r in rows)
    for label in valid:
        assert counts[label] >= 10, label


def test_fixtures_reviewed():
    rows = _rows()
    valid = {a.value for a in AttackType}

    for r in rows:
        assert r["reviewed"] or r["ambiguous"], r["id"]
        if r["review"] is not None:
            assert r["review"]["label_b"] in valid
    assert sum(r["ambiguous"] for r in rows) <= 0.1 * len(rows)
