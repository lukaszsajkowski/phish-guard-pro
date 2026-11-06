# Phase 0: Repository hygiene — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A clean PR tab, CI with required checks on `main`, repository metadata with a `v0.1.0` release, and LLM provider selection (openai/anthropic/ollama) with `gpt-6-luna` as the default.

**Architecture:** Four PRs to `main`:
- (A) a11y consolidation from the Jules PRs;
- (B) docs, `AGENTS.md` and CI/Dependabot/CodeQL, on branch `lukaszsajkowski/bream`;
- (C) LLM providers;
- (D) metadata and release.

Branch protection goes on after (B), so (C) and (D) already pass through the required checks. LLM providers are adapters behind the existing `LLMClient`. Retry and fallback stay in the client, and each adapter maps SDK errors to neutral exceptions.

**Tech Stack:** GitHub Actions, `gh` CLI, Python 3.13 + uv, `openai` SDK, `anthropic` SDK, Node 26 + Next.js 16, Vitest.

**Spec:** `docs/superpowers/specs/2026-11-05-phase0-repo-hygiene-design.md`

## Global Constraints

- README: factual fixes only (default models and variables, "LangChain-OpenAI" in the stack list). No new sections or badges.
- Commits follow `.claude/skills/commit/SKILL.md`: `<type>: <subject>`, no `Co-Authored-By`.
- Every change to `main` goes through a PR. After Task 5, branch protection applies to admins too (`enforce_admins: true`), with no required approval.
- Default provider `openai`, default model `gpt-6-luna` (after the ID check in Task 6).
- `conversation.py` and `profiler.py` do not change. The public interface `LLMClient.chat_completion(...) -> LLMResponse` stays.
- No LangChain or LiteLLM in the LLM layer. `langchain-openai` is removed from the dependencies.
- Dependabot: groups per ecosystem, `interval: monthly`, `open-pull-requests-limit: 3`.
- E2E (Playwright) is not a required CI check.
- Jules is switched off. `AGENTS.md` is the single source of rules for agents, and `.claude/CLAUDE.md` points to it.

## Review Focus

1. An existing `.env` with `OPENAI_PRIMARY_MODEL=gpt-4o` still works: the value is honoured as the primary model (test in Task 9).
2. `LLM_PROVIDER=anthropic` without `ANTHROPIC_API_KEY` raises `LLMConfigurationError` naming `ANTHROPIC_API_KEY`, not an OpenAI message (test in Task 9).
3. An unreachable Ollama (connection refused) goes through retry → fallback → `LLMRequestError`, with no unhandled SDK exception (test in Task 7).
4. Messages with role `system` sent to Anthropic (one or several, at the start of the list) go into the `system` parameter, not into `messages` (test in Task 8).
5. A model that rejected `temperature` gets its next request without `temperature` straight away, with no second 400 error (test in Task 7).

---

### Task 1: Switch Jules off (manual owner step)

- [ ] **Step 1:** Ask the owner to switch Jules off for `lukaszsajkowski/phish-guard-pro` in the Jules dashboard, including scheduled "Palette" tasks. Do not continue with Task 3 until they confirm.
- [ ] **Step 2: Check** after 24 h: `gh pr list --state open --json createdAt --jq '[.[].createdAt]|max'`. Expected: a date before the confirmation.

### Task 2: PR (A) — consolidate a11y fixes

**Files:**
- Modify: components in `frontend/src/components/` touched by the PR diffs (expected: `IntelDashboard.tsx`, `PhishingEmailCard`, `ChatMessage`, `ThemeToggle`, copy buttons)
- Test: the existing Vitest tests for those components in `frontend/src/**/__tests__` or next to the components

