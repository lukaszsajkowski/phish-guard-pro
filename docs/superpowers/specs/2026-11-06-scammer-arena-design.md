# Faza 1.1: Scammer Arena

Data: 2026-11-06. Punkt 1.1 mapy drogowej projektu (wraz z tą częścią 1.2, która wynika z tego samego przebiegu).

## Po co

PhishGuard nie ma dziś pomiaru, który pokazywałby, czy aktywna obrona działa: czy persona wyciąga od oszusta dane płatności, jak szybko, jak często oszust rozpoznaje bota i ile to kosztuje. Bez tego każda zmiana promptu lub grafu to zgadywanie.

Scammer Arena to harness eksperymentalny: toczy automatyczne rozmowy PhishGuard z oszustem granym przez LLM i mierzy wynik. Efektem jest plik `EVALS.md` w katalogu głównym repo.

**Obraz docelowy (decyzja właściciela).** `EVALS.md` zaczyna się od:

1. **Jednej tabeli „PhishGuard vs sam LLM bez grafu”** na tych samych scenariuszach. Kolumny: odsetek wydobytych sekretów, średnia liczba tur do pierwszego sekretu, jak często oszust wykrył bota, koszt jednej rozmowy.
2. Pod tabelą **krótkiego fragmentu prawdziwej rozmowy**, w której persona wyciąga od oszusta IBAN (albo inny sekret).
3. Zaraz pod spodem **uczciwych zastrzeżeń**, w tym że symulacja to nie produkcja.

Tabela i fragment rozmowy mają być zrozumiałe bez czytania kodu. Dalsza część pliku i surowe dane pozwalają prześledzić każdą liczbę do konkretnej rozmowy.

## Stan wyjściowy (sprawdzony 2026-11-06)

- Dwa grafy LangGraph w `backend/src/phishguard/orchestrator/graph.py`:
  - `create_phishguard_graph()`: `classify_email → extract_intel_from_email → select_persona`;
  - `create_continuation_graph()`: `add_scammer_message → extract_intel → generate_response → validate_safety → (regeneracja do 3 razy) → add_bot_response`.
- API (`api/routers/response.py`) woła graf kontynuacji z checkpointerem Postgres. Każde wywołanie to jedna odpowiedź bota. Pierwsza odpowiedź na maila też idzie tą drogą, z pustą historią.
- Router wykrywa demaskowanie (US-016) przez `phishguard.safety.detect_unmasking(message)` na wiadomości oszusta. Ta funkcja nie jest węzłem grafu.
- `select_persona` tworzy `PersonaEngine()` bez seeda (`orchestrator/nodes.py:82`). `PersonaEngine(seed=...)` już przyjmuje seed.
- Istnieje CLI ewaluacji profilera (`python -m phishguard.decisions.eval`) z wzorcem do naśladowania:
  - błąd pojedynczego przypadku jest zapisywany i przebieg leci dalej;
  - nic nie trafia do Supabase (`session_id=None`).
- Koszty liczy `decisions/eval/metrics.py`: `llm_cost_usd`, `PRICES_PER_MTOK`, gdzie `gpt-6-luna` kosztuje $0.10/$0.50 za 1M tokenów.
- Zależności już są w `pyproject.toml`:
  - `faker`, `phonenumbers`, `matplotlib` jako zależności bezpośrednie;
  - `pyyaml` w lockfile tylko pośrednio.

## Cele

1. Jedna komenda uruchamia 24 scenariusze × 2 systemy × 3 powtórzenia, czyli 144 rozmowy, i zapisuje wszystkie wyniki na dysk.
2. Druga komenda generuje z zapisanych wyników `EVALS.md` i wykres, bez ponownych wywołań API.
3. Każda liczba w `EVALS.md` da się prześledzić do konkretnych plików rozmów w repo.
4. Arena testuje **prawdziwy kod produkcyjny**: te same grafy, prompty, ekstrakcję IOC i warstwę bezpieczeństwa, z których korzysta aplikacja.

## Decyzje właściciela

