---
name: test-frontend
description: Run frontend test suites for PhishGuard — Vitest (unit/integration) and Playwright (E2E). `/test-frontend`, `/test-frontend unit`, `/test-frontend e2e`, `/test-frontend e2e ui`, `/test-frontend <path>`, `/test-frontend -t <name>`. Use when the user wants to run, re-run, or debug frontend tests without the full quality gate. Scoped runs, no auto-fix.
---

# /test-frontend — Run frontend unit and E2E tests

**Arguments:** `$ARGUMENTS` — optional:

**Scope selectors (first word):**
- empty / `unit` / `all` → Vitest one-shot on the whole `src/` suite
- `e2e` → Playwright on `frontend/e2e/`
- `<path>` under `src/**` → Vitest scoped to that file/dir
- `<spec>` under `e2e/**` → Playwright scoped to that spec file
- `-t <expr>` → Vitest test-name filter (`--testNamePattern`)

**Vitest modifiers** (combine with unit scope):
- `watch` → `npx vitest` (watch mode — runs in foreground, user Ctrl-C to stop)
- `coverage` → `npx vitest run --coverage`
- `verbose` → `--reporter=verbose`

**Playwright modifiers** (combine with `e2e`):
- `ui` → `--ui` (interactive UI mode)
- `headed` → `--headed` (see the browser)
- `debug` → `--debug` (step-through with inspector)
- `<spec>` → scoped spec file (e.g. `login.spec.ts` or `e2e/login.spec.ts`)
- `-g <expr>` → Playwright `--grep` filter

## Your job

Run the requested frontend test scope from `frontend/`, report a concise pass/fail summary, and surface failing output verbatim. **Do not** modify, skip, or `.skip()` tests to make them pass. **Do not** run ESLint or `tsc` — that's `/check-frontend`.

## Test layout (reference)

```
frontend/
├── src/
│   ├── **/__tests__/*.test.{ts,tsx}     ← Vitest unit/integration
│   └── __tests__/setup.ts                ← Vitest global setup
├── e2e/
│   ├── *.spec.ts                         ← Playwright E2E
│   └── global-teardown.ts
├── vitest.config.ts                      ← include: src/**/*.{test,spec}.{ts,tsx}
└── playwright.config.ts                  ← testDir: ./e2e, webServer: npm run dev
```

Key facts:
- Vitest `include` pattern: `src/**/*.{test,spec}.{ts,tsx}` — do not pass `e2e/` to Vitest; they're Playwright specs and will confuse the matcher.
- Playwright `webServer` is configured with `reuseExistingServer: true` — if `:3000` is already up (e.g. from `/run-frontend`), Playwright reuses it; otherwise it auto-starts `npm run dev` (up to 120s cold start).
- Playwright baseURL is `http://localhost:3000`. Most specs hit the backend at `:8000` — **E2E fails loudly if the backend is down**, so check before running.

## Steps

### 1. Parse `$ARGUMENTS`

Classify the first non-modifier word:

| First token | Runner | Target |
|---|---|---|
| empty / `unit` / `all` | Vitest | `src` (full include) |
| `e2e` | Playwright | `e2e/` |
| starts with `src/` or ends `.test.ts[x]` / `.spec.ts[x]` under `src/` | Vitest | that path |
| starts with `e2e/` or ends `.spec.ts` under `e2e/` | Playwright | that spec |
| `-t <expr>` | Vitest | `src --testNamePattern <expr>` |
| anything else | stop and show the user what you tried to resolve |

Apply modifiers for the chosen runner — reject modifiers that don't belong (e.g. `headed` on a Vitest run).

### 2. Preflight

Both runners:
- **`frontend/node_modules/` exists** — if not, stop and tell the user to run `cd frontend && npm install`. Do NOT run `npm install` automatically.

**Vitest only:**
- No further checks — Vitest is hermetic.

