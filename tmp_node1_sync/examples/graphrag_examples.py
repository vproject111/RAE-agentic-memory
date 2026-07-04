"""
GraphRAG Usage Examples

This file demonstrates various usage patterns for RAE's GraphRAG capabilities.
"""

import asyncio

import httpx

# Configuration
RAE_API_URL = "http://localhost:8000"
TENANT_ID = "demo-tenant"
PROJECT_ID = "demo-project"
API_KEY = "your-api-key-here"  # If authentication is enabled


# Helper function for API calls
async def rae_request(method: str, endpoint: str, **kwargs):
    """Make authenticated request to RAE API."""
    headers = {"X-Tenant-ID": TENANT_ID, "Content-Type": "application/json"}

    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"

    async with httpx.AsyncClient() as client:
        response = await client.request(
            method=method, url=f"{RAE_API_URL}{endpoint}", headers=headers, **kwargs
        )
        response.raise_for_status()
        return response.json()


# Example 1: Basic Graph Extraction
async def example_basic_extraction():
    """
    Example 1: Extract knowledge graph from episodic memories.

    This is the simplest way to get started with GraphRAG.
    """
    print("=== Example 1: Basic Graph Extraction ===\n")

    # First, store some episodic memories
    memories = [
        "User Alice reported bug #101 in the payment module causing transaction failures.",
        "Developer Bob fixed bug #101 by updating the PaymentProcessor class.",
        "The PaymentProcessor depends on the StripeAPI for payment processing.",
        "Feature request #202: Add support for PayPal integration to the payment system.",
    ]

    print("Storing memories...")
    for memory in memories:
        await rae_request(
            "POST",
            "/v1/memory/store",
            json={
                "content": memory,
                "layer": "em",
                "project": PROJECT_ID,
                "tags": ["payment", "development"],
            },
        )

    print(f"Stored {len(memories)} memories\n")

    # Extract knowledge graph
    print("Extracting knowledge graph...")
    result = await rae_request(
        "POST",
        "/v1/graph/extract",
        json={
            "project_id": PROJECT_ID,
            "limit": 50,
            "min_confidence": 0.5,
            "auto_store": True,
        },
    )

    print(f"Extracted {len(result['triples'])} triples")
    print(f"Found {len(result['extracted_entities'])} entities")
    print("\nSample triples:")
    for triple in result["triples"][:3]:
        print(
            f"  {triple['source']} --[{triple['relation']}]--> {triple['target']} (confidence: {triple['confidence']})"
        )

    print()


# Example 2: Hybrid Search
async def example_hybrid_search():
    """
    Example 2: Perform hybrid search combining vector similarity and graph traversal.

    This provides richer context by exploring graph relationships.
    """
    print("=== Example 2: Hybrid Search ===\n")

    query = "payment bugs and their fixes"

    print(f"Query: '{query}'")
    print("Performing hybrid search with graph traversal...\n")

    result = await rae_request(
        "POST",
        "/v1/memory/query",
        json={
            "query_text": query,
            "k": 5,
            "use_graph": True,
            "graph_depth": 2,
            "project": PROJECT_ID,
        },
    )

    print(f"Found {len(result['results'])} vector matches")

    if result.get("graph_statistics"):
        stats = result["graph_statistics"]
        print(f"Graph nodes discovered: {stats.get('graph_nodes', 0)}")
        print(f"Graph edges discovered: {stats.get('graph_edges', 0)}")

    print("\nTop results:")
    for i, memory in enumerate(result["results"][:3], 1):
        print(f"{i}. [Score: {memory['score']:.3f}] {memory['content'][:100]}...")

    if result.get("synthesized_context"):
        print("\n--- Synthesized Context Preview ---")
        print(result["synthesized_context"][:500] + "...")

    print()


# Example 3: Advanced Graph Query
async def example_advanced_graph_query():
    """
    Example 3: Use dedicated graph query endpoint for complex searches.

    This endpoint provides full graph traversal results including nodes and edges.
    """
    print("=== Example 3: Advanced Graph Query ===\n")

    result = await rae_request(
        "POST",
        "/v1/graph/query",
        json={
            "query": "payment module dependencies and relationships",
            "project_id": PROJECT_ID,
            "top_k_vector": 5,
            "graph_depth": 3,
            "traversal_strategy": "bfs",
        },
    )

    print(f"Vector matches: {len(result['vector_matches'])}")
    print(f"Graph nodes: {len(result['graph_nodes'])}")
    print(f"Graph edges: {len(result['graph_edges'])}")

    print("\nGraph Structure:")
    print("Nodes:")
    for node in result["graph_nodes"][:5]:
        print(f"  - {node['label']} (depth: {node['depth']})")

    print("\nRelationships:")
    for edge in result["graph_edges"][:5]:
        print(f"  - {edge['relation']}")

    print()


