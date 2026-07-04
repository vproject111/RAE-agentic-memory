# Plan Przygotowania Wydania i Weryfikacji (Release Prep Plan)

## Cel
Zapewnić powtarzalność instalacji (bootstrap) na świeżym środowisku oraz zweryfikować stabilność systemu przed wypchnięciem zmian.

## 1. Naprawa Bootstrapowania (Auto-Init)
Obecnie `ValidationService` blokuje start, jeśli kolekcje Qdrant nie istnieją. Na świeżej instancji kolekcje nie istnieją, więc system wpada w pętlę.
- [x] **Zadanie:** Zmodyfikować `apps/memory_api/main.py`, aby automatycznie tworzyć brakujące kolekcje zdefiniowane w `RAE_MEMORY_CONTRACT_V1` przed uruchomieniem walidacji.
- [x] **Cel:** `docker compose up` musi działać "od zera" bez ręcznego curl'owania.

## 2. Testy Lokalnej Integracji
Weryfikacja zmian za pomocą zestawu testów.
- [x] **Zakres:** Testy jednostkowe i integracyjne `apps/memory_api`.
- [x] **Wykluczenia:** Pominąć katalog `rae-lite` (chyba że mockowane).
- [x] **Konfiguracja:** Użyć `ANTHROPIC_API_KEY` obecnego w środowisku dla testów LLM.
- [x] **Komenda:** `pytest -v -m "not rae_lite" --ignore=rae-lite` (lub adekwatna selekcja).

## 3. Finalizacja
- [x] **Commit:** Zatwierdzić zmiany w `main.py` i ewentualne poprawki testów.
- [x] **Push:** Wypchnąć zmiany do zdalnego repozytorium (`develop`/`main`).