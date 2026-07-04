# TESTING_STRATEGY.md

Testing strategy for **RAE – Reflective Agentic-memory Engine**

Celem tego dokumentu jest opisanie **praktycznego, ale profesjonalnego** podejścia do testowania RAE:
- tak, żeby projekt był **bezpieczny i przewidywalny**,
- ale jednocześnie **nie zamienił się w laboratorium testów dla samych testów**.

---

## 1. Goals & Principles

1. **Protect the core logic**  
   Najwyższy priorytet mają moduły odpowiedzialne za:
   - pamięć (wszystkie warstwy),
   - orkiestrację zadań,
   - cost-guard / billing / limity,
   - integrację z modelami (LLM / RAG), która może powodować duże koszty lub „brzydkie” efekty dla użytkownika.

2. **Favour fast feedback**  
   - Lokalny cykl dev: szybkie testy (`pytest --no-cov` na wybranym module).
   - CI: pełna suite + coverage + jakościowe bramki.

3. **Measure quality, not just quantity**  
   - Line / branch coverage to minimum,
   - **diff coverage** dla nowego kodu,
   - **mutation testing** na krytycznych modułach.

4. **Stable, deterministic tests**  
   - Brak „flaky” testów (zależnych od czasu, sieci, losowości bez seedów).
   - Zewnętrzne usługi **mockowane / stubowane** (LLM, bazy zewnętrzne, API partnerów).

---

## 2. Test Pyramid for RAE

RAE stosuje klasyczną „piramidę testów”:

1. **Unit tests (podstawa)**  
   - Testują pojedyncze funkcje / klasy, **bez I/O / sieci / realnej bazy**.
   - Obejmują:
     - logikę pamięci (agregacje, scoring, wybór kontekstu),
     - transformacje danych (normalizacja, mapowanie typów, walidacja),
     - logikę decyzyjną (np. wybór strategii na podstawie parametrów).

2. **Integration tests**  
   - Testują współdziałanie kilku komponentów:
     - API ↔ warstwa logiki ↔ pamięć / DB,
     - task scheduler ↔ worker ↔ kolejka,
     - cost-guard ↔ LLM client ↔ storage.
   - Korzystają albo z:
     - lekkiej, tymczasowej bazy (np. SQLite / testowy Postgres w kontenerze),
     - albo fixture'ów uruchamiających mini-stack (np. docker compose do testów).

3. **End-to-End / Smoke tests**  
   - Minimalny scenariusz „od początku do końca”, np.:
     - „RAE przyjmuje zadanie → zapisuje kontekst → wybiera pamięć → generuje odpowiedź → loguje efekty”.
   - Celem jest potwierdzenie, że **podstawowy przepływ nie jest zepsuty** po zmianach.

---

## 3. Tooling

RAE używa następujących narzędzi testowych (rekomendowane):

- **pytest** – główny runner testów.
- **pytest-cov** – raporty pokrycia (line + opcjonalnie branch coverage).
- **Hypothesis** (property-based testing) – dla parsowania, transformacji, walidacji.
- **Mutation testing**:
  - rekomendowany **mutmut** lub **Cosmic Ray** dla krytycznych modułów.
- **diff-cover** (lub podobne narzędzie) – analiza pokrycia *nowych* zmian w PR.

Dodatkowo (jako część „quality gate”):

- **mypy** / type checking,
- **ruff / flake8** – linting,
- **black** – formatowanie.

---

## 4. Coverage Policy

### 4.1. Global Coverage (CI)

- **Minimalny próg globalny**:  
  Obecnie: `cov-fail-under = 48` (stan projektowy)  
  **Docelowo:** podnoszony stopniowo do **60–70%**, bez wymuszania 100% na całości.

- Globalny próg jest:
  - egzekwowany w **pełnym runie CI** (`pytest` bez ograniczania do jednego modułu),
  - **nie** używany przy lokalnym debugowaniu pojedynczych testów.

### 4.2. Diff Coverage (new code)

Dla pull requestów / nowych commitów:

- **Minimalny diff coverage dla nowego kodu:**  
  Rekomendacja: **≥ 80%** (nowe / zmodyfikowane linie).
- Narzędzie: `diff-cover` odpalane po `pytest --cov`.

To pozwala:
- nie dławić się historycznym długiem technicznym,
- a jednocześnie wymuszać wysoką jakość **nowych** fragmentów.

### 4.3. Branch Coverage

- Włączone stopniowo dla modułów, gdzie istotne są rozgałęzienia logiki (np. routing decyzji, cost-guard).
- Nie jest wymagane globalnie na start projektu, ale docelowo:
  - dla krytycznych modułów: **branch coverage ≥ 80%**.

---

## 5. What to Test Where (by module type)

### 5.1. Memory / Reasoning / Reflective Layer

**Unit tests:**
- scoring i ranking kandydatów,
- logika wyboru pamięci (episodic / semantic / reflective),
- reguły dotyczące limitów tokenów, windowingu, łączenia kontekstów.

**Integration tests:**
- interakcje pamięci z bazą (Postgres / Qdrant / Redis),
- zapis i odczyt wpisów pamięci, w tym:
  - wersjonowanie,
  - TTL / polityki odrzucania / kompresji.

**Mutation testing (wysoki priorytet):**
- funkcje decyzyjne, które wybierają, co trafia do promptu / reflekcji.

---

### 5.2. Cost-Guard / Budgeting / Limits

**Unit tests:**
- przeliczanie kosztów,
- limity na użytkownika / tenant / zadanie,
- logika alerta i odcinania dalszych calli przy przekroczeniu limitu.

