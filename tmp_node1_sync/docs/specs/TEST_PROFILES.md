# RAE Test Profiles Strategy

## Overview
This document defines the testing strategy for RAE, introducing specific **Test Profiles** mapped to the runtime environment. This approach replaces the monolithic testing strategy with a tiered approach to optimize for speed, coverage, and resource availability (GPU vs. CPU).

## 1. Profile: LITE (CI / Laptop / No GPU)
*   **Target Environment:** CI Runners (GitHub Actions), Developers' laptops without dedicated GPUs, Quick feedback loops.
*   **Goal:** Execution speed (< 2 minutes).
*   **Scope:**
    *   Unit Tests.
    *   Mocked LLM interactions (no real API calls).
    *   Mocked Vector Store or In-Memory (if feasible).
    *   DB Mode: `ignore` or `validate` (schema check only).
*   **Markers:** `not slow and not gpu and not integration`
*   **Command:** `make test-lite`

## 2. Profile: INTEGRATION (Docker Compose Dev)
*   **Target Environment:** Local Development with full Docker stack (Redis, Postgres, Qdrant running).
*   **Goal:** Verification of service contracts and system stability.
*   **Scope:**
    *   API Endpoint tests.
    *   Database CRUD operations.
    *   Redis Cache interactions.
    *   Qdrant connectivity and schema verification.
    *   LLM is still mocked or "stubbed" to avoid costs/latency.
*   **Markers:** `integration`
*   **Command:** `make test-int`

## 3. Profile: FULL_GPU (Workstations / Node1)
*   **Target Environment:** Dedicated Compute Nodes (e.g., Node1 "KUBUS", Node2 "PIOTREK") with GPU acceleration.
*   **Goal:** Performance benchmarking, Quality Assurance of Reranking, Real LLM responses.
*   **Scope:**
    *   End-to-End flows.
    *   **Generative Reranking** (using local LLM).
    *   **Vector Search Quality** (Accuracy/Recall).
    *   Performance Metrics (Latency, Throughput).
*   **Markers:** `gpu or benchmark`
*   **Command:** `make test-gpu`

## Implementation Details
- **Configuration:** `pytest.ini` will define markers.
- **Orchestration:** `Makefile` will encapsulate the commands and environment variables (e.g., `RAE_PROFILE=lite`).
