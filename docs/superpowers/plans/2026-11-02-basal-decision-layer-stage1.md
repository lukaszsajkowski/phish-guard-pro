# Basal Decision Layer — Stage 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `phishguard.decisions` layer (Basal client, language gate, shadow/live cascade, decision log, LLM token log), move the Profiler's attack-type decision onto it, and ship an offline eval CLI that produces the coverage-vs-error report.

**Architecture:** `DecisionService.decide_choice()` is the single entry point for closed questions. It asks a local `basal-serve` over HTTP and falls back to an injected LLM call. In `shadow` mode the LLM decides and Basal runs as a fire-and-forget task. In `live` mode Basal decides at or above the node threshold. Every decision is written to a new `decisions` table and every GPT call to `llm_usage`. The graph topology is unchanged: `ProfilerAgent` uses the service internally.

**Tech Stack:** Python 3.12, FastAPI, httpx (already in deps), fast-langdetect (new), Supabase (sync `supabase` client, service role), pytest + pytest-asyncio, matplotlib (new, dev-only for the eval chart), Next.js 16 / React 19 / Vitest for the source badge.

**Spec:** `docs/superpowers/specs/2026-11-02-basal-decision-layer-stage1-design.md` (Polish). Read it before starting any task.

## Global Constraints

- Basal endpoint: `POST {BASAL_URL}` with body `{"state": str, "questions": {name: {"type": "choice", "option_keys": "hide", "instructions": str, "criteria": {key: description}}}}`; read `answers[name]["choice"]`, `["probabilities"]`, `["confidence"]`.
- Settings (env, case-insensitive): `BASAL_URL=""`, `BASAL_MODE="shadow"` (`off|shadow|live`), `BASAL_THRESHOLD=0.9`, `BASAL_THRESHOLD_PROFILER` (optional, overrides for node `profiler.attack_type`), `BASAL_TIMEOUT_S=5`, `BASAL_MODEL=""`.
- Empty `BASAL_URL` behaves exactly like `BASAL_MODE=off`.
- Mode and thresholds change only via `.env` + backend restart; no UI or endpoint.
- Language gate: per line, skip lines with < 20 letters, reject when a non-{pl,en} language scores ≥ 0.5 (`fast-langdetect`, `model="lite"`).
- Basal decides when `confidence >= threshold` (inclusive).
- `decision_source` values: `"llm"`, `"basal"`, `"basal_low_confidence"`. Default `"llm"`.
- `confidence` in `ClassificationResult` stays 0–100; for Basal decisions it is `round(p * 100, 2)`.
- Basal reasoning text: `"Classified locally by Basal: {Display} (p={p:.2f}). Runner-up: {Display2} (p={p2:.2f})."`
- `decisions` rows never store email text.
- A failure to reach Basal, a timeout, or a failed DB write never fails a classification; it logs a warning.
- No category "other": options are exactly the 9 `AttackType` values.
- Shadow mode never delays the classification response.
- Live-mode fallback: if the LLM path raises (unparseable after retries, or `LLMRequestError`) and Basal returned an answer, return Basal's top option with `decision_source="basal_low_confidence"`; with no Basal answer keep today's behaviour.
- Commit style: conventional commits with US scope (`feat(US-047): ...`), no Co-Authored-By line (project `/commit` rule).
- Backend gate after each task: `cd backend && uv run pytest -q && uv run ruff check . && uv run ruff format --check .`

## Review Focus

1. **Basal returns a `choice` key that is not one of the asked options** (server misconfigured, wrong model). Expected: treated as Basal unavailable, the LLM decides. Test in Task 1.
2. **Shadow-mode LLM failure.** Expected: the original exception propagates exactly as today, and the Basal background task still writes its row with `llm_answer = null` and no "Task exception was never retrieved" warning. Test in Task 4.
3. **The decision-log write raises** (Supabase down, RLS/constraint error). Expected: the classification still returns. Test in Task 3.
4. **Polish email with an English signature or URL lines, and a German email.** Expected: the first goes to Basal, the second to the LLM with `skip_reason="language"`. Test in Task 2.
5. **Confidence exactly at the threshold** (0.9 vs 0.9). Expected: Basal decides. Test in Task 4.

