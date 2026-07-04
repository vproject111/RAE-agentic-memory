# RAE – Dokumentacja vs Kod  
Raport braków i rekomendacji (stan na 2025-12-01)

Ten dokument opisuje, **czego realnie brakuje w dokumentacji względem kodu** projektu RAE-agentic-memory oraz co warto dopisać, aby projekt był czytelny dla zewnętrznego użytkownika (i inwestora).

> Uwaga: raport jest oparty na dostępnych plikach README i strukturze repozytorium GitHub (`apps/`, `sdk/python/rae_memory_sdk`, `cli/agent-cli`, `helm/rae-memory`, `infra/`, `integrations/`, `examples/`, `docs/` itd.) oraz publicznych opisach funkcji w README. Nie analizuje każdego pliku źródłowego linia po linii, ale koncentruje się na **spójności “obietnic” dokumentacji z widocznymi elementami kodu**.

---

## 1. Podsumowanie głównych braków

Z perspektywy nowej osoby, która odpala RAE pierwszy raz:

1. **Brakuje pełnego „mapowania” architektury na katalogi i moduły kodu**  
   README bardzo dobrze opisuje warstwy pamięci i mikroserwisy, ale nie ma jednego miejsca, które mówi:  
   _„Ten prostokąt z diagramu = ten moduł w `apps/…` + te modele w `…/core/` + te tabele w DB.”_

2. **RAE Lite ma świetnie opisany „profil”, ale brakuje ultra-konkretnej ścieżki „Hello, world”**  
   Jest docker compose, jest opis usług, ale brakuje jednego, bardzo prostego, skończonego scenariusza:  
   _„Uruchom Lite, wrzuć 10 dokumentów, zadaj 3 pytania, zobacz jak działa pamięć i GraphRAG.”_

3. **API jest opisane ogólnie (OpenAPI + API_DOCUMENTATION.md), ale brakuje „task-oriented” cookbooka**  
   Typu:  
   - „Jak zapisać wspomnienie użytkownika?”  
   - „Jak zadać pytanie z kontekstem RAG + historii?”  
   - „Jak odpytać konkretną warstwę pamięci (LTM vs RM)?”

4. **Multi-model LLM + cost-guard są dobrze opisane koncepcyjnie w README, ale brakuje kompletnego „Config Reference” dla LLM**  
   W README jest lista providerów i ogólny opis, ale brakuje jednego miejsca z pełnym wzorcem:  
   `.env` → `llm_profiles.yaml` → które zmienne musi ustawić dev.

5. **SDK (python) ma prosty snippet w README, ale nie ma osobnego „SDK Reference + Examples”**  
   Dla kogoś, kto chce używać tylko SDK, przydałoby się:  
   - pełne API klasy `MemoryClient` (metody, parametry, typy, przykłady),  
   - 2–3 kompletne scenariusze (personal assistant, team KB, code assistant).

6. **CLI (`cli/agent-cli`) i integracje (`integrations/`) nie mają osobnego przewodnika**  
   Są katalogi, ale nie ma jednego dokumentu, który by spiął:  
   - jak użyć CLI do importu danych,  
   - jak uruchomić konkretną integrację (Slack/GitHub/itp.) end-to-end.

7. **Testy, coverage i status są udokumentowane osobno (TESTING.md, TESTING_STATUS.md, STATUS.md), ale brakuje „Mostu” do modułów**  
   Dla każdej większej funkcjonalności (GraphRAG, Reflection Engine, Rules Engine, Cost Control) przydałby się krótki akapit: _„Co dokładnie jest przetestowane i gdzie szukać testów (katalogi/plik)?“_

8. **ISO 42001 / Security / Governance – treści są bogate, ale mało „zakotwiczone” w kodzie**  
   Dokumenty polityczne są mocne (RAE-ISO_42001.md, Risk Register, Roles, SECURITY.md), ale brakuje cross-linków typu:  
   - „RISK-003 → mitigacja w module X w pliku Y”,  
   - „Ten endpoint realizuje to wymaganie ISO / ten worker realizuje retention”.

---

## 2. Architektura vs struktura repozytorium

### 2.1. Co widać w repo

Z poziomu katalogów:

- `apps/` – główne aplikacje (API, ML service, Reranker, dashboard itd.).
- `sdk/python/rae_memory_sdk` – klient Python.
- `cli/agent-cli` – CLI/agenci.
- `helm/rae-memory`, `charts/rae` – deployment Kubernetes/Helm.
- `infra/` – infrastruktura pomocnicza.
- `integrations/` – zewnętrzne integracje.
- `examples/` – przykłady użycia.
- `docs/` – bogaty zestaw plików .md (ISO, security, memory model itd.).
- `tests/`, `test_enterprise_features.py` – testy.

