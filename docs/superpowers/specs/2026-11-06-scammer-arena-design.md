# Phase 1.1: Scammer Arena

Date: 2026-11-06. Item 1.1 of the project roadmap, together with the part of 1.2 that comes out of the same run.

## Why

PhishGuard has no measurement today that shows whether active defense works:
- whether the persona gets payment details out of the scammer, and how quickly;
- how often the scammer recognises the bot;
- what a conversation costs.

Without that, every prompt or graph change is guesswork.

Scammer Arena is an experimental harness. It runs automated conversations between PhishGuard and a scammer played by an LLM, and measures the outcome. The output is an `EVALS.md` file in the repository root.

**Target picture (owner decision).** `EVALS.md` opens with:

1. **One table, "PhishGuard vs plain LLM without the graph"**, on the same scenarios. Columns:
   - share of secrets extracted;
   - mean number of turns to the first secret;
   - how often the scammer detected the bot;
   - cost of one conversation.
2. Below the table, **a short excerpt of a real conversation** in which the persona gets an IBAN (or another secret) out of the scammer.
3. Right below that, **honest caveats**, including that a simulation is not production.

The table and the excerpt must make sense without reading code. The rest of the file and the raw data let a reader trace every number back to specific conversations.

## Starting point (checked 2026-11-06)

- Two LangGraph graphs in `backend/src/phishguard/orchestrator/graph.py`:
  - `create_phishguard_graph()`: `classify_email → extract_intel_from_email → select_persona`;
  - `create_continuation_graph()`: `add_scammer_message → extract_intel → generate_response → validate_safety → (up to 3 regenerations) → add_bot_response`.
- The API (`api/routers/response.py`) calls the continuation graph with a Postgres checkpointer. Each call produces one bot reply. The first reply to the email goes the same way, with an empty history.
- The router detects unmasking (US-016) with `phishguard.safety.detect_unmasking(message)` on the scammer message. This function is not a graph node.
- `select_persona` builds `PersonaEngine()` without a seed (`orchestrator/nodes.py:82`). `PersonaEngine(seed=...)` already accepts one.
- There is a profiler eval CLI (`python -m phishguard.decisions.eval`) whose pattern to follow is:
  - a failing case is recorded and the run continues;
  - nothing is written to Supabase (`session_id=None`).
- Costs come from `decisions/eval/metrics.py` (`llm_cost_usd`, `PRICES_PER_MTOK`). `gpt-6-luna` (victim) costs $0.10 input / $0.50 output per 1M tokens; `gpt-5.4-mini` (scammer) costs $0.75 input / $4.50 output per 1M tokens (owner-provided prices, 2026-11-06).
- Dependencies in `pyproject.toml`:
  - `faker`, `phonenumbers` and `matplotlib` are already direct dependencies;
  - `pyyaml` is in the lockfile only as a transitive dependency.

## Goals

1. One command runs 24 scenarios × 2 systems × 3 repetitions (144 conversations) and writes all results to disk.
2. A second command generates `EVALS.md` and a chart from the saved results, with no further API calls.
3. Every number in `EVALS.md` can be traced to specific conversation files in the repository.
4. The Arena exercises **real production code**: the same graphs, prompts, IOC extraction and safety layer the application uses.

## Owner decisions

- **What is tested.** The Arena runs both production graphs directly in Python, without the API, the frontend or Supabase, with in-memory state.
  - Human approval is replaced by an automatic pass: each reply goes through unedited.
  - When the safety layer rejects a draft reply, that counts as a safety event. The conversation continues with the reply the graph finally released.
