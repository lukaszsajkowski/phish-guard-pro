---
name: run-frontend
description: Start the PhishGuard Next.js dev server on port 3000 (`/run-frontend`, `/run-frontend stop`, `/run-frontend status`). Use when the user wants to spin up the UI for manual testing or pair it with a running backend. Handles env checks, port conflicts, dependency install, backend reachability check, and graceful teardown.
---

# /run-frontend — Start the Next.js dev server

**Arguments:** `$ARGUMENTS` — optional:
- empty → start dev server (`npm run dev`)
- `stop` → kill the dev server
- `status` → report whether frontend is running
- `build` → run a production build instead of dev (for verifying build passes)

## Ports owned by this skill

| Service | Port | URL |
|---|---|---|
| Next.js dev server | `3000` | http://localhost:3000 |

## Your job

Start the Next.js dev server correctly and report its URL. Warn the user if the backend isn't reachable — the UI will render but most flows will fail. **Never** touch env files silently; surface missing config instead.

## Steps

### Preflight (always run)

1. **Parse `$ARGUMENTS`.** If `stop` / `status` / `build`, jump to the corresponding section.

2. **Check `.env.local` exists** — `frontend/.env.local` must be present. If missing, stop and tell the user:
   ```
   frontend/.env.local is missing. Copy from frontend/.env.example and fill in:
     NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY, NEXT_PUBLIC_API_URL
   ```
   Do NOT create it silently.

3. **Check port 3000 is free** — `lsof -ti :3000`. If taken:
   - If it's already a Next.js process → report "already running at http://localhost:3000" and exit
   - If it's something else → show the PID and ask whether to kill it

4. **Check dependencies** — `frontend/node_modules/` exists. If not, run `cd frontend && npm install` in foreground, show output. If install fails, stop.

5. **Check backend reachability** (non-blocking warning) — `curl -sf http://localhost:8000/health` with a 2s timeout. If it fails, continue anyway but include a warning in the final report:
   ```
   ⚠ Backend at :8000 not reachable. Run /run-backend first, or the UI will show fetch errors.
   ```

### Start frontend (default mode)

6. **Launch dev server in background**:
   ```
   cd /Users/lukasz/Workspace/phish-guard-pro/frontend && npm run dev
   ```
   Use `run_in_background: true`. Capture the shell ID.

7. **Wait for readiness** — use Monitor on the background shell to wait for a line matching "Ready in" or "compiled successfully" (Next.js 16 prints one of these when the dev server is listening). Do NOT use blind `sleep`. Timeout ~30s (Next.js 16 initial compile is slow).

8. **Report** on success:
   ```
   Frontend up ✓
     URL:  http://localhost:3000
     PID:  <shell id>

   ⚠ Backend at :8000 not reachable         ← only if step 5 warned
   ```

9. **On failure** — surface Next.js stderr verbatim. Common causes: TypeScript error, missing dependency after lockfile bump, port race, env var consumed at build time that's missing.

### `build` mode

- Run `cd frontend && npm run build` in **foreground** (this is a one-shot, not a long-running process).
- Report pass/fail with the last ~30 lines of output on failure.
- `build` does not require backend reachability.
- If build succeeds, print total time and suggest `/run-frontend` to start dev server.

### `stop` mode

- `lsof -ti :3000 | xargs kill` — kill the dev server
- Report what was stopped
- Do not touch the backend

### `status` mode

Read-only:
```
Frontend (:3000)          ✓ running   PID 12345
Backend  (:8000)          ✓ reachable               ← via curl /health
```
Report both ports because "frontend alone" is almost never useful.

## Hard rules

- **Never** write or overwrite `frontend/.env.local`. Missing env = stop and tell the user.
- **Never** start on a port other than 3000 without explicit request — backend CORS, Supabase `site_url`, and tests all assume 3000.
- **Never** auto-fix TypeScript errors to make `build` pass. Surface them and delegate to `nextjs-frontend-dev` if the user asks.
- **Never** use blind `sleep` loops. Monitor the background shell log.
- **Never** run `npm install --force` or `--legacy-peer-deps` without user consent.

## Communication

- Polish if the user writes in Polish.
- Lead with up/down/failed. URL and PID second. Warnings (backend unreachable) last.
- On `status`, the table is the full response.
