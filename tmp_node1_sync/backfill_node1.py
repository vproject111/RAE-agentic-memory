import asyncio
import os
import json
import httpx
import asyncpg
from tqdm import tqdm

# Database connection - using Node1 local connection
DB_CONFIG = {
    "host": "localhost",
    "user": "rae",
    "password": "rae_password",
    "database": "rae",
}

OLLAMA_URL = "http://localhost:11434/api/embeddings"
MODEL = "nomic-embed-text"

async def get_embedding(client, text):
    # Apply Nomic prefix
    processed_text = f"search_document: {text}"
    try:
        resp = await client.post(OLLAMA_URL, json={
            "model": MODEL,
            "prompt": processed_text
        })
        if resp.status_code == 200:
            return resp.json().get("embedding")
    except Exception as e:
        print(f"Error getting embedding: {e}")
    return None

async def backfill():
    print(f"🚀 Starting Local Backfill on Node1 using model: {MODEL}")
    
    conn = await asyncpg.connect(**DB_CONFIG)
    
    # 1. Find memories without embeddings for 'default' model
    sql_find = """
        SELECT m.id, m.content, m.tenant_id
        FROM memories m
        LEFT JOIN memory_embeddings me ON m.id = me.memory_id AND me.model_name = 'default'
        WHERE me.memory_id IS NULL
        LIMIT 5000
    """
    
    records = await conn.fetch(sql_find)
    print(f"Found {len(records)} memories needing embeddings.")
    
    if not records:
        print("Done! No memories to backfill.")
        await conn.close()
        return

    async with httpx.AsyncClient(timeout=30.0) as client:
        for row in tqdm(records):
            memory_id = row['id']
            content = row['content']
            tenant_id = row['tenant_id']
            
            embedding = await get_embedding(client, content)
            if embedding:
                # Save to memory_embeddings
                await conn.execute(
                    "INSERT INTO memory_embeddings (memory_id, model_name, embedding, tenant_id) VALUES ($1, $2, $3, $4)",
                    memory_id, 'default', embedding, tenant_id
                )
                
                # Also update the legacy column in memories table if needed
                # (Assuming the schema refactor is already done and we use memory_embeddings)
                
    await conn.close()
    print("✅ Backfill completed.")

if __name__ == "__main__":
    asyncio.run(backfill())
