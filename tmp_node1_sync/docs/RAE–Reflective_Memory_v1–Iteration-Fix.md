# RAE–Reflective_Memory_v1–Iteration-Fix-and-Polish-Plan  
_(kontynuacja: `RAE-Reflective_Memory_v1-Implementation.md`)_

**Stan bazowy:** `RAE-ReflectiveMemory-state-2025-11-27` + aktualny kod z `project_dump.txt`  
**Cel tej iteracji:** dopolerować implementację `Reflective Memory v1` tak, aby:

- była w pełni spójna z dokumentacją 4-warstwowej pamięci,
- była przewidywalna operacyjnie (decay, summarization, dreaming),
- była łatwa do użycia z poziomu agentów (ContextBuilder, Actor/Evaluator/Reflector),
- dało się ją z czystym sumieniem oznaczyć jako **stabilne v1**.

---

## 1. Zakres i definicja „Done”

### 1.1. Zakres iteracji

Ta iteracja nie dodaje nowych funkcji biznesowych, tylko:

1. **Porządkuje nazewnictwo i mapowanie warstw/typów pamięci** (`layer`, `memory_type` vs 4 poziomy).
2. **Domyka integrację Reflective Memory z pętlą agenta** (Actor–Evaluator–Reflector, ContextBuilder).
3. **Uszczelnia użycie feature flag i trybów (`lite` / `full`)**.
4. **Porządkuje worker’y utrzymaniowe** (decay, summarization, dreaming).
5. **Dodaje brakujące testy integracyjne + minimalną obserwowalność**.

### 1.2. Kryteria „Done”

Iterację uznajemy za zakończoną, gdy:

- [ ] Każdy element opisany w `REFLECTIVE_MEMORY_V1.md` ma _jednoznaczną_ reprezentację w kodzie (plik/klasa/funkcja) i jest to podlinkowane w dokumencie.
- [ ] Mapowanie 4 poziomów pamięci → `layer` + `memory_type` jest opisane w jednym miejscu i odsyłane z innych dokumentów.
- [ ] ContextBuilder **zawsze** używa `inject_reflections` (lub równoważnej logiki) w miejscach, gdzie to opisano.
- [ ] Feature flagi (`REFLECTIVE_MEMORY_ENABLED`, `REFLECTIVE_MEMORY_MODE`, `DREAMING_ENABLED`, `SUMMARIZATION_ENABLED` itd.) są faktycznie używane w kodzie.
- [ ] Worker’y utrzymaniowe mają:
  - [ ] przynajmniej 1 test integracyjny na każdy typ (decay, summarization, dreaming),
  - [ ] sensowne logowanie i metryki _co najmniej_ na poziomie liczby przetworzonych rekordów.
- [ ] Test integracyjny `Actor–Evaluator–Reflector flow` przechodzi w trybie CI i jest opisany w dokumencie.

---

## 2. Warstwy pamięci – ujednolicenie modelu

### 2.1. Problem

- W dokumentacji mówimy o **4 warstwach**:  
  Layer 1 – Sensory, Layer 2 – Working/STM, Layer 3 – LTM (episodic/semantic), Layer 4 – Reflective.
- W kodzie mamy:
  - `layer` (enum: `stm`, `ltm`, `em`, `rm`),
  - `memory_type` (np. `sensory`, `episodic`, `semantic`, `profile`, `reflection`, `strategy`).

Brakuje jednego, centralnego miejsca z **jawnie opisanym mapowaniem**.

### 2.2. Zadania

**[P0] Dodać sekcję „Model warstw pamięci w kodzie”**

- [ ] W nowym lub istniejącym dokumencie (np. `docs/REFLECTIVE_MEMORY_V1.md` lub osobnym `docs/MEMORY_MODEL.md`) dodać tabelkę:

  | Warstwa koncepcyjna | `layer` (enum) | `memory_type` typowe | Przykłady |
  |----------------------|----------------|-----------------------|-----------|
  | Layer 1 – Sensory    | `stm`          | `sensory`            | surowe eventy, logi, sensory |
  | Layer 2 – Working    | `stm` / `em`   | `episodic` (recent)  | bieżąca sesja, krótkoterminowy kontekst |
  | Layer 3 – LTM        | `ltm` / `em`   | `episodic`, `semantic`, `profile` | zakończone sesje, fakty, profil |
  | Layer 4 – Reflective | `rm`           | `reflection`, `strategy` | post-mortemy, lekcje, strategie |

- [ ] W każdym dokumencie, który używa pojęć „Layer 1/2/3/4”, wstawić link do tej tabelki.

**[P1] Ujednolicić komentarze w kodzie**