- [ ] **Step 1:** `git fetch origin && git switch -c chore/a11y-consolidation origin/main`.
- [ ] **Step 2: Inventory.**
  - Run `gh pr list --state open --limit 300 --json number,title,files,headRefName > <scratchpad>/prs.json` and group the PRs by changed files.
  - For each group, read the 1–2 newest diffs (`gh pr diff <n>`) and list the distinct changes:
    - `aria-live` or a changing `aria-label` on copy buttons;
    - `aria-expanded` + `aria-controls` on collapsible sections;
    - Radix tooltips on icon buttons;
    - `aria-label` on `ChatMessage` actions;
    - a `ThemeToggle` tooltip.
  - Skip changes already on `main`.
- [ ] **Step 3: Tests (failing).** For each change, add an assertion to the component test. Examples:
  - `expect(screen.getByRole('button', { name: /copy/i })).toHaveAttribute('aria-live', 'polite')`;
  - `expect(toggle).toHaveAttribute('aria-expanded', 'false')`, then `'true'` after a click.

  Run: `cd frontend && npx vitest run <files>`. Expected: FAIL on the new assertions.
- [ ] **Step 4:** Implement the changes in the components, using the existing `@radix-ui/react-tooltip` / `components/ui/tooltip`.
- [ ] **Step 5: Check.**
  - `npx vitest run && npx eslint . && npx tsc --noEmit`. Expected: all green (0 errors).
  - Then run E2E locally against a running stack (`/run-all`): `npm run test:e2e -- --project=chromium`. Expected: no new failures compared with `main`.
- [ ] **Step 6:** Commit `feat: consolidate accessibility fixes from automated PRs`, push, and `gh pr create` listing the source PR numbers. Merge after the owner's review.

### Task 3: Close the Jules PRs

**Interfaces:** Consumes: the PR (A) number from Task 2 and the confirmation from Task 1.

- [ ] **Step 1:** Build the list to close: open PRs whose `headRefName` is neither `chore/a11y-consolidation` nor `lukaszsajkowski/bream`, and that are not from `dependabot`. Show the owner the count and 5 sample titles. Close only after they say yes.
- [ ] **Step 2:** For each: `gh pr close <n> --delete-branch --comment "Closing automated accessibility PRs generated by Jules. The useful changes were consolidated in #<A>. Jules is disabled for this repository."`
- [ ] **Step 3: Check.** `gh pr list --state open --json number,headRefName`. Expected: only PR (A), if not merged yet, and PR (B).

### Task 4: PR (B) — `AGENTS.md`, CI, CodeQL, Dependabot

Branch: `lukaszsajkowski/bream` (already holds the spec and the plan). Run `git rebase origin/main` before starting.

**Files:**
- Create: `AGENTS.md`
- Modify: `.claude/CLAUDE.md` (process rules replaced by a pointer to `AGENTS.md`; the architecture description stays)
- Create: `.github/workflows/ci.yml`, `.github/workflows/codeql.yml`, `.github/dependabot.yml`

**Interfaces:** Produces: CI job names `backend`, `frontend` and `secrets`, used as required checks in Task 5. CodeQL reports as `Analyze (python)` and `Analyze (javascript-typescript)`.

- [ ] **Step 1: `AGENTS.md`.** Sections:
  - repository scope (1 paragraph);
  - working on a branch and through a PR to `main`;
  - the quality gate before a PR, using the commands from `CLAUDE.md`: `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `npx eslint .`, `npx vitest run`, `npx tsc --noEmit`;
  - no PR that duplicates an open one (check `gh pr list`);
  - the commit convention from Global Constraints;
  - no committing `.env` files or secrets;
  - the "no real personal data" rule.

  In `.claude/CLAUDE.md`, add at the top: "Process rules for coding agents live in `AGENTS.md`." and remove any duplicates of these rules.
- [ ] **Step 2: `ci.yml`.** Triggers: `pull_request` to `main` and `push` to `main`. `permissions: contents: read`. Actions are pinned to specific version tags. Jobs:
  - `backend` (ubuntu-latest, `working-directory: backend`): `astral-sh/setup-uv` with cache, Python 3.13, `uv sync --locked`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest -q`.
  - `frontend` (`working-directory: frontend`): `actions/setup-node` with Node 26 and npm cache, `npm ci`, `npx eslint .`, `npx vitest run`, `npx tsc --noEmit`, and `npm run build` with placeholder variables `NEXT_PUBLIC_SUPABASE_URL=http://localhost:54321`, `NEXT_PUBLIC_SUPABASE_ANON_KEY=ci-placeholder` and any other `NEXT_PUBLIC_*` the build needs.
  - `secrets`: `actions/checkout` with `fetch-depth: 0`, then `gitleaks/gitleaks-action@v2` (`GITHUB_TOKEN` in env).
