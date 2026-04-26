---
name: check-backend
description: Run the backend quality gate for PhishGuard — pytest, ruff check, and ruff format check. Use before committing backend changes, before opening a PR touching `backend/`, or when the user asks "is backend green / clean / passing". Reports a concise pass/fail summary.
---

# /check-backend — Backend quality gate

**Arguments:** `$ARGUMENTS` — optional:
- empty → full gate (pytest + ruff check + ruff format check)
- `fast` → skip slow/integration tests: `uv run pytest -q -m "not slow and not integration"`
- `<path>` → run pytest scoped to that path, still run full ruff on `backend/`

## Your job

Run the three canonical backend checks in parallel, collect results, and produce a terse pass/fail table. **Do not fix failures automatically.** If something fails, surface it and ask whether to delegate the fix.

## Steps

1. **Run in parallel** (three Bash calls in a single message):
   - `cd backend && uv run pytest -q` (or scoped variant per `$ARGUMENTS`)
   - `cd backend && uv run ruff check .`
   - `cd backend && uv run ruff format --check .`

2. **Parse results** — for each:
   - Exit code 0 → PASS
   - Non-zero → FAIL, capture the last ~20 lines of output

3. **Report** in this format:

   ```
   Backend quality gate

   pytest          ✓  147 passed in 12.3s
   ruff check      ✓  clean
   ruff format     ✗  3 files would be reformatted

   Overall: FAIL
   ```

4. **On any FAIL**:
   - Show the raw failure output inline (don't paraphrase — the user needs the actual error)
   - Ask: "Delegate fix to `python-backend-dev`?" — do not proceed without confirmation
   - For `ruff format` specifically: offer `uv run ruff format .` as a one-command fix if the user prefers that over subagent delegation

5. **On all PASS**: one-line confirmation. Nothing else.

## Hard rules

- Never run `ruff format .` (without `--check`) unless the user explicitly approves.
- Never run `pytest` with `--lf` or `--ff` as a default — those hide real failures.
- Never skip, xfail, or modify tests to make them pass.

## Communication

- Polish if the user writes in Polish.
- Lead with the table. Silence is good when everything is green.
