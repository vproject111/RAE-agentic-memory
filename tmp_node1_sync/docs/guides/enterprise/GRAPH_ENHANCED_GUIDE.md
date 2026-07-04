# Graph Enhanced Operations Guide

**Enterprise Feature** | **Version**: 2.2.0-enterprise

## Overview

Graph Enhanced Operations provide advanced knowledge graph capabilities beyond basic GraphRAG. Build sophisticated graph structures with temporal edges, weighted relationships, cycle detection, and graph versioning.

**Key Features**:
- 🕒 **Temporal Graphs**: Time-bound edges with validity windows
- ⚖️ **Weighted Edges**: Confidence scores and relationship strengths
- 🔍 **Advanced Algorithms**: BFS, DFS, Dijkstra shortest path, cycle detection
- 📸 **Graph Snapshots**: Version control for knowledge graphs
- 📊 **Node Analytics**: Centrality metrics, degree distributions
- ⚡ **Batch Operations**: Create hundreds of nodes/edges efficiently

---

## Quick Start

### 1. Create Nodes

```bash
curl -X POST http://localhost:8000/v1/graph-management/nodes \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo" \
  -H "X-API-Key: your-key" \
  -d '{
    "tenant_id": "demo",
    "project_id": "my-app",
    "node_id": "person_alice",
    "label": "Person",
    "properties": {
      "name": "Alice",
      "role": "Engineer",
      "department": "AI"
    }
  }'
```

**Response**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "tenant_id": "demo",
  "project_id": "my-app",
  "node_id": "person_alice",
  "label": "Person",
  "properties": {
    "name": "Alice",
    "role": "Engineer",
    "department": "AI"
  },
  "created_at": "2025-12-04T10:00:00Z"
}
```

### 2. Create Weighted, Temporal Edge

```bash
curl -X POST http://localhost:8000/v1/graph-management/edges \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo" \
  -H "X-API-Key": your-key" \
  -d '{
    "tenant_id": "demo",
    "project_id": "my-app",
    "source_node_id": "550e8400-e29b-41d4-a716-446655440000",
    "target_node_id": "660e8400-e29b-41d4-a716-446655440001",
    "relation": "WORKS_WITH",
    "edge_weight": 0.85,
    "confidence": 0.92,
    "bidirectional": true,
    "valid_from": "2025-01-01T00:00:00Z",
    "valid_to": "2025-12-31T23:59:59Z"
  }'
```

**Response**:
```json
{
  "id": "770e8400-e29b-41d4-a716-446655440002",
  "source_node_id": "550e8400-...",
  "target_node_id": "660e8400-...",
  "relation": "WORKS_WITH",
  "edge_weight": 0.85,
  "confidence": 0.92,
  "is_active": true,
  "valid_from": "2025-01-01T00:00:00Z",
  "valid_to": "2025-12-31T23:59:59Z"
}
```

---

## Node Operations

### Create Node

```bash
curl -X POST http://localhost:8000/v1/graph-management/nodes \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo" \
  -H "X-API-Key: your-key" \
  -d '{
    "tenant_id": "demo",
    "project_id": "my-app",
    "node_id": "concept_machine_learning",
    "label": "Concept",
    "properties": {
      "name": "Machine Learning",
      "category": "AI",
      "importance": 0.95
    }
  }'
```

### Get Node Metrics

Analyze node connectivity:

```bash
curl "http://localhost:8000/v1/graph-management/nodes/550e8400-e29b-41d4-a716-446655440000/metrics?tenant_id=demo&project_id=my-app" \
  -H "X-API-Key: your-key"
```

**Response**:
```json
{
  "node_id": "550e8400-e29b-41d4-a716-446655440000",
  "metrics": {
    "in_degree": 5,
    "out_degree": 8,
    "total_degree": 13,
    "weighted_in_degree": 4.2,
    "weighted_out_degree": 6.8,
    "betweenness_centrality": 0.34,
    "clustering_coefficient": 0.67
  },
  "message": "Node metrics retrieved successfully"
}
```

**Metric Definitions**:
- **in_degree**: Number of incoming edges
- **out_degree**: Number of outgoing edges
- **weighted_in_degree**: Sum of incoming edge weights
- **betweenness_centrality**: How often node appears on shortest paths
- **clustering_coefficient**: How connected neighbors are

### Find Connected Nodes

```bash
curl -X POST http://localhost:8000/v1/graph-management/nodes/connected \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo" \
  -H "X-API-Key: your-key" \
  -d '{
    "tenant_id": "demo",
    "project_id": "my-app",
    "node_id": "550e8400-e29b-41d4-a716-446655440000",
    "max_depth": 3
  }'