- [ ] **Step 3: `codeql.yml`.** The CodeQL template for `python` and `javascript-typescript`, `build-mode: none`, the same triggers as CI plus a weekly `schedule`.
- [ ] **Step 4: `dependabot.yml`.** Ecosystems: `uv` (`/backend`), `npm` (`/frontend`), `github-actions` (`/`). Each one: `schedule.interval: monthly`, `open-pull-requests-limit: 3`, a single group `patterns: ["*"]`.
- [ ] **Step 5: Local build check.** `cd frontend && NEXT_PUBLIC_SUPABASE_URL=http://localhost:54321 NEXT_PUBLIC_SUPABASE_ANON_KEY=ci-placeholder npm run build`. Expected: the build succeeds. If it needs other variables, add them to the job.
- [ ] **Step 6:** Commits (`docs: add AGENTS.md with coding agent rules`, `chore: add CI, CodeQL and Dependabot`), push, `gh pr create`.
- [ ] **Step 7: Check.** `gh pr checks <B> --watch`. Expected: `backend`, `frontend`, `secrets` and both `Analyze` jobs pass.
  - With the full history, gitleaks may find old secrets. Report every hit to the owner; rotating a key is their decision.
  - Add false positives to a `.gitleaks.toml` allowlist with a comment.
- [ ] **Step 8:** Merge PR (B) once the owner approves.

### Task 5: Branch protection and secret scanning

**Interfaces:** Consumes: the check names from Task 4.

- [ ] **Step 1:** Turn on native secret scanning and push protection: `gh api -X PATCH repos/lukaszsajkowski/phish-guard-pro -F 'security_and_analysis[secret_scanning][status]=enabled' -F 'security_and_analysis[secret_scanning_push_protection][status]=enabled'`.
- [ ] **Step 2:** Run `gh api -X PUT repos/lukaszsajkowski/phish-guard-pro/branches/main/protection --input <scratchpad>/protection.json` with this JSON:
  - `required_status_checks: {strict: true, contexts: ["backend","frontend","secrets","Analyze (python)","Analyze (javascript-typescript)"]}`;
  - `enforce_admins: true`;
  - `required_pull_request_reviews: {required_approving_review_count: 0}`;
  - `restrictions: null`;
  - `allow_force_pushes: false`;
  - `allow_deletions: false`.
- [ ] **Step 3: Check.** `gh api repos/lukaszsajkowski/phish-guard-pro/branches/main/protection --jq '.enforce_admins.enabled, .required_status_checks.contexts'`. Expected: `true` and the five check names.

### Task 6: Verify the model identifier (gate for Tasks 7–10)

- [ ] **Step 1:** With the owner's key (from their `.env` in the main checkout; never copy it into the worktree or logs): `uv run python -c "import openai; print(sorted(m.id for m in openai.OpenAI().models.list() if m.id.startswith('gpt-')))"`.
- [ ] **Step 2:** If `gpt-6-luna` is on the list, continue. If not, STOP, show the owner the `gpt-6*` list and ask.
- [ ] **Step 3: OpenAI fallback model.** Use `gpt-6-luna-mini` if it is on the list. Otherwise use the cheapest `gpt-6*` model from the pricing page `https://openai.com/api/pricing`. Record the choice and the prices of both models (input/output per 1M tokens) for Task 10.

