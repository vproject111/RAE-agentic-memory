import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

from rae_core.runtime import RAERuntime
from rae_adapters.sqlite.storage import SQLiteStorage
from rae_core.math.controller import MathLayerController
from rae_core.math.resonance import SemanticResonanceEngine
from rae_core.math.fusion import reciprocal_rank_fusion

from rae_lite.ingestion.ingestor import UniversalIngestor
from rae_lite.ingestion.watcher import DirectoryWatcher
from rae_lite.ingestion.channels.email import EmailConnector
from rae_lite.ingestion.channels.ui_observer import UIObserver
from rae_lite.llm_adapter import LlamaCppAdapter
from rae_lite.config import settings

logger = logging.getLogger(__name__)

class RAELiteService:
    """
    Main Service for RAE-Lite.
    Connects Ingestor -> Runtime -> Storage -> Math Layer (Full Power).
    """
    def __init__(self, storage_path: str, watch_dir: str | None = None, enable_observer: bool = False):
        self.storage_path = storage_path
        self.watch_dir = watch_dir
        self.enable_observer = enable_observer
        
        # 1. Storage & Runtime
        self.storage = SQLiteStorage(db_path=f"{storage_path}/memories.db")
        self.runtime = RAERuntime(storage=self.storage)
        
        # 2. The "Brains" (Math Layer)
        self.math_controller = MathLayerController()
        self.resonance_engine = SemanticResonanceEngine(resonance_factor=0.3)
        
        # 2.5 Hardware-Aware LLM Adapter
        self.llm_adapter = LlamaCppAdapter(
            llama_path=settings.llama_path,
            model_path=settings.model_path,
            profile=settings.selected_profile
        )
        
        # 3. Ingestion
        self.ingestor = UniversalIngestor()
        self.email_connector = EmailConnector()
        self.ui_observer = UIObserver() # Experimental
        self.watcher = None
        self.ingest_queue = asyncio.Queue()

    async def start(self):
        await self.storage.initialize()
        logger.info("RAE-Lite Storage initialized.")
        
        # Start File Watcher
        if self.watch_dir:
            self._scan_directory(self.watch_dir)
            self.watcher = DirectoryWatcher(self.watch_dir, self._on_file_change)
            self.watcher.start()
            asyncio.create_task(self._process_queue())
            
        # Start UI Observer (Opt-in)
        if self.enable_observer:
            self.ui_observer.start()
            asyncio.create_task(self._ui_observer_loop())

    async def stop(self):
        if self.watcher:
            self.watcher.stop()
        self.ui_observer.stop()

    async def _ui_observer_loop(self):
        """Background loop for UI scraping."""
        logger.info("Starting UI Observer Loop...")
        while self.enable_observer:
            try:
                # Run blocking UI call in thread executor to not freeze async loop
                # Although uiautomation is mostly fast, it interacts with OS.
                loop = asyncio.get_event_loop()
                memory_item = await loop.run_in_executor(None, self.ui_observer.scan_active_window)
                
                if memory_item:
                    await self.storage.store_memory(
                        content=memory_item["content"],
                        layer="working", # RESTRICTED -> Working Layer
                        tenant_id="local-user",
                        agent_id="rae-lite-observer",
                        tags=memory_item["tags"],
                        metadata=memory_item["metadata"],
                        info_class=memory_item["info_class"],
                        importance=0.7
                    )
            except Exception as e:
                logger.error(f"UI Observer Loop Error: {e}")
            
            await asyncio.sleep(5) # Poll every 5 seconds

    async def query(self, text: str, tenant_id: str) -> List[Dict[str, Any]]:
        """
        Smart Query utilizing FULL RAE-Lite Math Capabilities:
        1. Query Normalization (LLM if available)
        2. Retrieval (FTS)
        3. Math Scoring (Recency, Importance)
        4. Semantic Resonance (Graph Topology)
        5. Synthesis (LLM if available)
        """
        # 0. Query Normalization
        search_text = self.llm_adapter.normalize_query(text)
        logger.info(f"Query normalized: '{text}' -> '{search_text}'")

        # A. Raw Retrieval (FTS)
        raw_results = await self.storage.search_full_text(search_text, tenant_id=tenant_id)
        
        if not raw_results:
            return []

        # B. Parse Timestamps & Pre-Score
        processed_memories = []
        for item in raw_results:
            self._fix_timestamps(item)
            # Base similarity (from FTS rank or placeholder)
            base_similarity = item.get("score", 0.5)
            
            # Math Layer: Basic Scoring (Recency + Importance)
            math_score = self.math_controller.score_memory(
                memory=item,
                query_similarity=base_similarity
            )
            item["math_score"] = math_score
            item["search_score"] = math_score # Use this as base for resonance
            processed_memories.append(item)

        # C. Semantic Resonance (The "Magic" Layer)
        # In Lite/Offline, we build an Ad-Hoc Graph from metadata to simulate connections
        edges = self._build_adhoc_graph(processed_memories)
        
        # Apply Resonance (Boost scores based on connectivity)
        resonated_results = self.resonance_engine.compute_resonance(
            processed_memories,
            edges
        )

        # D. Final Sort
        resonated_results.sort(key=lambda x: x["math_score"], reverse=True)
        return resonated_results

    def _fix_timestamps(self, item: Dict[str, Any]):
        """Ensure timestamps are datetime objects for Math Controller."""
        for field in ["created_at", "last_accessed_at"]:
            val = item.get(field)
            if isinstance(val, str):
                try:
                    item[field] = datetime.fromisoformat(val)
                except ValueError:
                    pass

    def _build_adhoc_graph(self, memories: List[Dict[str, Any]]) -> List[tuple[str, str, float]]:
        """
        Constructs a temporary graph from search results to enable Resonance.
        Links memories that share context (file, thread, project).
        """
        edges = []
        # Group by Source (File) and Project/Context
        by_source = {}
        
        for m in memories:
            mid = str(m["id"])
            source = m.get("metadata", {}).get("source") or m.get("metadata", {}).get("filename")
            
            if source:
                if source not in by_source:
                    by_source[source] = []
                by_source[source].append(mid)

        # Create Edges
        for source, ids in by_source.items():
            if len(ids) > 1:
                # Fully connect items in same source (Clique)
                for i in range(len(ids)):
                    for j in range(i + 1, len(ids)):
                        # Weight 0.5 for same file co-occurrence
                        edges.append((ids[i], ids[j], 0.5)) 
                        edges.append((ids[j], ids[i], 0.5))
        
        return edges

    # --- Ingestion Logic ---
    def _scan_directory(self, dir_path: str):
        path = Path(dir_path)
        if not path.exists(): return
        for file_path in path.rglob("*"):
            if file_path.is_file(): self.ingest_queue.put_nowait(file_path)

    def _on_file_change(self, file_path: Path):
        self.ingest_queue.put_nowait(file_path)

    async def _process_queue(self):
        while True:
            file_path = await self.ingest_queue.get()
            try:
                await self._ingest_file(file_path)
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
            finally:
                self.ingest_queue.task_done()

    async def _ingest_file(self, file_path: Path):
        logger.info(f"Ingesting: {file_path}")
        if file_path.suffix.lower() == ".eml":
            await self._ingest_email(file_path)
        else:
            await self._ingest_standard_file(file_path)
        logger.info(f"Finished ingesting: {file_path}")

    async def _ingest_email(self, file_path: Path):
        email_data = self.email_connector.parse_eml(file_path)
        if email_data:
            await self.storage.store_memory(
                content=email_data["content"],
                layer="working",
                tenant_id="local-user",
                agent_id="rae-lite-email",
                tags=email_data["tags"],
                metadata=email_data["metadata"],
                info_class=email_data["info_class"],
                importance=0.9
            )

    async def _ingest_standard_file(self, file_path: Path):
        for chunk in self.ingestor.process_file(file_path):
            importance = 0.5
            filename = chunk["metadata"].get("filename", "").lower()
            if "policy" in filename: importance = 0.8
            elif chunk["metadata"].get("extension") == ".log": importance = 0.3
            
            await self.storage.store_memory(
                content=chunk["content"],
                layer="semantic", 
                tenant_id="local-user",
                agent_id="rae-lite-ingestor",
                tags=chunk["tags"],
                metadata=chunk["metadata"],
                info_class="internal",
                importance=importance
            )