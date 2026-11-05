# Faza 0: porządki w repozytorium — plan wykonania

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Czysta zakładka PR-ów, CI z wymaganymi checkami na `main`, metadane repo z release'em `v0.1.0` oraz wybór dostawcy LLM (openai/anthropic/ollama) z domyślnym `gpt-6-luna`.

**Architecture:** Cztery PR-y do `main`: (A) konsolidacja a11y z PR-ów Jules, (B) dokumenty + `AGENTS.md` + CI/Dependabot/CodeQL (gałąź `lukaszsajkowski/bream`), (C) dostawcy LLM, (D) metadane i release. Po (B) włączamy branch protection, więc (C) i (D) przechodzą już przez wymagane checki. Dostawcy LLM to adaptery za istniejącym `LLMClient`: retry i fallback zostają w kliencie, adapter mapuje błędy SDK na neutralne wyjątki.

**Tech Stack:** GitHub Actions, `gh` CLI, Python 3.13 + uv, `openai` SDK, `anthropic` SDK, Node 26 + Next.js 16, Vitest.

**Spec:** `docs/superpowers/specs/2026-11-05-phase0-repo-hygiene-design.md`

## Global Constraints

- README: wyłącznie poprawki faktów (domyślne modele/zmienne, „LangChain-OpenAI” w stacku). Żadnych nowych sekcji ani badge'y.
- Commity: konwencja z `.claude/skills/commit/SKILL.md` — `<type>: <subject>`, bez `Co-Authored-By`.
- Każda zmiana na `main` przez PR; po Task 5 branch protection obowiązuje też admina (`enforce_admins: true`), bez wymaganego approve.
- Domyślny dostawca `openai`, domyślny model `gpt-6-luna` (po weryfikacji ID w Task 6).
- `conversation.py` i `profiler.py` się nie zmieniają; publiczny interfejs `LLMClient.chat_completion(...) -> LLMResponse` zostaje.
- Bez LangChain i LiteLLM w warstwie LLM; `langchain-openai` usunięte z zależności.
- Dependabot: grupy per ekosystem, `interval: monthly`, `open-pull-requests-limit: 3`.
- E2E (Playwright) nie jest wymaganym checkiem CI.
- Jules wyłączony; `AGENTS.md` jedynym źródłem zasad dla agentów, `.claude/CLAUDE.md` do niego odsyła.

## Review Focus

1. Istniejący `.env` z `OPENAI_PRIMARY_MODEL=gpt-4o` dalej działa: wartość jest honorowana jako model główny (test w Task 9).
2. `LLM_PROVIDER=anthropic` bez `ANTHROPIC_API_KEY` daje `LLMConfigurationError` z nazwą `ANTHROPIC_API_KEY`, nie komunikat o OpenAI (test w Task 9).
3. Niedziałająca Ollama (connection refused) przechodzi ścieżkę retry → fallback → `LLMRequestError`, bez nieobsłużonego wyjątku SDK (test w Task 7).
4. Wiadomości z rolą `system` dla Anthropic (jedna lub kilka, na początku listy) trafiają do parametru `system`, a nie do `messages` (test w Task 8).
5. Model, który odrzucił `temperature`, przy kolejnym wywołaniu dostaje żądanie bez `temperature` od razu, bez ponownego błędu 400 (test w Task 7).

---

### Task 1: Wyłączenie Jules (krok ręczny właściciela)

- [ ] **Step 1:** Poproś właściciela o wyłączenie Jules dla repo `lukaszsajkowski/phish-guard-pro` w panelu Jules (w tym zaplanowanych zadań „Palette”). Nie kontynuuj Task 3, dopóki tego nie potwierdzi.
- [ ] **Step 2: Weryfikacja** — po 24 h: `gh pr list --state open --json createdAt --jq '[.[].createdAt]|max'`. Expected: data sprzed potwierdzenia wyłączenia.

### Task 2: PR (A) — konsolidacja poprawek a11y

**Files:**
- Modify: komponenty w `frontend/src/components/` wskazane przez diffy PR-ów (spodziewane: `IntelDashboard.tsx`, `PhishingEmailCard`, `ChatMessage`, `ThemeToggle`, przyciski kopiowania)
- Test: istniejące testy Vitest tych komponentów w `frontend/src/**/__tests__` lub obok komponentów