### Task 7: PR (C) — provider layer and OpenAI/Ollama adapter

Branch: `feat/llm-providers` from `origin/main`.

**Files:**
- Create: `backend/src/phishguard/llm/providers.py`
- Modify: `backend/src/phishguard/llm/client.py`
- Test: `backend/tests/unit/llm/test_providers.py`, `backend/tests/unit/llm/test_llm_client.py`

**Interfaces — Produces:**
- `Completion(NamedTuple)`: `content: str`, `prompt_tokens: int`, `completion_tokens: int` (replaces `_Completion`).
- Exceptions in `providers.py`: `ProviderError(Exception)`, with subclasses `ProviderAuthError`, `ProviderRateLimitError`, `ProviderConnectionError`, `ProviderServerError(status_code: int)` and `ProviderClientError(status_code: int)`.
- `class ChatProvider(Protocol)`:
  - `async def complete(self, messages: list[dict[str, str]], model: str, temperature: float, max_tokens: int | None) -> Completion`;
  - `async def close(self) -> None`.
- `class OpenAICompatibleProvider`: `__init__(self, api_key: str, timeout_seconds: float, base_url: str | None = None)`.
- `LLMClient.__init__(self, config: LLMClientConfig | None = None, api_key: str | None = None, provider: ChatProvider | None = None)`. Tests inject `provider`.

- [ ] **Step 1: Failing tests (`test_providers.py`):**
  - `test_openai_rate_limit_maps_to_provider_rate_limit`: SDK `create` raises `openai.RateLimitError`, so `complete` raises `ProviderRateLimitError`.
  - `test_openai_5xx_maps_to_server_error`: `APIStatusError` 503 becomes `ProviderServerError` with `status_code == 503`.
  - `test_openai_4xx_maps_to_client_error`: a 400 that does not mention temperature becomes `ProviderClientError(400)`.
  - `test_openai_connection_error_maps`: `openai.APIConnectionError` becomes `ProviderConnectionError` (Review Focus 3).
  - `test_openai_auth_error_maps`: `AuthenticationError` becomes `ProviderAuthError`.
  - `test_temperature_dropped_after_unsupported_error`:
    - the first `create` raises `BadRequestError` with `param="temperature"` / the message "Unsupported parameter: 'temperature'", and the second returns a response;
    - `complete` returns the content, and the second call's kwargs contain no `temperature`.
  - `test_temperature_omission_is_remembered_per_model`: after the above, the next `complete` for the same model calls `create` once, without `temperature`. For a different model, `temperature` is still sent (Review Focus 5).
  - `test_max_tokens_sent_as_max_completion_tokens`: `max_tokens=100` becomes the kwarg `max_completion_tokens=100`.
- [ ] **Step 2:** `cd backend && uv run pytest tests/unit/llm/test_providers.py -v`. Expected: FAIL (ImportError).
- [ ] **Step 3:** Implement `providers.py` as in Interfaces.
  - `OpenAICompatibleProvider` holds `AsyncOpenAI(api_key, timeout, base_url)` and a set `_no_temperature_models: set[str]`.
  - A temperature rejection is a `BadRequestError` with `param == "temperature"` or "temperature" in the message. On one, the provider adds the model to the set and retries once without `temperature`.
- [ ] **Step 4:** Rewrite `LLMClient`:
  - `_make_request` delegates to `self._provider.complete`.
  - `_attempt_with_retries` and `chat_completion` catch `Provider*` exceptions instead of `openai` types:
    - retry: connection, rate limit, server errors;
    - no retry and no fallback: client errors;
    - `ProviderAuthError` becomes `LLMConfigurationError`.
  - At this stage the client always builds `OpenAICompatibleProvider` (provider selection comes in Task 9).
  - Update `test_llm_client.py`: mock a `ChatProvider` (`AsyncMock`) passed through `provider=` and raise `Provider*` exceptions instead of `openai.*`. Keep the names and intent of the existing tests.
