# RAE-–Reflective_Memory_v1-Implementation-Plan

**Status:** draft → v1  
**Dotyczy stanu kodu:** `RAE-state-553ab2984` (referencyjny)  
**Cel:** wdrożenie pierwszej produkcyjnej wersji 4-warstwowej pamięci refleksyjnej w RAE, opartej o Postgres + Qdrant (vector + graph), bez dokładania nowych ciężkich baz (Neo4j itp.).

---

## 1. Zakres i cele

### 1.1. Co budujemy

W tej iteracji wdrażamy:

1. **Spójną implementację 4-warstwowej pamięci:**
   - Warstwa 1 – **Sensory** (wejścia/wyjścia, eventy).
   - Warstwa 2 – **Working / Short-Term** (context builder).
   - Warstwa 3 – **Long-Term (Episodic + Semantic)** w Postgres + Qdrant.
   - Warstwa 4 – **Reflective Memory** (lessons learned, strategie, post-mortemy).

2. **Reflective Engine v1:**
   - Minimalny cykl **Actor → Evaluator → Reflector** jako wzorzec,
   - Generowanie refleksji dla:
     - niepowodzeń (błędy narzędzi / testów),
     - sukcesów (wartościowe strategie),
   - Zapis refleksji jako osobnego typu pamięci + linki w Qdrant.

3. **Spójny scoring pamięci:**
   - funkcja łącząca:
     - **Relevance** (similarity),
     - **Importance** (LLM-driven, 1–10),
     - **Recency** (czas + decay + access_count),
   - wykorzystana w retrieval dla LTM + refleksji.

4. **Asynchroniczne zadania wspierające:**
   - aktualizacja `importance` / decay,
   - proste rekursywne sumaryzacje,
   - “lekki dreaming” (batchowe refleksje z historii sesji).

### 1.2. Czego *nie* robimy w tej iteracji

- Nie wprowadzamy dodatkowych silników grafowych (Neo4j, Memgraph).
- Nie budujemy pełnego Agentic Knowledge Graph z osobnym serwisem.
- Nie integrujemy jeszcze LangGraph jako głównego runtime (może być osobny eksperyment).

---

## 2. Architektura – widok wysokopoziomowy

### 2.1. Warstwy pamięci (model logiczny)

Definicja warstw w RAE:

- **Layer 1 – Sensory**  
  Surowe eventy: wiadomości, tool-calls, logi, telemetry.

- **Layer 2 – Working / Short-Term**  
  Złożony kontekst:
  - ostatnie N wiadomości,
  - wybrane pamięci LTM,
  - refleksje “lessons learned”,
  - profil użytkownika/systemu.

- **Layer 3 – Long-Term Memory**  
  Trwałe wspomnienia:
  - **episodic** – historia interakcji / zadań,
  - **semantic** – dokumenty, notatki, wiedza statyczna,
  - **profile** – preferencje, konfiguracja,
  - przechowywane w:
    - Postgres (treść + metadata + importance + recency),
    - Qdrant (embedding + linki grafowe).

- **Layer 4 – Reflective Memory**  
  Wyższy poziom:
  - **reflections** – wnioski po błędach / sukcesach,
  - **strategies** – stabilne reguły postępowania,
  - reprezentowane jako:
    - rekordy w Postgres (`memory_type="reflection"` / `"strategy"`),
    - powiązane edge’ami w Qdrant z eventami, błędami, sesjami.

---

## 3. Model danych

### 3.1. Postgres – tabela pamięci (uogólnienie)

Jeżeli już istnieje tabela `memory_items` / `memories`, rozszerzamy ją w taki sposób, by wspierała wszystkie warstwy.

#### 3.1.1. Proponowany schemat (koncepcyjny)

Tabela: `memory_items`

| Kolumna              | Typ              | Opis |
|----------------------|------------------|------|
| id                   | UUID             | klucz główny |
| tenant_id            | UUID             | multi-tenant isolation |
| session_id           | UUID (nullable)  | powiązanie z sesją (głównie episodic/sensory/reflective) |
| memory_type          | TEXT             | `sensory`, `episodic`, `semantic`, `profile`, `reflection`, `strategy` |
| layer                | INT              | 1–4 (redundantne dla szybkich filtrów) |
| content              | TEXT             | główna treść pamięci |
| metadata             | JSONB            | dodatkowe informacje (tags, source_tool, error_code, etc.) |
| importance           | FLOAT            | 0–1 / 1–10 (do ustalenia, ale spójne) |
| created_at           | TIMESTAMP        | czas utworzenia |
| last_accessed_at     | TIMESTAMP        | ostatni dostęp (NULL dla nieużywanych) |
| access_count         | INT              | liczba przywołań |
| qdrant_point_id      | UUID / TEXT      | ID punktu w Qdrant (dla tych, które mają embedding) |

