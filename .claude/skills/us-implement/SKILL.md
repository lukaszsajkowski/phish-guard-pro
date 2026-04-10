---
name: us-implement
description: Implement a PhishGuard user story from the PRD by its ID (e.g. `/us-implement US-015`). Use when the user wants to start, plan, or continue work on a specific user story. Extracts the US from `.ai/prd.md`, surveys current code state, and delegates execution to the `project-orchestrator` subagent.
---

# /us-implement — Implement a user story from the PRD

**Arguments:** `$ARGUMENTS` — a user story ID in the form `US-XXX` (e.g. `US-015`). If no ID is provided, ask the user which US they want before proceeding.

## Your job

Drive the end-to-end implementation of the requested user story by delegating to the `project-orchestrator` subagent. **You do not write implementation code in this skill** — orchestrator owns planning and delegation to the specialized dev subagents.

## Steps

1. **Resolve the US ID** from `$ARGUMENTS`. Validate it matches the pattern `US-\d{3}`. If missing or malformed, ask the user.

2. **Extract the user story from the PRD.** Use Grep on `.ai/prd.md` with pattern `^### US-XXX` to find the anchor, then Read the surrounding section (typically ~20–40 lines after the anchor, until the next `### US-` heading). Capture:
   - Title and status (look for `✅` — if already marked done, warn the user and ask whether to re-implement, extend, or abort)
   - Description / user-facing goal
   - Acceptance criteria
   - Any referenced FRs, NFRs, or dependencies

3. **Survey current code state** relevant to the US. Use Glob/Grep to check:
   - `backend/src/phishguard/` — agents, models, API routers, orchestrator nodes
   - `frontend/src/` — pages, components, hooks
   - `backend/tests/` — existing test coverage
   Produce a brief inventory: what exists, what is partial, what is missing.

4. **Delegate to `project-orchestrator`** via the Agent tool (`subagent_type: "project-orchestrator"`). The prompt MUST be self-contained and include:
   - The full US excerpt from step 2 (do not make the subagent re-read the PRD)
   - The code-state inventory from step 3
   - An explicit instruction to produce a task breakdown and execute it by delegating to the dev subagents (`python-backend-dev`, `nextjs-frontend-dev`, `test-engineer`, `security-safety-engineer`, `prompt-engineer`)
   - A request to report back with: tasks completed, tests added, lint/type status, and any open questions

5. **After orchestrator returns**, run verification yourself in parallel where possible:
   - Backend changed → `cd backend && uv run pytest -q` and `uv run ruff check .`
   - Frontend changed → `cd frontend && npm run lint` and `npm run test`
   Report pass/fail concisely. On failure, delegate the fix back to the appropriate subagent with the error output.

6. **Cross-check acceptance criteria** from step 2 one by one and produce a final checklist (✓/✗) for the user.

## Communication

- Respond in Polish if the user writes in Polish (this project's default).
- Be terse. The user wants outcomes, not narration of every tool call.
- If the US is ambiguous or conflicts with existing code, stop and ask before delegating — a wrong-direction delegation burns a full subagent cold-start.
