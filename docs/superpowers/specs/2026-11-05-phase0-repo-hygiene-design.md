# Faza 0: porządki w repozytorium przed rekrutacją

Data: 2026-11-05. Źródło: raport „PhishGuard Pro: kierunki rozwoju projektu portfolio (listopad 2026)”, sekcja „Faza 0”.

## Po co

Repo będzie oglądane w procesie rekrutacji. Pierwszy czytelnik to **HR albo executive**: nie czyta kodu, widzi stronę główną repo (opis, tematy, licencja, release) i liczbę otwartych PR-ów. Drugi czytelnik to **inżynier z dalszego etapu**: dla niego dowodem dojrzałości są zielone checki w CI, skanowanie sekretów, proces PR i aktualne, konfigurowalne modele.

Dziś oba wrażenia są złe: 138 otwartych, niemal identycznych PR-ów od agenta, brak CI, brak opisu i licencji, domyślny model z 2024 roku.

## Stan wyjściowy (sprawdzony 2026-11-05)

- 138 otwartych PR-ów, wszystkie z konta właściciela (Jules działa w jego imieniu). 134 mają tytuł „🎨 Palette…”, 4 pozostałe też dotyczą a11y/tooltipów. Daty: od 2026-04-15 do 2026-11-05; Jules nadal otwiera nowe codziennie.
- Brak `.github/`, zero workflow w Actions. Zmergowany przez PR tylko 1; praca trafia na `main` bezpośrednio.
- Opis repo pusty, brak tematów, brak pliku `LICENSE` (README deklaruje MIT w sekcji „License”), brak release'ów, brak `SECURITY.md`, `AGENTS.md`, `CHANGELOG.md`.
- LLM: `backend/src/phishguard/llm/client.py` używa bezpośrednio `openai.AsyncOpenAI` (nie LangChain; zależność `langchain-openai` w `pyproject.toml` nie jest importowana w `src/`). Domyślne modele `gpt-4o` / `gpt-4o-mini` w `core/__init__.py:33-34`, `llm/client.py:51-52` i `.env.example` (`OPENAI_PRIMARY_MODEL`, `OPENAI_FALLBACK_MODEL`). Ceny tylko dla gpt-4o wpisane na sztywno w `decisions/eval/metrics.py:15-16`. Wołający: `agents/conversation.py`, `agents/profiler.py`.
- Playwright E2E startuje `npm run dev` i zakłada działający backend z Supabase i kluczem OpenAI.

## Cele

1. Zakładka Pull requests jest czysta, a Jules już nie otwiera nowych PR-ów.
2. Każda zmiana na `main` przechodzi przez PR z zielonymi checkami.
3. Strona główna repo ma opis, tematy, licencję i release `v0.1.0`.
4. Dostawcę i model LLM wybiera się w konfiguracji; domyślny model jest aktualny.

## Poza zakresem (decyzje właściciela)

- **Publiczne demo i Docker Compose** (punkt 0.5 raportu) wypadają.
- **README bez przebudowy** w tej fazie: bez nowych sekcji, bez badge'y, bez sekcji o pracy z agentami. Dozwolone (i wymagane) są **poprawki faktów**, które zdezaktualizuje 0.4: domyślne modele i zmienne środowiskowe (README.md:155-157), „LangChain-OpenAI” w stacku (README.md:15). To samo dotyczy `.claude/CLAUDE.md`.
- Jules nie jest konfigurowany „w ryzach”, tylko wyłączony.

## Anty-cele

- Utrata sensownych poprawek a11y przy masowym zamykaniu PR-ów.
- CI, które jest czerwone albo wymaga sekretów, przez co blokuje każdy PR. Lepiej mniej checków, ale wiarygodnie zielonych.
- Zmiana dostawcy LLM, która zmienia zachowanie aplikacji przy domyślnej konfiguracji poza samą wymianą modelu.

## Zakres

### 0.1 Jules i PR-y

- **Wyłączenie Jules**: robi to właściciel ręcznie w panelu Jules (nie da się z repo). Plan ma to wymienić jako krok ręczny, przed zamknięciem PR-ów, żeby nie dochodziły nowe.
- **Konsolidacja**: przejrzeć 138 PR-ów, wyłuskać niepowtarzające się poprawki (`aria-live` na przyciskach kopiowania, `aria-expanded` na rozwijanych sekcjach, tooltipy Radix na przyciskach ikonowych, `aria-label` w `ChatMessage`), sprawdzić, które nie są już na `main`, i złożyć je w **jeden PR** na aktualnym `main`, z testami tam, gdzie testy komponentów już istnieją.
- **Zamknięcie**: pozostałe PR-y zamknąć z jednym, wspólnym komentarzem (po angielsku) odsyłającym do PR-u konsolidującego. Usunąć ich gałęzie zdalne.
- **`AGENTS.md`** w korzeniu: zasady dla agentów kodujących (Claude, Gemini): praca na gałęzi i przez PR, uruchomienie quality gate'u przed PR, nie otwierać PR-u dublującego otwarty, konwencja commitów. Bez wzmianki o Jules jako aktywnym agencie.

### 0.2 CI i ochrona `main`

- Workflow GitHub Actions uruchamiany na PR do `main` i na push do `main`:
  - backend: `uv sync`, `ruff check`, `ruff format --check`, `pytest` (testy niewymagające sieci/sekretów),
  - frontend: `npm ci`, `eslint`, `vitest run`, type-check, `next build`.
