---
name: us-status
description: Report implementation status of all PhishGuard user stories from the PRD (e.g. `/us-status`, `/us-status US-020..US-030`, `/us-status pending`). Use when the user asks what's done, what's left, what to work on next, or for a snapshot of project progress. Reads `.ai/prd.md` and cross-references with the codebase.
---

# /us-status — PRD vs code status report

**Arguments:** `$ARGUMENTS` — optional filter:
- empty → report on all user stories
- `US-020..US-030` → inclusive range
- `pending` / `done` / `in-progress` → filter by status
- `US-020` → single US deep-dive

## Your job

Produce a concise, accurate snapshot of which PRD user stories are implemented, partially implemented, or not started. **This is a read-only skill — never modify code or the PRD.**

## Method

1. **Parse the filter** from `$ARGUMENTS`.

2. **Enumerate user stories** in `.ai/prd.md` using Grep with pattern `^### US-\d+`. Capture for each: ID, title, and whether the heading contains `✅` (explicit done marker).

3. **For the selected stories**, determine real status using this 3-tier rubric:
   - **Done (✓)** — heading has `✅` AND at least one corresponding code artifact exists (search `backend/src/phishguard/` + `frontend/src/` for names/paths mentioned in the US body).
   - **Partial (~)** — code artifacts exist but no `✅`, OR `✅` present but key artifact missing (flag as inconsistency).
   - **Not started (✗)** — neither marker nor artifacts found.

   Do not trust `✅` alone. The PRD can drift from reality — your value is cross-referencing.

4. **Detect inconsistencies** and list them explicitly:
   - US marked ✅ but referenced code missing → likely stale PRD
   - Code exists matching US scope but no ✅ → likely forgot to update PRD
   - Tests missing for a ✅'d US → flag as "done without tests"

5. **Output format** — a single compact table plus an inconsistency section. Example:

```
PRD status (42 stories total, filter: pending)

US-032  ✓   Enhanced Risk Score          backend/services/risk_score_service.py
US-033  ~   IOC Enrichment Foundation    backend: stub, frontend: missing, tests: 0
US-034  ✗   IOC Enrichment UI            no artifacts

Inconsistencies:
- US-028 marked ✅ in PRD but `backend/src/phishguard/agents/summarizer.py` not found
- US-031 has implementation in `frontend/src/components/SessionTimeline.tsx` but no ✅

Suggested next: US-033 (blocks US-034, US-035)
```

6. **Performance** — for a full scan (all US), prefer a single PRD read plus targeted Globs, not per-US grep storms. If the PRD is very long, read it in chunks.

## Communication

- Polish if the user writes in Polish.
- Lead with the table. No preamble.
- If the user asked for a single US, expand to a deeper view: list acceptance criteria and mark each ✓/✗ based on code inspection.