- **Co jest testowane.** Arena uruchamia oba produkcyjne grafy bezpośrednio w Pythonie, bez API, frontendu i Supabase, ze stanem w pamięci.
  - Zatwierdzenie odpowiedzi przez człowieka zastępuje automat: odpowiedź idzie dalej bez edycji.
  - Gdy warstwa bezpieczeństwa zablokuje szkic odpowiedzi, liczymy to jako zdarzenie bezpieczeństwa. Rozmowa toczy się dalej na wersji, którą graf ostatecznie wypuścił.
- **Baseline.** Ten sam model i ta sama persona, ale jedno zwykłe wywołanie LLM na turę, z prostym promptem ofiary. Nie ma grafu, ekstrakcji IOC sterującej rozmową ani warstwy bezpieczeństwa. Różnica wyników ma mierzyć wartość grafu, a nie różnicę modeli.
- **Scenariusze.** 24 sztuki:
  - **16 po angielsku:** każdy z 8 typów, które PhishGuard rozpoznaje (`AttackType` bez `not_phishing`: 419, CEO fraud, fake invoice, romance, tech support, lottery, crypto investment, credential phishing), w dwóch wariantach, łatwiejszy i trudniejszy oszust;
  - **8 po polsku:** OLX/Allegro „dopłata do paczki”, BLIK, fałszywy przelew, inwestycje krypto (po dwa warianty).
  - Każdy scenariusz to plik YAML:
    - treść pierwszego maila;
    - opis postaci oszusta;
    - od 2 do 3 sekretów z warunkami ujawnienia;
    - limit **10 tur**.
  - Wszystkie dane są fikcyjne, ale mają poprawny format.
- **Model.** `gpt-6-luna` po obu stronach: ofiara (PhishGuard i baseline) oraz oszust. `EVALS.md` mówi wprost, że ten sam model po obu stronach może zawyżać wyniki. Inny model oszusta to rozszerzenie na później.
- **Powtórzenia.** Każdy scenariusz 3 razy dla każdego systemu. W tabeli: średnia i rozrzut (min–max).
  - Stały seed persony per scenariusz, żeby oba systemy grały tę samą ofiarę.
  - Każda rozmowa jest zapisywana do JSON.
  - Fragment rozmowy w `EVALS.md` pochodzi z prawdziwego przebiegu.
- **Zakres 1.1:**
  - Arena;
  - 24 scenariusze;
  - przebieg baseline;
  - zapis rozmów;
  - `EVALS.md` z tabelą i fragmentem rozmowy;
  - metryki, które wynikają z samego przebiegu (sekcja „Metryki”).
- **Poza zakresem 1.1:**
  - spójność persony przez LLM-as-judge (1.2, wymaga ręcznej kalibracji);
  - uruchamianie w CI (1.3);
  - porównanie regex vs LLM w ekstrakcji (1.6).

  Arena ma być zbudowana tak, żeby te punkty dało się podpiąć bez przeróbek.
- **Komendy i pliki:**
  - `uv run python -m phishguard.arena run` zapisuje wyniki do `evals/results/<data>/`: każda rozmowa jako osobny JSON plus plik podsumowania;
  - `uv run python -m phishguard.arena report` tworzy `EVALS.md` w katalogu głównym i jeden wykres słupkowy PNG „PhishGuard vs baseline”;
  - do repo trafiają wyniki, wszystkie 144 rozmowy, wykres i `EVALS.md`.

## Jak przebiega jedna rozmowa

Jedna rozmowa to para (scenariusz, system, powtórzenie).

1. **Przygotowanie (wspólne dla obu systemów w danym scenariuszu i powtórzeniu).**
   - Uruchom `create_phishguard_graph()` na mailu ze scenariusza, z `session_id=None` i bez zapisu do bazy. Daje to klasyfikację, IOC z maila i personę.
   - Persona powstaje z seeda wyprowadzonego deterministycznie z identyfikatora scenariusza.
   - Klasyfikację i personę zapisujemy w wyniku. Baseline dostaje tę samą personę.
2. **Pierwsza odpowiedź ofiary** na maila, z pustą historią, tak jak w API.
   - PhishGuard: `create_continuation_graph()` bez wiadomości oszusta.
   - Baseline: jedno wywołanie LLM.
