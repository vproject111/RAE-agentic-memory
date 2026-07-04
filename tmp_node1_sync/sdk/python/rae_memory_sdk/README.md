# RAE Memory Python SDK

Enterprise-grade Python client for **RAE (Reflective Agentic Memory Engine)** v2.0.

The RAE Python SDK provides a comprehensive interface to all RAE Memory API features including:
- Core memory operations (store, query, delete)
- GraphRAG knowledge graph extraction and querying
- Agent execution with full memory orchestration
- Governance and cost tracking
- Context cache management
- Reflection generation

## Installation

### From Source

```bash
git clone https://github.com/dreamsoft-pro/RAE-agentic-memory.git
cd RAE-agentic-memory/sdk/python
pip install -e rae_memory_sdk
```

### From PyPI (when published)

```bash
pip install rae-memory-sdk
```

## Quick Start

```python
from rae_memory_sdk import RAEClient
from rae_memory_sdk.models import StoreMemoryRequest

# Initialize client
client = RAEClient(
    api_url="http://localhost:8000",
    api_key="your-api-key",
    tenant_id="your-tenant-id"
)

# Store a memory
memory = StoreMemoryRequest(
    content="User prefers dark mode in the application",
    source="user_preference",
    importance=0.8,
    layer="em",  # Episodic memory
    tags=["preference", "ui"],
    project="my-project"
)

response = client.store(memory)
print(f"Stored memory: {response.id}")

# Query memories
results = client.query(
    query_text="user interface preferences",
    k=10
)

for item in results.results:
    print(f"[{item.score:.2f}] {item.content}")
```

## Configuration

The SDK can be configured via constructor parameters or environment variables:

```python
# Option 1: Direct parameters
client = RAEClient(
    api_url="http://localhost:8000",
    api_key="your-api-key",
    tenant_id="your-tenant-id"
)

# Option 2: Environment variables
# RAE_API_URL=http://localhost:8000
# RAE_API_KEY=your-api-key
# RAE_TENANT_ID=your-tenant-id
client = RAEClient()
```

## Core Memory Operations

### Store Memory

```python
from rae_memory_sdk.models import StoreMemoryRequest

memory = StoreMemoryRequest(
    content="Important business logic rule",
    source="code_analysis",
    importance=0.9,
    layer="sm",  # Semantic memory (facts/knowledge)
    tags=["business-logic", "rules"],
    project="project-1"
)

response = client.store(memory)
print(f"Memory ID: {response.id}")
```

**Memory Layers:**
- `em` - Episodic Memory (events, interactions)
- `sm` - Semantic Memory (facts, knowledge)
- `rm` - Reflective Memory (insights, patterns)

### Query Memories

**Standard Vector Search:**

```python
response = client.query(
    query_text="authentication errors",
    k=10
)

for memory in response.results:
    print(f"[{memory.score:.2f}] {memory.content}")
    print(f"  Last accessed: {memory.last_accessed_at}")
    print(f"  Usage count: {memory.usage_count}")
```

**Hybrid Search with GraphRAG:**

```python
# Enable graph traversal for richer context
response = client.query(
    query_text="machine learning concepts",
    k=5,
    use_graph=True,
    graph_depth=2,
    project="ml-project"
)

# Access synthesized context from graph
if response.synthesized_context:
    print(f"Graph context: {response.synthesized_context}")

# View graph statistics
if response.graph_statistics:
    print(f"Nodes traversed: {response.graph_statistics['nodes_traversed']}")
```

### Delete Memory

```python
response = client.delete(memory_id="550e8400-e29b-41d4-a716-446655440000")
print(response.message)
```

## GraphRAG Operations

### Extract Knowledge Graph

```python
# Extract entities and relationships from memories
result = client.extract_knowledge_graph(
    project_id="project-1",
    limit=50,
    min_confidence=0.5,
    auto_store=True
)

print(f"Extracted {len(result['triples'])} triples")
print(f"Found {len(result['entities'])} unique entities")

for triple in result['triples']:
    print(f"{triple['subject']} --[{triple['predicate']}]--> {triple['object']}")
    print(f"  Confidence: {triple['confidence']}")
```

### Advanced Graph Query

```python
# Hybrid search combining vector + graph traversal
result = client.query_graph(
    query="machine learning optimization techniques",
    project_id="ml-project",
    top_k_vector=5,
    graph_depth=2,
    traversal_strategy="bfs"  # or "dfs"
)

print(f"Vector matches: {len(result['vector_matches'])}")
print(f"Graph nodes: {len(result['graph_nodes'])}")
print(f"Graph edges: {len(result['graph_edges'])}")
print(f"\nSynthesized context:\n{result['synthesized_context']}")
```

