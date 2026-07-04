#!/usr/bin/env python3
"""
RAE Memory Analyzer
-------------------
Scans memories to categorize them by topic.
"""

import asyncio
import logging
import os
from typing import Any, Dict, List

import httpx

RAE_API_URL = os.getenv("RAE_API_URL", "http://localhost:8001")
TENANT_DEFAULT = "00000000-0000-0000-0000-000000000000"

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


class MemoryAnalyzer:
    def __init__(self, api_url: str):
        self.api_url = api_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=30.0)

    async def fetch_all(self, tenant_id: str) -> List[Dict[str, Any]]:
        all_memories = []
        offset = 0
        limit = 1000

        print(f"Scanning tenant {tenant_id}...")
        while True:
            try:
                resp = await self.client.get(
                    f"{self.api_url}/v1/memory/list",
                    params={"limit": limit, "offset": offset},
                    headers={
                        "Content-Type": "application/json",
                        "X-Tenant-Id": tenant_id,
                    },
                )
                if resp.status_code != 200:
                    print(f"Error: {resp.status_code}")
                    break

                data = resp.json()
                results = data.get("results", [])
                if not results:
                    break

                all_memories.extend(results)
                offset += limit
                print(f"Fetched {len(all_memories)}...")

                if len(results) < limit:
                    break
            except Exception as e:
                print(f"Error: {e}")
                break
        return all_memories

    def analyze(self, memories: List[Dict[str, Any]]):
        stats = {"screenwatcher": 0, "benchmark": 0, "rae": 0, "other": 0}

        projects = {}

        for m in memories:
            content = str(m.get("content", "")).lower()
            project = str(m.get("project", "")).lower()

            # Count projects
            if project:
                projects[project] = projects.get(project, 0) + 1

            # Categorize
            if "screenwatcher" in content or "screenwatcher" in project:
                stats["screenwatcher"] += 1
            elif (
                "benchmark" in content
                or "benchmark" in project
                or "mmit" in content
                or "lect" in content
            ):
                stats["benchmark"] += 1
            elif "rae" in content or "rae" in project:
                stats["rae"] += 1
            else:
                stats["other"] += 1

        print("\n=== MEMORY ANALYSIS REPORT ===")
        print(f"Total Memories: {len(memories)}")
        print("\nBy Category (Content/Project Keyword):")
        for k, v in stats.items():
            print(f"  - {k.ljust(15)}: {v}")

        print("\nTop 10 Projects found in metadata:")
        sorted_projects = sorted(projects.items(), key=lambda x: x[1], reverse=True)[
            :10
        ]
        for p, count in sorted_projects:
            print(f"  - {p.ljust(30)}: {count}")

    async def run(self):
        memories = await self.fetch_all(TENANT_DEFAULT)
        self.analyze(memories)
        await self.client.aclose()


if __name__ == "__main__":
    asyncio.run(MemoryAnalyzer(RAE_API_URL).run())
