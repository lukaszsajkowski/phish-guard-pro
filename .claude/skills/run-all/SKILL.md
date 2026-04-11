---
name: run-all
description: Start the full PhishGuard stack — local Supabase + FastAPI backend + Next.js frontend — with health checks and dependency gating (`/run-all`, `/run-all stop`, `/run-all status`, `/run-all cloud` to skip local Supabase). Use when the user wants to spin up the entire app for end-to-end manual testing or a demo. Orchestrates the three `run-*` skills in the correct order with health-gated handoff.
---

# /run-all — Start the full PhishGuard stack

**Arguments:** `$ARGUMENTS` — optional:
- empty → full local stack: `supabase start` → backend → frontend
- `cloud` → skip local Supabase, assume env points at cloud Supabase
- `stop` → stop everything this skill started (frontend → backend → Supabase, reverse order)
- `status` → compact table of all services

## Ports owned by this skill

| Service | Port | URL |
|---|---|---|
| Next.js frontend | `3000` | http://localhost:3000 |
| FastAPI backend | `8000` | http://localhost:8000 |
| Supabase API | `54321` | http://127.0.0.1:54321 |
| Supabase DB | `54322` | `postgresql://postgres:postgres@127.0.0.1:54322/postgres` |
| Supabase Studio | `54323` | http://127.0.0.1:54323 |
| Inbucket | `54324` | http://127.0.0.1:54324 |

## Your job

Bring up the full stack in the correct dependency order, gate each step on a health check, and produce one consolidated report at the end. **Never start a downstream service before its upstream is healthy** — a frontend talking to a dead backend, or a backend talking to a dead DB, wastes the user's time with misleading errors.

## Dependency order (this is load-bearing)

```
Supabase (54321)  →  Backend (8000)  →  Frontend (3000)
```

- Backend reads env pointing at Supabase; if Supabase isn't up (and env is local), backend crashes on first DB call.
- Frontend hard-codes `NEXT_PUBLIC_API_URL` at build time; if backend isn't up, UI renders but all flows fail.
- `cloud` mode skips Supabase locally but still requires the env to point at a reachable cloud instance.

## Steps

### Preflight (always run)

1. **Parse `$ARGUMENTS`.** If `stop` / `status`, jump to the corresponding section.

2. **Check env file exists:**
   - `.env` at the project root (`/Users/lukasz/Workspace/phish-guard-pro/.env`) — shared by backend and frontend
   If missing, stop and tell the user. Do not create it.

3. **Check ports are free** — `lsof -ti :3000 :8000 :54321` in one call. If any port is taken:
   - Identify whether it's already part of this stack (uvicorn / next / supabase) — if yes, treat as "partially up" and reuse; if not, stop and ask whether to kill the offending process.

4. **Check Docker is running** (only if not `cloud` mode) — `docker info >/dev/null 2>&1`. If not, stop and tell the user to start Docker Desktop. Supabase local needs it.

### Start Supabase (skip if `cloud` mode)

5. **If port 54321 is free**, run `cd /Users/lukasz/Workspace/phish-guard-pro && supabase start` in **foreground** (prints anon key + URLs, user may need them). Cold start 30–60s, warm 5s.

6. **Health check** — `curl -sf http://127.0.0.1:54321/rest/v1/ -H "apikey: <anon-key-from-stdout>"` should return 200 or 404 (both mean the API is up). If neither, stop and surface error.

7. **Do NOT run `supabase db reset`** automatically. If the user wants migrations applied, they'll say so. If this is a fresh clone and the DB is empty, warn:
   ```
   ⚠ Local Supabase is up but no migrations applied. Run: supabase db reset
   ```

### Start backend

8. **Launch uvicorn in background:**
   ```
   cd /Users/lukasz/Workspace/phish-guard-pro/backend && uv run uvicorn src.phishguard.main:app --reload --port 8000
   ```
   Use `run_in_background: true`. Capture shell ID.

9. **Health check (gated)** — use Monitor on the background shell to wait for "Uvicorn running on" log line (timeout 15s). Then `curl -sf http://localhost:8000/health` (or `/` — Read `backend/src/phishguard/main.py` once to confirm the exposed path). If health fails, STOP the cascade — do not start frontend. Surface the backend stderr.

### Start frontend

10. **Launch Next.js dev in background:**
    ```
    cd /Users/lukasz/Workspace/phish-guard-pro/frontend && npm run dev
    ```
    Use `run_in_background: true`. Capture shell ID.

11. **Health check** — Monitor the background shell for "Ready in" or "compiled successfully" (timeout 30s; Next.js 16 initial compile is slow). Then `curl -sf http://localhost:3000` should return 200.

### Consolidated report

12. **On full success:**

    ```
    PhishGuard stack up ✓

    Supabase API     http://127.0.0.1:54321
    Supabase Studio  http://127.0.0.1:54323
    Inbucket         http://127.0.0.1:54324
    Backend          http://localhost:8000        PID <id>
      └ docs         http://localhost:8000/docs
    Frontend         http://localhost:3000        PID <id>

    Total startup: ~42s
    Stop with: /run-all stop
    ```

13. **On partial failure** — report what's up, what failed, the error output verbatim, and the recovery command (e.g. "Backend failed. Supabase and no frontend started. Fix backend and re-run `/run-all`").

### `stop` mode (reverse dependency order)

1. `lsof -ti :3000 | xargs kill` — frontend first (harmless to kill under load)
2. `lsof -ti :8000 | xargs kill` — backend next (LangGraph state is checkpointed in DB, so this is safe)
3. **Ask before** `cd /Users/lukasz/Workspace/phish-guard-pro && supabase stop` — stopping Supabase drops the local DB container; user may not want that if they have in-progress test data
4. Report what was stopped and what was skipped

### `status` mode

Read-only consolidated table:
```
Frontend    (:3000)  ✓ running   PID 11111
Backend     (:8000)  ✓ running   PID 22222
Supabase    (:54321) ✓ running
  └ Studio  (:54323) ✓ running
  └ Inbucket(:54324) ✓ running
```
If Supabase ports are down but backend is up, check whether backend is pointed at cloud (root `.env` SUPABASE_URL starts with `http://127.0.0.1` or not) and label accordingly: `Supabase (cloud) — not checked`.

## Hard rules

- **Never** start frontend before backend is health-green
- **Never** start backend before Supabase is health-green (unless `cloud` mode)
- **Never** run `supabase db reset` automatically
- **Never** create `.env` or `.env.local` files
- **Never** kill processes with `-9` without trying graceful kill first
- **Never** use blind `sleep N` loops — always Monitor the background shell log
- **Never** silently swallow stderr from any of the three services
- **Never** parallelize the startup. The dependency order is sequential for a reason — parallel start makes flaky-failure debugging a nightmare.

## Communication

- Polish if the user writes in Polish.
- The consolidated report IS the response on success. No narration of each step.
- On failure, lead with "STOPPED at stage X" then the error, then the recovery command.
- On `status`, the table is the full response.