# Example 4: Graph Statistics and Monitoring
async def example_graph_statistics():
    """
    Example 4: Monitor knowledge graph health and growth.

    Useful for understanding graph structure and planning optimizations.
    """
    print("=== Example 4: Graph Statistics ===\n")

    stats = await rae_request("GET", f"/v1/graph/stats?project_id={PROJECT_ID}")

    print(f"Project: {stats['project_id']}")
    print(f"Total nodes: {stats['total_nodes']}")
    print(f"Total edges: {stats['total_edges']}")
    print(f"Average edges per node: {stats['statistics']['avg_edges_per_node']}")

    print("\nUnique relations:")
    for relation in stats["unique_relations"]:
        print(f"  - {relation}")

    print()


# Example 5: Subgraph Exploration
async def example_subgraph_exploration():
    """
    Example 5: Explore local neighborhoods in the graph.

    Useful for understanding entity relationships and building visualizations.
    """
    print("=== Example 5: Subgraph Exploration ===\n")

    # First, get some nodes
    stats = await rae_request("GET", f"/v1/graph/nodes?project_id={PROJECT_ID}&limit=3")

    if stats:
        node_ids = [node["node_id"] for node in stats[:2]]
        node_ids_str = ",".join(node_ids)

        print(f"Exploring subgraph starting from: {', '.join(node_ids)}\n")

        result = await rae_request(
            "GET",
            f"/v1/graph/subgraph?project_id={PROJECT_ID}&node_ids={node_ids_str}&depth=2",
        )

        print(f"Nodes in subgraph: {result['statistics']['nodes_found']}")
        print(f"Edges in subgraph: {result['statistics']['edges_found']}")

        print("\nSubgraph structure:")
        for node in result["nodes"]:
            print(f"  Node: {node['label']}")

        for edge in result["edges"]:
            print(f"  Edge: {edge['relation']}")

    print()


# Example 6: Hierarchical Reflection
async def example_hierarchical_reflection():
    """
    Example 6: Generate hierarchical summaries from large episode collections.

    Uses map-reduce approach to handle thousands of episodes without hitting context limits.
    """
    print("=== Example 6: Hierarchical Reflection ===\n")

    print("Generating hierarchical reflection...")
    result = await rae_request(
        "POST",
        "/v1/graph/reflection/hierarchical",
        json={"project_id": PROJECT_ID, "bucket_size": 10, "max_episodes": 100},
    )

    print(f"Processed {result['episodes_processed']} episodes")
    print("\n--- Reflection Summary ---")
    print(result["summary"][:500] + "...")

    print()


# Example 7: Incremental Graph Updates
async def example_incremental_updates():
    """
    Example 7: Update knowledge graph incrementally as new memories arrive.

    This pattern is efficient for production systems with continuous memory ingestion.
    """
    print("=== Example 7: Incremental Graph Updates ===\n")

    # Simulate new memories arriving
    new_memories = [
        "QA team found regression in bug #101 after the recent fix.",
        "Bob reopened bug #101 and added additional test cases.",
    ]

    print("Storing new memories...")
    for memory in new_memories:
        await rae_request(
            "POST",
            "/v1/memory/store",
            json={"content": memory, "layer": "em", "project": PROJECT_ID},
        )

    # Extract only recent memories (efficient incremental update)
    print("Updating knowledge graph with recent memories...")
    result = await rae_request(
        "POST",
        "/v1/graph/extract",
        json={
            "project_id": PROJECT_ID,
            "limit": 10,  # Only process recent memories
            "min_confidence": 0.5,
            "auto_store": True,
        },
    )

    print(f"Added {len(result['triples'])} new triples to the graph")
    print()