```

**Response**:
```json
{
  "node_id": "550e8400-...",
  "connected_nodes": [
    {
      "node_id": "660e8400-...",
      "distance": 1,
      "path_weight": 0.85
    },
    {
      "node_id": "770e8400-...",
      "distance": 2,
      "path_weight": 1.72
    }
  ],
  "total_connected": 2
}
```

---

## Edge Operations

### Create Edge

```bash
curl -X POST http://localhost:8000/v1/graph-management/edges \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo" \
  -H "X-API-Key: your-key" \
  -d '{
    "tenant_id": "demo",
    "project_id": "my-app",
    "source_node_id": "550e8400-e29b-41d4-a716-446655440000",
    "target_node_id": "660e8400-e29b-41d4-a716-446655440001",
    "relation": "DEPENDS_ON",
    "edge_weight": 0.75,
    "confidence": 0.88,
    "bidirectional": false,
    "properties": {
      "dependency_type": "strong",
      "criticality": "high"
    },
    "metadata": {
      "source": "api",
      "created_by": "system"
    }
  }'
```

### Update Edge Weight

```bash
curl -X PUT http://localhost:8000/v1/graph-management/edges/770e8400-e29b-41d4-a716-446655440002/weight \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{
    "new_weight": 0.90,
    "new_confidence": 0.95
  }'
```

### Deactivate Edge (Soft Delete)

```bash
curl -X POST http://localhost:8000/v1/graph-management/edges/770e8400-e29b-41d4-a716-446655440002/deactivate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{
    "reason": "Relationship no longer valid"
  }'
```

### Reactivate Edge

```bash
curl -X POST http://localhost:8000/v1/graph-management/edges/770e8400-e29b-41d4-a716-446655440002/activate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{}'
```

### Set Temporal Validity

Define when an edge is valid:

```bash
curl -X PUT http://localhost:8000/v1/graph-management/edges/770e8400-e29b-41d4-a716-446655440002/temporal \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{
    "valid_from": "2025-01-01T00:00:00Z",
    "valid_to": "2025-06-30T23:59:59Z"
  }'
```

**Use Cases**:
- Temporary relationships (internships, contracts)
- Seasonal patterns
- Time-based dependencies
- Historical analysis

---

## Graph Traversal

### BFS Traversal

Breadth-First Search explores layer by layer:

```bash
curl -X POST http://localhost:8000/v1/graph-management/traverse \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo" \
  -H "X-API-Key: your-key" \
  -d '{
    "tenant_id": "demo",
    "project_id": "my-app",
    "start_node_id": "550e8400-e29b-41d4-a716-446655440000",
    "algorithm": "BFS",
    "max_depth": 3
  }'
```

**Response**:
```json
{
  "nodes": [
    {"node_id": "550e8400-...", "label": "Person", "properties": {...}},
    {"node_id": "660e8400-...", "label": "Team", "properties": {...}}
  ],
  "edges": [
    {"source": "550e8400-...", "target": "660e8400-...", "relation": "MEMBER_OF"}
  ],
  "total_nodes": 15,
  "total_edges": 22,
  "max_depth_reached": 3,
  "execution_time_ms": 45,
  "algorithm_used": "BFS"
}
```

### DFS Traversal

Depth-First Search explores deep before wide:

```bash
curl -X POST http://localhost:8000/v1/graph-management/traverse \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo" \
  -H "X-API-Key: your-key" \
  -d '{
    "tenant_id": "demo",
    "project_id": "my-app",
    "start_node_id": "550e8400-e29b-41d4-a716-446655440000",
    "algorithm": "DFS",
    "max_depth": 5
  }'
```

### Filtered Traversal

Apply filters during traversal:

```bash
curl -X POST http://localhost:8000/v1/graph-management/traverse \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo" \
  -H "X-API-Key: your-key" \
  -d '{
    "tenant_id": "demo",
    "project_id": "my-app",
    "start_node_id": "550e8400-e29b-41d4-a716-446655440000",
    "algorithm": "BFS",
    "max_depth": 3,
    "relation_filter": ["WORKS_WITH", "REPORTS_TO"],
    "min_weight": 0.7,
    "min_confidence": 0.8
  }'
