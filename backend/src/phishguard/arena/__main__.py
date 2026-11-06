"""CLI: python -m phishguard.arena run [...]."""

import argparse
import asyncio
import sys
from pathlib import Path

from phishguard.arena.runner import (
    DEFAULT_SCENARIOS_DIR,
    REPO_ROOT,
    default_out_dir,
    run_arena,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m phishguard.arena")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="Run scenarios against the selected systems")
    run.add_argument("--scenarios", type=Path, default=DEFAULT_SCENARIOS_DIR)
    run.add_argument("--scenario", action="append", default=None, metavar="ID")
    run.add_argument("--repetitions", type=int, default=3)
    run.add_argument(
        "--system", choices=["phishguard", "baseline", "both"], default="both"
    )
    run.add_argument("--out", type=Path, default=None)
    run.add_argument("--concurrency", type=int, default=4)
    report = sub.add_parser("report", help="Write EVALS.md and the chart from results")
    report.add_argument("--results", type=Path, default=None)
    report.add_argument("--excerpt", default=None, metavar="STEM")
    report.add_argument("--out", type=Path, default=REPO_ROOT / "EVALS.md")
    report.add_argument("--chart", type=Path, default=REPO_ROOT / "evals" / "chart.png")
    report.add_argument("--scenarios", type=Path, default=DEFAULT_SCENARIOS_DIR)
    return parser.parse_args(argv)


def _cost(entries) -> float:
    from phishguard.decisions.eval.metrics import llm_cost_usd

    return sum(
        llm_cost_usd(e.prompt_tokens, e.completion_tokens, e.model) for e in entries
    )


def _summary(record) -> str:
    reveals = {r for t in record.turns for r in t.detected_reveals}
    return (
        f"{record.scenario_id} {record.system} r{record.repetition}: "
        f"{record.status} ({record.end_reason}), {len(record.turns)} turns, "
        f"{len(reveals)} secrets revealed"
        + (f" [{record.status_reason}]" if record.status_reason else "")
    )


def _rel(path: Path) -> str:
    """Path relative to the repo root, with forward slashes (for Markdown links)."""
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _report(args: argparse.Namespace) -> int:
    from phishguard.arena.metrics import summarise
    from phishguard.arena.report import render_chart, render_markdown, select_excerpt
    from phishguard.arena.scenario import load_scenarios

    results = args.results
    if results is None:
        candidates = sorted(
            p for p in (REPO_ROOT / "evals" / "results").glob("*") if p.is_dir()
        )
        if not candidates:
            print("No results found in evals/results/", file=sys.stderr)
            return 2
        results = candidates[-1]
    if not (results / "run.json").exists():
        print(f"Not a results folder (no run.json): {results}", file=sys.stderr)
        return 2

    scenarios = {s.id: s for s in load_scenarios(args.scenarios)}
    summary = summarise(results, scenarios)
    try:
        excerpt = select_excerpt(results, args.excerpt, args.scenarios)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Cannot use --excerpt: {exc}", file=sys.stderr)
        return 2
    render_chart(summary, args.chart)
    text = render_markdown(
        summary,
        summary.meta,
        excerpt,
        _rel(args.chart),
        _rel(results),
        args.excerpt,
        args.scenarios,
    )
    args.out.write_text(text, encoding="utf-8")
    print(f"Wrote {args.out} and {args.chart}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.command == "report":
        return _report(args)
    from phishguard.arena.scenario import load_scenarios

    scenarios = load_scenarios(args.scenarios)
    if args.scenario:
        known = {s.id for s in scenarios}
        missing = [i for i in args.scenario if i not in known]
        if missing:
            print(f"Unknown scenario id(s): {', '.join(missing)}", file=sys.stderr)
            return 2
        scenarios = [s for s in scenarios if s.id in args.scenario]
    systems = ["phishguard", "baseline"] if args.system == "both" else [args.system]
    out_dir = args.out or default_out_dir()

    records = []

    def on_record(record) -> None:
        records.append(record)
        print(_summary(record), flush=True)

    asyncio.run(
        run_arena(
            scenarios,
            systems,
            args.repetitions,
            out_dir,
            args.concurrency,
            on_record=on_record,
        )
    )

    from phishguard.arena.setup import ScenarioSetup

    setup_usage = []
    for path in sorted((out_dir / "setup").glob("*.json")):
        setup_usage += ScenarioSetup.model_validate_json(
            path.read_text(encoding="utf-8")
        ).usage
    victim = _cost(setup_usage) + sum(_cost(r.victim_usage) for r in records)
    scammer = sum(_cost(r.scammer_usage) for r in records)
    print(f"Results: {out_dir}")
    print(
        f"Cost this run: victim ${victim:.4f}, scammer ${scammer:.4f}, "
        f"total ${victim + scammer:.4f}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