- [ ] **Step 5:** `uv run pytest tests/unit/llm -v && uv run pytest -q`. Expected: all PASS (baseline: 709 passed, 1 xfailed, plus the new tests).
- [ ] **Step 6:** Commit `refactor: put OpenAI behind a provider adapter in LLMClient`.

### Task 8: Anthropic adapter

**Files:**
- Modify: `backend/src/phishguard/llm/providers.py`, `backend/pyproject.toml` (+ `anthropic`), `backend/uv.lock`
- Test: `backend/tests/unit/llm/test_providers.py`

**Interfaces:**
- Consumes: `ChatProvider`, `Completion` and the `Provider*` exceptions from Task 7.
- Produces: `class AnthropicProvider` with `__init__(self, api_key: str, timeout_seconds: float)`, and the constant `ANTHROPIC_DEFAULT_MAX_TOKENS = 1024`.

- [ ] **Step 1: Failing tests:**
  - `test_anthropic_system_messages_go_to_system_param`: input `[system "A", system "B", user "hi"]` makes `messages.create` receive `system="A\n\nB"` and `messages=[{"role":"user","content":"hi"}]` (Review Focus 4).
  - `test_anthropic_default_max_tokens`: `max_tokens=None` sends `max_tokens=1024`.
  - `test_anthropic_joins_text_blocks_and_usage`: a response with two text blocks and `usage.input_tokens=10, output_tokens=5` gives `Completion("ab", 10, 5)`.
  - `test_anthropic_error_mapping` (parametrised):
    - `anthropic.RateLimitError` → `ProviderRateLimitError`;
    - `APIStatusError` 529 → `ProviderServerError`;
    - 400 → `ProviderClientError`;
    - `APIConnectionError` → `ProviderConnectionError`;
    - `AuthenticationError` → `ProviderAuthError`.
- [ ] **Step 2:** `uv add anthropic` (in `backend/`), then `uv run pytest tests/unit/llm/test_providers.py -k anthropic -v`. Expected: FAIL.
- [ ] **Step 3:** Implement `AnthropicProvider` on top of `anthropic.AsyncAnthropic`.
- [ ] **Step 4:** `uv run pytest tests/unit/llm -v`. Expected: PASS.
- [ ] **Step 5:** Commit `feat: add Anthropic provider for LLMClient`.

### Task 9: Provider selection in configuration

**Files:**
- Modify: `backend/src/phishguard/core/__init__.py:32-34`, `backend/src/phishguard/llm/client.py` (`LLMClientConfig`, `LLMClient.__init__`, `create_llm_client`), `backend/src/phishguard/llm/__init__.py`
- Test: `backend/tests/unit/llm/test_llm_client.py`, `backend/tests/unit/core/test_settings_llm.py` (new; if `tests/unit/core` does not exist, create it with an `__init__.py`)

**Interfaces — Produces:**
- `Settings`:
  - `llm_provider: Literal["openai","anthropic","ollama"] = "openai"`;
  - `llm_primary_model: str = Field(default="", validation_alias=AliasChoices("LLM_PRIMARY_MODEL","OPENAI_PRIMARY_MODEL"))`;
  - `llm_fallback_model`, the same way with `OPENAI_FALLBACK_MODEL`;
  - `anthropic_api_key: str = ""`;
  - `ollama_base_url: str = "http://localhost:11434/v1"`.

  The fields `openai_primary_model` and `openai_fallback_model` are removed.
- `PROVIDER_DEFAULT_MODELS: dict[str, tuple[str, str]]` in `client.py`:
  - `openai → ("gpt-6-luna", <fallback from Task 6>)`;
  - `anthropic → ("claude-sonnet-5-5", "claude-haiku-5-5")`;
  - `ollama → ("qwen3:8b", "qwen3:4b")`.
