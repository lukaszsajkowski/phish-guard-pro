# Phase 0: Repository hygiene

Date: 2026-11-05. Phase 0 of the project roadmap.

## Why

The repository is public. A visitor first sees the front page: description, topics, licence, releases, and the number of open PRs. A reader who goes further looks at:
- green CI checks;
- secret scanning;
- the PR process;
- current, configurable models.

Today both pictures are poor:
- 138 open, near-identical PRs from an agent;
- no CI;
- no description and no licence;
- a default model from 2024.

## Starting point (checked 2026-11-05)

- **Open PRs.**
  - 138 open PRs, all from the owner's account (Jules acts on the owner's behalf).
  - 134 are titled "🎨 Palette…", and the other 4 are also about a11y and tooltips.
  - They date from 2026-04-15 to 2026-11-05, and Jules still opens new ones daily.
- **CI and process.** No `.github/` directory and no Actions workflows. Only 1 change was ever merged through a PR; work lands on `main` directly.
- **Repository metadata.**
  - The description is empty and there are no topics.
  - There is no `LICENSE` file, although the README declares MIT in its "License" section.
  - There are no releases and no `SECURITY.md`, `AGENTS.md` or `CHANGELOG.md`.
- **LLM.**
  - `backend/src/phishguard/llm/client.py` uses `openai.AsyncOpenAI` directly, not LangChain. The `langchain-openai` dependency in `pyproject.toml` is not imported anywhere in `src/`.
  - Default models are `gpt-4o` / `gpt-4o-mini`, set in `core/__init__.py:33-34`, `llm/client.py:51-52` and `.env.example` (`OPENAI_PRIMARY_MODEL`, `OPENAI_FALLBACK_MODEL`).
  - Prices exist only for gpt-4o, hard-coded in `decisions/eval/metrics.py:15-16`.
  - Callers: `agents/conversation.py` and `agents/profiler.py`.
- **E2E tests.** Playwright starts `npm run dev` and assumes a running backend with Supabase and an OpenAI key.

## Goals

1. The Pull requests tab is clean, and Jules no longer opens new PRs.
2. Every change to `main` goes through a PR with green checks.
3. The repository front page has a description, topics, a licence and a `v0.1.0` release.
4. The LLM provider and model are chosen in configuration, and the default model is current.

## Out of scope (owner decisions)

- **Public demo and Docker Compose** (roadmap item 0.5) are dropped.
- **No README overhaul** in this phase: no new sections, no badges, no section on working with agents.
  - **Factual fixes** that 0.4 makes outdated are allowed, and required:
    - default models and environment variables (README.md:155-157);
    - "LangChain-OpenAI" in the stack list (README.md:15).
  - The same applies to `.claude/CLAUDE.md`.
- Jules is not "kept in check"; it is switched off.

## Anti-goals

- Losing worthwhile a11y fixes while mass-closing PRs.
- CI that is red or needs secrets and therefore blocks every PR. Fewer checks that are reliably green are better.
- An LLM provider change that alters application behaviour under the default configuration beyond the model swap itself.

## Scope

### 0.1 Jules and PRs

- **Switching Jules off**: the owner does this by hand in the Jules dashboard; it cannot be done from the repository. The plan lists it as a manual step before closing PRs, so no new ones arrive.
- **Consolidation**:
  - Review the 138 PRs and pick out the distinct fixes: `aria-live` on copy buttons, `aria-expanded` on collapsible sections, Radix tooltips on icon buttons, `aria-label` in `ChatMessage`.
  - Check which of them are not on `main` yet.
  - Combine them into **one PR** on current `main`, with tests where component tests already exist.
- **Closing**: close the remaining PRs with one shared comment pointing to the consolidating PR, and delete their remote branches.
- **`AGENTS.md`** in the root, with rules for coding agents (Claude, Gemini):
  - work on a branch and through a PR;
  - run the quality gate before opening a PR;
  - never open a PR that duplicates an open one;
  - follow the commit convention.

  It does not mention Jules as an active agent.

### 0.2 CI and `main` protection

- A GitHub Actions workflow runs on PRs to `main` and on pushes to `main`:
  - backend: `uv sync`, `ruff check`, `ruff format --check`, `pytest` (tests that need no network or secrets);
  - frontend: `npm ci`, `eslint`, `vitest run`, type-check, `next build`.
