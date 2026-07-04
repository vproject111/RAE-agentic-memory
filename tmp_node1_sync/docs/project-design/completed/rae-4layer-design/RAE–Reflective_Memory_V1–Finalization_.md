# RAE–Reflective_Memory_V1–Finalization_Plan  
_(focus: things still “not fully tightened” around reflective memory)_

**Stan odniesienia:**  
- Kod po ostatnich poprawkach (`project_dump.txt`)  
- Dokumenty: `REFLECTIVE_MEMORY_V1.md`, `RAE-improve_01.md`, `RAE-improve-02.md`  
- Oznaczenie stanu: **RAE-ReflectiveMemory-state-2025-11-28-pre-Claude-fixes**

> 🔁 **WAŻNE DLA KOLEJNEJ ITERACJI (np. Claude):**  
> Zanim zmienisz kod, **ZAWSZE** najpierw sprawdź **stan faktyczny kodu**, a dopiero potem porównuj z dokumentacją.  
> Dokumenty mogły nie nadążyć za refaktorem – nie wolno zakładać, że to, co jest w `.md`, na pewno jest lub nie jest implementacją.

---

## 0. Procedura pracy w tej iteracji

**Krok 0 – Reality check (konieczne przed każdą większą zmianą)**

1. Przeskanuj repo lokalnie (Claude CLI / agent):  
   - struktura `apps/memory_api`,  
   - `services/`, `workers/`, `config`, `security`, `ContextBuilder`, testy integracyjne.
2. Dla każdego punktu poniżej:
   - najpierw **znajdź realną implementację w kodzie**,
   - zapisz krótko: `STAN: implemented / partial / missing`,
   - dopiero potem wprowadzaj zmiany.

Do wyniku tej iteracji dopisz krótki raport (w osobnym `.md`), gdzie dla każdego punktu z tego pliku podasz status po Twojej pracy.

---

## 1. Feature flagi & tryby reflective memory (`lite` / `full`)

**Cel:** Każda flaga i tryb opisany w dokumentacji **realnie wpływa** na zachowanie kodu.  
Bez martwych zmiennych konfiguracyjnych.

### 1.1. Audyt istniejących flag (stan faktyczny)

**Zadanie A1 – Inwentaryzacja:**

- Znajdź i wypisz wszystkie flagi dotyczące reflective memory i workerów:
  - `REFLECTIVE_MEMORY_ENABLED`
  - `REFLECTIVE_MEMORY_MODE` (`lite` / `full`)
  - `DREAMING_ENABLED`
  - `SUMMARIZATION_ENABLED`
  - progi importance, decay, token limits (np. `REFLECTIONS_MAX_TOKENS` itd.)
- Dla każdej flagi zanotuj:
  - gdzie jest zdefiniowana (config / settings),
  - gdzie jest używana (konkretny plik/funkcja),
  - czy wpływa na logikę, czy tylko „wisi”.

**Zadanie A2 – Dopiąć użycie flag:**

Doprowadź do stanu:

- `REFLECTIVE_MEMORY_ENABLED`:
  - jeśli `false` →  
    - nie generujemy nowych refleksji/strategii,  
    - ContextBuilder pomija sekcję „Lessons Learned” albo ją wyraźnie oznacza jako wyłączoną.
- `REFLECTIVE_MEMORY_MODE`:
  - `lite`:
    - brak dreaming (worker nie uruchamia lub kończy się natychmiast),
    - summarization only (lub mocno ograniczone),
    - brak cięższych operacji refleksji / meta-refleksji.
  - `full`:
    - pełny pipeline: decay + summarization + dreaming + refleksje.
- `DREAMING_ENABLED` / `SUMMARIZATION_ENABLED`:
  - realnie włączają/wyłączają odpowiednie worker’y, niezależnie od trybu.

**Zadanie A3 – Testy & dokumentacja:**

- Dodaj **mini testy** (nawet jeśli na początku będą bardziej integracyjne niż „ładne”):
  - `test_reflective_flags_disable_reflections_when_off()`
  - `test_reflective_lite_mode_no_dreaming()`
  - `test_reflective_full_mode_runs_all_workers()`
- Zaktualizuj w `REFLECTIVE_MEMORY_V1.md` tabelkę zachowań flag:
  - dopasuj do tego, jak kod faktycznie działa po zmianach,
  - usuń lub popraw wszystkie opisy, które już nie odpowiadają rzeczywistości.

---

## 2. Scheduler & maintenance: decay / summarization / dreaming

