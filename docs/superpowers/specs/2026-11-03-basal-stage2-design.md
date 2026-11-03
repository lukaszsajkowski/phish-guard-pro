# Basal Decision Layer — Etap 2: sygnały znaczeniowe obok regexów

Data: 2026-11-03. Kontynuacja `2026-11-02-basal-decision-layer-stage1-design.md`.

## Po co

Etap 1 sprawdził jedyne miejsce, w którym Basal mógł **zastąpić** GPT (typ ataku w Profilerze). Wynik:

| Bramka | Dane | Wynik |
|---|---|---|
| 1 (fixtures) | 98 syntetycznych e-maili PL/EN, etykiety dwóch modeli Claude | **zaliczona**: próg 0,70, pokrycie 93,9%, błąd 0%, zgodność kaskady 98% |
| 2 (shadow) | 29 prawdziwych e-maili (korpus Nazario `phishing-2025`, CC BY 4.0) | **niezaliczona**: zgodność z gpt-5.1 13/28, przy progu 0,70 błąd ~48%; Basal uznał 13/28 phishingów za `not_phishing`, część z pewnością 0,92–0,98 |

Wniosek: Basal dobrze rozpoznaje **cechę znaczeniową tekstu, który nie udaje niewinnego** (jawny scam), i źle odróżnia **phishing przebrany za rutynowe powiadomienie** od prawdziwej poczty. Syntetyczny zbiór zawyżył wynik: bramka 1 nie przewidziała bramki 2.

Etap 2 przenosi Basala tam, gdzie te warunki działają na jego korzyść: do decyzji, które dziś podejmują **angielskie regexy** albo **nikt**, na tekście napastnika lub na naszym własnym. Basal nie konkuruje tu z lepszym modelem, tylko z listą fraz, która nie zna polskiego i parafraz.

## Decyzje właściciela

- Opóźnienie Basala (~4–9 s na M1 Pro, MLX, model `max`) jest **poza zakresem** tego etapu (2026-11-03). Projekt nie optymalizuje czasu odpowiedzi i nie ukrywa go w UI.
- Profiler zostaje na GPT. Węzeł `profiler.attack_type` nie przechodzi na `live`.

## Cele

1. Warstwa decyzyjna obsługuje **tryb sygnału**: Basal obok deterministycznej referencji (regex) zamiast kaskady Basal → LLM.
2. **Tryb per węzeł** (`off`/`shadow`/`live`), bo Profiler zostaje w `shadow`/`off`, a nowe węzły przechodzą na `live` niezależnie.
3. Trzy węzły:
   - `response.in_role`: czy wygenerowana odpowiedź wychodzi z roli persony (nowa kontrola, dziś nie istnieje).
   - `scammer.unmasking`: czy napastnik zorientował się, że rozmawia z botem (dziś 17 angielskich fraz, US-016).
   - `scammer.urgency`: poziom presji w wiadomości napastnika (dziś ~20 angielskich regexów z wagami, składnik risk score US-032).
4. Eval z CLI dla każdego węzła i bramki przejścia na `live` oparte na **prawdziwym tekście**, nie tylko syntetycznym.

## Non-goals (etap 2)

- Opóźnienie i wydajność Basala (decyzja właściciela).
- Profiler: bez zmian w logice, zostaje na GPT.
- Kontekst IOC („czy to adres, na który napastnik chce dostać pieniądze”) i faza wiadomości napastnika: etap 3, opisane niżej tylko jako kierunek.
- Personalizacja (`analyzers/personalization.py`): zostaje deterministyczna; zysk z Basala za mały.
- Walidator PII (`safety/output_validator.py`): zostaje deterministyczny, Basal go nie dotyka.
- Nowe kategorie ataku (`credential_phishing`): osobna decyzja produktowa, patrz „Poza planem”.

## Anti-goals (porażka, nawet jeśli „działa”)

