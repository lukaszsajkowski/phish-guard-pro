# Basal Decision Layer — Stage 1: foundation and Profiler

Date: 2026-11-02 · Source: the "Basal Decision Layer in PhishGuard Pro" PRD and a PRD-vs-code review from 2026-11-02.

## Why

PhishGuard Pro classifies an email (Profiler) with GPT-4o, which also reports its own 0–100 "confidence". That number is not calibrated. When GPT's answer cannot be parsed, the Profiler returns `not_phishing` with confidence 25 and the session ends.

Basal is a local decision model. It answers with a probability distribution over a closed list of options, calibrated so that a confidence threshold maps to a known error rate. The Basal → LLM cascade pattern is proven in autoshield (`~/Workspace/autoshield/judge.py`): 84% of verdicts were made locally at threshold 0.9, with zero disagreements on 250 cases.

**The code review changed the project goal.** The original PRD promised −50% LLM cost. That is not achievable. GPT is called in two places:
- the Profiler, once per session (`max_tokens=200`);
- the Conversation Agent, once per turn, and the Conversation Agent stays on GPT.

So the project goal is **decisions with trustworthy confidence** and, in later stages, **new semantic checks** that regexes cannot provide. Cost is measured, but it is not the hypothesis.

Stage 1 builds the decision layer and moves onto it the one decision where Basal actually replaces GPT: the attack type in the Profiler. It also produces the eval numbers that stages 2 and 3 build on.

## Stage 1 hypothesis

