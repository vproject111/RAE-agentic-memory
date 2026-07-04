# RAE – Zestawienie: co jest w kodzie, a czego brakuje w dokumentacji  
(„code → docs gap report”, stan na 2025-12-01)

Ten dokument zbiera **konkretne elementy zaimplementowane w kodzie**, które nie mają jeszcze
własnej, wystarczająco szczegółowej dokumentacji (poza wzmianką w README albo STATUS).

> Uwaga: zestawienie oparte jest na:
> - strukturze repo (`apps/`, `sdk/python/rae_memory_sdk`, `cli/agent-cli`, `integrations/`, `tools/`, `eval/`, `helm/`, `infra/`, `tests/`),
> - głównym `README.md`, `STATUS.md`, `TESTING_STATUS.md`, `TODO.md`,
> - fakcie istnienia konkretnych plików / katalogów w repo.
>
> W wielu miejscach istnieją **zalążki** dokumentacji (README, krótkie sekcje w innych .md),
> ale **brakuje pełnego, osobnego opisu „jak tego używać”**.

---

## 1. Warstwa kodu `apps/` – usługi, które nie mają osobnych opisów

### 1.1. Background Workers (Decay / Summarization / Dreaming)

**W kodzie:**

- W `apps/` są moduły odpowiedzialne za:
  - cykle **Decay**,
  - **Summarization** (podsumowania pamięci),
  - **Dreaming** (syntetyczne sample / internal rehearsal).
- `README.md` mówi, że:
  - „Background Workers: Fully operational Decay, Summarization, and Dreaming cycles.”  
    (sekcja „Reality Check / What works”).  

**Braki w dokumentacji:**

- Brak osobnego pliku, który tłumaczy:
  - jakie są **parametry cykli** (częstotliwość, limity tokenów, progi),
  - jakie **kroki przetwarzania** wykonuje każdy worker,
  - jak te cykle są **powiązane z poziomami pamięci** (sensory/working/LTM/RM),
  - jak je **konfigurować per tenant** (lub globalnie),
  - jak monitorować ich pracę (logi, metryki, alerty).

**Propozycja brakującej dokumentacji:**

- `docs/BACKGROUND_WORKERS.md`
- `docs/DECAY_SUMMARIZATION_DREAMING.md` (bardziej „productowo”)

---

### 1.2. Reflection Engine V2 – detale implementacji

**W kodzie:**

- Reflection Engine V2 jest zaimplementowany jako osobny komponent (Actor–Evaluator–Reflector),
  uruchamiany z poziomu API i workerów.
- `README.md` dość szczegółowo opisuje **koncepcję** Reflection Engine V2
  (pattern, 4 warstwy pamięci itd.).

**Braki w dokumentacji:**

- Brak dokumentu, który:
  - mapuje **pattern z README** na **konkretne klasy / funkcje** w `apps/`,
  - opisuje **pełny flow** na poziomie API:
    - co wyzwala refleksję (trigger),
    - jakie dane wejściowe dostaje evaluator,
    - jak powstaje „reflection” i gdzie jest zapisywana (który layer, jakie tagi),
  - pokazuje **1–2 kompletne przykłady** (JSON in → JSON out) dla:
    - refleksji nad historią rozmowy,
    - refleksji nad LTM (episodic/semantic).

**Propozycja brakującej dokumentacji:**

- `docs/REFLECTION_ENGINE_V2_IMPLEMENTATION.md`

---

### 1.3. Rules Engine (polityki, automaty, triggerowane akcje)

**W kodzie:**

- W `apps/` jest moduł „Rules Engine” (wspominany w README), który:
  - reaguje na zdarzenia (np. nowe wspomnienie, przekroczony budżet, określony typ zapytania),
  - wykonuje akcje (np. uruchamia refleksję, decay, alerty).

**Braki w dokumentacji:**

- Brak pełnej specyfikacji:
  - jakie **typy reguł** są obsługiwane (event-based, schedule, threshold),
  - jak wygląda **format reguły** (JSON/YAML),
  - gdzie i jak są **przechowywane** (DB / pliki),
  - w jaki sposób reguły są **spięte z ISO 42001 / risk register**.