**Playwright only:**
- **Browsers installed** — the first Playwright run after a fresh clone needs `npx playwright install`. You cannot cheaply check this ahead of time; if the run fails with "Executable doesn't exist", surface that error and tell the user to run `cd frontend && npx playwright install`.
- **Backend reachability (warn, don't block)** — `curl -sf http://localhost:8000/health` with a 2s timeout. If it fails, warn before starting:
  ```
  ⚠ Backend at :8000 not reachable. E2E specs that hit the API will fail.
    Start with /run-backend (or /run-all), then re-run /test-frontend e2e.
  ```
  Ask the user whether to proceed anyway or abort. Default: abort — wasting 2 minutes on a flaky run is worse than stopping.
- **Frontend (`:3000`) is NOT a prerequisite** — Playwright's `webServer` auto-starts it via `npm run dev` and `reuseExistingServer: true` means an existing dev server will be reused. Mention this in the report if `:3000` was already up (the run will be faster).

### 3. Run

Single Bash call, from `frontend/`.

**Vitest default (one-shot):**
```
cd /Users/lukasz/Workspace/phish-guard-pro/frontend && npx vitest run <target> [--coverage] [--reporter=verbose] [--testNamePattern "<expr>"]
```
- NEVER use `npm run test` (that's watch mode and will hang). Use `npx vitest run`.
- `watch` modifier → `npx vitest <target>` (no `run`, foreground, inform the user "running in watch mode — Ctrl-C to stop").

**Playwright:**
```
cd /Users/lukasz/Workspace/phish-guard-pro/frontend && npx playwright test <target> [--ui|--headed|--debug] [--grep "<expr>"]
```
- `ui` and `debug` launch interactive windows — warn the user they'll need to drive the UI manually; the Bash call will block until they close the window.
- Default `reporter: html` in `playwright.config.ts` — after a fail, point the user at `frontend/playwright-report/index.html` with `npx playwright show-report`.

### 4. Report

**Vitest PASS** — one line with the summary Vitest prints:
```
Frontend tests ✓  42 passed in 3.1s  (scope: src)
```

**Vitest FAIL** — lead with counts, then the raw failing output (stack + assertion message). Don't paraphrase.
```
Frontend tests ✗  2 failed, 40 passed in 3.4s  (scope: src)

FAIL  src/components/__tests__/EmailInput.test.tsx > EmailInput > submits on Enter
<raw assertion + stack>
```
Ask: "Delegate fix to `nextjs-frontend-dev`?" — do not start fixing on your own.

**Playwright PASS:**
```
E2E tests ✓  21 passed in 47.2s  (scope: e2e)
  Reused dev server at http://localhost:3000        ← only if :3000 was up beforehand
```

**Playwright FAIL:**
```
E2E tests ✗  3 failed, 18 passed in 52.1s  (scope: e2e)

✘  [chromium] › login.spec.ts:14:3 › login redirects to dashboard
<raw error + failing step>
...

Report: npx playwright show-report (frontend/playwright-report/index.html)
Traces/screenshots: frontend/test-results/
```
Ask: "Delegate fix to `nextjs-frontend-dev`?"

**On missing browsers / collection error** — surface the error verbatim, don't report counts.

### 5. Coverage mode (Vitest)

- Command: `npx vitest run <target> --coverage`
- Requires `@vitest/coverage-v8` (already in devDependencies per `vitest.config.ts` provider: v8).
- On success, include the coverage summary table after the pass line (the per-file breakdown is the useful part — skip the header banner).

## Hard rules

- **Never** modify, `.skip()`, `.only()`, or delete tests to make them pass.
- **Never** run ESLint, `tsc`, Prettier — that's `/check-frontend`.
- **Never** touch `frontend/.env.local` / root `.env`.
- **Never** run `npm install` automatically — if deps are missing, stop and tell the user.
- **Never** run `npm run test` (watch-mode) for a one-shot run — always `npx vitest run`.
- **Never** auto-install Playwright browsers — `npx playwright install` has to be user-authorized (it downloads hundreds of MB).
- **Never** retry failing tests automatically. Flaky = bug = surface it.
- **Never** pass `--update-snapshots` / `-u` without explicit user request.
- **Never** start E2E with a known-down backend without confirmation — burning 2 minutes on red-by-design is worse than stopping.
- **Never** mix `e2e/` paths into a Vitest run (the `include` pattern won't match and you'll get 0 tests + misleading "pass").

## Examples

| User says | Command |
|---|---|
| `/test-frontend` | `npx vitest run src` |
| `/test-frontend unit` | `npx vitest run src` |
| `/test-frontend watch` | `npx vitest src` (foreground, Ctrl-C to stop) |
| `/test-frontend coverage` | `npx vitest run src --coverage` |
| `/test-frontend src/components/__tests__/EmailInput.test.tsx` | `npx vitest run src/components/__tests__/EmailInput.test.tsx` |
| `/test-frontend -t "submits on Enter"` | `npx vitest run src --testNamePattern "submits on Enter"` |
| `/test-frontend e2e` | `npx playwright test` |
| `/test-frontend e2e ui` | `npx playwright test --ui` |
| `/test-frontend e2e headed` | `npx playwright test --headed` |
| `/test-frontend e2e login.spec.ts` | `npx playwright test e2e/login.spec.ts` |
| `/test-frontend e2e -g "login"` | `npx playwright test --grep "login"` |

## Communication

- Polish if the user writes in Polish.
- Silence is good when green — one line per runner is enough.
- When red, the runner's output IS the response. No paraphrasing, no "I see X failing" summaries.
- Always include the scope + runner in the summary line — "Frontend tests" (Vitest) vs "E2E tests" (Playwright).
- For interactive Playwright modes (`ui`, `debug`), tell the user up front that the call will block until they close the window.
