# Scammer Arena Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A harness that runs PhishGuard and a plain-LLM baseline against an LLM-played scammer on 24 scenarios × 3 repetitions, saves every conversation, and generates `EVALS.md` with a chart from the saved results.

**Architecture:**
- New package `backend/src/phishguard/arena/`:
  - scenarios (YAML → Pydantic);
  - a scammer driver;
  - two victim adapters (`PhishGuardVictim` over the production LangGraph graphs, `BaselineVictim` with one LLM call per turn);
  - a conversation loop;
  - a runner/CLI that writes JSON;
  - pure metric and report modules that read only the JSON.
- Four small production seams make the real graphs measurable without changing app behaviour:
  - a persona seed;
  - exposing the agent's regeneration count;
  - a distinct "safety exhausted" error;
  - context-local LLM usage tracking.

**Tech Stack:** Python 3.13, uv, LangGraph (existing graphs), Pydantic v2, PyYAML, phonenumbers, matplotlib (Agg backend), pytest + pytest-asyncio.

**Spec:** `docs/superpowers/specs/2026-11-06-scammer-arena-design.md`

## Global Constraints

- Model `gpt-6-luna` on both sides (victim and scammer); token prices come from `PRICES_PER_MTOK` via `llm_cost_usd`.
- 24 scenarios:
  - 16 `en`: the 8 `AttackType` values other than `not_phishing`, × `easy`/`hard`;
  - 8 `pl`: parcel surcharge (OLX/Allegro), BLIK, fake bank transfer and crypto investment, × `easy`/`hard`.
- `max_turns` defaults to 10. Turn 0 is the victim's first reply to the email. Turn n ≥ 1 is a scammer message plus the victim reply.
- 3 repetitions per scenario per system. The table shows the mean of the per-repetition means and the min–max. "Within noise" means the min–max ranges overlap.
- Persona seed per scenario, derived deterministically from the scenario id. Setup (classification + persona) runs once per scenario and is shared by both systems and all repetitions.
- The Arena forces Basal off: `BASAL_URL=""` before settings load, with `get_settings.cache_clear()`.
- No Supabase writes: `session_id=None` everywhere.
- Unit tests never call an LLM API. CI required checks are unchanged.
- All scenario data is fictional:
  - IBAN, BTC and URL secrets must be extracted by `IntelCollector` exactly as written;
  - phones must pass `phonenumbers.is_valid_number`;
  - URL hosts must end in `.example`, `.test` or `.invalid`.
- Victim cost per conversation includes PhishGuard's setup cost (classification + persona), split evenly across that scenario's PhishGuard conversations. Scammer cost is recorded but never compared.
- Paths:
  - code in `backend/src/phishguard/arena/`;
  - scenarios in `evals/scenarios/<id>.yaml`;
  - results in `evals/results/<YYYY-MM-DD>/`;
  - report in `EVALS.md` and `evals/chart.png` at the repo root.
- All repository text is English. Polish appears only inside the 8 Polish scenarios.
- Commits follow `.claude/skills/commit/SKILL.md` (`<type>: <subject>`, no `Co-Authored-By`).

## Review Focus

1. The scammer writes a secret in a different format than the scenario stores it: a spaced IBAN, a phone with dashes, a URL followed by a full stop or a comma. The reveal must still be detected. Test in Task 7: `test_reveal_detected_despite_formatting`.
2. The scammer reveals a secret in the same message that ends the conversation. The reveal must count, and the victim does not reply. Test in Task 7: `test_reveal_in_final_scammer_message_counts`.
3. Setup fails for a scenario: the profiler returns `not_phishing` or the intake graph returns `error`. All conversations of that scenario must be recorded as `invalid` with the reason, and the run must continue. Test in Task 8: `test_setup_failure_marks_scenario_invalid_and_run_continues`.
4. The result folder is incomplete (an interrupted run, or one system only). `report` must still render and list the missing conversations, never crash. Test in Task 10: `test_report_renders_with_missing_conversations`.
5. Conversations running concurrently must each count only their own tokens. Test in Task 2: `test_usage_is_isolated_between_concurrent_tasks`.

---

### Task 1: Graph seams — persona seed, regeneration count, safety-exhausted error

**Files:**
- Modify:
  - `backend/src/phishguard/orchestrator/state.py` (add `persona_seed: int | None`, `agent_regeneration_count: int`);
  - `backend/src/phishguard/orchestrator/nodes.py:66-100` (`select_persona`) and `:103-170` (`generate_response`);
  - `backend/src/phishguard/agents/conversation.py:61` (new subclass) and `:261` (raise site).
- Test: `backend/tests/unit/orchestrator/test_arena_seams.py`