---

### Task 1: Settings + Basal HTTP client (US-047)

**Files:**
- Modify: `backend/src/phishguard/core/__init__.py` (add fields to `Settings`)
- Modify: `.env.example` (add a `# BASAL (Backend only, optional)` block with the six variables and defaults)
- Create: `backend/src/phishguard/decisions/__init__.py`
- Create: `backend/src/phishguard/decisions/basal_client.py`
- Test: `backend/tests/unit/decisions/__init__.py`, `backend/tests/unit/decisions/test_basal_client.py`

**Interfaces:**
- Produces:
  - `Settings.basal_url: str`, `basal_mode: Literal["off","shadow","live"]`, `basal_threshold: float`, `basal_threshold_profiler: float | None`, `basal_timeout_s: float`, `basal_model: str`
  - `Settings.basal_threshold_for(node: str) -> float` (`"profiler.attack_type"` → `basal_threshold_profiler` if set, else `basal_threshold`)
  - `Settings.basal_effective_mode -> Literal["off","shadow","live"]` (property; `"off"` when `basal_url` is empty)
  - `@dataclass(frozen=True) BasalAnswer(answer: str, probabilities: dict[str, float], confidence: float, latency_ms: int)`
  - `class BasalUnavailableError(Exception)`
  - `class BasalClient(url: str, timeout_s: float, transport: httpx.AsyncBaseTransport | None = None)` with `async ask_choice(state: str, instructions: str, criteria: dict[str, str]) -> BasalAnswer`

- [ ] **Step 1: Write failing tests** with `httpx.MockTransport` (no new dependency):
  - `test_ask_choice_parses_answer`: transport returns `{"answers": {"q": {"type": "choice", "choice": "romance_scam", "probabilities": {"romance_scam": 0.94, "nigerian_419": 0.06}, "confidence": 0.94}}}`; assert `answer == "romance_scam"`, `confidence == 0.94`, `latency_ms >= 0`, and the captured request JSON has `questions["q"]["option_keys"] == "hide"` and `type == "choice"`.
  - `test_ask_choice_raises_on_5xx`, `test_ask_choice_raises_on_timeout` (transport raises `httpx.ReadTimeout`), `test_ask_choice_raises_on_missing_answer_key` (body `{"answers": {}}`): all `pytest.raises(BasalUnavailableError)`.
  - `test_ask_choice_raises_when_choice_not_in_criteria` (Review Focus 1): `choice == "other"` → `BasalUnavailableError`.
  - `test_settings_threshold_for_node`: `Settings(basal_threshold=0.9, basal_threshold_profiler=0.95).basal_threshold_for("profiler.attack_type") == 0.95`, and `== 0.9` for `"other.node"`.
  - `test_effective_mode_off_without_url`: `Settings(basal_url="", basal_mode="live").basal_effective_mode == "off"`.
- [ ] **Step 2: Run** `cd backend && uv run pytest tests/unit/decisions -v`. Expected: FAIL (ImportError).
- [ ] **Step 3: Implement** the settings fields and `BasalClient`. Internally the question name is `"q"`. Every `httpx.HTTPError`, `KeyError`, `ValueError` and out-of-options choice is wrapped in `BasalUnavailableError`.
- [ ] **Step 4: Run** the same command. Expected: PASS. Then the backend gate.
- [ ] **Step 5: Commit** `feat(US-047): add Basal settings and HTTP client`

### Task 2: Language gate (US-048)

**Files:**
- Modify: `backend/pyproject.toml` (add `"fast-langdetect>=1.1.0"` to `dependencies`), then `uv sync`
- Create: `backend/src/phishguard/decisions/language.py`
- Test: `backend/tests/unit/decisions/test_language.py`

