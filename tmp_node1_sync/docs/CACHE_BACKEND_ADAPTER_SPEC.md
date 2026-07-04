📄 2) CACHE_BACKEND_ADAPTER_SPEC.md

(agnostyczny system cache + pełna telemetria)

CACHE_BACKEND_ADAPTER_SPEC.md

Agnostyczny system cache dla RAE + telemetria

🎯 Cel

Obecnie cache = Redis.
Docelowo musi być:

Redis

Dragonfly

KeyDB

Memcached

InMemory (mobile, lite)

Cloud Cache (AWS/GCP/Azure)

Cache musi wspierać uniform API + pełną telemetrię, aby RAE-mobile, RAE-local, RAE-server i RAE-cluster mogły się wymieniać stanem i optymalizować koszty tokenów.

🧩 1. Interfejs CacheBackend
class CacheBackend(Protocol):
    async def get(self, key: str) -> Any: ...
    async def set(self, key: str, value: Any, ttl: int | None = None) -> None: ...
    async def delete(self, key: str) -> None: ...
    async def exists(self, key: str) -> bool: ...
    async def increment(self, key: str, amount: int = 1) -> int: ...
    async def flush(self) -> None: ...
    async def stats(self) -> dict: ...

📊 2. Telemetria obowiązkowa
Traces

cache.get

cache.set

cache.delete

cache.increment

Metrics

rae.cache.ops_total

rae.cache.hits_total

rae.cache.misses_total

rae.cache.latency_seconds

rae.cache.error_total

rae.cache.bytes_stored

Atrybuty

backend_type

key_length

ttl

value_size_bytes

🧱 3. Implementacje backendów
Iteracja 1:

RedisCache

InMemoryCache

NoopCache

Iteracja 2:

DragonflyCache

KeyDBCache

MemcachedCache

Iteracja 3:

Cloud cache providers:

AWS ElastiCache

GCP MemoryStore

Azure Cache for Redis

🗂️ 4. Struktura katalogów
/rae_core/cache/
    base.py
    factory.py
    redis_backend.py
    dragonfly_backend.py
    memcached_backend.py
    memory_backend.py
    noop_backend.py

🧭 5. Integracja z RAE-mobile, RAE-local, RAE-server
Wersja	Domyślny cache
RAE-mobile	InMemoryCache
RAE-local	InMemory / Redis (opcjonalnie)
RAE-server	Redis / Dragonfly
RAE-cluster	Dragonfly / Cloud cache

Telemetria musi działać w każdej wersji, nawet bez zewnętrznego cache.

🧪 6. Testy obowiązkowe

get/set/delete/exists/inc/flush

TTL precision

concurrency

eviction policies (if backend supports)

telemetry presence in each call

✔ Efekt końcowy

RAE staje się cache-agnostic

działa w każdym środowisku

pozwala na multi-device memory sync

zachowuje pełną telemetrię

rozszerza filozofię „Memory OS”