**Interfaces — Produces:**
- `PhishGuardState.persona_seed: int | None`: when set, `select_persona` builds `PersonaEngine(seed=persona_seed)`. When absent, it builds `PersonaEngine()` as today.
- `PhishGuardState.agent_regeneration_count: int`: `generate_response` returns `result.regeneration_count` under this key.
- `class SafetyRegenerationExhaustedError(ResponseGenerationError)` in `phishguard.agents.conversation`, raised only when every regeneration attempt failed safety. LLM failures keep raising plain `ResponseGenerationError`.

- [ ] **Step 1: Write the failing tests**
  - `test_select_persona_with_seed_is_deterministic`: two `select_persona({"classification": {"attack_type": "romance_scam", ...}, "persona_seed": 1234})` calls return equal `persona` dicts.
  - `test_select_persona_without_seed_still_works`: no `persona_seed`, and the result has a `persona` with a non-empty `name`.
  - `test_generate_response_exposes_agent_regeneration_count`: patch `ConversationAgent.generate_response` to return a `ResponseGenerationResult` with `regeneration_count=2`, and assert the node output has `agent_regeneration_count == 2`.
  - `test_exhausted_safety_raises_dedicated_error`: patch the validator so every draft is unsafe and use a fake LLM client (injected via `ConversationAgent(llm_client=...)`).
    - `pytest.raises(SafetyRegenerationExhaustedError)`;
    - it is also an instance of `ResponseGenerationError`.
  - `test_llm_failure_is_not_safety_exhausted`: the fake client raises `LLMRequestError`. The raised error is `ResponseGenerationError` and **not** `SafetyRegenerationExhaustedError`.
- [ ] **Step 2: Run the tests to verify they fail**
  Run: `cd backend && uv run pytest tests/unit/orchestrator/test_arena_seams.py -v`
  Expected: FAIL (ImportError for `SafetyRegenerationExhaustedError`, KeyError / missing keys).
- [ ] **Step 3: Implement the seams** as in Interfaces. API callers never set `persona_seed`, so API behaviour is unchanged.
- [ ] **Step 4: Run the tests and the full suite**
  Run: `uv run pytest tests/unit/orchestrator/test_arena_seams.py -v && uv run pytest -q`
  Expected: all PASS (baseline 753 passed, 1 xfailed, plus the new tests).
- [ ] **Step 5: Commit** `feat: add persona seed and safety seams to the graph`

### Task 2: Context-local LLM usage tracking

**Files:**
- Create: `backend/src/phishguard/llm/usage.py`
- Modify: `backend/src/phishguard/llm/client.py` (`LLMClient.chat_completion`), `backend/src/phishguard/llm/__init__.py` (export)
- Test: `backend/tests/unit/llm/test_usage.py`

**Interfaces — Produces:**
- `class UsageEntry(BaseModel)`: `model: str`, `prompt_tokens: int`, `completion_tokens: int`, `latency_ms: int`.
- `class UsageLog`: `entries: list[UsageEntry]`, `def total_cost_usd(self) -> float` (sum of `llm_cost_usd` per entry).
- `@contextmanager def track_usage() -> Iterator[UsageLog]`: backed by a `contextvars.ContextVar[UsageLog | None]`. Nested blocks record into the innermost log only.
- `LLMClient.chat_completion` appends one `UsageEntry` per successful response to the active log. With no active log, it does nothing.

- [ ] **Step 1: Write the failing tests**
  - `test_track_usage_records_each_completion`: a client with an injected fake provider returns `Completion("ok", 10, 5)` twice. Inside `track_usage()`, `len(log.entries) == 2` and `log.entries[0].prompt_tokens == 10`.
  - `test_no_active_log_records_nothing`: a call outside `track_usage()` raises nothing, and the module-level var stays `None`.
  - `test_usage_is_isolated_between_concurrent_tasks` (Review Focus 5): two `asyncio.gather` tasks, each inside its own `track_usage()`, making 1 and 3 calls. Each log has exactly its own count.
  - `test_total_cost_uses_price_table`: one entry for `gpt-6-luna` with 1,000,000 / 1,000,000 tokens gives `total_cost_usd() == pytest.approx(0.60)`.
- [ ] **Step 2: Run them to verify they fail**
  Run: `uv run pytest tests/unit/llm/test_usage.py -v`
  Expected: FAIL (ModuleNotFoundError).
- [ ] **Step 3: Implement `usage.py` and the hook in `chat_completion`.** The latency is the wall time of the successful attempt, including the fallback when it was used.
- [ ] **Step 4: Run the tests and the full suite**
  Run: `uv run pytest tests/unit/llm -v && uv run pytest -q`
  Expected: PASS.
- [ ] **Step 5: Commit** `feat: track LLM token usage per async context`

### Task 3: Scenario model, loader and validation

**Files:**
- Create: `backend/src/phishguard/arena/__init__.py`, `backend/src/phishguard/arena/scenario.py`
- Modify: `backend/pyproject.toml` (add `pyyaml>=6.0` as a direct dependency), `backend/uv.lock`
- Test: `backend/tests/unit/arena/__init__.py`, `backend/tests/unit/arena/test_scenario.py`, fixtures in `backend/tests/unit/arena/fixtures/`

