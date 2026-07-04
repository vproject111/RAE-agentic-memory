🧠 RAE Architecture Refactoring Plan v2
RAE Ecosystem: Core + Server + Lite + Mobile
Wersja: 2.0
Data: 2025-12-08
Autor: Plan przygotowany dla projektu RAE-agentic-memory

📋 Spis treści

Wizja ekosystemu RAE
Analiza obecnego stanu RAE
RAE-core - serce ekosystemu
RAE-Server (obecne "Duże RAE")
RAE-Lite - lokalna instalka bez Dockera
RAE-Mobile - wersja mobilna
RAE-Sync - protokół synchronizacji
Browser Extension (opcjonalne)
Plan refaktoryzacji
Mapowanie plików
Harmonogram


1. Wizja ekosystemu RAE
1.1 Architektura ekosystemu
┌─────────────────────────────────────────────────────────────────────────────┐
│                           RAE ECOSYSTEM                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│                         ┌─────────────────┐                                 │
│                         │    RAE-core     │                                 │
│                         │  (Pure Python)  │                                 │
│                         │   pip install   │                                 │
│                         │                 │                                 │
│                         │ • 4 Memory Layers│                                │
│                         │ • 3 Math Layers │                                 │
│                         │ • Hybrid Search │                                 │
│                         │ • Reflection    │                                 │
│                         │ • Interfaces    │                                 │
│                         └────────┬────────┘                                 │
│                                  │                                          │
│            ┌─────────────────────┼─────────────────────┐                    │
│            │                     │                     │                    │
│            ▼                     ▼                     ▼                    │
│   ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐          │
│   │   RAE-Server    │   │    RAE-Lite     │   │   RAE-Mobile    │          │
│   │                 │   │                 │   │                 │          │
│   │ 🐳 Docker/K8s   │   │ 💻 .exe/.app    │   │ 📱 iOS/Android  │          │
│   │ 🐘 PostgreSQL   │   │ 📦 SQLite       │   │ 📦 SQLite       │          │
│   │ 🔍 Qdrant       │   │ 🔍 sqlite-vec   │   │ 🔍 ONNX/CoreML  │          │
│   │ ⚡ Redis        │   │ 🤖 Ollama opt.  │   │ 🤖 On-device    │          │
│   │ 🌐 FastAPI      │   │ 🖥️ Tray App     │   │ 📲 Native UI    │          │
│   │ 👥 Multi-tenant │   │ 👤 Single user  │   │ 👤 Single user  │          │
│   │ ☁️ Cloud/On-prem│   │ 💾 Local-first  │   │ 💾 Local-first  │          │
│   └────────┬────────┘   └────────┬────────┘   └────────┬────────┘          │
│            │                     │                     │                    │
│            └─────────────────────┼─────────────────────┘                    │
│                                  │                                          │
│                         ┌────────▼────────┐                                 │
│                         │    RAE-Sync     │                                 │
│                         │   (Protocol)    │                                 │
│                         │                 │                                 │
│                         │ • Lite ↔ Server │                                 │
│                         │ • Mobile ↔ Lite │                                 │
│                         │ • Mobile ↔ Srvr │                                 │
│                         │ • E2E encryption│                                 │
│                         │ • CRDT merging  │                                 │
│                         └─────────────────┘                                 │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                     OPTIONAL EXTENSIONS                                     │
│                                                                             │
│   ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐          │
│   │ Browser Plugin  │   │   MCP Server    │   │  IDE Extension  │          │
│   │ (ChatGPT, etc.) │   │ (Cursor, etc.)  │   │ (VSCode, etc.)  │          │
│   │                 │   │                 │   │                 │          │
│   │ Łączy się z:    │   │ Łączy się z:    │   │ Łączy się z:    │          │
│   │ • RAE-Lite      │   │ • RAE-Server    │   │ • RAE-Lite      │          │
│   │ • RAE-Server    │   │ • RAE-Lite      │   │ • RAE-Server    │          │
│   └─────────────────┘   └─────────────────┘   └─────────────────┘          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
1.2 Produkty w ekosystemie
ProduktTargetStorageDeploymentUsersLLMRAE-coreDevelopers- (library)pip install rae-core-Interface onlyRAE-ServerTeams, EnterprisePostgreSQL + QdrantDocker/K8sMulti-tenantCloud APIsRAE-LiteIndywidualniSQLite.exe/.app installerSingle userOllama/NoneRAE-MobileMobile usersSQLiteApp Store/PlaySingle userOn-device
1.3 Kluczowe zasady architektury
ZasadaOpisRAE-core = Single Source of Truth100% logiki pamięci w jednym pakiecie PythonStorage agnosticInterfejsy abstrakcyjne, adaptery dla konkretnych bazLLM optionalKażdy produkt może działać BEZ LLM (rule-based fallback)Offline-firstRAE-Lite i RAE-Mobile działają w pełni offlineSync optionalKażda instancja niezależna, sync to opt-in featurePrivacy by defaultDane lokalne, sync tylko gdy user włączyNo vendor lock-inMożliwość migracji między produktami
1.4 Scenariusze użycia
Scenariusz 1: Indywidualny developer
─────────────────────────────────────
[RAE-Lite na laptopie] ← jedyny komponent
    • Przechwytuje rozmowy z ChatGPT/Claude (browser plugin)
    • Lokalna pamięć w SQLite
    • Ollama dla refleksji (opcjonalnie)
    • Zero kosztów, zero chmury


Scenariusz 2: Developer + Mobile
─────────────────────────────────────
[RAE-Lite na laptopie] ←──sync──→ [RAE-Mobile na telefonie]
    • Sync przez RAE-Sync (P2P w LAN lub przez relay)
    • Dostęp do pamięci z obu urządzeń
    • Nadal zero chmury (LAN sync)


Scenariusz 3: Zespół w firmie
─────────────────────────────────────
[RAE-Server (Docker)] ←──API──→ [RAE-Lite u developerów]
                      ←──API──→ [RAE-Mobile u użytkowników]
    • Centralny serwer z PostgreSQL
    • Multi-tenant (zespoły, projekty)
    • Developerzy mają lokalne kopie (sync)
    • RBAC, audit logs, compliance


Scenariusz 4: Enterprise + Compliance
─────────────────────────────────────
[RAE-Server (K8s)] ←──mTLS──→ [RAE-Server repliki]
    • High availability
    • ISO 42001 compliance
    • Governance dashboard
    • Cost control

2. Analiza obecnego stanu RAE
2.1 Obecna struktura (z README)
RAE-agentic-memory/
├── apps/
│   ├── memory_api/          # 🎯 Główna logika - TUTAJ JEST CORE
│   │   ├── core/            # ⭐ Math layers, scoring
│   │   ├── services/        # ⭐ HybridSearch, Reflection, Context
│   │   ├── repositories/    # DAO pattern (Postgres specific)
│   │   ├── models/          # Pydantic + SQLAlchemy models
│   │   ├── routers/         # FastAPI endpoints
│   │   └── tasks/           # Celery workers
│   ├── ml_service/          # ML microservice
│   ├── reranker-service/    # Reranking service
│   └── llm/                 # LLM Orchestrator
├── sdk/python/              # Python SDK
├── integrations/            # MCP, LangChain, Ollama
├── infra/                   # Docker, Prometheus
├── tools/memory-dashboard/  # Streamlit dashboard
├── docker compose.yml       # Full stack
├── docker compose.lite.yml  # Docker Lite (nie to samo co RAE-Lite!)
└── ...
2.2 Co mamy vs czego potrzebujemy
KomponentObecnieDocelowoLogika pamięciW apps/memory_api/Wydzielone do rae-coreStoragePostgreSQL hardcodedInterfejsy + adapteryVector DBQdrant hardcodedInterfejsy + adapteryLLMOpenAI/AnthropicInterfejsy + adapteryAPIFastAPI w coreFastAPI tylko w RAE-ServerDesktop appBrakRAE-Lite (.exe)Mobile appBrakRAE-Mobile (future)SyncBrakRAE-Sync protokół
2.3 Istniejące docker compose.lite.yml
⚠️ Uwaga: Obecny docker compose.lite.yml to mniejszy Docker stack, nie instalka .exe!
docker compose.lite.ymlRAE-Lite (nowy)Docker containersSingle .exe filePostgreSQLSQLiteQdrantsqlite-vecWymaga DockerZero dependenciesDla developerówDla end-users

3. RAE-core
3.1 Cel RAE-core
RAE-core to czysta biblioteka Python zawierająca:

100% logiki 4-warstwowej pamięci
100% logiki 3-warstwowej matematyki
100% logiki hybrid search
100% logiki reflection engine
0% infrastruktury (brak FastAPI, Postgres, Docker)

