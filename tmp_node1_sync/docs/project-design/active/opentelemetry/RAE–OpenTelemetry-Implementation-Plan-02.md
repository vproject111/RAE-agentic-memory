<br>
Iteracja 2 – Instrumentacja Postgres, Redis, Qdrant
Cel

Uzyskać pełny wgląd w operacje pamięci, kolejki i baz danych.

Zakres

automatyczna instrumentacja asyncpg (Postgres)

instrumentacja Redis (cache + locking)

własne trace’y dla Qdrant (bo brak natywnej integracji)

dodanie atrybutów dla operacji pamięci

Do zrobienia

Instalacja:

opentelemetry-instrumentation-asyncpg
opentelemetry-instrumentation-redis


Dodać w main.py:

from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor

AsyncPGInstrumentor().instrument()
RedisInstrumentor().instrument()


Dodać wrapper Qdrant:

rae_core/observability/traced_qdrant.py

każde wywołanie Qdrant objęte span’em

atrybuty:

qdrant.collection

qdrant.operation

qdrant.vector_count

qdrant.latency_ms

Zaimplementować testy mockujące połączenia.

Testy
Jednostkowe

poprawna inicjalizacja instrumentorów

test wrappera Qdrant (czy tworzy span i nadaje atrybuty)

Integracyjne

query do Postgresa → trace w Collector

operacje Redis: SET, GET → trace

operacje Qdrant → trace z poprawnymi atrybutami

Kryteria ukończenia

Każda warstwa pamięci (Postgres, Redis, Qdrant) generuje trace’y.

Latencje są widoczne w exporterze.

Testy przechodzą.