**Interfaces:**
- Produces: `is_basal_language(text: str) -> bool` (port of `~/Workspace/autoshield/judge.py:is_basal_language`, same constants)

- [ ] **Step 1: Write failing parametrized test** `test_is_basal_language` with cases: a 3-line Polish 419 email → True; an English tech-support email → True; a Polish email with an English signature line and a URL line → True (Review Focus 4); a German invoice email → False; text with only short lines (`"OK\n123"`) → True; empty string → True.
- [ ] **Step 2: Run** `uv run pytest tests/unit/decisions/test_language.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement.** If the first `detect` call downloads a model, make sure the test passes offline after `uv sync` (the `lite` model ships with the package).
- [ ] **Step 4: Run.** Expected: PASS. Then the gate.
- [ ] **Step 5: Commit** `feat(US-048): add Basal language gate`

### Task 3: Migrations + decision/usage recorder (US-048)

**Files:**
- Create: `supabase/migrations/20261102120000_create_decisions.sql` (columns exactly as the spec's `decisions` table; checks on `mode` and `source`; `skip_reason` check in `('disabled','language','unavailable','timeout','below_threshold')`; indexes on `session_id` and `node`; RLS select/insert for the session owner, copied from `20241231183202_create_ioc_extracted.sql`)
- Create: `supabase/migrations/20261102120100_create_llm_usage.sql` (`id, session_id uuid null references sessions on delete cascade, agent text check in ('profiler','conversation','eval'), model text, prompt_tokens int, completion_tokens int, latency_ms int, created_at`; same RLS shape)
- Create: `supabase/migrations/20261102120200_add_decision_source.sql` (`sessions.decision_source text null check in ('llm','basal','basal_low_confidence')`)
- Create: `backend/src/phishguard/decisions/recorder.py`
- Test: `backend/tests/unit/decisions/test_recorder.py`

**Interfaces:**
- Produces:
  - `@dataclass DecisionRecord(session_id: str, node: str, mode: str, options: list[str], threshold: float, final_answer: str, source: str, basal_answer: str | None = None, basal_probabilities: dict[str, float] | None = None, basal_confidence: float | None = None, basal_ms: int | None = None, basal_model: str | None = None, skip_reason: str | None = None, llm_answer: str | None = None, llm_model: str | None = None, llm_ms: int | None = None)`
  - `async record_decision(record: DecisionRecord) -> None`
  - `async record_llm_usage(session_id: str | None, agent: str, model: str, prompt_tokens: int, completion_tokens: int, latency_ms: int) -> None`
  - Both use `session_service._get_supabase_client()` and swallow every exception with `logger.warning`.

- [ ] **Step 1: Write failing tests** patching `phishguard.decisions.recorder._get_supabase_client`:
  - `test_record_decision_inserts_row`: assert `table("decisions").insert(...)` was called with a dict that contains `final_answer`, `source`, `mode` and **no key holding email text**.
  - `test_record_decision_swallows_errors` (Review Focus 3): `execute()` raises `Exception("db down")` → returns None, warning logged (`caplog`).
  - `test_record_llm_usage_inserts_row` with `session_id=None`.
- [ ] **Step 2: Run** `uv run pytest tests/unit/decisions/test_recorder.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** the recorder and write the three migrations.
- [ ] **Step 4: Run** the tests (PASS). If the local Supabase is running, apply the migrations with `supabase db reset` or `supabase migration up` and confirm the three objects exist (`\d decisions`). Otherwise note in the commit body that the migrations were not applied.
- [ ] **Step 5: Commit** `feat(US-048): add decisions and llm_usage tables with recorder`

### Task 4: Decision cascade (US-048)

**Files:**
- Create: `backend/src/phishguard/decisions/cascade.py`
- Modify: `backend/src/phishguard/decisions/__init__.py` (export `DecisionService`, `ChoiceQuestion`, `Decision`, `create_decision_service`)
- Test: `backend/tests/unit/decisions/test_cascade.py`