- Basal sam **blokuje, przepisuje albo wysyła** odpowiedź. Kontrola roli tylko ostrzega człowieka, który zatwierdza wiadomość.
- Basal sam **kończy sesję**. Unmasking dalej tylko proponuje zakończenie (US-016).
- Basal **osłabia** istniejącą kontrolę: dla unmaskingu regex dalej działa, Basal może tylko dodać wykrycie.
- Przejście na `live` na podstawie samego syntetycznego zbioru. Lekcja z etapu 1: bramka 1 zaliczona, bramka 2 oblana.
- Wpis w `decisions`, z którego nie da się odczytać, co było referencją (regex czy LLM) i której wiadomości dotyczył.

## Jak to działa

### Tryb sygnału

Kaskada z etapu 1 zakłada, że gdy Basal nie jest pewny, decyduje LLM. W etapie 2 referencją jest regex, a Basal **dokłada** odpowiedź:

| Tryb | `response.in_role` | `scammer.unmasking` | `scammer.urgency` |
|---|---|---|---|
| `off` | brak kontroli (jak dziś) | tylko regex (jak dziś) | tylko regex (jak dziś) |
| `shadow` | Basal liczy i zapisuje, UI nic nie pokazuje | regex decyduje, Basal zapisany obok | regex decyduje, Basal zapisany obok |
| `live` | ostrzeżenie przy szkicu, gdy `breaks_role` ≥ próg | wykrycie = regex **lub** Basal `unmasked` ≥ próg | poziom z Basala ≥ próg, inaczej regex |

Gdy Basal jest niedostępny, przekroczy timeout albo bramka języka odrzuci tekst (`language.py`, PL/EN), węzeł wraca do zachowania z `off` i zapisuje `skip_reason`, tak jak w etapie 1.

### Węzły i pytania

**`response.in_role`** (opcje):
- `in_role`: odpowiedź brzmi jak persona, nie zdradza, że to bot ani że rozmowa jest pułapką.
- `breaks_role`: przyznaje się do bycia AI, odmawia, moralizuje, wspomina o scamie, policji lub CERT, przechodzi na ton asystenta albo mówi niezgodnie z personą (wiek, styl, wiedza).

Stan dla Basala: opis persony (typ, styl) i treść odpowiedzi. Uruchamiana po walidacji PII, na każdej wygenerowanej odpowiedzi, także po edycji przez użytkownika (US-008), jeśli edycja przechodzi przez backend.

**`scammer.unmasking`** (opcje): `unmasked` (zarzuca bycie botem, mówi, że wie, co się dzieje, kończy z irytacją) / `engaged` (dalej prowadzi scam). Uruchamiana tam, gdzie dziś `detect_unmasking` (`api/routers/response.py:333`).

**`scammer.urgency`** (opcje): `none` / `low` / `medium` / `high`, z opisami presji czasowej, gróźb i ostatecznych terminów. Mapowanie na skalę 0–10 risk score: wartość oczekiwana z rozkładu Basala (np. 0 / 3,3 / 6,7 / 10), a nie suma wag. **Liczona raz, przy zapisie wiadomości napastnika**, i przechowywana; `risk_score_service` czyta zapisane etykiety i liczy regexem tylko wiadomości bez etykiety. Dziś risk score jest liczony na żądanie ze wszystkich wiadomości, więc wołanie Basala przy każdym odczycie nie wchodzi w grę.

### UI

- `response.in_role` w `live`: ostrzeżenie przy szkicu odpowiedzi z krótkim powodem (opis wybranej opcji i `p`). Przycisk wysyłki / kopiowania działa dalej.
- `scammer.unmasking`: istniejąca propozycja zakończenia sesji pokazuje źródło wykrycia (fraza z regexu albo „Basal, p=…”).
- `scammer.urgency`: w rozbiciu risk score etykieta poziomu zamiast listy słów, gdy źródłem jest Basal.

## Dane

### `decisions` (migracja)

