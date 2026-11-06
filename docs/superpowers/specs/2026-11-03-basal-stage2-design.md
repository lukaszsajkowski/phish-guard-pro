# Basal Decision Layer — Stage 2: semantic signals alongside regexes

Date: 2026-11-03. Continues `2026-11-02-basal-decision-layer-stage1-design.md`.

## Why

Stage 1 tested the one place where Basal could **replace** GPT: the attack type in the Profiler. Result:

| Gate | Data | Result |
|---|---|---|
| 1 (fixtures) | 98 synthetic PL/EN emails, labels from two Claude models | **passed**: threshold 0.70, coverage 93.9%, error 0%, cascade agreement 98% |
| 2 (shadow) | 29 real emails (Nazario corpus `phishing-2025`, CC BY 4.0) | **failed**: agreement with gpt-5.1 13/28, at threshold 0.70 error ~48%; Basal labelled 13/28 phishing emails `not_phishing`, some with confidence 0.92–0.98 |

Takeaway: Basal recognises well **a semantic feature of text that does not pretend to be innocent** (an open scam). It is bad at telling **phishing dressed up as a routine notification** apart from genuine mail. The synthetic set inflated the result: gate 1 did not predict gate 2.

Stage 2 moves Basal to where those conditions work in its favour. These are decisions that today are made by **English regexes** or by **nobody**, on the attacker's text or on our own. Here Basal does not compete with a better model, only with a phrase list that knows no Polish and no paraphrases.

## Owner decisions

- Basal latency (~4–9 s on an M1 Pro, MLX, `max` model) is **out of scope** for this stage (2026-11-03). The project does not optimise response time and does not hide it in the UI.
- The Profiler stays on GPT. The `profiler.attack_type` node does not move to `live`.

## Goals

1. The decision layer supports a **signal mode**: Basal alongside a deterministic reference (regex) instead of a Basal → LLM cascade.
2. **Per-node mode** (`off`/`shadow`/`live`), because the Profiler stays in `shadow`/`off` while the new nodes move to `live` independently.
3. Three nodes:
   - `response.in_role`: whether a generated reply breaks the persona's character (a new check that does not exist today).
   - `scammer.unmasking`: whether the attacker realised they are talking to a bot (today: 17 English phrases, US-016).
   - `scammer.urgency`: the pressure level in the attacker's message (today: ~20 weighted English regexes, a risk score component, US-032).
4. An eval CLI for each node, and gates for switching to `live` based on **real text**, not only synthetic text.

## Non-goals (stage 2)

- Basal latency and performance (owner decision).
- Profiler: no logic changes; it stays on GPT.
- IOC context ("is this the address the attacker wants money sent to") and the attacker message phase: stage 3, described below only as a direction.
- Personalisation (`analyzers/personalization.py`): stays deterministic; the gain from Basal is too small.
- The PII validator (`safety/output_validator.py`): stays deterministic; Basal does not touch it.
- New attack categories (`credential_phishing`): a separate product decision, see "Outside the plan".

## Anti-goals (failure even if it "works")

- Basal **blocks, rewrites or sends** a reply on its own. The in-role check only warns the human who approves the message.
- Basal **ends a session** on its own. Unmasking still only proposes ending it (US-016).
- Basal **weakens** an existing check. For unmasking the regex keeps working, and Basal can only add detections.
- Switching to `live` based on the synthetic set alone. The lesson from stage 1: gate 1 passed, gate 2 failed.
- A `decisions` row from which you cannot tell what the reference was (regex or LLM) and which message it concerned.

## How it works

### Signal mode

The stage 1 cascade assumes that when Basal is unsure, the LLM decides. In stage 2 the reference is the regex, and Basal **adds** its answer:

| Mode | `response.in_role` | `scammer.unmasking` | `scammer.urgency` |
|---|---|---|---|
| `off` | no check (as today) | regex only (as today) | regex only (as today) |
| `shadow` | Basal computes and records; the UI shows nothing | regex decides; Basal recorded alongside | regex decides; Basal recorded alongside |
| `live` | warning on the draft when `breaks_role` ≥ threshold | detected = regex **or** Basal `unmasked` ≥ threshold | level from Basal ≥ threshold, otherwise regex |

When Basal is unavailable, times out, or the language gate rejects the text (`language.py`, PL/EN), the node falls back to its `off` behaviour and records a `skip_reason`, as in stage 1.

