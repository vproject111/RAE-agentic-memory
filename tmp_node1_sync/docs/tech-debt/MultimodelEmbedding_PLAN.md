# Plan Wdrożenia: Multimodel Embedding & Semantic Federation

## Opinia o zmianach
Propozycja opisana w `MultimodelEmbedding.md` jest **krytyczna i architektonicznie poprawna** dla systemu rozproszonego takiego jak RAE.
- **Problem:** Obecna architektura zakłada jedną przestrzeń wektorową, co przy hybrydowym środowisku (laptop + serwer) prowadzi do "równania w dół" (używania słabych modeli wszędzie) lub niespójności.
- **Rozwiązanie:** Traktowanie embeddingów jako **lokalnych projekcji**, a nie globalnej prawdy. To pozwala na używanie lekkich modeli (Ollama/Nomic) na Edge i potężnych (Gemini/Claude) w Chmurze/Serverze bez konfliktu.
- **Wniosek:** To zmiana paradygmatu z RAG na "Federated Cognitive Memory". Jestem w pełni za.

## Szczegółowy Plan Wdrożenia

### Faza 1: Warstwa Danych (Baza Danych) [ZREALIZOWANO]
Odejście od kolumny `embedding` w tabeli `memories` na rzecz relacji 1:N.

1. **Nowa tabela `memory_embeddings`** [OK]:
   - `id` (UUID, PK)
   - `memory_id` (UUID, FK -> memories)
   - `model_name` (string, np. "nomic-embed-text-v1.5", "text-embedding-004")
   - `embedding` (vector, wymiar dynamiczny)
   - `created_at` (timestamp)
   - `metadata` (jsonb)

2. **Migracja** [OK]:
   - Utworzenie tabeli (Alembic `5b600ed8dfcb`).
   - Migracja danych z obecnej kolumny `memories.embedding` do nowej tabeli jako "default".
   - Zachowanie kolumny w `memories` tymczasowo jako deprecated dla kompatybilności wstecznej.

### Faza 2: Warstwa Core (RAE Engine) [ZREALIZOWANO]
Rozszerzenie interfejsów w `rae-core` i `apps/memory_api`.

1. **Embedding Manager** [OK]:
   - Wprowadzenie `EmbeddingManager` w `rae_core.embedding.manager`.
   - Rejestracja wielu providerów.
   - Aktualizacja `RAECoreService` do używania Managera.

2. **Konfiguracja (Config)** [W TOKU]:
   - Przygotowano grunt pod `EMBEDDING_PROFILES` w `EmbeddingManager`.

### Faza 3: Logika Aplikacji (Service Layer) [ZREALIZOWANO]

1. **Zapis Pamięci (`store_memory`)** [OK]:
   - Zaktualizowano `RAEEngine.store_memory`.
   - Asynchroniczne generowanie embeddingów dla wszystkich aktywnych profili (via `generate_all_embeddings`).
   - Zapis wyników do `memory_embeddings` oraz Vector Store (legacy).

2. **Wyszukiwanie Hybrydowe (`HybridSearchService`)** [Częściowo]:
   - **Krok 1 (Cheap):** Zaktualizowano `_vector_search` do używania tabeli `memory_embeddings`.
   - **Krok 2 (Lexical):** Bez zmian (działa).
   - **Krok 3 (Deep):** Gotowe do wdrożenia (wymaga konfiguracji profilu "heavy").

### Faza 4: Protokół Federacyjny (API) [ZREALIZOWANO]
Umożliwienie współpracy wielu instancji RAE.

1. **Endpoint `POST /federation/query`** [OK]:
   - Zaimplementowano w `apps/memory_api/routes/federation.py`.
   - Zwraca listę kandydatów (ID + Fragment tekstu) bez wektorów.

2. **Lokalna Reinterpretacja**:
   - Logika klienta (odbiorcy) do implementacji w przyszłości.

## Następne Kroki (Actionable Items)
1. **Zastosowanie Migracji**: Uruchomienie `alembic upgrade head`.
2. **Konfiguracja Profili**: Dodać obsługę `EMBEDDING_PROFILES` w `apps/memory_api/config.py` i ładowanie ich w `RAECoreService`.
3. **Testy**: Zweryfikować działanie multi-model na środowisku dev.