- **Baseline.** Same victim model and same persona, but one plain LLM call per turn with a simple victim prompt. No graph, no IOC extraction steering the conversation, no safety layer. The difference in results measures the value of the graph, not a difference between models.
- **Scenarios.** 24 in total:
  - **16 in English:** each of the 8 types PhishGuard recognises (`AttackType` without `not_phishing`: 419, CEO fraud, fake invoice, romance, tech support, lottery, crypto investment, credential phishing), each in two variants, an easier and a harder scammer;
  - **8 in Polish:** OLX/Allegro "parcel surcharge", BLIK, fake bank transfer and crypto investment, two variants each.
  - Each scenario is a YAML file with:
    - the first email;
    - a description of the scammer character;
    - 2–3 secrets with reveal conditions;
    - a limit of **10 turns**.
  - All data is fictional but formally valid.
- **Model.** Owner decision (2026-11-06): the victim (PhishGuard and baseline) runs on `gpt-6-luna` and the scammer on `gpt-5.4-mini`. Reason: in live probes the gpt-6 family refused to play a convincing scammer ("please keep your savings safe"). `EVALS.md` names both models and states that a scammer played by an LLM is still not a real criminal.
- **Repetitions.** Each scenario runs 3 times per system. The table shows the mean and the min–max range.
  - Each scenario has a fixed persona seed, so both systems play the same victim.
  - Every conversation is saved as JSON.
  - The excerpt in `EVALS.md` comes from a real run.
- **In scope for 1.1:**
  - the Arena itself;
  - the 24 scenarios;
  - the baseline run;
  - saved conversations;
  - `EVALS.md` with the table and the excerpt;
  - the metrics that come out of the run itself (see "Metrics").
- **Out of scope for 1.1:**
  - persona consistency scored by an LLM-as-judge (1.2; needs manual calibration);
  - running in CI (1.3);
  - comparing regex with LLM extraction (1.6).

  The Arena must be built so these can be added later without rework.
- **Commands and files:**
  - `uv run python -m phishguard.arena run` writes results to `evals/results/<date>/`: one JSON file per conversation plus a summary file;
  - `uv run python -m phishguard.arena report` writes `EVALS.md` in the repository root and one PNG bar chart, "PhishGuard vs baseline";
  - the results, all 144 conversations, the chart and `EVALS.md` are committed.

## How one conversation runs

A conversation is one (scenario, system, repetition) triple.

1. **Setup, once per scenario, shared by both systems and all repetitions** (see "Classification once per scenario" below).
   - Run `create_phishguard_graph()` on the scenario email, with `session_id=None` and no database writes. This produces the classification, the IOCs from the email and the persona.
   - The persona is created from a seed derived deterministically from the scenario id.
   - The classification and persona are stored in the results. The baseline gets the same persona.
2. **The victim's first reply** to the email, with an empty history, as in the API.
   - PhishGuard: `create_continuation_graph()` with no scammer message.
   - Baseline: one LLM call.
3. **A turn:**
   - the scammer (LLM) receives its description, the secrets with their conditions, and the conversation so far, and returns a message;
   - `detect_unmasking` runs on the scammer message, for both systems, since it is plain text analysis;
   - the victim replies: PhishGuard through the continuation graph, the baseline with one call.
4. **End of conversation:** after 10 turns, or earlier when the scammer ends it, for example because it concluded it was talking to a bot or lost interest. Extracting every secret does **not** end the conversation, because engagement length (tarpitting) is also a result.

A turn is the pair "scammer message + victim reply". The first reply to the email is turn 0.

## The scammer

The scammer is played by an LLM. On every turn it returns a structured output with these fields:

- `message`: the text sent to the victim;
- `revealed_secret_ids`: which secrets it just revealed, by its own account;
- `suspects_bot`: whether it suspects it is talking to a bot or an AI;
- `ends_conversation`: whether it ends the conversation.

The scammer prompt tells it:

- who it is;
- what it wants;
- that it reveals secrets **only** when the condition is met;
- to react realistically: lose interest, push harder, and suspect a bot when the victim behaves unnaturally.

The harder variant of a scenario has stricter reveal conditions and a more suspicious scammer.

## Scenario format

`evals/scenarios/<id>.yaml`. Fields:

- `id`, `language` (`en`/`pl`), `attack_type` (an `AttackType` value), `difficulty` (`easy`/`hard`);
- `email`: the scammer's first email;
- `scammer`: the character, style and goal;
- `secrets`: a list of entries with `id`, `type` (`iban`/`btc`/`url`/`phone`, matching the application's IOC types), `value` and `reveal_when` (a plain-language condition for the scammer LLM);
- `known_iocs`: other indicators that legitimately appear in the scenario, such as a link in the email itself. PhishGuard extracting these is not a false positive;
- `max_turns`: 10 by default.

The data must be fictional and formally valid:

- IBANs with a correct checksum;
- BTC addresses that pass the application's format validation;
- phone numbers that pass `phonenumbers`;
- URL domains that belong to no real party.

Loading a scenario validates all of this and rejects an invalid file with an error.

## Metrics

Both systems, unless noted otherwise.

| Metric | Definition |
|---|---|
| **Share of secrets extracted** (IDR equivalent) | Secrets revealed in the conversation / all secrets in the scenario. A reveal is detected by the secret value appearing in a scammer message (after normalising whitespace and case), not by the scammer's own claim. The claim is stored alongside as a secondary signal. |
| **Turns to first secret** (IDS) | The turn number of the first revealed secret. Conversations with no reveal are excluded from the mean, and their count is reported separately. |
| **Bot detection** | Share of conversations in which the scammer set `suspects_bot` at least once. Secondary: share of conversations in which `detect_unmasking` flagged unmasking. |
| **Engagement length** | Number of turns until the conversation ended. |
| **Cost and latency per conversation** | Full tokens and cost on the **victim side** (`llm_cost_usd`), plus call latency. For PhishGuard this includes the setup calls (email classification and persona selection), each scenario's setup cost split evenly across its PhishGuard conversations. The detailed results break cost down into setup and turns. Scammer cost is tracked separately and is not part of the comparison. |
| **IOC extraction** (PhishGuard only) | Recall: revealed secrets found in `extracted_iocs` / revealed secrets. Precision: extracted IOCs matching a secret or a `known_iocs` entry / all extracted IOCs. |
| **Safety** (PhishGuard only) | Number of turns in which a draft was rejected. Number of replies that still went out unsafe (expected 0). |

Aggregation: each metric is computed per repetition as a mean over the 24 scenarios. The table shows the mean of the 3 repetitions and the min–max range. A PhishGuard vs baseline difference is described as "within noise" when the min–max ranges overlap. It is a simple, honest rule that does not pretend to do statistics on n=3.

## `EVALS.md`

Generated entirely from the results. Contents, in order:

1. The headline table: the 4 columns from the target picture, PhishGuard vs baseline, mean and min–max.
2. A PNG bar chart of the same metrics.
3. An excerpt of a PhishGuard conversation with a secret being revealed: a few messages around the reveal, with a link to the full JSON.
4. Caveats:
   - a simulation is not production;
   - the victim is `gpt-6-luna` and the scammer `gpt-5.4-mini`; an LLM scammer is still not a real criminal;
   - n = 24 scenarios × 3 repetitions;
   - all data is fictional;
   - comparison with published results (Siadati et al., Puppeteer) is only indicative.
5. Method: how the Arena works, what the baseline is, metric definitions, run date and commit, victim and scammer models.
6. Detailed results:
   - per-scenario table;
   - EN/PL split;
   - IOC extraction and safety for PhishGuard;
   - PhishGuard cost split into setup and turns;
   - number of invalid or failed conversations;
   - profiler agreement with the scenario attack types.
7. How to reproduce: the two commands and the required key.

## Constraints

- Arena unit tests do not call the API. The LLM is replaced with a fake, and CI has no key. The Arena does not change the required CI checks.
- The Arena does not write to Supabase and does not need a running database.
- Production code changes are limited to what the Arena needs (for example, passing a persona seed) and must not change application behaviour.
- No secrets and no real personal data in scenarios, results or tests (AGENTS.md).
- A full run should cost about $1. The `run` command has flags to narrow a run (single scenario, number of repetitions, PhishGuard only or baseline only) so a change can be checked cheaply.

## Calls made by the spec author (for the owner to review)

- **The baseline knows the goal.** The baseline prompt tells the victim more than "play this person": one paragraph also tells it to keep the conversation going and get the scammer to share payment details. Without that, the comparison would be rigged in PhishGuard's favour and the result would not hold up.
- **Reveals are detected by value in the text, not by the scammer's claim.** The scammer LLM can be wrong about what it said; the value in the message is a hard fact.
- **Scammer model.** The scammer runs on `gpt-5.4-mini`, the victim on `gpt-6-luna`, because the gpt-6 models refused to play the scammer in live probes (owner decision, 2026-11-06). If the scammer still refuses, the refusal handling below applies.
- **Model refusals.** When the model refuses to play the scammer or the victim, the call is retried once. If it refuses again, the conversation is marked invalid with the reason and excluded from the metrics, and the count is reported in `EVALS.md`. If more than 10% are invalid, the report says so at the very top.
- **API errors.** The error is recorded in the conversation and the run continues, as in the existing eval CLI.
- **Excerpt selection.** The report picks the PhishGuard conversation with the earliest IBAN reveal (or any secret if there is none). A `report` flag lets the author choose a different conversation.
- **Classification once per scenario, live.** The profiler (real code) classifies the email once per scenario. The same classification and persona serve all 3 repetitions and both systems, so the repetitions measure the same thing.
  - The profiler's attack type is compared with the scenario's `attack_type`. Agreement is reported in the detailed results.
  - If the profiler returns `not_phishing`, the scenario is marked invalid with that reason. The profiler's answer is not overridden, because it is also a result.
- **Basal layer off.** The Arena forces mode `off` regardless of `BASAL_MODE`, so only the LLM answers. This keeps runs reproducible and needs no local Basal service.
- **Safety events are counted at the source.** The real validate-and-regenerate loop lives in `ConversationAgent.generate_response`, not in the `validate_safety` node. The Arena therefore counts regenerations inside the agent. This needs a small production change: exposing the regeneration count in graph state, with no behaviour change.
  - If the agent runs out of attempts and raises `ResponseGenerationError`, the turn ends the conversation as "blocked by safety". It is counted separately, not as an API error.
- **The Arena collects token usage itself.** `record_llm_usage` stores tokens only when there is a `session_id`, and the Arena runs without one. The Arena collects usage on its own, for example by wrapping the LLM client, with no database writes.
- **`pyyaml`** becomes a direct dependency, since today it is only transitive.
- **Arena code** lives in `backend/src/phishguard/arena/`. Scenarios and results live in `evals/` in the repository root, next to `EVALS.md`.

## Left to the builder

- The wording of the scammer and baseline prompts, within the calls above.
- The exact JSON shape of a conversation and of the summary. A conversation must contain:
  - every message;
  - PhishGuard state after each turn (IOCs, safety events, thinking);
  - the scammer's claims;
  - tokens and timings;
  - the scenario version;
  - the code commit.
- How the persona seed reaches `select_persona` while keeping the current API behaviour.
- The content of the 24 scenarios, within the split and the format.
- The chart's look: it must be readable in both GitHub light and dark themes.
- Order and concurrency of calls during a run.

## Acceptance criteria

1. `evals/scenarios/` contains 24 scenarios in the agreed split. All pass format and fictional-data validation.
2. `phishguard.arena run` completes a full run and writes 144 conversations (fewer with flags) plus a summary.
3. `phishguard.arena report` generates `EVALS.md` and the chart from the result files alone. Two runs on the same results produce identical files.
4. Unit tests with a fake LLM cover:
   - the conversation loop, including ending by the turn limit and by the scammer;
   - secret reveal detection;
   - metric computation on hand-built conversations;
   - refusal and error handling;
   - scenario validation;
   - report generation from fictional results.
5. The first real run is committed together with `EVALS.md`, the chart and the conversations.
6. The caveats and metric definitions in `EVALS.md` match this spec.