### 2.2. Braki i rekomendacje

**Brak 1 – Brak jednej „mapy” architektury → katalogi i moduły**

README świetnie opisuje architekturę (4 warstwy, GraphRAG, Reflection Engine V2, ML Service, Reranker, RulesEngine itd.), ale nie ma jednego dokumentu, który:

- bierze diagram z README,
- i **dla każdego klocka** wypisuje:
  - katalog(i),
  - kluczowe klasy/funkcje,
  - główne tabele/indeksy w DB (Postgres/Qdrant/Redis),
  - powiązane testy.

**Rekomendacja:**  
Dodać dokument, np. `docs/ARCHITECTURE_CODE_MAP.md`, w którym:

- Dla każdego komponentu z sekcji „Core Services”, „Enterprise Services”, „Background Workers” w README:
  - `HybridSearchService` → ścieżka w kodzie (np. `apps/memory_api/services/hybrid_search.py`),  
  - `ReflectionEngineV2` → moduł, główne klasy, konfiguracja,  
  - `RulesEngine` → moduł + obsługiwane typy triggerów,  
  - `DecayWorker` / `SummarizationWorker` / `DreamingWorker` → gdzie są definicje zadań (Celery/Redis/itp.).

To jest plik, który bardzo pomaga maintainerowi / contributorowi wskoczyć w projekt.

---

## 3. RAE Lite vs Standard vs Enterprise

README opisuje:

- **RAE Lite** – 4 usługi, 4 GB RAM, Core API + GraphRAG + koszt.
- **Standard** – + ML Service, Reranker, Dashboard.
- **Enterprise** – + K8s, autoscaling, monitoring.

Jest odwołanie do **„RAE Lite Profile Documentation”**.

### Braki:

1. Z poziomu README nie widać:
   - pełnej listy kontenerów/services dla każdego profilu,
   - minimalnej i rekomendowanej konfiguracji `.env` dla Lite,
   - check-listy: co trzeba zrobić, żeby uznać, że Lite jest „poprawnie skonfigurowany i zdrowy”.

2. Nie widać gotowego „end-to-end scenariusza” dla Lite:
   - `docker compose.lite.yml up`,
   - wgranie danych,
   - przykładowe zapytania,
   - monitorowanie.

### Rekomendacje:

Dodać (lub doszlifować, jeśli częściowo istnieje) dokument:

- `docs/RAE_Lite_Profile.md` zawierający:
  - Tabelę: **Service → Port → Rola → Czy wymagany w Lite/Standard/Enterprise**
  - Sekcję **„Minimalny scenariusz E2E dla Lite”**:
    - krok po kroku z curl / httpie / Postmanem,
    - dokładnie użyte endpointy (np. `POST /memory`, `POST /query`, `GET /graph/...`),
    - przykładowe payloady i spodziewane odpowiedzi.
  - Sekcję **„Granice Lite”**:
    - brak ML Service, brak Rerankera, brak dashboardu, brak workerów – co to praktycznie oznacza,
    - co się zmienia po migracji do Standard (zachowanie API, side-effects, wydajność).

---

## 4. API i model pamięci

README opisuje:

- 4 warstwy pamięci (sensory, working, long-term, reflective),
- hybrid search,
- GraphRAG,
- Reflection Engine V2,
- multi-layer memory.

Wspomina też o `MEMORY_MODEL.md` i `REFLECTIVE_MEMORY_V1.md`.

### 4.1. Brak – Cookbook API per „use case”

Obecnie dokumentacja API (OpenAPI + API_DOCUMENTATION.md) jest postrzegana jako referencja techniczna. Natomiast brakuje:

- **zadaniowych mini-przewodników** typu:
  - „Jak zapisać jedno zdanie jako sensory memory vs long-term memory?”
  - „Jak wymusić, żeby zapytanie korzystało z GraphRAG?”
  - „Jak odpytać tylko reflective memory (Layer 4) i dostać same „lekcje/wisdom”?”

### Rekomendacja:

Dodać dokument np. `docs/API_COOKBOOK.md`:

- sekcje:

  1. **„Zapis wspomnień”**
     - przykłady requestów:
       - `POST /memory` dla sensory,
       - `POST /memory` dla episodic/semantic/profile,
       - znaczenie `layer`, `memory_type`, tagów, tenant_id.
  2. **„Zapytania”**
     - `POST /query` z różnymi strategiami:
       - „tylko LTM”,
       - „LTM + GraphRAG”,
       - „RM-only” (reflections).
  3. **„Kontrola wersji / kasowanie / GDPR”**
     - przykład kasowania danych użytkownika,
     - pokazanie w logach i audycie.

