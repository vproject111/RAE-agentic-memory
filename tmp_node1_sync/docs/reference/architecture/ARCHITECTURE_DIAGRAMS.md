# RAE Agentic Memory - Architecture Diagrams

**Version**: 2.2.0-enterprise

This document contains visual architecture diagrams for the RAE Agentic Memory system.

---

## System Overview

```mermaid
graph TB
    Client[Client Application] --> API[FastAPI Memory API]
    API --> Auth[Authentication Layer]
    Auth --> Core[Core Services]
    Auth --> Enterprise[Enterprise Services]

    Core --> Memory[Memory Service]
    Core --> Agent[Agent Service]
    Core --> Graph[Knowledge Graph]

    Enterprise --> Triggers[Event Triggers]
    Enterprise --> Search[Hybrid Search]
    Enterprise --> Reflections[Reflections]
    Enterprise --> Compliance[ISO 42001 Compliance]

    Memory --> DB[(PostgreSQL)]
    Memory --> Vector[(Qdrant Vector Store)]
    Graph --> DB
    Search --> Vector
    Search --> DB

    Agent --> LLM[LLM Service]
    Reflections --> LLM
    Compliance --> DB

    style Core fill:#90EE90
    style Enterprise fill:#FFB6C1
    style DB fill:#87CEEB
    style Vector fill:#87CEEB
    style LLM fill:#FFD700
```

---

## Request Flow

### Memory Storage Flow

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Auth
    participant MemoryService
    participant MLService
    participant DB
    participant Vector

    Client->>API: POST /v1/memory/store
    API->>Auth: Verify API Key & Tenant
    Auth-->>API: Authenticated

    API->>MemoryService: store_memory()
    MemoryService->>MLService: generate_embedding(content)
    MLService-->>MemoryService: embedding[384]

    par Database & Vector Store
        MemoryService->>DB: INSERT INTO memories
        DB-->>MemoryService: memory_id
    and
        MemoryService->>Vector: upsert(id, embedding)
        Vector-->>MemoryService: OK
    end

    MemoryService-->>API: {memory_id, created_at}
    API-->>Client: 200 OK
```

### Hybrid Search Flow

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant HybridSearch
    participant Vector
    participant Graph
    participant LLM
    participant Cache

    Client->>API: POST /v1/search/hybrid
    API->>HybridSearch: hybrid_search(query, k=10)

    HybridSearch->>Cache: check_cache(query_hash)

    alt Cache Hit
        Cache-->>HybridSearch: cached_results
    else Cache Miss
        par Parallel Search
            HybridSearch->>Vector: vector_search(embedding)
            Vector-->>HybridSearch: vector_results
        and
            HybridSearch->>Graph: graph_traversal(query)
            Graph-->>HybridSearch: graph_results
        and
            HybridSearch->>LLM: semantic_search(query)
            LLM-->>HybridSearch: semantic_results
        end

        HybridSearch->>HybridSearch: fuse_results()
        HybridSearch->>LLM: rerank(results)
        LLM-->>HybridSearch: reranked_results

        HybridSearch->>Cache: store(query_hash, results)
    end

    HybridSearch-->>API: results
    API-->>Client: 200 OK
```

---

## Data Flow

### Memory Lifecycle

```mermaid
flowchart LR
    Input[Input Content] --> Validate{Validate}
    Validate -->|Invalid| Error[400 Error]
    Validate -->|Valid| Embed[Generate Embedding]

    Embed --> Store[Store in DB]
    Store --> Vector[Store in Vector DB]
    Vector --> Index[Add to Search Index]

    Index --> Episodic[Episodic Memory]
    Episodic --> |Time-based Decay| Semantic[Semantic Memory]
    Semantic --> |Reflection| LTM[Long-term Memory]

    LTM --> Archive[Archive/Retention]
    Archive -->|Retention Policy| Delete[Delete/GDPR]

    style Input fill:#90EE90
    style Episodic fill:#FFB6C1
    style Semantic fill:#87CEEB
    style LTM fill:#FFD700
    style Delete fill:#FF6B6B
```

### Event Trigger Flow