**Interfaces:**
- Consumes: `BasalClient`, `BasalAnswer`, `BasalUnavailableError` (Task 1); `is_basal_language` (Task 2); `DecisionRecord`, `record_decision` (Task 3)
- Produces:
  - `@dataclass(frozen=True) ChoiceQuestion(node: str, instructions: str, criteria: dict[str, str])`
  - `@dataclass(frozen=True) Decision(Generic[T]): source: Literal["llm","basal","basal_low_confidence"]; answer: str; basal: BasalAnswer | None; llm_result: T | None`
  - `class DecisionService(basal: BasalClient | None, mode: Literal["off","shadow","live"], threshold_for: Callable[[str], float], basal_model: str = "", recorder: Callable[[DecisionRecord], Awaitable[None]] | None = record_decision)`
  - `async DecisionService.decide_choice(question: ChoiceQuestion, state: str, session_id: str | None, llm_call: Callable[[], Awaitable[T]], llm_answer: Callable[[T], str], llm_model: Callable[[T], str]) -> Decision[T]`
  - `create_decision_service(settings: Settings | None = None) -> DecisionService`
  - `async drain_background_tasks() -> None` (awaits pending shadow tasks; used by tests and the eval)

Behaviour (each is a test):
- `off`: only `llm_call`; row with `skip_reason="disabled"`, `source="llm"`.
- `live`, non-PL/EN state: no Basal call, LLM decides, `skip_reason="language"`.
- `live`, `BasalUnavailableError`: LLM decides, `skip_reason="unavailable"` (`"timeout"` when the cause is `httpx.TimeoutException`; expose this via an attribute on `BasalUnavailableError`, e.g. `is_timeout: bool`).
- `live`, `confidence >= threshold`: `llm_call` is **not** awaited, `source="basal"`, `answer == basal.answer`.
- `live`, below threshold: LLM decides, `skip_reason="below_threshold"`, Basal fields still recorded.
- `live`, below threshold and `llm_call` raises: if Basal answered → `source="basal_low_confidence"`, `llm_result=None`; if not → re-raise.
- `shadow`: returns as soon as `llm_call` finishes; Basal runs in `asyncio.create_task`, keeps its task in a module-level `set` and discards it on done. The row is written after both Basal and the LLM outcome are known; the LLM outcome is passed through an `asyncio.Future` that the main path resolves (or resolves with `None` on LLM error, then re-raises).
- No row is written when `session_id is None` or `recorder is None`.

- [ ] **Step 1: Write failing tests**, one per behaviour above, with a fake `BasalClient` (`AsyncMock(spec=BasalClient)`) and a fake recorder that appends to a list. Must include:
  - `test_live_threshold_is_inclusive` (Review Focus 5): confidence `0.9`, threshold `0.9` → `source == "basal"`.
  - `test_shadow_does_not_wait_for_basal`: fake Basal `await asyncio.sleep(1)`; assert `decide_choice` returns in < 0.2 s with `source == "llm"`; after `await drain_background_tasks()` the recorder holds one row with the Basal answer and `mode == "shadow"`.
  - `test_shadow_llm_failure_still_records` (Review Focus 2): `llm_call` raises `LLMRequestError` → `decide_choice` raises the same error; after draining, one row with `llm_answer is None`; no unretrieved task exception (assert with `caplog` that no `"Task exception was never retrieved"` appears).
  - `test_shadow_basal_timeout_records_timeout`.