3.2 Struktura pakietu
rae-core/
├── pyproject.toml
├── README.md
├── LICENSE
│
└── rae_core/
    ├── __init__.py
    ├── py.typed                    # PEP 561 type hints
    ├── version.py
    │
    ├── engine.py                   # 🎯 RAEEngine - główny entry point
    │
    ├── models/                     # 📦 Modele danych (Pydantic only)
    │   ├── __init__.py
    │   ├── memory.py              # MemoryItem, MemoryLayer, MemoryType
    │   ├── graph.py               # GraphNode, GraphEdge
    │   ├── reflection.py          # Reflection, ReflectionPolicy
    │   ├── search.py              # SearchQuery, SearchResult, SearchWeights
    │   ├── context.py             # WorkingContext, ContextWindow
    │   ├── scoring.py             # ScoringWeights, QualityMetrics
    │   └── sync.py                # SyncState, SyncDelta (dla RAE-Sync)
    │
    ├── layers/                     # 🧠 4-warstwowa architektura
    │   ├── __init__.py
    │   ├── base.py                # AbstractMemoryLayer
    │   ├── sensory.py             # Layer 1: Sensory Memory
    │   ├── working.py             # Layer 2: Working Memory
    │   ├── longterm.py            # Layer 3: Long-Term (Episodic + Semantic)
    │   └── reflective.py          # Layer 4: Reflective Memory
    │
    ├── math/                       # 🔢 3-warstwowa matematyka
    │   ├── __init__.py
    │   ├── controller.py          # MathLayerController
    │   ├── math1_structure.py     # Structure Analysis
    │   ├── math2_dynamics.py      # Dynamics Tracking
    │   ├── math3_policy.py        # Policy Optimization
    │   └── metrics.py             # All metrics classes
    │
    ├── search/                     # 🔍 Hybrid Search Engine
    │   ├── __init__.py
    │   ├── engine.py              # HybridSearchEngine
    │   ├── strategies/
    │   │   ├── __init__.py
    │   │   ├── base.py            # AbstractSearchStrategy
    │   │   ├── vector.py          # VectorSearchStrategy
    │   │   ├── graph.py           # GraphTraversalStrategy
    │   │   ├── sparse.py          # SparseVectorStrategy
    │   │   └── fulltext.py        # FullTextStrategy
    │   ├── query_analyzer.py      # Query intent classification
    │   ├── fusion.py              # Result fusion
    │   └── cache.py               # Search cache logic (interface)
    │
    ├── reflection/                 # 🎭 Reflection Engine V2
    │   ├── __init__.py
    │   ├── engine.py              # ReflectionEngine
    │   ├── actor.py               # Actor component
    │   ├── evaluator.py           # Evaluator component
    │   └── reflector.py           # Reflector component
    │
    ├── context/                    # 📝 Context Building
    │   ├── __init__.py
    │   ├── builder.py             # ContextBuilder
    │   └── window.py              # ContextWindow management
    │
    ├── scoring/                    # 📊 Memory Scoring
    │   ├── __init__.py
    │   ├── scorer.py              # MemoryScoringV2
    │   └── decay.py               # ImportanceDecay
    │
    ├── interfaces/                 # 🔌 Abstrakcyjne interfejsy (DI)
    │   ├── __init__.py
    │   ├── storage.py             # IMemoryStorage
    │   ├── vector.py              # IVectorStore
    │   ├── graph.py               # IGraphStore
    │   ├── cache.py               # ICacheProvider
    │   ├── llm.py                 # ILLMProvider
    │   ├── embedding.py           # IEmbeddingProvider
    │   └── sync.py                # ISyncProvider (dla RAE-Sync)
    │
    ├── llm/                        # 🤖 LLM abstraction (bez providerów)
    │   ├── __init__.py
    │   ├── orchestrator.py        # LLMOrchestrator
    │   ├── strategies.py          # Single, Fallback strategies
    │   ├── fallback.py            # NoLLM rule-based fallback
    │   └── config.py              # LLMConfig
    │
    ├── sync/                       # 🔄 Sync protocol (core logic)
    │   ├── __init__.py
    │   ├── protocol.py            # SyncProtocol
    │   ├── diff.py                # Memory diff calculation
    │   ├── merge.py               # CRDT-based merging
    │   └── encryption.py          # E2E encryption helpers
    │
    ├── config/                     # ⚙️ Configuration
    │   ├── __init__.py
    │   ├── settings.py            # RAESettings (pydantic-settings)
    │   └── defaults.py            # Default values
    │
    ├── exceptions/                 # ❌ Exceptions
    │   ├── __init__.py
    │   └── errors.py              # RAEError hierarchy
    │
    └── utils/                      # 🛠️ Utilities
        ├── __init__.py
        ├── hashing.py             # Content hashing
        ├── temporal.py            # Timestamp utils
        └── validation.py          # Input validation
3.3 Główny interfejs RAEEngine
python# rae_core/engine.py

from typing import Optional, List
from .interfaces.storage import IMemoryStorage
from .interfaces.vector import IVectorStore
from .interfaces.graph import IGraphStore
from .interfaces.llm import ILLMProvider
from .interfaces.embedding import IEmbeddingProvider
from .interfaces.cache import ICacheProvider
from .interfaces.sync import ISyncProvider

from .models.memory import MemoryItem, MemoryLayer
from .models.search import SearchQuery, SearchResult
from .models.reflection import Reflection

from .layers.sensory import SensoryLayer
from .layers.working import WorkingLayer
from .layers.longterm import LongTermLayer
from .layers.reflective import ReflectiveLayer

from .search.engine import HybridSearchEngine
from .reflection.engine import ReflectionEngine
from .context.builder import ContextBuilder
from .math.controller import MathController