3. **Tura:**
   - oszust (LLM) dostaje swój opis, sekrety z warunkami i dotychczasową rozmowę, po czym zwraca wiadomość;
   - na wiadomości oszusta uruchamiamy `detect_unmasking` (dla obu systemów, to tylko analiza tekstu);
   - ofiara odpowiada (PhishGuard przez graf kontynuacji, baseline jednym wywołaniem).
4. **Koniec rozmowy:** po 10 turach albo wcześniej, gdy oszust zakończy rozmowę, np. bo uznał, że rozmawia z botem, albo się zniechęcił. Wydobycie wszystkich sekretów **nie** kończy rozmowy, bo długość zaangażowania (tarpitting) to też wynik.

Turą nazywamy parę „wiadomość oszusta + odpowiedź ofiary”. Pierwsza odpowiedź na maila to tura 0.

## Oszust

Oszusta gra LLM. W każdej turze zwraca strukturę (structured output) z polami:

- `message`: treść wiadomości do ofiary;
- `revealed_secret_ids`: które sekrety właśnie ujawnił, według niego samego;
- `suspects_bot`: czy podejrzewa, że rozmawia z botem lub AI;
- `ends_conversation`: czy kończy rozmowę.

Prompt oszusta mówi mu:

- kim jest;
- jaki ma cel;
- że sekrety ujawnia **tylko** przy spełnieniu warunku;
- że ma reagować realistycznie, czyli zniechęcać się, naciskać i podejrzewać bota, gdy ofiara zachowuje się nienaturalnie.

Trudniejszy wariant scenariusza ma ostrzejsze warunki ujawnienia i bardziej podejrzliwego oszusta.

## Format scenariusza

`evals/scenarios/<id>.yaml`. Pola:

- `id`, `language` (`en`/`pl`), `attack_type` (wartość `AttackType`), `difficulty` (`easy`/`hard`);
- `email`: pierwszy mail od oszusta;
- `scammer`: opis postaci, stylu i celu;
- `secrets`: lista z `id`, `type` (`iban`/`btc`/`url`/`phone`, zgodnie z typami IOC aplikacji), `value` i `reveal_when` (warunek opisowy dla LLM oszusta);
- `known_iocs`: inne wskaźniki, które legalnie występują w scenariuszu, np. link w samym mailu. Wyciągnięcie ich przez PhishGuard nie jest fałszywym trafieniem.
- `max_turns`: domyślnie 10.

Dane muszą być fikcyjne i poprawne formalnie:

- IBAN z prawidłową sumą kontrolną;
- adresy BTC przechodzące walidację formatu aplikacji;
- telefony przechodzące `phonenumbers`;
- domeny URL nienależące do nikogo realnego.

Ładowanie scenariusza waliduje to wszystko i odrzuca plik z błędem.

## Metryki

Dla obu systemów, chyba że zaznaczono inaczej.

| Metryka | Definicja |
|---|---|
| **Odsetek wydobytych sekretów** (odpowiednik IDR) | Sekrety ujawnione w rozmowie / wszystkie sekrety scenariusza. Ujawnienie rozpoznajemy po wartości sekretu w treści wiadomości oszusta (po normalizacji: spacje, wielkość liter), a nie po deklaracji oszusta. Deklarację zapisujemy obok jako sygnał pomocniczy. |
| **Tury do pierwszego sekretu** (IDS) | Numer tury z pierwszym ujawnionym sekretem. Rozmowy bez ujawnienia nie wchodzą do średniej; podajemy osobno, ile ich było. |
| **Wykrycie bota** | Odsetek rozmów, w których oszust choć raz ustawił `suspects_bot`. Obok pomocniczo: odsetek rozmów, w których `detect_unmasking` zgłosił demaskowanie. |
| **Długość zaangażowania** | Liczba tur do końca rozmowy. |
| **Koszt i czas rozmowy** | Tokeny i koszt **strony ofiary** (`llm_cost_usd`), czas wywołań. Koszt oszusta liczymy osobno i nie wchodzi do porównania. |
| **Ekstrakcja IOC** (tylko PhishGuard) | Recall: ujawnione sekrety, które znalazły się w `extracted_iocs` / ujawnione sekrety. Precision: wyciągnięte IOC pasujące do sekretów lub `known_iocs` / wszystkie wyciągnięte IOC. |
| **Bezpieczeństwo** (tylko PhishGuard) | Liczba tur, w których `validate_safety` odrzuciło szkic. Liczba odpowiedzi, które mimo to wyszły jako niebezpieczne (oczekiwane 0). |