- [ ] **Step 2: Run** `uv run pytest tests/unit/decisions/test_cascade.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement `cascade.py`.** `final_answer` in a shadow row = LLM answer (or `""` when the LLM failed).
- [ ] **Step 4: Run** (PASS), then the gate.
- [ ] **Step 5: Commit** `feat(US-048): add Basal→LLM decision cascade with shadow mode`

### Task 5: Token usage on every GPT call

**Files:**
- Modify: `backend/src/phishguard/llm/client.py` (`LLMResponse` gets `prompt_tokens: int = 0`, `completion_tokens: int = 0`; `_make_request` and `_attempt_with_retries` return a private `NamedTuple _Completion(content: str, prompt_tokens: int, completion_tokens: int)` from `response.usage`, 0 when `usage` is None)
- Modify: `backend/src/phishguard/agents/conversation.py` (`generate_response(..., session_id: str | None = None)`; after each `chat_completion` call `record_llm_usage(session_id, "conversation", ...)` when `session_id` is set)
- Modify: `backend/src/phishguard/orchestrator/nodes.py` (`generate_response` node passes `state.get("session_id")`)
- Test: `backend/tests/unit/llm/test_llm_client.py`, `backend/tests/unit/agents/test_conversation.py`

**Interfaces:**
- Consumes: `record_llm_usage` (Task 3)
- Produces: `LLMResponse.prompt_tokens`, `LLMResponse.completion_tokens` (Task 6 uses them for the Profiler)

- [ ] **Step 1: Write failing tests:** `test_chat_completion_returns_usage` (mock OpenAI response with `usage.prompt_tokens=120, completion_tokens=40` → `LLMResponse` has those values); `test_chat_completion_usage_missing_defaults_zero`; `test_generate_response_records_usage` (patch `phishguard.agents.conversation.record_llm_usage`, assert one call per LLM attempt with `agent="conversation"`); `test_generate_response_without_session_skips_usage`.
- [ ] **Step 2: Run** `uv run pytest tests/unit/llm tests/unit/agents/test_conversation.py -v`. Expected: the new tests FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** (PASS, existing tests unchanged), then the gate.
- [ ] **Step 5: Commit** `feat: record GPT token usage per call`

### Task 6: Profiler on the cascade + decision_source end to end, backend (US-049)

**Files:**
- Modify: `backend/src/phishguard/models/classification.py` (`ClassificationResult.decision_source: Literal["llm","basal","basal_low_confidence"] = "llm"`)
- Modify: `backend/src/phishguard/agents/profiler.py`
- Create: `backend/src/phishguard/agents/prompts/profiler_basal.py` (`PROFILER_BASAL_INSTRUCTIONS: str`, `ATTACK_TYPE_CRITERIA: dict[str, str]`, one entry per `AttackType` value, descriptions taken from the enum docstrings and `PROFILER_SYSTEM_PROMPT`)
- Modify: `backend/src/phishguard/orchestrator/state.py` (`ClassificationState.decision_source: str`)
- Modify: `backend/src/phishguard/orchestrator/nodes.py` (`classify_email` calls `profiler.classify(email_content, session_id=state.get("session_id"))` and copies `decision_source`)
- Modify: `backend/src/phishguard/api/routers/classification.py` (passes `decision_source` into `ClassificationResult`)
- Modify: `backend/src/phishguard/services/session_service.py` (`update_session_classification` writes `decision_source`)
- Modify: `backend/src/phishguard/api/routers/session.py` (`SessionRestoreResponse.decision_source: str | None`, read from the session row)
- Test: `backend/tests/agents/test_profiler.py`, `backend/tests/unit/agents/test_profiler_basal.py` (new)

**Interfaces:**
- Consumes: `DecisionService`, `ChoiceQuestion`, `Decision`, `create_decision_service` (Task 4); `record_llm_usage` (Task 3); `LLMResponse.prompt_tokens/completion_tokens` (Task 5)
- Produces:
  - `ProfilerAgent(llm_client: LLMClient | None = None, decision_service: DecisionService | None = None)`
  - `async ProfilerAgent.classify(email_content: str, session_id: str | None = None) -> ClassificationResult`
  - `async ProfilerAgent.classify_with_llm(email_content: str, session_id: str | None = None) -> ClassificationResult`: today's LLM path, but it raises `ClassificationParseError(ClassificationError)` after the parse retries instead of returning the fallback (the eval uses it)
  - `PROFILER_NODE = "profiler.attack_type"`
  - `build_basal_reasoning(answer: BasalAnswer) -> str` (copy fixed in Global Constraints)

`classify()` flow: `decision_service.decide_choice(question, email_content, session_id, llm_call=lambda: self.classify_with_llm(...), llm_answer=lambda r: r.attack_type.value, llm_model=...)`, then:
- `source == "llm"` → the LLM result with `decision_source="llm"`
- `"basal"` / `"basal_low_confidence"` → a new `ClassificationResult` with Basal answer, `confidence=round(p*100, 2)`, `build_basal_reasoning` text, and that source
- `ClassificationParseError` escaping the service (off/shadow, or live with no Basal answer) → today's `_create_fallback_result`
- `LLMRequestError` escaping → `ClassificationError` as today

- [ ] **Step 1: Write failing tests** in `test_profiler_basal.py` with a fake `DecisionService`:
  - `test_basal_decision_maps_to_result`: Basal `romance_scam` p=0.94, runner-up `nigerian_419` 0.03 → `attack_type == ROMANCE_SCAM`, `confidence == 94.0`, `decision_source == "basal"`, `reasoning == "Classified locally by Basal: Romance Scam (p=0.94). Runner-up: Nigerian 419 (p=0.03)."`
  - `test_low_confidence_fallback_source`
  - `test_parse_error_without_basal_returns_legacy_fallback`: `attack_type == NOT_PHISHING`, `confidence == 25.0`
  - `test_criteria_cover_all_attack_types`: `set(ATTACK_TYPE_CRITERIA) == {t.value for t in AttackType}`
  - `test_classify_records_profiler_usage_with_session`
  - `test_restore_returns_decision_source` in the existing session-restore tests if they exist, otherwise a new unit test patching `session_service.get_session`.
- [ ] **Step 2: Run** `uv run pytest tests/agents/test_profiler.py tests/unit/agents/test_profiler_basal.py -v`. Expected: the new tests FAIL. The existing `test_profiler.py` tests must keep passing once implemented: build their `ProfilerAgent` with `decision_service=DecisionService(basal=None, mode="off", threshold_for=lambda n: 0.9, recorder=None)` if needed.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** the full backend gate. Expected: all green.
- [ ] **Step 5: Manual smoke test.** Start Basal (`~/basal-mlx/bin/basal-serve --model Remek/basal-2.0-max-MLX-8bit --mode mlx --port 8011`), set `BASAL_URL=http://127.0.0.1:8011/v1/systemone`, then classify one email from the dashboard in `shadow` and once in `live` (`/run-all`). Check one `decisions` row per run and the matching `sessions.decision_source`. Then stop Basal and classify again in `live`: the session still works, and the row has `skip_reason="unavailable"`.
- [ ] **Step 6: Commit** `feat(US-049): classify attack type through Basal cascade`