class RAEEngine:
    """
    Main entry point for RAE memory system.
    
    Usage:
        # Minimal (no LLM, in-memory)
        engine = RAEEngine(
            storage=InMemoryStorage(),
            vector_store=NumpyVectorStore()
        )
        
        # Full (with LLM, persistent)
        engine = RAEEngine(
            storage=SQLiteStorage("~/.rae/memory.db"),
            vector_store=SQLiteVecStore("~/.rae/memory.db"),
            graph_store=SQLiteGraphStore("~/.rae/memory.db"),
            llm_provider=OllamaProvider(),
            embedding_provider=SentenceTransformerProvider()
        )
    """
    
    def __init__(
        self,
        # Required
        storage: IMemoryStorage,
        vector_store: IVectorStore,
        
        # Optional
        graph_store: Optional[IGraphStore] = None,
        cache_provider: Optional[ICacheProvider] = None,
        llm_provider: Optional[ILLMProvider] = None,
        embedding_provider: Optional[IEmbeddingProvider] = None,
        sync_provider: Optional[ISyncProvider] = None,
        
        # Config
        tenant_id: str = "default",
        enable_math_layers: bool = True,
        enable_reflection: bool = True,
    ):
        self.storage = storage
        self.vector_store = vector_store
        self.graph_store = graph_store
        self.cache = cache_provider
        self.llm = llm_provider
        self.embedding = embedding_provider
        self.sync = sync_provider
        
        self.tenant_id = tenant_id
        
        # Initialize layers
        self.sensory = SensoryLayer(storage)
        self.working = WorkingLayer(storage)
        self.longterm = LongTermLayer(storage, graph_store)
        self.reflective = ReflectiveLayer(storage, llm_provider)
        
        # Initialize engines
        self.search = HybridSearchEngine(
            vector_store=vector_store,
            graph_store=graph_store,
            cache=cache_provider
        )
        
        if enable_reflection and llm_provider:
            self.reflection = ReflectionEngine(llm_provider, storage)
        else:
            self.reflection = None
        
        if enable_math_layers:
            self.math = MathController(storage, vector_store)
        else:
            self.math = None
        
        self.context_builder = ContextBuilder(
            storage=storage,
            search=self.search,
            reflection=self.reflection
        )
    
    # ─────────────────────────────────────────────────────────
    # Core API
    # ─────────────────────────────────────────────────────────
    
    async def store(
        self,
        content: str,
        layer: MemoryLayer = MemoryLayer.SENSORY,
        source: Optional[str] = None,
        metadata: Optional[dict] = None,
        **kwargs
    ) -> str:
        """
        Store new memory.
        
        Args:
            content: Memory content
            layer: Target layer (default: sensory)
            source: Source identifier (e.g., "chatgpt", "user")
            metadata: Additional metadata
            
        Returns:
            Memory ID
        """
        memory = MemoryItem(
            content=content,
            layer=layer,
            tenant_id=self.tenant_id,
            source=source,
            metadata=metadata or {}
        )
        
        # Store in appropriate layer
        if layer == MemoryLayer.SENSORY:
            memory_id = await self.sensory.store(memory)
        elif layer == MemoryLayer.WORKING:
            memory_id = await self.working.store(memory)
        elif layer == MemoryLayer.LONGTERM:
            memory_id = await self.longterm.store(memory)
        else:
            memory_id = await self.reflective.store(memory)
        
        # Generate and store embedding
        if self.embedding:
            embedding = await self.embedding.embed(content)
            await self.vector_store.upsert(
                id=memory_id,
                vector=embedding,
                metadata={"tenant_id": self.tenant_id, "layer": layer.value}
            )
        
        return memory_id
    
    async def query(
        self,
        query: str,
        top_k: int = 10,
        layers: Optional[List[MemoryLayer]] = None,
        include_reflections: bool = True,
        **kwargs
    ) -> List[SearchResult]:
        """
        Query memories using hybrid search.
        
        Args:
            query: Search query
            top_k: Number of results
            layers: Filter by layers (default: all)
            include_reflections: Include relevant reflections
            
        Returns:
            List of search results
        """
        search_query = SearchQuery(
            text=query,
            tenant_id=self.tenant_id,
            top_k=top_k,
            layer_filter=layers
        )
        
        # Get embedding for query
        query_embedding = None
        if self.embedding:
            query_embedding = await self.embedding.embed(query)
            search_query.embedding = query_embedding
        
        # Execute hybrid search
        results = await self.search.search(search_query)
        
        return results
    
    async def build_context(
        self,
        query: str,
        max_tokens: int = 4000,
        **kwargs
    ) -> str:
        """
        Build working context for LLM prompt.
        
        Args:
            query: Current query/task
            max_tokens: Max context size
            
        Returns:
            Formatted context string
        """
        return await self.context_builder.build(
            query=query,
            tenant_id=self.tenant_id,
            max_tokens=max_tokens
        )
    
    async def reflect(
        self,
        trigger: str = "scheduled",
        **kwargs
    ) -> List[Reflection]:
        """
        Generate reflections from recent memories.
        
        Args:
            trigger: What triggered reflection
            
        Returns:
            List of generated reflections
        """
        if not self.reflection:
            return []
        
        return await self.reflection.generate(
            tenant_id=self.tenant_id,
            trigger=trigger
        )
    
    async def consolidate(self) -> dict:
        """
        Run memory consolidation (STM → LTM promotion).
        
        Returns:
            Stats about consolidated memories
        """
        stats = {
            "promoted": 0,
            "decayed": 0,
            "pruned": 0
        }
        
        # Promote important memories from working to long-term
        promoted = await self.working.consolidate_to(self.longterm)
        stats["promoted"] = len(promoted)
        
        # Run decay on long-term memories
        if self.math:
            decayed = await self.math.run_decay()
            stats["decayed"] = decayed
        
        return stats
    
    # ─────────────────────────────────────────────────────────
    # Sync API (for RAE-Sync)
    # ─────────────────────────────────────────────────────────
    
    async def get_sync_state(self) -> dict:
        """Get current sync state for synchronization."""
        if not self.sync:
            raise NotImplementedError("Sync not configured")
        return await self.sync.get_state(self.tenant_id)
    
    async def apply_sync_delta(self, delta: dict) -> dict:
        """Apply sync delta from remote."""
        if not self.sync:
            raise NotImplementedError("Sync not configured")
        return await self.sync.apply_delta(self.tenant_id, delta)
3.4 Interfejsy (przykłady)
python# rae_core/interfaces/storage.py

from abc import ABC, abstractmethod
from typing import List, Optional, AsyncIterator
from ..models.memory import MemoryItem, MemoryLayer


class IMemoryStorage(ABC):
    """Abstract interface for memory storage."""
    
    @abstractmethod
    async def store(self, memory: MemoryItem) -> str:
        """Store memory, return ID."""
        pass
    
    @abstractmethod
    async def get(self, memory_id: str) -> Optional[MemoryItem]:
        """Get memory by ID."""
        pass
    
    @abstractmethod
    async def update(self, memory_id: str, updates: dict) -> bool:
        """Update memory fields."""
        pass
    
    @abstractmethod
    async def delete(self, memory_id: str) -> bool:
        """Delete memory."""
        pass
    
    @abstractmethod
    async def list(
        self,
        tenant_id: str,
        layer: Optional[MemoryLayer] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[MemoryItem]:
        """List memories with filters."""
        pass
    
    @abstractmethod
    async def count(
        self,
        tenant_id: str,
        layer: Optional[MemoryLayer] = None
    ) -> int:
        """Count memories."""
        pass
    
    # For sync
    @abstractmethod
    async def get_changes_since(
        self,
        tenant_id: str,
        since_timestamp: str
    ) -> AsyncIterator[MemoryItem]:
        """Get memories changed since timestamp (for sync)."""
        pass
python# rae_core/interfaces/vector.py

from abc import ABC, abstractmethod
from typing import List, Optional
from ..models.search import SearchResult


class IVectorStore(ABC):
    """Abstract interface for vector storage."""
    
    @abstractmethod
    async def upsert(
        self,
        id: str,
        vector: List[float],
        metadata: Optional[dict] = None
    ) -> None:
        """Upsert vector."""
        pass
    
    @abstractmethod
    async def search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        filters: Optional[dict] = None
    ) -> List[SearchResult]:
        """Vector similarity search."""
        pass
    
    @abstractmethod
    async def delete(self, id: str) -> bool:
        """Delete vector."""
        pass
    
    @abstractmethod
    async def get_vector(self, id: str) -> Optional[List[float]]:
        """Get vector by ID."""
        pass
python# rae_core/interfaces/llm.py

from abc import ABC, abstractmethod
from typing import List, Optional, AsyncIterator
from dataclasses import dataclass


@dataclass
class LLMResponse:
    content: str
    model: str
    tokens_used: int
    finish_reason: str


class ILLMProvider(ABC):
    """Abstract interface for LLM providers."""
    
    @abstractmethod
    async def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """Generate completion."""
        pass
    
    @abstractmethod
    async def stream(
        self,
        prompt: str,
        system: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream completion."""
        pass
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Current model name."""
        pass
    
    @property
    @abstractmethod
    def supports_functions(self) -> bool:
        """Whether model supports function calling."""
        pass
3.5 Zależności RAE-core
toml# rae-core/pyproject.toml

[project]
name = "rae-core"
version = "0.1.0"
description = "Core library for RAE (Reflective Agentic-memory Engine)"
readme = "README.md"
license = {text = "Apache-2.0"}
requires-python = ">=3.10"
authors = [
    {name = "Dreamsoft", email = "contact@dreamsoft.pro"}
]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: Apache Software License",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]

dependencies = [
    "pydantic>=2.0,<3.0",
    "pydantic-settings>=2.0,<3.0",
    "numpy>=1.24,<2.0",
    "typing-extensions>=4.0",
]

[project.optional-dependencies]
# Minimal in-memory implementations for testing
testing = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
    "pytest-cov>=4.0",
]

