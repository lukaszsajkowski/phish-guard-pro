# Basal Decision Layer — Etap 1: fundament i Profiler

Data: 2026-11-02 · Źródło: PRD „Basal Decision Layer w PhishGuard Pro” (Downloads), przegląd PRD vs kod z 2026-11-02.

## Po co

PhishGuard Pro klasyfikuje e-mail (Profiler) przez GPT-4o, który sam podaje sobie „pewność” 0–100. Ta liczba nie jest skalibrowana, a gdy odpowiedź GPT nie daje się sparsować, Profiler zwraca `not_phishing` z pewnością 25 i sesja się kończy.

Basal to lokalny model decyzyjny: odpowiada rozkładem prawdopodobieństwa po zamkniętej liście opcji, skalibrowanym tak, że próg pewności przekłada się na znany poziom błędu. Wzorzec kaskady Basal → LLM jest sprawdzony w autoshield (`~/Workspace/autoshield/judge.py`: 84% werdyktów lokalnie przy progu 0,9, zero niezgodności na 250 przypadkach).

**Przegląd kodu zmienił cel projektu.** Pierwotny PRD obiecywał −50% kosztu LLM. To nieosiągalne: GPT jest wołany w dwóch miejscach, Profiler raz na sesję (`max_tokens=200`), Conversation Agent co turę, i ten drugi zostaje na GPT. Cel projektu to więc **decyzje z wiarygodną pewnością** i, w kolejnych etapach, **nowe kontrole znaczeniowe**, których regexy nie dają. Koszt jest mierzony, ale nie jest hipotezą.

Etap 1 buduje warstwę decyzyjną, przepina na nią jedyną decyzję, w której Basal faktycznie zastępuje GPT (typ ataku w Profilerze), i daje liczby z evalu, na których opierają się etapy 2 i 3.

## Hipoteza etapu 1

Przy wybranym progu Basal rozstrzyga lokalnie co najmniej 70% klasyfikacji typu ataku, zgadzając się z GPT-4o w ≥ 95% (błąd ≤ 2% wśród decyzji Basala), z medianą opóźnienia < 150 ms lokalnie. Liczby są punktem startowym; pierwszy eval może je skorygować.

## Cele

1. Moduł `phishguard.decisions`: klient Basala, detekcja języka, kaskada Basal → LLM, zapis każdej decyzji.
2. Trzy tryby pracy: `off`, `shadow` (Basal liczy, werdykt daje GPT), `live` (kaskada).
3. Profiler korzysta z kaskady dla typu ataku.
4. Licznik tokenów dla każdego wywołania GPT (Profiler i Conversation Agent), żeby koszt „przed i po” był zmierzony, a nie szacowany.
5. Eval z CLI: zapisane sesje z Supabase + syntetyczny zbiór e-maili, raport coverage vs. błąd w funkcji progu.

## Non-goals (etap 1)

- Kontrola „czy odpowiedź wychodzi z roli” (etap 2), ocena IOC jako przynęty (etap 3).
- Poziom ryzyka na Basalu: deterministyczna formuła w `risk_score_service.py` zostaje, jest wyjaśnialna i darmowa.
- „Następny krok” jako `act`: dziś taktykę wybiera Conversation Agent w tym samym wywołaniu, w którym pisze odpowiedź, więc osobna decyzja dodałaby wywołanie zamiast je usunąć.
- Panel Decision Ops w aplikacji: w etapie 1 jego rolę pełni raport z evalu.
- Tryb `evidence`: działa tylko z modelem w procesie PyTorch, a nie na MLX (`basal/server.py`: „evidence is not available for this model”). Na Macu nie da się go użyć.
- Fine-tuning Basala, GPU w chmurze, języki inne niż PL/EN w Basalu.

## Anti-goals (porażka, nawet jeśli „działa”)

- Sesja przerywa się albo klasyfikacja zwraca błąd, bo Basal jest wyłączony, wolny lub zwraca coś nieoczekiwanego.
- Tryb cienia zauważalnie spowalnia klasyfikację (Basal i GPT muszą iść równolegle).
- Tabela `decisions` staje się drugą kopią treści e-maili (treść jest już w `messages`; `decisions` trzyma odniesienie do sesji, nie tekst).
- Zmiana znaczenia `confidence` psuje dzisiejsze ostrzeżenia w UI bez świadomej decyzji.

## Jak to działa

### Kaskada (tryb `live`)