- Bezpieczeństwo: secret scanning (gitleaks albo natywny GitHub secret scanning + push protection), CodeQL (Python, JavaScript/TypeScript), Dependabot (pip/uv, npm, github-actions).
- **Branch protection na `main`**: merge tylko przez PR, wymagane zielone checki z powyższej listy, bez wymaganego approve (właściciel pracuje sam), bez force-pushy. **Reguły obowiązują też admina** (`enforce_admins`, decyzja właściciela): changelog i release również idą przez PR.
- **Dependabot** (decyzja asystenta): aktualizacje grupowane per ekosystem, harmonogram miesięczny, niski `open-pull-requests-limit`, plus alerty/aktualizacje bezpieczeństwa. Cel: nie odtworzyć zalewu PR-ów.
- Od tej fazy właściciel pracuje workflow gałąź → PR → zielone checki → merge.

### 0.3 Metadane repo

- Opis (jedno zdanie po angielsku) i tematy: m.in. `langgraph`, `agentic-ai`, `threat-intelligence`, `scambaiting`, `honeypot`, `phishing`, `fastapi`, `nextjs`.
- `LICENSE` (MIT, właściciel: Lukasz Sajkowski, 2026), zgodnie z deklaracją w README.
- `SECURITY.md`: jak zgłaszać podatności, zakres, zasada „żadnych prawdziwych danych osobowych”.
- `CHANGELOG.md` i release `v0.1.0` z notatkami zbudowanymi z historii (grupowanie po US/obszarach, nie lista 144 commitów).

### 0.4 Dostawca i model LLM

- Konfiguracja wybiera dostawcę: `openai` (domyślny), `anthropic`, `ollama`.
- Domyślny model główny: **`gpt-6-luna`** (decyzja właściciela). Przed wpisaniem identyfikator trzeba potwierdzić na liście modeli z API OpenAI, bo jest nowszy niż wiedza asystenta.
- Publiczny interfejs `LLMClient` (`chat_completion`, `LLMResponse` z `used_fallback`, `model_used`, tokenami) zostaje, więc `conversation.py` i `profiler.py` się nie zmieniają. Retry z backoffem i fallback do tańszego modelu działają dla każdego dostawcy.
- Ceny w `decisions/eval/metrics.py` przechodzą do jednej tabeli per model, obejmującej nowe modele domyślne (Ollama = koszt 0).
- `.env.example` i `core/__init__.py` opisują nowe zmienne; stare `OPENAI_PRIMARY_MODEL` / `OPENAI_FALLBACK_MODEL` dalej działają albo są czytelnie zastąpione (decyzja wykonawcy, byle lokalne `.env` nie przestało działać bez komunikatu).

## Kolejność

1. Wyłączenie Jules (ręcznie) → 0.1 (konsolidacja, zamknięcie PR-ów, `AGENTS.md`).
2. 0.2 CI, potem włączenie branch protection. Od tego momentu wszystko idzie przez PR.
3. 0.4 jako pierwszy „prawdziwy” PR przez nowe CI.
4. 0.3 na końcu: release `v0.1.0` obejmuje wszystko powyżej.

## Decyzje asystenta (do sprawdzenia przez właściciela)

- **Abstrakcja dostawcy**: wcześniej w rozmowie proponowałem `init_chat_model` z LangChain. Kod okazał się nie używać LangChain do LLM, tylko SDK OpenAI. Zamiast tego: adaptery za istniejącym `LLMClient` — SDK OpenAI dla `openai` i dla `ollama` (endpoint zgodny z OpenAI, `base_url`), natywne SDK `anthropic` dla Anthropic. Nie dokładamy LangChain ani LiteLLM.
- **Model zapasowy** dla OpenAI wybiera asystent z listy modeli API (tańszy wariant z tej samej rodziny co domyślny). Domyślne modele dla `anthropic` i `ollama` też wybiera asystent.
- **Parametry modelu**: jeśli `gpt-6-luna` (lub inny model) nie przyjmuje `temperature` albo wymaga `max_completion_tokens` zamiast `max_tokens`, dopasowanie robi `LLMClient` na podstawie modelu; wołający się nie zmieniają. Pominięcie `temperature` dla modelu, który go nie obsługuje, jest akceptowaną częścią „wymiany modelu”.
- **Weryfikacja identyfikatora modelu**: lokalnie, kluczem z `backend/.env` właściciela, na początku 0.4. Jeśli `gpt-6-luna` nie ma na liście, praca nad 0.4 staje i wraca do właściciela.
- **`AGENTS.md` jako jedyne źródło zasad**: `.claude/CLAUDE.md` odsyła do niego zamiast powtarzać reguły. Konwencja commitów zgodna z istniejącym skillem `.claude/skills/commit`.
- **PR konsolidujący a11y** może zawierać widoczne tooltipy, nie tylko atrybuty aria. Przed mergem E2E uruchamiane lokalnie.
- **E2E (Playwright) nie jest wymaganym checkiem** w tej fazie, bo potrzebuje backendu, Supabase i klucza OpenAI. Można go dodać jako workflow ręczny (`workflow_dispatch`) albo pominąć.
- Nieużywaną zależność `langchain-openai` usuwamy przy 0.4.

## Zostawione wykonawcy

- Wybór gitleaks vs natywny secret scanning, wersje akcji, cache w CI, macierz wersji.
- Jak dokładnie oznaczyć testy backendu wymagające sieci, jeśli takie istnieją.
- Treść komentarza zamykającego PR-y, opis repo, dokładna lista tematów, treść `SECURITY.md` i `AGENTS.md`.