# Development tools
dev = [
    "mypy>=1.0",
    "ruff>=0.1",
    "black>=23.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["rae_core"]
Kluczowe: Zero zależności na FastAPI, SQLAlchemy, psycopg2, qdrant-client, redis!

4. RAE-Server
4.1 Cel
RAE-Server to obecne "Duże RAE" - pełny serwer z Docker, PostgreSQL, Qdrant.
Po refaktoryzacji będzie używać RAE-core jako biblioteki.
4.2 Struktura po refaktoryzacji
RAE-agentic-memory/              # Repozytorium główne
├── rae-core/                    # Git submodule lub monorepo package
│   └── ...                      # (struktura z sekcji 3)
│
├── rae-server/                  # RAE Server package
│   ├── pyproject.toml
│   └── rae_server/
│       ├── __init__.py
│       ├── main.py              # FastAPI app
│       │
│       ├── adapters/            # Implementacje interfejsów
│       │   ├── __init__.py
│       │   ├── storage/
│       │   │   ├── postgres.py  # PostgresMemoryStorage(IMemoryStorage)
│       │   │   └── models.py    # SQLAlchemy models
│       │   ├── vector/
│       │   │   └── qdrant.py    # QdrantVectorStore(IVectorStore)
│       │   ├── graph/
│       │   │   └── postgres.py  # PostgresGraphStore(IGraphStore)
│       │   ├── cache/
│       │   │   └── redis.py     # RedisCacheProvider(ICacheProvider)
│       │   ├── llm/
│       │   │   ├── openai.py    # OpenAIProvider(ILLMProvider)
│       │   │   ├── anthropic.py # AnthropicProvider(ILLMProvider)
│       │   │   ├── ollama.py    # OllamaProvider(ILLMProvider)
│       │   │   └── ...
│       │   └── embedding/
│       │       ├── openai.py    # OpenAIEmbedding(IEmbeddingProvider)
│       │       └── local.py     # SentenceTransformerEmbedding
│       │
│       ├── routers/             # FastAPI routers
│       │   ├── __init__.py
│       │   ├── memory.py
│       │   ├── search.py
│       │   ├── reflection.py
│       │   ├── sync.py          # Sync API endpoints
│       │   └── admin.py
│       │
│       ├── middleware/          # FastAPI middleware
│       │   ├── auth.py
│       │   ├── tenant.py
│       │   └── rate_limit.py
│       │
│       ├── tasks/               # Celery tasks
│       │   ├── decay.py
│       │   ├── reflection.py
│       │   └── sync.py
│       │
│       ├── dependencies/        # FastAPI DI
│       │   └── engine.py        # get_rae_engine() dependency
│       │
│       └── config.py            # Server-specific config
│
├── apps/                        # Legacy location (deprecated, redirect)
│   └── memory_api/ → ../rae-server/
│
├── infra/                       # Docker infrastructure
├── integrations/                # MCP, LangChain, etc.
├── tools/                       # Dashboard
├── docker compose.yml
└── ...
4.3 Adapter przykład (PostgreSQL)
python# rae_server/adapters/storage/postgres.py

from typing import List, Optional, AsyncIterator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

from rae_core.interfaces.storage import IMemoryStorage
from rae_core.models.memory import MemoryItem, MemoryLayer

from .models import MemoryORM  # SQLAlchemy model


class PostgresMemoryStorage(IMemoryStorage):
    """PostgreSQL implementation of IMemoryStorage."""
    
    def __init__(self, session_factory):
        self.session_factory = session_factory
    
    async def store(self, memory: MemoryItem) -> str:
        async with self.session_factory() as session:
            orm_obj = MemoryORM(
                id=memory.id,
                content=memory.content,
                layer=memory.layer.value,
                memory_type=memory.memory_type.value,
                tenant_id=memory.tenant_id,
                project_id=memory.project_id,
                source=memory.source,
                importance=memory.importance,
                decay_rate=memory.decay_rate,
                tags=memory.tags,
                metadata=memory.metadata,
                created_at=memory.created_at
            )
            session.add(orm_obj)
            await session.commit()
            return memory.id
    
    async def get(self, memory_id: str) -> Optional[MemoryItem]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(MemoryORM).where(MemoryORM.id == memory_id)
            )
            orm_obj = result.scalar_one_or_none()
            if orm_obj:
                return self._to_model(orm_obj)
            return None
    
    async def list(
        self,
        tenant_id: str,
        layer: Optional[MemoryLayer] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[MemoryItem]:
        async with self.session_factory() as session:
            query = select(MemoryORM).where(
                MemoryORM.tenant_id == tenant_id
            )
            if layer:
                query = query.where(MemoryORM.layer == layer.value)
            
            query = query.order_by(MemoryORM.created_at.desc())
            query = query.limit(limit).offset(offset)
            
            result = await session.execute(query)
            return [self._to_model(row) for row in result.scalars()]
    
    # ... other methods
    
    def _to_model(self, orm: MemoryORM) -> MemoryItem:
        return MemoryItem(
            id=orm.id,
            content=orm.content,
            layer=MemoryLayer(orm.layer),
            # ... map all fields
        )

5. RAE-Lite
5.1 Cel
RAE-Lite to samodzielna aplikacja desktopowa:

💻 Instalowana jak zwykły program (.exe na Windows, .app na macOS)
📦 Zero zależności zewnętrznych (bez Docker, bez serwera)
💾 Wszystkie dane lokalnie w SQLite
🤖 Opcjonalne LLM przez Ollama lub bez LLM
🔌 Opcjonalny browser plugin do przechwytywania rozmów
🔄 Opcjonalna synchronizacja z RAE-Server lub innymi RAE-Lite

5.2 Architektura RAE-Lite
┌─────────────────────────────────────────────────────────────────────────┐
│                         RAE-Lite Application                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                     System Tray Application                       │  │
│  │  ┌─────────┐  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐  │  │
│  │  │  Tray   │  │   Quick     │  │   Settings  │  │    Status    │  │  │
│  │  │  Icon   │  │   Search    │  │   Window    │  │   Monitor    │  │  │
│  │  └─────────┘  └─────────────┘  └─────────────┘  └──────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                    │                                    │
│  ┌─────────────────────────────────┴─────────────────────────────────┐  │
│  │                      Local HTTP Server                            │  │
│  │                    (localhost:8765)                               │  │
│  │  • REST API (for browser plugin)                                  │  │
│  │  • WebSocket (for real-time updates)                              │  │
│  │  • MCP Protocol (for IDE integration)                             │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                    │                                    │
│  ┌─────────────────────────────────┴─────────────────────────────────┐  │
│  │                        RAE-core Engine                            │  │
│  │                                                                   │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │  │
│  │  │ 4 Memory    │  │ Hybrid      │  │ Reflection  │               │  │
│  │  │ Layers      │  │ Search      │  │ Engine      │               │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘               │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │  │
│  │  │ 3 Math      │  │ Context     │  │ Scoring &   │               │  │
│  │  │ Layers      │  │ Builder     │  │ Decay       │               │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘               │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                    │                                    │
│  ┌─────────────────────────────────┴─────────────────────────────────┐  │
│  │                      SQLite Adapters                              │  │
│  │                                                                   │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────────┐  │  │
│  │  │ SQLiteMemory    │  │ SQLiteVector    │  │ SQLiteGraph      │  │  │
│  │  │ Storage         │  │ Store           │  │ Store            │  │  │
│  │  │                 │  │ (sqlite-vec)    │  │                  │  │  │
│  │  └─────────────────┘  └─────────────────┘  └──────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                    │                                    │
│  ┌─────────────────────────────────┴─────────────────────────────────┐  │
│  │                   ~/.rae-lite/memory.db                           │  │
│  │                      (Single SQLite file)                         │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                      Optional Components                          │  │
│  │                                                                   │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐   │  │
│  │  │ Ollama LLM  │  │ RAE-Sync    │  │ Local Embedding Model   │   │  │
│  │  │ (optional)  │  │ (optional)  │  │ (all-MiniLM-L6-v2)      │   │  │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────┘   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
5.3 Struktura projektu RAE-Lite
rae-lite/
├── pyproject.toml
├── README.md
├── LICENSE
│
├── rae_lite/
│   ├── __init__.py
│   ├── main.py                     # Entry point
│   ├── version.py
│   │
│   ├── app/                        # Desktop application
│   │   ├── __init__.py
│   │   ├── tray.py                 # System tray (pystray)
│   │   ├── windows/
│   │   │   ├── __init__.py
│   │   │   ├── search.py           # Quick search window
│   │   │   ├── settings.py         # Settings window
│   │   │   └── status.py           # Status/monitoring
│   │   └── resources/
│   │       ├── icons/
│   │       └── styles/
│   │
│   ├── server/                     # Local HTTP server
│   │   ├── __init__.py
│   │   ├── app.py                  # FastAPI app (localhost only)
│   │   ├── routers/
│   │   │   ├── memory.py
│   │   │   ├── search.py
│   │   │   └── plugin.py           # For browser plugin
│   │   └── websocket.py            # Real-time updates
│   │
│   ├── adapters/                   # SQLite adapters
│   │   ├── __init__.py
│   │   ├── storage.py              # SQLiteMemoryStorage
│   │   ├── vector.py               # SQLiteVectorStore (sqlite-vec)
│   │   ├── graph.py                # SQLiteGraphStore
│   │   └── cache.py                # In-memory LRU cache
│   │
│   ├── embedding/                  # Local embeddings
│   │   ├── __init__.py
│   │   ├── sentence_transformer.py # sentence-transformers
│   │   └── onnx.py                 # ONNX runtime (lighter)
│   │
│   ├── llm/                        # Optional LLM
│   │   ├── __init__.py
│   │   ├── ollama.py               # Ollama adapter
│   │   └── none.py                 # No-LLM fallback
│   │
│   ├── sync/                       # RAE-Sync client
│   │   ├── __init__.py
│   │   ├── client.py               # Sync client
│   │   └── discovery.py            # LAN discovery (mDNS)
│   │
│   └── config/
│       ├── __init__.py
│       └── settings.py             # Pydantic settings
│
├── browser-plugin/                 # Optional browser extension
│   ├── manifest.json
│   ├── background.js
│   ├── content-scripts/
│   │   ├── chatgpt.js
│   │   ├── claude.js
│   │   ├── gemini.js
│   │   └── ...
│   └── popup/
│
├── scripts/
│   ├── build_exe.py                # PyInstaller build
│   ├── build_installer.py          # NSIS/WiX installer
│   └── build_macos.py              # macOS .app bundle
│
└── tests/
5.4 SQLite Adapters
python# rae_lite/adapters/storage.py

import sqlite3
import json
import aiosqlite
from pathlib import Path
from typing import List, Optional, AsyncIterator
from datetime import datetime

from rae_core.interfaces.storage import IMemoryStorage
from rae_core.models.memory import MemoryItem, MemoryLayer, MemoryType


class SQLiteMemoryStorage(IMemoryStorage):
    """SQLite implementation of IMemoryStorage for RAE-Lite."""
    
    def __init__(self, db_path: str = "~/.rae-lite/memory.db"):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialized = False
    
    async def _ensure_initialized(self):
        if self._initialized:
            return
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    layer TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    tenant_id TEXT NOT NULL DEFAULT 'local',
                    project_id TEXT,
                    source TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT,
                    accessed_at TEXT,
                    importance REAL DEFAULT 0.5,
                    relevance_score REAL,
                    decay_rate REAL DEFAULT 0.01,
                    tags TEXT,
                    related_ids TEXT,
                    metadata TEXT,
                    -- For sync
                    sync_version INTEGER DEFAULT 0,
                    deleted_at TEXT
                )
            """)
            
            # Indexes
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_layer 
                ON memories(layer, tenant_id)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_created 
                ON memories(created_at DESC)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_sync 
                ON memories(sync_version)
            """)
            
            await db.commit()
        
        self._initialized = True
    
    async def store(self, memory: MemoryItem) -> str:
        await self._ensure_initialized()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO memories 
                (id, content, layer, memory_type, tenant_id, project_id,
                 source, created_at, updated_at, importance, decay_rate,
                 tags, related_ids, metadata, sync_version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 
                        COALESCE((SELECT sync_version FROM memories WHERE id = ?), 0) + 1)
            """, (
                memory.id,
                memory.content,
                memory.layer.value if isinstance(memory.layer, MemoryLayer) else memory.layer,
                memory.memory_type.value if isinstance(memory.memory_type, MemoryType) else memory.memory_type,
                memory.tenant_id,
                memory.project_id,
                memory.source,
                memory.created_at.isoformat(),
                datetime.utcnow().isoformat(),
                memory.importance,
                memory.decay_rate,
                json.dumps(memory.tags),
                json.dumps(memory.related_ids),
                json.dumps(memory.metadata),
                memory.id  # For sync_version subquery
            ))
            await db.commit()
        
        return memory.id
    
    async def get(self, memory_id: str) -> Optional[MemoryItem]:
        await self._ensure_initialized()
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM memories WHERE id = ? AND deleted_at IS NULL",
                (memory_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return self._row_to_memory(row)
        return None
    
    async def update(self, memory_id: str, updates: dict) -> bool:
        await self._ensure_initialized()
        
        # Build SET clause dynamically
        set_parts = []
        values = []
        for key, value in updates.items():
            if key in ('tags', 'related_ids', 'metadata'):
                value = json.dumps(value)
            set_parts.append(f"{key} = ?")
            values.append(value)
        
        set_parts.append("updated_at = ?")
        values.append(datetime.utcnow().isoformat())
        
        set_parts.append("sync_version = sync_version + 1")
        
        values.append(memory_id)
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                f"UPDATE memories SET {', '.join(set_parts)} WHERE id = ?",
                values
            )
            await db.commit()
            return cursor.rowcount > 0
    
    async def delete(self, memory_id: str) -> bool:
        await self._ensure_initialized()
        
        # Soft delete for sync
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                UPDATE memories 
                SET deleted_at = ?, sync_version = sync_version + 1
                WHERE id = ? AND deleted_at IS NULL
            """, (datetime.utcnow().isoformat(), memory_id))
            await db.commit()
            return cursor.rowcount > 0
    
    async def list(
        self,
        tenant_id: str,
        layer: Optional[MemoryLayer] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[MemoryItem]:
        await self._ensure_initialized()
        
        query = "SELECT * FROM memories WHERE tenant_id = ? AND deleted_at IS NULL"
        params = [tenant_id]
        
        if layer:
            query += " AND layer = ?"
            params.append(layer.value if isinstance(layer, MemoryLayer) else layer)
        
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_memory(row) for row in rows]
    
    async def count(
        self,
        tenant_id: str,
        layer: Optional[MemoryLayer] = None
    ) -> int:
        await self._ensure_initialized()
        
        query = "SELECT COUNT(*) FROM memories WHERE tenant_id = ? AND deleted_at IS NULL"
        params = [tenant_id]
        
        if layer:
            query += " AND layer = ?"
            params.append(layer.value if isinstance(layer, MemoryLayer) else layer)
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(query, params) as cursor:
                row = await cursor.fetchone()
                return row[0]
    
    async def get_changes_since(
        self,
        tenant_id: str,
        since_version: int
    ) -> AsyncIterator[MemoryItem]:
        """Get all memories changed since given sync version."""
        await self._ensure_initialized()
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM memories 
                WHERE tenant_id = ? AND sync_version > ?
                ORDER BY sync_version ASC
            """, (tenant_id, since_version)) as cursor:
                async for row in cursor:
                    yield self._row_to_memory(row)
    
    def _row_to_memory(self, row) -> MemoryItem:
        return MemoryItem(
            id=row["id"],
            content=row["content"],
            layer=MemoryLayer(row["layer"]),
            memory_type=MemoryType(row["memory_type"]),
            tenant_id=row["tenant_id"],
            project_id=row["project_id"],
            source=row["source"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None,
            importance=row["importance"],
            decay_rate=row["decay_rate"],
            tags=json.loads(row["tags"]) if row["tags"] else [],
            related_ids=json.loads(row["related_ids"]) if row["related_ids"] else [],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {}
        )
python# rae_lite/adapters/vector.py

import numpy as np
import aiosqlite
from typing import List, Optional
from pathlib import Path

from rae_core.interfaces.vector import IVectorStore
from rae_core.models.search import SearchResult


class SQLiteVectorStore(IVectorStore):
    """
    SQLite + sqlite-vec for local vector search.
    
    Falls back to numpy cosine similarity if sqlite-vec not available.
    """
    
    def __init__(self, db_path: str, dimension: int = 384):
        self.db_path = Path(db_path).expanduser()
        self.dimension = dimension
        self._use_sqlite_vec = False
        self._initialized = False
    
    async def _ensure_initialized(self):
        if self._initialized:
            return
        
        async with aiosqlite.connect(self.db_path) as db:
            # Try to load sqlite-vec extension
            try:
                await db.execute("SELECT load_extension('vec0')")
                self._use_sqlite_vec = True
                
                # Create virtual table
                await db.execute(f"""
                    CREATE VIRTUAL TABLE IF NOT EXISTS vec_memories
                    USING vec0(
                        id TEXT PRIMARY KEY,
                        embedding FLOAT[{self.dimension}]
                    )
                """)
            except Exception:
                # Fallback to regular table with numpy
                self._use_sqlite_vec = False
                await db.execute(f"""
                    CREATE TABLE IF NOT EXISTS vec_memories (
                        id TEXT PRIMARY KEY,
                        embedding BLOB,
                        tenant_id TEXT,
                        layer TEXT
                    )
                """)
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_vec_tenant 
                    ON vec_memories(tenant_id)
                """)
            
            await db.commit()
        
        self._initialized = True
    
    async def upsert(
        self,
        id: str,
        vector: List[float],
        metadata: Optional[dict] = None
    ) -> None:
        await self._ensure_initialized()
        
        vec_bytes = np.array(vector, dtype=np.float32).tobytes()
        metadata = metadata or {}
        
        async with aiosqlite.connect(self.db_path) as db:
            if self._use_sqlite_vec:
                await db.execute("""
                    INSERT OR REPLACE INTO vec_memories (id, embedding)
                    VALUES (?, ?)
                """, (id, vec_bytes))
            else:
                await db.execute("""
                    INSERT OR REPLACE INTO vec_memories 
                    (id, embedding, tenant_id, layer)
                    VALUES (?, ?, ?, ?)
                """, (
                    id, 
                    vec_bytes,
                    metadata.get("tenant_id"),
                    metadata.get("layer")
                ))
            await db.commit()
    
    async def search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        filters: Optional[dict] = None
    ) -> List[SearchResult]:
        await self._ensure_initialized()
        
        query_vec = np.array(query_vector, dtype=np.float32)
        
        if self._use_sqlite_vec:
            return await self._search_sqlite_vec(query_vec, top_k, filters)
        else:
            return await self._search_numpy(query_vec, top_k, filters)
    
    async def _search_sqlite_vec(
        self,
        query_vec: np.ndarray,
        top_k: int,
        filters: Optional[dict]
    ) -> List[SearchResult]:
        """Search using sqlite-vec extension."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("SELECT load_extension('vec0')")
            
            query_bytes = query_vec.tobytes()
            
            async with db.execute(f"""
                SELECT id, distance
                FROM vec_memories
                WHERE embedding MATCH ?
                ORDER BY distance
                LIMIT ?
            """, (query_bytes, top_k)) as cursor:
                rows = await cursor.fetchall()
                
                return [
                    SearchResult(
                        id=row[0],
                        score=1.0 / (1.0 + row[1]),  # Convert distance to similarity
                        source="vector"
                    )
                    for row in rows
                ]
    
    async def _search_numpy(
        self,
        query_vec: np.ndarray,
        top_k: int,
        filters: Optional[dict]
    ) -> List[SearchResult]:
        """Fallback search using numpy cosine similarity."""
        async with aiosqlite.connect(self.db_path) as db:
            query = "SELECT id, embedding FROM vec_memories"
            params = []
            
            if filters:
                conditions = []
                if "tenant_id" in filters:
                    conditions.append("tenant_id = ?")
                    params.append(filters["tenant_id"])
                if "layer" in filters:
                    conditions.append("layer = ?")
                    params.append(filters["layer"])
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
            
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
            
            if not rows:
                return []
            
            # Calculate cosine similarities
            results = []
            query_norm = np.linalg.norm(query_vec)
            
            for row in rows:
                vec = np.frombuffer(row[1], dtype=np.float32)
                vec_norm = np.linalg.norm(vec)
                
                if query_norm > 0 and vec_norm > 0:
                    similarity = np.dot(query_vec, vec) / (query_norm * vec_norm)
                else:
                    similarity = 0.0
                
                results.append(SearchResult(
                    id=row[0],
                    score=float(similarity),
                    source="vector"
                ))
            
            # Sort by score and return top_k
            results.sort(key=lambda x: x.score, reverse=True)
            return results[:top_k]
    
    async def delete(self, id: str) -> bool:
        await self._ensure_initialized()
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM vec_memories WHERE id = ?",
                (id,)
            )
            await db.commit()
            return cursor.rowcount > 0
    
    async def get_vector(self, id: str) -> Optional[List[float]]:
        await self._ensure_initialized()
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT embedding FROM vec_memories WHERE id = ?",
                (id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return np.frombuffer(row[0], dtype=np.float32).tolist()
        return None
5.5 Desktop Application (System Tray)
python# rae_lite/app/tray.py

import pystray
from PIL import Image
import threading
import asyncio
from pathlib import Path

from ..server.app import create_app
from ..config.settings import Settings


class RAELiteTray:
    """System tray application for RAE-Lite."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.icon = None
        self.server_thread = None
        self.engine = None
        
    def run(self):
        """Start the tray application."""
        # Load icon
        icon_path = Path(__file__).parent / "resources" / "icons" / "rae.png"
        image = Image.open(icon_path)
        
        # Create menu
        menu = pystray.Menu(
            pystray.MenuItem("🔍 Quick Search", self.on_search),
            pystray.MenuItem("📊 Status", self.on_status),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("⚙️ Settings", self.on_settings),
            pystray.MenuItem("🔄 Sync Now", self.on_sync),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("📖 Documentation", self.on_docs),
            pystray.MenuItem("❓ About", self.on_about),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("🚪 Exit", self.on_exit),
        )
        
        # Create tray icon
        self.icon = pystray.Icon(
            "RAE-Lite",
            image,
            "RAE-Lite - Memory Engine",
            menu
        )
        
        # Start server in background
        self.start_server()
        
        # Run tray (blocking)
        self.icon.run()
    
    def start_server(self):
        """Start local HTTP server in background thread."""
        def run_server():
            import uvicorn
            app = create_app(self.settings)
            uvicorn.run(
                app,
                host="127.0.0.1",
                port=self.settings.server_port,
                log_level="warning"
            )
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
    
    def on_search(self, icon, item):
        """Open quick search window."""
        from .windows.search import SearchWindow
        SearchWindow(self.settings).show()
    
    def on_status(self, icon, item):
        """Open status window."""
        from .windows.status import StatusWindow
        StatusWindow(self.settings).show()
    
    def on_settings(self, icon, item):
        """Open settings window."""
        from .windows.settings import SettingsWindow
        SettingsWindow(self.settings).show()
    
    def on_sync(self, icon, item):
        """Trigger sync."""
        asyncio.run(self._do_sync())
    
    async def _do_sync(self):
        from ..sync.client import SyncClient
        client = SyncClient(self.settings)
        await client.sync()
    
    def on_docs(self, icon, item):
        """Open documentation in browser."""
        import webbrowser
        webbrowser.open("https://rae-memory.dev/docs/lite")
    
    def on_about(self, icon, item):
        """Show about dialog."""
        from .windows.about import show_about
        show_about()
    
    def on_exit(self, icon, item):
        """Exit application."""
        self.icon.stop()