- Security:
  - secret scanning: gitleaks, or native GitHub secret scanning with push protection;
  - CodeQL for Python and JavaScript/TypeScript;
  - Dependabot for pip/uv, npm and github-actions.
- **Branch protection on `main`:**
  - merge only through a PR;
  - the checks above are required to pass;
  - no required approval, since the owner works alone;
  - no force-pushes.

  **The rules apply to admins too** (`enforce_admins`, owner decision), so the changelog and the release also go through PRs.
- **Dependabot** (assistant decision): updates grouped per ecosystem, a monthly schedule, a low `open-pull-requests-limit`, plus security alerts and updates. The goal is not to recreate the PR flood.
- From this phase on, the owner works branch → PR → green checks → merge.

### 0.3 Repository metadata

- A one-sentence description and topics, including `langgraph`, `agentic-ai`, `threat-intelligence`, `scambaiting`, `honeypot`, `phishing`, `fastapi` and `nextjs`.
- `LICENSE` (MIT, Lukasz Sajkowski, 2026), as declared in the README.
- `SECURITY.md`: how to report vulnerabilities, the scope, and the "no real personal data" rule.
- `CHANGELOG.md` and a `v0.1.0` release with notes built from the history, grouped by user story or area rather than listing 144 commits.

### 0.4 LLM provider and model

- Configuration selects the provider: `openai` (default), `anthropic` or `ollama`.
- Default primary model: **`gpt-6-luna`** (owner decision). Before it is written in, the identifier must be confirmed against the OpenAI API model list, because it is newer than the assistant's knowledge.
- The public `LLMClient` interface stays: `chat_completion`, and `LLMResponse` with `used_fallback`, `model_used` and token counts. As a result, `conversation.py` and `profiler.py` do not change. Retry with backoff and fallback to a cheaper model work for every provider.
- Prices in `decisions/eval/metrics.py` move to a single per-model table covering the new default models (Ollama costs 0).
- `.env.example` and `core/__init__.py` describe the new variables. The old `OPENAI_PRIMARY_MODEL` / `OPENAI_FALLBACK_MODEL` either keep working or are clearly replaced. That choice is the implementer's, as long as a local `.env` does not silently stop working.

## Order

1. Switch Jules off (by hand), then 0.1: consolidation, closing PRs, `AGENTS.md`.
2. 0.2 CI, then turn on branch protection. From then on everything goes through PRs.
3. 0.4 as the first real PR through the new CI.
4. 0.3 last: the `v0.1.0` release covers everything above.

## Assistant decisions (for the owner to review)

- **Provider abstraction.** Earlier in the conversation I proposed LangChain's `init_chat_model`. The code turned out not to use LangChain for the LLM at all, only the OpenAI SDK. Instead, the plan uses adapters behind the existing `LLMClient`:
  - the OpenAI SDK for `openai`;
  - the same SDK for `ollama` (an OpenAI-compatible endpoint via `base_url`);
  - the native `anthropic` SDK for Anthropic.

  Neither LangChain nor LiteLLM is added.
- **The OpenAI fallback model** is chosen by the assistant from the API model list: a cheaper variant from the same family as the default. The assistant also chooses the default models for `anthropic` and `ollama`.
- **Model parameters.** If `gpt-6-luna` (or another model) rejects `temperature`, or needs `max_completion_tokens` instead of `max_tokens`, `LLMClient` adapts based on the model, and callers do not change. Dropping `temperature` for a model that does not support it is an accepted part of the model swap.
- **Model identifier check**: done locally with the owner's key from `backend/.env` at the start of 0.4. If `gpt-6-luna` is not on the list, work on 0.4 stops and goes back to the owner.
- **`AGENTS.md` as the single source of rules.** `.claude/CLAUDE.md` points to it instead of repeating the rules. The commit convention matches the existing `.claude/skills/commit` skill.
- **The consolidating a11y PR** may include visible tooltips, not only aria attributes. E2E tests run locally before merging.
- **E2E (Playwright) is not a required check** in this phase, because it needs the backend, Supabase and an OpenAI key. It can be added as a manual workflow (`workflow_dispatch`) or skipped.
- The unused `langchain-openai` dependency is removed as part of 0.4.

## Left to the implementer

- Gitleaks vs native secret scanning, action versions, CI caching, version matrix.
- How exactly to mark backend tests that need the network, if there are any.
- The wording of the PR-closing comment, the repository description, the exact topic list, and the contents of `SECURITY.md` and `AGENTS.md`.
