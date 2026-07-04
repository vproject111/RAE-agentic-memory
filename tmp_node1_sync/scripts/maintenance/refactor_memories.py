#!/usr/bin/env python3
"""
RAE Memory Refactor Script (v3 - UUID Fix)
------------------------------------------
MIGRATION & CLEANUP TOOL
Execution Target: Node1 (Lumina) or Local Orchestrator

This script connects to the RAE API and reorganizes memories into the correct Tenant/Project structure.
It uses heuristic analysis to fix:
1. Wrong Tenant IDs (e.g., 'default' -> 'rae-core' or 'screenwatcher')
2. Wrong Project IDs
3. Missing metadata

Author: Gemini Agent
Date: 2026-01-14
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Dict, List

import httpx

# Configuration
RAE_API_URL = os.getenv("RAE_API_URL", "http://localhost:8001")
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

# Tenant Constants
TENANT_DEFAULT = "00000000-0000-0000-0000-000000000000"
TENANT_SCREENWATCHER = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
TENANT_RAE_CORE = "b0eebc99-9c0b-4ef8-bb6d-6bb9bd380b22"

TARGET_TENANTS = {
    "core": TENANT_RAE_CORE,
    "screenwatcher": TENANT_SCREENWATCHER,
    "default": TENANT_DEFAULT,
}

# Scan only valid UUID tenants (or mapping friendly names for logging)
SOURCE_TENANTS = [TENANT_DEFAULT]

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MemoryRefactor:
    def __init__(self, api_url: str):
        self.api_url = api_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=30.0)

    async def fetch_memories(self, tenant_id: str) -> List[Dict[str, Any]]:
        """Fetch all memories for a given tenant using new /list endpoint."""
        all_memories = []
        offset = 0
        limit = 100

        logger.info(f"Fetching memories for tenant: {tenant_id}...")

        while True:
            try:
                response = await self.client.get(
                    f"{self.api_url}/v1/memory/list",
                    params={"limit": limit, "offset": offset},
                    headers={
                        "Content-Type": "application/json",
                        "X-Tenant-Id": tenant_id,
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])
                    data.get("total", 0)

                    if not results:
                        break

                    all_memories.extend(results)
                    offset += limit

                    if len(results) < limit:
                        break  # End of list
                elif response.status_code == 404:
                    logger.warning(
                        f"List endpoint not found (404) for tenant {tenant_id}. Check API deployment."
                    )
                    break
                else:
                    logger.error(
                        f"Error fetching from {tenant_id}: {response.status_code} - {response.text}"
                    )
                    break
            except Exception as e:
                logger.error(f"Exception fetching from {tenant_id}: {e}")
                break

        return all_memories

    def analyze_memory(
        self, memory: Dict[str, Any], current_tenant: str
    ) -> Dict[str, Any]:
        """Determine correct target Tenant and Project."""
        content = str(memory.get("content", "")).lower()
        metadata = memory.get("metadata", {}) or {}
        project = str(
            memory.get("project", "") or metadata.get("project", "") or ""
        ).lower()
        source = str(metadata.get("source", "")).lower()

        # Heuristics
        is_screenwatcher = (
            "screenwatcher" in content
            or "screenwatcher" in project
            or "screenwatcher" in source
        )

        is_rae_core = (
            "rae-core" in project
            or "rae-agentic-memory-agnostic-core" in project
            or "rae-core" in content
        )

        target_tenant = current_tenant
        target_project = memory.get("project")  # Keep original case if possible

        if is_screenwatcher:
            target_tenant = TARGET_TENANTS["screenwatcher"]
            target_project = "screenwatcher_project"
        elif is_rae_core:
            target_tenant = TARGET_TENANTS["core"]
            target_project = "rae-core"

        # If still default tenant and no classification, assume RAE Core if we are running in RAE Core repo?
        # No, safer to leave in default or mark as unknown.
        # But user asked to organize.

        # Check if change is needed
        if target_tenant != current_tenant or target_project != memory.get("project"):
            return {
                "action": "move",
                "id": memory.get("id"),
                "current_tenant": current_tenant,
                "target_tenant": target_tenant,
                "target_project": target_project,
                "original_memory": memory,
            }

        return {"action": "skip"}

    async def move_memory(self, plan: Dict[str, Any]):
        """Moves memory by creating a copy in the new tenant and deleting the old one."""
        original = plan["original_memory"]

        new_payload = {
            "content": original.get("content"),
            "layer": original.get("layer", "episodic"),
            "project": plan["target_project"],
            "metadata": original.get("metadata", {}) or {},
            "importance": original.get("importance", 0.5),
            "tags": original.get("tags", []),
        }

        # Metadata tracking
        new_payload["metadata"]["migrated_from_tenant"] = plan["current_tenant"]
        new_payload["metadata"]["original_id"] = original.get("id")
        new_payload["metadata"]["migration_ts"] = str(datetime.now())

        logger.info(
            f"MOVING {plan['id'][:8]}... -> {plan['target_tenant']} (Proj: {plan['target_project']})"
        )

        if not DRY_RUN:
            # CREATE
            resp = await self.client.post(
                f"{self.api_url}/v1/memory/store",
                headers={"X-Tenant-Id": plan["target_tenant"]},
                json=new_payload,
            )
            if resp.status_code in [200, 201]:
                # DELETE OLD
                del_resp = await self.client.delete(
                    f"{self.api_url}/v1/memory/delete",
                    params={"memory_id": plan["id"]},
                    headers={"X-Tenant-Id": plan["current_tenant"]},
                )
                if del_resp.status_code != 200:
                    logger.warning(
                        f"Failed to delete old memory {plan['id']}: {del_resp.text}"
                    )
            else:
                logger.error(f"Failed to create new memory: {resp.text}")

    async def run(self):
        logger.info(f"Starting RAE Memory Refactor V3 (Dry Run: {DRY_RUN})")
        logger.info(f"Source Tenant: {SOURCE_TENANTS}")
        logger.info(
            f"Targets: Core={TENANT_RAE_CORE}, Screenwatcher={TENANT_SCREENWATCHER}"
        )

        tasks = []
        for tenant in SOURCE_TENANTS:
            memories = await self.fetch_memories(tenant)
            logger.info(f"Tenant '{tenant}': Found {len(memories)} memories.")

            for mem in memories:
                analysis = self.analyze_memory(mem, tenant)
                if analysis["action"] == "move":
                    tasks.append(analysis)

        logger.info(f"Found {len(tasks)} memories needing migration.")

        for task in tasks:
            print(
                f"[PLAN] {task['id'][:8]}... | {task['current_tenant'][:8]} -> {task['target_tenant'][:8]} | {task['target_project']}"
            )
            if not DRY_RUN:
                await self.move_memory(task)

        await self.client.aclose()


if __name__ == "__main__":
    refactor = MemoryRefactor(RAE_API_URL)
    asyncio.run(refactor.run())