- `LLMClientConfig`: a new field `provider: Literal["openai","anthropic","ollama"] = "openai"`. The default `primary_model` / `fallback_model` are the values from `PROVIDER_DEFAULT_MODELS["openai"]`.
- `create_llm_client(primary_model=None, fallback_model=None, timeout_seconds=..., api_key=None)`, with an unchanged signature. It reads the provider from settings, and an empty model means the provider's default.
- `build_provider(provider: str, api_key: str | None, timeout_seconds: float) -> ChatProvider` in `providers.py`.

- [ ] **Step 1: Failing tests:**
  - `test_legacy_openai_primary_model_env_is_honored`: `monkeypatch.setenv("OPENAI_PRIMARY_MODEL","gpt-4o")` gives `Settings(_env_file=None).llm_primary_model == "gpt-4o"` (Review Focus 1).
  - `test_llm_primary_model_wins_over_legacy`: with both set, `LLM_PRIMARY_MODEL` wins.
  - `test_invalid_provider_rejected`: `LLM_PROVIDER=gemini` raises `ValidationError`.
  - `test_defaults_per_provider` (parametrised over the three providers): `create_llm_client()` with empty models takes `primary_model` / `fallback_model` from `PROVIDER_DEFAULT_MODELS`.
  - `test_anthropic_without_key_raises_named_error`: `llm_provider="anthropic"` with `anthropic_api_key=""` raises `LLMConfigurationError` whose message contains `ANTHROPIC_API_KEY` (Review Focus 2).
  - `test_ollama_needs_no_key_and_uses_base_url`: `llm_provider="ollama"` with no keys builds a client whose provider is an `OpenAICompatibleProvider` with `base_url == settings.ollama_base_url`.
  - Update `test_default_values` in `TestLLMClientConfig` to the new defaults.
- [ ] **Step 2:** `uv run pytest tests/unit/llm tests/unit/core -v`. Expected: FAIL.
- [ ] **Step 3:** Implement as in Interfaces.
  - Keys: `openai → openai_api_key` (`OPENAI_API_KEY`), `anthropic → anthropic_api_key` (`ANTHROPIC_API_KEY`), `ollama →` the constant `"ollama"`.
  - Update the `mock_settings` fixture in the tests (`llm_provider`, `llm_primary_model`, …).
- [ ] **Step 4:** `uv run pytest -q && uv run ruff check . && uv run ruff format --check .`. Expected: PASS and clean. `grep -rn "openai_primary_model\|openai_fallback_model" backend/src` finds nothing.
- [ ] **Step 5:** Commit `feat: select LLM provider and model from configuration`.

### Task 10: Prices, dependencies, factual docs; finish PR (C)

**Files:**
- Modify:
  - `backend/src/phishguard/decisions/eval/metrics.py:11-17`;
  - `backend/pyproject.toml` (− `langchain-openai`), `backend/uv.lock`;
  - `.env.example:25-29`;
  - `README.md:15` and `README.md:155-157`;
  - `.claude/CLAUDE.md` (the LangChain-OpenAI line).
- Test: `backend/tests/unit/decisions/test_eval_report.py` or the existing metrics test

- [ ] **Step 1: Failing test** `test_prices_cover_provider_defaults`: every model in `PROVIDER_DEFAULT_MODELS` (both tuple items, all providers) is a key of `PRICES_PER_MTOK`, and the `ollama` models are `(0.0, 0.0)`.
- [ ] **Step 2:** Fill in `PRICES_PER_MTOK`:
  - the OpenAI models from Task 6;
  - `claude-sonnet-5-5` and `claude-haiku-5-5` from the Anthropic price list (check with the `claude-api` skill or on the pricing page);
  - the ollama models at `(0.0, 0.0)`.

  Keep `gpt-4o` / `gpt-4o-mini` for old reports. Update the comment with the check date 2026-11-05 and the sources.