# Example 8: Context-Rich AI Agent
async def example_ai_agent_integration():
    """
    Example 8: Integrate GraphRAG with an AI agent for context-rich responses.

    Demonstrates how to use synthesized context from hybrid search in LLM prompts.
    """
    print("=== Example 8: AI Agent Integration ===\n")

    user_question = "What are the known issues with the payment system?"

    print(f"User asks: '{user_question}'\n")

    # Get rich context using hybrid search
    context_result = await rae_request(
        "POST",
        "/v1/memory/query",
        json={
            "query_text": user_question,
            "k": 5,
            "use_graph": True,
            "graph_depth": 2,
            "project": PROJECT_ID,
        },
    )

    synthesized_context = context_result.get("synthesized_context", "")

    # In a real application, you would now pass this context to your LLM
    print("Context retrieved for AI agent:")
    print(f"  - {len(context_result['results'])} relevant memories")
    print(f"  - {context_result['graph_statistics']['graph_nodes']} related entities")
    print(f"  - {context_result['graph_statistics']['graph_edges']} relationships")

    print("\nSynthesized context would be used in prompt:")
    print("---")
    print(synthesized_context[:300] + "...")
    print("---")

    # LLM would generate response using this context
    # response = llm.generate(prompt=f"Context:\n{synthesized_context}\n\nQuestion: {user_question}")

    print()


# Example 9: Dependency Analysis
async def example_dependency_analysis():
    """
    Example 9: Analyze code/system dependencies using the knowledge graph.

    Useful for understanding architecture and impact analysis.
    """
    print("=== Example 9: Dependency Analysis ===\n")

    target_entity = "PaymentProcessor"

    print(f"Analyzing dependencies of: {target_entity}\n")

    result = await rae_request(
        "POST",
        "/v1/graph/query",
        json={
            "query": f"{target_entity} dependencies and dependents",
            "project_id": PROJECT_ID,
            "top_k_vector": 3,
            "graph_depth": 3,
            "traversal_strategy": "bfs",
        },
    )

    # Analyze relationships
    dependencies = []
    dependents = []

    for edge in result["graph_edges"]:
        if edge["relation"] == "DEPENDS_ON":
            dependencies.append(edge)
        elif "DEPENDS" in edge["relation"]:  # Catch variations
            dependents.append(edge)

    print(f"Direct dependencies: {len(dependencies)}")
    print(f"Dependent systems: {len(dependents)}")

    print("\nDependency tree:")
    for node in result["graph_nodes"][:5]:
        indent = "  " * node["depth"]
        print(f"{indent}- {node['label']} (depth {node['depth']})")

    print()


# Example 10: Custom Confidence Filtering
async def example_confidence_filtering():
    """
    Example 10: Use confidence scores to filter extraction results.

    Demonstrates how to balance precision vs. recall based on use case.
    """
    print("=== Example 10: Confidence Filtering ===\n")

    # Extract with different confidence thresholds
    thresholds = [0.3, 0.5, 0.7, 0.9]

    print("Comparing extraction with different confidence thresholds:\n")

    for threshold in thresholds:
        result = await rae_request(
            "POST",
            "/v1/graph/extract",
            json={
                "project_id": PROJECT_ID,
                "limit": 50,
                "min_confidence": threshold,
                "auto_store": False,  # Don't store, just analyze
            },
        )

        triple_count = len(result["triples"])
        entity_count = len(result["extracted_entities"])

        print(
            f"Threshold {threshold:.1f}: {triple_count} triples, {entity_count} entities"
        )

    print("\nGuidelines:")
    print("  - High precision (0.7-1.0): Critical systems")
    print("  - Balanced (0.5-0.7): General use")
    print("  - High recall (0.3-0.5): Exploration")

    print()


# Main execution
async def main():
    """Run all examples."""
    print("=" * 60)
    print("RAE GraphRAG Examples")
    print("=" * 60)
    print()

    try:
        await example_basic_extraction()
        await asyncio.sleep(1)

        await example_hybrid_search()
        await asyncio.sleep(1)

        await example_advanced_graph_query()
        await asyncio.sleep(1)

        await example_graph_statistics()
        await asyncio.sleep(1)

        await example_subgraph_exploration()
        await asyncio.sleep(1)

        await example_hierarchical_reflection()
        await asyncio.sleep(1)

        await example_incremental_updates()
        await asyncio.sleep(1)

        await example_ai_agent_integration()
        await asyncio.sleep(1)

        await example_dependency_analysis()
        await asyncio.sleep(1)

        await example_confidence_filtering()

        print("=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\nError: {e}")
        print("\nMake sure:")
        print("  1. RAE API is running at http://localhost:8000")
        print("  2. Database migrations are applied (make db-migrate)")
        print("  3. LLM provider is configured (OpenAI, Anthropic, or Gemini)")


if __name__ == "__main__":
    asyncio.run(main())
