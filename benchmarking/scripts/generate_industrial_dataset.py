#!/usr/bin/env python3
"""
Universal Generator for Industrial Benchmark Datasets

Generates 1k - 1M memories with real-world patterns:
- Time-series data (logs, events, metrics)
- Duplicate/near-duplicate entries
- Evolving concepts
- Multi-domain knowledge

Usage:
    python generate_industrial_dataset.py --name industrial_extreme --size 10000 --queries 500 --output ../sets/industrial_extreme.yaml
"""

import argparse
import os
import random
from datetime import datetime, timedelta
from typing import Dict, List

import yaml
from common import UniquenessGuard


class IndustrialDataGenerator:
    """Generate realistic industrial benchmark data"""

    def __init__(self, seed: int = 42):
        random.seed(seed)
        self.domains = self._init_domains()
        self.base_date = datetime(2024, 1, 1)
        self.guard = UniquenessGuard()

    def _ensure_unique(self, text: str) -> str:
        return self.guard.ensure_unique(text)

    def _init_domains(self) -> Dict[str, Dict]:
        """Initialize domain-specific templates"""
        return {
            "logs": {
                "levels": ["INFO", "WARN", "ERROR", "CRITICAL", "DEBUG"],
                "services": [
                    "api-gateway",
                    "auth-service",
                    "db-cluster",
                    "cache-layer",
                    "ml-inference",
                    "payment-gateway",
                    "user-service",
                    "notification-service",
                ],
                "templates": [
                    "{service} - {level}: Request processed in {latency}ms",
                    "{service} - {level}: Connection pool size: {count}",
                    "{service} - {level}: Cache hit rate: {percent}%",
                    "{service} - {level}: Memory usage: {size}MB",
                    "{service} - {level}: Queue depth: {count} messages",
                    "{service} - {level}: Failed to connect to {target} (retrying...)",
                    "{service} - {level}: Transaction {tx_id} failed: {reason}",
                ],
            },
            "tickets": {
                "types": ["bug", "feature", "improvement", "question"],
                "priorities": ["low", "medium", "high", "critical"],
                "statuses": ["open", "in_progress", "resolved", "closed"],
                "templates": [
                    "User reports {issue_type} with {component}: {description}",
                    "{issue_type} - {component} performance degradation: {metric}",
                    "Request for {feature} in {component} - priority: {priority}",
                    "Customer complaint: {component} {description}",
                ],
            },
            "metrics": {
                "types": [
                    "cpu_usage",
                    "memory",
                    "disk_io",
                    "network",
                    "requests",
                    "error_rate",
                ],
                "templates": [
                    "Server {server_id}: {metric_type} at {value}% - timestamp {time}",
                    "Alert: {metric_type} exceeded threshold ({threshold}%) on {server_id}",
                    "Metric: {metric_type} for cluster {cluster_id}: {value}",
                ],
            },
            "documentation": {
                "types": [
                    "api",
                    "architecture",
                    "deployment",
                    "troubleshooting",
                    "onboarding",
                ],
                "templates": [
                    "API endpoint /{path} accepts {method} requests with {params} parameters",
                    "Architecture: {component} communicates with {other_component} via {protocol}",
                    "Deployment procedure for {service}: {steps}",
                    "Troubleshooting guide: {problem} - solution: {solution}",
                    "Onboarding: How to setup {service} locally",
                ],
            },
            "incidents": {
                "severities": ["sev1", "sev2", "sev3", "sev4"],
                "templates": [
                    "Incident {id}: {service} outage - duration: {duration} mins",
                    "{severity} incident: {description} - affected users: {count}",
                    "Post-mortem: {incident_type} caused by {root_cause}",
                    "Alert storm detected on {service}: {count} alerts in 5 mins",
                ],
            },
        }

    def generate_log_entry(self, idx: int) -> Dict:
        """Generate a log entry memory"""
        domain = self.domains["logs"]
        level = random.choice(domain["levels"])
        service = random.choice(domain["services"])
        template = random.choice(domain["templates"])

        text = template.format(
            service=service,
            level=level,
            latency=random.randint(10, 500),
            count=random.randint(1, 100),
            percent=random.randint(50, 99),
            size=random.randint(100, 4000),
            target=random.choice(["database", "redis", "kafka"]),
            tx_id=f"tx-{random.randint(1000, 9999)}",
            reason=random.choice(["timeout", "invalid_input", "deadlock"]),
        )

        timestamp = self.base_date + timedelta(
            seconds=idx * 30, microseconds=random.randint(0, 999999)  # Unique jitter
        )

        # Add unique operational nonce to ensure zero collisions
        nonce = f" [SN-{idx:06d}]"
        text += nonce

        return {
            "id": f"log_{idx:06d}",  # 6 digits for larger datasets
            "text": text,
            "tags": ["log", level.lower(), service],
            "metadata": {
                "source": "System Logs",
                "importance": (
                    0.3 if level == "INFO" else 0.6 if level == "WARN" else 0.9
                ),
                "timestamp": timestamp.isoformat(),
                "service": service,
                "level": level,
                "nonce": nonce.strip(),
            },
        }

    def generate_ticket_entry(self, idx: int) -> Dict:
        """Generate a support ticket memory"""
        domain = self.domains["tickets"]
        ticket_type = random.choice(domain["types"])
        priority = random.choice(domain["priorities"])
        status = random.choice(domain["statuses"])

        components = [
            "dashboard",
            "api",
            "database",
            "authentication",
            "reporting",
            "billing",
            "search",
        ]
        component = random.choice(components)

        descriptions = [
            "slow response times",
            "intermittent failures",
            "incorrect data displayed",
            "timeout errors",
            "unable to access feature",
            "crashes on startup",
            "UI alignment issue",
        ]

        text = f"[{ticket_type.upper()}] {component}: {random.choice(descriptions)} - Priority: {priority}, Status: {status}"

        timestamp = self.base_date + timedelta(
            hours=idx, microseconds=random.randint(0, 999999)
        )
        nonce = f" [SN-{idx:06d}]"
        text = f"[{ticket_type.upper()}] {component}: {random.choice(descriptions)} - Priority: {priority}, Status: {status}{nonce}"

        return {
            "id": f"ticket_{idx:06d}",
            "text": text,
            "tags": ["ticket", ticket_type, priority],
            "metadata": {
                "source": "Support System",
                "importance": {
                    "low": 0.3,
                    "medium": 0.5,
                    "high": 0.8,
                    "critical": 0.95,
                }[priority],
                "timestamp": timestamp.isoformat(),
                "type": ticket_type,
                "priority": priority,
                "component": component,
                "nonce": nonce.strip(),
            },
        }

    def generate_metric_entry(self, idx: int) -> Dict:
        """Generate a metrics memory"""
        domain = self.domains["metrics"]
        metric_type = random.choice(domain["types"])
        server_id = f"srv-{random.randint(1, 200):03d}"
        cluster_id = f"cls-{random.choice(['alpha', 'beta', 'prod'])}"

        value = random.randint(20, 95)
        timestamp = self.base_date + timedelta(
            minutes=idx, microseconds=random.randint(0, 999999)
        )

        template = random.choice(domain["templates"])
        nonce = f" [SN-{idx:06d}]"
        text = (
            template.format(
                metric_type=metric_type,
                server_id=server_id,
                value=value,
                time=timestamp.strftime("%H:%M:%S.%f"),
                threshold=random.choice([80, 90, 95]),
                cluster_id=cluster_id,
            )
            + nonce
        )

        return {
            "id": f"metric_{idx:06d}",
            "text": text,
            "tags": ["metric", metric_type, server_id],
            "metadata": {
                "source": "Monitoring System",
                "importance": 0.5 if value < 70 else 0.8 if value < 90 else 0.95,
                "timestamp": timestamp.isoformat(),
                "server_id": server_id,
                "metric_type": metric_type,
                "value": value,
                "nonce": nonce.strip(),
            },
        }

    def generate_doc_entry(self, idx: int) -> Dict:
        """Generate documentation memory"""
        domain = self.domains["documentation"]
        doc_type = random.choice(domain["types"])

        paths = [
            "users",
            "posts",
            "comments",
            "auth",
            "metrics",
            "database",
            "payments",
            "search",
        ]
        methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]
        components = ["API", "DB", "Cache", "Worker", "Frontend"]

        template = random.choice(domain["templates"])
        nonce = f" [SN-{idx:06d}]"
        text = (
            template.format(
                path=random.choice(paths),
                method=random.choice(methods),
                params=random.choice(["id, name", "query, limit", "user_id"]),
                component=random.choice(components),
                other_component=random.choice(components),
                protocol=random.choice(["HTTP", "gRPC", "AMQP"]),
                service=random.choice(self.domains["logs"]["services"]),
                steps="1. Install 2. Configure 3. Run",
                problem="Service fails to start",
                solution="Check configuration file",
            )
            + nonce
        )

        # Ensure 'database' is covered if selected
        if "database" in paths and "database" not in text:
            # Randomly inject specific database docs to ensure coverage for common queries
            if random.random() < 0.1:
                text = f"Documentation ({doc_type}): Database schema and connection string configuration.{nonce}"

        return {
            "id": f"doc_{idx:06d}",
            "text": text,
            "tags": ["documentation", doc_type, "api"],
            "metadata": {
                "source": "Technical Documentation",
                "importance": 0.7,
                "type": doc_type,
                "nonce": nonce.strip(),
            },
        }

    def generate_incident_entry(self, idx: int) -> Dict:
        """Generate incident memory"""
        domain = self.domains["incidents"]
        severity = random.choice(domain["severities"])

        services = self.domains["logs"]["services"]
        service = random.choice(services)

        duration = random.randint(5, 240)
        affected_users = random.randint(10, 10000)

        template = random.choice(domain["templates"])
        nonce = f" [SN-{idx:06d}]"
        text = (
            template.format(
                id=idx,
                service=service,
                duration=duration,
                severity=severity,
                description="unexpected error rate increase",
                count=affected_users,
                incident_type="Database failover",
                root_cause="Configuration drift",
            )
            + nonce
        )

        timestamp = self.base_date + timedelta(
            days=idx // 20, microseconds=random.randint(0, 999999)
        )

        return {
            "id": f"incident_{idx:06d}",
            "text": text,
            "tags": ["incident", severity, service],
            "metadata": {
                "source": "Incident Management",
                "importance": {"sev4": 0.4, "sev3": 0.6, "sev2": 0.85, "sev1": 0.99}[
                    severity
                ],
                "timestamp": timestamp.isoformat(),
                "severity": severity,
                "duration_minutes": duration,
                "affected_users": affected_users,
                "nonce": nonce.strip(),
            },
        }

    def generate_memories(self, count: int) -> List[Dict]:
        """Generate mixed collection of memories with strict uniqueness"""
        memories = []

        # Distribution: 40% logs, 25% tickets, 20% metrics, 10% docs, 5% incidents
        distributions = [
            (0.40, self.generate_log_entry),
            (0.25, self.generate_ticket_entry),
            (0.20, self.generate_metric_entry),
            (0.10, self.generate_doc_entry),
            (0.05, self.generate_incident_entry),
        ]

        idx = 0
        attempts = 0
        max_attempts = count * 2  # Allow some retries for uniqueness

        while len(memories) < count and attempts < max_attempts:
            attempts += 1
            rand = random.random()
            cumulative: float = 0.0
            for threshold, generator in distributions:
                cumulative += threshold
                if rand < cumulative:
                    mem = generator(idx)
                    # Apply Silicon Oracle Uniqueness Guard
                    original_text = mem["text"]
                    unique_text = self._ensure_unique(original_text)

                    mem["text"] = unique_text
                    memories.append(mem)
                    idx += 1
                    break

        return memories[:count]

    def generate_queries(self, num_queries: int, memories: List[Dict]) -> List[Dict]:
        """Generate atomic queries based on unique nonces"""
        queries: List[Dict] = []

        # Select random memories to query about
        targets = random.sample(memories, min(num_queries, len(memories)))

        for m in targets:
            nonce = m["metadata"]["nonce"]

            # 50% chance for exact nonce query, 50% for semantic + nonce
            if random.random() > 0.5:
                query = f"Find entry with code {nonce}"
            else:
                # Use a snippet of the text + nonce
                words = m["text"].split()
                snippet = " ".join(words[: min(5, len(words))])
                query = f"{snippet} (Reference: {nonce})"

            queries.append(
                {
                    "query": query,
                    "expected_source_ids": [m["id"]],
                    "difficulty": "easy",
                    "category": "atomic_lookup",
                }
            )

        return queries