### Graph Statistics

```python
stats = client.get_graph_stats(project_id="project-1")

print(f"Total nodes: {stats['total_nodes']}")
print(f"Total edges: {stats['total_edges']}")
print(f"Unique relations: {stats['unique_relations']}")
print(f"Average edges per node: {stats['statistics']['avg_edges_per_node']}")
```

### Get Graph Nodes and Edges

```python
# Get important nodes using PageRank
nodes = client.get_graph_nodes(
    project_id="project-1",
    limit=20,
    use_pagerank=True,
    min_pagerank_score=0.01
)

for node in nodes:
    print(f"{node['label']} (PageRank: {node['properties']['pagerank_score']})")

# Get edges filtered by relation type
edges = client.get_graph_edges(
    project_id="project-1",
    limit=50,
    relation="depends_on"
)
```

### Get Subgraph

```python
# Extract subgraph starting from specific nodes
subgraph = client.get_subgraph(
    project_id="project-1",
    node_ids=["node-id-1", "node-id-2"],
    depth=2
)

print(f"Subgraph nodes: {len(subgraph['nodes'])}")
print(f"Subgraph edges: {len(subgraph['edges'])}")
```

## Agent Execution

Execute AI agent tasks with full memory retrieval and context management:

```python
# Execute agent with automatic memory retrieval
result = client.execute_agent(
    tenant_id="tenant-1",
    project="project-1",
    prompt="What are the user's preferences for the dashboard layout?"
)

print(f"Answer: {result['answer']}")

# View retrieved memories
for memory in result['used_memories']['results']:
    print(f"[{memory['score']:.2f}] {memory['content']}")

# View cost breakdown
cost = result['cost']
print(f"Input tokens: {cost['input_tokens']}")
print(f"Output tokens: {cost['output_tokens']}")
print(f"Total cost: ${cost['total_estimate']:.4f}")
```

## Reflection Management

### Rebuild Reflections

```python
# Trigger background task to rebuild reflective memories
response = client.rebuild_reflections(
    tenant_id="tenant-1",
    project="project-1"
)
print(response['message'])
```

### Get Reflection Statistics

```python
stats = client.get_reflection_stats(project="project-1")
print(f"Reflective memories: {stats['reflective_memory_count']}")
print(f"Average strength: {stats['average_strength']:.2f}")
```

### Generate Hierarchical Reflection

```python
# Map-reduce summarization of large episode collections
reflection = client.generate_hierarchical_reflection(
    project="project-1",
    bucket_size=10,
    max_episodes=100
)

print(f"Summary: {reflection['summary']}")
print(f"Episodes processed: {reflection['statistics']['episode_count']}")
```

## Governance & Cost Tracking

### System Overview (Admin)

```python
overview = client.get_governance_overview(days=30)

print(f"Total cost: ${overview['total_cost_usd']:.2f}")
print(f"Total calls: {overview['total_calls']}")
print(f"Unique tenants: {overview['unique_tenants']}")

# Top tenants by cost
for tenant in overview['top_tenants']:
    print(f"  {tenant['tenant_id']}: ${tenant['cost_usd']:.2f}")
```

### Tenant Governance

```python
stats = client.get_tenant_governance(
    tenant_id="tenant-1",
    days=30
)

print(f"Total cost: ${stats['total_cost_usd']:.2f}")
print(f"Cache hit rate: {stats['cache_hit_rate'] * 100:.1f}%")
print(f"Cache savings: ${stats['cache_savings_usd']:.2f}")

# Cost breakdown by project
for project in stats['by_project']:
    print(f"  {project['project_id']}: ${project['cost_usd']:.2f}")
```

### Budget Status

```python
budget = client.get_tenant_budget(tenant_id="tenant-1")

print(f"Budget: ${budget['budget_usd_monthly']:.2f}")
print(f"Used: ${budget['current_month_cost_usd']:.2f}")
print(f"Budget used: {budget['budget_used_percent']:.1f}%")
print(f"Status: {budget['status']}")

if budget['alerts']:
    for alert in budget['alerts']:
        print(f"  ⚠️  {alert}")
```

## ISO/IEC 42001 Compliance

The SDK provides comprehensive support for ISO/IEC 42001 AI management system compliance features:

### Human Approval Workflows

Request and track approval for high-risk operations:

```python
# Request approval for a critical operation
approval = client.request_approval(
    tenant_id="tenant-1",
    project_id="project-1",
    operation_type="delete",
    operation_description="Delete user data from all memory layers",
    risk_level="high",
    resource_type="user_data",
    resource_id="user-12345",
    requested_by="admin@example.com"
)

print(f"Approval request ID: {approval['request_id']}")
print(f"Status: {approval['status']}")
print(f"Required approvals: {approval['min_approvals']}")

# Check approval status
status = client.check_approval_status(request_id=approval['request_id'])
print(f"Current status: {status['status']}")
print(f"Approvals: {status['current_approvals']}/{status['min_approvals']}")
print(f"Expires at: {status['expires_at']}")

# Process approval decision (typically done by an approver)
decision = client.process_approval_decision(
    request_id=approval['request_id'],
    approved=True,
    approver_id="manager@example.com",
    reason="Reviewed and approved for GDPR compliance"
)
```

**Risk Levels:**
- `none` - No risk, auto-approved
- `low` - Minimal risk, auto-approved
- `medium` - Requires 1 approval (24h timeout)
- `high` - Requires 1 approval (48h timeout)
- `critical` - Requires 2 approvals (72h timeout)

### Context Provenance

Track decision lineage from query to final decision:

```python
# Create decision context
context = client.create_decision_context(
    tenant_id="tenant-1",
    project_id="project-1",
    query="Should we approve this loan application?",
    sources=[
        {
            "source_id": "mem-123",
            "source_type": "memory",
            "relevance_score": 0.9,
            "trust_level": "high",
            "content": "Credit score: 750"
        },
        {
            "source_id": "mem-456",
            "source_type": "memory",
            "relevance_score": 0.8,
            "trust_level": "high",
            "content": "Employment: stable for 5 years"
        }
    ]
)

print(f"Context ID: {context['context_id']}")
print(f"Quality metrics - Trust: {context['avg_trust']}, Relevance: {context['avg_relevance']}")

# Record the decision
decision = client.record_decision(
    tenant_id="tenant-1",
    project_id="project-1",
    context_id=context['context_id'],
    decision="Approve loan with $50,000 limit",
    decision_type="loan_approval",
    confidence=0.87,
    human_approved=True,
    approver_id="loan_officer@example.com"
)

print(f"Decision ID: {decision['decision_id']}")

# Get full provenance lineage
lineage = client.get_decision_lineage(decision_id=decision['decision_id'])
print(f"Query: {lineage['query']}")
print(f"Sources used: {len(lineage['sources'])}")
print(f"Final decision: {lineage['decision']}")
print(f"Human oversight: {lineage['human_approved']}")
```

### Circuit Breakers

Monitor system health and circuit breaker states:

```python
# Get all circuit breakers
breakers = client.get_all_circuit_breakers()

for breaker in breakers:
    print(f"{breaker['name']}: {breaker['state']}")
    print(f"  Failures: {breaker['failure_count']}")
    print(f"  Success rate: {breaker['success_rate']:.1%}")

# Get specific circuit breaker
db_breaker = client.get_circuit_breaker_state(name="database")
print(f"Database circuit breaker: {db_breaker['state']}")

# Reset circuit breaker (admin only)
result = client.reset_circuit_breaker(name="database")
print(result['message'])
```

**Circuit Breaker States:**
- `closed` - Normal operation
- `open` - Failing fast, service unhealthy
- `half_open` - Testing recovery

### Policy Management

Manage governance policies with versioning:

```python
# List all policies
policies = client.list_policies(
    tenant_id="tenant-1",
    policy_type="data_retention"
)

for policy in policies['policies']:
    print(f"{policy['policy_id']} v{policy['version']} - {policy['status']}")

# Create a new policy
policy = client.create_policy(
    tenant_id="tenant-1",
    policy_id="data_retention_policy",
    policy_type="data_retention",
    rules={
        "max_retention_days": 365,
        "auto_delete": True,
        "layers": ["episodic", "working"]
    },
    created_by="compliance@example.com",
    description="Retain episodic memories for 1 year"
)

print(f"Created policy version: {policy['version_id']}")

# Activate policy
activation = client.activate_policy(
    policy_id="data_retention_policy",
    version_id=policy['version_id'],
    tenant_id="tenant-1"
)

print(f"Policy activated: {activation['status']}")

# Enforce policy
enforcement = client.enforce_policy(
    policy_id="data_retention_policy",
    tenant_id="tenant-1",
    context={
        "operation": "store_memory",
        "layer": "episodic",
        "retention_days": 400
    }
)

print(f"Enforcement result: {enforcement['compliant']}")
if enforcement['violations']:
    print("Violations:")
    for violation in enforcement['violations']:
        print(f"  - {violation}")
```

**Policy Types:**
- `data_retention` - Data retention rules
- `access_control` - Access control policies
- `approval_workflow` - Approval requirements
- `trust_scoring` - Source trust scoring
- `risk_assessment` - Risk assessment rules
- `human_oversight` - Human-in-the-loop requirements