def main():
    """Entry point for RAE-Lite."""
    from ..config.settings import load_settings
    
    settings = load_settings()
    app = RAELiteTray(settings)
    app.run()


if __name__ == "__main__":
    main()
5.6 Build Configuration (PyInstaller)
python# scripts/build_exe.py

import PyInstaller.__main__
from pathlib import Path

ROOT = Path(__file__).parent.parent
DIST = ROOT / "dist"
BUILD = ROOT / "build"

def build_windows():
    """Build Windows .exe"""
    PyInstaller.__main__.run([
        str(ROOT / "rae_lite" / "main.py"),
        "--name=RAE-Lite",
        "--onefile",
        "--windowed",  # No console
        f"--icon={ROOT / 'rae_lite' / 'app' / 'resources' / 'icons' / 'rae.ico'}",
        f"--add-data={ROOT / 'rae_lite' / 'app' / 'resources'};resources",
        "--hidden-import=pystray._win32",
        "--hidden-import=aiosqlite",
        "--hidden-import=sentence_transformers",
        f"--distpath={DIST}",
        f"--workpath={BUILD}",
        "--clean",
    ])

def build_macos():
    """Build macOS .app"""
    PyInstaller.__main__.run([
        str(ROOT / "rae_lite" / "main.py"),
        "--name=RAE-Lite",
        "--onefile",
        "--windowed",
        f"--icon={ROOT / 'rae_lite' / 'app' / 'resources' / 'icons' / 'rae.icns'}",
        f"--add-data={ROOT / 'rae_lite' / 'app' / 'resources'}:resources",
        "--hidden-import=pystray._darwin",
        "--hidden-import=aiosqlite",
        "--osx-bundle-identifier=dev.rae-memory.lite",
        f"--distpath={DIST}",
        f"--workpath={BUILD}",
        "--clean",
    ])