```
pytanie zamknięte
  ├─ BASAL_URL puste / tryb off ──────────────────────────► LLM
  ├─ tekst nie PL/EN (detekcja per linia) ────────────────► LLM
  ├─ Basal: błąd HTTP / timeout ──────────────────────────► LLM  (sesja trwa, warning w logu)
  ├─ Basal: pewność ≥ próg węzła ─────────────────────────► werdykt Basala
  └─ Basal: pewność < próg ───────────────────────────────► LLM (ta sama lista opcji)
```

Detekcja języka jak w autoshield (`is_basal_language`): `fast-langdetect`, sprawdzane per linia, linie < 20 liter pomijane, odrzucenie gdy język spoza {pl, en} ma score ≥ 0,5.

### Tryb `shadow`

Werdykt zawsze z LLM, dokładnie jak dziś. Basal rusza jako zadanie w tle (`asyncio.create_task`) w chwili startu wywołania LLM, a klasyfikacja **nie czeka** na jego wynik. Zadanie samo zapisuje wiersz w `decisions` po zakończeniu, także po zwróceniu odpowiedzi HTTP. `BASAL_TIMEOUT_S` ogranicza tylko to zadanie; przekroczenie zapisuje się jako `skip_reason = 'timeout'`. Wyjątki w zadaniu są łapane i logowane, nigdy nie wyciekają. Referencje do zadań trzymane w zbiorze modułu, żeby nie zebrał ich GC (moja decyzja; `asyncio.gather` z timeoutem dodawałby do 5 s do każdej klasyfikacji).

W trybie `live` Basal jest wołany najpierw i LLM tylko przy eskalacji, więc tam opóźnienie Basala jest częścią ścieżki.

### Interfejs Basala

Serwer `basal-serve`, endpoint `POST {BASAL_URL}` (np. `http://127.0.0.1:8011/v1/systemone`), jak w autoshield:

```json
{"state": "<treść e-maila>",
 "questions": {"attack_type": {"type": "choice", "option_keys": "hide",
                               "instructions": "...", "criteria": {"nigerian_419": "...", ...}}}}
```

Odpowiedź: `answers.attack_type` z `choice`, `probabilities` (klucz → p) i `confidence`. Kluczami opcji są wartości `AttackType` (9 sztuk, w tym `not_phishing`), a opisami treści z docstringów enumu i z `PROFILER_SYSTEM_PROMPT`. `option_keys: "hide"`, bo tak Basal był kalibrowany (komentarz w autoshield). Kategorii „inny” nie dodajemy; tak jak dziś, niepewne przypadki trafiają do LLM.

Model: `Remek/basal-2.0-max-MLX-8bit`, ten sam co w autoshield, już zainstalowany lokalnie w `~/basal-mlx`. To moja decyzja. `BASAL_MODEL` służy tylko do logowania i raportu, model wybiera serwer.

### Profiler w kaskadzie

`ProfilerAgent` dostaje wstrzykiwany `DecisionService` (domyślnie z ustawień). Graf się nie zmienia. Zmienia się węzeł `classify_email` (przekazuje `session_id` do `classify()` i kopiuje `decision_source` do stanu), `ClassificationState` (nowe pole `decision_source`) oraz `api/routers/classification.py` (przenosi pole do `ClassificationResult`).

`decision_source` jest zapisywane w nowej kolumnie `sessions.decision_source` (text, null dla starych sesji) w `update_session_classification`, a przywracanie sesji (US-031) je odczytuje. Dzięki temu etykieta źródła przetrwa przeładowanie. Moja decyzja: bez tego przywrócona sesja pokazywałaby pewność Basala bez etykiety.

Kiedy decyduje Basal:
- `attack_type` = odpowiedź Basala.
- `confidence` = skalibrowane p × 100 (pole zostaje w skali 0–100).
- `reasoning` = tekst z szablonu, bo Basal nie pisze uzasadnień, a `evidence` na MLX nie działa: `"Classified locally by Basal: Romance Scam (p=0.94). Runner-up: Nigerian 419 (p=0.03)."`
- `decision_source = "basal"` (nowe pole w `ClassificationResult`, domyślnie `"llm"`).

Kiedy decyduje LLM: zachowanie jak dziś, `decision_source = "llm"`.

**Poprawka fallbacku (tylko `live`).** Jeśli GPT zwróci nieparsowalną odpowiedź albo całe wywołanie się nie uda (`LLMRequestError`, dziś kończy się 500), a Basal odpowiedział (nawet poniżej progu), zwracamy najwyższą opcję Basala z jej prawdziwą pewnością i `decision_source = "basal_low_confidence"`, zamiast `not_phishing`/25. Bez odpowiedzi Basala zostaje dzisiejszy fallback.