Agregacja: każda metryka liczona per powtórzenie (średnia po 24 scenariuszach), w tabeli średnia z 3 powtórzeń i min–max. Różnicę PhishGuard vs baseline opisujemy jako „w granicach szumu”, gdy zakresy min–max się nakładają. To prosta i uczciwa reguła bez udawania statystyki na n=3.

## `EVALS.md`

Generowany w całości z wyników. Zawiera, w tej kolejności:

1. Tabela główna (4 kolumny z obrazu docelowego, PhishGuard vs baseline, średnia i min–max).
2. Wykres słupkowy PNG z tymi samymi metrykami.
3. Fragment rozmowy PhishGuard z ujawnieniem sekretu, czyli kilka wiadomości wokół ujawnienia, z linkiem do pełnego JSON.
4. Zastrzeżenia:
   - symulacja to nie produkcja;
   - ten sam model po obu stronach;
   - n = 24 scenariusze × 3 powtórzenia;
   - dane fikcyjne;
   - porównanie z literaturą (Siadati i in., Puppeteer) jest tylko orientacyjne.
5. Metoda: jak działa Arena, czym jest baseline, definicje metryk, data i commit przebiegu, model.
6. Wyniki szczegółowe:
   - tabela per scenariusz;
   - podział EN/PL;
   - ekstrakcja IOC i bezpieczeństwo dla PhishGuard;
   - liczba rozmów nieważnych lub z błędem.
7. Jak odtworzyć: dwie komendy i wymagany klucz.

Język `EVALS.md`: angielski, jak README, bo czytelnik może nie znać polskiego.

## Ograniczenia

- Testy jednostkowe Areny nie wołają API. LLM jest podmieniany atrapą, a w CI nie ma klucza. Arena nie zmienia wymaganych checków CI.
- Arena nie pisze do Supabase i nie wymaga działającej bazy.
- Zmiany w kodzie produkcyjnym tylko tam, gdzie Arena tego potrzebuje (np. możliwość podania seeda persony), bez zmiany zachowania aplikacji.
- Brak sekretów i prawdziwych danych osobowych w scenariuszach, wynikach i testach (AGENTS.md).
- Pełny przebieg ma kosztować około $1. Komenda `run` ma flagi do ograniczenia przebiegu (pojedynczy scenariusz, liczba powtórzeń, sam PhishGuard albo sam baseline), żeby dało się tanio sprawdzić zmianę.

## Moje decyzje (do sprawdzenia przez właściciela)

- **Baseline zna cel.** Prompt baseline mówi ofierze nie tylko „udawaj tę osobę”, ale też jednym akapitem, że ma podtrzymywać rozmowę i nakłonić oszusta do podania danych płatności. Bez tego porównanie byłoby z góry ustawione na korzyść PhishGuard i podważałoby wynik.
- **Ujawnienie sekretu wykrywamy po wartości w tekście, a nie po deklaracji oszusta.** LLM oszusta może się mylić w deklaracjach; wartość w treści jest twardym faktem.
- **Odmowy modelu.** Gdy model odmówi zagrania oszusta albo ofiary, ponawiamy próbę raz. Przy kolejnej odmowie rozmowa jest oznaczana jako nieważna z powodem i wyłączana z metryk, a jej liczbę podajemy w `EVALS.md`. Gdy nieważnych jest więcej niż 10%, raport mówi to na samej górze.
- **Błędy API.** Błąd zapisujemy w rozmowie i przebieg leci dalej, tak jak w istniejącym CLI ewaluacji.
- **Wybór fragmentu rozmowy.** Raport sam wybiera rozmowę PhishGuard z najwcześniejszym ujawnieniem IBAN-u (a w razie braku dowolnego sekretu). Flaga komendy `report` pozwala wskazać inną rozmowę ręcznie.
- **Klasyfikacja raz na scenariusz, na żywo.** Profiler (prawdziwy kod) klasyfikuje maila raz na scenariusz. Ta sama klasyfikacja i persona służą wszystkim 3 powtórzeniom i obu systemom, więc powtórzenia mierzą to samo.
  - Typ ataku z profilera porównujemy z `attack_type` scenariusza. Zgodność klasyfikacji podajemy w wynikach szczegółowych.
  - Gdy profiler zwróci `not_phishing`, scenariusz jest oznaczany jako nieważny z tym powodem. Nie podmieniamy wyniku profilera, bo to też jest wynik.