```

### Temporal Traversal

Traverse graph as it existed at a specific time:

```bash
curl -X POST http://localhost:8000/v1/graph-management/traverse \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo" \
  -H "X-API-Key: your-key" \
  -d '{
    "tenant_id": "demo",
    "project_id": "my-app",
    "start_node_id": "550e8400-e29b-41d4-a716-446655440000",
    "algorithm": "BFS",
    "max_depth": 3,
    "at_timestamp": "2025-06-01T00:00:00Z"
  }'
```

**Use Cases**:
- Historical analysis ("What did the graph look like in June?")
- Temporal debugging
- Version comparison
- Audit trails

---

## Path Finding

### Shortest Path (Dijkstra)

Find minimum weight path between two nodes:

```bash
curl -X POST http://localhost:8000/v1/graph-management/path/shortest \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo" \
  -H "X-API-Key: your-key" \
  -d '{
    "tenant_id": "demo",
    "project_id": "my-app",
    "start_node_id": "550e8400-e29b-41d4-a716-446655440000",
    "end_node_id": "880e8400-e29b-41d4-a716-446655440003",
    "algorithm": "dijkstra",
    "max_depth": 10
  }'
```

**Response**:
```json
{
  "path_found": true,
  "path": {
    "nodes": [
      "550e8400-...",
      "660e8400-...",
      "770e8400-...",
      "880e8400-..."
    ],
    "edges": [
      {"source": "550e8400-...", "target": "660e8400-...", "weight": 0.85},
      {"source": "660e8400-...", "target": "770e8400-...", "weight": 0.78},
      {"source": "770e8400-...", "target": "880e8400-...", "weight": 0.92}
    ],
    "length": 3,
    "total_weight": 2.55
  },
  "algorithm_used": "dijkstra",
  "execution_time_ms": 23
}
```

### Temporal Shortest Path

Find path valid at specific timestamp:

```bash
curl -X POST http://localhost:8000/v1/graph-management/path/shortest \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo" \
  -H "X-API-Key: your-key" \
  -d '{
    "tenant_id": "demo",
    "project_id": "my-app",
    "start_node_id": "550e8400-e29b-41d4-a716-446655440000",
    "end_node_id": "880e8400-e29b-41d4-a716-446655440003",
    "algorithm": "dijkstra",
    "at_timestamp": "2025-03-15T12:00:00Z"
  }'
```

---

## Cycle Detection

Prevent circular dependencies:

```bash
curl -X POST http://localhost:8000/v1/graph-management/cycles/detect \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo" \
  -H "X-API-Key: your-key" \
  -d '{
    "tenant_id": "demo",
    "project_id": "my-app",
    "source_node_id": "550e8400-e29b-41d4-a716-446655440000",
    "target_node_id": "660e8400-e29b-41d4-a716-446655440001",
    "max_depth": 10
  }'
```

**Response (No Cycle)**:
```json
{
  "has_cycle": false,
  "message": "Cycle not detected"
}
```

**Response (Cycle Detected)**:
```json
{
  "has_cycle": true,
  "cycle_length": 4,
  "cycle_path": [
    "550e8400-...",
    "660e8400-...",
    "770e8400-...",
    "880e8400-...",
    "550e8400-..."
  ],
  "message": "Cycle detected (length: 4)"
}
```

**Use Cases**:
- Dependency validation
- Workflow verification
- Data lineage analysis
- Prevent infinite loops

---

## Graph Snapshots

Version control for knowledge graphs.

### Create Snapshot

```bash
curl -X POST http://localhost:8000/v1/graph-management/snapshots \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo" \
  -H "X-API-Key: your-key" \
  -d '{
    "tenant_id": "demo",
    "project_id": "my-app",
    "snapshot_name": "before-migration",
    "description": "Graph state before Q1 2025 migration",
    "include_inactive_edges": false,
    "tags": ["migration", "backup", "q1-2025"]
  }'
