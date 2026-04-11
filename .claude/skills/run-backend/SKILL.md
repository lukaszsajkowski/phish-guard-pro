---
name: run-backend
description: Start the PhishGuard FastAPI backend on port 8000, optionally with a local Supabase stack (`/run-backend`, `/run-backend with-supabase`, `/run-backend stop`). Use when the user wants to spin up the API for manual testing, debugging, or to pair with a running frontend. Handles env checks, port conflicts, health verification, and graceful teardown.
---

# /run-backend — Start the FastAPI backend

**Arguments:** `$ARGUMENTS` — optional:
- empty → start backend only (assumes Supabase is running OR env points at cloud Supabase)
- `with-supabase` → also start the local Supabase stack first (`supabase start`)
- `stop` → stop the backend (and Supabase if it was started by this skill)
- `status` → report whether backend and Supabase are currently running

## Ports owned by this skill

| Service | Port | URL |
|---|---|---|
| FastAPI backend | `8000` | http://localhost:8000 |
| FastAPI docs | `8000` | http://localhost:8000/docs |
| Supabase API (local) | `54321` | http://127.0.0.1:54321 |
| Supabase DB (local) | `54322` | `postgresql://postgres:postgres@127.0.0.1:54322/postgres` |
| Supabase Studio (local) | `54323` | http://127.0.0.1:54323 |
| Inbucket (email testing) | `54324` | http://127.0.0.1:54324 |

## Your job

Start the backend correctly on the first try. **Never** spawn processes blind — verify env, check ports, run in background, then health-check. On any failure, stop and tell the user what's wrong; do not "fix" configs silently.

## Steps

### Preflight (always run)

1. **Parse `$ARGUMENTS`.** If `stop` or `status`, jump to the corresponding section below.

2. **Check `.env` exists** — the root `.env` at `/Users/lukasz/Workspace/phish-guard-pro/.env` must be present (shared by backend and frontend). If missing, stop and tell the user:
   ```
   .env at project root is missing. Copy from .env.example and fill in:
     SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, OPENAI_API_KEY
   ```
   Do NOT create it from a template silently.

3. **Check port 8000 is free** — `lsof -ti :8000`. If something is listening:
   - If it's already a uvicorn process for this project → report "already running at http://localhost:8000" and exit (do not restart)
   - If it's something else → stop and show the PID/process; ask the user whether to kill it before starting

4. **Check dependencies** — `backend/.venv/` exists. If not, run `cd backend && uv sync` (foreground, show output). If `uv sync` fails, stop with the error.

### Supabase (only if `with-supabase`)

5. **Check Docker is running** — `docker info >/dev/null 2>&1`. If not, stop and tell the user to start Docker Desktop.

6. **Check if Supabase is already up** — `lsof -ti :54321`. If yes, skip the start step and report "Supabase already running".

7. **Start Supabase** — run `cd /Users/lukasz/Workspace/phish-guard-pro && supabase start` in **foreground** (it prints the anon key and local URLs, user needs those). This is the ONE foreground step — it takes 30–60s on cold start. On subsequent runs it's ~5s.

8. **Apply migrations** — `cd /Users/lukasz/Workspace/phish-guard-pro && supabase db reset` OR if the user has data they want to keep, skip this and report "migrations not applied; run `supabase db reset` manually if needed". **Ask before `db reset`** — it wipes local data.

### Start backend (always)

9. **Launch uvicorn in background**:
   ```
   cd /Users/lukasz/Workspace/phish-guard-pro/backend && uv run uvicorn src.phishguard.main:app --reload --port 8000
   ```
   Use `run_in_background: true`. Capture the shell ID.

10. **Wait for readiness** — poll `curl -sf http://localhost:8000/health` (or `/` if no health endpoint — Read `backend/src/phishguard/main.py` once to confirm what's exposed) up to ~10 seconds. Do NOT use `sleep N` loops; use Monitor on the background shell to wait for a "Uvicorn running on" log line, then curl once.

11. **Report** on success:
    ```
    Backend up ✓
      API:   http://localhost:8000
      Docs:  http://localhost:8000/docs
      PID:   <shell id>

    Supabase (local):          ← only if with-supabase
      API:     http://127.0.0.1:54321
      Studio:  http://127.0.0.1:54323
      Inbucket: http://127.0.0.1:54324
    ```

12. **On failure** — surface the uvicorn stderr verbatim. Common causes: missing env var, Supabase not reachable, import error, port race. Do not retry automatically.

### `stop` mode

- `lsof -ti :8000 | xargs kill` — kill the backend
- If the user also started Supabase via this skill in the same session, offer `cd /Users/lukasz/Workspace/phish-guard-pro && supabase stop` — **ask first**, because stopping Supabase kills local DB state
- Report what was stopped and what was left running

### `status` mode

Read-only. Report in a compact table:
```
Backend (:8000)           ✓ running   PID 12345   uptime ~3m
Supabase API (:54321)     ✓ running
Supabase Studio (:54323)  ✓ running
```
Use `lsof -ti :<port>` per port. No side effects.

## Hard rules

- **Never** write or overwrite the root `.env`. Missing env = stop and tell the user.
- **Never** run `supabase db reset` without explicit confirmation — it drops local data.
- **Never** `kill -9` without first trying graceful `kill`.
- **Never** start the backend on a port other than 8000 without explicit user request — the frontend hard-codes it as default.
- **Never** use blind `sleep` loops. Monitor the background shell or curl with a bounded retry.
- **Never** swallow stderr. If uvicorn fails, the error goes straight to the user.

## Communication

- Polish if the user writes in Polish.
- Lead with the outcome (up / down / failed). PIDs and URLs second.
- On `status`, the table is the entire response.