**Integration tests:**
- wpisywanie logów kosztów do storage (DB / log store),
- współdziałanie z LLM clientem (mock / fake).

**Mutation testing (wysoki priorytet):**
- wszystkie warunki `>`, `<`, `>=` w logice limitów,
- flagi „czy pozwolić na droższą operację?”.

---

### 5.3. LLM / RAG Clients

**Unit tests:**
- generowanie payloadów,
- mapowanie odpowiedzi z providerów do wewnętrznych struktur.

**Integration tests:**
- symulowane (mockowane) odpowiedzi LLM,
- obsługa błędów, timeoutów, retry.

**Zasada:**  
Brak realnych calli do modelu w testach – tylko mocki / fake clients.

---

### 5.4. Orchestration / Pipelines / Tasks

**Unit tests:**
- logika decompozycji zadań na subtaski,
- reguły priorytetyzacji i kolejkowania.

**Integration tests:**
- flow: API → scheduler → worker → zapis wyników,
- testy z wykorzystaniem testowego brokera (np. Redis / in-memory queue).

**E2E / Smoke:**
- minimalny scenariusz „zadanie wchodzi do systemu i wychodzi z wynikiem”.

---

## 6. Mutation Testing Policy

**Cel:** sprawdzić, czy testy są w stanie „zabić” proste błędy, a nie tylko przechodzić szczęśliwe ścieżki.

### 6.1. Scope

Mutation testing nie jest odpalane globalnie na cały projekt w każdym buildzie.  
Obowiązuje:

- **Krytyczne moduły:**
  - pamięć / reasoning,
  - cost-guard,
  - kluczowe transformacje danych.
- Pozostałe moduły – tylko ad-hoc, gdy pojawia się podejrzenie słabych testów.

### 6.2. Schedule

- **Lokalnie / ad-hoc:**  
  Developer może odpalić `mutmut` / `cosmic-ray` na wybranym module przy większej refaktoryzacji.
- **CI (opcjonalnie):**
  - dedykowany job (np. nightly / weekly) dla wybranych pakietów,
  - wyniki jako raport, **bez blokowania** merge’a na starcie projektu.

---

## 7. Property-Based Testing (Hypothesis)

Property-based tests są używane tam, gdzie:

- są **wejścia o dużej wariancji**, a my chcemy uniknąć ręcznego wypisywania wszystkich przypadków, np.:
  - parsowanie tekstu / promptów / JSON,
  - transformacje danych wejściowych / wyników modeli,
  - walidacja parametrów.

Zasady:

- Hypothesis **nie zastępuje** klasycznych testów – uzupełnia je.
- Każdy test property-based musi mieć jasno opisaną „własność”, np.:
  - „operacja jest idempotentna”,
  - „wynikowa struktura zachowuje wymagane invariants”.

---

## 8. Handling External Dependencies

Zasada ogólna: **testy są deterministyczne i nie sieciowe.**

- LLM / API providerzy:
  - używamy mocków/fake’ów z predefiniowanymi odpowiedziami,
  - testujemy mapowanie błędów (timeout, 4xx, 5xx) na logikę RAE.
- Bazy danych:
  - unit testy: brak realnej bazy (tylko in-memory struktury / mocki),
  - integration: tymczasowa baza (np. docker w CI, testcontainers).
- Kolejki / brokerzy:
  - dla unit: mock,
  - dla integration: test instance.

---

## 9. CI Pipeline Integration

### 9.1. Local Developer Workflow

Rekomendowany schemat:

1. Szybkie testy w trakcie pracy:
   ```bash
   pytest --no-cov path/to/module_or_tests
Przed pushem / większym commitem:

bash
Skopiuj kod
pytest
(pełna suite lokalnie, jeśli rozsądny czas wykonania).

Okresowo / przy zmianach w krytycznym module:

bash
Skopiuj kod
mutmut run  # lub odpowiednik
mutmut results
9.2. CI Stages (przykład)
Lint & type check

ruff, mypy, black --check.

Tests + coverage

pytest --cov=...

global coverage ≥ min threshold (np. 48–60%).

Diff coverage

analiza pokrycia nowego kodu,

diff coverage ≥ 80% (wartość do doprecyzowania).

Optional / scheduled:

mutation testing job (np. mutmut na krytycznych modułach),

raport w artefaktach / dashboardzie.

10. Developer Expectations
Przy dodawaniu / modyfikowaniu kodu:

Każda istotna zmiana w logice:

ma odpowiadający unit test,

jeśli dotyczy integracji – także integration test.

PR bez testów jest akceptowalny tylko, gdy:

dotyczy czystej dokumentacji / komentarzy,

lub drobnych zmian kosmetycznych, które nie dotykają logiki.

Gdy test jest trudny do napisania:

należy to uzasadnić w opisie PR,

i rozważyć, czy nie jest to sygnał do poprawy architektury (np. zbyt mocne sprzężenie).

11. Pragmatic Limits & Non-Goals
Celem nie jest:

osiągnięcie 100% coverage na całym projekcie,

odpalanie mutation testingu na wszystkim przy każdym PR,

perfekcja formalna kosztem dowożenia funkcji.

Celem jest:

mieć wysoką pewność jakości tam, gdzie błąd najbardziej boli,

mieć testy, które są:

szybkie,

stabilne,

zrozumiałe dla kolejnych osób w projekcie,

stopniowo podnosić poziom jakości, gdy projekt dojrzewa.