### Task 7: Source badge in the UI (US-049)

**Files:**
- Modify: `frontend/src/components/app/ClassificationResult.tsx` (prop `decisionSource?: "llm" | "basal" | "basal_low_confidence"`; badge next to the confidence pill, styled like it, `data-testid="decision-source"`; labels `"GPT-4o"`, `"Basal"`, `"Basal (low confidence)"`; no badge when the prop is undefined, e.g. old sessions)
- Modify: `frontend/src/app/dashboard/page.tsx` (both `setClassificationResult` calls, ~lines 233 and 832: map `data.decision_source`; pass the prop at both `<ClassificationResult` usages, ~line 1051)
- Test: `frontend/src/components/app/__tests__/ClassificationResult.test.tsx` (new)

- [ ] **Step 1: Write failing tests:** renders `"Basal"` for `decisionSource="basal"`; `"GPT-4o"` for `"llm"`; no `decision-source` element when the prop is omitted; confidence thresholds (30/50/80 styling) unchanged.
- [ ] **Step 2: Run** `cd frontend && npx vitest run src/components/app/__tests__/ClassificationResult.test.tsx`. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** `npm run lint && npm run test && npx tsc --noEmit`. Expected: all pass.
- [ ] **Step 5: Commit** `feat(US-049): show decision source next to classification confidence`

### Task 8: Eval fixtures + human label review (US-053)