### Znaczenie `confidence` w UI

Progi we froncie (`ClassificationResult.tsx`: < 30 ostrzeżenie dla `not_phishing`, < 50 żółty, ≥ 80 „wysoka”) zostają bez zmian w etapie 1, ale **liczba zmienia znaczenie**: przy Basalu to prawdopodobieństwo skalibrowane, przy GPT samoocena. Dlatego:
- Obok pewności UI pokazuje małą etykietę źródła („Basal” / „GPT-4o”), żeby było widać, którą skalę się czyta. To moja decyzja.
- Raport z evalu pokazuje, czy progi 30/50/80 mają sens dla pewności Basala; zmiana progów to decyzja po evalu.

## Dane

### Tabela `decisions` (nowa migracja)

| kolumna | typ | uwagi |
|---|---|---|
| id | uuid pk | |
| session_id | uuid fk → sessions, on delete cascade | |
| node | text | `'profiler.attack_type'` w etapie 1 |
| mode | text check in (`shadow`, `live`) | |
| options | jsonb | lista kluczy opcji |
| basal_answer | text null | |
| basal_probabilities | jsonb null | |
| basal_confidence | float null | |
| basal_ms | int null | |
| basal_model | text null | |
| threshold | float | próg obowiązujący przy tej decyzji |
| skip_reason | text null | `disabled`, `language`, `unavailable`, `timeout`, `below_threshold` |
| llm_answer | text null | |
| llm_model | text null | |
| llm_ms | int null | |
| final_answer | text | |
| source | text check in (`basal`, `llm`, `basal_low_confidence`) | |
| created_at | timestamptz default now() | |

RLS: odczyt i zapis dla właściciela sesji, wzorowane na `ioc_extracted`. Indeks po `session_id` i `node`.

Zapis decyzji nie może zablokować klasyfikacji: błąd zapisu kończy się warningiem w logu.

### Tabela `llm_usage` (nowa migracja)

`id, session_id (fk, null dozwolone), agent ('profiler'|'conversation'|'eval'), model, prompt_tokens, completion_tokens, latency_ms, created_at`, RLS jak wyżej.

`LLMResponse` dostaje `prompt_tokens` i `completion_tokens` z `usage` OpenAI. Agenci zapisują je do `llm_usage`. Koszt liczy raport na podstawie cennika w jednym słowniku (model → USD/1M tokenów in/out), nie w bazie.

## Konfiguracja (`.env`, `Settings`)

| zmienna | domyślnie | znaczenie |
|---|---|---|
| `BASAL_URL` | `""` | puste = warstwa wyłączona, wszystko idzie do LLM |
| `BASAL_MODE` | `shadow` | `off` / `shadow` / `live`; ignorowane, gdy `BASAL_URL` puste |
| `BASAL_THRESHOLD` | `0.9` | domyślny próg (jak w autoshield) |
| `BASAL_THRESHOLD_PROFILER` | brak | nadpisuje próg dla węzła Profilera |
| `BASAL_TIMEOUT_S` | `5` | timeout zapytania do Basala |
| `BASAL_MODEL` | `""` | etykieta modelu do logów i raportu |

Progi są per węzeł od początku, bo etap 2 (kontrola roli) dostanie ostrzejszy próg.

