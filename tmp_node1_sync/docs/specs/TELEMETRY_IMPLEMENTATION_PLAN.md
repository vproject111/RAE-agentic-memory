# 📡 RAE Telemetry & Synchronization Implementation Plan

> **Status**: Draft
> **Version**: 1.0.0
> **Based on**: `telemetria-prometheus.md` & `RAE_Architecture_Refactoring_Plan_v2.md`

## 1. Vision & Philosophy

RAE is not just an application; it is a **Reflective Cognitive System**. Telemetry in RAE serves two distinct purposes:
1.  **Operational (Ops):** Is the system running? Is it fast? (For Admins/Users)
2.  **Cognitive (Internal):** Why did I make this decision? Where did this memory come from? Do I trust it? (For the Agent/Self-Optimization)

Furthermore, the **RAE Ecosystem** (Server, Lite, Mobile) relies on a mesh of synchronized memories. Telemetry must track the **provenance** and **flow** of information across this distributed network to ensure trust and consistency.

---

## 2. The 3-Layer Telemetry Architecture

We strictly separate concerns to avoid overengineering while enabling deep research capabilities.

### ✅ Layer 1: Operational Metrics (Default / Always On)
*   **Audience:** End-users, Admins, RAE-Lite users.
*   **Technology:** Pure Python counters exposed via lightweight `/metrics` endpoint (Prometheus format) or internal status API.
*   **No external dependencies:** No OTel Collector, no Jaeger required by default.
*   **Key Metrics:**
    *   `rae_uptime_seconds`
    *   `rae_memory_count_total`
    *   `rae_sync_last_success_timestamp`
    *   `rae_api_requests_total`
    *   `rae_errors_total`

### 🧠 Layer 2: Cognitive & Sync Telemetry (Internal / Persistent)
*   **Audience:** The RAE Agent itself (Reflection Engine), Sync Protocol.
*   **Technology:** Structured Logs (JSON) stored in `rae-core` storage (SQLite/Postgres). Part of the Memory Model.
*   **Role:** Inputs for the Reflection Engine and Trust System.
*   **Key Context:**
    *   **Provenance:** Source of memory (User, Company, RAE-Lite, RAE-Mobile).
    *   **Trust Score:** Calculated reliability of the source.
    *   **Sync State:** `sync_version`, `peer_id`, `conflict_resolution`.
    *   **Decision Trail:** "I chose action X because memory Y (from Mobile) had higher relevance."

### 🔬 Layer 3: Research & Cluster Tracing (Optional / Opt-in)
*   **Audience:** Researchers, Core Developers, Enterprise Clusters.
*   **Technology:** OpenTelemetry (OTel), Jaeger, Tempo.
*   **Activation:** Enabled via `RAE_TELEMETRY_MODE=external` or `RAE_PROFILE=research`.
*   **Capabilities:**
    *   Distributed Tracing across Node1 (GPU), Server, and Lite.
    *   Deep profiling of LLM latency (Time to First Token).
    *   Visualizing the full request lifecycle across the mesh.

---

## 3. RAE-Sync Integration Strategy

The "Vision of Development" mandates memory sharing (User↔Company, Lite↔Mobile). Telemetry must support the **RAE-Sync Protocol**.

### 3.1. Container & Node Identity
To support mesh networking and synchronization, every RAE instance must be uniquely identifiable but discoverable.

*   **Dynamic Naming:**
    *   `rae-server-{tenant}`
    *   `rae-lite-{user}`
    *   `rae-mobile-{device}`
*   **Network Tags:** Docker/Mesh tags to identify roles (e.g., `role=compute`, `role=storage`, `role=client`).

### 3.2. Sync Telemetry Attributes
Every memory item and sync packet carries telemetry metadata:

| Attribute | Description | Example |
| :--- | :--- | :--- |
| `rae.sync.origin` | Original creator of the memory | `device:mobile-pixel-7` |
| `rae.sync.path` | Path taken to reach current node | `mobile -> lite -> server` |
| `rae.trust.level` | Verification level of the source | `verified_company`, `untrusted_public` |
| `rae.sync.version` | Monotonic counter for CRDT merging | `1042` |

### 3.3. The "Handshake" Metrics
Telemetry tracks the health of the synchronization mesh:
*   `rae_sync_peers_connected`: Number of active sync partners.
*   `rae_sync_conflicts_resolved`: Count of merge conflicts handled automatically vs. manually.
*   `rae_sync_latency_ms`: Time for a memory to propagate from Edge to Core.

---

## 4. Implementation Roadmap

### Phase 1: Slim Down & Layer 1 (Now)
*   [ ] Refactor `docker-compose.yml` to remove OTel/Jaeger by default.
*   [ ] Implement lightweight `/metrics` endpoint in `rae-api` (using `prometheus-client` without sidecars).
*   [ ] Ensure `RAE-Lite` can run with ZERO telemetry containers.

### Phase 2: Layer 2 & Cognitive Context (Next)
*   [ ] Update `MemoryItem` model in `rae-core` to include `provenance` and `sync_metadata`.
*   [ ] Update `ReflectionEngine` to read these metadata fields for "Source Awareness".
*   [ ] Implement `SyncLog` in the database to track synchronization events.

### Phase 3: RAE-Sync Protocol (Future)
*   [ ] Implement `ISyncProvider` interfaces in `rae-core`.
*   [ ] Build the "Handshake" logic using Layer 2 telemetry data.
*   [ ] Create dashboard visualization for "Memory Flow" (User -> Company).

### Phase 4: Layer 3 (Research Mode)
*   [ ] Re-introduce OTel as an *optional* overlay controlled by env vars.
*   [ ] Configure trace propagation headers for distributed nodes (e.g., Node1 KUBUS).

---

## 5. Architectural Decision Record (ADR) Summary

*   **Decision:** Telemetry is split into Operational (light) and Cognitive (deep).
*   **Constraint:** RAE-Lite MUST NOT require Docker or sidecars.
*   **Standard:** All sync operations MUST carry provenance metadata.
*   **Observation:** Telemetry is data. It feeds the AI, it doesn't just monitor it.