**Files:**
- Create: `backend/tests/fixtures/eval/profiler_emails.jsonl`
- Create: `backend/tests/fixtures/eval/README.md` (schema, how to review, the "don't look at model answers while reviewing" rule)
- Test: `backend/tests/unit/decisions/test_eval_fixtures.py`

Row schema: `{"id": "pl-romance-01", "lang": "pl"|"en", "gold": <AttackType value>, "reviewed": false, "email": "...", "notes": ""}`.

Content: about 100 rows, at least 10 per `AttackType` (`not_phishing` included: real invoices, newsletters, delivery notices), about half PL and half EN, with at least 15 deliberately hard cases (CEO fraud vs fake invoice, crypto vs romance, real vs fake delivery). No real personal data: names from Faker, IBANs and BTC addresses in the official example formats.

- [ ] **Step 1: Write failing test** `test_fixtures_schema`: every line parses, `gold` is in `AttackType`, `lang` is in {pl,en}, ids are unique, each `AttackType` has ≥ 10 rows, total is 90–110.
- [ ] **Step 2: Run** `uv run pytest tests/unit/decisions/test_eval_fixtures.py -v`. Expected: FAIL (no file).
- [ ] **Step 3: Write the fixtures**, all with `reviewed: false`.
- [ ] **Step 4: Run** (PASS), then commit `test(US-053): add profiler eval fixtures pending label review`.
- [ ] **Step 5: HUMAN CHECKPOINT.** Stop and ask Łukasz to review the `gold` labels and set `reviewed: true`. He reviews before seeing any model output. Continue with Task 9 in the meantime; Task 10's gate verdict waits for this.

### Task 9: Eval metrics (US-053)

