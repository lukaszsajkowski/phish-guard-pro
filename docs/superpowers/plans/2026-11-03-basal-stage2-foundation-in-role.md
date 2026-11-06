# Basal Stage 2 — Foundation + In-Role Check Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the decision layer a per-node mode and a "signal" mode (Basal next to a deterministic reference instead of a Basal → LLM cascade), and ship the first signal node end to end: `response.in_role`, a Basal check that warns the user when a generated or edited reply breaks the persona's role.

**Architecture:** Each node gets its own `DecisionService` built by `create_decision_service(node=...)`, with mode and threshold resolved per node from settings. A new `DecisionService.decide_signal()` asks Basal and logs a `decisions` row; in `shadow` it runs in the background and returns the reference, in `live` it awaits Basal and returns Basal's answer at or above the threshold. `check_in_role()` wraps it for the in-role node and is called from `/response/generate` and `/response/validate`; the warning travels to the chat message in the UI. The eval CLI gains an `in-role` subcommand and a sample generator.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, Supabase (sync client, service role), pytest + pytest-asyncio, Next.js 16 / React 19 / Vitest.

**Spec:** `docs/superpowers/specs/2026-11-03-basal-stage2-design.md` (Polish). Read it before starting any task. This plan covers phases 0, A and B. Phase C (`scammer.unmasking`, `scammer.urgency`) gets its own plan after the data reconnaissance (phase R).

## Global Constraints

- Node names: `profiler.attack_type` (existing), `response.in_role` (new). In-role option keys: exactly `in_role`, `breaks_role`.
- Settings (env, case-insensitive), new: `BASAL_MODE_PROFILER`, `BASAL_MODE_IN_ROLE` (each `off|shadow|live`, optional, overrides `BASAL_MODE` for that node), `BASAL_THRESHOLD_IN_ROLE` (optional float 0–1, overrides `BASAL_THRESHOLD`). Existing settings keep their meaning. Empty `BASAL_URL` forces every node to `off`.
- Mode and thresholds change only via `.env` + backend restart.
- Basal decides / flags when `confidence >= threshold` (inclusive).
- `decisions.source` values: `llm`, `basal`, `basal_low_confidence` (existing) plus `regex`, `none` (new). `decisions.reference_kind`: `llm`, `regex` or null.
- `decisions` rows never store email text or reply text. The reply is reachable only through `message_id`.
- Basal never blocks, rewrites or sends a reply, and never ends a session. The in-role result is a warning only.
- A Basal failure, timeout, language-gate rejection or failed DB write never fails `/response/generate` or `/response/validate`.
- The PII validator (`safety/output_validator.py`) is not modified.
- The Profiler's behaviour does not change; only its factory call and the new reference columns on its rows.
- Warning copy (UI, exact): `This reply may break the persona's role. Review it before sending.` followed by ` (Basal, p=0.87)` with the confidence to two decimals.
- Commit style: conventional commits with US scope (`feat(US-056): ...`), no Co-Authored-By line (project `/commit` rule).
- Backend gate after each backend task: `cd backend && uv run pytest -q && uv run ruff check . && uv run ruff format --check .`. Frontend gate after the frontend task: `/check-frontend`.

## Review Focus

1. **Basal times out or is down while `response.in_role` is `live`.** Expected: `/response/generate` returns normally with `in_role_warning: null`; the row has `skip_reason="timeout"` or `"unavailable"`. Tests in Task 3 and Task 5.
2. **User edits a flagged reply into an in-role one.** Expected: `/response/validate` returns `in_role_warning: null` and the UI removes the warning from that message. Tests in Task 5 and Task 6.
3. **Edited content fails the PII check.** Expected: violations returned as today, Basal never called for that content. Test in Task 5.
4. **Session has no persona when `/response/validate` runs.** Expected: validation result as today, `in_role_warning: null`, no 500. Test in Task 5.
5. **Global `BASAL_MODE=live` with `BASAL_MODE_PROFILER=off`.** Expected: the Profiler service is `off`, the in-role service is `live`. Test in Task 1.

---

### Task 1: Per-node mode and threshold (US-056)

