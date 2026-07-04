# Plan Sesji: RAE Smart Black Box - Faza 3 (Enforcement)

## 🚀 Cel Główny
Wdrożenie logiki wymuszania polityk bezpieczeństwa (ISO 27000) i mapowania wzorców agentowych (Agentic Patterns) w `RAECoreService`.

## 🛠️ Protokół Startowy (Zapobiegający błądzeniu)

1.  **Weryfikacja Środowiska (Fail Fast):**
    ```bash
    python scripts/connect_cluster.py && curl -s http://localhost:8001/health
    ```
    *Oczekiwany wynik:* Cluster OK, API Health OK. Jeśli nie działa, sprawdź `docker compose ps` (port 8001).

2.  **Pobranie Kontekstu (RAE-First):**
    ```bash
    curl -s -X POST "http://localhost:8001/v1/memory/query" \
      -H "Content-Type: application/json" \
      -H "X-API-Key: secret" \
      -H "X-Tenant-Id: 00000000-0000-0000-0000-000000000000" \
      -d '{"query_text": "Smart Black Box Faza 3 Manifest", "k": 3, "project": "RAE-Smart-Black-Box"}'
    ```
    *Cel:* Agent musi "przypomnieć sobie", co to jest `AGENTIC_PATTERNS_MANIFEST.md` i gdzie skończyliśmy.

3.  **Załadowanie Kontraktów (Single Source of Truth):**
    ```bash
    cat docs/contracts/RAE_AGENTIC_CONTRACT.md docs/contracts/AGENTIC_PATTERNS_MANIFEST.md docs/rules/AGENT_CORE_PROTOCOL.md
    ```

## 📋 Lista Zadań (Faza 3)

1.  **Enforcement Logic (Core):**
    *   W `RAECoreService.store_memory` dodać walidację `info_class`.
    *   **Zasada:** Jeśli `info_class == RESTRICTED` i warstwa != `Working`, rzuć `SecurityPolicyViolation`.
2.  **Agentic Pattern Detection:**
    *   Zaimplementować detekcję wzorców z Manifestu (np. `chain_length > 5` -> `high_risk_sequence`).
    *   Miejsce zmian: `RAECoreService` lub nowy serwis `GovernanceService`.
3.  **Testy (Fail Fast):**
    *   Używaj `make test-fast` do szybkiej pętli.
    *   Napisz test: `test_restricted_data_blocked_in_episodic`.

## ⚠️ Kluczowe Przypomnienie
Nie zmieniaj architektury 4 warstw! Jedynie dodaj logikę "Strażnika" (Guard) przy wejściu danych.