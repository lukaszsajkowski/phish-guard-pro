---
name: check-frontend
description: Run the frontend quality gate for PhishGuard — ESLint, Vitest, and TypeScript type-check. Use before committing frontend changes, before opening a PR touching `frontend/`, or when the user asks "is frontend green / clean / passing". Reports a concise pass/fail summary.
---

# /check-frontend — Frontend quality gate

**Arguments:** `$ARGUMENTS` — optional:
- empty → full gate (lint + unit tests + type-check)
- `e2e` → also run Playwright E2E: `npm run test:e2e`
- `<path>` → scope Vitest to that path, still run full lint + type-check

## Your job

Run the three canonical frontend checks in parallel, collect results, and produce a terse pass/fail table. **Do not fix failures automatically.** If something fails, surface it and ask whether to delegate to `nextjs-frontend-dev`.

## Steps

1. **Run in parallel** (three Bash calls in a single message):
   - `cd frontend && npm run lint`
   - `cd frontend && npm run test` (or scoped path per `$ARGUMENTS`)
   - `cd frontend && npx tsc --noEmit`

2. **If `$ARGUMENTS == "e2e"`**, also run `cd frontend && npm run test:e2e` sequentially after the parallel batch (Playwright is slow and resource-heavy).

3. **Parse results** — for each:
   - Exit code 0 → PASS
   - Non-zero → FAIL, capture the last ~20 lines of output

4. **Report** in this format:

   ```
   Frontend quality gate

   eslint          ✓  clean
   vitest          ✓  42 passed in 3.1s
   tsc --noEmit    ✗  2 type errors

   Overall: FAIL
   ```

5. **On any FAIL**:
   - Show raw failure output inline
   - Ask: "Delegate fix to `nextjs-frontend-dev`?" — do not proceed without confirmation

6. **On all PASS**: one-line confirmation.

## Hard rules

- Never use `--fix` on eslint without explicit user approval.
- Never modify `tsconfig.json`, eslint config, or test files to make the gate pass.
- `npx tsc --noEmit` is mandatory — `next build` alone does NOT catch all type errors (Next.js skips some type checks in dev).

## Communication

- Polish if the user writes in Polish.
- Lead with the table. Silence is good when everything is green.
