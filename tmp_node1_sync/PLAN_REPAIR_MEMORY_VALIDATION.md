# Plan Naprawy Walidacji Kontraktu Pamięci (Memory Contract Validation Repair Plan)

## Cel
Naprawić implementację walidacji pamięci w RAE, aby była w pełni zgodna z wymaganiami architektonicznymi, w szczególności w zakresie **agnostyczności** i pokrycia wszystkich warstw pamięci (Database, Cache, Storage/Vector).

## Diagnoza Obecnego Stanu
1.  **Brak Agnostyczności:** Walidacja jest zaimplementowana tylko dla Postgres (`PostgresValidator`) i wywoływana bezpośrednio w `main.py`.
2.  **Brak Pokrycia:** Cache (Redis) i Storage (Qdrant) nie są walidowane pod kątem zgodności z kontraktem.
3.  **Brak Abstracji:** Brak wspólnego interfejsu dla adapterów walidacji.

## Plan Działania

### 1. Architektura i Kontrakt
- [x] **Stworzyć interfejs `MemoryAdapter`** (`apps/memory_api/adapters/base.py`):
    - Metody abstrakcyjne: `connect()`, `validate(contract)`, `report()`.
- [x] **Rozszerzyć `MemoryContract`** (`apps/memory_api/core/contract.py`): (Already implemented)
- [x] **Zaktualizować Definicję Kontraktu** (`apps/memory_api/core/contract_definition.py`): (Already implemented)

### 2. Implementacja Adapterów
- [x] **Refaktoryzacja Postgres:**
    - Dostosować `PostgresValidator` (lub opakować go w `PostgresAdapter`) do interfejsu `MemoryAdapter`.
- [x] **Redis Adapter** (`apps/memory_api/adapters/redis_adapter.py`):
    - Implementacja walidacji dostępności i podstawowej konfiguracji (np. czy persistence jest włączone, jeśli wymagane).
- [x] **Qdrant Adapter** (`apps/memory_api/adapters/qdrant_adapter.py`):
    - Implementacja walidacji istnienia kolekcji i zgodności konfiguracji wektorów (wymiarowość, metryka).

### 3. Integracja i Start Systemu
- [x] **Unified Validation Logic** (`apps/memory_api/services/validation_service.py`):
    - Stworzyć mechanizm, który pobiera listę skonfigurowanych adapterów.
    - Uruchamia walidację dla każdego z nich.
    - Agreguje wyniki i raportuje błędy.
- [x] **Aktualizacja `main.py`:**
    - Zastąpić obecną logikę walidacji Postgres wywołaniem zunifikowanego walidatora.
    - Upewnić się, że błąd w DOWOLNEJ warstwie zatrzymuje start (Fail Fast).

### 4. Weryfikacja
- [x] **Testy Jednostkowe:**
    - Testy dla nowych adapterów (Redis, Qdrant).
    - Testy dla logiki agregacji walidacji.
- [x] **Testy Integracyjne:**
    - Symulacja błędu w Redis/Qdrant i weryfikacja czy aplikacja odmawia startu.

## Oczekiwany Rezultat
System RAE przy starcie weryfikuje spójność wszystkich warstw pamięci (SQL, NoSQL, Cache) względem zdefiniowanego kontraktu, zachowując czystość architektoniczną i agnostyczność rdzenia.