Każdy przykład: **pełny request + pełna odpowiedź**, z krótkim komentarzem.

---

## 5. Multi-model LLM i Cost Control

README ma bogaty opis:

- lista providerów (OpenAI, Anthropic, Google, DeepSeek, Qwen, Grok, Ollama),
- fallbacki, cost-aware, profiles, tool calling, JSON mode,
- budżety, HTTP 402 itd.

### Braki:

1. Brak jednego pliku „LLM & Cost Config Reference”, który zdejmuje z użytkownika zgadywanie:
   - jakie zmienne środowiskowe są **faktycznie wymagane** dla każdego providera,
   - jak wygląda przykładowy `llm_profiles.yaml` (lub równoważny config),
   - jakie eventy/endpointy generują wpisy w cost-guardzie i gdzie w DB są trzymane.

2. Brak przykładu: „Jak skonfigurować 2 modele równocześnie (np. local + cloud) i sprawdzić, że fallback działa?”.

### Rekomendacje:

Dodać dokument:

- `docs/LLM_CONFIG_AND_COST_GUARD.md`

z sekcjami:

1. **„Provider Matrix”** – tabela:
   - Provider,
   - Wymagane env (np. `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `OLLAMA_BASE_URL`),
   - Obsługiwane tryby (stream, tools, json),
   - Typowe ograniczenia / caveaty.

2. **„llm_profiles.yaml – pełny przykład”**
   - profile dla:
     - taniego modelu do embedów,
     - droższego modelu do refleksji,
     - lokalnego LLaMA dla offline work.

3. **„Cost Guard – jak to działa w praktyce”**
   - schemat: request → LLM call → zapis kosztu → budżet → 402,
   - przykładowe logi,
   - powiązanie z tabelami w DB.

---

## 6. SDK (Python) – `sdk/python/rae_memory_sdk`

README pokazuje snippet typu:

```python
from rae_memory_sdk import MemoryClient

agent = MemoryClient()
agent.store("User prefers dark mode…")
results = agent.query("What are the user's UI preferences?")
Braki:
Brak pełnego opisu API SDK:

jakie metody oferuje MemoryClient (store, query, delete, search, batch, health?),

jakie są typy i struktury danych (dict, pydantic models, typed responses?),

obsługa wyjątków i retry.

Brak wielu przykładów:

„Team Knowledge Base – ingest z plików / Slacka / PR-ów”,

„Code Review Bot – jak powiązać commit/PR z pamięcią”,

„Research Assistant – jak wgrać wiele dokumentów i zadawać pytania z cytatami”.

Rekomendacje:
Dodać:

docs/SDK_PYTHON_REFERENCE.md:

pełny opis klas, metod, argumentów,

tabelka: metoda → odpowiadający endpoint backendu.

examples/sdk/…:

minimum 2–3 kompletne skrypty z komentarzami.

7. CLI (cli/agent-cli) i integracje (integrations/)
W repo widać katalog cli/agent-cli i integrations/, ale nie ma z README jasnego, jak:

zainstalować CLI (jako paczkę / lokalnie),

skonfigurować tokeny / endpointy,

używać CLI do codziennych zadań (import, query, monitorowanie),

odpalić konkretną integrację (np. Slack, GitHub, e-mail).

Braki:
Brak osobnego dokumentu „RAE CLI & Integrations”.

Brak przykładowych „przepływów” (flows) pokazujących, jak RAE żyje z zewnętrznymi narzędziami.

Rekomendacje:
Dodać:

docs/CLI_AND_INTEGRATIONS.md, z:

Instalacja CLI – krok-po-kroku,

Podstawowe komendy:

rae ingest …,

rae query …,

rae status …,

rae cost ….

Integracje (każda podsekcja):

wymagane env/sekrety,

konfiguracja webhooków/cronów,

przykład „end-to-end” (np. Slack → RAE → odpowiedź).

8. Testowanie, status i jakość
Są pliki: TESTING.md, TESTING_STATUS.md, STATUS.md, test_enterprise_features.py, katalog tests/.

Braki:
Brak szybkiego „spisu treści testów” z podziałem na funkcjonalności:

GraphRAG – które testy?

Reflection Engine V2 – które testy?

Rules Engine, Cost Guard, PII Scrubber, Decay/Summarization/Dreaming – jakie testy istnieją, jakie są planowane?

Brak prostej tabelki: „feature → typ testów (unit/integration/e2e) → coverage (przybliżony)”.

Rekomendacje:
Rozbudować TESTING_STATUS.md (lub dodać nowy plik docs/TEST_COVERAGE_MAP.md) o:

tabelę:

Feature / Moduł	Testy unit	Testy integracyjne	Testy e2e	Szac. pokrycie	Główne pliki testowe
HybridSearchService	✔	✔	✖	~xx%	tests/test_hybrid_search.py
ReflectionEngineV2	✔	✔	✔	~yy%	tests/test_reflection.py
Rules Engine	…	…	…	…	…

oraz sekcję „Plany” (dla brakujących testów).

9. ISO 42001, Security, Risk, Roles
README i pliki:

RAE-ISO_42001.md,

RAE-Risk-Register.md,

RAE-Roles.md,

SECURITY.md,

opisują governance w sposób bardzo dojrzały (risk register, RACI, audit, RLS, PII, telemetry itd.).

Braki:
Brak „wiązania dokumentów governance z kodem”:

konkretne ryzyka z Risk Register nie są (z poziomu README) wprost powiązane z modułami / klasami,

RACI mówi, kto jest odpowiedzialny, ale nie ma przykładowych procesów/flow (np. „jak wygląda proces usuwania danych użytkownika z punktu widzenia roli Data Steward”).

Rekomendacje:
Dodać dokument:

docs/ISO42001_IMPLEMENTATION_MAP.md:

tabela:

Wymaganie / Ryzyko	Implementacja w kodzie	Plik / moduł
RISK-003	Cost Guard + budżety + 402	apps/memory_api/services/cost_*
GDPR Art. 17	Cascade delete + audit trail	apps/.../delete_service.py
Row-Level Security	RLS w Postgres + filtry tenant_id w repozytoriach	apps/.../repositories/*.py

przykładowe „procesy”:

„Deleting a user”: ścieżka API + logi + audyt.

10. Helm / K8s / Infra
Repo zawiera:

helm/rae-memory,

charts/rae,

infra/.

Braki:
Brak jednego „Helm & K8s Deployment Guide” skrojonego pod osoby DevOps-owe:

wymagane secrety i ConfigMapy,

typowe wartości (values.yaml) dla Lite/Standard/Enterprise,

jak podłączyć zewnętrzny Postgres/Qdrant/Redis,

jak włączyć monitoring (Prometheus, Grafana) i logowanie (OpenTelemetry).

Rekomendacja:
Dodać:

docs/DEPLOY_K8S_HELM.md, z 2–3 kompletnymi scenariuszami:

Single-tenant demo cluster,

Multi-tenant „team knowledge base”,

Highly available Enterprise.

11. Priorytetowa lista TODO (szczególnie pod RAE Lite)
Jeżeli chcesz szybko podnieść „odbieralność” projektu szczególnie dla małych firm / JST / MVP:

ARCHITECTURE_CODE_MAP.md (mapa: diagram → katalogi → moduły)

RAE_Lite_Profile.md z jednym bardzo prostym, pełnym scenariuszem E2E

API_COOKBOOK.md – kilka gotowych przepływów API (store, query, GDPR delete)

SDK_PYTHON_REFERENCE.md + przykłady w examples/sdk/

LLM_CONFIG_AND_COST_GUARD.md – pełna matryca providerów + config

Te 5 plików praktycznie „domyka” historię dla:

małego zespołu devów,

pilotażu w firmie / gminie,

potencjalnego partnera/inwestora, który chce ocenić jakość inżynierską.

12. Propozycja struktury w docs/
Na koniec propozycja docelowego układu dokumentów (część już istnieje, część jest do dodania):

docs/

ARCHITECTURE_OVERVIEW.md ✅ (może istnieje w innej formie)

ARCHITECTURE_CODE_MAP.md 🆕

MEMORY_MODEL.md ✅

REFLECTIVE_MEMORY_V1.md ✅

RAE_Lite_Profile.md 🆕 (lub ujednolicić istniejący plik)

API_DOCUMENTATION.md ✅

API_COOKBOOK.md 🆕

SDK_PYTHON_REFERENCE.md 🆕

CLI_AND_INTEGRATIONS.md 🆕

LLM_CONFIG_AND_COST_GUARD.md 🆕

ISO42001_IMPLEMENTATION_MAP.md 🆕

TEST_COVERAGE_MAP.md 🆕 (lub rozbudowa TESTING_STATUS.md)

SECURITY.md ✅

RAE-ISO_42001.md ✅

RAE-Risk-Register.md ✅

RAE-Roles.md ✅

Tak ułożone drzewo dokumentacji daje bardzo jasny sygnał:
„To nie jest tylko ładny README – to pełny, inżynierski produkt z governance, testami i klarowną mapą między teorią a kodem.”