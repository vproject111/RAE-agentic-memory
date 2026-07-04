# LLM_ORCHESTRATOR.md
# LLM Orchestrator for RAE
## Cel i założenia

Celem LLM Orchestratora jest:

- **odklejenie core RAE od konkretnego modelu LLM** (brak „przyspawania” do jednego providera),
- umożliwienie użycia:
  - **0 LLM** (tryb bezmodelowy),
  - **1 LLM** (prosto i tanio),
  - **N LLM** (różni dostawcy / różne modele),
- zachowanie prostego, stabilnego **interfejsu dla core pamięci**.

Orchestrator jest **osobną warstwą** między RAE a światem modeli LLM.  
Core nie musi wiedzieć, ile jest modeli ani od kogo – widzi tylko **jeden logiczny „LLM Service”**.

---

## 1. Pozycja Orchestratora w architekturze

```text
+--------------------------+
|        RAE Core          |
|  4-layer memory, math,   |
|  reflection, GraphRAG    |
+------------+-------------+
             |
             v
+--------------------------+
|     LLM Orchestrator     |
|  (Single / Multi LLM)    |
+------------+-------------+
             |
   +---------+---------+
   |         |         |
   v         v         v
 Model A   Model B   Model C
 (API)     (API)     (local)
Zasada: RAE Core rozmawia tylko z Orchestrator-em, nigdy bezpośrednio z konkretnym LLM.

2. Interfejs Orchestratora
Minimalny kontrakt (pseudo-Python, nazwy do dostosowania):

python
Skopiuj kod
class LLMOrchestrator(Protocol):
    def generate(self, request: LLMRequest) -> LLMResponse: ...
    def score(self, request: LLMScoreRequest) -> LLMScoreResponse: ...
    def summarize(self, request: LLMSummarizeRequest) -> LLMResponse: ...
Przykładowa struktura żądania:

python
Skopiuj kod
@dataclass
class LLMRequest:
    prompt: str
    system_prompt: str | None = None
    context: dict[str, Any] | None = None
    tags: list[str] | None = None       # np. ["reflection", "summary"]
    strategy: str | None = None         # np. "single", "fallback", "ensemble"
Core:

nie wskazuje konkretnego modelu,

określa typ zadania (tagi, strategia),

dostaje jedną odpowiedź + metadane.

3. Konfiguracja: modele i strategie
Orchestrator czyta konfigurację z pliku (np. llm_config.yaml):

yaml
Skopiuj kod
default_strategy: single

models:
  - id: openai_gpt4o
    provider: openai
    enabled: true
    roles: [general, reflection, coding]
    cost_weight: 1.0

  - id: claude_opus
    provider: anthropic
    enabled: false
    roles: [analysis, legal]
    cost_weight: 1.2

  - id: local_qwen
    provider: ollama
    enabled: true
    roles: [low_cost, offline]
    cost_weight: 0.2

strategies:
  reflection:
    mode: single
    primary: openai_gpt4o

  summaries:
    mode: fallback
    primary: openai_gpt4o
    fallback: local_qwen

  analysis_heavy:
    mode: ensemble
    models: [openai_gpt4o, claude_opus]
Idee:

roles – miękkie etykiety, które pomagają Orchestratorowi dobrać model do zadania.

strategies – nazwy strategii, które Core może podać w request.strategy.

4. Tryby pracy Orchestratora
4.1. single
Najprostszy tryb, zgodny z obecnym podejściem:

wybierany jest jeden konkretny model (np. openai_gpt4o),

Orchestrator robi jedno wywołanie i zwraca wynik,

jeśli model jest niedostępny – Orchestrator może:

zwrócić błąd,

przełączyć się na globalny fallback (jeżeli jest zdefiniowany).

4.2. fallback
Orchestrator woła primary,

jeśli dostanie błąd / timeout – woła fallback,

wynik zawiera informację, który model faktycznie odpowiedział.

Zastosowanie:

środowiska produkcyjne z wymogiem wysokiej dostępności,

konfiguracje:

„chmurowy model” + „lokalny model” jako backup.

4.3. ensemble (współpraca / prosty multi-LLM)
Na starcie utrzymujemy prostotę:

2+ modeli dostaje to samo żądanie,

Orchestrator:

zbiera ich odpowiedzi,

może:

wybrać jedną wg prostych heurystyk (długość, spójność, score),

zwrócić wszystkie wraz z metadanymi do warstwy refleksji.

Docelowo ensemble może być rozszerzony o:

tryb competitive (modele rywalizują, refleksja wybiera),

tryb debate (modele wymieniają argumenty w kilku rundach).

Ale na poziomie Orchestratora nie wymuszamy całej złożonej debaty – to może być wyższy poziom logiki, jeśli będzie potrzebny.

5. Tryb no-LLM (bez modeli)
Orchestrator musi umieć działać w sytuacji, gdy:

nie ma skonfigurowanego żadnego modelu,

albo wszystkie są globalnie wyłączone (np. w JST / środowisku z ograniczeniami).

Zachowanie:

metody generate/summarize/score:

zwracają kontrolowany błąd typu LLMUnavailable,

lub zwracają prostą, techniczną odpowiedź, jeśli jest fallback oparty na regułach.

Core może:

oznaczać takie operacje jako „do uzupełnienia przez człowieka”,

albo w ogóle wyłączyć funkcje wymagające LLM.

Kluczowe założenie:

RAE musi działać sensownie, nawet gdy Orchestrator jest w trybie no-LLM.

6. Telemetria i koszty
Orchestrator jest też miejscem do zbierania metryk:

liczba wywołań per model,

koszt per model / per strategia,

czas odpowiedzi,

błędy.

Przykładowe metryki:

rae.llm.request_count{model_id, strategy}

rae.llm.latency_ms{model_id, strategy}

rae.llm.cost_token{model_id}

rae.llm.error_count{model_id, error_type}

Dzięki temu:

można porównywać modele między sobą,

można dynamicznie zmieniać strategie (np. częściej używać tańszego modelu, gdy jakość jest wystarczająca).

7. Plan wdrożenia (iteracje)
Iteracja 1 – Single + Fallback
Wprowadzenie Orchestratora jako warstwy pośredniej.

Implementacja:

single,

fallback.

Przekierowanie wszystkich wywołań LLM przez Orchestrator.

Proste metryki (czas, liczba wywołań).

Iteracja 2 – Prosty ensemble
Dodanie możliwości wołania 2+ modeli i porównywania wyników.

Wykorzystanie tego głównie w trybie badawczym / testowym.

Logowanie pełnych wyników do warstwy refleksji.

Iteracja 3 – Integracja z rozbudowanymi trybami refleksji
Warstwa refleksji może świadomie wybierać:

strategię (single, fallback, ensemble),

klasę modeli (np. „local-only”, „cloud-preferred”).

Ewentualne wprowadzenie prostych trybów „debate” na poziomie Orchestratora, jeśli okaże się to potrzebne.

8. Podsumowanie
LLM Orchestrator:

uwalnia core RAE od jednego, „przyspawanego” modelu,

pozwala:

działać bez LLM,

korzystać z jednego modelu,

lub wielu modeli,

daje miejsce na:

kontrolę kosztów,

metryki,

eksperymenty naukowe (multi-LLM),

nie komplikuje core – cała zmienność jest skoncentrowana w jednym module.