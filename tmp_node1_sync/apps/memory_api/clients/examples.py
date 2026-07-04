"""
RAE API Client - Usage Examples

This module demonstrates how to use the enhanced RAE API client
with various resilience patterns.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from apps.memory_api.clients.rae_api import RAEAPIClient
from apps.memory_api.clients.rae_client import ErrorCategory, RAEClientError

# ============================================================================
# Basic Usage
# ============================================================================


async def basic_usage_example():
    """Basic client usage with automatic retry and circuit breaker."""

    # Initialize client with default settings
    async with RAEAPIClient(
        base_url="http://localhost:8000",
        api_key="your-api-key",
        tenant_id="example-tenant",
        project_id="example-project",
    ) as client:
        # Create a memory
        memory = await client.create_memory(
            content="This is a test memory", importance=0.8, tags=["test", "example"]
        )
        print(f"Created memory: {memory['id']}")

        # Search memories
        results = await client.search_memories(query="test memory", k=10)
        print(f"Found {len(results['results'])} memories")

        # Generate reflection
        reflection = await client.generate_reflection(
            memory_ids=[memory["id"]], reflection_type="insight"
        )
        print(f"Generated reflection: {reflection['reflection_id']}")


# ============================================================================
# Advanced Configuration
# ============================================================================


async def advanced_configuration_example():
    """Client with custom retry and circuit breaker configuration."""

    async with RAEAPIClient(
        base_url="http://localhost:8000",
        api_key="your-api-key",
        tenant_id="example-tenant",
        project_id="example-project",
        # Retry configuration
        max_retries=5,
        initial_backoff_ms=200,
        max_backoff_ms=30000,
        backoff_multiplier=2.5,
        # Circuit breaker configuration
        enable_circuit_breaker=True,
        failure_threshold=3,
        success_threshold=2,
        # Cache configuration
        enable_cache=True,
        cache_ttl_seconds=600,
        # Connection configuration
        timeout=60.0,
        max_connections=200,
    ) as client:
        # Use client normally
        # Retry and circuit breaker work automatically
        results = await client.hybrid_search(
            query="machine learning optimization",
            k=20,
            weight_profile="quality_focused",
            enable_reranking=True,
        )

        print(f"Hybrid search returned {len(results['results'])} results")

        # Check client statistics
        stats = client.get_stats()
        print(f"Client stats: {stats}")


# ============================================================================
# Error Handling
# ============================================================================


async def error_handling_example():
    """Proper error handling with error classification."""

    async with RAEAPIClient(
        base_url="http://localhost:8000",
        api_key="your-api-key",
        tenant_id="example-tenant",
        project_id="example-project",
    ) as client:
        try:
            # This might fail
            await client.get_memory(uuid4())

        except RAEClientError as e:
            # Handle specific error categories
            if e.category == ErrorCategory.NETWORK:
                print("Network error - check connectivity")
            elif e.category == ErrorCategory.TIMEOUT:
                print("Request timeout - server may be overloaded")
            elif e.category == ErrorCategory.AUTHENTICATION:
                print("Authentication error - check API key")
            elif e.category == ErrorCategory.SERVER_ERROR:
                print(f"Server error: {e.message}")
            elif e.category == ErrorCategory.RATE_LIMIT:
                print("Rate limited - back off and retry later")
            else:
                print(f"Unexpected error: {e.message}")

            # Log original error if available
            if e.original_error:
                print(f"Original error: {e.original_error}")


# ============================================================================
# Caching Examples
# ============================================================================


async def caching_example():
    """Using response cache for GET requests."""

    async with RAEAPIClient(
        base_url="http://localhost:8000",
        api_key="your-api-key",
        tenant_id="example-tenant",
        project_id="example-project",
        enable_cache=True,
        cache_ttl_seconds=300,
    ) as client:
        # First call - cache miss
        print("First call (cache miss)")
        await client.search_memories(query="machine learning", k=10)

        # Second call - cache hit (instant)
        print("Second call (cache hit)")
        await client.search_memories(query="machine learning", k=10)

        # Check stats to see cache hit
        stats = client.get_stats()
        print(f"Cache hit rate: {stats.get('cache_hit_rate', 0):.2%}")

        # Invalidate cache for specific request
        client.invalidate_cache("GET", "/v1/memories/search")

        # Clear entire cache
        client.client.cache.clear()


# ============================================================================
# Semantic Memory Workflow
# ============================================================================


async def semantic_memory_workflow():
    """Complete semantic memory workflow."""

    async with RAEAPIClient(
        base_url="http://localhost:8000",
        api_key="your-api-key",
        tenant_id="example-tenant",
        project_id="example-project",
    ) as client:
        # 1. Create memory
        memory = await client.create_memory(
            content="Python is a high-level programming language with dynamic semantics",
            importance=0.9,
            tags=["programming", "python"],
        )
        print(f"Created memory: {memory['id']}")

        # 2. Extract semantic nodes
        extraction = await client.extract_semantics(memory_id=memory["id"])
        print(f"Extracted {extraction['nodes_created']} semantic nodes")

        # 3. Semantic search
        search_results = await client.semantic_search(
            query="programming languages", k=10
        )
        print(f"Semantic search found {len(search_results['results'])} results")

        # 4. Extract knowledge graph (replaces manual graph CRUD)
        # Note: create_graph_edge() is deprecated - use GraphRAG instead
        extraction = await client.extract_knowledge_graph(limit=10, min_confidence=0.7)
        print(f"Extracted {len(extraction.get('triples', []))} knowledge triples")


# ============================================================================
# Evaluation Workflow
# ============================================================================


async def evaluation_workflow():
    """Search evaluation and drift detection."""

    async with RAEAPIClient(
        base_url="http://localhost:8000",
        api_key="your-api-key",
        tenant_id="example-tenant",
        project_id="example-project",
    ) as client:
        # Define relevance judgments (ground truth)
        relevance_judgments = {
            "query1": {
                "doc1": 1.0,  # Highly relevant
                "doc2": 0.5,  # Somewhat relevant
                "doc3": 0.0,  # Not relevant
            }
        }

        # Search results to evaluate
        search_results = {
            "query1": [
                {"document_id": "doc1", "rank": 1, "score": 0.95},
                {"document_id": "doc3", "rank": 2, "score": 0.80},
                {"document_id": "doc2", "rank": 3, "score": 0.75},
            ]
        }

        # Evaluate search quality
        evaluation = await client.evaluate_search(
            relevance_judgments=relevance_judgments,
            search_results=search_results,
            metrics=["mrr", "ndcg", "precision", "recall"],
        )

        print("Search quality metrics:")
        print(f"  MRR: {evaluation['evaluation_result']['metrics']['mrr']:.3f}")
        print(f"  NDCG@10: {evaluation['evaluation_result']['metrics']['ndcg@10']:.3f}")

        # Detect drift
        now = datetime.now(timezone.utc)
        baseline_start = now - timedelta(days=14)
        baseline_end = now - timedelta(days=7)
        current_start = now - timedelta(days=7)
        current_end = now

        drift_result = await client.detect_drift(
            metric_name="search_score",
            drift_type="data_drift",
            baseline_start=baseline_start,
            baseline_end=baseline_end,
            current_start=current_start,
            current_end=current_end,
        )

        if drift_result["drift_result"]["drift_detected"]:
            print("Drift detected!")
            print(f"  Severity: {drift_result['drift_result']['severity']}")
            print(f"  Actions: {drift_result['drift_result']['recommended_actions']}")


# ============================================================================
# Event Triggers and Automation
# ============================================================================


async def event_triggers_example():
    """Creating and using event triggers."""

    async with RAEAPIClient(
        base_url="http://localhost:8000",
        api_key="your-api-key",
        tenant_id="example-tenant",
        project_id="example-project",
    ) as client:
        # Create trigger: Generate reflection when 50 memories created
        trigger = await client.create_trigger(
            rule_name="Auto Reflection on 50 Memories",
            event_types=["memory_created"],
            actions=[
                {
                    "action_type": "generate_reflection",
                    "config": {"reflection_type": "synthesis"},
                }
            ],
            condition_group={
                "operator": "AND",
                "conditions": [
                    {
                        "field": "payload.memory_count",
                        "operator": "greater_equal",
                        "value": 50,
                    }
                ],
            },
            priority=7,
        )
        print(f"Created trigger: {trigger['trigger_id']}")

        # Emit custom event
        event_result = await client.emit_event(
            event_type="quality_degraded",
            payload={"quality_score": 0.65, "threshold": 0.70, "metric": "mrr"},
            tags=["quality", "alert"],
        )
        print(f"Event emitted: {event_result['event_id']}")
        print(f"Triggers matched: {event_result['triggers_matched']}")

        # List all triggers
        triggers = await client.list_triggers(limit=100)
        print(f"Total triggers: {triggers['total_count']}")


# ============================================================================
# Dashboard and Monitoring
# ============================================================================


async def dashboard_monitoring_example():
    """Using dashboard and monitoring features."""

    async with RAEAPIClient(
        base_url="http://localhost:8000",
        api_key="your-api-key",
        tenant_id="example-tenant",
        project_id="example-project",
    ) as client:
        # Get dashboard metrics
        metrics = await client.get_dashboard_metrics(period="last_24h")
        print("Dashboard metrics:")
        print(f"  Total memories: {metrics['system_metrics']['total_memories']}")
        print(f"  Total reflections: {metrics['system_metrics']['total_reflections']}")
        print(f"  Active triggers: {metrics['system_metrics']['active_triggers']}")
        print(f"  Health status: {metrics['system_metrics']['health_status']}")

        # Get visualization data - Reflection tree
        reflection_tree = await client.get_visualization(
            visualization_type="reflection_tree", max_depth=5, limit=100
        )

        if reflection_tree["reflection_tree"]:
            tree = reflection_tree["reflection_tree"]
            print(f"Reflection tree root: {tree['content'][:50]}...")
            print(f"Children: {len(tree['children'])}")

        # Get visualization data - Semantic graph
        semantic_graph = await client.get_visualization(
            visualization_type="semantic_graph", limit=50
        )

        if semantic_graph["semantic_graph"]:
            graph = semantic_graph["semantic_graph"]
            print("Semantic graph:")
            print(f"  Nodes: {graph['node_count']}")
            print(f"  Edges: {graph['edge_count']}")
            print(f"  Avg degree: {graph['avg_degree']:.2f}")

        # Check system health
        health = await client.get_system_health(include_sub_components=True)

        print(f"System health: {health['system_health']['overall_status']}")
        print("Components:")
        for component in health["system_health"]["components"]:
            print(f"  {component['component_name']}: {component['status']}")

        if health["recommendations"]:
            print("Recommendations:")
            for rec in health["recommendations"]:
                print(f"  - {rec}")


# ============================================================================
# Bulk Operations
# ============================================================================


async def bulk_operations_example():
    """Performing bulk operations efficiently."""

    async with RAEAPIClient(
        base_url="http://localhost:8000",
        api_key="your-api-key",
        tenant_id="example-tenant",
        project_id="example-project",
        max_connections=50,  # Higher connection pool for parallel requests
    ) as client:
        # Create multiple memories in parallel
        memory_contents = [
            "First memory about machine learning",
            "Second memory about data science",
            "Third memory about artificial intelligence",
            "Fourth memory about neural networks",
            "Fifth memory about deep learning",
        ]

        # Create tasks
        tasks = [
            client.create_memory(content=content, importance=0.7, tags=["bulk_import"])
            for content in memory_contents
        ]

        # Execute in parallel
        memories = await asyncio.gather(*tasks)
        print(f"Created {len(memories)} memories in parallel")

        # Extract semantics from all memories in parallel
        extraction_tasks = [
            client.extract_semantics(memory_id=memory["id"]) for memory in memories
        ]

        extractions = await asyncio.gather(*extraction_tasks)
        total_nodes = sum(e["nodes_created"] for e in extractions)
        print(f"Extracted {total_nodes} semantic nodes in total")


# ============================================================================
# Main Example Runner
# ============================================================================


async def main():
    """Run all examples."""
    print("=" * 80)
    print("RAE API Client - Usage Examples")
    print("=" * 80)

    examples = [
        ("Basic Usage", basic_usage_example),
        ("Advanced Configuration", advanced_configuration_example),
        ("Error Handling", error_handling_example),
        ("Caching", caching_example),
        ("Semantic Memory Workflow", semantic_memory_workflow),
        ("Evaluation Workflow", evaluation_workflow),
        ("Event Triggers", event_triggers_example),
        ("Dashboard Monitoring", dashboard_monitoring_example),
        ("Bulk Operations", bulk_operations_example),
    ]

    for name, example_func in examples:
        print(f"\n{'=' * 80}")
        print(f"Example: {name}")
        print("=" * 80)

        try:
            await example_func()
        except Exception as e:
            print(f"Example failed: {e}")

        await asyncio.sleep(1)  # Brief pause between examples


if __name__ == "__main__":
    # Run examples
    asyncio.run(main())
