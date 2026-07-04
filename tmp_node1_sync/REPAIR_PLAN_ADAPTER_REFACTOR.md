# Plan Naprawy Refaktoryzacji Adapterów

## Cel
Naprawa błędów architektonicznych wprowadzonych podczas ostatniej refaktoryzacji, poprawa wszystkich powiązanych testów oraz aktualizacja dokumentacji w celu odzwierciedlenia poprawnej, agnostycznej struktury.

## Główna zasada
Moduł `rae-core` musi być w 100% agnostyczny. Definiuje wyłącznie interfejsy. Jego testy muszą używać mocków dla tych interfejsów i **nie mogą** zależeć od modułu `apps` ani żadnego innego modułu na poziomie aplikacji.

---

### Faza 1: Przywrócenie agnostycyzmu `rae-core` (Naprawa testów `rae-core`)

**Cel:** Uczynienie testów `rae-core` samowystarczalnymi, zależnymi wyłącznie od interfejsów i mocków.

**Kroki:**

1.  **Identyfikacja i przeniesienie testów implementacji:** Testy znajdujące się w `rae-core/tests/unit/adapters/` błędnie testują konkretne implementacje, które zostały przeniesione. Należy je przenieść do odpowiedniej lokalizacji w aplikacji, np. `apps/memory_api/tests/adapters/`, ponieważ to aplikacja jest właścicielem implementacji.
2.  **Poprawa ścieżek `patch` w `rae-core`:** Zweryfikować pozostałe testy w `rae-core` i zaktualizować wszystkie wywołania `patch`, aby odnosiły się do interfejsów (`rae_core.interfaces.*`), a nie do konkretnych implementacji.
3.  **Utworzenie testów dla interfejsów (jeśli konieczne):** Sprawdzić, czy `rae-core` posiada logikę zależną od interfejsów adapterów. Jeśli tak, utworzyć nowe testy jednostkowe w `rae-core`, które dostarczają **mocki** tych interfejsów. Zapewni to, że `rae-core` poprawnie współpracuje z kontraktem (interfejsem), a nie z implementacją.

---

### Faza 2: Naprawa testów aplikacji (`apps/memory_api`)

**Cel:** Zapewnienie, że wszystkie testy w `apps/memory_api` używają poprawnych, nowych ścieżek do adapterów.

**Kroki:**

1.  **Poprawa importów w testach:** Systematycznie przejrzeć wszystkie pliki w `apps/memory_api/tests/` i zastąpić stare importy (`from rae_core.adapters...`) nowymi (`from apps.memory_api.adapters...`).
2.  **Poprawa ścieżek `patch` w testach aplikacji:** Zaktualizować wywołania `patch` w tych testach, aby wskazywały na nowe lokalizacje klas adapterów (np. `patch('apps.memory_api.adapters.qdrant.QdrantClient')`).

---

### Faza 3: Porządki i dokumentacja

**Cel:** Aktualizacja wszystkich plików dokumentacji, przykładów i konfiguracji, aby odzwierciedlały nową architekturę.

**Kroki:**

1.  **Aktualizacja `rae-lite.spec`:** Poprawić ścieżki w sekcji `hiddenimports`.
2.  **Aktualizacja plików `README.md`:** Wyszukać przykłady kodu w plikach `.md` (zwłaszcza w `rae-core/README.md`) i zaktualizować w nich ścieżki importu.
3.  **Aktualizacja pozostałej dokumentacji:** Przejrzeć pozostałe pliki (stare plany, logi) znalezione podczas analizy i zaktualizować w nich ścieżki, aby uniknąć pomyłek w przyszłości.

---
Zapisano jako `REPAIR_PLAN_ADAPTER_REFACTOR.md`
