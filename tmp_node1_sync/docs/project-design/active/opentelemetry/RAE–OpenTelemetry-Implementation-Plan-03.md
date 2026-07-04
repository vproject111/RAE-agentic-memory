<br>
Iteracja 3 – Instrumentacja Celery + Zadania Refleksji
Cel

Monitorować działanie agentów refleksji, pipeline’u zadań oraz błędy w workerach.

Zakres

instrumentacja Celery

span dla każdego zadania refleksji

integracja z pipeline pamięci refleksyjnej

eksport logów z trace-id

Do zrobienia

Instalacja:

opentelemetry-instrumentation-celery


Dodanie do celery_app.py:

from opentelemetry.instrumentation.celery import CeleryInstrumentor
CeleryInstrumentor().instrument()


Dodanie wrappera tasków:

każdy task otwiera span:

task.name

reflection.iteration

memory.layer

cost.tokens

Przepięcie loggera Celery, aby dodawał trace_id i span_id.

Testy zapewniają, że:

trace tworzy się automatycznie

błędy(worker crash) są eksportowane jako exception.event

Testy
Jednostkowe

span tworzony przy starcie tasku

logger poprawnie dodaje trace-id

Integracyjne

task Celery uruchomiony → widoczny trace

wyjątek w tasku → trace z eventem exception

E2E

cały pipeline refleksji (Evaluator → Polisher → Memory Update)
→ pełny trace w Jaegerze jako jeden łańcuch

Kryteria ukończenia

pełny monitoring zadań Celery

każdy cykl refleksji generuje spójny trace

błędy są widoczne w OTEL
