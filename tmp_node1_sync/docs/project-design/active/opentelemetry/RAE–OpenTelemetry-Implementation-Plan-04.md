



<br>
Iteracja 4 – Deep Observability: Reflective Memory + Semantic/Graph RAG
Cel

Monitorować najważniejszy element RAE: procesy rozumowania i interakcje agentów.

To będzie przewaga RAE nad zwykłymi frameworkami RAG.

Zakres

dedykowane span’y dla 4 warstw pamięci:

episodic

semantic

graph

reflective

mierzenie:

koszt tokenów

głębokość reasoning loop

ilość operacji na grafie

trace’y łączone w cały cykl myślenia RAE

Do zrobienia

Dodać dekorator:

@trace_memory(layer="semantic")

@trace_memory(layer="graph")

zapisuje:

layer

operation

vector_count

graph_nodes

graph_edges

reasoning.depth

tokens.input

tokens.output

Owinąć nim:

Semantic Memory operations

Graph Memory operations

Reflective Memory pipeline

Dodać wrapper na Evaluator i Polisher, aby każdy krok reasoning był spanem-childem.

Testy snapshotowe — porównują tree struktury trace.

Testy
Jednostkowe

dekorator tworzy span z poprawnymi atrybutami

testy tokenów → poprawnie agregowane

Integracyjne

wywołanie reasoning pipeline → pełna struktura w trace

E2E

agentic loop (3 iteracje refleksji)
→ timeline w Jaegerze: parent → child → child → child

Performance Benchmarks

narzut telemetrii < 8% (sprawdzane w profilach CPU)

Kryteria ukończenia

pełny obraz rozumowania RAE

korelacja wszystkich operacji w jednym trace-id

analityka reasoning, kosztów tokenów i grafu działa

Finalne Korzyści po 4 iteracjach

✔ 100% pokrycie telemetrią wszystkich kluczowych komponentów
✔ możliwość analizy reasoning pipeline w czasie rzeczywistym
✔ przewaga nad standardowymi RAG (Trace Graph Reasoning)
✔ pełna zgodność z architekturą AI Factory Core (OTEL-first)
✔ przygotowanie pod ISO 42001 i audyty operacyjne