**Files:**
- Modify: `backend/src/phishguard/core/__init__.py` (Basal settings block and the two methods below it)
- Modify: `backend/src/phishguard/decisions/cascade.py` (`create_decision_service`)
- Modify: `backend/src/phishguard/agents/profiler.py:107` (pass the node)
- Modify: `.env.example` (Basal block: the three new variables, commented, one line each)
- Test: `backend/tests/unit/decisions/test_settings_nodes.py`, `backend/tests/unit/decisions/test_cascade.py`

**Interfaces:**
- Produces:
  - `Settings.basal_mode_profiler: Literal["off","shadow","live"] | None = None`, `Settings.basal_mode_in_role: ... | None = None`, `Settings.basal_threshold_in_role: float | None = Field(None, ge=0, le=1)`
  - `Settings.basal_mode_for(node: str) -> Literal["off","shadow","live"]`: node override if set, else `basal_mode`; always `"off"` when `basal_url` is empty
  - `Settings.basal_threshold_for(node: str) -> float`: node override if set (`profiler.attack_type` → `basal_threshold_profiler`, `response.in_role` → `basal_threshold_in_role`), else `basal_threshold`
  - `create_decision_service(settings: Settings | None = None, *, node: str = "profiler.attack_type") -> DecisionService` using `settings.basal_mode_for(node)`
  - `Settings.basal_effective_mode` stays (used elsewhere) and equals `basal_mode_for("profiler.attack_type")`

- [ ] **Step 1: Write failing tests** in `test_settings_nodes.py`, parametrized: `(BASAL_MODE, override, url) → expected` for both nodes, including `("live", {"basal_mode_profiler": "off"}, url) → profiler off, in_role live` (Review Focus 5) and empty url → off for both; thresholds: in-role override 0.8 vs global 0.9; unknown node → global. In `test_cascade.py`: `create_decision_service(settings, node="response.in_role").mode == "live"` while the profiler service is `"off"`.
- [ ] **Step 2: Run** `cd backend && uv run pytest tests/unit/decisions/test_settings_nodes.py tests/unit/decisions/test_cascade.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** the settings, the factory and the Profiler call (`create_decision_service(node=PROFILER_NODE)`). Existing positional calls `create_decision_service(settings)` keep working.
- [ ] **Step 4: Run** the same command (PASS), then the backend gate.
- [ ] **Step 5: Commit** `feat(US-056): resolve Basal mode and threshold per decision node`

### Task 2: `decisions` migration + recorder fields (US-056)

**Files:**
- Create: `supabase/migrations/20261103120000_decisions_signal_mode.sql`
- Modify: `backend/src/phishguard/decisions/recorder.py` (`DecisionRecord`)
- Modify: `backend/src/phishguard/decisions/cascade.py` (`_record`: Profiler rows get `reference_kind="llm"`, `reference_answer=<llm answer>`)
- Test: `backend/tests/unit/decisions/test_recorder.py`, `backend/tests/unit/decisions/test_cascade.py`

**Interfaces:**
- Produces: `DecisionRecord` gains `message_id: str | None = None`, `reference_kind: str | None = None`, `reference_answer: str | None = None` (defaults keep existing constructors valid).

Migration content: `message_id uuid null references public.messages(id) on delete cascade`; `reference_kind text null check (reference_kind in ('llm','regex'))`; `reference_answer text null`; replace the `source` check with one allowing `('basal','llm','basal_low_confidence','regex','none')`; backfill `reference_kind='llm', reference_answer=llm_answer where node='profiler.attack_type'`; index on `message_id`. Header comment in the style of `20261102120000_create_decisions.sql`.

- [ ] **Step 1: Write failing tests:** `test_record_decision_sends_new_fields` (patched `_get_supabase_client`, asserts `message_id`, `reference_kind`, `reference_answer` in the inserted dict); in `test_cascade.py`, a shadow Profiler decision's recorded row has `reference_kind == "llm"` and `reference_answer == llm answer`.
- [ ] **Step 2: Run** `uv run pytest tests/unit/decisions/test_recorder.py tests/unit/decisions/test_cascade.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** the dataclass fields, the `_record` change and the migration.
- [ ] **Step 4: Run** (PASS) and the gate. Apply locally: `supabase migration up --local`, then confirm with `docker exec supabase_db_phish-guard-pro psql -U postgres -c '\d decisions'` that the three columns exist and existing profiler rows have `reference_kind = 'llm'`. If local Supabase is not running, say so in the commit body.
- [ ] **Step 5: Commit** `feat(US-056): add message and reference columns to decisions`