At the chosen threshold, Basal settles at least 70% of attack-type classifications locally, agreeing with GPT-4o in ≥ 95% of cases (error ≤ 2% among Basal's decisions), with median latency < 150 ms locally. These numbers are a starting point; the first eval may adjust them.

## Goals

1. A `phishguard.decisions` module with:
   - a Basal client;
   - language detection;
   - the Basal → LLM cascade;
   - a record of every decision.
2. Three modes: `off`, `shadow` (Basal computes, GPT gives the verdict) and `live` (the cascade).
3. The Profiler uses the cascade for the attack type.
4. A token counter for every GPT call (Profiler and Conversation Agent), so the "before and after" cost is measured rather than estimated.
5. An eval CLI over saved Supabase sessions plus a synthetic email set. It produces a coverage vs. error report as a function of the threshold.

## Non-goals (stage 1)

- The "does the reply break character" check (stage 2) and scoring IOCs as bait (stage 3).
- Risk level on Basal: the deterministic formula in `risk_score_service.py` stays, because it is explainable and free.
- "Next step" as `act`: today the Conversation Agent picks the tactic in the same call that writes the reply, so a separate decision would add a call instead of removing one.
- A Decision Ops panel in the app: in stage 1 the eval report plays that role.
- `evidence` mode: it only works with an in-process PyTorch model, not on MLX (`basal/server.py`: "evidence is not available for this model"), so it cannot be used on a Mac.
- Fine-tuning Basal, cloud GPUs, and languages other than PL/EN in Basal.

## Anti-goals (failure even if it "works")

- A session breaks or classification returns an error because Basal is off, slow or returns something unexpected.
- Shadow mode noticeably slows classification. Basal and GPT must run in parallel.
- The `decisions` table becomes a second copy of email content. The content is already in `messages`; `decisions` holds a reference to the session, not the text.
- Changing the meaning of `confidence` breaks today's UI warnings without a deliberate decision.

## How it works

### Cascade (`live` mode)

```
closed question
  ├─ BASAL_URL empty / mode off ──────────────────────────► LLM
  ├─ text not PL/EN (per-line detection) ─────────────────► LLM
  ├─ Basal: HTTP error / timeout ─────────────────────────► LLM  (session continues, warning in log)
  ├─ Basal: confidence ≥ node threshold ──────────────────► Basal verdict
  └─ Basal: confidence < threshold ───────────────────────► LLM (same option list)
```

Language detection follows autoshield (`is_basal_language`):
- `fast-langdetect`, checked per line;
- lines shorter than 20 letters are skipped;
- the text is rejected when a language outside {pl, en} scores ≥ 0.5.

### `shadow` mode

The verdict always comes from the LLM, exactly as today.
- Basal starts as a background task (`asyncio.create_task`) when the LLM call starts, and classification **does not wait** for it.
- The task writes its own `decisions` row when it finishes, even after the HTTP response has been returned.
- `BASAL_TIMEOUT_S` limits only this task; exceeding it is recorded as `skip_reason = 'timeout'`.
- Exceptions in the task are caught and logged and never leak.
- References to the tasks are kept in a module-level set so the GC does not collect them. This is my call: `asyncio.gather` with a timeout would add up to 5 s to every classification.

In `live` mode Basal is called first and the LLM only on escalation, so there Basal's latency is part of the path.

### Basal interface

The `basal-serve` server, endpoint `POST {BASAL_URL}` (e.g. `http://127.0.0.1:8011/v1/systemone`), as in autoshield:

```json
{"state": "<email content>",
 "questions": {"attack_type": {"type": "choice", "option_keys": "hide",
                               "instructions": "...", "criteria": {"nigerian_419": "...", ...}}}}
```

The response is `answers.attack_type` with `choice`, `probabilities` (key → p) and `confidence`.
- The option keys are the `AttackType` values (9 of them, including `not_phishing`). The descriptions come from the enum docstrings and `PROFILER_SYSTEM_PROMPT`.
- `option_keys: "hide"`, because that is how Basal was calibrated (comment in autoshield).
- No "other" category is added; as today, uncertain cases go to the LLM.

Model: `Remek/basal-2.0-max-MLX-8bit`, the same as in autoshield, already installed locally in `~/basal-mlx`. This is my call. `BASAL_MODEL` is used only for logs and the report; the server picks the model.

### Profiler in the cascade

`ProfilerAgent` gets an injected `DecisionService` (built from settings by default). The graph does not change. What changes:
- the `classify_email` node, which passes `session_id` to `classify()` and copies `decision_source` into state;
- `ClassificationState`, with a new `decision_source` field;
- `api/routers/classification.py`, which carries the field into `ClassificationResult`.

`update_session_classification` stores `decision_source` in a new column, `sessions.decision_source` (text, null for old sessions), and session restore (US-031) reads it back. That way the source label survives a reload. This is my call: without it, a restored session would show Basal's confidence with no label.

When Basal decides:
- `attack_type` = Basal's answer.
- `confidence` = calibrated p × 100 (the field stays on the 0–100 scale).
- `reasoning` = a templated text, because Basal does not write rationales and `evidence` does not work on MLX: `"Classified locally by Basal: Romance Scam (p=0.94). Runner-up: Nigerian 419 (p=0.03)."`
- `decision_source = "basal"` (a new field in `ClassificationResult`, default `"llm"`).

When the LLM decides: behaviour as today, with `decision_source = "llm"`.

**Fallback fix (`live` only).** The fix applies when GPT returns an unparseable answer, or the whole call fails (`LLMRequestError`, which today ends in a 500). If Basal did answer, even below the threshold, we return Basal's top option with its real confidence and `decision_source = "basal_low_confidence"`, instead of `not_phishing`/25. If Basal did not answer, today's fallback stays.

### Meaning of `confidence` in the UI

The frontend thresholds (`ClassificationResult.tsx`: < 30 warning for `not_phishing`, < 50 yellow, ≥ 80 "high") stay unchanged in stage 1. **The number changes meaning**, though: with Basal it is a calibrated probability, with GPT a self-assessment. Therefore:
- Next to the confidence, the UI shows a small source label ("Basal" / "GPT-4o") so it is clear which scale is being read. This is my call.
- The eval report shows whether the 30/50/80 thresholds make sense for Basal's confidence. Changing the thresholds is a decision for after the eval.

## Data

### `decisions` table (new migration)

| column | type | notes |
|---|---|---|
| id | uuid pk | |
| session_id | uuid fk → sessions, on delete cascade | |
| node | text | `'profiler.attack_type'` in stage 1 |
| mode | text check in (`shadow`, `live`) | |
| options | jsonb | list of option keys |
| basal_answer | text null | |
| basal_probabilities | jsonb null | |
| basal_confidence | float null | |
| basal_ms | int null | |
| basal_model | text null | |
| threshold | float | threshold in force for this decision |
| skip_reason | text null | `disabled`, `language`, `unavailable`, `timeout`, `below_threshold` |
| llm_answer | text null | |
| llm_model | text null | |
| llm_ms | int null | |
| final_answer | text | |
| source | text check in (`basal`, `llm`, `basal_low_confidence`) | |
| created_at | timestamptz default now() | |

RLS: read and write for the session owner, modelled on `ioc_extracted`. Index on `session_id` and `node`.

Writing a decision must never block classification: a write failure ends in a log warning.

### `llm_usage` table (new migration)

`id, session_id (fk, nullable), agent ('profiler'|'conversation'|'eval'), model, prompt_tokens, completion_tokens, latency_ms, created_at`, with RLS as above.

`LLMResponse` gets `prompt_tokens` and `completion_tokens` from the OpenAI `usage`. The agents write them to `llm_usage`. The report computes cost from a price list in a single dictionary (model → USD per 1M tokens in/out), not in the database.

## Configuration (`.env`, `Settings`)

| variable | default | meaning |
|---|---|---|
| `BASAL_URL` | `""` | empty = layer off, everything goes to the LLM |
| `BASAL_MODE` | `shadow` | `off` / `shadow` / `live`; ignored when `BASAL_URL` is empty |
| `BASAL_THRESHOLD` | `0.9` | default threshold (as in autoshield) |
| `BASAL_THRESHOLD_PROFILER` | unset | overrides the threshold for the Profiler node |
| `BASAL_TIMEOUT_S` | `30` | timeout for the Basal request. The default was raised to 30 s because local Basal on MLX needs several seconds per call, and shadow mode never blocks the response. The live-path timeout must be revisited before switching to live. |
| `BASAL_MODEL` | `""` | model label for logs and the report |

Thresholds are per node from the start, because stage 2 (the in-role check) will get a stricter threshold.

**Changing mode and thresholds:** only through `.env` and a backend restart (`Settings` is cached with `lru_cache`).
- In stage 1 there is no UI switch or endpoint. It is a single-owner setting for the whole instance, not per user or per session.
- Every `decisions` row records `mode` and `threshold`, so the data shows when settings changed.
- An in-app switch can come together with the Decision Ops panel.

## Eval (CLI)

`uv run python -m phishguard.decisions.eval profiler --source supabase|fixtures|decisions|all --out <dir>`

- `--source decisions` calls no model. It reads the `shadow`-mode rows from the `decisions` table (those with both a Basal and an LLM answer) and computes the same metrics on them, with the LLM as the reference. This is the tool for gate 2.
- `all` = `supabase` + `fixtures` (without `decisions`).

**Input:**
- **Supabase:** every session with its original email (`session_service.get_original_email`), read with the service role key. The number of usable sessions is unknown; the script reports it.
- **Fixtures:** `backend/tests/fixtures/eval/profiler_emails.jsonl`.
  - About 100 PL/EN emails with a `gold` label, several for each of the 9 types.
  - It includes hard cases: the CEO fraud / fake invoice boundary, real invoices, newsletters.
  - The emails are generated with an LLM.
  - **Labels are reviewed by a model, not a human** (owner decision, 2026-11-02), in a blind process:

1. The generator writes the email with its intended `gold` label and `reviewed: false`.
2. A fresh Claude subagent assigns a label (`label_b`). It is not GPT and not Basal, because the models being compared must not grade themselves. It sees only:
   - the email;
   - the list of 9 types with descriptions from `ATTACK_TYPE_CRITERIA`.

   It does not see `gold` or any model's answer.
3. `label_b == gold` gives `reviewed: true`.
4. On disagreement, a second, independent subagent gives `label_c`, also blind.
   - If two of the three labels agree, that label becomes `gold` and the row gets `reviewed: true`.
   - Otherwise the row gets `ambiguous: true` and does not count towards gate 1; the report shows it separately.
5. Every row records `review: {"label_b": ..., "label_c": ... | null, "reviewer_model": ...}`.

This set covers the "not enough historical sessions" risk.
- The eval report warns when any row has `reviewed: false`, and such a result does not pass gate 1.
- The report also states one limitation plainly: the labels are the agreement of two Claude models, not an expert's judgement.

**Run:** for each email, Basal (full distribution) and a fresh GPT-4o call with the current Profiler prompt. The reference is `gold` for fixtures and GPT-4o for Supabase. The `attack_type` stored in the session is only an extra column, because it may have come from `gpt-4o-mini` (the fallback).

**Output:**
- `results.jsonl`: one row per case, with Basal's distribution, GPT's answer, the reference and the timings.
- `report.md` covers thresholds 0.50–0.99 in steps of 0.01 and contains:
  - per threshold: coverage, error among Basal's decisions, overall cascade agreement;
  - p50/p95 latency of Basal and GPT;
  - GPT cost per 1,000 classifications;
  - a confusion matrix;
  - the lowest threshold meeting error ≤ 2%;
  - the distribution of Basal's confidence across the 30/50/80 bands, to inform the UI threshold decision.
- A coverage vs. error chart as a PNG (matplotlib) for the README.

The eval does not change settings. The owner picks the threshold and the `shadow` → `live` switch after reading the report.

## Gates for switching to `live`

1. Eval report: agreement ≥ 95% at the chosen threshold, on fixtures and on Supabase (if there are at least 30 sessions).
2. At least 30 `shadow`-mode decisions on real emails, with Basal vs. LLM disagreements reviewed by hand (`eval --source decisions`). The gate is a number of decisions rather than a time period (my call): the app runs as a manual simulation, so a week may bring a few sessions or none.

## Tests

- Basal client: mocked HTTP (success, 5xx error, timeout, response without the expected key).
- Cascade: parametrised cases for every branch of the diagram and every mode. In `shadow` the verdict always comes from the LLM, even at Basal confidence 0.99.
- Profiler: a Basal decision yields the right `confidence`, `reasoning` and `decision_source`; the fallback fix works only in `live`.
- Language detection: PL, EN, DE, mixed text, short lines.
- Eval: metric computation on a small, hand-computed set.
- Existing Profiler and graph tests pass unchanged with `BASAL_URL=""`.

## Mapping to the PRD

The numbering continues `.ai/prd.md` (latest: US-045/046).
- Stage 1 is:
  - US-047 (client);
  - US-048 (cascade + `decisions`);
  - US-049 (Profiler, attack type only);
  - US-053 (eval, Profiler only);
  - new user stories for the token counter.
- The original US-050/051/052/054 move to stages 2–3, reshaped by the review.
- Updating `.ai/prd.md` is part of the work.

## Left to the builder

- File layout in `phishguard/decisions/` and class names.
- How to write to Supabase (the same client as `session_service`).
- The HTTP mocking library for tests (whatever is already in `pyproject.toml`).
- The wording of the option descriptions for Basal (from the `AttackType` docstrings and the Profiler prompt).
- The look of the source label in the UI, in the style of the existing confidence badge.

## Results (2026-11-03)

| Gate | Data | Result |
|---|---|---|
| 1 (fixtures) | 98 synthetic PL/EN emails, labels from two Claude models | **passed**: threshold 0.70, coverage 93.9%, error 0%, cascade agreement 98% |
| 2 (shadow) | 29 real emails (Nazario corpus `phishing-2025`, CC BY 4.0) | **failed**: agreement with gpt-5.1 13/28; at threshold 0.70 error ~48%; Basal labelled 13/28 phishing emails `not_phishing` |

- Latency: ~8 s per request (M1 Pro, MLX, `max` model) vs. ~1.6 s for gpt-5.1.
- Decision: the Profiler stays on GPT. The synthetic set inflated the result, so gate 1 did not predict gate 2. Basal moves to decisions that today are made by regexes or by nobody (stage 2).
