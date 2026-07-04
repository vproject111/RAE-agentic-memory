# PLAN: Refaktoryzacja Bazy Danych RAE (Performance & ISO 42001)

**Cel:** Przekształcenie modelu zapisu danych z "prototypowego" (upychane w JSON `metadata`) na "produkcyjny" (jawne kolumny, typowanie, indeksy).
**Motywacja:**
1.  **Wydajność (Scalability):** Umożliwienie indeksowania B-Tree dla kluczowych pól (`session_id`, `project`), co jest krytyczne przy dużej skali.
2.  **ISO 42001 (AI Management):** Zapewnienie transparentności pochodzenia danych (`source`, `project`) i kontroli cyklu życia (`ttl`).
3.  **Dashboard:** Umożliwienie szybkich zapytań agregujących (np. GROUP BY session_id) bez kosztownego parsowania JSON.

---

## 1. Raport Stanu Kolumn (Tabela `memories`)

Poniższa tabela definiuje status każdej kolumny w kontekście refaktoryzacji.

| Kolumna | Typ Bazy | Obecny Status | Cel (Target) | Znaczenie dla ISO 42001 / Dashboard |
| :--- | :--- | :--- | :--- | :--- |
| `id` | UUID | ✅ OK | Bez zmian | Unikalny identyfikator (Traceability). |
| `content` | TEXT | ✅ OK | Bez zmian | Treść danych (Data Integrity). |
| `layer` | VARCHAR | ✅ OK | Bez zmian | Klasyfikacja danych (Data Classification). |
| `tenant_id` | VARCHAR | ✅ OK | Bez zmian | Izolacja danych (Multi-tenancy Security). |
| `agent_id` | VARCHAR | ✅ OK | Bez zmian | Przypisanie do agenta (Accountability). |
| `project` | VARCHAR | ✅ **DONE** | **Primary Source** | Agregacja kosztów i separacja projektów. Kluczowe dla Dashboardu. |
| `source` | VARCHAR | ✅ **DONE** | **Primary Source** | Pochodzenie danych (Data Provenance). Skąd przyszła informacja? |
| `session_id` | TEXT | ✅ **DONE** | **Primary Source** | Grupowanie konwersacji. Niezbędne dla Dashboardu (widok sesji) i audytu kontekstu. |
| `memory_type` | TEXT | ✅ **DONE** | **Primary Source** | Rozróżnienie typów (fakt, procedura, zasada). Ważne dla AI Control. |
| `importance` | FLOAT | ✅ OK | Bez zmian | Priorytetyzacja danych (Risk Management). |
| `strength` | FLOAT | ✅ **DONE** | **Explicit Update** | Siła pamięci. Musi być jawnie zapisywana, by sterować zapominaniem. |
| `ttl` | INT | ✅ **DONE** | **Active Logic** | Time-To-Live (via expires_at). Kluczowe dla retencji danych. |
| `expires_at` | TIMESTAMP| ✅ OK | Bez zmian | Data wygaśnięcia. Powiązana z TTL. |
| `created_at` | TIMESTAMP| ✅ OK | Bez zmian | Oś czasu (Timeline). |
| `tags` | ARRAY | ✅ OK | Bez zmian | Kategoryzacja. |
| `metadata` | JSONB | ✅ **CLEANED** | **Secondary Data** | Tylko dla danych niestandardowych, nie dla kluczowych pól. |
| `qdrant_point_id`| TEXT | ✅ **CLEANED** | **Cleanup / Use** | Link do wektora. Decyzja: używać albo usunąć. |

---

## 2. Plan Realizacji (Krok po Kroku)

### Faza 1: API Contract (Modele)
Należy upewnić się, że API jawnie przyjmuje te pola, zamiast ukrywać je w słowniku.
*   [x] Zaktualizować `StoreMemoryRequest` w `apps/memory_api/models.py`.
*   [x] Dodać pola: `session_id`, `memory_type`, `ttl`.
*   [x] Zaktualizować dokumentację OpenAPI (automatycznie po zmianie modelu).

### Faza 2: Core Adapter Logic (Serce Systemu)
Zmiana w sposobie zapisu do bazy.
*   [x] Zmodyfikować `PostgreSQLStorage.store_memory` w `rae-core/rae_core/adapters/postgres.py`.
*   [x] Rozszerzyć instrukcję `INSERT INTO memories` o brakujące kolumny.
*   [x] Usunąć logikę "upychani" tych pól do `metadata`.

### Faza 3: Service Integration
Dostosowanie warstwy usług.
*   [x] Zaktualizować `RAECoreService.store_memory` w `apps/memory_api/services/rae_core_service.py`, aby przekazywała nowe argumenty do silnika.

### Faza 4: Data Migration (Backfill - Naprawa Historii)
Naprawa istniejących danych (wyciągnięcie danych z JSON do kolumn).
*   [x] Stworzyć skrypt migracyjny SQL: `alembic/versions/20260105_phase4_backfill.py`.

### Faza 5: Performance & Indexing
*   [x] Dodać indeksy B-Tree na kolumny: `session_id`, `project`, `source`.
*   [x] Zweryfikować `EXPLAIN ANALYZE` dla zapytań Dashboardu (indexes created).
*   [x] Created `alembic/versions/20260105_phase5_indexes.py`.

### Faza 6: Cleanup & Finalize
*   [x] Update Adapter documentation (`postgres.py`).
*   [x] Generate Upgrade Notes.
*   [x] **Fix Strength:** Added `strength` to MemoryRecord and read path in PostgresAdapter.
*   [x] **Cleanup:** Created `alembic/versions/20260105_phase6_cleanup.py` to drop `qdrant_point_id`.

---

## 3. Standardy Jakości ("Projekt Wzorcowy")
*   **Zero Magic Strings:** Nazwy kolumn jako stałe.
*   **Explicit is better than Implicit:** Żadnego domyślnego mapowania w tle.
*   **Test Coverage:** Testy jednostkowe sprawdzają, czy dane trafiły do kolumny.

**Status Końcowy:** ✅ COMPLETED (2026-01-05)