- [ ] **Step 3:** `uv remove langchain-openai`. `grep -rn "langchain" backend/src` finds nothing.
- [ ] **Step 4:** `.env.example`: a `# LLM` section with:
  - `LLM_PROVIDER=openai`;
  - `LLM_PRIMARY_MODEL=` (empty means the provider default) and `LLM_FALLBACK_MODEL=`;
  - `OPENAI_API_KEY=` and `ANTHROPIC_API_KEY=`;
  - `OLLAMA_BASE_URL=http://localhost:11434/v1`;
  - a comment that `OPENAI_PRIMARY_MODEL` / `OPENAI_FALLBACK_MODEL` are still read.
- [ ] **Step 5:** README:
  - line 15: `LangChain-OpenAI` becomes `OpenAI / Anthropic / Ollama`;
  - the table/section at 155–157 gets the new variables and the `gpt-6-luna` default.

  The same in `.claude/CLAUDE.md`. Nothing else in the README.
- [ ] **Step 6:** `uv run pytest -q && uv run ruff check . && uv run ruff format --check .`. Expected: PASS.
- [ ] **Step 7: Live smoke test** (with the owner's key, as in Task 6): `uv run python -c "import asyncio; from phishguard.llm import create_llm_client; print(asyncio.run(create_llm_client().chat_completion([{'role':'user','content':'Say OK'}], temperature=0.7, max_tokens=20)))"`. Expected: an `LLMResponse` with `model_used='gpt-6-luna'` and `used_fallback=False`.
- [ ] **Step 8:** Commits (`chore: update model prices and drop langchain-openai`, `docs: correct LLM configuration facts`), push, `gh pr create`, `gh pr checks --watch` until pass, then merge after the owner approves.

### Task 11: PR (D) — repository metadata and `v0.1.0` release

**Files:**
- Create: `LICENSE`, `SECURITY.md`, `CHANGELOG.md`

- [ ] **Step 1:** `gh repo edit lukaszsajkowski/phish-guard-pro --description "AI agents that keep phishing scammers talking, waste their time and extract IOCs (wallets, IBANs, phones, URLs)." --add-topic langgraph,agentic-ai,threat-intelligence,scambaiting,honeypot,phishing,fastapi,nextjs`. Check: `gh repo view --json description,repositoryTopics`.
- [ ] **Step 2:** Branch `chore/release-v0.1.0` from `origin/main`. `LICENSE`: the standard MIT text, `Copyright (c) 2026 Lukasz Sajkowski`.
- [ ] **Step 3:** `SECURITY.md`:
  - scope: the code in this repository;
  - reporting through GitHub Private Vulnerability Reporting (turn it on with `gh api -X PUT repos/lukaszsajkowski/phish-guard-pro/private-vulnerability-reporting`);
  - "best effort" response time;
  - the rule that the project never sends real personal data, and reports should not contain any.
- [ ] **Step 4:** `CHANGELOG.md` in Keep a Changelog format:
  - one section, `## [0.1.0] - <release date>`, with `Added` / `Changed` / `Security` groups;
  - built from `git log --oneline` and the user story headings in `.ai/prd.md`;
  - areas: profiler, persona, conversation, IOC and enrichment, safety, session history, Basal, phase 0;
  - 10–25 entries, not a commit list.
- [ ] **Step 5:** Commit `docs: add license, security policy and changelog`, open the PR, `gh pr checks --watch` until pass, merge.
- [ ] **Step 6:** After the merge: `gh release create v0.1.0 --target main --title "v0.1.0" --notes-file <the 0.1.0 section of CHANGELOG.md>`. Check: `gh repo view --json latestRelease,licenseInfo` shows `v0.1.0` and `MIT`.

### Task 12: Final phase 0 check

- [ ] **Step 1:** `gh pr list --state open` shows at most Dependabot PRs (≤ 3 per ecosystem).
- [ ] **Step 2:** `gh api repos/lukaszsajkowski/phish-guard-pro/actions/runs --jq '.workflow_runs[0:3][] | {name, conclusion, head_branch}'` shows the latest runs on `main` with `conclusion: success`.
- [ ] **Step 3:** Give the owner a summary: repository link, number of PRs closed, PR numbers A–D, the release.