### Nodes and questions

**`response.in_role`** (options):
- `in_role`: the reply sounds like the persona and does not reveal that it is a bot or that the conversation is a trap.
- `breaks_role`: it admits to being an AI, refuses, moralises, mentions a scam, the police or CERT, switches to an assistant tone, or speaks out of character (age, style, knowledge).

State for Basal: the persona description (type, style) and the reply text.
- It runs after PII validation, on every generated reply.
- It also runs after a user edit (US-008), if the edit goes through the backend.

**`scammer.unmasking`** (options):
- `unmasked`: accuses the victim of being a bot, says they know what is going on, or quits in irritation;
- `engaged`: carries on with the scam.

It runs where `detect_unmasking` runs today (`api/routers/response.py:333`).

**`scammer.urgency`** (options): `none` / `low` / `medium` / `high`, with descriptions of time pressure, threats and final deadlines.
- Mapping to the 0–10 risk score scale is the expected value of Basal's distribution (e.g. 0 / 3.3 / 6.7 / 10), not a sum of weights.
- **It is computed once, when the attacker message is saved**, and stored.
- `risk_score_service` reads the stored labels and uses the regex only for messages without a label.
- Today the risk score is computed on demand from all messages, so calling Basal on every read is not an option.

### UI

- `response.in_role` in `live`: a warning on the reply draft with a short reason (the chosen option's description and `p`). The send / copy button keeps working.
- `scammer.unmasking`: the existing "end session" proposal shows the detection source (the regex phrase or "Basal, p=…").
- `scammer.urgency`: in the risk score breakdown, a level label instead of a word list when the source is Basal.

## Data

### `decisions` (migration)

The stage 1 table stays. Additions:
- `message_id` (nullable, FK to `messages`): which message the decision is about. The Profiler leaves it `null`.
- The reference kind: `llm` (Profiler) or `regex` (new nodes), with the reference's answer.
  - The stage 1 `llm_*` columns stay for the Profiler.
  - How to store the regex reference (new columns vs. generalising the existing ones) is left to the builder, as long as a row is unambiguous without reading the code.
- `source` allows the value `regex`, and `node` allows the new node names.

### Urgency label on a message

The `scammer.urgency` result (level, distribution, source) is stored so the risk score can read it without calling Basal again. Where it lives (a column on `messages` or a lookup in `decisions` by `message_id`) is left to the builder.

## Configuration

- `BASAL_MODE_<NODE>` overrides the global `BASAL_MODE`, just as `BASAL_THRESHOLD_<NODE>` overrides the threshold. This also covers the Profiler (`BASAL_MODE_PROFILER`).
- Thresholds are per node from the start and are set after the eval.
- Changes only through `.env` and a restart (as in stage 1).

## Eval data (the biggest risk of this stage)

| Node | Real text | Source |
|---|---|---|
| `response.in_role` | replies from our Conversation Agent | **Under our control.** Generated by the app for every persona and attack type; this is the node's real distribution. `breaks_role` cases are rare in practice, so synthetic cases are added, marked as synthetic and reported separately. |
| `scammer.unmasking`, `scammer.urgency` | attacker replies (second and later messages) | **Unknown.** The Nazario corpus has only first emails, and the local database has 3 sessions. Candidates to check: public scambaiting archives (e.g. 419eater), academic datasets, sessions collected in the app. Check each source's licence. |

Labels: the same blind process as in stage 1 (two independent Claude subagents, a third on disagreement, `ambiguous` outside the gate). The report states the limitation: labels are model agreement, not an expert's judgement.

**Exit criterion for the data search:** at least 150 real attacker messages under a licence that allows use, some of them in Polish. If that fails, unmasking and urgency stay in `shadow` until the app collects its own sessions, and the report says so plainly.

## Eval (CLI)

The stage 1 `eval` gets subcommands for the new nodes (`in_role`, `unmasking`, `urgency`) and the `fixtures` / `decisions` sources. Report per node:

- `in_role` and `unmasking`, separately for PL and EN:
  - Basal's precision / recall for the rare class (`breaks_role`, `unmasked`) as a function of the threshold;
  - the number of detections the regex misses (unmasking);
  - the number of false alarms.
- `urgency`, separately for PL and EN:
  - agreement with the label on the ordinal scale (MAE in levels, confusion matrix);
  - comparison with the regex.
- The confidence distribution and Basal's p50/p95 latency (for information).

## Gates for switching to `live` (per node)

The numbers are a starting point, as in stage 1.

1. **Eval on real text** (synthetic text only supplements it):
   - `in_role`: `breaks_role` recall ≥ 90% with false alarms ≤ 10%.
   - `unmasking`: Basal precision ≥ 90% at the threshold. Regex OR Basal detects more than the regex alone, and the difference shows on Polish messages.
   - `urgency`: MAE ≤ 0.5 levels against the labels, and no worse than the regex on English.
2. **Shadow:** at least 30 decisions by the node on real sessions. Disagreements with the regex (or, for `in_role`, every `breaks_role`) are reviewed by hand (`eval <node> --source decisions`).

## Order

| Phase | Scope | Depends on |
|---|---|---|
| 0 | Stage 1 results added to the stage 1 spec; `BASAL_MODE_PROFILER` | — |
| A | Signal mode, per-node mode, `decisions` migration, eval skeleton for the new nodes | 0 |
| R | Search for attacker data (in parallel from the start) | — |
| B | `response.in_role` end to end: node, UI, dataset, eval, shadow | A |
| C | `scammer.unmasking` + `scammer.urgency`: shared dataset, nodes, storing the urgency label, UI, eval, shadow | A, R |

`in_role` goes first because its data is under our control. Unmasking and urgency wait for the data search and share one dataset.

## Tests

- Signal mode: every node in every mode, including the fallback to the regex on `unavailable`, `timeout` and `language`. Unmasking in `live`: if the regex detected it and Basal did not, the detection stands.
- Per-node mode: overriding the global mode; the Profiler in `off` while the new nodes are in `live`.
- Urgency: the label is computed once on save, the risk score uses it and does not call Basal; a message without a label is scored by the regex.
- Eval: metrics on a small hand-computed set for each node.
- Existing tests pass unchanged with `BASAL_URL=""`.

## Mapping to the PRD

- The original US-050 (safety check) returns as `response.in_role`.
- New user stories from US-056: signal mode and per-node mode, unmasking via Basal, urgency via Basal.
- US-051 (IOC scoring) stays in stage 3.
- Updating `.ai/prd.md` is part of the work.

## Stage 3 (direction, not scope)

- `ioc.context`: whether an extracted IOC is where the attacker wants the money sent, or a mention, a quote, or a legitimate company's address. It feeds IOC quality (US-040). It needs attacker messages with IOCs, so it relies on the data search (R).
- `scammer.phase`: the message phase (building trust / asking for data / asking for payment / payment details / threat / goodbye). Build it only when there is a consumer, e.g. a session timeline.

## Outside the plan (found at gate 2, separate tasks)

- **500 error:** when the Conversation Agent fails PII validation three times (email #116 from the corpus, an `ssn` violation), the whole `/api/v1/classification/analyze` returns 500 and leaves an empty session, even though classification succeeded.
- **Probably a false `ssn`** in the same case: to be checked in the validator regex.
- **Taxonomy gap:** about half of real phishing is credential harvesting; gpt-5.1 spreads it between `tech_support` and `fake_invoice`. A candidate for a `credential_phishing` category.

## Left to the builder

- Code layout for signal mode (extending `DecisionService` or a separate class) and names.
- The storage schema for the regex reference and the urgency label (within the conditions above).
- The wording of the option descriptions for Basal (from the detector docstrings and the Conversation Agent prompt).
- The state format for `in_role` (how to give Basal the persona).
- The look of UI warnings, within the existing components.

## Stage 2 results — first in-role eval (2026-11-03)

- Dataset: 124 cases (64 real agent replies, 60 synthetic), fixtures.
- The gate (`breaks_role` recall ≥ 90% with false alarms ≤ 10%) **failed**:
  - recall was 52.1% at threshold 0.50, 37.5% at 0.70 and 27.1% at 0.90;
  - false alarms were 0% at every threshold.
- By behaviour at 0.50:
  - admits to being an AI 7/8;
  - breaks age/style 7/8;
  - moralises 5/8;
  - mentions a scam/police 4/8;
  - refuses 2/8;
  - assistant tone 0/8.
- Basal p50 latency 3.5 s.
- `response.in_role` stays in `shadow` until the gate is passed.