```mermaid
flowchart TB
    Event[System Event] --> Emit[Emit Event]
    Emit --> RulesEngine[Rules Engine]

    RulesEngine --> Match{Match<br/>Triggers?}
    Match -->|No| Log[Log & Discard]
    Match -->|Yes| Eval[Evaluate Conditions]

    Eval --> |All Pass| Queue[Queue Actions]
    Eval --> |Fail| Log

    Queue --> Priority[Sort by Priority]
    Priority --> Execute[Execute Actions]

    Execute --> Action1[Action 1]
    Execute --> Action2[Action 2]
    Execute --> Action3[Action N]

    Action1 --> Success1{Success?}
    Action2 --> Success2{Success?}
    Action3 --> Success3{Success?}

    Success1 -->|No| Retry1[Retry Logic]
    Success2 -->|No| Retry2[Retry Logic]
    Success3 -->|No| Retry3[Retry Logic]

    Success1 -->|Yes| AuditLog[Audit Log]
    Success2 -->|Yes| AuditLog
    Success3 -->|Yes| AuditLog

    Retry1 --> AuditLog
    Retry2 --> AuditLog
    Retry3 --> AuditLog

    style Event fill:#90EE90
    style RulesEngine fill:#FFB6C1
    style Queue fill:#87CEEB
    style AuditLog fill:#FFD700
```

---

## Service Architecture

### 3-Layer Architecture

```mermaid
graph TB
    subgraph "API Layer"
        Routes[FastAPI Routes]
        Auth[Authentication]
        Validation[Request Validation]
    end

    subgraph "Service Layer"
        MemoryService[Memory Service]
        GraphService[Graph Service]
        SearchService[Hybrid Search Service]
        ComplianceService[Compliance Service]
        TriggerService[Trigger Service]
    end

    subgraph "Repository Layer"
        MemoryRepo[Memory Repository]
        GraphRepo[Graph Repository]
        TriggerRepo[Trigger Repository]
        MetricsRepo[Metrics Repository]
    end

    subgraph "Data Layer"
        Postgres[(PostgreSQL)]
        Qdrant[(Qdrant)]
        Redis[(Redis Cache)]
    end

    Routes --> Auth
    Auth --> Validation
    Validation --> MemoryService
    Validation --> GraphService
    Validation --> SearchService
    Validation --> ComplianceService
    Validation --> TriggerService

    MemoryService --> MemoryRepo
    GraphService --> GraphRepo
    TriggerService --> TriggerRepo
    SearchService --> MetricsRepo

    MemoryRepo --> Postgres
    GraphRepo --> Postgres
    TriggerRepo --> Postgres
    MetricsRepo --> Postgres

    MemoryService --> Qdrant
    SearchService --> Qdrant
    SearchService --> Redis

    style "API Layer" fill:#90EE90
    style "Service Layer" fill:#FFB6C1
    style "Repository Layer" fill:#87CEEB
    style "Data Layer" fill:#FFD700
```

### Microservices

```mermaid
graph LR
    subgraph "Client"
        App[Application]
    end

    subgraph "API Gateway"
        Gateway[API Gateway<br/>Port 8000]
    end

    subgraph "Core Services"
        Memory[Memory API<br/>Port 8000]
        ML[ML Service<br/>Port 8001]
        Reranker[Reranker Service<br/>Port 8002]
    end

    subgraph "Enterprise Services"
        Dashboard[Dashboard<br/>Port 3000]
        MCP[MCP Server<br/>Port 3001]
    end

    subgraph "Data Stores"
        DB[(PostgreSQL<br/>Port 5432)]
        Vector[(Qdrant<br/>Port 6333)]
        Cache[(Redis<br/>Port 6379)]
    end

    App --> Gateway
    Gateway --> Memory
    Memory --> ML
    Memory --> Reranker
    Memory --> DB
    Memory --> Vector
    Memory --> Cache

    App --> Dashboard
    App --> MCP
    Dashboard --> Gateway
    MCP --> Gateway

    style Gateway fill:#90EE90
    style Memory fill:#FFB6C1
    style ML fill:#87CEEB
    style Dashboard fill:#FFD700
```

---

## Database Schema

### Core Tables