if __name__ == "__main__":
    import sys
    if sys.platform == "win32":
        build_windows()
    elif sys.platform == "darwin":
        build_macos()
    else:
        print("Linux: use build_linux.py with AppImage")

6. RAE-Mobile
6.1 Cel
RAE-Mobile to natywna aplikacja mobilna (iOS/Android):

📱 Native UI (Swift/Kotlin lub React Native/Flutter)
📦 SQLite jako storage (jak RAE-Lite)
🤖 On-device ML (CoreML na iOS, ONNX na Android)
🔄 Sync z RAE-Lite i/lub RAE-Server
💾 Offline-first

6.2 Architektura (high-level)
┌─────────────────────────────────────────────────────────────────────────┐
│                         RAE-Mobile App                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                        Native UI Layer                            │  │
│  │  • Home (recent memories, quick actions)                          │  │
│  │  • Search (semantic search interface)                             │  │
│  │  • Browse (layers, tags, sources)                                 │  │
│  │  • Capture (manual entry, share extension)                        │  │
│  │  • Settings (sync, LLM, privacy)                                  │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                    │                                    │
│  ┌─────────────────────────────────┴─────────────────────────────────┐  │
│  │                      RAE-core (via bindings)                      │  │
│  │                                                                   │  │
│  │  Option A: PyO3 bindings (Python → Rust → Mobile)                │  │
│  │  Option B: Native port (Kotlin/Swift implementation)              │  │
│  │  Option C: Embedded Python (Kivy/BeeWare)                        │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                    │                                    │
│  ┌─────────────────────────────────┴─────────────────────────────────┐  │
│  │                      On-Device ML                                 │  │
│  │                                                                   │  │
│  │  iOS: CoreML (all-MiniLM-L6-v2.mlmodel)                          │  │
│  │  Android: ONNX Runtime (all-MiniLM-L6-v2.onnx)                   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                    │                                    │
│  ┌─────────────────────────────────┴─────────────────────────────────┐  │
│  │                      SQLite Storage                               │  │
│  │                   (same schema as RAE-Lite)                       │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                    │                                    │
│  ┌─────────────────────────────────┴─────────────────────────────────┐  │
│  │                      RAE-Sync Client                              │  │
│  │  • LAN sync (mDNS discovery)                                      │  │
│  │  • Cloud sync (RAE-Server)                                        │  │
│  │  • E2E encryption                                                 │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
6.3 Strategia implementacji
OpcjaProsConsRecommendationA: PyO3 → Rust bindingsReuse RAE-coreComplex buildLaterB: Native portBest performanceDuplicate logicNoC: React Native + Embedded PythonFast devPerformanceMVPD: Flutter + FFICross-platformLearning curveConsider
Rekomendacja dla MVP: React Native z lokalnym API (jak RAE-Lite server)
6.4 Roadmap RAE-Mobile
FazaZakresTimelinePhase 1Basic viewer (read-only) + syncQ2 2025Phase 2Search + captureQ3 2025Phase 3Full RAE-core on deviceQ4 2025

