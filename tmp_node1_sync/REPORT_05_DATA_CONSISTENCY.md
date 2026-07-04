# REPORT_05_DATA_CONSISTENCY.md

## Goal
Evaluate consistency across relational storage, vector storage, cache layers, and derived state.

## Findings

### Consistency Model
- **Primary Source of Truth**: PostgreSQL.
- **Secondary Stores**: Qdrant (Vectors) and Redis (Cache).
- **Consistency Level**: Eventual (Manual synchronization).

### Weak Points
- **Distributed Deletion (MEDIUM RISK)**: In `memory.py`, deleting a memory from Postgres is the first step. If vector store (Qdrant) deletion fails, the failure is only logged, and the request succeeds. This results in **Orphaned Embeddings** in Qdrant, leading to potential search results pointing to non-existent memories.
- **Dual Write Pattern**: No distributed transaction or compensation logic (Saga) ensures that a store operation succeeds in BOTH Postgres and Qdrant.

### Detection Mechanisms
- **Absence of Data Integrity Checks**: `ValidationService` checks the schema (structure) but does not verify data integrity between Postgres and Qdrant (e.g., "Are all memories indexed?").

## Risk Level: MEDIUM
Potential for "Ghost Memories" in search results due to orphaned entries in Qdrant if deletions fail or if storage operations are partially successful.
