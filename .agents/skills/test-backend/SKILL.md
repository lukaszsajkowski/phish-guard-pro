---
name: test-backend
description: Run backend pytest suites for PhishGuard — unit and/or integration (`/test-backend`, `/test-backend unit`, `/test-backend integration`, `/test-backend <path>`, `/test-backend -k <expr>`). Use when the user wants to run, re-run, or debug backend tests without the full quality gate. Scoped runs, verbose on failure, no auto-fix.
---

# /test-backend — Run backend unit and integration tests

**Arguments:** `$ARGUMENTS` — optional:
- empty → run the full suite: `uv run pytest -q`
- `unit` → only `backend/tests/unit/`
- `integration` → only `backend/tests/integration/`
- `all` → explicit alias for the full suite (same as empty)
- `<path>` → any path under `backend/tests/` (file or directory), e.g. `tests/unit/agents/test_profiler.py`
- `-k <expr>` → pass through a pytest `-k` keyword filter
- `failed` → re-run only last-failed tests (`--lf`), for iterating on a red run

Modifiers (can be combined with any of the above):
- `verbose` → `-vv` instead of `-q`
- `coverage` → add `--cov=src/phishguard --cov-report=term-missing` (requires `pytest-cov`; if not installed, stop and tell the user)

## Your job

Run the requested pytest scope from `backend/`, report a concise pass/fail summary, and surface failing test output verbatim. **Do not** modify, skip, or xfail tests to make them pass. **Do not** run linters — that's `/check-backend`.

## Test layout (reference)

```
backend/tests/
├── conftest.py
├── test_auth.py                ← top-level tests (run as part of "all")
├── test_email_analysis.py
├── test_health.py
├── unit/
│   ├── agents/  api/  core/  llm/  models/  safety/  services/
│   └── test_unmasking_detector.py
└── integration/
    ├── test_intel_dashboard.py
    └── test_response_generation.py
```

pytest config lives in `backend/pyproject.toml`:
- `asyncio_mode = "auto"` — async tests auto-discovered, no `@pytest.mark.asyncio` needed
- `testpaths = ["tests"]`
- No custom markers defined — **scope by directory, not by `-m`**

## Steps

### 1. Parse `$ARGUMENTS`

Resolve the scope token (first non-modifier word) to a pytest target:

| Token | pytest target |
|---|---|
| empty / `all` | `tests` |
| `unit` | `tests/unit` |
| `integration` | `tests/integration` |
| `failed` | `tests --lf` |
| anything starting with `tests/` or `backend/tests/` | that exact path |
| starts with `-k` | `tests -k "<expr>"` |
| other | treat as a path relative to `backend/`; if it does not exist under `backend/`, stop and show the user what you tried |

Resolve modifiers:
- `verbose` → swap `-q` for `-vv`
- `coverage` → append `--cov=src/phishguard --cov-report=term-missing`

If both `unit` and `integration` appear, run them as a single invocation: `uv run pytest -q tests/unit tests/integration`.

### 2. Preflight

- **venv present** — `backend/.venv/` must exist. If missing, stop and tell the user to run `cd backend && uv sync`. Do NOT run `uv sync` automatically (it can pull network dependencies the user may not expect).
- **Target exists** — if a resolved path does not exist on disk, stop before invoking pytest and show the user the path you resolved.

### 3. Run pytest

Single Bash call:

```
cd /Users/lukasz/Workspace/phish-guard-pro/backend && uv run pytest <flags> <target>
```

Defaults: `-q` (quiet). Always run in **foreground** — tests are the output.

Do NOT:
- default to `--lf` / `--ff` (hides real failures)
- add `-x` unless the user asks (fail-fast masks the full picture)
- add `--no-cov` or tweak warnings filters silently

### 4. Report

**On PASS** — one-line confirmation, include the summary line pytest prints:

```
Backend tests ✓  147 passed in 12.3s  (scope: tests/unit)
```

**On FAIL** — lead with the count, then the raw failing output (last ~40 lines of pytest stdout, untrimmed around the FAILED lines):

```
Backend tests ✗  3 failed, 144 passed in 14.1s  (scope: tests)

FAILED tests/unit/agents/test_profiler.py::test_classifies_romance_scam
<raw pytest error block>
...
```

Then ask: "Delegate fix to `python-backend-dev`?" — do not start fixing on your own.

**On collection error** (pytest returns exit code 2) — surface the collection error verbatim. Common causes: import error in a test module, fixture not found, syntax error. This is not a "test failure"; treat it as a hard stop and do not report counts.

### 5. Coverage mode specifics

If `coverage` was requested:
- Verify `pytest-cov` is available: the run will fail fast with "unrecognized arguments: --cov" if it isn't — in that case report "pytest-cov not installed; add to `dev` group in `backend/pyproject.toml`" and stop.
- On success, after the summary, include the last ~25 lines of the coverage table (the per-file breakdown is the useful part; the banner header is noise).

## Hard rules

- **Never** modify, skip, xfail, or delete tests to make them pass.
- **Never** run `ruff` / `mypy` / formatters — that's `/check-backend`.
- **Never** touch `backend/.env` or any fixture data file.
- **Never** run `uv sync` automatically — if deps are missing, stop and tell the user.
- **Never** auto-retry failed tests. Flaky tests are bugs; surface them.
- **Never** pass `-x` / `--lf` / `--ff` unless the user explicitly asks (`failed` keyword handles `--lf`).
- **Never** swallow stderr. Collection and runtime errors go to the user verbatim.

## Examples

| User says | Command |
|---|---|
| `/test-backend` | `uv run pytest -q tests` |
| `/test-backend unit` | `uv run pytest -q tests/unit` |
| `/test-backend integration` | `uv run pytest -q tests/integration` |
| `/test-backend unit verbose` | `uv run pytest -vv tests/unit` |
| `/test-backend tests/unit/agents/test_profiler.py` | `uv run pytest -q tests/unit/agents/test_profiler.py` |
| `/test-backend -k profiler` | `uv run pytest -q tests -k "profiler"` |
| `/test-backend failed` | `uv run pytest -q tests --lf` |
| `/test-backend unit coverage` | `uv run pytest -q tests/unit --cov=src/phishguard --cov-report=term-missing` |

## Communication

- Polish if the user writes in Polish.
- Silence is good when green — one line is enough.
- When red, the pytest output IS the response. No paraphrasing, no "I see a failure in X" summaries.
- Always include the scope in the summary line — it's easy to lose track of whether you ran unit or everything.
