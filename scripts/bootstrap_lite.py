#!/usr/bin/env python3
"""
RAE-Lite Bootstrap Script
-------------------------
Starts the RAE Core logic in "Embedded Mode" (No Docker).
Uses SQLite + Local Qdrant adapters.
"""
import sys
import os
import asyncio
import logging
import structlog
from uuid import uuid4

# Setup basic logging first
logging.basicConfig(level=logging.INFO)

# --- 1. Path Setup (Crucial for embedded imports) ---
# We assume this script runs from the project root or scripts/
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "rae-core"))

# --- 2. Imports (After path fix) ---
try:
    from rae_core.runtime import RAERuntime
    from rae_core.models.interaction import RAEInput, AgentActionType
    from rae_adapters.sqlite.storage import SQLiteStorage
    # Local Qdrant placeholder (we will use a Mock or File-based approach for this test)
    # real implementation will go to rae_adapters.qdrant_local later.
    from rae_core.config.settings import RAESettings
except ImportError as e:
    print(f"❌ Import Error: {e}")
    print(f"PYTHONPATH: {sys.path}")
    sys.exit(1)

# --- 3. Configuration ---
LITE_STORAGE_DIR = os.path.join(project_root, "rae_lite_storage")
DB_PATH = os.path.join(LITE_STORAGE_DIR, "memories.db")

async def main():
    print(f"🚀 RAE-Lite Bootstrap (Embedded Mode)")
    print(f"📂 Storage: {LITE_STORAGE_DIR}")
    
    # Ensure storage exists
    os.makedirs(LITE_STORAGE_DIR, exist_ok=True)
    
    # --- 4. Initialize Adapters ---
    print("🔌 Initializing SQLite Storage...")
    storage = SQLiteStorage(db_path=DB_PATH)
    await storage.initialize()
    print("✅ Storage Connected.")

    # --- 5. Instantiate Runtime (The Brain) ---
    # Note: In a full boot, we would pass an 'agent' here. 
    # For now, we just test the Storage/Runtime wiring.
    runtime = RAERuntime(storage=storage)
    
    # --- 6. Test Operation: Store a Memory directly ---
    tenant_id = "test-tenant-lite"
    print(f"🧠 storing test memory for tenant: {tenant_id}")
    
    mem_id = await storage.store_memory(
        content="RAE-Lite is running in embedded mode without Docker.",
        layer="working",
        tenant_id=tenant_id,
        agent_id="bootstrap-script",
        tags=["system", "boot", "lite"],
        metadata={"os": "linux", "mode": "embedded"}
    )
    print(f"✅ Memory Stored. ID: {mem_id}")

    # --- 7. Test Operation: Search ---
    print("🔎 Searching for 'embedded'...")
    results = await storage.search_full_text("embedded", tenant_id=tenant_id)
    
    if results:
        print(f"✅ Found {len(results)} results.")
        print(f"   Top result: {results[0]['content']}")
    else:
        print("❌ Search returned no results (Index might need flush).")

    print("\n🎉 RAE-Core is ALIVE in Lite Mode.")
    print(f"   Database file size: {os.path.getsize(DB_PATH)} bytes")

if __name__ == "__main__":
    asyncio.run(main())