- [ ] W kluczowych modelach (DB, modele Pydantic) dopisać krótkie komentarze:

  - przy `layer`: „logiczna warstwa przetwarzania (STM/LTM/episodic/reflective) – patrz MEMORY_MODEL.md”,
  - przy `memory_type`: „funkcjonalny typ wspomnienia (sensory/episodic/semantic/profile/reflection/strategy) – patrz MEMORY_MODEL.md”.

---

## 3. ContextBuilder + wstrzykiwanie refleksji

### 3.1. Problem

- Plan zakłada, że **każdy agent**, który ma włączoną reflective memory, korzysta z kontekstu zawierającego:
  - profil,
  - lekcje (reflections/strategies),
  - relewantne wspomnienia (episodic/semantic),
  - ostatnie wiadomości.
- W dokumentacji jest helper `inject_reflections_into_prompt(...)`, ale trzeba upewnić się, że:
  - [ ] ContextBuilder rzeczywiście go używa,
  - [ ] wszystkie call-site’y agentów korzystają z **nowego** ContextBuildera.

### 3.2. Zadania

**[P0] Spiąć ContextBuilder z reflective memory**

- [ ] W `ContextBuilder.build_context(...)` dopilnować, że:
  - refleksje/strategie są zawsze pobierane przez `MemoryStore.search_memories(...)` z filtrem `memory_type in ["reflection", "strategy"]`,
  - limit tokenów na refleksje jest przestrzegany (konfiguracja z `.env`),
  - sekcja „Lessons Learned” jest zawsze obecna (choćby pusta) w strukturze `WorkingMemoryContext`.

- [ ] W Helpers (np. `inject_reflections_into_prompt(...)`) doprecyzować:
  - format sekcji (np. nagłówek `## Lessons Learned (Reflective Memory)`),
  - sposób łączenia refleksji (np. bullet listy, max X refleksji).

**[P1] Wymusić użycie ContextBuildera w agent loop**

