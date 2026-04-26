---
name: check-all
description: Run the full quality gate for PhishGuard — backend + frontend in parallel. Use before committing any non-trivial change, before opening a PR, before merging to main, or when the user asks "is everything green / ready to ship". Combines `/check-backend` and `/check-frontend` with a single consolidated report.
---

# /check-all — Full-stack quality gate

**Arguments:** `$ARGUMENTS` — optional:
- empty → standard gate (backend + frontend, no e2e)
- `e2e` → also include Playwright E2E tests
- `fast` → backend `fast` mode (skip slow/integration) + frontend standard

## Your job

Run all backend and frontend checks in parallel and produce a single consolidated go/no-go report. This is the pre-commit / pre-PR gate. **Do not fix failures automatically.**

## Steps

1. **Run ALL checks in parallel** — six Bash calls in a single message:
   - `cd backend && uv run pytest -q` (use `-m "not slow and not integration"` if `fast`)
   - `cd backend && uv run ruff check .`
   - `cd backend && uv run ruff format --check .`
   - `cd frontend && npm run lint`
   - `cd frontend && npm run test`
   - `cd frontend && npx tsc --noEmit`

   Running all six in parallel is the whole point of this skill — do NOT call `/check-backend` then `/check-frontend` sequentially, that wastes wall time.

2. **If `$ARGUMENTS == "e2e"`**, run `cd frontend && npm run test:e2e` sequentially AFTER the parallel batch completes (Playwright is slow and contends for resources).

3. **Collect results**. Exit code 0 → PASS, non-zero → FAIL with last ~20 lines captured.

4. **Report** in this consolidated format:

   ```
   Full-stack quality gate

   Backend
     pytest          ✓  147 passed in 12.3s
     ruff check      ✓  clean
     ruff format     ✓  clean

   Frontend
     eslint          ✓  clean
     vitest          ✓  42 passed in 3.1s
     tsc --noEmit    ✓  clean

   Overall: READY TO SHIP ✓
   ```

   Or on failure:

   ```
   Full-stack quality gate

   Backend
     pytest          ✗  2 failed, 145 passed
     ruff check      ✓  clean
     ruff format     ✓  clean

   Frontend
     eslint          ✓  clean
     vitest          ✓  42 passed
     tsc --noEmit    ✗  1 type error

   Overall: NOT READY — 2 failing areas

   --- pytest failures ---
   <raw output>

   --- tsc failures ---
   <raw output>
   ```

5. **On any FAIL**:
   - Group failures by area (backend/frontend)
   - Ask: "Delegate backend fixes to `python-backend-dev` and frontend fixes to `nextjs-frontend-dev` in parallel?"
   - Do not proceed without confirmation

6. **On all PASS**: "Overall: READY TO SHIP ✓" plus one line with total wall time. Nothing else.

## Hard rules

- ALWAYS run all 6 checks in parallel (not sequential, not via sub-skills)
- Never skip a check because "it's probably fine"
- Never modify configs/tests to make the gate pass
- If the user already ran one of the checks recently and it passed, still re-run it here — the gate's value is that it's a single trustworthy snapshot

## Communication

- Polish if the user writes in Polish.
- Lead with the table. On green, the report IS the full response.