### Async ISO/IEC 42001 Methods

All compliance methods have async equivalents:

```python
# Async approval request
approval = await client.request_approval_async(...)

# Async status check
status = await client.check_approval_status_async(request_id)

# Async decision approval
decision = await client.process_approval_decision_async(...)

# Async provenance
context = await client.create_decision_context_async(...)
decision = await client.record_decision_async(...)
lineage = await client.get_decision_lineage_async(decision_id)

# Async circuit breakers
breakers = await client.get_all_circuit_breakers_async()
state = await client.get_circuit_breaker_state_async(name)
result = await client.reset_circuit_breaker_async(name)

# Async policies
policies = await client.list_policies_async(tenant_id, policy_type)
policy = await client.create_policy_async(...)
activation = await client.activate_policy_async(...)
enforcement = await client.enforce_policy_async(...)
```

## Health & Cache

### Health Check

```python
health = client.get_health()

print(f"Status: {health['status']}")
print(f"Version: {health['version']}")

for component, info in health['components'].items():
    print(f"{component}: {info['status']} ({info['response_time_ms']:.1f}ms)")
```

### Rebuild Cache

```python
# Rebuild context cache after bulk operations
response = client.rebuild_cache()
print(response['message'])
```

## Async Usage

All methods have async equivalents with `_async` suffix:

```python
import asyncio
from rae_memory_sdk import RAEClient
from rae_memory_sdk.models import StoreMemoryRequest

async def main():
    client = RAEClient(
        api_url="http://localhost:8000",
        api_key="your-api-key",
        tenant_id="your-tenant-id"
    )

    # Store memory asynchronously
    memory = StoreMemoryRequest(
        content="Async operation completed",
        layer="em",
        project="async-project"
    )
    response = await client.store_async(memory)
    print(f"Memory ID: {response.id}")

    # Query asynchronously
    results = await client.query_async(
        query_text="async operations",
        k=5
    )

    # GraphRAG async
    graph_result = await client.extract_knowledge_graph_async(
        project_id="async-project",
        limit=10
    )

    # Agent execution async
    agent_result = await client.execute_agent_async(
        tenant_id="tenant-1",
        project="async-project",
        prompt="Analyze async operations"
    )

    # Cleanup
    await client.close()

asyncio.run(main())
```

## Error Handling

```python
import httpx
from rae_memory_sdk import RAEClient

client = RAEClient(
    api_url="http://localhost:8000",
    api_key="your-api-key",
    tenant_id="your-tenant-id"
)

try:
    response = client.query(query_text="test", k=10)
except httpx.HTTPStatusError as e:
    print(f"HTTP error: {e.response.status_code}")
    print(f"Response: {e.response.text}")
except httpx.RequestError as e:
    print(f"Request error: {e}")
```

## Complete Example

```python
from rae_memory_sdk import RAEClient
from rae_memory_sdk.models import StoreMemoryRequest

# Initialize
client = RAEClient(
    api_url="http://localhost:8000",
    api_key="your-api-key",
    tenant_id="production-tenant"
)

# 1. Store some memories
for i in range(5):
    memory = StoreMemoryRequest(
        content=f"User action {i}: performed task",
        layer="em",
        tags=["user-action"],
        project="demo"
    )
    response = client.store(memory)
    print(f"Stored: {response.id}")

# 2. Extract knowledge graph
graph = client.extract_knowledge_graph(
    project_id="demo",
    limit=10,
    auto_store=True
)
print(f"Extracted {len(graph['triples'])} knowledge triples")

# 3. Query with graph
results = client.query_graph(
    query="user actions and tasks",
    project_id="demo",
    top_k_vector=3,
    graph_depth=2
)
print(f"Found {len(results['vector_matches'])} relevant memories")

# 4. Execute agent
agent_result = client.execute_agent(
    tenant_id="production-tenant",
    project="demo",
    prompt="Summarize user actions"
)
print(f"Agent response: {agent_result['answer']}")
print(f"Cost: ${agent_result['cost']['total_estimate']:.4f}")

# 5. Check governance
budget = client.get_tenant_budget(tenant_id="production-tenant")
print(f"Budget status: {budget['status']}")
print(f"Used: {budget['budget_used_percent']:.1f}%")
```

## API Reference

For complete API documentation, see:
- [API Documentation](../../API_DOCUMENTATION.md)
- [GraphRAG Guide](../../docs/graphrag_guide.md)
- [Architecture Documentation](../../docs/architecture.md)

## Support

- **GitHub Issues:** https://github.com/dreamsoft-pro/RAE-agentic-memory/issues
- **Documentation:** Official documentation in repository
- **License:** See LICENSE file

## Version

Current version: **2.0.0** (Enterprise)