```

**Response**:
```json
{
  "snapshot_id": "990e8400-e29b-41d4-a716-446655440004",
  "snapshot_name": "before-migration",
  "node_count": 1547,
  "edge_count": 3892,
  "created_at": "2025-12-04T10:00:00Z",
  "size_bytes": 2457600,
  "message": "Snapshot created successfully"
}
```

### List Snapshots

```bash
curl "http://localhost:8000/v1/graph-management/snapshots?tenant_id=demo&project_id=my-app" \
  -H "X-API-Key: your-key"
```

### Get Snapshot Details

```bash
curl http://localhost:8000/v1/graph-management/snapshots/990e8400-e29b-41d4-a716-446655440004 \
  -H "X-API-Key: your-key"
```

**Response**:
```json
{
  "id": "990e8400-...",
  "tenant_id": "demo",
  "project_id": "my-app",
  "snapshot_name": "before-migration",
  "description": "Graph state before Q1 2025 migration",
  "node_count": 1547,
  "edge_count": 3892,
  "created_at": "2025-12-04T10:00:00Z",
  "tags": ["migration", "backup", "q1-2025"],
  "metadata": {
    "created_by": "admin",
    "system_version": "2.2.0-enterprise"
  }
}
```

### Restore Snapshot

```bash
curl -X POST http://localhost:8000/v1/graph-management/snapshots/990e8400-e29b-41d4-a716-446655440004/restore \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo" \
  -H "X-API-Key: your-key" \
  -d '{
    "restore_mode": "replace",
    "create_backup": true
  }'
```

**Restore Modes**:
- `replace`: Delete current graph, restore snapshot
- `merge`: Keep current graph, add snapshot data
- `preview`: Dry-run, show what would change

**Response**:
```json
{
  "snapshot_id": "990e8400-...",
  "restore_status": "completed",
  "nodes_restored": 1547,
  "edges_restored": 3892,
  "backup_snapshot_id": "aa0e8400-...",
  "execution_time_ms": 3450,
  "message": "Snapshot restored successfully"
}
```

---

## Graph Statistics

### Get Statistics

```bash
curl -X POST http://localhost:8000/v1/graph-management/statistics \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo" \
  -H "X-API-Key: your-key" \
  -d '{
    "tenant_id": "demo",
    "project_id": "my-app",
    "include_centrality": true,
    "include_distributions": true
  }'
```

**Response**:
```json
{
  "node_count": 1547,
  "edge_count": 3892,
  "active_edge_count": 3654,
  "inactive_edge_count": 238,
  "avg_degree": 5.03,
  "graph_density": 0.00326,
  "connected_components": 3,
  "avg_clustering_coefficient": 0.45,
  "diameter": 12,
  "node_labels": {
    "Person": 845,
    "Concept": 512,
    "Document": 190
  },
  "relation_types": {
    "WORKS_WITH": 1205,
    "DEPENDS_ON": 987,
    "RELATES_TO": 1462
  },
  "weight_distribution": {
    "min": 0.12,
    "max": 0.98,
    "mean": 0.74,
    "median": 0.78,
    "std_dev": 0.15
  },
  "top_central_nodes": [
    {
      "node_id": "550e8400-...",
      "betweenness": 0.87,
      "degree": 45
    }
  ]
}
```

---

## Batch Operations

Create multiple nodes/edges efficiently.

### Batch Create Nodes

```bash
curl -X POST http://localhost:8000/v1/graph-management/nodes/batch \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo" \
  -H "X-API-Key: your-key" \
  -d '{
    "tenant_id": "demo",
    "project_id": "my-app",
    "nodes": [
      {
        "node_id": "person_bob",
        "label": "Person",
        "properties": {"name": "Bob", "role": "Manager"}
      },
      {
        "node_id": "person_carol",
        "label": "Person",
        "properties": {"name": "Carol", "role": "Designer"}
      },
      {
        "node_id": "team_alpha",
        "label": "Team",
        "properties": {"name": "Alpha Team", "size": 8}
      }
    ]
  }'
```

**Response**:
```json
{
  "created_count": 3,
  "failed_count": 0,
  "created_ids": [
    "bb0e8400-...",
    "cc0e8400-...",
    "dd0e8400-..."
  ],
  "errors": []
}
```

### Batch Create Edges

```bash
curl -X POST http://localhost:8000/v1/graph-management/edges/batch \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo" \
  -H "X-API-Key: your-key" \
  -d '{
    "tenant_id": "demo",
    "project_id": "my-app",
    "edges": [
      {
        "source_node_id": "bb0e8400-...",
        "target_node_id": "dd0e8400-...",
        "relation": "MEMBER_OF",
        "edge_weight": 1.0
      },
      {
        "source_node_id": "cc0e8400-...",
        "target_node_id": "dd0e8400-...",
        "relation": "MEMBER_OF",
        "edge_weight": 1.0
      }
    ]
  }'