**Propozycja brakującej dokumentacji:**

- `docs/RULES_ENGINE.md`  
- ewentualnie sekcja „Rules Engine & Governance” w `RAE-ISO_42001.md`

---

### 1.4. Multi-tenant API – szczegółowa mapa tenantów

**W kodzie:**

- API jest **multi-tenant** (tenant_id w modelach, RLS w Postgres, itd.).
- W `STATUS.md` i `README.md` jest informacja, że multi-tenancy jest w pełni zaimplementowane
  oraz że RAE jest „Enterprise Ready”.

**Braki w dokumentacji:**

- Brak jednego miejsca, które tłumaczy:
  - jak **tworzyć tenantów** (endpointy / CLI / migracje),
  - jak są realizowane **granice danych** (RLS, filtry, audyt),
  - jak wygląda **model ról i uprawnień** na poziomie tenantów,
  - jak od strony API/SDK używać `tenant_id` (nagłówki, parametry).

**Propozycja brakującej dokumentacji:**

- `docs/MULTI_TENANCY.md` albo rozbudowa `RAE-Roles.md` + cross-link do API.

---

## 2. LLM Service, profile i Cost Guard – kod > dokumentacja

### 2.1. Pełne wsparcie wielu providerów LLM

**W kodzie:**

- Obsługa wielu providerów (OpenAI, Anthropic, Google, DeepSeek, Qwen, Grok, Ollama, itp.).
- Abstrakcyjna warstwa „LLM profiles” (profile modeli, fallbacki, cost-aware routing).
- Integracja z cost trackiem i budżetami per profile/tenant.

**Braki w dokumentacji:**

- Brak jednej, „inżynierskiej” matrycy konfiguracji:
  - **dokładne nazwy zmiennych środowiskowych** dla każdego providera,
  - wzorcowy `llm_profiles.yaml` (lub odpowiedni config),
  - przykłady **fallback chains** (np. tani lokalny → droższy chmurowy),
  - opis, jak spiąć **LLM profiles** z **cost guardem** i budżetami.

**Propozycja brakującej dokumentacji:**

- `docs/LLM_PROFILES_AND_COST_GUARD.md`  
  - sekcja „Provider Matrix”  
  - sekcja „Profile Examples”  
  - sekcja „How Cost Guard hooks into LLM calls”

---

### 2.2. Cost Guard & Budgets – implementacja a faktyczne „how-to”

**W kodzie:**

- Aktywny **Cost Guard**:
  - liczenie kosztów na poziomie requestów,
  - budżety per tenant / per profile,
  - blokowanie requestu z HTTP **402** przy przekroczeniu budżetu.

**Braki w dokumentacji:**

- Brak osobnego:
  - wyjaśnienia **modelu danych** (jak zapisywane są koszty, w jakich tabelach),
  - przykładowych zapytań SQL / API do odczytu kosztów,
  - scenariusza „jak ustawić budżet na 50 USD/miesiąc dla klienta X i zobaczyć,
    że blokady działają”.

**Propozycja brakującej dokumentacji:**

- Można dołączyć do `LLM_PROFILES_AND_COST_GUARD.md`
- Ewentualnie osobny plik: `docs/COST_GUARD_IMPLEMENTATION.md`

---

## 3. SDK Python (`sdk/python/rae_memory_sdk`) – API SDK vs dokumentacja

**W kodzie:**

- Istnieje pełny **Python SDK**:
  - klasa klienta (np. `MemoryClient`),
  - metody do:
    - zapisu wspomnień,
    - zapytań z RAG/GraphRAG,
    - zarządzania pamięcią (kasowanie, tagowanie, itp.),
  - obsługa autoryzacji / endpointów RAE.

**Braki w dokumentacji:**

- README tylko **krótko wspomina** SDK i pokazuje prosty snippet.
- Brak:
  - pełnej listy metod (`store`, `query`, `search`, `delete`, ewentualne `batch_*`),
  - opisów **typów parametrów i odpowiedzi** (modele, schematy JSON),
  - przykładów:
    - jak korzystać z SDK w **asystencie zespołowym**,  
    - jak zbudować **„project memory”** dla kodu/PR-ów,
    - jak spiąć SDK z **klientami LLM** (np. w swoim agencie).

