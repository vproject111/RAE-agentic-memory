# NODE DELEGATION SPECIFICATION (v1.0)

> Ten dokument definiuje techniczne wymogi dla zadań delegowanych na węzły zewnętrzne (Node1/KUBUS).

## 1. STRUKTURA ZADANIA (Atomic Task)

Każde zadanie `POST /tasks` musi być sformatowane w sposób minimalizujący swobodę interpretacyjną modelu DeepSeek:

```json
{
  "goal": "Krótki, techniczny opis celu",
  "files": ["ścieżka/do/pliku.py"],
  "context_id": "UUID-Z-RAE",
  "contract_ref": "Klasa/Interfejs bazowy",
  "instructions": [
    "1. Użyj asynchronicznego adaptera X",
    "2. Dodaj telemetrię dla operacji Y",
    "3. Napisz test jednostkowy w Z"
  ],
  "constraints": [
    "No absolute paths",
    "Async-first only",
    "Strict type hinting"
  ]
}
```

## 2. PĘTLA WRITER/REVIEWER (Lokalna na Node)

Agent `infra/node_agent` musi wymusić następujący przepływ:

### Krok A: Writer (DeepSeek)
Prompt systemowy:
*"Jesteś ekspertem Python w projekcie RAE. Piszesz kod wysokiej jakości, asynchroniczny, z pełnym typowaniem. Twoim zadaniem jest realizacja punktów z listy 'instructions' przy zachowaniu 'constraints'. Nie twórz niepotrzebnych zależności."*

### Krok B: Reviewer (Ollama)
Prompt systemowy:
*"Jesteś Senior Architektem RAE. Sprawdzasz kod pod kątem: 1. Poprawności async/await. 2. Obecności telemetrii OTel. 3. Istnienia testów. 4. Agnostyczności (brak hardkodowanych ścieżek). Jeśli znajdziesz błędy, zwróć je w formacie listy punktowej."*

## 3. WYMOGI JAKOŚCIOWE (Quality Gates)

### A. Telemetria
Nowy kod **musi** zawierać:
```python
from apps.memory_api.observability.rae_tracing import trace_agent_operation

@trace_agent_operation(operation="nazwa_op")
async def nowa_funkcja(...):
    # ...
```

### B. Testowanie
Node1 musi dostarczyć plik `test_*.py` zawierający:
*   Mockowanie zewnętrznych serwisów (`AsyncMock`).
*   Testy typu "happy path" i "edge cases".
*   Weryfikację asercji logicznych.

## 4. RAPORTOWANIE WYNIKÓW

Wynik z Node1 musi zostać zapisany w RAE Memory jako zdarzenie typu `task_completed` z dołączonym diffem i raportem z review.

---
**Zasada Krytyczna**: Jeśli kod z Node1 nie przechodzi lokalnego `ruff check` na Twoim systemie po pobraniu – cofnij zmiany (Revert) i zgłoś błąd w delegacji.