7. RAE-Sync
7.1 Cel
RAE-Sync to protokół synchronizacji między instancjami RAE:

🔄 Lite ↔ Server
📱 Mobile ↔ Lite
📱 Mobile ↔ Server
💻 Lite ↔ Lite (P2P w LAN)

7.2 Architektura protokołu
┌─────────────────────────────────────────────────────────────────────────┐
│                         RAE-Sync Protocol                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                      Sync Modes                                   │  │
│  │                                                                   │  │
│  │  1. Server Sync      RAE-Lite/Mobile → RAE-Server (HTTPS)        │  │
│  │  2. LAN P2P Sync     RAE-Lite ↔ RAE-Lite (mDNS + WebSocket)      │  │
│  │  3. Relay Sync       RAE-Mobile → Relay → RAE-Lite (NAT punch)   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                      Sync State                                   │  │
│  │                                                                   │  │
│  │  • sync_version: Monotonic counter per memory                     │  │
│  │  • last_sync: Timestamp of last successful sync                   │  │
│  │  • peer_id: Unique identifier for each RAE instance               │  │
│  │  • conflict_resolution: "last-write-wins" or "merge"              │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                      Delta Sync Algorithm                         │  │
│  │                                                                   │  │
│  │  1. Client: GET /sync/state → {last_version, peer_id}            │  │
│  │  2. Server: Compare versions, return delta                        │  │
│  │  3. Client: Apply remote changes                                  │  │
│  │  4. Client: POST /sync/push → {local_changes}                    │  │
│  │  5. Server: Merge and return conflicts                            │  │
│  │  6. Client: Resolve conflicts (auto or manual)                    │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                      Security                                     │  │
│  │                                                                   │  │
│  │  • E2E Encryption: All memories encrypted before sync             │  │
│  │  • Key Exchange: X25519 ECDH                                      │  │
│  │  • Encryption: XChaCha20-Poly1305                                 │  │
│  │  • Server sees only encrypted blobs                               │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
7.3 Sync API (w RAE-core)
python# rae_core/interfaces/sync.py

from abc import ABC, abstractmethod
from typing import List, Optional, AsyncIterator
from dataclasses import dataclass
from datetime import datetime


@dataclass
class SyncState:
    """Current sync state for a tenant."""
    peer_id: str
    last_sync_version: int
    last_sync_time: Optional[datetime]
    pending_changes: int


@dataclass
class SyncDelta:
    """Delta of changes for sync."""
    memories: List[dict]  # Changed/new memories
    deletions: List[str]  # Deleted memory IDs
    from_version: int
    to_version: int


@dataclass
class SyncConflict:
    """Conflict during sync."""
    memory_id: str
    local_version: dict
    remote_version: dict
    resolution: Optional[str] = None  # "local", "remote", "merge"


class ISyncProvider(ABC):
    """Abstract interface for sync operations."""
    
    @abstractmethod
    async def get_state(self, tenant_id: str) -> SyncState:
        """Get current sync state."""
        pass
    
    @abstractmethod
    async def get_delta(
        self,
        tenant_id: str,
        since_version: int
    ) -> SyncDelta:
        """Get changes since version."""
        pass
    
    @abstractmethod
    async def apply_delta(
        self,
        tenant_id: str,
        delta: SyncDelta
    ) -> List[SyncConflict]:
        """Apply remote delta, return conflicts."""
        pass
    
    @abstractmethod
    async def resolve_conflict(
        self,
        tenant_id: str,
        conflict: SyncConflict,
        resolution: str
    ) -> bool:
        """Resolve a sync conflict."""
        pass
    
    @abstractmethod
    async def push_changes(
        self,
        tenant_id: str,
        target_url: str
    ) -> SyncDelta:
        """Push local changes to remote."""
        pass

8. Browser Extension (opcjonalne)
8.1 Cel
Browser extension to opcjonalny dodatek do RAE-Lite:

Przechwytuje rozmowy z ChatGPT, Claude, Gemini, etc.
Wysyła do lokalnego RAE-Lite (localhost API)
Nie wymaga RAE-Server - wszystko lokalnie

8.2 Architektura
┌─────────────────────────────────────────────────────────────────────────┐
│                    Browser Extension                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Content Scripts (per site)          Background Service Worker          │
│  ┌─────────────────────────┐        ┌─────────────────────────┐        │
│  │ chatgpt.js              │───────▶│                         │        │
│  │ claude.js               │        │  Aggregates messages    │        │
│  │ gemini.js               │        │  Sends to RAE-Lite      │        │
│  │ grok.js                 │        │  (localhost:8765)       │        │
│  │ deepseek.js             │        │                         │        │
│  │ qwen.js                 │        └───────────┬─────────────┘        │
│  │ mistral.js              │                    │                       │
│  │ bielik.js               │                    ▼                       │
│  └─────────────────────────┘        ┌─────────────────────────┐        │
│                                     │   RAE-Lite              │        │
│  Popup UI                           │   (localhost:8765)      │        │
│  ┌─────────────────────────┐        │                         │        │
│  │ Status indicator        │        │   Memory stored         │        │
│  │ Quick search            │        │   locally in SQLite     │        │
│  │ Recent captures         │        └─────────────────────────┘        │
│  │ Settings                │                                           │
│  └─────────────────────────┘                                           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
8.3 Struktura extension
browser-extension/
├── manifest.json               # Manifest V3
├── background/
│   └── service-worker.js       # Background service worker
├── content-scripts/
│   ├── base.js                 # Base interceptor class
│   ├── chatgpt.js              # chat.openai.com
│   ├── claude.js               # claude.ai
│   ├── gemini.js               # gemini.google.com
│   ├── grok.js                 # x.com/i/grok, grok.x.ai
│   ├── deepseek.js             # chat.deepseek.com
│   ├── qwen.js                 # qwenlm.ai, tongyi.aliyun.com
│   ├── mistral.js              # chat.mistral.ai
│   └── bielik.js               # bielik.ai (if exists)
├── popup/
│   ├── popup.html
│   ├── popup.js
│   └── popup.css
├── options/
│   ├── options.html
│   └── options.js
├── icons/
│   ├── icon-16.png
│   ├── icon-48.png
│   └── icon-128.png
└── _locales/                   # i18n
    ├── en/messages.json
    └── pl/messages.json