**Cel:** Algorytm importance/decay i worker’y są nie tylko zaimplementowane, ale też **realnie odpalane** i obserwowalne.

### 2.1. Decay

**Zadanie B1 – Sprawdzenie implementacji:**

- Zlokalizuj:
  - serwis odpowiedzialny za decay (np. `ImportanceScoringService.decay_importance`),
  - worker (np. `DecayWorker`),
  - scheduler (Celery / cron / moduł uruchamiany z CLI).
- Ustal:
  - czy istnieje rzeczywisty entrypoint (np. komenda CLI, task Celery) odpalający decay cyklicznie,
  - czy jest wykorzystywany w Docker Compose / K8s (np. osobny worker service).

**Zadanie B2 – Domknięcie schedulera:**

Jeżeli scheduler jest tylko „na papierze”:

- dodaj realny task (np. Celery) lub skrypt CLI:
  - `python -m apps.memory_api.workers.memory_maintenance decay`  
- upewnij się, że w `docker compose` / K8s jest proces, który go faktycznie uruchamia cyklicznie.

**Zadanie B3 – Logi & metryki:**

- Dodaj logi:
  - start/stop joba,
  - liczba rekordów zaktualizowanych,
  - średnia i max zmiana importance.
- Jeżeli jest `/metrics`:
  - eksportuj licznik typu `rae_reflective_decay_updated_total`.

---

### 2.2. Summarization

**Zadanie C1 – Sprawdzenie implementacji:**

- Znajdź worker summarization (np. `SummarizationWorker`) i jego wywołania.
- Zweryfikuj:
  - jakie są realne progi (długość sesji, importance),
  - gdzie powstają `memory_type="episodic_summary"`.

**Zadanie C2 – Dopiąć logikę progów:**

- Upewnij się, że summarization:
  - nie generuje summary dla każdej drobnej sesji,
  - działa głównie na długich / „ciężkich” sesjach (jak opisane w docs).

**Zadanie C3 – Test integracyjny:**

- Utwórz test, który:
  - tworzy kilka długich sesji,
  - odpala summarization,
  - sprawdza, że powstają `episodic_summary` powiązane z odpowiednimi `session_id`.

---

### 2.3. Dreaming (refleksje/strategie w tle)

**Zadanie D1 – Sprawdzenie implementacji:**

- Zlokalizuj `DreamingWorker` / odpowiednik.
- Sprawdź:
  - jak wybierane są epizody (importance/progi),
  - jak powstają `reflection` / `strategy`,
  - czy istnieje zabezpieczenie przed duplikatami (np. proste podobieństwo tekstowe / hash).

**Zadanie D2 – Zasady wyboru epizodów:**

- Jeżeli w kodzie brak twardych progów:
  - dodaj minimalne progi importance / recency,
  - upewnij się, że dreaming nie mieli całej tabeli przy każdym uruchomieniu.

**Zadanie D3 – Test integracyjny + metryki:**

- Test:
  - kilkanaście epizodów o wysokim importance,
  - uruchomić dreaming,
  - sprawdzić, że powstały nowe `reflection`/`strategy` z poprawnymi powiązaniami.
- Metryki/logi:
  - liczba wybranych epizodów,
  - liczba wygenerowanych refleksji,
  - średnie importance epizodów vs refleksji.

---

## 3. ContextBuilder & wstrzykiwanie refleksji do promptów

**Cel:** Każdy agent z reflective memory **korzysta z ContextBuildera**, a ten **zawsze** bierze pod uwagę refleksje i strategie.

### 3.1. Audyt call-site’ów

**Zadanie E1 – Znajdź wszystkie miejsca, gdzie budowany jest prompt:**

- API endpoints (`/v1/agent/execute`, inne agentowe ścieżki),
- integracje (MCP, SDK, context-watcher, inne usługi),
- ewentualne dedykowane „agent loops”.

**Dla każdego miejsca zanotuj:**

- czy używa `ContextBuilder.build_context(...)`,
- czy potem używa ujednoliconej metody `context.to_prompt()` / helpera,
- czy gdzieś jeszcze ręcznie składa się string z promptem.

### 3.2. Wymuszenie użycia ContextBuildera

**Zadanie E2 – Refaktoryzacja:**

- W każdym miejscu, które:
  - ma dostęp do `tenant_id`, `project_id`, `session_id` i „celu zadania”,
- wymuś schemat:

