"""
Unified Content Factory for RAE Benchmarks.
Generates unique, high-quality memories and associated ground-truth queries.
"""

import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

import yaml


class IndustrialFactory:
    def __init__(self, config_path: str = None, seed: int = 42):
        if config_path is None:
            base_path = Path(__file__).parent.parent.parent
            config_path = (
                base_path / "rae-core/rae_core/config/benchmark_templates.yaml"
            )

        with open(config_path, "r") as f:
            self.templates = yaml.safe_load(f)
        self.base_date = datetime(2025, 1, 1)
        random.seed(seed)

    def generate_benchmark_set(self, count: int) -> Dict[str, Any]:
        """Generates memories and queries that target them."""
        memories = self._generate_memories(count)
        queries = self._generate_queries(memories)

        return {
            "name": f"gold_standard_{count}",
            "description": f"Automated gold standard with {count} unique memories",
            "memories": memories,
            "queries": queries,
        }

    def _generate_memories(self, count: int) -> List[Dict[str, Any]]:
        domain_mix = {"industrial": 0.6, "academic": 0.3, "nine_five": 0.1}
        memories = []
        seen_content = set()

        while len(memories) < count:
            domain = random.choices(
                list(domain_mix.keys()), weights=list(domain_mix.values())
            )[0]
            categories = list(self.templates["domains"][domain].keys())
            category = random.choice(categories)
            cfg = self.templates["domains"][domain][category]

            template = random.choice(cfg["patterns"])
            params = self._generate_params(cfg, domain, category, len(memories))

            try:
                content = template.format(**params)
                if content not in seen_content:
                    seen_content.add(content)
                    memories.append(
                        {
                            "id": f"doc_{len(memories):06d}",
                            "content": content,
                            "metadata": {
                                "domain": domain,
                                "category": category,
                                "params": params,
                            },
                        }
                    )
            except:
                continue
        return memories

    def _generate_queries(self, memories: List[Dict]) -> List[Dict]:
        queries = []
        # Target 10% of memories for testing
        targets = random.sample(memories, min(100, len(memories)))

        for m in targets:
            params = m["metadata"]["params"]
            category = m["metadata"]["category"]

            # Create a query based on a unique anchor in the memory
            if "sn" in params:
                query = f"Show me maintenance details for serial {params['sn']}"
            elif "job_id" in params:
                query = f"What happened during {params['job_id']}?"
            elif "uuid" in params:
                query = f"Trace request {params['uuid']}"
            else:
                # Semantic query from content
                words = m["content"].split()
                query = " ".join(words[2 : min(8, len(words))])

            queries.append(
                {
                    "query": query,
                    "expected_source_ids": [m["id"]],  # This is the original DOC id
                    "category": category,
                }
            )
        return queries

    def _generate_params(
        self, cfg: Dict, domain: str, category: str, idx: int
    ) -> Dict[str, Any]:
        params = {
            "timestamp": (self.base_date + timedelta(minutes=idx * 2)).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "uuid": str(uuid.uuid4())[:8],
            "latency": random.randint(5, 2000),
            "count": random.randint(1, 100),
            "val": round(random.uniform(20.0, 95.0), 1),
            "threshold": 85,
            "percent": random.randint(0, 100),
            "result": random.choice(["confirmed", "inconclusive", "anomalous"]),
            "condition": random.choice(["high pressure", "vacuum", "ambient"]),
            "effect": random.choice(["interference", "resonance", "decay"]),
        }

        singular_map = {
            "theories": "theory",
            "particles": "particle",
            "environments": "environment",
            "authors": "author",
            "titles": "title",
            "themes": "theme",
            "machines": "machine",
            "services": "service",
            "levels": "level",
            "components": "component",
            "priorities": "priority",
            "descriptions": "description",
            "types": "type",
            "departments": "department",
            "topics": "topic",
        }

        for key, values in cfg.items():
            if not isinstance(values, list) or key == "patterns":
                continue
            param_name = singular_map.get(key, key[:-1] if key.endswith("s") else key)
            params[param_name] = random.choice(values)

        if domain == "industrial":
            params["pool_id"] = f"P-{random.randint(1, 20):02d}"
            params["sn"] = f"SN-{random.randint(100000, 999999)}"
            params["job_id"] = f"JOB-{idx:05d}"

        return params
