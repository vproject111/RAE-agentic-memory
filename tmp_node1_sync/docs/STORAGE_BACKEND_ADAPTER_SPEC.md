📄 1) STORAGE_BACKEND_ADAPTER_SPEC.md

(Agnostyczna warstwa przechowywania danych w RAE + pełna telemetria)

STORAGE_BACKEND_ADAPTER_SPEC.md

Modularna, agnostyczna warstwa storage dla RAE (semantic, episodic, metadata) z pełną telemetrią

🎯 Cel

Aktualny RAE-core jest sprzęgnięty z Qdrant i Postgres.
To uniemożliwia:

skalowanie horyzontalne,

użycie alternatywnych baz,

uruchamianie RAE-mobile / RAE-lite bez ciężkich zależności,

pracę w środowiskach enterprise (gdzie narzucane są konkretne bazy),

integrację z HPC / Big Data,

testy z różnymi backendami.

Celem tego dokumentu jest zdefiniowanie adapterów storage, które:

oddzielają RAE od konkretnej technologii,

umożliwiają wybór backendu w konfiguracji,

integrują telemetrię OpenTelemetry na każdym poziomie operacji I/O,

zapewniają spójny model pamięci dla RAE-local, RAE-lite, RAE-mobile, RAE-server i RAE-cluster.

🧱 1. Architektura Storage Abstraction Layer

RAE wymaga trzech warstw pamięci:

Semantic Store – wektory + embeddingi + metadata

Episodic Store – zdarzenia, temporalne logi pamięci

Metadata Store – stan, rekordy, konfiguracje, graf wiedzy

Każda warstwa otrzyma osobny adapter, ale ich API musi być spójne pomiędzy backendami.

🧬 2. Interfejsy (Protocol)
2.1 SemanticStore
class SemanticStore(Protocol):
    async def add(self, record: SemanticRecord) -> str: ...
    async def search(self, query: VectorQuery) -> list[SemanticRecord]: ...
    async def update(self, record_id: str, data: dict) -> None: ...
    async def delete(self, record_id: str) -> None: ...
    async def stats(self) -> dict: ...

Telemetria wymagana:

czas operacji (histogram)

liczba rekordów dodanych / usuniętych

metadane zapytania (bez treści)

liczba wektorów zwróconych

rozkład odległości (min/avg/max)

błędy (counter)

2.2 EpisodicStore
class EpisodicStore(Protocol):
    async def append(self, event: EpisodicEvent) -> str: ...
    async def get_range(self, start_ts, end_ts) -> list[EpisodicEvent]: ...
    async def delete(self, event_id: str) -> None: ...
    async def stats(self) -> dict: ...

Telemetria wymagana:

liczba zapisanych eventów

średnia długość eventu

czas odczytu zakresu

liczba eventów per zakres

błędy I/O

2.3 MetadataStore
class MetadataStore(Protocol):
    async def get(self, id: str) -> dict | None: ...
    async def set(self, id: str, data: dict) -> None: ...
    async def search(self, filters: dict) -> list[dict]: ...
    async def delete(self, id: str) -> None: ...
    async def stats(self) -> dict: ...

Telemetria wymagana:

liczba operacji get/set/search

TTL hits/misses jeśli backend wspiera

czas wyszukiwania

liczba rekordów zwróconych

🔌 3. Backend Implementations (Iteracja 1–3)
ITERACJA 1 — Minimal viable abstraction

QdrantSemanticStore

PostgresMetadataStore

SQLiteMetadataStore (RAE-mobile, RAE-local)

SQLiteEpisodicStore

InMemorySemanticStore (fallback)

ITERACJA 2 — Enterprise & HPC

MilvusSemanticStore

WeaviateSemanticStore

PineconeSemanticStore

BigTableEpisodicStore

DynamoDBMetadataStore

ITERACJA 3 — Cloud-first

BigQueryVectorSearchStore

VertexMatchingEngineStore

AuroraMetadataStore

🗂️ 4. Struktura katalogów
/rae_core/
    storage/
        semantic/
            base.py
            qdrant_store.py
            milvus_store.py
            weaviate_store.py
            chroma_store.py
            inmemory_store.py

        episodic/
            base.py
            postgres_store.py
            sqlite_store.py
            bigtable_store.py
            dynamodb_store.py

        metadata/
            base.py
            postgres_store.py
            sqlite_store.py
            redisjson_store.py
            neo4j_store.py

        factory.py

⚙️ 5. Telemetria – wymagania globalne

Każdy adapter musi emitować:

Traces

storage.semantic.add

storage.semantic.search

storage.episodic.append

storage.metadata.get
…z pełnym czasem operacji i atrybutami.

Metrics

rae.storage.ops_total (counter)

rae.storage.latency_seconds (histogram)

rae.storage.errors_total (counter)

rae.storage.bytes_in / bytes_out

rae.storage.records_total

Atrybuty obowiązkowe

backend type (postgres/qdrant/milvus/etc.)

table/collection name

record_count

vector_dimension

query_top_k

result_count

🔄 6. Fabryka backendów
def create_storage(config: StorageConfig) -> StorageBundle:
    semantic = load_semantic_backend(config.semantic)
    episodic = load_episodic_backend(config.episodic)
    metadata = load_metadata_backend(config.metadata)
    return StorageBundle(semantic, episodic, metadata)

🚀 7. Wymagania dla RAE-mobile / RAE-local / RAE-server
Wersja	SemanticStore	MetadataStore	EpisodicStore
RAE-mobile	InMemory / Chroma	SQLite	SQLite
RAE-local	Qdrant / Chroma	SQLite/PG	SQLite/PG
RAE-server	Qdrant / Milvus	Postgres	Postgres
RAE-cluster	Milvus / Pinecone	Aurora/BigTable	BigTable/Dynamo
🧪 8. Testy obowiązkowe

Każdy backend musi przejść taki sam zestaw testów:

test_add_search_update_delete

test_vector_dimensions

test_range_queries

test_metadata_filters

test_concurrency

test_telemetry_emission

✔ Efekt końcowy

RAE jest storage-agnostic

działa na mobile, lokalnie, w chmurze, w klastrze

telemetria pozwala badać zachowanie pamięci

przygotowanie do RAE Cloud-native (multi-region, multi-backend)