### Task 3: Signal mode in `DecisionService` (US-056)

**Files:**
- Modify: `backend/src/phishguard/decisions/cascade.py`
- Modify: `backend/src/phishguard/decisions/__init__.py` (export the new names)
- Test: `backend/tests/unit/decisions/test_signal.py`

**Interfaces:**
- Consumes: Task 1 factory, Task 2 `DecisionRecord` fields.
- Produces:
  - `SignalSource = Literal["basal", "regex", "none"]`
  - `@dataclass(frozen=True) SignalDecision(source: SignalSource, answer: str | None, basal: BasalAnswer | None)`
  - `DecisionService.decide_signal(question: ChoiceQuestion, state: str, session_id: str | None, message_id: str | None = None, reference_kind: Literal["regex"] | None = None, reference_answer: str | None = None) -> SignalDecision`

Behaviour (copy into the docstring):
- Reference result = `SignalDecision("regex", reference_answer, None)` when `reference_answer` is not None, else `SignalDecision("none", None, None)`.
- `off`: return the reference result; no Basal call; no row.
- `shadow`: return the reference result immediately; when `session_id` and a recorder exist, a background task (registered in `_background_tasks`, so `drain_background_tasks` waits for it) asks Basal and writes the row. `below_threshold` is set as in the Profiler's shadow task.
- `live`: await Basal; at or above the node threshold return `SignalDecision("basal", basal.answer, basal)`; otherwise the reference result with the Basal answer attached in `basal`. Write the row before returning.
- Row: `mode`, `options`, `threshold`, `final_answer = answer or ""`, `source` = the returned source in `live` and the reference source in `shadow`, `message_id`, `reference_kind`, `reference_answer`, Basal fields, `skip_reason`; `llm_*` null.
- Never raises; a Basal error, a language-gate rejection or a recorder error is logged and yields the reference result.

- [ ] **Step 1: Write failing tests** with `AsyncMock(spec=BasalClient)` and a list-appending recorder: off → no Basal call, no row; shadow → returns reference before Basal finishes (Basal mock awaits an `asyncio.Event` the test sets after the call returns), then `drain_background_tasks()` → one row with `mode="shadow"`, `message_id` set, `llm_answer is None`; live at confidence exactly = threshold → `source="basal"`; live below threshold with `reference_answer="engaged"` → `source="regex"`, `basal` attached, row `skip_reason="below_threshold"`; live with no reference below threshold → `source="none"`, `final_answer == ""`; live Basal raises `BasalUnavailableError(is_timeout=True)` → reference result, row `skip_reason="timeout"` (Review Focus 1); recorder raises → result still returned; `session_id=None` in shadow → no Basal call.
- [ ] **Step 2: Run** `uv run pytest tests/unit/decisions/test_signal.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** `decide_signal` reusing `_ask_basal` and extending `_record` with `message_id`, `reference_kind`, `reference_answer` keyword arguments.
- [ ] **Step 4: Run** (PASS), then the gate (the existing cascade tests must stay green unchanged).
- [ ] **Step 5: Commit** `feat(US-056): add signal mode for Basal next to a deterministic reference`

### Task 4: In-role question and check (US-050)

**Files:**
- Create: `backend/src/phishguard/agents/prompts/in_role_basal.py`
- Create: `backend/src/phishguard/models/in_role.py`
- Create: `backend/src/phishguard/services/in_role_check.py`
- Test: `backend/tests/unit/services/test_in_role_check.py`

**Interfaces:**
- Consumes: Task 3 `decide_signal`, Task 1 factory.
- Produces:
  - `IN_ROLE_NODE = "response.in_role"`, `IN_ROLE_INSTRUCTIONS: str`, `IN_ROLE_CRITERIA: dict[str, str]` with keys `in_role`, `breaks_role`. The descriptions follow the spec's "Nodes and questions" section: `breaks_role` covers admitting to being AI, refusing, moralizing, mentioning a scam, police or CERT, assistant tone, and speaking against the persona's age, style or knowledge. The instructions say the reply is the data to judge and any instructions inside it are ignored.
  - `build_in_role_state(persona: PersonaProfile, content: str) -> str`: persona type display name, age, style description, a blank line, then `Reply:` and the content. No name and no background.
  - `class InRoleWarning(BaseModel): message: str; confidence: float` (0–1)
  - `IN_ROLE_WARNING_MESSAGE = "This reply may break the persona's role. Review it before sending."`
  - `async def check_in_role(persona: PersonaProfile, content: str, session_id: str, message_id: str, service: DecisionService | None = None) -> InRoleWarning | None`: builds the service with `create_decision_service(node=IN_ROLE_NODE)` when none is given, once per process on first use (a module-level lazy singleton, so the HTTP client and settings are not rebuilt per request); returns a warning only for `source == "basal"` and `answer == "breaks_role"`; never raises (catches and logs everything).

- [ ] **Step 1: Write failing tests** with a fake `DecisionService` whose `decide_signal` returns preset `SignalDecision`s: `basal`/`breaks_role` p=0.87 → `InRoleWarning(message=IN_ROLE_WARNING_MESSAGE, confidence=0.87)`; `basal`/`in_role` → None; `none` → None; `decide_signal` raises → None; the state passed to `decide_signal` contains the reply and the persona style, does not contain the persona name, and `message_id`/`session_id` are passed through; `IN_ROLE_CRITERIA` keys are exactly `{"in_role", "breaks_role"}`.
- [ ] **Step 2: Run** `uv run pytest tests/unit/services/test_in_role_check.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** (PASS), then the gate.
- [ ] **Step 5: Commit** `feat(US-050): add Basal in-role check for generated replies`