```

**Performance**: Batch operations are 10-50x faster than individual calls.

---

## Real-World Examples

### Example 1: Dependency Graph for Microservices

```bash
# Create service nodes
curl -X POST http://localhost:8000/v1/graph-management/nodes/batch \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo" \
  -H "X-API-Key: your-key" \
  -d '{
    "tenant_id": "demo",
    "project_id": "prod",
    "nodes": [
      {"node_id": "api-gateway", "label": "Service", "properties": {"name": "API Gateway"}},
      {"node_id": "auth-service", "label": "Service", "properties": {"name": "Auth Service"}},
      {"node_id": "user-service", "label": "Service", "properties": {"name": "User Service"}},
      {"node_id": "order-service", "label": "Service", "properties": {"name": "Order Service"}}
    ]
  }'

# Create dependencies
curl -X POST http://localhost:8000/v1/graph-management/edges/batch \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo" \
  -H "X-API-Key: your-key" \
  -d '{
    "tenant_id": "demo",
    "project_id": "prod",
    "edges": [
      {
        "source_node_id": "{api-gateway-uuid}",
        "target_node_id": "{auth-service-uuid}",
        "relation": "DEPENDS_ON",
        "edge_weight": 1.0,
        "properties": {"criticality": "high"}
      },
      {
        "source_node_id": "{auth-service-uuid}",
        "target_node_id": "{user-service-uuid}",
        "relation": "DEPENDS_ON",
        "edge_weight": 0.8
      }
    ]
  }'

# Detect circular dependencies
curl -X POST http://localhost:8000/v1/graph-management/cycles/detect \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo" \
  -H "X-API-Key: your-key" \
  -d '{
    "tenant_id": "demo",
    "project_id": "prod",
    "source_node_id": "{order-service-uuid}",
    "target_node_id": "{auth-service-uuid}"
  }'
```

### Example 2: Temporal Organization Chart

```bash
# Create employee node
curl -X POST http://localhost:8000/v1/graph-management/nodes \
  -d '{
    "tenant_id": "demo",
    "project_id": "hr",
    "node_id": "emp_001",
    "label": "Employee",
    "properties": {"name": "Alice", "title": "Senior Engineer"}
  }'

# Create reporting relationship valid for 6 months
curl -X POST http://localhost:8000/v1/graph-management/edges \
  -d '{
    "tenant_id": "demo",
    "project_id": "hr",
    "source_node_id": "{alice-uuid}",
    "target_node_id": "{manager-uuid}",
    "relation": "REPORTS_TO",
    "valid_from": "2025-01-01T00:00:00Z",
    "valid_to": "2025-06-30T23:59:59Z"
  }'

# Query org chart as it was in March
curl -X POST http://localhost:8000/v1/graph-management/traverse \
  -d '{
    "tenant_id": "demo",
    "project_id": "hr",
    "start_node_id": "{ceo-uuid}",
    "algorithm": "BFS",
    "at_timestamp": "2025-03-15T00:00:00Z",
    "relation_filter": ["REPORTS_TO"]
  }'
```

### Example 3: Knowledge Graph Versioning

```bash
# Before major update, create snapshot
curl -X POST http://localhost:8000/v1/graph-management/snapshots \
  -d '{
    "tenant_id": "demo",
    "project_id": "knowledge",
    "snapshot_name": "pre-update-v2.1",
    "description": "Before upgrading to v2.1",
    "tags": ["backup", "v2.0"]
  }'

# Perform updates...
# (add/remove nodes and edges)

# If something breaks, restore
curl -X POST http://localhost:8000/v1/graph-management/snapshots/{snapshot-id}/restore \
  -d '{
    "restore_mode": "replace",
    "create_backup": true
  }'
