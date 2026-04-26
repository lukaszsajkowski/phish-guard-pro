---
name: new-langgraph-node
description: Scaffold a new LangGraph node for the PhishGuard orchestrator (e.g. `/new-langgraph-node validate_iocs`). Use when the user wants to add a processing step to the workflow graph — creates the node function, state fields, graph wiring, and test stub following the existing pattern in `backend/src/phishguard/orchestrator/`.
---

# /new-langgraph-node — Scaffold a LangGraph node

**Arguments:** `$ARGUMENTS` — the node name in `snake_case` (e.g. `validate_iocs`, `enrich_wallet`). Required. Must be a valid Python identifier. If missing or invalid, ask.

## Your job

Create a new LangGraph node that plugs into PhishGuard's existing orchestrator without breaking the graph. This is a scaffolding skill — you produce a working skeleton, then hand off to the user (or delegate to `python-backend-dev` for the real business logic).

## Canonical files (ALWAYS read before scaffolding)

Before writing anything, Read these to match the current project pattern exactly — do not rely on memory:

- `backend/src/phishguard/orchestrator/state.py` — the `PhishGuardState` TypedDict / Pydantic model
- `backend/src/phishguard/orchestrator/nodes.py` — existing node functions (pattern to match)
- `backend/src/phishguard/orchestrator/graph.py` — how nodes are wired with `add_node` / `add_edge` / `add_conditional_edges`
- `backend/tests/` — find existing node tests (e.g. `tests/unit/orchestrator/test_nodes.py` or similar) to match the test pattern

## Steps

1. **Validate the node name** — must match `^[a-z][a-z0-9_]*$`, must NOT already exist in `nodes.py`. If invalid or duplicate, stop and ask.

2. **Read canonical files** (listed above). Extract:
   - How nodes are defined (async signature, return type, logging pattern, error handling)
   - What fields `PhishGuardState` currently has
   - How `graph.py` registers nodes and edges
   - Test file location and structure

3. **Confirm with user BEFORE editing** — produce a short plan:
   ```
   Scaffolding node: <name>

   - Add async function `<name>(state: PhishGuardState) -> dict[str, Any]` to orchestrator/nodes.py
   - (If needed) Add state fields: <list or "none">
   - Wire in graph.py:
       - add_node("<name>", <name>)
       - add_edge("<predecessor>", "<name>")   # ← ask user which predecessor
       - add_edge("<name>", "<successor>")     # ← ask user which successor
   - Add test stub at tests/unit/orchestrator/test_<name>.py

   Does this match your intent? Which existing nodes should this sit between?
   ```

   **Wait for user confirmation** — especially on the graph wiring. A wrong edge can deadlock the workflow or skip safety validation. Never guess this.

4. **After confirmation**, scaffold:

   **a. Node function in `nodes.py`** — match the existing async pattern exactly. Include:
   - Google-format docstring
   - `logger.info(...)` entry log with session_id
   - Input state access with defensive defaults
   - `TODO: implement` marker with a comment pointing to what the node should do
   - Return a dict with the state update

   **b. State fields** (only if needed) — modify `state.py` to add new fields. Use the existing typing style. Flag any type change clearly in the final report.

   **c. Graph wiring** — modify `graph.py`:
   - Add `from phishguard.orchestrator.nodes import <name>` to imports
   - Add `graph.add_node("<name>", <name>)` in the right section
   - Add edges per user's spec from step 3
   - If the user specified a conditional edge, use `add_conditional_edges` with a routing function stub

   **d. Test stub** at `backend/tests/unit/orchestrator/test_<name>.py` (or wherever the existing convention points):
   - Import the node function
   - One passing test that constructs a minimal `PhishGuardState` and asserts the node returns a dict
   - One `@pytest.mark.xfail(reason="not implemented")` test for the real behavior (with a clear TODO)
   - Follow the AAA pattern per CLAUDE.md

5. **Run the backend gate** after scaffolding:
   ```
   cd backend && uv run ruff check . && uv run ruff format --check . && uv run pytest tests/unit/orchestrator/ -q
   ```
   Report pass/fail. The scaffold MUST at least lint-clean and not break existing orchestrator tests.

6. **Final report** — list all files created/modified, the edges added, and the next step ("implement the TODO in nodes.py or run `/us-implement` if this node belongs to a specific user story").

## Hard rules

- Never skip the confirmation step in #3. Graph wiring is load-bearing and non-obvious.
- Never add edges to `END` or bypass `validate_safety` without asking — that would skip the safety layer.
- Never modify `checkpointer.py` from this skill.
- Never write business logic inside the scaffold — just the skeleton. Real logic is `python-backend-dev`'s job.
- If the canonical files have changed their pattern (e.g. nodes are now class-based instead of functions), adapt to the CURRENT pattern. Do not force the old one.

## Communication

- Polish if the user writes in Polish.
- Keep the plan in step 3 short and actionable.
- In the final report, use file_path:line_number references so the user can jump straight to the scaffolds.