```python
context = context_builder.build_context(
    tenant_id=...,
    project_id=...,
    session_id=...,
    task_description="...",
    ...
)
prompt = context.to_prompt()  # lub równoważny helper
Usuń lub wycofaj wszystkie stare helpery, które składają prompt bez ContextBuildera (oznacz jako deprecated lub usuń).

3.3. Refleksje w ContextBuilderze
Zadanie E3 – Zapewnienie obecności refleksji:

Upewnij się, że build_context(...):

zawsze próbuje pobrać memory_type in ["reflection", "strategy"] z memory store,

szanuje limit tokenów i ewentualne progi importance,

tworzy sekcję w stylu ## Lessons Learned (Reflective Memory).

Jeśli reflective memory jest wyłączone:

sekcja powinna być albo pusta, albo z jasnym komunikatem (to pomaga debugować).

3.4. Test end-to-end
Zadanie E4 – Test integracyjny:

Przebieg:

Aktor wykonuje zadanie i „zawala” (błąd narzędzia / nieudane żądanie).

Evaluator ocenia wynik i tworzy EvaluationResult.

Reflector generuje refleksję/strategię i zapisuje ją do pamięci.

Kolejne wywołanie agenta:

korzysta z ContextBuildera,

w prompt jest widoczna wcześniejsza refleksja.

Test powinien sprawdzać:

że refleksja została faktycznie pobrana,

że jest użyta przy generowaniu promptu (np. przez asercję na fragment stringa).

4. Bezpieczeństwo & tenancy w kontekście pamięci
Cel: 4-warstwowa pamięć jest chroniona zgodnie z multi-tenant, a wyłączenie auth nie zostawia „dziur” w governance.

4.1. Audyt auth / tenant guard
Zadanie F1 – Sprawdzenie implementacji:

Znajdź:

aktualny mechanizm auth (JWT / API key / inny),

funkcje typu get_current_tenant, check_tenant_access.

Ustal:

czy wszystkie endpointy związane z pamięcią (store/query/reflect/governance) używają tych mechanizmów,

czy jest jakiś „bypass” dla DEBUG / AUTH_DISABLED.

4.2. Minimalne wymagania dla „almost enterprise”
Zadanie F2 – Dopięcie minimalnej ochrony:

Upewnij się, że:

endpointy pamięci (store/query/reflection/governance) nigdy nie działają w pełni otwarcie, nawet przy AUTH_DISABLED=true – w takim przypadku trzeba przynajmniej:

wymagać X-Tenant-ID,

nie mieszać danych między tenantami.

dostęp do governance / metrics / audit track:

wymaga co najmniej roli admin / system.

4.3. Krótki opis w dokumentacji
Zadanie F3 – Uczciwy opis stanu:

W Project maturity – why "almost enterprise":

dopisz podpunkt nt. bieżącego stanu bezpieczeństwa:

co jest (RLS, tenant_id w API),

czego jeszcze brakuje (np. brak kompleksowego audytu security, brak penetration tests),

jakie są bezpieczne konfiguracje dla PoC (np. dev/lab, nie internet bez reverse proxy).

5. Raport z tej iteracji
Po zakończeniu prac nad tym plikiem:

Utwórz nowy plik, np. docs/RAE-ReflectiveMemory_v1-Finalization-REPORT.md.

Dla każdej sekcji z tego planu (1–4) zapisz:

Co sprawdziłeś w kodzie (stan przed): 1–3 zdania + kluczowe pliki.

Co zmieniłeś: zwięzła lista commit-level (np. „dodałem Celery task X”, „usunięto helper Y”).

Stan po: done / partial / postponed.

Zaktualizuj STATUS.md i/lub REFLECTIVE_MEMORY_V1.md:

tak, żeby nowa dokumentacja odzwierciedlała stan faktyczny po tej iteracji.

6. Definicja końca „almost enterprise” dla reflective memory
Uznajemy, że Reflective Memory V1 jest „dopięta” gdy:

 Wszystkie flagi i tryby mają pokrycie w kodzie i testach.

 Decay/summarization/dreaming mają realny scheduler, metryki i minimalne testy.

 Wszystkie agent entrypointy korzystają z ContextBuildera i refleksji.

 Dostęp do pamięci jest spójny z modelem multi-tenant i minimalnie bezpieczny.

 Dokumentacja (REFLECTIVE_MEMORY_V1 + README + STATUS) odpowiada realnemu stanowi kodu.

Po spełnieniu tych warunków reflective memory przestaje być „ładnym planem” i staje się gotowym, bez wstydu prezentowalnym modułem – również przed znajomymi z dużych firm.