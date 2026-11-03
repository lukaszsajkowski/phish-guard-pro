"""Tests for load_in_role_decisions and write_decisions_report (US-050)."""

import json
from pathlib import Path
from unittest.mock import patch

from phishguard.decisions.eval.binary import write_decisions_report
from phishguard.decisions.eval.sources import load_in_role_decisions

META = {"date": "2026-11-03"}


class FakeQuery:
    def __init__(self, client: "FakeClient", table: str) -> None:
        self.client = client
        self.table = table
        self.filters: list[tuple] = []

    def select(self, *_a):
        return self

    def eq(self, col, val):
        self.filters.append(("eq", col, val))
        return self

    def in_(self, col, vals):
        self.filters.append(("in", col, list(vals)))
        return self

    def order(self, *_a, **_k):
        return self

    def execute(self):
        self.client.queries.append((self.table, self.filters))
        rows = self.client.data[self.table]
        for kind, col, val in self.filters:
            if kind == "eq":
                rows = [r for r in rows if r.get(col) == val]
            else:
                rows = [r for r in rows if r.get(col) in val]

        class Result:
            data = rows

        return Result()


class FakeClient:
    def __init__(self, decisions: list[dict], messages: list[dict]) -> None:
        self.data = {"decisions": decisions, "messages": messages}
        self.queries: list[tuple] = []

    def table(self, name: str) -> FakeQuery:
        return FakeQuery(self, name)


def _decision(
    id_, message_id, created_at, answer="breaks_role", node="response.in_role"
):
    return {
        "id": id_,
        "node": node,
        "message_id": message_id,
        "created_at": created_at,
        "basal_answer": answer,
        "basal_confidence": 0.9,
        "skip_reason": None,
        "threshold": 0.5,
        "mode": "live",
    }


def _load(decisions, messages):
    client = FakeClient(decisions, messages)
    with patch(
        "phishguard.decisions.eval.sources._get_supabase_client", return_value=client
    ):
        return load_in_role_decisions(), client


def test_filters_by_node_and_fetches_content_by_message_id():
    decisions = [
        _decision("d1", "m1", "2026-11-01T10:00"),
        _decision("d2", "m2", "2026-11-01T11:00", node="profiler.attack_type"),
    ]
    messages = [{"id": "m1", "content": "hello"}, {"id": "m2", "content": "other"}]

    rows, client = _load(decisions, messages)

    assert [r["id"] for r in rows] == ["d1"]
    assert rows[0]["content"] == "hello"
    assert rows[0]["superseded"] is False
    assert ("decisions", [("eq", "node", "response.in_role")]) in client.queries
    assert ("messages", [("in", "id", ["m1"])]) in client.queries


def test_message_lookup_is_batched_by_100():
    decisions = [
        _decision(f"d{i}", f"m{i:03}", f"2026-11-01T10:{i:03}") for i in range(250)
    ]
    messages = [{"id": f"m{i:03}", "content": f"t{i}"} for i in range(250)]

    rows, client = _load(decisions, messages)

    message_queries = [q for q in client.queries if q[0] == "messages"]
    assert [len(q[1][0][2]) for q in message_queries] == [100, 100, 50]
    assert all(r["content"] is not None for r in rows)


def test_missing_message_and_null_message_id():
    decisions = [
        _decision("d1", "gone", "2026-11-01T10:00"),
        _decision("d2", None, "2026-11-01T11:00"),
    ]

    rows, _ = _load(decisions, [])

    assert [r["content"] for r in rows] == [None, None]
    assert [r["superseded"] for r in rows] == [False, False]


def test_earlier_rows_for_same_message_are_superseded_without_text():
    decisions = [
        _decision("d2", "m1", "2026-11-01T12:00", answer="in_role"),
        _decision("d1", "m1", "2026-11-01T10:00"),
    ]

    rows, _ = _load(decisions, [{"id": "m1", "content": "edited text"}])

    by_id = {r["id"]: r for r in rows}
    assert by_id["d2"]["superseded"] is False
    assert by_id["d2"]["content"] == "edited text"
    assert by_id["d1"]["superseded"] is True
    assert by_id["d1"]["content"] is None


def test_report_excludes_superseded_from_review_and_lists_them(tmp_path: Path):
    def row(id_, mid, ts, superseded, content):
        return {
            **_decision(id_, mid, ts),
            "superseded": superseded,
            "content": content,
        }

    rows = [
        row("d1", "m1", "2026-11-01T10:00", True, None),
        row("d2", "m1", "2026-11-01T12:00", False, "still bad"),
        row("d3", None, "2026-11-01T13:00", False, None),
        row("d4", "gone", "2026-11-01T14:00", False, None),
    ]

    write_decisions_report(rows, tmp_path, META)

    report = (tmp_path / "report.md").read_text(encoding="utf-8")
    review, superseded = report.split("## Superseded decisions (reply later edited)")
    assert "- breaks_role: 4" in review  # superseded still counted
    assert review.count("### ") == 3
    assert "> still bad" in review
    assert "(no message linked)" in review
    assert "(reply text unavailable)" in review
    assert "d1 | 2026-11-01T10:00 | breaks_role | 0.90" in superseded
    assert "d2" not in superseded
    assert "current text not shown for review" in superseded
    results = (tmp_path / "results.jsonl").read_text(encoding="utf-8").splitlines()
    assert json.loads(results[0])["id"] == "d1"


def test_report_has_no_superseded_section_when_none(tmp_path: Path):
    rows = [
        {
            **_decision("d1", "m1", "2026-11-01T10:00"),
            "superseded": False,
            "content": "x",
        }
    ]

    write_decisions_report(rows, tmp_path, META)

    assert "Superseded" not in (tmp_path / "report.md").read_text(encoding="utf-8")