```mermaid
erDiagram
    memories ||--o{ memory_tags : has
    memories ||--o{ graph_nodes : generates
    memories {
        uuid id PK
        string tenant_id
        string project_id
        string content
        vector embedding
        string layer
        float importance
        timestamp created_at
    }

    graph_nodes ||--o{ graph_edges : connects
    graph_nodes {
        uuid id PK
        string tenant_id
        string project_id
        string node_id
        string label
        jsonb properties
    }

    graph_edges {
        uuid id PK
        uuid source_node_id FK
        uuid target_node_id FK
        string relation
        float edge_weight
        float confidence
        boolean is_active
    }

    reflections ||--o{ reflection_relationships : has
    reflections {
        uuid id PK
        string tenant_id
        string level
        text content
        float importance
        timestamp created_at
    }

    trigger_rules ||--o{ trigger_executions : executes
    trigger_rules {
        uuid id PK
        string tenant_id
        string rule_name
        jsonb conditions
        jsonb actions
        string status
    }
```

### Enterprise Tables

```mermaid
erDiagram
    approval_requests ||--o{ approval_decisions : has
    approval_requests {
        uuid id PK
        string tenant_id
        string operation_type
        string risk_level
        string status
        timestamp expires_at
    }

    approval_decisions {
        uuid id PK
        uuid request_id FK
        string approver_id
        string decision
        timestamp decided_at
    }

    context_records ||--o{ decision_records : produces
    context_records {
        uuid id PK
        string tenant_id
        string query
        jsonb sources
        jsonb quality_metrics
    }

    decision_records {
        uuid id PK
        uuid context_id FK
        string decision_type
        text output
        float confidence
        boolean human_approved
    }

    ab_tests ||--o{ ab_test_results : tracks
    ab_tests {
        uuid id PK
        string tenant_id
        string test_name
        jsonb variant_a
        jsonb variant_b
        string status
    }

    metrics_timeseries {
        uuid id PK
        string tenant_id
        string metric_name
        float value
        timestamp recorded_at
    }
```

---

## Deployment Architecture

### Docker Compose

```mermaid
graph TB
    subgraph "Docker Network"
        subgraph "Application Containers"
            API[memory-api<br/>FastAPI]
            ML[ml-service<br/>Python]
            Reranker[reranker-service<br/>Python]
            Dashboard[dashboard<br/>Streamlit]
        end

        subgraph "Data Containers"
            DB[(postgres<br/>PostgreSQL 15)]
            Vector[(qdrant<br/>Qdrant)]
            Cache[(redis<br/>Redis 7)]
        end

        subgraph "Monitoring"
            Prometheus[prometheus]
            Grafana[grafana]
        end
    end

    API --> DB
    API --> Vector
    API --> Cache
    API --> ML
    API --> Reranker

    Dashboard --> API

    Prometheus --> API
    Prometheus --> DB
    Prometheus --> Vector

    Grafana --> Prometheus

    style API fill:#90EE90
    style DB fill:#87CEEB
    style Vector fill:#FFB6C1
    style Prometheus fill:#FFD700
```

### Production Deployment

```mermaid
graph TB
    subgraph "Load Balancer"
        LB[NGINX/HAProxy]
    end

    subgraph "API Cluster"
        API1[Memory API 1]
        API2[Memory API 2]
        API3[Memory API 3]
    end

    subgraph "Service Cluster"
        ML1[ML Service 1]
        ML2[ML Service 2]
    end

    subgraph "Database Cluster"
        DBPrimary[(PostgreSQL<br/>Primary)]
        DBReplica1[(PostgreSQL<br/>Replica 1)]
        DBReplica2[(PostgreSQL<br/>Replica 2)]
    end

    subgraph "Vector Store Cluster"
        VectorNode1[(Qdrant Node 1)]
        VectorNode2[(Qdrant Node 2)]
        VectorNode3[(Qdrant Node 3)]
    end

    subgraph "Cache Cluster"
        Redis1[(Redis Primary)]
        Redis2[(Redis Replica)]
    end

    LB --> API1
    LB --> API2
    LB --> API3

    API1 --> ML1
    API2 --> ML1
    API3 --> ML2
    API1 --> ML2
    API2 --> ML2
    API3 --> ML1

    API1 --> DBPrimary
    API2 --> DBReplica1
    API3 --> DBReplica2

    DBPrimary --> DBReplica1
    DBPrimary --> DBReplica2

    API1 --> VectorNode1
    API2 --> VectorNode2
    API3 --> VectorNode3

    API1 --> Redis1
    API2 --> Redis1
    API3 --> Redis1
    Redis1 --> Redis2

    style LB fill:#90EE90
    style API1 fill:#FFB6C1
    style DBPrimary fill:#87CEEB
    style VectorNode1 fill:#FFD700
```