**Files:**
- Create: `backend/src/phishguard/decisions/eval/__init__.py`
- Create: `backend/src/phishguard/decisions/eval/metrics.py`
- Test: `backend/tests/unit/decisions/test_eval_metrics.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) EvalCase(id: str, source: str, reference: str, basal: BasalAnswer | None, llm_answer: str | None, llm_ms: int | None, llm_prompt_tokens: int, llm_completion_tokens: int, reviewed: bool = True)`
  - `@dataclass(frozen=True) ThresholdRow(threshold: float, coverage: float, basal_error: float, cascade_agreement: float, n_basal: int, n_total: int)`
  - `threshold_curve(cases: list[EvalCase], thresholds: list[float]) -> list[ThresholdRow]`, where `coverage` = share of cases with `basal.confidence >= t`; `basal_error` = wrong among those (0.0 when none); `cascade_agreement` = share of all cases where (Basal if covered else `llm_answer`) == `reference`
  - `pick_threshold(rows: list[ThresholdRow], max_error: float = 0.02) -> ThresholdRow | None`: lowest threshold with `basal_error <= max_error` and `n_basal >= 1`
  - `confusion_matrix(cases, use: Literal["basal","llm"]) -> dict[str, dict[str, int]]`
  - `percentile(values: list[int], p: float) -> float`
  - `confidence_buckets(cases) -> dict[str, int]` with keys `"<30"`, `"30-50"`, `"50-80"`, `">=80"` (Basal p × 100)
  - `llm_cost_usd(prompt_tokens: int, completion_tokens: int, model: str) -> float` from `PRICES_PER_MTOK: dict[str, tuple[float, float]]` (`gpt-4o`, `gpt-4o-mini`; values from OpenAI's current price page at implementation time, with the date in a comment)

- [ ] **Step 1: Write failing tests** on a 5-case hand-computed set: at t=0.9, coverage 0.6, basal_error 1/3, cascade_agreement 0.8 (build the cases to give exactly these); `pick_threshold` returns the expected row and `None` when no row qualifies; the confusion matrix counts; `percentile([10,20,30,40], 50) == 25.0`; bucket edges (p=0.30 → "30-50", p=0.80 → ">=80").
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** (PASS), then the gate.
- [ ] **Step 5: Commit** `feat(US-053): add eval metrics for decision thresholds`

### Task 10: Eval CLI, sources and report (US-053)

**Files:**
- Create: `backend/src/phishguard/decisions/eval/__main__.py` (argparse: `profiler --source supabase|fixtures|decisions|all --out DIR [--limit N]`)
- Create: `backend/src/phishguard/decisions/eval/sources.py`
- Create: `backend/src/phishguard/decisions/eval/report.py`
- Modify: `backend/pyproject.toml` (`matplotlib` in the `dev` dependency group)
- Test: `backend/tests/unit/decisions/test_eval_report.py`

**Interfaces:**
- Consumes: Task 9 metrics; `BasalClient` (Task 1); `ProfilerAgent.classify_with_llm` (Task 6); `ATTACK_TYPE_CRITERIA`, `PROFILER_BASAL_INSTRUCTIONS` (Task 6)
- Produces:
  - `load_fixture_inputs(path: Path) -> list[tuple[str, str, str, bool]]` (id, email, gold, reviewed)
  - `load_supabase_inputs(limit: int | None) -> list[tuple[str, str, str | None]]` (session_id, email from `session_service.get_original_email`, stored attack_type)
  - `load_decision_cases() -> list[EvalCase]` (shadow rows from `decisions` where both `basal_answer` and `llm_answer` are not null; reference = `llm_answer`; no model calls)
  - `write_report(cases: list[EvalCase], out_dir: Path, meta: dict) -> None`, which writes `results.jsonl`, `report.md` and `coverage_vs_error.png`

Run rules: for fixtures and supabase, every input is sent to Basal and to `classify_with_llm` (with `session_id=None`, so nothing is written to `decisions` or `llm_usage`); requests run with `asyncio.Semaphore(4)`; a Basal or LLM error for one case is recorded in that case and does not stop the run. Reference = `gold` for fixtures, the fresh GPT-4o answer for supabase (the stored `attack_type` is an extra column in `results.jsonl`). `all` = supabase + fixtures. The CLI prints the number of usable sessions.

`report.md` contains: meta (date, Basal model, LLM model, sources, n per source); a threshold table 0.50–0.99 step 0.01, per source and combined; the picked threshold for `max_error=0.02`; the confusion matrices; p50/p95 latency for Basal and the LLM; LLM cost per 1000 classifications; confidence buckets; and the line **`⚠ Fixture labels not reviewed — this result does not pass gate 1.`** at the top when any fixture case has `reviewed=false`.

- [ ] **Step 1: Write failing tests:** `test_write_report_creates_files` (tmp_path, 4 synthetic cases → three files exist, `report.md` contains `"| 0.90 |"`); `test_report_warns_on_unreviewed`; `test_report_no_warning_when_all_reviewed`; `test_load_decision_cases_filters_incomplete_rows` (patched Supabase client).
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** the gate. Then a real run against the local Basal: `cd backend && uv run python -m phishguard.decisions.eval profiler --source fixtures --out ../eval-results/$(date +%F) --limit 10`. Expected: the three files exist and the report has the unreviewed warning (until Task 8 Step 5 is done). Add `eval-results/` to `.gitignore`.
- [ ] **Step 5: Commit** `feat(US-053): add profiler eval CLI and report`

### Task 11: PRD update

**Files:**
- Modify: `.ai/prd.md`

- [ ] **Step 1:** Add US-047, US-048, US-049 and US-053 as the spec scopes them (Profiler attack type only), plus `US-055: GPT token usage logging`. Add a short note that the original US-050/051/052/054 move to stages 2–3, reshaped per the spec. Use the existing US format in the file (check `/prd-excerpt US-045` for the shape). Mark the implemented ones ✅ the way US-045/046 are marked.
- [ ] **Step 2:** Run `/check-all`. Expected: backend and frontend green.
- [ ] **Step 3: Commit** `docs: add Basal decision layer stage 1 user stories to PRD`

Gates 1 and 2 (the switch to `live`) are not implementation tasks. Łukasz makes that call from the eval report and the shadow data.