**Interfaces — Produces:**
- `class Secret(BaseModel)`: `id: str`, `type: Literal["iban","btc_wallet","url","phone"]` (the `IOCType` values), `value: str`, `reveal_when: str`.
- `class Scenario(BaseModel)`:
  - `id: str`;
  - `language: Literal["en","pl"]`;
  - `attack_type: AttackType` (validator rejects `not_phishing`);
  - `difficulty: Literal["easy","hard"]`;
  - `email: str`;
  - `scammer: str`;
  - `secrets: list[Secret]` (length 2–3);
  - `known_iocs: list[str] = []`;
  - `max_turns: int = 10`;
  - property `content_hash: str` (sha256 of the canonical JSON dump, first 12 hex chars);
  - property `persona_seed: int` (`int(sha256(id)[:8], 16)`).
- `def load_scenario(path: Path) -> Scenario`, `def load_scenarios(directory: Path) -> list[Scenario]` (sorted by id). The file stem must equal `id`.
- `class ScenarioError(ValueError)`.
- Validation (raises `ScenarioError` naming the file and the secret):
  - `iban`, `btc_wallet` and `url` values are extracted by `IntelCollector().extract(value, 0)` as exactly that type and value;
  - `phone` passes `phonenumbers.is_valid_number(phonenumbers.parse(value, None))`;
  - URL hosts end in `.example`, `.test` or `.invalid`;
  - secret ids are unique.

  Note: `IntelCollector` does not extract spaced IBANs (checked 2026-11-06), so `iban` secrets are stored compact (e.g. `PL61109010140000071219812874`). Scammers may still write them spaced, and Task 7 normalises for reveal detection.

- [ ] **Step 1: Write the failing tests**
  - `test_load_valid_scenario` (fixture `valid.yaml`): fields parse, `persona_seed` is stable across two loads, `content_hash` has 12 chars.
  - `test_rejects_not_phishing_attack_type`.
  - `test_rejects_secret_count_outside_2_to_3` (1 and 4 secrets).
  - `test_rejects_iban_with_bad_checksum`, `test_rejects_spaced_iban`, `test_rejects_invalid_phone`, `test_rejects_real_looking_url_host` (e.g. `https://paypal.com/x`).
  - `test_rejects_duplicate_secret_ids`, `test_rejects_file_name_id_mismatch`.
  - `test_load_scenarios_sorted_by_id`.
- [ ] **Step 2: Run them to verify they fail**
  Run: `uv add pyyaml && uv run pytest tests/unit/arena/test_scenario.py -v`
  Expected: FAIL (ModuleNotFoundError `phishguard.arena`).
- [ ] **Step 3: Implement `scenario.py`** with `yaml.safe_load` and Pydantic validators.
- [ ] **Step 4: Run the tests**
  Run: `uv run pytest tests/unit/arena -v`
  Expected: PASS.
- [ ] **Step 5: Commit** `feat: add Arena scenario model and validation`

### Task 4: The 24 scenarios

**Files:**
- Create: `evals/scenarios/*.yaml` (24 files)
- Test: `backend/tests/unit/arena/test_scenario_set.py`

**Interfaces:**
- Consumes: `load_scenarios` and `Scenario` from Task 3.
- Produces: scenario ids
  - `en-<attack_type>-<easy|hard>` for each of `nigerian_419`, `ceo_fraud`, `fake_invoice`, `romance_scam`, `tech_support`, `lottery_prize`, `crypto_investment` and `credential_phishing`;
  - `pl-parcel-<d>`, `pl-blik-<d>`, `pl-transfer-<d>` and `pl-crypto-<d>`.

  Each Polish scenario's `attack_type` is the closest `AttackType` for the scheme, chosen by the author and stated in the file.

- [ ] **Step 1: Write the failing test** `test_scenario_set_matches_spec` (loads `<repo>/evals/scenarios` via a path relative to the test file):
  - 24 scenarios, 16 `en` and 8 `pl`;
  - every non-`not_phishing` `AttackType` appears exactly twice among the `en` scenarios, once `easy` and once `hard`;
  - the ids match the list above;
  - each of `iban`, `btc_wallet`, `url` and `phone` appears as a secret type in at least 4 scenarios;
  - at least 12 scenarios have an `iban` secret;
  - every `hard` scenario's `scammer` text contains the word "suspicious" or "wary". This is a cheap guard that the hard variant is actually harder; the author writes the scammer accordingly.
- [ ] **Step 2: Run it to verify it fails**
  Run: `uv run pytest tests/unit/arena/test_scenario_set.py -v`
  Expected: FAIL (0 scenarios).