- **Warstwa Basal wyłączona.** Arena wymusza tryb `off` niezależnie od `BASAL_MODE`, czyli odpowiada sam LLM. Daje to powtarzalność i nie wymaga lokalnej usługi Basal.
- **Zdarzenia bezpieczeństwa liczymy u źródła.** Właściwa pętla walidacji i regeneracji działa w `ConversationAgent.generate_response`, a nie w węźle `validate_safety`. Arena liczy więc regeneracje wewnątrz agenta. Wymaga to małej zmiany produkcyjnej: wystawienia licznika regeneracji w stanie grafu, bez zmiany zachowania.
  - Gdy agent wyczerpie próby i zgłosi `ResponseGenerationError`, tura kończy rozmowę jako „zablokowana przez bezpieczeństwo”. Liczymy ją osobno, a nie jako błąd API.
- **Tokeny zbieramy w Arenie.** `record_llm_usage` zapisuje tokeny tylko przy `session_id`, a Arena działa bez niego. Arena zbiera użycie tokenów sama (np. przez opakowanie klienta LLM), bez zapisu do bazy.
- **`pyyaml`** dopisujemy jako zależność bezpośrednią, bo dziś jest tylko pośrednia.
- **Kod Areny** mieszka w `backend/src/phishguard/arena/`, a scenariusze i wyniki w `evals/` w katalogu głównym repo, obok `EVALS.md`.

## Zostawione budowniczemu

- Treść promptów oszusta i baseline (w ramach decyzji powyżej).
- Dokładny kształt JSON rozmowy i podsumowania. Rozmowa musi zawierać:
  - wszystkie wiadomości;
  - stan PhishGuard po każdej turze (IOC, zdarzenia bezpieczeństwa, thinking);
  - deklaracje oszusta;
  - tokeny i czasy;
  - wersję scenariusza;
  - commit kodu.
- Jak podać seed persony do `select_persona` przy zachowaniu obecnego zachowania API.
- Treść 24 scenariuszy w ramach podziału i formatu.
- Wygląd wykresu: ma być czytelny w jasnym i ciemnym motywie GitHuba.
- Kolejność i współbieżność wywołań w przebiegu.

## Kryteria akceptacji

1. `evals/scenarios/` zawiera 24 scenariusze w ustalonym podziale. Wszystkie przechodzą walidację formatu i fikcyjności danych.
2. `phishguard.arena run` wykonuje pełny przebieg i zapisuje 144 rozmowy (lub mniej przy flagach) plus podsumowanie.
3. `phishguard.arena report` z samych plików wyników generuje `EVALS.md` i wykres. Dwa uruchomienia na tych samych wynikach dają identyczne pliki.
4. Testy jednostkowe z atrapą LLM pokrywają:
   - pętlę rozmowy, w tym koniec przez limit i przez oszusta;
   - wykrywanie ujawnienia sekretów;
   - liczenie metryk na ręcznie przygotowanych rozmowach;
   - obsługę odmów i błędów;
   - walidację scenariuszy;
   - generowanie raportu z fikcyjnych wyników.
5. Pierwszy prawdziwy przebieg jest zacommitowany razem z `EVALS.md`, wykresem i rozmowami.
6. Zastrzeżenia i definicje metryk w `EVALS.md` zgadzają się z tym spec.
