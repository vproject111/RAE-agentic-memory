import asyncio
import json
import os
import sys
from pathlib import Path

import asyncpg
import httpx
import structlog

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apps.memory_api.config import settings

logger = structlog.get_logger(__name__)

# CONFIGURATION
OLLAMA_URL = "http://localhost:11434/api/embeddings"
MODEL = "nomic-embed-text"
BATCH_SIZE = 1  # Ollama native embeddings API is usually single-prompt
STATE_FILE = Path(".backfill_progress.json")


def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"last_memory_id": None, "total_processed": 0}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


async def process_record(client, pool, record):
    content = record["content"]
    # Apply Nomic prefix
    prompt = f"search_document: {content}"
    try:
        resp = await client.post(
            OLLAMA_URL, json={"model": MODEL, "prompt": prompt}, timeout=30.0
        )

        if resp.status_code == 200:
            embedding = resp.json().get("embedding")
            if embedding:
                emb_str = str(embedding)
                async with pool.acquire() as conn:
                    # 1. Primary storage: memory_embeddings
                    await conn.execute(
                        """INSERT INTO memory_embeddings (memory_id, model_name, embedding)
                           VALUES ($1, $2, $3)
                           ON CONFLICT (memory_id, model_name) DO UPDATE SET embedding = $3""",
                        record["id"],
                        "default",
                        emb_str,
                    )
                    # 2. Legacy update
                    try:
                        await conn.execute(
                            "UPDATE memories SET embedding = $1 WHERE id = $2",
                            emb_str,
                            record["id"],
                        )
                    except Exception:
                        pass
                return True
        else:
            logger.error("ollama_error", status=resp.status_code, text=resp.text)
    except Exception as e:
        logger.error("request_failed", error=str(e))
    return False


async def backfill():
    state = load_state()
    print("🚀 RAE Lightning Backfill (Direct Ollama via SSH Tunnel)")

    pool = await asyncpg.create_pool(
        host=settings.POSTGRES_HOST,
        database=settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
    )

    sql_find = """
        SELECT m.id, m.content, m.tenant_id
        FROM memories m
        LEFT JOIN memory_embeddings me ON m.id = me.memory_id AND me.model_name = 'default'
        WHERE me.memory_id IS NULL
        ORDER BY m.timestamp ASC
        LIMIT 15000
    """

    records = await pool.fetch(sql_find)
    total_to_process = len(records)
    print(f"Found {total_to_process} memories pending processing.")

    if not records:
        print("✅ Success: No more memories to backfill.")
        await pool.close()
        return

    async with httpx.AsyncClient() as client:
        # Use a semaphore to limit concurrency but still run in parallel
        semaphore = asyncio.Semaphore(10)

        async def sem_process(record):
            async with semaphore:
                return await process_record(client, pool, record)

        tasks = [sem_process(r) for r in records]

        # Process with progress bar
        success_count = 0
        for i, task in enumerate(asyncio.as_completed(tasks)):
            if await task:
                success_count += 1
            if i % 50 == 0:
                print(f"Progress: {i}/{total_to_process} (Success: {success_count})")
                state["total_processed"] += 50  # Approximation for progress
                save_state(state)

    await pool.close()
    print(f"✅ Finished batch. Success count: {success_count}")


if __name__ == "__main__":
    asyncio.run(backfill())
