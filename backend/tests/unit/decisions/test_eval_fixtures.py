"""Schema checks for the profiler eval fixtures (US-053)."""

import json
from collections import Counter
from pathlib import Path

import pytest

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


@pytest.mark.xfail(
    strict=True,
    reason="credential_phishing rows pending blind re-review (fixtures README)",
)
def test_fixtures_cover_every_attack_type():
    counts = Counter(r["gold"] for r in _rows())

    for label in (a.value for a in AttackType):
        assert counts[label] >= 10, label


def test_fixtures_reviewed():
    rows = _rows()
    valid = {a.value for a in AttackType}

    for r in rows:
        assert r["reviewed"] or r["ambiguous"], r["id"]
        review = r["review"]
        assert isinstance(review, dict), r["id"]
        assert set(review) == {"label_b", "label_c", "reviewer_model"}, r["id"]
        assert review["label_b"] in valid, r["id"]
        assert review["label_c"] is None or review["label_c"] in valid, r["id"]
        assert review["reviewer_model"], r["id"]
        if not r["ambiguous"]:
            assert review["label_b"] == r["gold"] or review["label_c"] == r["gold"], r[
                "id"
            ]
    assert sum(r["ambiguous"] for r in rows) <= 0.1 * len(rows)