- [ ] Przejrzeć wszystkie miejsca, w których agent buduje prompt (MCP, REST `/v1/agent/execute`, integracje z SDK).
- [ ] Upewnić się, że _wszędzie_ zamiast ręcznego składania promptu używany jest:

  ```python
  context = context_builder.build_context(...)
  prompt = context.to_prompt()  # lub równoważny helper
 Dodać krótki rozdział w REFLECTIVE_MEMORY_V1.md:
„Jak poprawnie używać ContextBuildera z reflective memory (przykład end-to-end)”.

4. Feature flagi i tryby lite / full
4.1. Problem
W dokumentacji opisane są:

REFLECTIVE_MEMORY_ENABLED – globalne włączenie/wyłączenie reflective memory,

REFLECTIVE_MEMORY_MODE – lite vs full,

DREAMING_ENABLED, SUMMARIZATION_ENABLED, progi importance itd.

Trzeba upewnić się, że każda z tych flag realnie wpływa na zachowanie kodu.

4.2. Zadania
[P0] Audyt i implementacja użycia flag

 W config.py zebrać wszystkie flagi dot. reflective memory i przypisać im domyślne wartości.

 W reflection_engine_v2, memory_maintenance.py, ContextBuilder:

warunkowo wykonywać:

generację refleksji (jeśli REFLECTIVE_MEMORY_ENABLED),

dreaming (jeśli DREAMING_ENABLED i tryb full),

summarization (jeśli SUMMARIZATION_ENABLED),

w trybie lite:

wyłączyć dreaming,

ograniczyć długość refleksji/tokenów,

ewentualnie skrócić okno historii dla analizy.

[P1] Dodać mały matrix zachowań do dokumentacji

 W REFLECTIVE_MEMORY_V1.md dodać tabelkę:

Flaga / Tryb	Efekt
REFLECTIVE_MEMORY_ENABLED=0	brak refleksji, brak sekcji „Lessons Learned”
REFLECTIVE_MEMORY_MODE=lite	brak dreaming, uproszczone summarization
REFLECTIVE_MEMORY_MODE=full	pełny pipeline (dreaming + summarization)
DREAMING_ENABLED=0	wyłączone dreaming niezależnie od trybu
SUMMARIZATION_ENABLED=0	brak episodic_summary

5. Worker’y utrzymaniowe: decay, summarization, dreaming
5.1. Problem
Kod workerów jest zaawansowany, ale:

trzeba do końca domknąć przewidywalność operacyjną,

zadbać o proste metryki/logi,

dołożyć testy integracyjne, które pokazują, że lifecycle pamięci działa jak w dokumentacji.

5.2. Zadania
[P0] Decay

 Upewnić się, że ImportanceScoringService.decay_importance(...):

nie degraduje „świeżych” wspomnień o wysokim access_count,

nie pozostawia nigdy importance < 0 (ustalić dolny limit, np. 0.01).

 Dodać metryki:

liczba rekordów zaktualizowanych,

średnia i max zmiana importance,

czas wykonania joba.

 Dodać test integracyjny:

wstawić kilka wspomnień z różnym wiekiem i importance,

odpalić decay,

asercja na oczekiwane zmiany (z tolerancją).

[P1] Summarization

 Ustalić progi: kiedy generujemy episodic_summary (np. liczba wiadomości w sesji, min importance).

 Dodać metrykę:

liczba wygenerowanych summary per run,

procent sesji z summary.

 Test integracyjny:

utworzyć długą sesję,

odpalić worker,

sprawdzić, że pojawiło się co najmniej jedno memory_type="episodic_summary" powiązane z session_id.

[P1] Dreaming

 Upewnić się, że Dreaming wybiera:

tylko wspomnienia powyżej pewnego progu importance,

nie generuje refleksji duplikujących istniejące (np. prosty check podobieństwa tekstowego).

 Dodać metryki:

liczba wybranych epizodów,

liczba wygenerowanych refleksji/strategii,

średnie importance epizodów vs importance refleksji.

 Test integracyjny:

przygotować epizody z wysokim importance,

odpalić dreaming,

sprawdzić, że powstały nowe reflection/strategy powiązane z tymi epizodami.

6. Actor–Evaluator–Reflector – dopięcie kontraktu
6.1. Problem
Koncepcja Actor–Evaluator–Reflector jest dobrze opisana, ale:

brakuje „twardego” kontraktu (interfejsu) dla Evaluatora,

trzeba sprawdzić, że test integracyjny rzeczywiście pokrywa cały przepływ.

6.2. Zadania
[P0] Interfejs Evaluatora

 Dodać prosty protokół / abstrakcyjną klasę Evaluator (np. w apps/memory_api/services/evaluation.py) z metodą:

python
Skopiuj kod
class EvaluationResult(BaseModel):
    outcome: OutcomeType  # success / failure / partial
    error_info: Optional[ErrorInfo]
    notes: Optional[str]
    importance_hint: Optional[float]
python
Skopiuj kod
class Evaluator(Protocol):
    def evaluate(self, execution_context: ExecutionContext) -> EvaluationResult:
        ...
 Zapewnić, że refleksje są odpalane na podstawie EvaluationResult, a nie ad-hoc.

[P1] Test integracyjny Actor–Evaluator–Reflector

 Uporządkować/test tests/integration/test_reflection_flow.py tak, aby scenariusz był jasny:

Actor wykonuje zadanie, które kończy się błędem.

Evaluator ocenia błąd i przekazuje EvaluationResult.

Reflector generuje refleksję/strategię i zapisuje do pamięci.

Kolejne zadanie korzysta z refleksji (ContextBuilder), co zmniejsza prawdopodobieństwo tej samej klasy błędu.

 W dokumentacji dopisać mini-sequence diagram (ASCII/mermaid) tego przepływu.

7. Testy, metryki, DX
7.1. Testy
[P0] Pokrycie krytycznych ścieżek

 Dodać sekcję w docs/TESTING_STATUS.md dedykowaną Reflective Memory:

lista testów integracyjnych (deklaratywnie),

krótkie opisy scenariuszy.

 Minimum:

test decay,

test summarization,

test dreaming,

test Actor–Evaluator–Reflector + ContextBuilder.

7.2. Metryki i logi
[P1] Minimalna obserwowalność

 W workerach dodać logi na poziomie INFO:

start/koniec joba,

liczba rekordów,

kluczowe parametry konfiguracji (np. progi importance).

 Eksportować podstawowe metryki do Prometheusa (jeśli już masz /metrics):

rae_reflective_decay_updated_total,

rae_reflective_summaries_created_total,

rae_reflective_dreaming_reflections_created_total.

8. Podsumowanie i plan wykonania
8.1. Kolejność realizacji
Model warstw i nazewnictwo (sekcja 2) – mały wysiłek, duży zysk mentalny.

ContextBuilder + użycie refleksji (sekcja 3) – klucz do realnych korzyści.

Feature flagi i tryby (sekcja 4) – ważne dla stabilności wdrożeń.

Worker’y utrzymaniowe + testy (sekcja 5).

Actor–Evaluator–Reflector kontrakt + test integracyjny (sekcja 6).

Testy + metryki (sekcja 7).

8.2. Efekt końcowy
Po tej iteracji:

dokumentacja 4-warstwowej pamięci i stan kodu są 1:1 spójne,

reflective memory działa w trybach lite i full,

agent loop konsekwentnie korzysta z refleksji,

worker’y utrzymaniowe są obserwowalne i przetestowane,

Reflective Memory v1 można oznaczyć jako stabilne wydanie i pokazywać na zewnątrz jako „feature complete”.