**Zmiana trybu i progów:** tylko przez `.env` i restart backendu (`Settings` jest cache'owane przez `lru_cache`). W etapie 1 nie ma przełącznika w UI ani endpointu: to ustawienie jednego właściciela dla całej instancji, a nie per użytkownik czy per sesja. Każdy wiersz `decisions` zapisuje `mode` i `threshold`, więc w danych widać, kiedy ustawienia się zmieniły. Przełącznik w aplikacji może wejść razem z panelem Decision Ops.

## Eval (CLI)

`uv run python -m phishguard.decisions.eval profiler --source supabase|fixtures|decisions|all --out <dir>`

`--source decisions` nie woła żadnego modelu: czyta wiersze trybu `shadow` z tabeli `decisions` (te z odpowiedzią i Basala, i LLM) i liczy na nich te same metryki, z LLM jako referencją. To jest narzędzie do bramki 2. `all` = `supabase` + `fixtures` (bez `decisions`).

**Wejście:**
- **Supabase:** wszystkie sesje z oryginalnym e-mailem (`session_service.get_original_email`), czytane kluczem service role. Liczba sesji nadających się do evalu nie jest znana; skrypt ją raportuje.
- **Fixtures:** `backend/tests/fixtures/eval/profiler_emails.jsonl`, około 100 e-maili PL/EN z etykietą `gold`, po kilka na każdy z 9 typów, w tym trudne przypadki (granice CEO fraud / fake invoice, prawdziwe faktury, newslettery). Generowane z pomocą LLM; **etykiety przegląda ręcznie właściciel projektu (Łukasz)** i każdy wiersz dostaje pole `reviewed: true` po przeglądzie. Ten zbiór pokrywa ryzyko „za mało historycznych sesji”.

Punkt przekazania: budowniczy generuje zbiór z `reviewed: false` i zatrzymuje się na przegląd. Eval na fixtures da się uruchomić wcześniej (do strojenia skryptu), ale raport oznacza wtedy wynik jako „etykiety nieprzejrzane” i taki wynik nie zalicza bramki 1. Etykiety muszą być niezależne od GPT: przy przeglądzie właściciel nie widzi odpowiedzi GPT-4o ani Basala dla danego e-maila.

**Przebieg:** dla każdego e-maila Basal (pełny rozkład) i świeże wywołanie GPT-4o z obecnym promptem Profilera. Referencja: `gold` dla fixtures, GPT-4o dla Supabase. `attack_type` zapisany w sesji to tylko dodatkowa kolumna, bo mógł pochodzić z `gpt-4o-mini` (fallback).

**Wyjście:**
- `results.jsonl`: jeden wiersz na przypadek, z rozkładem Basala, odpowiedzią GPT, referencją i czasami.
- `report.md`: dla progów 0,50–0,99 co 0,01 coverage, błąd wśród decyzji Basala, łączna zgodność kaskady, p50/p95 opóźnienia Basala i GPT, koszt GPT na 1000 klasyfikacji. Do tego macierz pomyłek, najniższy próg spełniający błąd ≤ 2% oraz rozkład pewności Basala w przedziałach 30/50/80 (pod decyzję o progach w UI).
- Wykres coverage vs. błąd jako PNG (matplotlib) do README i case study.

Eval nie zmienia ustawień. Próg i przejście `shadow` → `live` wybiera właściciel po przeczytaniu raportu.

## Bramki przejścia na `live`

1. Raport z evalu: zgodność ≥ 95% przy wybranym progu na fixtures i na Supabase (jeśli jest co najmniej 30 sesji).
2. Co najmniej 30 decyzji w trybie `shadow` na prawdziwych e-mailach, z rozbieżnościami Basal vs. LLM przejrzanymi ręcznie (`eval --source decisions`). Próg jest liczbą decyzji, a nie czasem (moja decyzja): aplikacja działa w ręcznej symulacji, więc tydzień może dać kilka sesji albo żadnej.

## Testy

- Klient Basala: zamockowany HTTP (sukces, błąd 5xx, timeout, odpowiedź bez oczekiwanego klucza).
- Kaskada: sparametryzowane przypadki dla każdej gałęzi diagramu i każdego trybu. W `shadow` werdykt zawsze z LLM, nawet przy pewności Basala 0,99.
- Profiler: decyzja Basala daje poprawne `confidence`, `reasoning` i `decision_source`; poprawka fallbacku działa tylko w `live`.
- Detekcja języka: PL, EN, DE, tekst mieszany, krótkie linie.
- Eval: liczenie metryk na małym, ręcznie policzonym zbiorze.
- Istniejące testy Profilera i grafu przechodzą bez zmian przy `BASAL_URL=""`.

## Mapowanie na PRD

Numeracja kontynuuje `.ai/prd.md` (ostatnie: US-045/046). Etap 1 = US-047 (klient), US-048 (kaskada + `decisions`), US-049 (Profiler, tylko typ ataku), US-053 (eval, tylko Profiler), plus nowe US na licznik tokenów. Pierwotne US-050/051/052/054 przechodzą do etapów 2–3 w zmienionym kształcie z przeglądu. Aktualizacja `.ai/prd.md` jest częścią pracy.

## Zostawione budowniczemu

- Układ plików w `phishguard/decisions/` i nazwy klas.
- Sposób zapisu do Supabase (ten sam klient co `session_service`).
- Biblioteka do mockowania HTTP w testach (zgodnie z tym, co już jest w `pyproject.toml`).
- Treść opisów opcji dla Basala (z docstringów `AttackType` i promptu Profilera).
- Wygląd etykiety źródła w UI, w stylu istniejącego badge’a pewności.