---

## Security Architecture

```mermaid
graph TB
    Client[Client] --> WAF[Web Application Firewall]
    WAF --> RateLimit[Rate Limiter]
    RateLimit --> Auth[Authentication]

    Auth --> |API Key| KeyValidation[API Key Validation]
    Auth --> |JWT| TokenValidation[JWT Token Validation]

    KeyValidation --> RBAC[Role-Based Access Control]
    TokenValidation --> RBAC

    RBAC --> TenantCheck[Tenant Isolation Check]
    TenantCheck --> Encryption[Data Encryption Layer]

    Encryption --> Service[Service Layer]
    Service --> RLS[Row Level Security]
    RLS --> Database[(Database)]

    subgraph "Security Layers"
        WAF
        RateLimit
        Auth
        RBAC
        TenantCheck
        Encryption
        RLS
    end

    style WAF fill:#FF6B6B
    style Auth fill:#FFB6C1
    style RBAC fill:#90EE90
    style Encryption fill:#87CEEB
    style RLS fill:#FFD700
```

---

## Compliance Flow (ISO/IEC 42001)

```mermaid
flowchart TB
    Start[High-Risk Operation] --> Risk{Risk<br/>Assessment}

    Risk -->|Low| AutoApprove[Auto-Approve]
    Risk -->|Medium/High| HumanReview[Human Approval]
    Risk -->|Critical| MultiApproval[Multi-Approver]

    HumanReview --> Approval1{Approved?}
    MultiApproval --> Approval2{2 Approvals?}

    Approval1 -->|Yes| Context[Create Context Record]
    Approval1 -->|No| Reject[Reject & Log]
    Approval2 -->|Yes| Context
    Approval2 -->|No| Reject
    AutoApprove --> Context

    Context --> Execute[Execute Operation]
    Execute --> Decision[Record Decision]

    Decision --> Provenance[Store Provenance]
    Provenance --> Audit[Audit Log]

    Audit --> Monitor[Continuous Monitoring]
    Monitor --> CircuitBreaker{Circuit<br/>Breaker?}

    CircuitBreaker -->|Open| Failsafe[Fail-Safe Mode]
    CircuitBreaker -->|Closed| Success[Success]

    Failsafe --> Alert[Alert Administrators]

    style Risk fill:#FF6B6B
    style HumanReview fill:#FFB6C1
    style Context fill:#90EE90
    style Provenance fill:#87CEEB
    style Monitor fill:#FFD700
```

---

## Viewing These Diagrams

### GitHub/GitLab

Mermaid diagrams render automatically in Markdown files.

### VS Code

Install extension: **Markdown Preview Mermaid Support**

### Online Editors

- **Mermaid Live Editor**: https://mermaid.live/
- **Mermaid Chart**: https://www.mermaidchart.com/

### Export as Images

```bash
# Install mermaid-cli
npm install -g @mermaid-js/mermaid-cli

# Generate PNG
mmdc -i ARCHITECTURE_DIAGRAMS.md -o diagrams/

# Generate SVG
mmdc -i ARCHITECTURE_DIAGRAMS.md -o diagrams/ -t svg
```

---

## Further Reading

- [System Architecture](SYSTEM_ARCHITECTURE.md) - Detailed architecture documentation
- [API Reference](../api/api_reference.md) - API endpoints
- [Deployment Guide](../deployment/DEPLOYMENT_GUIDE.md) - Production deployment

---

**Last Updated**: 2025-12-04
**Version**: 2.2.0-enterprise