- [ ] **Step 1:** `git fetch origin && git switch -c chore/a11y-consolidation origin/main`.
- [ ] **Step 2: Inwentaryzacja.** `gh pr list --state open --limit 300 --json number,title,files,headRefName > <scratchpad>/prs.json`; zgrupuj PR-y po zmienianych plikach. Dla każdej grupy obejrzyj 1–2 najnowsze diffy (`gh pr diff <n>`) i spisz unikalne zmiany: `aria-live`/zmienny `aria-label` na przyciskach kopiowania, `aria-expanded` + `aria-controls` na rozwijanych sekcjach, tooltipy Radix na przyciskach ikonowych, `aria-label` na akcjach `ChatMessage`, tooltip `ThemeToggle`. Pomiń zmiany już obecne na `main`.
- [ ] **Step 3: Testy (failing).** Dla każdej zmiany dodaj asercję w teście komponentu, np. `expect(screen.getByRole('button', { name: /copy/i })).toHaveAttribute('aria-live', 'polite')`, `expect(toggle).toHaveAttribute('aria-expanded', 'false')` → po kliknięciu `'true'`. Run: `cd frontend && npx vitest run <pliki>`. Expected: FAIL na nowych asercjach.
- [ ] **Step 4:** Zaimplementuj zmiany w komponentach, używając istniejącego `@radix-ui/react-tooltip` / `components/ui/tooltip`.
- [ ] **Step 5: Weryfikacja.** `npx vitest run && npx eslint . && npx tsc --noEmit`. Expected: wszystko zielone (0 errors). Następnie lokalnie E2E przy działającym stacku (`/run-all`): `npm run test:e2e -- --project=chromium`. Expected: brak nowych porażek względem `main`.
- [ ] **Step 6:** Commit `feat: consolidate accessibility fixes from automated PRs`, push, `gh pr create` z listą numerów PR-ów, z których pochodzą zmiany. Merge po review właściciela.

### Task 3: Zamknięcie PR-ów Jules

**Interfaces:** Consumes: numer PR-u (A) z Task 2, potwierdzenie z Task 1.

- [ ] **Step 1:** Zbuduj listę do zamknięcia: otwarte PR-y, których `headRefName` nie jest `chore/a11y-consolidation` ani `lukaszsajkowski/bream` i które nie są od `dependabot`. Pokaż właścicielowi liczbę i 5 przykładowych tytułów; zamykanie wykonaj dopiero po jego „tak”.
- [ ] **Step 2:** Dla każdego: `gh pr close <n> --delete-branch --comment "Closing automated accessibility PRs generated by Jules. The useful changes were consolidated in #<A>. Jules is disabled for this repository."`
- [ ] **Step 3: Weryfikacja.** `gh pr list --state open --json number,headRefName`. Expected: tylko PR (A) jeśli jeszcze niezmergowany i PR (B).

### Task 4: PR (B) — `AGENTS.md`, CI, CodeQL, Dependabot

Gałąź: `lukaszsajkowski/bream` (zawiera już spec i plan); przed pracą `git rebase origin/main`.

**Files:**
- Create: `AGENTS.md`
- Modify: `.claude/CLAUDE.md` (zasady procesu zastąpione odesłaniem do `AGENTS.md`; opis architektury zostaje)
- Create: `.github/workflows/ci.yml`, `.github/workflows/codeql.yml`, `.github/dependabot.yml`

**Interfaces:** Produces: nazwy jobów CI `backend`, `frontend`, `secrets` — używane jako wymagane checki w Task 5 (CodeQL raportuje jako `Analyze (python)`, `Analyze (javascript-typescript)`).