Tabela z etapu 1 zostaje. Dochodzi:
- `message_id` (nullable, FK do `messages`): której wiadomości dotyczy decyzja. Profiler zostawia `null`.
- Informacja o rodzaju referencji: `llm` (Profiler) albo `regex` (nowe węzły), z odpowiedzią referencji. Kolumny `llm_*` z etapu 1 zostają dla Profilera; sposób zapisu referencji regexowej (nowe kolumny vs. uogólnienie istniejących) zostaje budowniczemu, pod warunkiem że wiersz jest jednoznaczny bez zaglądania do kodu.
- `source` dopuszcza wartość `regex`, `node` nowe nazwy węzłów.

### Etykieta urgency przy wiadomości

Wynik `scammer.urgency` (poziom, rozkład, źródło) zapisany tak, żeby risk score mógł go odczytać bez ponownego wołania Basala. Miejsce (kolumna w `messages` czy odczyt z `decisions` po `message_id`) zostaje budowniczemu.

## Konfiguracja

- `BASAL_MODE_<WĘZEŁ>` nadpisuje globalny `BASAL_MODE`, tak jak `BASAL_THRESHOLD_<WĘZEŁ>` nadpisuje próg. Dotyczy też Profilera (`BASAL_MODE_PROFILER`).
- Progi per węzeł od początku, ustalane po evalu.
- Zmiana tylko przez `.env` i restart (jak w etapie 1).

## Dane do evalu (największe ryzyko etapu)

| Węzeł | Prawdziwy tekst | Skąd |
|---|---|---|
| `response.in_role` | odpowiedzi naszego Conversation Agenta | **pod kontrolą**: generowane z aplikacji dla wszystkich typów person i ataków; to jest rzeczywisty rozkład tego węzła. Przypadki `breaks_role` są w praktyce rzadkie, więc dochodzą przypadki syntetyczne, oznaczone jako syntetyczne i liczone w raporcie osobno. |
| `scammer.unmasking`, `scammer.urgency` | odpowiedzi napastników (druga i kolejne wiadomości) | **nieznane**: korpus Nazario ma tylko pierwsze e-maile, lokalna baza ma 3 sesje. Kandydaci do sprawdzenia: publiczne archiwa scambaitingu (np. 419eater), zbiory akademickie, sesje zbierane w aplikacji. Sprawdzić licencję każdego źródła. |

Etykiety: ten sam proces „na ślepo” co w etapie 1 (dwa niezależne subagenty Claude, trzeci przy niezgodności, `ambiguous` poza bramką). Ograniczenie podawane w raporcie: etykiety to zgoda modeli, a nie ekspert.

**Kryterium wyjścia z rekonesansu danych:** co najmniej 150 prawdziwych wiadomości napastników z licencją pozwalającą na użycie, w tym część po polsku. Jeśli się nie uda, unmasking i urgency zostają w `shadow`, dopóki aplikacja nie zbierze własnych sesji, a raport mówi to wprost.

## Eval (CLI)

`eval` z etapu 1 dostaje podkomendy dla nowych węzłów (`in_role`, `unmasking`, `urgency`) i źródła `fixtures` / `decisions`. Raport per węzeł:

- `in_role` i `unmasking`: precision / recall Basala dla klasy rzadkiej (`breaks_role`, `unmasked`) w funkcji progu, liczba wykryć, których regex nie ma (unmasking), liczba fałszywych alarmów, osobno PL i EN.
- `urgency`: zgodność z etykietą na skali porządkowej (MAE w poziomach, macierz pomyłek), porównanie z regexem, osobno PL i EN.
- Rozkład pewności i p50/p95 czasu Basala (informacyjnie).

## Bramki przejścia na `live` (per węzeł)

Liczby są punktem startowym, jak w etapie 1.

1. **Eval na prawdziwym tekście** (syntetyczny tylko uzupełnia):
   - `in_role`: recall `breaks_role` ≥ 90% przy fałszywych alarmach ≤ 10%.
   - `unmasking`: precision Basala ≥ 90% przy progu; regex OR Basal wykrywa więcej niż sam regex, a różnica jest widoczna na wiadomościach PL.
   - `urgency`: MAE ≤ 0,5 poziomu względem etykiet i nie gorzej niż regex na EN.