```

---

## Best Practices

### 1. Use Meaningful Node IDs
❌ **Bad**: `"node_id": "node_12345"`

✅ **Good**: `"node_id": "person_alice_smith"`

### 2. Set Edge Weights Consistently
Use 0.0-1.0 range for all edges:
- 0.9-1.0: Strong relationship
- 0.7-0.9: Medium relationship
- 0.5-0.7: Weak relationship
- <0.5: Very weak

### 3. Use Batch Operations
For >10 nodes/edges, always use batch endpoints.

### 4. Create Snapshots Regularly
Before major changes:
```bash
# Weekly snapshot
curl -X POST .../snapshots -d '{"snapshot_name": "weekly-2025-W49"}'
```

### 5. Monitor Graph Statistics
Track growth and complexity:
```bash
# Daily stats check
curl -X POST .../statistics
```

### 6. Use Temporal Edges Wisely
Only add `valid_from`/`valid_to` when needed (adds complexity).

### 7. Detect Cycles Before Creating Edges
```bash
# Check first
curl -X POST .../cycles/detect -d '{...}'
# Then create edge if no cycle
curl -X POST .../edges -d '{...}'
```

---

## Performance Tips

### Traversal Performance
- **BFS**: Faster for shallow traversals (depth ≤ 3)
- **DFS**: Better for deep, narrow paths

### Large Graphs (>10K nodes)
- Use `max_depth` to limit traversal
- Apply filters to reduce result set
- Consider pagination for results

### Batch Operations
- Optimal batch size: 50-200 items
- For >1000 items, split into multiple batches

---

## Troubleshooting

### Cycle Detected Unexpectedly

**Check bidirectional edges**:
```bash
curl -X POST .../edges \
  -d '{
    "bidirectional": false,  # Try with false first
    ...
  }'
```

### Path Not Found

**Increase max_depth**:
```bash
curl -X POST .../path/shortest \
  -d '{
    "max_depth": 20,  # Default is 10
    ...
  }'
```

**Check temporal validity**:
```bash
# Ensure edges are valid at timestamp
curl -X POST .../traverse \
  -d '{
    "at_timestamp": null,  # Use null for current time
    ...
  }'
```

### Slow Traversal

**Apply filters**:
```bash
curl -X POST .../traverse \
  -d '{
    "relation_filter": ["IMPORTANT_RELATION"],
    "min_weight": 0.7,
    "min_confidence": 0.8
  }'
```

---

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/graph-management/nodes` | POST | Create node |
| `/v1/graph-management/nodes/{node_id}/metrics` | GET | Get node metrics |
| `/v1/graph-management/nodes/connected` | POST | Find connected nodes |
| `/v1/graph-management/edges` | POST | Create edge |
| `/v1/graph-management/edges/{edge_id}/weight` | PUT | Update weight |
| `/v1/graph-management/edges/{edge_id}/deactivate` | POST | Deactivate edge |
| `/v1/graph-management/edges/{edge_id}/activate` | POST | Activate edge |
| `/v1/graph-management/edges/{edge_id}/temporal` | PUT | Set temporal validity |
| `/v1/graph-management/traverse` | POST | Traverse graph |
| `/v1/graph-management/path/shortest` | POST | Find shortest path |
| `/v1/graph-management/cycles/detect` | POST | Detect cycle |
| `/v1/graph-management/snapshots` | POST | Create snapshot |
| `/v1/graph-management/snapshots/{snapshot_id}` | GET | Get snapshot |
| `/v1/graph-management/snapshots` | GET | List snapshots |
| `/v1/graph-management/snapshots/{snapshot_id}/restore` | POST | Restore snapshot |
| `/v1/graph-management/statistics` | POST | Get statistics |
| `/v1/graph-management/nodes/batch` | POST | Batch create nodes |
| `/v1/graph-management/edges/batch` | POST | Batch create edges |
| `/v1/graph-management/health` | GET | Health check |

**Full API documentation**: [API_INDEX.md](../../reference/api/API_INDEX.md#graph-enhanced-operations-19)

---

## Further Reading

- [Knowledge Graph Guide](../core/KNOWLEDGE_GRAPH_GUIDE.md) - Basic graph operations
- [GraphRAG Guide](../core/GRAPHRAG_GUIDE.md) - Graph + RAG patterns
- [API Cookbook](../../reference/api/API_COOKBOOK.md) - More graph recipes

---

**Last Updated**: 2025-12-04
**API Version**: 2.2.0-enterprise