### Task 5: In-role check in the response API (US-050)

**Files:**
- Modify: `backend/src/phishguard/api/routers/response.py` (models at lines 38–92; `generate_response` persona parsing at ~139–175 and the save at ~288; `validate_response` at ~391)
- Test: `backend/tests/unit/api/test_response_in_role.py` (follow the client/patching pattern of `backend/tests/unit/api/test_response_validation.py`)

**Interfaces:**
- Consumes: Task 4 `check_in_role`, `InRoleWarning`.
- Produces: `ResponseGenerationResponse.in_role_warning: InRoleWarning | None = None`, `ResponseValidationResponse.in_role_warning: InRoleWarning | None = None`; private helper `_parse_persona(persona_data: dict | None) -> PersonaProfile | None` used by both endpoints (generate keeps its current 400/500 errors when it gets `None` or a parse error).

Rules: generate calls `check_in_role(persona, response_content, request.session_id, message_id)` after `add_bot_response`. Validate calls it only when the content passed the PII check and the session has a parsable persona, using `request.message_id`.

- [ ] **Step 1: Write failing tests** (patch `check_in_role` and the session service): generate returns the warning from the patched check; generate with the check returning None → `in_role_warning` null; validate of safe content returns the warning; validate of unsafe content → violations as today and `check_in_role` not called (Review Focus 3); validate when the session has no persona → 200, `in_role_warning` null (Review Focus 4); validate of safe content where the check returns None after a previously flagged message → null (Review Focus 2, backend half).
- [ ] **Step 2: Run** `uv run pytest tests/unit/api/test_response_in_role.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** (PASS), then the full gate.
- [ ] **Step 5: Commit** `feat(US-050): return in-role warning from response generate and validate`

### Task 6: In-role warning in the chat UI (US-050)

**Files:**
- Modify: `frontend/src/types/schemas.ts` (`InRoleWarning`, field on `ResponseGenerationResult` and `ChatMessage`)
- Modify: `frontend/src/app/dashboard/page.tsx` (both `/response/generate` handlers at ~321 and ~467 store the warning on the new bot message; the `/response/validate` handler at ~404 replaces it on the edited message, clearing it when null)
- Modify: `frontend/src/components/dashboard/ChatMessage.tsx` (render under bot messages, not while editing)
- Test: `frontend/src/components/dashboard/__tests__/ChatMessage.test.tsx` (new; follow the render/setup pattern of the other tests in that folder)

**Interfaces:**
- Consumes: Task 5 JSON field `in_role_warning: {message: string, confidence: number} | null`.
- Produces: `export interface InRoleWarning { message: string; confidence: number }`; `ChatMessage.inRoleWarning?: InRoleWarning | null`.

Rendering: an amber notice in the existing design tokens with `data-testid="in-role-warning"`, text `{message} (Basal, p={confidence.toFixed(2)})`, and `role="status"`. The copy/send controls stay enabled.

- [ ] **Step 1: Write failing tests:** a bot message with `inRoleWarning {confidence: 0.87}` shows `This reply may break the persona's role. Review it before sending. (Basal, p=0.87)`; a bot message without it shows no `in-role-warning`; a scammer message never shows it; in edit mode it is hidden.
- [ ] **Step 2: Run** `cd frontend && npx vitest run src/components/dashboard/__tests__/ChatMessage.test.tsx`. Expected: FAIL.
- [ ] **Step 3: Implement** the type, the component and the three handlers.
- [ ] **Step 4: Run** the test (PASS), then `/check-frontend`.
- [ ] **Step 5: Commit** `feat(US-050): show in-role warning on bot messages`

