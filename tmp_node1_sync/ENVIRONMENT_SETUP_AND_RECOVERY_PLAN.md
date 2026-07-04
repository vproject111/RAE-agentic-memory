# Przewodnik Konfiguracji Środowiska i Plan Naprawy Testów

Ten dokument opisuje kroki niezbędne do skonfigurowania lokalnego środowiska programistycznego od zera oraz przedstawia plan naprawy dla istniejących błędów w testach.

## 1. Konfiguracja Środowiska Programistycznego

Celem jest postawienie w pełni funkcjonalnego środowiska do pracy z RAE, włączając w to bazę danych, usługi i zależności Pythona.

### Krok 1: Wymagania Wstępne

- **Python:** Upewnij się, że masz zainstalowanego Pythona w wersji 3.10 lub nowszej.
- **Docker & Docker Compose:** Niezbędne do uruchomienia usług takich jak baza danych PostgreSQL i Ollama.

### Krok 2: Konfiguracja Zmiennych Środowiskowych

Projekt używa plików `.env` do zarządzania konfiguracją.

1.  **Główna konfiguracja Docker:** Skopiuj `.env.docker` do `.env`, jeśli nie istnieje. Ten plik zawiera podstawowe dane logowania do bazy danych i konfigurację usług.
    ```bash
    cp .env.docker .env
    ```
2.  **Konfiguracja testowa:** Skopiuj `.env.example` do `.env.test`. Ten plik będzie używany podczas uruchamiania testów. Będziesz musiał uzupełnić go o klucze API do usług zewnętrznych, jeśli chcesz w pełni testować ich integracje.
    ```bash
    cp .env.example .env.test
    ```

### Krok 3: Wirtualne Środowisko Pythona

1.  **Utwórz wirtualne środowisko:**
    ```bash
    python -m venv .venv
    ```
2.  **Aktywuj środowisko:**
    -   Linux/macOS: `source .venv/bin/activate`
    -   Windows: `.venv\Scripts\activate`

### Krok 4: Instalacja Zależności

1.  **Zainstaluj główne zależności aplikacji:**
    ```bash
    pip install -r apps/memory_api/requirements.txt
    ```
2.  **Zainstaluj zależności deweloperskie i testowe:**
    ```bash
    pip install -r requirements-dev.txt
    ```
3.  **Zainstaluj lokalne pakiety w trybie edytowalnym:** To kluczowy krok, który sprawia, że zmiany w kodzie `rae-core` i `sdk` są natychmiast widoczne w środowisku.
    ```bash
    pip install -e ./rae-core
    pip install -e ./sdk/python/rae_memory_sdk
    ```

### Krok 5: Uruchomienie Usług w Dockerze

Projekt korzysta z Docker Compose do zarządzania kontenerami deweloperskimi.

1.  **Zbuduj i uruchom kontenery:** Użyj poniższej komendy, aby uruchomić bazę danych, API i inne niezbędne usługi.
    ```bash
    docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d
    ```
2.  **Sprawdź status kontenerów:**
    ```bash
    docker compose ps
    ```
    Powinieneś zobaczyć działające kontenery, w tym `postgres_db`, `api` i `ollama`.

## 2. Plan Naprawy Testów

Po poprawnym skonfigurowaniu środowiska, uruchomienie testów (`.venv/bin/pytest`) ujawnia kilka błędów. Poniżej znajduje się plan ich naprawy.

### Problem 1: Niezgodność Schematu Bazy Danych (`tenant_id`)

-   **Błąd:** `AssertionError: Database Schema Violation Detected! - TYPE_MISMATCH: Column 'tenant_id' expected TEXT, found 'uuid'.`
-   **Przyczyna:** Model SQLAlchemy w kodzie oczekuje, że kolumna `tenant_id` w tabeli `memories` będzie typu `TEXT`, ale migracja Alembic tworzy ją jako `uuid`.
-   **Plan Naprawy:**
    1.  **Zlokalizuj migrację:** Znajdź plik w `alembic/versions/`, który definiuje tabelę `memories`.
    2.  **Zlokalizuj model:** Znajdź klasę `Memory` w `rae-core/rae_core/models/` (prawdopodobnie `memory.py`).
    3.  **Ujednolić typy:** Zdecyduj, czy prawidłowym typem jest `TEXT` czy `UUID`. Biorąc pod uwagę błąd testu, prawdopodobnie należy zmienić typ w migracji Alembic z `sa.UUID` na `sa.String` lub `sa.Text`.

### Problem 2: Nieprawidłowe UUID w Testach Integracyjnych

-   **Błąd:** `asyncpg.exceptions.DataError: invalid input for query argument $1: 'test-tenant-graphrag'`
-   **Przyczyna:** Testy w `tests/integration/test_graphrag.py` i `tests/integration/test_reflection_flow.py` używają statycznego stringa jako `tenant_id`, podczas gdy baza danych oczekuje formatu UUID.
-   **Plan Naprawy:**
    1.  Zaimportuj moduł `uuid` w plikach testowych.
    2.  Zastąp wszystkie wystąpienia błędnych identyfikatorów (np. `'test-tenant-graphrag'`) dynamicznie generowanym UUID: `str(uuid.uuid4())`.

### Problem 3: Błąd Walidacji Pydantic (pole `layer`)

-   **Błąd:** `pydantic_core.ValidationError` dla pola `layer` z wartością `'em'`.
-   **Przyczyna:** Test `test_agent_execute_happy_path` w `tests/api/v1/test_agent.py` próbuje utworzyć obiekt z nieprawidłową wartością dla pola `layer`, które jest enumem.
-   **Plan Naprawy:**
    1.  Otwórz plik `tests/api/v1/test_agent.py`.
    2.  Znajdź dane wejściowe dla testu.
    3.  Zmień wartość pola `layer` z `'em'` na jedną z dozwolonych wartości, np. `'episodic'` lub `'working'`.

### Problem 4: Błędy Konfiguracji Usług Zewnętrznych (Ollama, OpenAI)

-   **Błędy:** `litellm.AuthenticationError` (brak klucza OpenAI), `404 Not Found` (brak modelu Ollama).
-   **Przyczyna:** Środowisko testowe nie ma skonfigurowanych poprawnych kluczy API ani pobranych modeli LLM wymaganych przez testy.
-   **Plan Naprawy (Opcjonalnie):**
    -   **Opcja A (Pełna integracja):** Uzupełnij plik `.env.test` o prawdziwy klucz `OPENAI_API_KEY` i upewnij się, że lokalna usługa Ollama ma pobrany model `deepseek-coder:1.3b`.
    -   **Opcja B (Mockowanie/Pominięcie):** Jeśli testy mają być uruchamiane w środowisku CI bez dostępu do tych usług, należy zamockować odpowiedzi od tych serwisów lub pominąć te testy za pomocą dekoratora `@pytest.mark.skip`.

Po wykonaniu tych kroków, ponowne uruchomienie `pytest` powinno zakończyć się sukcesem.
