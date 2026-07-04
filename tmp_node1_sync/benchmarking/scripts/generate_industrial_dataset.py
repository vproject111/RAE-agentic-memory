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


class IndustrialDataGenerator:
    """Generate realistic industrial benchmark data"""

    def __init__(self, seed: int = 42):
        random.seed(seed)
        self.domains = self._init_domains()
        self.base_date = datetime(2024, 1, 1)

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
            seconds=idx * 30
        )  # More frequent for logs

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

        timestamp = self.base_date + timedelta(hours=idx)

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
            },
        }

    def generate_metric_entry(self, idx: int) -> Dict:
        """Generate a metrics memory"""
        domain = self.domains["metrics"]
        metric_type = random.choice(domain["types"])
        server_id = f"srv-{random.randint(1, 200):03d}"
        cluster_id = f"cls-{random.choice(['alpha', 'beta', 'prod'])}"

        value = random.randint(20, 95)
        timestamp = self.base_date + timedelta(minutes=idx)

        template = random.choice(domain["templates"])
        text = template.format(
            metric_type=metric_type,
            server_id=server_id,
            value=value,
            time=timestamp.strftime("%H:%M"),
            threshold=random.choice([80, 90, 95]),
            cluster_id=cluster_id,
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
        text = template.format(
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

        # Ensure 'database' is covered if selected
        if "database" in paths and "database" not in text:
            # Randomly inject specific database docs to ensure coverage for common queries
            if random.random() < 0.1:
                text = f"Documentation ({doc_type}): Database schema and connection string configuration."

        return {
            "id": f"doc_{idx:06d}",
            "text": text,
            "tags": ["documentation", doc_type, "api"],
            "metadata": {
                "source": "Technical Documentation",
                "importance": 0.7,
                "type": doc_type,
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
        text = template.format(
            id=idx,
            service=service,
            duration=duration,
            severity=severity,
            description="unexpected error rate increase",
            count=affected_users,
            incident_type="Database failover",
            root_cause="Configuration drift",
        )

        timestamp = self.base_date + timedelta(days=idx // 20)

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
            },
        }

    def generate_memories(self, count: int) -> List[Dict]:
        """Generate mixed collection of memories"""
        memories = []

        # Distribution: 40% logs, 25% tickets, 20% metrics, 10% docs, 5% incidents
        distributions = [
            (0.40, self.generate_log_entry),
            (0.25, self.generate_ticket_entry),
            (0.20, self.generate_metric_entry),
            (0.10, self.generate_doc_entry),
            (0.05, self.generate_incident_entry),
        ]

        for idx in range(count):
            rand = random.random()
            cumulative: float = 0.0
            for threshold, generator in distributions:
                cumulative += threshold
                if rand < cumulative:
                    memories.append(generator(idx))
                    break

        # Fallback if floating point weirdness
        if len(memories) < count:
            for i in range(count - len(memories)):
                memories.append(self.generate_log_entry(count + i))

        return memories

    def generate_queries(self, num_queries: int, memories: List[Dict]) -> List[Dict]:
        """Generate queries based on memories"""
        queries: List[Dict] = []

        # Sample different types of queries
        query_templates = [
            {
                "template": "What {service} issues occurred?",
                "filter_tag": "log",
                "category": "service_issues",
            },
            {
                "template": "Show critical incidents",
                "filter_tag": "incident",
                "category": "incidents",
            },
            {
                "template": "What are high priority tickets?",
                "filter_tag": "ticket",
                "category": "tickets",
            },
            {
                "template": "What servers have high {metric}?",
                "filter_tag": "metric",
                "category": "metrics",
            },
            {
                "template": "Find documentation about {component}",
                "filter_tag": "documentation",
                "category": "documentation",
            },
        ]

        attempts = 0
        max_attempts = num_queries * 5  # Prevent infinite loops

        while len(queries) < num_queries and attempts < max_attempts:
            attempts += 1
            template_info = random.choice(query_templates)
            template = template_info["template"]

            # Select parameters first to allow filtering
            service_param = random.choice(self.domains["logs"]["services"])
            metric_param = random.choice(
                ["cpu_usage", "memory", "disk_io", "error_rate"]
            )
            component_param = random.choice(
                ["API", "authentication", "database", "search", "billing"]
            )

            # Format query
            query_text = template.format(
                service=service_param,
                metric=metric_param,
                component=component_param,
            )

            # Determine relevance keyword based on what's in the template
            relevance_keyword = None
            if "{service}" in template:
                relevance_keyword = service_param
            elif "{metric}" in template:
                relevance_keyword = metric_param
            elif "{component}" in template:
                if component_param == "API":
                    relevance_keyword = "api"
                elif component_param == "authentication":
                    relevance_keyword = "auth"
                else:
                    relevance_keyword = component_param.lower()

            # Find relevant memories (tag + content match)
            filter_tag = template_info["filter_tag"]
            relevant_memories = []

            for m in memories:
                if filter_tag not in m["tags"]:
                    continue

                # If we have a specific keyword, check for it
                if relevance_keyword:
                    # Check text and specific metadata fields
                    text_lower = m["text"].lower()

                    # Exact or partial match logic
                    text_match = relevance_keyword in text_lower
                    meta_match = any(
                        str(v).lower() == relevance_keyword
                        for v in m["metadata"].values()
                    )

                    # For docs, check if the keyword appears in the path or description
                    doc_match = False
                    if filter_tag == "documentation":
                        if relevance_keyword in text_lower:
                            doc_match = True

                    if text_match or meta_match or doc_match:
                        relevant_memories.append(m)
                else:
                    # No keyword (e.g. "critical incidents")
                    if "critical" in template:
                        # Check tags, priority, or severity
                        is_crit = False
                        if "critical" in m.get("tags", []):
                            is_crit = True
                        if m.get("metadata", {}).get("priority") == "critical":
                            is_crit = True
                        if m.get("metadata", {}).get("severity") == "sev1":
                            is_crit = True

                        if is_crit:
                            relevant_memories.append(m)

                    elif "high priority" in template:
                        if m.get("metadata", {}).get("priority") == "high":
                            relevant_memories.append(m)
                    else:
                        relevant_memories.append(m)

            # Use ALL relevant memories as expected results
            if not relevant_memories:
                continue

            expected_ids = [m["id"] for m in relevant_memories]
            num_expected = len(expected_ids)

            difficulty = (
                "easy"
                if num_expected <= 5
                else "medium" if num_expected <= 50 else "hard"
            )

            queries.append(
                {
                    "query": query_text,
                    "expected_source_ids": expected_ids,
                    "difficulty": difficulty,
                    "category": template_info["category"],
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