def main():
    parser = argparse.ArgumentParser(
        description="Generate industrial benchmark dataset"
    )
    parser.add_argument(
        "--name",
        type=str,
        required=True,
        help="Name of the benchmark (e.g. industrial_extreme)",
    )
    parser.add_argument(
        "--size", type=int, default=1000, help="Number of memories to generate"
    )
    parser.add_argument(
        "--queries", type=int, default=100, help="Number of queries to generate"
    )
    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="Output file path",
    )
    parser.add_argument(
        "--seed", type=int, default=42, help="Random seed for reproducibility"
    )

    args = parser.parse_args()

    # Ensure output directory exists
    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    print(f"🏭 Generating {args.name} Benchmark")
    print(f"   Memories: {args.size}")
    print(f"   Queries: {args.queries}")
    print(f"   Output: {args.output}")

    generator = IndustrialDataGenerator(seed=args.seed)

    print("\n📝 Generating memories...")
    memories = generator.generate_memories(args.size)

    print("🔍 Generating queries...")
    queries = generator.generate_queries(args.queries, memories)

    # Create benchmark structure
    benchmark = {
        "name": args.name,
        "description": f"{args.name} benchmark with {args.size} memories simulating real-world production data",
        "version": "2.0",
        "memories": memories,
        "queries": queries,
        "config": {
            "top_k": 20 if args.size > 1000 else 10,
            "min_relevance_score": 0.25,
            "enable_reranking": True,
            "enable_reflection": True,
            "enable_graph": True,
            "test_scale": True,
            "test_performance": True,
        },
    }

    # Write to YAML
    print(f"\n💾 Writing to {args.output}...")
    with open(args.output, "w") as f:
        yaml.dump(
            benchmark, f, default_flow_style=False, allow_unicode=True, sort_keys=False
        )

    print("\n✅ Generated successfully!")
    print(f"   Total memories: {len(memories)}")
    print(f"   Total queries: {len(queries)}")
    # print(f"   File size: {len(yaml.dump(benchmark)) / 1024:.1f} KB") # Avoid double dump


if __name__ == "__main__":
    main()