**Propozycja brakującej dokumentacji:**

- `docs/SDK_PYTHON_REFERENCE.md`
- `examples/sdk/…` z 2–3 pełnymi przykładami.

---

## 4. CLI (`cli/agent-cli`) i narzędzia developerskie (`tools/`, `scripts/`, `eval/`)

### 4.1. `cli/agent-cli` – brak pełnej dokumentacji CLI

**W kodzie:**

- Istnieje **CLI** do interakcji z RAE:
  - odpalanie agentów,
  - import danych,
  - zapytania,
  - diagnostyka.

**Braki w dokumentacji:**

- Brak osobnego:
  - opisu instalacji CLI (lokalnie / jako pakiet),
  - listy komend (`rae …`),
  - przykładów użycia w typowych taskach:
    - ingest dokumentów,
    - szybkie zapytania diagnostyczne,
    - sprawdzanie statusu workerów / budżetów.

**Propozycja brakującej dokumentacji:**

- `docs/CLI_REFERENCE.md` + sekcja „examples”:
  - `examples/cli/demo_*.md` / `examples/cli/*.sh`

---

### 4.2. `tools/` i `scripts/` – helpery niewyjaśnione w docs

**W kodzie:**

- Skrypty typu:
  - `generate_tests_v8.py`,
  - `eptt.py`,
  - inne narzędzia w `tools/` / `scripts/` do:
    - generowania testów,
    - analizy pokrycia,
    - migracji / utilities.

**Braki w dokumentacji:**

- Brak:
  - listy narzędzi developerskich z krótkim opisem:
    - co robi dany skrypt,
    - kiedy go używać,
    - jakie ma parametry / wymagania (venv, env).
  - wskazania, które z nich są:
    - **dla maintainerów**, a które **bezpieczne dla użytkowników**.

**Propozycja brakującej dokumentacji:**

- `docs/DEV_TOOLS_AND_SCRIPTS.md`:
  - tabela: `plik → opis → typ (dev/prod) → przykładowe wywołanie`.

---

### 4.3. `eval/` – framework ewaluacyjny

**W kodzie:**

- Katalog `eval/` sugeruje istnienie:
  - frameworka do testów jakościowych / benchmarków,
  - skryptów do ewaluacji pamięci / rozumowania.

**Braki w dokumentacji:**

- Brak:
  - opisu „jak uruchomić ewaluację”,
  - jakie metryki są zbierane,
  - jak interpretować wyniki (np. raporty JSON/CSV).

**Propozycja brakującej dokumentacji:**

- `docs/EVAL_FRAMEWORK.md`

---

## 5. Integracje (`integrations/`) i MCP/IDE

### 5.1. Integracje (Slack / GitHub / e-mail itd.)

**W kodzie:**

- Katalog `integrations/` sugeruje gotowe albo częściowo gotowe integracje:
  - Slack / chat,
  - GitHub / PR memory,
  - inne kanały.

**Braki w dokumentacji:**

- Brak **per-integracja**:
  - wymaganych secretów i zmiennych środowiskowych,
  - konfiguracji webhooków / eventów,
  - przykładowego przepływu: „event → RAE → odpowiedź / aktualizacja pamięci”.

**Propozycja brakującej dokumentacji:**

- `docs/INTEGRATIONS_OVERVIEW.md`
- szczegółowe:
  - `docs/integrations/SLACK.md`
  - `docs/integrations/GITHUB.md`
  - itd.

---

### 5.2. MCP / integracja z IDE

**W kodzie:**

- README reklamuje integrację przez **Model Context Protocol (MCP)**,
  więc w repo są:
  - definicje MCP tools,
  - konfiguracje do użycia z IDE / agentami.

**Braki w dokumentacji:**

- Brak:
  - jasnej instrukcji „jak wpiąć RAE do IDE X (np. VS Code, Cursor, Zed) przez MCP”,
  - przykładów konfiguracji `.json` / `.yaml` dla MCP,
  - checklisty:
    - jakie endpointy RAE udostępnia MCP,
    - jakie operacje są wspierane (search, memory read/write, itd.).

**Propozycja brakującej dokumentacji:**