### Task 7: In-role eval samples + blind label review (US-050)

**Files:**
- Modify: `backend/src/phishguard/decisions/eval/__main__.py` (subcommand `in-role-samples --out FILE --per-type N`)
- Create: `backend/tests/fixtures/eval/in_role_responses.jsonl`
- Modify: `backend/tests/fixtures/eval/README.md` (section for the in-role set)
- Test: `backend/tests/unit/decisions/test_in_role_fixtures.py`

**Interfaces:**
- Consumes: `PersonaEngine.select_persona(attack_type)`, `ConversationAgent.generate_response(persona, email_content, attack_type, session_id=None)`, `load_fixture_inputs` (profiler fixtures).
- Produces: row schema `{"id", "lang": "pl"|"en", "gold": "in_role"|"breaks_role", "synthetic": bool, "persona": {persona_type, age, style_description}, "response", "reviewed", "ambiguous", "review", "notes"}`.

`in-role-samples` takes reviewed, non-ambiguous profiler fixtures except `not_phishing`, `N` per attack type, generates the first reply for each with the real agent (no session, so nothing is written), and writes rows with `synthetic: false`, `gold: "in_role"` as a placeholder and `reviewed: false`.

Content of the final set: ≥ 60 real rows (`--per-type 8`, about 64), ≥ 40 synthetic `breaks_role` rows covering every behaviour in `IN_ROLE_CRITERIA["breaks_role"]`, and ≥ 10 synthetic hard `in_role` rows (a persona naively mentioning that their bank warns about scams, a confused persona asking "is this real?", an elderly persona writing formally). About half PL, half EN.