2. **Shadow:** co najmniej 30 decyzji węzła na prawdziwych sesjach, rozbieżności z regexem (albo, dla `in_role`, wszystkie `breaks_role`) przejrzane ręcznie (`eval <węzeł> --source decisions`).

## Kolejność

| Faza | Zakres | Zależności |
|---|---|---|
| 0 | Wyniki etapu 1 dopisane do specu etapu 1; `BASAL_MODE_PROFILER` | — |
| A | Tryb sygnału, tryb per węzeł, migracja `decisions`, szkielet evalu dla nowych węzłów | 0 |
| R | Rekonesans danych napastników (równolegle od początku) | — |
| B | `response.in_role` end to end: węzeł, UI, zbiór, eval, shadow | A |
| C | `scammer.unmasking` + `scammer.urgency`: wspólny zbiór, węzły, zapis etykiety urgency, UI, eval, shadow | A, R |

`in_role` idzie pierwszy, bo jego dane są pod kontrolą; unmasking i urgency czekają na rekonesans i dzielą jeden zbiór.

## Testy

- Tryb sygnału: każdy węzeł w każdym trybie, w tym fallback do regexu przy `unavailable`, `timeout`, `language`. Unmasking w `live`: regex wykrył, Basal nie → wykrycie zostaje.
- Tryb per węzeł: nadpisanie globalnego trybu, Profiler w `off` przy nowych węzłach w `live`.
- Urgency: etykieta liczona raz przy zapisie, risk score jej używa i nie woła Basala; wiadomość bez etykiety liczona regexem.
- Eval: metryki na ręcznie policzonym małym zbiorze dla każdego węzła.
- Istniejące testy przechodzą bez zmian przy `BASAL_URL=""`.

## Mapowanie na PRD

Pierwotne US-050 (kontrola bezpieczeństwa) wraca jako `response.in_role`. Nowe US od US-056: tryb sygnału i tryb per węzeł, unmasking przez Basala, urgency przez Basala. US-051 (ocena IOC) zostaje w etapie 3. Aktualizacja `.ai/prd.md` jest częścią pracy.

## Etap 3 (kierunek, nie zakres)

- `ioc.context`: czy wyciągnięty IOC to miejsce, na które napastnik chce dostać pieniądze, czy wzmianka / cytat / adres legalnej firmy. Zasila jakość IOC (US-040). Wymaga wiadomości napastników z IOC, więc korzysta z rekonesansu R.
- `scammer.phase`: faza wiadomości (budowanie zaufania / prośba o dane / prośba o płatność / dane do płatności / groźba / pożegnanie). Budować dopiero, gdy pojawi się odbiorca, np. oś czasu sesji.

## Poza planem (znalezione przy bramce 2, osobne zadania)

- **Błąd 500:** gdy Conversation Agent trzy razy nie przejdzie walidacji PII (e-mail #116 z korpusu, naruszenie `ssn`), cały `/api/v1/classification/analyze` zwraca 500 i zostawia pustą sesję, choć klasyfikacja się udała.
- **Prawdopodobnie fałszywe `ssn`** w tym samym przypadku: do sprawdzenia w regexie walidatora.
- **Luka w taksonomii:** ~połowa prawdziwego phishingu to wyłudzanie danych logowania; gpt-5.1 rozkłada je między `tech_support` i `fake_invoice`. Kandydat na kategorię `credential_phishing`.

## Zostawione budowniczemu

- Układ kodu trybu sygnału (rozszerzenie `DecisionService` czy osobna klasa) i nazwy.
- Schemat zapisu referencji regexowej i etykiety urgency (z warunkami opisanymi wyżej).
- Treść opisów opcji dla Basala (z docstringów detektorów i promptu Conversation Agenta).
- Format stanu dla `in_role` (jak podać personę Basalowi).
- Wygląd ostrzeżeń w UI w ramach istniejących komponentów.