- `docs/MCP_IDE_INTEGRATION.md`

---

## 6. Helm / K8s (`helm/rae-memory`, `charts/rae`) i `infra/`

**W kodzie:**

- Pełne **Helm chart** oraz manifesty K8s,
- katalog `infra/` z infrastrukturą (bazy, monitoring, sieć).

**Braki w dokumentacji:**

- Brak:
  - jednego przewodnika „jak wdrożyć RAE na K8s”:
    - wymagane secrety (DB, LLM, auth),
    - różnice między Lite/Standard/Enterprise na klastrze,
    - przykładowe `values.yaml`,
    - integracja z Prometheus/Grafana/OpenTelemetry.

**Propozycja brakującej dokumentacji:**

- `docs/DEPLOY_K8S_HELM.md`  
- ewentualnie podział:
  - `docs/DEPLOY_LITE_K8S.md`
  - `docs/DEPLOY_ENTERPRISE_K8S.md`

---

## 7. Testy (`tests/`, `test_enterprise_features.py`, `TESTING_STATUS.md`)

**W kodzie:**

- Rozbudowany katalog `tests/`,
- plik `test_enterprise_features.py`,
- testy jednostkowe + integracyjne dla najważniejszych komponentów.

**Braki w dokumentacji:**

- `TESTING_STATUS.md` i `TESTING.md` podają ogólny stan,
  ale nie ma **mapowania „feature → testy → pliki”**:
  - np.:
    - GraphRAG – które pliki testów?
    - Reflection Engine – gdzie go testujemy?
    - Rules Engine, Cost Guard, PII Scrubber – które testy to obejmują?

**Propozycja brakującej dokumentacji:**

- `docs/TEST_COVERAGE_MAP.md`
  - tabela: `Feature → unit tests → integration tests → e2e → pliki testów`.

---

## 8. ISO 42001 / Security / Risk – powiązanie dokumentów z kodem

**W kodzie:**

- Implementacje:
  - RLS w Postgres,
  - audyt logów,
  - PII scrubber,
  - role / uprawnienia,
  - retention / kasowanie.

**W dokumentach:**

- `RAE-ISO_42001.md`
- `RAE-Risk-Register.md`
- `RAE-Roles.md`
- `SECURITY.md`

**Braki w dokumentacji:**

- Brak **jednego pliku**, który:
  - mapuje **konkretne ryzyka i wymagania** (z ISO / risk register)
    → na **konkretne moduły w kodzie** (pliki, klasy, funkcje),
  - pokazuje **przykładowe procesy** (np. „Right to be forgotten”),
  - łączy RACI (Roles) z faktycznymi API / operacjami w systemie.

**Propozycja brakującej dokumentacji:**

- `docs/ISO42001_IMPLEMENTATION_MAP.md`

---

## 9. Podsumowanie – lista brakujących dokumentów (propozycje)

Z perspektywy „co jest już w kodzie, a nie ma pełnej dokumentacji”:

1. `docs/BACKGROUND_WORKERS.md`  
2. `docs/REFLECTION_ENGINE_V2_IMPLEMENTATION.md`  
3. `docs/RULES_ENGINE.md`  
4. `docs/MULTI_TENANCY.md`  
5. `docs/LLM_PROFILES_AND_COST_GUARD.md`  
6. `docs/SDK_PYTHON_REFERENCE.md` + przykłady w `examples/sdk/`  
7. `docs/CLI_REFERENCE.md`  
8. `docs/DEV_TOOLS_AND_SCRIPTS.md`  
9. `docs/EVAL_FRAMEWORK.md`  
10. `docs/INTEGRATIONS_OVERVIEW.md` + per-integracja w `docs/integrations/*.md`  
11. `docs/MCP_IDE_INTEGRATION.md`  
12. `docs/DEPLOY_K8S_HELM.md`  
13. `docs/TEST_COVERAGE_MAP.md`  
14. `docs/ISO42001_IMPLEMENTATION_MAP.md`

Te dokumenty nie zmieniają kodu – **tylko odsłaniają to, co już jest zrobione**, i ułatwiają
zewnętrznym użytkownikom, partnerom i audytorom zrozumienie, jak faktycznie działa RAE.