- [ ] **Step 1: `AGENTS.md`.** Sekcje: zakres repo (1 akapit), praca na gałęzi i przez PR do `main`, quality gate przed PR (komendy z `CLAUDE.md`: `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `npx eslint .`, `npx vitest run`, `npx tsc --noEmit`), zakaz otwierania PR-u dublującego otwarty (sprawdź `gh pr list`), konwencja commitów (jak w Global Constraints), zakaz commitowania `.env`/sekretów, zasada „żadnych prawdziwych danych osobowych”. W `.claude/CLAUDE.md` dodaj na górze: „Process rules for coding agents live in `AGENTS.md`.” i usuń z niego ewentualne duplikaty tych reguł.
- [ ] **Step 2: `ci.yml`.** Triggery: `pull_request` do `main`, `push` do `main`. `permissions: contents: read`. Joby:
  - `backend` (ubuntu-latest, `working-directory: backend`): `astral-sh/setup-uv` z cache, Python 3.13, `uv sync --locked`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest -q`.
  - `frontend` (`working-directory: frontend`): `actions/setup-node` Node 26 z cache npm, `npm ci`, `npx eslint .`, `npx vitest run`, `npx tsc --noEmit`, `npm run build` z atrapami `NEXT_PUBLIC_SUPABASE_URL=http://localhost:54321`, `NEXT_PUBLIC_SUPABASE_ANON_KEY=ci-placeholder` i innymi `NEXT_PUBLIC_*` wymaganymi przy buildzie.
  - `secrets`: `actions/checkout` z `fetch-depth: 0`, `gitleaks/gitleaks-action@v2` (`GITHUB_TOKEN` w env).
  Akcje przypięte do konkretnych tagów wersji.
- [ ] **Step 3: `codeql.yml`.** Szablon CodeQL dla `python` i `javascript-typescript`, `build-mode: none`, triggery jak CI + `schedule` raz w tygodniu.
- [ ] **Step 4: `dependabot.yml`.** Ekosystemy: `uv` (`/backend`), `npm` (`/frontend`), `github-actions` (`/`). Każdy: `schedule.interval: monthly`, `open-pull-requests-limit: 3`, jedna grupa `patterns: ["*"]`.
- [ ] **Step 5: Lokalna weryfikacja buildu.** `cd frontend && NEXT_PUBLIC_SUPABASE_URL=http://localhost:54321 NEXT_PUBLIC_SUPABASE_ANON_KEY=ci-placeholder npm run build`. Expected: build kończy się sukcesem. Jeśli wymaga innych zmiennych, dopisz je do joba.
- [ ] **Step 6:** Commity (`docs: add AGENTS.md with coding agent rules`, `chore: add CI, CodeQL and Dependabot`), push, `gh pr create`.
- [ ] **Step 7: Weryfikacja.** `gh pr checks <B> --watch`. Expected: `backend`, `frontend`, `secrets`, oba `Analyze` = pass. Gitleaks przy pełnej historii może znaleźć stare sekrety: zgłoś każde trafienie właścicielowi (rotacja klucza to jego decyzja), fałszywe alarmy wpisz do `.gitleaks.toml` allowlist z komentarzem.
- [ ] **Step 8:** Merge PR (B) po akceptacji właściciela.

### Task 5: Branch protection i secret scanning

**Interfaces:** Consumes: nazwy checków z Task 4.

- [ ] **Step 1:** Włącz natywny secret scanning i push protection: `gh api -X PATCH repos/lukaszsajkowski/phish-guard-pro -F 'security_and_analysis[secret_scanning][status]=enabled' -F 'security_and_analysis[secret_scanning_push_protection][status]=enabled'`.
- [ ] **Step 2:** `gh api -X PUT repos/lukaszsajkowski/phish-guard-pro/branches/main/protection --input <scratchpad>/protection.json`, gdzie JSON: `required_status_checks: {strict: true, contexts: ["backend","frontend","secrets","Analyze (python)","Analyze (javascript-typescript)"]}`, `enforce_admins: true`, `required_pull_request_reviews: {required_approving_review_count: 0}`, `restrictions: null`, `allow_force_pushes: false`, `allow_deletions: false`.
- [ ] **Step 3: Weryfikacja.** `gh api repos/lukaszsajkowski/phish-guard-pro/branches/main/protection --jq '.enforce_admins.enabled, .required_status_checks.contexts'`. Expected: `true` i pięć nazw checków.

### Task 6: Weryfikacja identyfikatora modelu (bramka dla Task 7–10)

- [ ] **Step 1:** Z kluczem właściciela (z jego `.env` w głównym checkoucie; nie kopiuj go do worktree ani logów): `uv run python -c "import openai; print(sorted(m.id for m in openai.OpenAI().models.list() if m.id.startswith('gpt-')))"`.
- [ ] **Step 2:** Jeśli `gpt-6-luna` jest na liście → kontynuuj. Jeśli nie → STOP, pokaż właścicielowi listę `gpt-6*` i zapytaj.
- [ ] **Step 3: Model zapasowy OpenAI.** `gpt-6-luna-mini`, jeśli jest na liście; w przeciwnym razie najtańszy model `gpt-6*` z cennika `https://openai.com/api/pricing`. Zapisz wybór i ceny (input/output za 1M tokenów) obu modeli do użycia w Task 10.

### Task 7: PR (C) — warstwa dostawcy i adapter OpenAI/Ollama

Gałąź: `feat/llm-providers` z `origin/main`.

**Files:**
- Create: `backend/src/phishguard/llm/providers.py`
- Modify: `backend/src/phishguard/llm/client.py`
- Test: `backend/tests/unit/llm/test_providers.py`, `backend/tests/unit/llm/test_llm_client.py`

**Interfaces — Produces:**
- `Completion(NamedTuple)`: `content: str`, `prompt_tokens: int`, `completion_tokens: int` (zastępuje `_Completion`).
- Wyjątki w `providers.py`: `ProviderError(Exception)`; podklasy `ProviderAuthError`, `ProviderRateLimitError`, `ProviderConnectionError`, `ProviderServerError(status_code: int)`, `ProviderClientError(status_code: int)`.
- `class ChatProvider(Protocol)`: `async def complete(self, messages: list[dict[str, str]], model: str, temperature: float, max_tokens: int | None) -> Completion`; `async def close(self) -> None`.
- `class OpenAICompatibleProvider`: `__init__(self, api_key: str, timeout_seconds: float, base_url: str | None = None)`.
- `LLMClient.__init__(self, config: LLMClientConfig | None = None, api_key: str | None = None, provider: ChatProvider | None = None)` — `provider` wstrzykiwany w testach.

- [ ] **Step 1: Failing tests (`test_providers.py`):**
  - `test_openai_rate_limit_maps_to_provider_rate_limit` — SDK `create` rzuca `openai.RateLimitError` → `complete` rzuca `ProviderRateLimitError`.
  - `test_openai_5xx_maps_to_server_error` — `APIStatusError` 503 → `ProviderServerError` z `status_code == 503`.
  - `test_openai_4xx_maps_to_client_error` — 400 bez wzmianki o temperature → `ProviderClientError(400)`.
  - `test_openai_connection_error_maps` — `openai.APIConnectionError` → `ProviderConnectionError` (Review Focus 3).
  - `test_openai_auth_error_maps` — `AuthenticationError` → `ProviderAuthError`.
  - `test_temperature_dropped_after_unsupported_error` — pierwsze `create` rzuca `BadRequestError` z `param="temperature"`/komunikatem „Unsupported parameter: 'temperature'”, drugie zwraca odpowiedź; `complete` zwraca treść, a kwargs drugiego wywołania nie zawierają `temperature`.
  - `test_temperature_omission_is_remembered_per_model` — po powyższym kolejne `complete` dla tego samego modelu wywołuje `create` raz, bez `temperature`; dla innego modelu `temperature` jest wysyłane (Review Focus 5).
  - `test_max_tokens_sent_as_max_completion_tokens` — `max_tokens=100` → kwarg `max_completion_tokens=100`.
- [ ] **Step 2:** `cd backend && uv run pytest tests/unit/llm/test_providers.py -v`. Expected: FAIL (ImportError).
- [ ] **Step 3:** Zaimplementuj `providers.py` jak w Interfaces. `OpenAICompatibleProvider` trzyma `AsyncOpenAI(api_key, timeout, base_url)` i zbiór `_no_temperature_models: set[str]`. Odrzucenie temperatury rozpoznaje `BadRequestError` z `param == "temperature"` lub „temperature” w komunikacie; wtedy dodaje model do zbioru i ponawia raz bez `temperature`.
- [ ] **Step 4:** Przepisz `LLMClient`: `_make_request` deleguje do `self._provider.complete`, a `_attempt_with_retries` i `chat_completion` łapią wyjątki `Provider*` w miejsce typów `openai` (retry: connection, rate limit, server; brak retry i brak fallbacku: client error; `ProviderAuthError` → `LLMConfigurationError`). Na tym etapie klient zawsze buduje `OpenAICompatibleProvider` (wybór dostawcy w Task 9). Zaktualizuj `test_llm_client.py`: mockuj `ChatProvider` (`AsyncMock`) przekazany przez `provider=` i rzucaj wyjątki `Provider*` zamiast `openai.*`; nazwy i sens istniejących testów zostają.
- [ ] **Step 5:** `uv run pytest tests/unit/llm -v && uv run pytest -q`. Expected: wszystko PASS (baseline: 709 passed, 1 xfailed + nowe).
- [ ] **Step 6:** Commit `refactor: put OpenAI behind a provider adapter in LLMClient`.

### Task 8: Adapter Anthropic

**Files:**
- Modify: `backend/src/phishguard/llm/providers.py`, `backend/pyproject.toml` (+ `anthropic`), `backend/uv.lock`
- Test: `backend/tests/unit/llm/test_providers.py`

**Interfaces:** Consumes: `ChatProvider`, `Completion`, wyjątki `Provider*` z Task 7. Produces: `class AnthropicProvider`: `__init__(self, api_key: str, timeout_seconds: float)`; stała `ANTHROPIC_DEFAULT_MAX_TOKENS = 1024`.

- [ ] **Step 1: Failing tests:**
  - `test_anthropic_system_messages_go_to_system_param` — wejście `[system "A", system "B", user "hi"]` → `messages.create` dostaje `system="A\n\nB"` i `messages=[{"role":"user","content":"hi"}]` (Review Focus 4).
  - `test_anthropic_default_max_tokens` — `max_tokens=None` → `max_tokens=1024`.
  - `test_anthropic_joins_text_blocks_and_usage` — odpowiedź z dwoma blokami tekstu i `usage.input_tokens=10, output_tokens=5` → `Completion("ab", 10, 5)`.
  - `test_anthropic_error_mapping` (parametryzowany): `anthropic.RateLimitError` → `ProviderRateLimitError`, `APIStatusError` 529 → `ProviderServerError`, 400 → `ProviderClientError`, `APIConnectionError` → `ProviderConnectionError`, `AuthenticationError` → `ProviderAuthError`.
- [ ] **Step 2:** `uv add anthropic` (w `backend/`), potem `uv run pytest tests/unit/llm/test_providers.py -k anthropic -v`. Expected: FAIL.
- [ ] **Step 3:** Zaimplementuj `AnthropicProvider` na `anthropic.AsyncAnthropic`.
- [ ] **Step 4:** `uv run pytest tests/unit/llm -v`. Expected: PASS.
- [ ] **Step 5:** Commit `feat: add Anthropic provider for LLMClient`.

### Task 9: Wybór dostawcy w konfiguracji

**Files:**
- Modify: `backend/src/phishguard/core/__init__.py:32-34`, `backend/src/phishguard/llm/client.py` (`LLMClientConfig`, `LLMClient.__init__`, `create_llm_client`), `backend/src/phishguard/llm/__init__.py`
- Test: `backend/tests/unit/llm/test_llm_client.py`, `backend/tests/unit/core/test_settings_llm.py` (nowy; jeśli katalog `tests/unit/core` nie istnieje, utwórz go z `__init__.py`)

**Interfaces — Produces:**
- `Settings`: `llm_provider: Literal["openai","anthropic","ollama"] = "openai"`; `llm_primary_model: str = Field(default="", validation_alias=AliasChoices("LLM_PRIMARY_MODEL","OPENAI_PRIMARY_MODEL"))`; `llm_fallback_model` analogicznie z `OPENAI_FALLBACK_MODEL`; `anthropic_api_key: str = ""`; `ollama_base_url: str = "http://localhost:11434/v1"`. Pola `openai_primary_model`/`openai_fallback_model` usunięte.
- `PROVIDER_DEFAULT_MODELS: dict[str, tuple[str, str]]` w `client.py`: `openai → ("gpt-6-luna", <fallback z Task 6>)`, `anthropic → ("claude-sonnet-5-5", "claude-haiku-5-5")`, `ollama → ("qwen3:8b", "qwen3:4b")`.
- `LLMClientConfig`: nowe pole `provider: Literal["openai","anthropic","ollama"] = "openai"`; domyślne `primary_model`/`fallback_model` = wartości z `PROVIDER_DEFAULT_MODELS["openai"]`.
- `create_llm_client(primary_model=None, fallback_model=None, timeout_seconds=..., api_key=None)` — sygnatura bez zmian; czyta dostawcę z ustawień, pusty model → domyślny dostawcy.
- `build_provider(provider: str, api_key: str | None, timeout_seconds: float) -> ChatProvider` w `providers.py`.

- [ ] **Step 1: Failing tests:**
  - `test_legacy_openai_primary_model_env_is_honored` — `monkeypatch.setenv("OPENAI_PRIMARY_MODEL","gpt-4o")`, `Settings(_env_file=None).llm_primary_model == "gpt-4o"` (Review Focus 1).
  - `test_llm_primary_model_wins_over_legacy` — oba ustawione → wygrywa `LLM_PRIMARY_MODEL`.
  - `test_invalid_provider_rejected` — `LLM_PROVIDER=gemini` → `ValidationError`.
  - `test_defaults_per_provider` (parametryzowany po trzech dostawcach) — `create_llm_client()` przy pustych modelach ma `primary_model`/`fallback_model` z `PROVIDER_DEFAULT_MODELS`.
  - `test_anthropic_without_key_raises_named_error` — `llm_provider="anthropic"`, `anthropic_api_key=""` → `LLMConfigurationError`, w komunikacie `ANTHROPIC_API_KEY` (Review Focus 2).
  - `test_ollama_needs_no_key_and_uses_base_url` — `llm_provider="ollama"`, brak kluczy → klient powstaje; provider to `OpenAICompatibleProvider` z `base_url == settings.ollama_base_url`.
  - Zaktualizuj `test_default_values` w `TestLLMClientConfig` na nowe domyślne.
- [ ] **Step 2:** `uv run pytest tests/unit/llm tests/unit/core -v`. Expected: FAIL.
- [ ] **Step 3:** Zaimplementuj wg Interfaces. Klucz: `openai → openai_api_key` (`OPENAI_API_KEY`), `anthropic → anthropic_api_key` (`ANTHROPIC_API_KEY`), `ollama →` stała `"ollama"`. Zaktualizuj fixture `mock_settings` w testach (`llm_provider`, `llm_primary_model`, …).
- [ ] **Step 4:** `uv run pytest -q && uv run ruff check . && uv run ruff format --check .`. Expected: PASS / czysto. `grep -rn "openai_primary_model\|openai_fallback_model" backend/src` → brak wyników.
- [ ] **Step 5:** Commit `feat: select LLM provider and model from configuration`.

### Task 10: Ceny, zależności, dokumentacja faktów; zamknięcie PR (C)

**Files:**
- Modify: `backend/src/phishguard/decisions/eval/metrics.py:11-17`, `backend/pyproject.toml` (− `langchain-openai`), `backend/uv.lock`, `.env.example:25-29`, `README.md:15` i `README.md:155-157`, `.claude/CLAUDE.md` (linia o LangChain-OpenAI)
- Test: `backend/tests/unit/decisions/test_eval_report.py` lub istniejący test metryk

- [ ] **Step 1: Failing test** `test_prices_cover_provider_defaults` — każdy model z `PROVIDER_DEFAULT_MODELS` (oba elementy krotki, wszyscy dostawcy) jest kluczem `PRICES_PER_MTOK`; modele `ollama` mają `(0.0, 0.0)`.
- [ ] **Step 2:** Uzupełnij `PRICES_PER_MTOK`: modele OpenAI z Task 6, `claude-sonnet-5-5` i `claude-haiku-5-5` z cennika Anthropic (sprawdzić skillem `claude-api` lub na stronie cennika), modele ollama `(0.0, 0.0)`. Zostaw `gpt-4o`/`gpt-4o-mini` (stare raporty). Zaktualizuj komentarz z datą weryfikacji 2026-11-05 i źródłami.
- [ ] **Step 3:** `uv remove langchain-openai`; `grep -rn "langchain" backend/src` → brak wyników.
- [ ] **Step 4:** `.env.example`: sekcja `# LLM` z `LLM_PROVIDER=openai`, `LLM_PRIMARY_MODEL=` (pusty = domyślny dostawcy), `LLM_FALLBACK_MODEL=`, `OPENAI_API_KEY=`, `ANTHROPIC_API_KEY=`, `OLLAMA_BASE_URL=http://localhost:11434/v1`, komentarz, że `OPENAI_PRIMARY_MODEL`/`OPENAI_FALLBACK_MODEL` są nadal czytane.
- [ ] **Step 5:** README: linia 15 `LangChain-OpenAI` → `OpenAI / Anthropic / Ollama`; tabela/sekcja 155–157 → nowe zmienne i domyślne `gpt-6-luna`. To samo w `.claude/CLAUDE.md`. Nic więcej w README.
- [ ] **Step 6:** `uv run pytest -q && uv run ruff check . && uv run ruff format --check .`. Expected: PASS.
- [ ] **Step 7: Dymny test na żywo** (z kluczem właściciela, jak w Task 6): `uv run python -c "import asyncio; from phishguard.llm import create_llm_client; print(asyncio.run(create_llm_client().chat_completion([{'role':'user','content':'Say OK'}], temperature=0.7, max_tokens=20)))"`. Expected: `LLMResponse` z `model_used='gpt-6-luna'`, `used_fallback=False`.
- [ ] **Step 8:** Commity (`chore: update model prices and drop langchain-openai`, `docs: correct LLM configuration facts`), push, `gh pr create`, `gh pr checks --watch` → pass, merge po akceptacji właściciela.

### Task 11: PR (D) — metadane repo i release `v0.1.0`

**Files:**
- Create: `LICENSE`, `SECURITY.md`, `CHANGELOG.md`

- [ ] **Step 1:** `gh repo edit lukaszsajkowski/phish-guard-pro --description "AI agents that keep phishing scammers talking, waste their time and extract IOCs (wallets, IBANs, phones, URLs)." --add-topic langgraph,agentic-ai,threat-intelligence,scambaiting,honeypot,phishing,fastapi,nextjs`. Weryfikacja: `gh repo view --json description,repositoryTopics`.
- [ ] **Step 2:** Gałąź `chore/release-v0.1.0` z `origin/main`. `LICENSE`: standardowy tekst MIT, `Copyright (c) 2026 Lukasz Sajkowski`.
- [ ] **Step 3:** `SECURITY.md`: zakres (kod w tym repo), zgłaszanie przez GitHub Private Vulnerability Reporting (włącz: `gh api -X PUT repos/lukaszsajkowski/phish-guard-pro/private-vulnerability-reporting`), czas odpowiedzi „best effort”, zasada: projekt nigdy nie wysyła prawdziwych danych osobowych, zgłoszenia nie powinny ich zawierać.
- [ ] **Step 4:** `CHANGELOG.md` w formacie Keep a Changelog, jedna sekcja `## [0.1.0] - <data release'u>` z grupami `Added` / `Changed` / `Security`, zbudowana z `git log --oneline` i nagłówków US z `.ai/prd.md` (obszary: profiler, persona, rozmowa, IOC i wzbogacanie, safety, historia sesji, Basal, faza 0). 10–25 pozycji, nie lista commitów.
- [ ] **Step 5:** Commit `docs: add license, security policy and changelog`, PR, `gh pr checks --watch` → pass, merge.
- [ ] **Step 6:** Po merge: `gh release create v0.1.0 --target main --title "v0.1.0" --notes-file <sekcja 0.1.0 z CHANGELOG.md>`. Weryfikacja: `gh repo view --json latestRelease,licenseInfo` → `v0.1.0` i `MIT`.

### Task 12: Końcowa weryfikacja fazy 0

- [ ] **Step 1:** `gh pr list --state open` → tylko ewentualne PR-y Dependabota (≤ 3 na ekosystem).
- [ ] **Step 2:** `gh api repos/lukaszsajkowski/phish-guard-pro/actions/runs --jq '.workflow_runs[0:3][] | {name, conclusion, head_branch}'` → ostatnie przebiegi na `main` z `conclusion: success`.
- [ ] **Step 3:** Pokaż właścicielowi podsumowanie: link do repo, liczba zamkniętych PR-ów, numery PR-ów A–D, release.