9. Plan refaktoryzacji
9.1 Fazy projektu
┌─────────────────────────────────────────────────────────────────────────┐
│                    RAE ECOSYSTEM DEVELOPMENT ROADMAP                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  PHASE 1: RAE-core Extraction (Weeks 1-4)                              │
│  ─────────────────────────────────────────                              │
│  ├── Week 1: Interfaces & Models                                        │
│  │   ├── Create rae-core repo/package                                   │
│  │   ├── Define all interfaces (IMemoryStorage, IVectorStore, etc.)     │
│  │   └── Port Pydantic models (without SQLAlchemy)                      │
│  │                                                                      │
│  ├── Week 2: Memory Layers & Math                                       │
│  │   ├── Extract 4 memory layers logic                                  │
│  │   ├── Extract 3 math layers logic                                    │
│  │   └── Unit tests (no infra needed)                                   │
│  │                                                                      │
│  ├── Week 3: Search & Reflection                                        │
│  │   ├── Extract HybridSearchEngine                                     │
│  │   ├── Extract ReflectionEngine                                       │
│  │   └── Extract ContextBuilder                                         │
│  │                                                                      │
│  └── Week 4: Integration & RAEEngine                                    │
│      ├── Create RAEEngine main class                                    │
│      ├── Add in-memory adapters for testing                             │
│      ├── Full test suite                                                │
│      └── Documentation & pypi publish                                   │
│                                                                         │
│  PHASE 2: RAE-Server Refactoring (Weeks 5-6)                           │
│  ───────────────────────────────────────────                            │
│  ├── Week 5: Adapters                                                   │
│  │   ├── PostgresMemoryStorage adapter                                  │
│  │   ├── QdrantVectorStore adapter                                      │
│  │   ├── RedisCache adapter                                             │
│  │   └── LLM provider adapters                                          │
│  │                                                                      │
│  └── Week 6: Integration                                                │
│      ├── Refactor imports to use rae-core                               │
│      ├── Update tests                                                   │
│      ├── Verify all existing functionality                              │
│      └── Release RAE-Server v3.0                                        │
│                                                                         │
│  PHASE 3: RAE-Lite Development (Weeks 7-10)                            │
│  ──────────────────────────────────────────                             │
│  ├── Week 7: SQLite Adapters                                            │
│  │   ├── SQLiteMemoryStorage                                            │
│  │   ├── SQLiteVectorStore (sqlite-vec + numpy fallback)                │
│  │   └── SQLiteGraphStore                                               │
│  │                                                                      │
│  ├── Week 8: Desktop App                                                │
│  │   ├── System tray (pystray)                                          │
│  │   ├── Local HTTP server                                              │
│  │   └── Basic UI windows                                               │
│  │                                                                      │
│  ├── Week 9: Build & Distribution                                       │
│  │   ├── PyInstaller config                                             │
│  │   ├── Windows installer (NSIS/WiX)                                   │
│  │   ├── macOS .app bundle                                              │
│  │   └── Linux AppImage                                                 │
│  │                                                                      │
│  └── Week 10: Polish & Release                                          │
│      ├── Auto-updater                                                   │
│      ├── First-run wizard                                               │
│      ├── Documentation                                                  │
│      └── Release RAE-Lite v0.1                                          │
│                                                                         │
│  PHASE 4: Browser Extension (Weeks 11-12) [OPTIONAL]                   │
│  ──────────────────────────────────────────────────                     │
│  ├── Week 11: Core Extension                                            │
│  │   ├── Manifest V3 setup                                              │
│  │   ├── Base interceptor class                                         │
│  │   └── ChatGPT + Claude interceptors                                  │
│  │                                                                      │
│  └── Week 12: More Platforms & Polish                                   │
│      ├── Gemini, Grok, DeepSeek interceptors                            │
│      ├── Popup UI                                                       │
│      ├── Chrome Web Store submission                                    │
│      └── Firefox Add-ons submission                                     │
│                                                                         │
│  PHASE 5: RAE-Sync (Weeks 13-14)                                       │
│  ───────────────────────────────                                        │
│  ├── Week 13: Protocol & Server                                         │
│  │   ├── Sync protocol in rae-core                                      │
│  │   ├── Sync endpoints in RAE-Server                                   │
│  │   └── E2E encryption                                                 │
│  │                                                                      │
│  └── Week 14: Client Implementation                                     │
│      ├── Sync client in RAE-Lite                                        │
│      ├── LAN discovery (mDNS)                                           │
│      └── Conflict resolution UI                                         │
│                                                                         │
│  PHASE 6: RAE-Mobile (Q2-Q4 2025) [FUTURE]                             │
│  ─────────────────────────────────────────                              │
│  ├── Q2: Read-only viewer + sync                                        │
│  ├── Q3: Search + capture                                               │
│  └── Q4: Full RAE-core on device                                        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
9.2 Szczegółowy plan Phase 1 (RAE-core)
TydzieńDzieńZadanieOutputW11Setup repo, pyproject.toml, CIrae-core/ initialized2interfaces/storage.py, interfaces/vector.pyAbstract interfaces3interfaces/graph.py, interfaces/llm.py, interfaces/embedding.pyAll interfaces4models/memory.py, models/graph.pyCore models5models/search.py, models/reflection.py, models/sync.pyAll modelsW21layers/base.py, layers/sensory.pyLayer 12layers/working.pyLayer 23layers/longterm.pyLayer 34layers/reflective.pyLayer 45math/math1_structure.py, math/math2_dynamics.pyMath layersW31math/math3_policy.py, math/controller.pyMath complete2search/strategies/*.pySearch strategies3search/engine.py, search/fusion.pyHybrid search4reflection/engine.py, reflection/actor.pyReflection5context/builder.py, scoring/scorer.pyContext & scoringW41engine.py (RAEEngine)Main entry point2In-memory adapters for testingTest infrastructure3Unit tests (layers, search, reflection)Test suite4Documentation, READMEDocs5PyPI publish, releasepip install rae-core

10. Mapowanie plików
10.1 Z obecnego RAE do RAE-core
Źródło (apps/memory_api/)Cel (rae_core/)Uwagicore/math*.pymath/Bez zmian logikimodels/*.pymodels/Usunąć SQLAlchemyservices/hybrid_search.pysearch/engine.pyWydzielić strategieservices/query_analyzer.pysearch/query_analyzer.py-services/reflection_engine.pyreflection/Podzielić na komponentyservices/context_builder.pycontext/builder.py-services/memory_scoring.pyscoring/scorer.py-repositories/*.py❌ NIE przenosićZostaje jako adapteryrouters/*.py❌ NIE przenosićZostaje w RAE-Server
10.2 Nowe pliki dla RAE-core
PlikOpisinterfaces/*.pyNowe - abstrakcyjne interfejsyengine.pyNowe - RAEEngine główny entry pointllm/fallback.pyNowe - rule-based fallback bez LLMsync/protocol.pyNowe - protokół syncsync/merge.pyNowe - CRDT merging

11. Harmonogram
11.1 Timeline
2025-01     2025-02     2025-03     2025-04     2025-05
    │           │           │           │           │
    ▼           ▼           ▼           ▼           ▼
┌───────────────────────────────────────────────────────────────────────┐
│ Phase 1: RAE-core (4 weeks)                                          │
│ ████████████████                                                      │
└───────────────────────────────────────────────────────────────────────┘
                ┌───────────────────────────────────────────────────────┐
                │ Phase 2: RAE-Server refactor (2 weeks)               │
                │ ████████                                              │
                └───────────────────────────────────────────────────────┘
                        ┌───────────────────────────────────────────────┐
                        │ Phase 3: RAE-Lite (4 weeks)                  │
                        │ ████████████████                              │
                        └───────────────────────────────────────────────┘
                                        ┌───────────────────────────────┐
                                        │ Phase 4: Browser Ext (2 wks) │
                                        │ ████████                      │
                                        └───────────────────────────────┘
                                                ┌───────────────────────┐
                                                │ Phase 5: Sync (2 wks)│
                                                │ ████████              │
                                                └───────────────────────┘
11.2 Milestones
MilestoneDataDeliverableM1Week 4rae-core v0.1.0 na PyPIM2Week 6RAE-Server v3.0 (używa rae-core)M3Week 10RAE-Lite v0.1.0 (.exe/.app)M4Week 12Browser Extension v0.1.0M5Week 14RAE-Sync v0.1.0M6Q4 2025RAE-Mobile v0.1.0

Appendix A: Zależności pakietów
RAE-core (minimal)
tomldependencies = [
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "numpy>=1.24",
    "typing-extensions>=4.0",
]
RAE-Server (full)
tomldependencies = [
    "rae-core>=0.1.0",
    "fastapi>=0.100",
    "uvicorn>=0.23",
    "sqlalchemy>=2.0",
    "asyncpg>=0.28",
    "qdrant-client>=1.6",
    "redis>=5.0",
    "celery>=5.3",
    "openai>=1.0",
    "anthropic>=0.7",
    # ... more
]
RAE-Lite (desktop)
tomldependencies = [
    "rae-core>=0.1.0",
    "aiosqlite>=0.19",
    "pystray>=0.19",
    "pillow>=10.0",
    "sentence-transformers>=2.2",  # or onnxruntime
]

[project.optional-dependencies]
ollama = ["ollama>=0.1"]
sqlite-vec = ["sqlite-vec>=0.1"]

Appendix B: Decyzje architektoniczne
ADR-001: RAE-core jako pure Python
Decyzja: RAE-core nie ma zależności na konkretne bazy danych ani frameworki webowe.
Uzasadnienie: Umożliwia użycie na różnych platformach (server, desktop, mobile).
Konsekwencje: Adaptery muszą być implementowane osobno dla każdej platformy.
ADR-002: SQLite dla RAE-Lite
Decyzja: RAE-Lite używa SQLite jako jedynego storage.
Uzasadnienie: Zero konfiguracji, single-file, działa offline.
Konsekwencje: Ograniczenia skalowalności (OK dla single-user).
ADR-003: Sync jako opt-in
Decyzja: Synchronizacja jest opcjonalna i musi być włączona przez użytkownika.
Uzasadnienie: Privacy-first, dane lokalne domyślnie.
Konsekwencje: Użytkownicy muszą świadomie włączyć sync.
ADR-004: E2E Encryption dla sync
Decyzja: Wszystkie synchronizowane dane są szyfrowane end-to-end.
Uzasadnienie: Serwer nie powinien widzieć treści pamięci.
Konsekwencje: Klucze muszą być zarządzane przez użytkownika.