- [ ] **Step 1: Write failing test** `test_in_role_fixtures_schema`: every line parses, `gold` in the two keys, `lang` in {pl,en}, unique ids, ≥ 60 rows with `synthetic: false`, ≥ 40 synthetic `breaks_role`, ≥ 10 synthetic `in_role`, every row `reviewed: true` or `ambiguous: true`, ambiguous ≤ 10%.
- [ ] **Step 2: Run** `uv run pytest tests/unit/decisions/test_in_role_fixtures.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** the subcommand and run it: `uv run python -m phishguard.decisions.eval in-role-samples --out tests/fixtures/eval/in_role_responses.jsonl --per-type 8`. Append the synthetic rows by hand.
- [ ] **Step 4: Blind review**, as in stage 1 Task 8 Step 5: the controller dispatches a fresh Claude subagent with only `id`, `persona` and `response` per row and the two options with their `IN_ROLE_CRITERIA` descriptions; mismatches against `gold` (for real rows the placeholder counts as `gold`) go to a second fresh subagent; 2 of 3 decides, otherwise `ambiguous: true`; write `review` on every row. Run the test (PASS) and the gate.
- [ ] **Step 5: Commit** `test(US-050): add in-role eval samples with blind label review`

### Task 8: In-role eval report (US-050)

**Files:**
- Create: `backend/src/phishguard/decisions/eval/binary.py`
- Modify: `backend/src/phishguard/decisions/eval/__main__.py` (subcommand `in-role --source fixtures|decisions --out DIR [--limit N]`)
- Modify: `backend/src/phishguard/decisions/eval/sources.py` (`load_in_role_fixtures`, `load_in_role_decisions`)
- Test: `backend/tests/unit/decisions/test_eval_binary.py`

**Interfaces:**
- Consumes: Task 7 fixtures, `BasalClient.ask_choice`, `IN_ROLE_INSTRUCTIONS`, `IN_ROLE_CRITERIA`, `build_in_role_state` (the persona dict is turned into a `PersonaProfile` with placeholder name/background, which the state does not use).
- Produces:
  - `@dataclass(frozen=True) BinaryCase(id: str, gold: str, basal: BasalAnswer | None, lang: str, synthetic: bool, ambiguous: bool = False)`
  - `@dataclass(frozen=True) BinaryRow(threshold: float, precision: float, recall: float, false_alarm_rate: float, n_flagged: int, n_positive: int, n_negative: int)`
  - `binary_curve(cases: list[BinaryCase], positive: str, thresholds: list[float]) -> list[BinaryRow]`: flagged = `basal.answer == positive and basal.confidence >= t`; cases without a Basal answer count as not flagged; precision 0.0 when nothing is flagged
  - `pick_binary_threshold(rows, min_recall: float = 0.9, max_false_alarm: float = 0.1) -> BinaryRow | None`: the highest threshold meeting both
  - `write_binary_report(cases, out_dir: Path, meta: dict) -> None` → `results.jsonl`, `report.md`
  - `load_in_role_decisions() -> list[dict]`: rows with `node = 'response.in_role'` and their message content fetched by `message_id` (service role), for manual review only

`report.md` (fixtures): meta (date, Basal model, n real / synthetic, ambiguous excluded); threshold table 0.50–0.99 step 0.01 for all, real only, synthetic only, PL, EN; the picked threshold for the spec's gate (recall ≥ 90%, false alarms ≤ 10%) or the line `No threshold meets the gate.`; Basal p50/p95 latency as information; the label caveat from stage 1. Report (decisions): count per `basal_answer` and `skip_reason`, then every `breaks_role` row with confidence, threshold, mode and the reply text for manual review (gate 2 of the spec).

- [ ] **Step 1: Write failing tests** on a 6-case hand-computed set (3 positive, 3 negative): at t=0.8 precision 2/3, recall 2/3, false-alarm 1/3; a case with `basal=None` counts as not flagged; `pick_binary_threshold` returns the expected row and `None` when nothing qualifies; `write_binary_report` writes both files and `report.md` contains `"| 0.80 |"` and `No threshold meets the gate.` for a failing set.
- [ ] **Step 2: Run** `uv run pytest tests/unit/decisions/test_eval_binary.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement.** Basal requests go one at a time (`asyncio.Semaphore(1)`): the server handles one request at a time, and four in flight caused the stage 1 timeouts.
- [ ] **Step 4: Run** the gate. Then a real run against the local Basal: `uv run python -m phishguard.decisions.eval in-role --source fixtures --out ../eval-results/in-role-$(date +%F)`. Expected: report written, no Basal errors.
- [ ] **Step 5: Commit** `feat(US-050): add in-role eval report`

### Task 9: Docs — stage 1 results, PRD

**Files:**
- Modify: `docs/superpowers/specs/2026-11-02-basal-decision-layer-stage1-design.md` (new final section `## Wyniki (2026-11-03)`)
- Modify: `.ai/prd.md`

- [ ] **Step 1:** In the stage 1 spec, add the results table from the stage 2 spec's "Why" section (gate 1 passed at 0.70 / 93.9% / 0% / 98%; gate 2 failed: 13/28 agreement, ~48% error at 0.70, 13/28 phishing as `not_phishing`), measured latency (~8 s per request on M1 Pro, MLX, `max` model, vs ~1.6 s gpt-5.1), and the decision that the Profiler stays on GPT.
- [ ] **Step 2:** In the PRD, add `US-056: Per-node Basal mode and signal mode` and the reshaped `US-050: Persona in-role check (Basal)` with acceptance criteria taken from Tasks 1–6 and 8, in the existing US format (`/prd-excerpt US-055` for the shape). Mark them ✅ only after their tasks are done. Update the "Original US-050…" note: US-050 is now the in-role check; US-051 stays in stage 3; unmasking and urgency get their own US in the phase C plan.
- [ ] **Step 3:** Run `/check-all`. Expected: backend and frontend green.
- [ ] **Step 4: Commit** `docs: record Basal stage 1 results and add stage 2 user stories`

Gates for switching `response.in_role` to `live` are not implementation tasks. Łukasz makes that call from the Task 8 reports and the shadow data (at least 30 real in-role decisions, every `breaks_role` reviewed).