- [ ] **Step 3: Write the 24 YAML files.**
  - Emails and scammer descriptions are realistic for their scheme. Polish scenarios are written in Polish.
  - The `reveal_when` conditions are concrete behaviours, e.g. "after the victim agrees to pay and asks where to send the money". `hard` conditions require two victim behaviours, or come after a verification question.
  - Brand names (OLX, Allegro, BLIK) appear only as the thing the scammer impersonates. No real people, real phone numbers or real domains.
- [ ] **Step 4: Run the tests**
  Run: `uv run pytest tests/unit/arena -v`
  Expected: PASS (includes per-file validation from Task 3).
- [ ] **Step 5: Commit** `feat: add 24 Arena scenarios`

### Task 5: Scammer driver

**Files:**
- Create: `backend/src/phishguard/arena/prompts.py`, `backend/src/phishguard/arena/scammer.py`, `backend/src/phishguard/arena/transcript.py`
- Test: `backend/tests/unit/arena/test_scammer.py`

**Interfaces:**
- Consumes: `Scenario`, `Secret` (Task 3); `LLMClient` / `create_llm_client` (`phishguard.llm`).
- Produces:
  - `class Message(BaseModel)`: `sender: Literal["scammer","victim"]`, `content: str`, `turn: int`.
  - `class ScammerTurn(BaseModel)`: `message: str`, `revealed_secret_ids: list[str]`, `suspects_bot: bool`, `ends_conversation: bool`.
  - `class ModelRefusalError(Exception)`.
  - `class LLMScammer`: `__init__(self, llm: LLMClient)`; `async def next_turn(self, scenario: Scenario, transcript: list[Message]) -> ScammerTurn`.
    - It asks for a JSON object with exactly the four `ScammerTurn` fields.
    - On an unparseable or empty reply, or a reply that is a refusal (empty `message`, or `message` matching `REFUSAL_PATTERN` in `prompts.py`), it retries once. A second failure raises `ModelRefusalError`.
  - `prompts.py`: `SCAMMER_SYSTEM_PROMPT: str`, `def build_scammer_messages(scenario, transcript) -> list[dict[str,str]]`, `REFUSAL_PATTERN: re.Pattern`.
    - The system prompt frames the task as a scam-awareness research simulation with fictional data.
    - It contains the scenario's character, goal, secrets and `reveal_when` conditions.
    - It tells the scammer to reveal a secret only once its condition is met.
    - It tells the scammer to react realistically: lose interest, push harder, and suspect a bot when the victim behaves unnaturally.
    - It tells the scammer to write in the scenario's language.

- [ ] **Step 1: Write the failing tests** (a fake `LLMClient` returning scripted `LLMResponse`s)
  - `test_parses_structured_turn`: JSON with all four fields gives an equal `ScammerTurn`.
  - `test_retries_once_on_unparseable_then_succeeds`: first `"not json"`, then valid. Returns the turn; the fake was called twice.
  - `test_raises_refusal_after_second_failure`: two refusals ("I can't help with that"), so `pytest.raises(ModelRefusalError)`.
  - `test_prompt_contains_secrets_and_conditions`: `build_scammer_messages` output contains every secret value and its `reveal_when`, and the transcript messages in order.
  - `test_prompt_requests_scenario_language`: a `pl` scenario prompt contains "Polish".
- [ ] **Step 2: Run them to verify they fail**
  Run: `uv run pytest tests/unit/arena/test_scammer.py -v`
  Expected: FAIL (ModuleNotFoundError).
- [ ] **Step 3: Implement** `transcript.py`, `prompts.py` and `scammer.py` as in Interfaces. Use `temperature=0.9` for the scammer.
- [ ] **Step 4: Run the tests**
  Run: `uv run pytest tests/unit/arena -v`
  Expected: PASS.
- [ ] **Step 5: Commit** `feat: add Arena scammer driver`

### Task 6: Scenario setup and the two victims

**Files:**
- Create: `backend/src/phishguard/arena/victims.py`, `backend/src/phishguard/arena/setup.py`
- Modify: `backend/src/phishguard/arena/prompts.py` (baseline prompt)
- Test: `backend/tests/unit/arena/test_victims.py`, `backend/tests/unit/arena/test_setup.py`