**TODO:**
- [ ] Potwierdzić istniejący schemat i dopasować nazwy kolumn.
- [ ] Dodać brakujące kolumny migracjami (jeśli potrzeba).
- [ ] Ustalić docelowy zakres `importance` (np. `0.0–1.0` lub `1–10`).

### 3.2. Qdrant – kolekcje i graf

W Qdrant mamy już:

- **kolekcję wektorową** (np. `rae_memories`) przechowującą:
  - embedding (`vector`),
  - payload (zawierający `memory_item_id`, `tenant_id`, `memory_type`, `tags`),
- **linki grafowe**:
  - powiązania między punktami (`linked points`).

#### 3.2.1. Standard payload dla punktu w kolekcji pamięci

```json
{
  "memory_item_id": "uuid",
  "tenant_id": "uuid",
  "memory_type": "episodic | semantic | reflection | strategy",
  "layer": 3,
  "session_id": "uuid or null",
  "tags": ["sql", "timeout", "error", "reflection"],
  "source": "ingest | chat | tool | reflector",
  "error_type": "TimeoutError",
  "confidence": 0.87
}
3.2.2. Przykładowe typy powiązań (graf)
event → reflection (geneza refleksji),

error → strategy (strategia naprawcza),

reflection → strategy (ewolucja myśli),

memory_item ↔ memory_item (podobieństwo / kontynuacja).

TODO:

 Ustalić konwencję typów powiązań (edge_type w payload/metadata).

 Dodać helpery w repo Qdrant do tworzenia/aktualizacji linków.

4. Interfejsy i serwisy
4.1. MemoryStore / MemoryRepository
Cel: jeden spójny interfejs do pracy z pamięcią, niezależnie od warstwy.

4.1.1. Minimalny kontrakt (Python)
python
Skopiuj kod
class MemoryStore(Protocol):
    def store_memory(
        self,
        tenant_id: UUID,
        memory_type: str,
        content: str,
        metadata: dict | None = None,
        importance: float | None = None,
        session_id: UUID | None = None,
        layer: int | None = None,
        embed: bool = True,
    ) -> MemoryItem: ...

    def search_memories(
        self,
        tenant_id: UUID,
        query: str | None,
        query_embedding: list[float] | None,
        filters: dict | None,
        limit: int = 10,
        include_reflections: bool = True,
    ) -> list[MemoryItemWithScore]: ...

    def record_access(self, memory_id: UUID) -> None: ...
TODO:

 Zweryfikować istniejący interfejs MemoryRepository i dopasować.

 Dodać parametry layer, memory_type, importance tam, gdzie brak.

4.2. ReflectiveEngine
Nowy serwis odpowiedzialny za generowanie refleksji.

4.2.1. Kontrakt
python
Skopiuj kod
class ReflectiveEngine(Protocol):
    async def generate_reflection(
        self,
        tenant_id: UUID,
        session_id: UUID | None,
        context: ReflectionContext,
    ) -> ReflectionResult: ...
Gdzie:

python
Skopiuj kod
@dataclass
class ReflectionContext:
    events: list[Event]           # kroki aktora, tool_calls, odpowiedzi
    outcome: Outcome              # SUCCESS / FAILURE / PARTIAL
    error: ErrorInfo | None       # kod błędu, traceback, itp.
    task_description: str | None  # wysokopoziomowy cel
python
Skopiuj kod
@dataclass
class ReflectionResult:
    reflection_text: str          # opis co poszło nie tak / co działa
    strategy_text: str | None     # reguła postępowania (jeśli możliwa)
    importance: float             # 0–1 / 1–10
    confidence: float             # 0–1
    tags: list[str]
TODO:

 Zdefiniować ReflectionContext na podstawie aktualnych struktur (trace/log).

 Napisać pierwszą implementację opartą o LLM (prompt refleksyjny).

 Wpiąć ReflectiveEngine w pipeline obsługi błędów / zakończenia zadań.

5. Scoring: Relevance + Importance + Recency
5.1. Funkcja scoringu
Zaimplementować spójną funkcję scoringu dla retrieval:

python
Skopiuj kod
def compute_memory_score(
    similarity: float,     # relevance: np. cosinus
    importance: float,     # 0–1
    last_accessed_at: datetime | None,
    created_at: datetime,
    access_count: int,
    now: datetime,
    base_decay_rate: float = 0.001,
) -> float:
    ...
Szkic algorytmu:

Recency / decay:

python
Skopiuj kod
time_ref = last_accessed_at or created_at
time_diff = (now - time_ref).total_seconds()

effective_decay = base_decay_rate / (math.log(1 + access_count) + 1)
recency_component = math.exp(-effective_decay * time_diff)
Agregacja:

python
Skopiuj kod
alpha, beta, gamma = 0.5, 0.3, 0.2  # do kalibracji
score = alpha * similarity + beta * importance + gamma * recency_component
TODO:

 Dodać tę funkcję do MemoryRepository / serwisu retrieval.

 Ustawić rozsądne domyślne wartości alpha/beta/gamma.

 Dodać testy jednostkowe i prosty benchmark.

6. Pętla Actor – Evaluator – Reflector (v1)
6.1. Actor
Już istnieje jako główny LLM-backend:

przyjmuje:

context (Working Memory),

system prompt,

generuje:

odpowiedź,

opcjonalnie wewnętrzny trace (myśli, narzędzia).

TODO:

 Zdefiniować standardowy ActorContext i ActorResult (jeśli jeszcze nie ma).

6.2. Evaluator
W v1 wspieramy 2 przypadki:

Deterministyczny evaluator:

np. testy, walidacja JSON, status narzędzi (success/failure).

LLM-evaluator:

prompt oceniający: “Czy ta odpowiedź jest poprawna / pomocna / bezpieczna?”,

zwraca structured JSON z polami: is_ok, reasons, score.

TODO:

 Wprowadzić prosty interfejs Evaluator z evaluate(actor_result, context).

6.3. Reflector
Schemat:

Po zakończeniu tasku:

jeśli Evaluator → is_ok = False lub score poniżej progu → wywołujemy ReflectiveEngine.

ReflectiveEngine:

tworzy ReflectionResult,

zapisuje:

reflection_text jako memory_type="reflection", layer=4,

strategy_text (jeśli jest) jako memory_type="strategy", layer=4,

tworzy powiązania w Qdrant:

event → reflection,

error → strategy.

TODO:

 Dodać hook w pipeline tasków, który odpala refleksję w odpowiednich momentach.

 Zadbać o logowanie (INFO/DEBUG) dla audytu.

7. Wykorzystanie Refleksji w kontekście (Working Memory)
7.1. Retrieval refleksji
Przy budowie kontekstu (ContextBuilder / MemoryService):

Na podstawie zapytania (user query, task_description):

generujemy embedding,

wykonujemy zapytanie do MemoryStore.search_memories z filtrami:

memory_type in ["reflection", "strategy"],

tenant_id itp.

Zwracamy np. 3–5 najlepiej dopasowanych refleksji/strategii.

7.2. Wstrzykiwanie do promptu
W system prompt / kontekście tworzymy blok:

text
Skopiuj kod
# Lessons learned (internal reflective memory)

- [SQL / Timeouts] W tym środowisku należy unikać SELECT * bez LIMIT – domyślnie stosuj paginację.
- [Python / Style] Użytkownik preferuje kod z type-hintami i zgodny z PEP-8.
- [Tools / Retries] Jeśli narzędzie X wywołało kilka time-outów, rozważ użycie narzędzia Y lub mniejszego batcha.
TODO:

 Dodać do ContextBuilder etap inject_reflections(...).

 Zadbać o limit tokenów (np. maks 512–1024 tokenów na refleksje).

8. Zadania asynchroniczne (worker)
8.1. Decay + importance update
Co jakiś czas (np. co godzinę / noc):

pobieramy:

pamięci o niskim access_count i starym last_accessed_at,

aktualizujemy:

importance (np. delikatne obniżenie),

ewentualnie flagujemy do archiwizacji.

TODO:

 Dodać job update_memory_decay (Celery / inny worker).

 Konfigurowalne progi i częstotliwość.

8.2. Rekursywna sumaryzacja sesji
Dla długich sesji:

gdy liczba eventów > N:

generujemy sumaryczny wpis memory_type="episodic_summary",

zawiera:

najważniejsze fakty o użytkowniku,

postępy w realizacji celu,

potencjalne wnioski (light-reflection).

TODO:

 Dodać job session_summarization.

 Wpiąć to jako krok po zamknięciu sesji lub nocny batch.

8.3. Lekki “dreaming”
Na etapie v1 – minimalna wersja:

okresowo (np. raz dziennie) losujemy kilka epizodów o wysokiej importance z ostatnich X godzin,

prosimy LLM:

“Zidentyfikuj powtarzające się błędy / działania i zaproponuj 1–3 strategie ogólne”,

zapisujemy je jako:

memory_type="reflection" / "strategy",

importance wysokie,

powiązania grafowe w Qdrant.

9. Konfiguracja i feature flagi
9.1. Konfiguracja
Dodać sekcję w configu (np. rae_settings):

REFLECTIVE_MEMORY_ENABLED: bool = True

REFLECTIVE_MAX_ITEMS_PER_QUERY: int = 5

REFLECTIVE_LESSONS_TOKEN_BUDGET: int = 1024

MEMORY_BASE_DECAY_RATE: float = 0.001

MEMORY_SCORE_WEIGHTS: {alpha, beta, gamma}

9.2. Tryby pracy
Mode: lite

refleksje generowane tylko na błędach krytycznych,

brak “dreamingu”, minimalny overhead.

Mode: full

refleksje na błędach + “ważnych” sukcesach,

sumaryzacje sesji,

podstawowy “dreaming”.

TODO:

 Dodać prosty mechanizm przełączania trybu w configu/env.

10. Testy i walidacja
10.1. Testy jednostkowe
scoring:

różne kombinacje relevance/importance/recency,

ReflectiveEngine:

poprawna struktura ReflectionResult przy różnych kontekstach,

MemoryStore:

zachowanie record_access (inkrementacja + update timestamps).

10.2. Testy integracyjne
scenariusz “błąd narzędzia”:

Actor wywołuje tool → błąd,

Evaluator oznacza failure,

Reflector generuje refleksję,

refleksja pojawia się w pamięci,

kolejne zadanie korzysta z refleksji w kontekście.

scenariusz “preferencje użytkownika”:

użytkownik kilka razy prosi o określony styl,

refleksja “user preference”,

kolejne odpowiedzi od razu uwzględniają preferencję bez przypominania.

10.3. Obserwowalność
logi:

kiedy generowana jest refleksja,

kiedy używana jest refleksja w kontekście,

jaki scoring ma dana pamięć przy retrieval.

metryki:

liczba refleksji na dzień / tenant,

procent odpowiedzi, w których użyto refleksji.

11. Plan wdrożenia (kroki)
Przegląd aktualnego modelu danych:

zmapowanie istniejącej tabeli pamięci na powyższy schemat,

przygotowanie migracji (jeśli potrzebne).

Wdrożenie scoringu i update access:

implementacja compute_memory_score,

adaptacja retrieval do nowego scoringu,

testy.

Implementacja ReflectiveEngine v1:

definicja ReflectionContext i ReflectionResult,

pierwsza implementacja LLM-based,

wpięcie w pipeline błędów / zakończonych zadań.

Wstrzykiwanie refleksji do kontekstu:

rozbudowa ContextBuilder o sekcję “Lessons learned”,

kontrola budżetu tokenów.

Zadania asynchroniczne (v1):

update_memory_decay,

session_summarization.

Feature flags i konfiguracja:

REFLECTIVE_MEMORY_ENABLED,

tryb lite / full.

Testy integracyjne + docs:

opis w API_DOCUMENTATION.md / ARCHITECTURE.md,

przykładowe scenariusze “jak działa refleksja”.

12. Roadmapa po v1 (opcjonalna)
v1.1 – bardziej zaawansowane szablony promptów refleksji (domenowe).

v1.2 – bardziej rozbudowany “dreaming” (klastrowanie epizodów).

v2.0 – opcjonalny Enterprise Reflective Graph:

bogatsza semantyka grafu,

integracja z LangGraph,

być może osobny moduł / repo.