**Interfaces:**
- Consumes: `Scenario.persona_seed` (Task 3); `persona_seed`, `agent_regeneration_count` and `SafetyRegenerationExhaustedError` (Task 1); `track_usage` / `UsageLog` (Task 2); `Message` (Task 5).
- Produces:
  - `class ScenarioSetup(BaseModel)`: `scenario_id: str`, `classification: dict`, `persona: dict`, `email_iocs: list[dict]`, `usage: list[UsageEntry]`, `error: str | None`.
  - `async def prepare_scenario(scenario: Scenario) -> ScenarioSetup`:
    - runs `create_phishguard_graph().ainvoke` with `{"email_content": scenario.email, "persona_seed": scenario.persona_seed, "session_id": None}` inside `track_usage()`;
    - sets `error` to `"not_phishing"` when the classification is `not_phishing`, to the graph's `error` value when present, or to the exception text on an exception.
  - `class VictimReply(BaseModel)`: `content: str`, `extracted_iocs: list[dict]` (IOCs found in the scammer message that preceded this reply), `regenerations: int`, `is_safe: bool` (the graph's final `is_safe`; always `True` for the baseline), `thinking: dict | None`.
  - `class Victim(Protocol)`: `name: str`; `async def reply(self, transcript: list[Message], scammer_message: str | None) -> VictimReply`.
  - `class PhishGuardVictim`: `__init__(self, setup: ScenarioSetup, email: str)`.
    - It keeps its own `conversation_history` in the graph format.
    - Each `reply` calls `create_continuation_graph().ainvoke` with `{email_content, classification, persona, conversation_history, scammer_message, extracted_iocs: [], is_safe: True, safety_violations: [], regeneration_count: 0, session_id: None}`.
    - It updates its history from `result_state["conversation_history"]`.
    - It returns `regenerations = agent_regeneration_count + regeneration_count`.
    - `SafetyRegenerationExhaustedError` propagates.
  - `class BaselineVictim`: `__init__(self, persona: dict, email: str, language: str, llm: LLMClient)`.
    - One `chat_completion` per reply, with `BASELINE_SYSTEM_PROMPT` (in `prompts.py`) plus the email and the transcript as chat turns.
    - `extracted_iocs=[]`, `regenerations=0`, `thinking=None`.
    - `BASELINE_SYSTEM_PROMPT` describes the persona (name, age, style, background). In one paragraph it tells the victim to stay in character, keep the conversation going and get the scammer to share payment details. It asks for a reply in the language of the scammer's latest message. It says nothing about IOC extraction or safety.

- [ ] **Step 1: Write the failing tests** (patch `create_llm_client` in `phishguard.agents.profiler` and `phishguard.agents.conversation` to a scripted fake for the PhishGuard tests)
  - `test_prepare_scenario_returns_seeded_persona`: two calls give equal `persona`. `usage` has ≥ 1 entry (the profiler call).
  - `test_prepare_scenario_not_phishing_sets_error`: the fake profiler answers `not_phishing`, so `setup.error == "not_phishing"`.
  - `test_phishguard_victim_carries_history_between_turns`: a first reply with `scammer_message=None`, then a second with "send money". The second graph call receives a history of 2 messages (bot, scammer). `extracted_iocs` contains the IBAN when the scammer message contains `GB82WEST12345698765432`.
  - `test_phishguard_victim_propagates_safety_exhausted`.
  - `test_baseline_prompt_states_goal_and_persona`: `BASELINE_SYSTEM_PROMPT` rendered for a persona contains the persona name and "payment details".
  - `test_baseline_victim_sends_transcript_as_chat_turns`: scammer messages map to role `user`, victim messages to role `assistant`.
- [ ] **Step 2: Run them to verify they fail**
  Run: `uv run pytest tests/unit/arena/test_victims.py tests/unit/arena/test_setup.py -v`
  Expected: FAIL.
- [ ] **Step 3: Implement** `setup.py`, `victims.py` and the baseline prompt.
- [ ] **Step 4: Run the tests**
  Run: `uv run pytest tests/unit/arena -v && uv run pytest -q`
  Expected: PASS.
- [ ] **Step 5: Commit** `feat: add Arena scenario setup and victim adapters`

### Task 7: Conversation loop and reveal detection

**Files:**
- Create: `backend/src/phishguard/arena/conversation.py`, `backend/src/phishguard/arena/records.py`
- Test: `backend/tests/unit/arena/test_conversation.py`

**Interfaces:**
- Consumes: `Scenario` (Task 3); `LLMScammer`, `ScammerTurn`, `Message`, `ModelRefusalError` (Task 5); `Victim`, `VictimReply` (Task 6); `track_usage` (Task 2); `detect_unmasking` (`phishguard.safety`); `SafetyRegenerationExhaustedError` (Task 1).
- Produces:
  - `def normalise(text: str) -> str`: lowercase; remove whitespace, `-`, `(` and `)`; strip trailing `.,;:!?`. It is applied both to secret values and to the message, before substring matching.
  - `def detect_reveals(scenario: Scenario, message: str) -> list[str]`: the ids of secrets whose normalised value appears in the normalised message.
  - `records.py`:
    - `class TurnRecord(BaseModel)`: `index: int`, `scammer: ScammerTurn | None`, `detected_reveals: list[str]`, `unmasking_detected: bool`, `victim: VictimReply | None`.
    - `class ConversationRecord(BaseModel)`:
      - `scenario_id: str`, `scenario_hash: str`, `system: Literal["phishguard","baseline"]`, `repetition: int`;
      - `status: Literal["completed","invalid","error","blocked_by_safety"]`, `status_reason: str | None`;
      - `end_reason: Literal["turn_limit","scammer_ended","blocked_by_safety","invalid","error"]`;
      - `turns: list[TurnRecord]`;
      - `victim_usage: list[UsageEntry]`, `scammer_usage: list[UsageEntry]`;
      - `started_at: str`, `duration_ms: int`.
  - `async def run_conversation(scenario: Scenario, victim: Victim, scammer: LLMScammer, system: str, repetition: int) -> ConversationRecord`:
    - turn 0: the victim replies to the email;
    - then, for turn 1..`max_turns`:
      - scammer turn;
      - `detect_reveals`;
      - `detect_unmasking`;
      - if `ends_conversation`, record the turn without a victim reply and stop with `scammer_ended`;
      - otherwise the victim replies.
    - Exceptions map to the status:
      - `ModelRefusalError` → `invalid` (reason `scammer_refused` or `victim_refused`);
      - `SafetyRegenerationExhaustedError` → `blocked_by_safety`;
      - any other exception → `error` with the exception text.
    - Victim and scammer calls run under separate `track_usage()` blocks.

- [ ] **Step 1: Write the failing tests** (a fake victim and a fake scammer with scripted turns)
  - `test_runs_to_turn_limit`: a scammer that never ends with `max_turns=3` gives `end_reason == "turn_limit"` and turns 0..3 (4 records). Turn 0 has `scammer is None`.
  - `test_scammer_can_end_conversation`: ends at turn 2, so `end_reason == "scammer_ended"` and the last turn has `victim is None`.
  - `test_reveal_detected_despite_formatting` (Review Focus 1), parametrised over:
    - secret `PL61109010140000071219812874` in the message `"konto: PL61 1090 1014 0000 0712 1981 2874."`;
    - phone `+447700900123` in `"call +44 7700-900123,"`;
    - url `https://pay.example/x` in `"go to https://pay.example/x."`.

    Each is detected.
  - `test_reveal_not_detected_for_partial_value`: half of an IBAN is not a reveal.
  - `test_reveal_in_final_scammer_message_counts` (Review Focus 2): the ending turn contains the IBAN, so `detected_reveals` holds its id.
  - `test_refusal_marks_invalid`, `test_safety_exhausted_marks_blocked`, `test_unexpected_error_marks_error`: each status and reason as specified, and a record is still returned.
  - `test_unmasking_flag_recorded`: the scammer message "are you a bot?" gives `unmasking_detected is True`.
- [ ] **Step 2: Run them to verify they fail**
  Run: `uv run pytest tests/unit/arena/test_conversation.py -v`
  Expected: FAIL.
- [ ] **Step 3: Implement** `records.py` and `conversation.py`.
- [ ] **Step 4: Run the tests**
  Run: `uv run pytest tests/unit/arena -v`
  Expected: PASS.
- [ ] **Step 5: Commit** `feat: add Arena conversation loop and reveal detection`

### Task 8: Runner and `run` command

**Files:**
- Create: `backend/src/phishguard/arena/runner.py`, `backend/src/phishguard/arena/__main__.py`
- Test: `backend/tests/unit/arena/test_runner.py`

**Interfaces:**
- Consumes: everything from Tasks 3–7.
- Produces:
  - `class RunMeta(BaseModel)`: `date: str`, `commit: str` (`git rev-parse --short HEAD`, or `"unknown"`), `model: str`, `repetitions: int`, `systems: list[str]`, `scenario_ids: list[str]`.
  - `async def run_arena(scenarios: list[Scenario], systems: list[str], repetitions: int, out_dir: Path, concurrency: int = 4, *, victim_factory=None, scammer_factory=None, setup_fn=prepare_scenario) -> RunMeta`. The keyword factories are test seams.
  - On-disk layout:
    - `out_dir/run.json` (`RunMeta`);
    - `out_dir/setup/<scenario_id>.json` (`ScenarioSetup`);
    - `out_dir/conversations/<scenario_id>__<system>__r<n>.json` (`ConversationRecord`, `indent=2`, `sort_keys=True`, UTF-8, `ensure_ascii=False`).
  - A scenario whose setup has `error` gets `invalid` records for every system and repetition, with `status_reason = "setup: <error>"`.
  - An existing conversation file is skipped (resume), so an interrupted run can be continued without paying twice.
  - `force_basal_off()`: sets `os.environ["BASAL_URL"] = ""` and calls `get_settings.cache_clear()`. Called at the start of `run_arena`.
  - CLI: `python -m phishguard.arena run [--scenarios DIR] [--scenario ID ...] [--repetitions N] [--system phishguard|baseline|both] [--out DIR] [--concurrency N]`.
    - Defaults: `<repo>/evals/scenarios`, all scenarios, 3 repetitions, `both`, `<repo>/evals/results/<today>`, concurrency 4.
    - It prints a one-line summary per conversation and the total victim and scammer cost at the end.

- [ ] **Step 1: Write the failing tests** (fake factories and a fake `setup_fn`, `tmp_path`)
  - `test_writes_expected_files`: 2 scenarios × 2 systems × 2 repetitions give 8 conversation files, 2 setup files and `run.json` with `repetitions == 2`.
  - `test_setup_failure_marks_scenario_invalid_and_run_continues` (Review Focus 3): `setup_fn` returns `error="not_phishing"` for one scenario. Its records are all `invalid` with reason `"setup: not_phishing"`, and the other scenario's records are `completed`.
  - `test_existing_conversation_files_are_skipped`: pre-create one file. The factory is not called for it and the file is unchanged.
  - `test_force_basal_off`: with `BASAL_URL=http://x` set, after `force_basal_off()` `get_settings().basal_mode_for("profiler.attack_type") == "off"`.
  - `test_cli_parses_flags`: `parse_args(["run","--scenario","en-romance_scam-easy","--system","baseline","--repetitions","1"])` gives the expected namespace.
- [ ] **Step 2: Run them to verify they fail**
  Run: `uv run pytest tests/unit/arena/test_runner.py -v`
  Expected: FAIL.
- [ ] **Step 3: Implement** `runner.py` and `__main__.py`. Bound concurrency with `asyncio.Semaphore`.
- [ ] **Step 4: Run the tests and the full gate**
  Run: `uv run pytest -q && uv run ruff check . && uv run ruff format --check .`
  Expected: PASS and clean.
- [ ] **Step 5: Commit** `feat: add Arena runner and run command`

### Task 9: Metrics

**Files:**
- Create: `backend/src/phishguard/arena/metrics.py`
- Test: `backend/tests/unit/arena/test_metrics.py`

**Interfaces:**
- Consumes: `ConversationRecord`, `ScenarioSetup`, `RunMeta`, `UsageEntry`, `llm_cost_usd`.
- Produces:
  - `class ConversationMetrics(BaseModel)`:
    - `secrets_revealed_share: float`;
    - `turns_to_first_secret: int | None`;
    - `suspected_bot: bool` (any `scammer.suspects_bot`);
    - `unmasking_detected: bool`;
    - `engagement_turns: int` (the highest turn index with a scammer message);
    - `victim_cost_usd: float` (turn usage plus the setup share for PhishGuard);
    - `setup_cost_usd: float`;
    - `victim_latency_ms: int`;
    - `scammer_claimed_reveals: int`;
    - `ioc_true_positives: int`, `ioc_false_positives: int`, `ioc_revealed: int`;
    - `safety_regenerations: int` (total regenerations), `safety_turns: int` (turns with at least one regeneration), `unsafe_replies_sent: int` (replies with `is_safe == False`; expected 0).
  - `def conversation_metrics(record: ConversationRecord, scenario: Scenario, setup_cost_share: float) -> ConversationMetrics`.
    - An IOC true positive is an extracted IOC whose normalised value matches a revealed secret.
    - A false positive matches neither a secret nor a `known_iocs` entry.
  - `class Aggregate(BaseModel)`: `mean: float | None`, `min: float | None`, `max: float | None`, `n_valid: int`, `n_excluded: int`.
  - `def aggregate(per_repetition_values: list[float | None]) -> Aggregate`. The inputs are per-repetition means; `None` values are excluded and counted.
  - `def within_noise(a: Aggregate, b: Aggregate) -> bool`: true when `[a.min, a.max]` and `[b.min, b.max]` overlap.
  - `def summarise(results_dir: Path, scenarios: dict[str, Scenario]) -> Summary`. `Summary` holds:
    - headline `Aggregate`s per system for the four headline metrics plus engagement;
    - per-scenario rows;
    - an EN/PL split;
    - PhishGuard IOC precision/recall and safety totals;
    - PhishGuard cost split into setup and turns;
    - profiler agreement;
    - counts of invalid / error / blocked / missing conversations.

    Only `completed` and `blocked_by_safety` conversations enter the metrics.

- [ ] **Step 1: Write the failing tests** (hand-built records with known answers)
  - `test_share_and_turns_to_first_secret`: 3 secrets, reveals at turns 2 and 5, so the share is `2/3` and `turns_to_first_secret == 2`.
  - `test_no_reveal_gives_none_turns`.
  - `test_setup_cost_added_for_phishguard_only`: the same usage with a setup share of 0.003 gives PhishGuard cost = baseline cost + 0.003.
  - `test_ioc_precision_counts_known_iocs_as_not_false`.
  - `test_aggregate_excludes_none_and_reports_min_max`: `[0.5, None, 0.7]` gives mean 0.6, min 0.5, max 0.7, `n_excluded` 1.
  - `test_within_noise_overlap_rule`: `(0.4–0.6)` vs `(0.55–0.8)` is True; `(0.4–0.5)` vs `(0.6–0.8)` is False.
  - `test_invalid_conversations_excluded_and_counted`.
- [ ] **Step 2: Run them to verify they fail**
  Run: `uv run pytest tests/unit/arena/test_metrics.py -v`
  Expected: FAIL.
- [ ] **Step 3: Implement `metrics.py`.** Per repetition, take the mean over scenarios; then `aggregate` across repetitions.
- [ ] **Step 4: Run the tests**
  Run: `uv run pytest tests/unit/arena -v`
  Expected: PASS.
- [ ] **Step 5: Commit** `feat: add Arena metrics`

### Task 10: Report and `report` command

**Files:**
- Create: `backend/src/phishguard/arena/report.py`
- Modify: `backend/src/phishguard/arena/__main__.py` (subcommand)
- Test: `backend/tests/unit/arena/test_report.py`, fixture results in `backend/tests/unit/arena/fixtures/results/`

**Interfaces:**
- Consumes: `summarise`, `Summary`, `within_noise` (Task 9); records (Task 7); `RunMeta` (Task 8).
- Produces:
  - `def select_excerpt(results_dir: Path, override: str | None) -> tuple[ConversationRecord, int]`. It returns the PhishGuard conversation with the earliest `iban` reveal (ties broken by file name), else the earliest reveal of any secret, plus the reveal turn index. `override` is a conversation file stem.
  - `def render_markdown(summary: Summary, meta: RunMeta, excerpt: tuple[ConversationRecord, int], chart_path: str, results_rel: str) -> str`. Sections in the spec's order:
    1. the headline table;
    2. the chart;
    3. the excerpt (2 messages before the reveal through 1 after it, and a link to the JSON);
    4. caveats;
    5. method;
    6. detailed results;
    7. how to reproduce.

    The caveats list the spec's five items. If invalid conversations exceed 10%, a warning line sits above the table.
  - `def render_chart(summary: Summary, path: Path) -> None`:
    - matplotlib `Agg`;
    - grouped bars for the 4 headline metrics, PhishGuard vs baseline, with min–max error bars;
    - transparent background and mid-grey text, readable in GitHub light and dark;
    - `savefig(..., metadata={"Software": None})` so output is byte-stable.
  - CLI: `python -m phishguard.arena report [--results DIR] [--excerpt STEM] [--out EVALS.md] [--chart evals/chart.png]`. Defaults: the newest folder in `evals/results/`, `<repo>/EVALS.md`, `<repo>/evals/chart.png`.

- [ ] **Step 1: Write the failing tests** (a fixture results folder with 2 scenarios × 2 systems × 2 repetitions, hand-written)
  - `test_report_starts_with_headline_table`: the first table in the output has the columns "Secrets extracted", "Turns to first secret", "Bot detected" and "Cost / conversation" and rows "PhishGuard" and "Baseline (plain LLM)".
  - `test_report_contains_caveats_and_reproduce_section`: it contains "simulation is not production", "same model", "fictional" and the two commands.
  - `test_excerpt_prefers_earliest_iban_reveal`.
  - `test_excerpt_override`.
  - `test_report_is_deterministic`: two renders, plus two chart renders, are byte-identical.
  - `test_report_renders_with_missing_conversations` (Review Focus 4): delete half the baseline files. The report renders, and the detailed section states the missing count.
  - `test_invalid_share_warning`: with > 10% invalid, a warning line appears above the table.
- [ ] **Step 2: Run them to verify they fail**
  Run: `uv run pytest tests/unit/arena/test_report.py -v`
  Expected: FAIL.
- [ ] **Step 3: Implement** `report.py` and the subcommand.
- [ ] **Step 4: Run the tests and the full gate**
  Run: `uv run pytest -q && uv run ruff check . && uv run ruff format --check .`
  Expected: PASS and clean.
- [ ] **Step 5: Commit** `feat: add Arena report and chart`

### Task 11: First real run and `EVALS.md`

This task spends API money (about $1) with the owner's key. **Ask the owner before Step 2.**

- [ ] **Step 1: Smoke run.** With the owner's key exported from their `.env` in the main checkout (never copied into the worktree or logs):

  `cd backend && uv run python -m phishguard.arena run --scenario en-romance_scam-easy --repetitions 1 --out /tmp/arena-smoke`

  Expected: 2 conversation files with `status == "completed"`, and a printed cost below $0.05. Read one transcript end to end. If the scammer or victim behaves wrongly (refuses, breaks format, ignores the conditions), adjust the prompts in `prompts.py`, re-run the unit tests and repeat Step 1.
- [ ] **Step 2: Full run** (after the owner's go-ahead): `uv run python -m phishguard.arena run`.

  Expected:
  - 144 files in `evals/results/<today>/conversations/`;
  - invalid ≤ 10%;
  - the total victim cost is printed.
- [ ] **Step 3: Report.** `uv run python -m phishguard.arena report`. Expected: `EVALS.md` and `evals/chart.png` exist. Read `EVALS.md` top to bottom, and check the headline numbers against 3 conversation files by hand.
- [ ] **Step 4: Commit** `docs: add first Scammer Arena results` (`evals/`, `EVALS.md`), push, and open the PR with the headline table in the description.
