# RAE-Windows (Universal Node) Implementation Plan

**Codename:** "RAE-Mesh Edge"
**Architecture:** RAE-Core Embedded (No-Docker)
**Target:** Windows Laptop / Any Offline Environment
**Vision:** RAE-Lite is not just a search tool; it is an intelligent edge node in the RAE Ecosystem (Server-Lite-Mobile). It captures "non-obvious ideas" from private communications and safely shares knowledge via the RAE-Mesh protocol.

## 1. Executive Summary
This plan transforms RAE-Windows into a **Privacy-First Intelligence Node**. It implements the **Reflective Layer** for "Idea Extraction" from sensitive sources (Chats, Emails, Personal Notes) and prepares the system for **P2P Synchronization (RAE-Mesh)** with other instances (Full Server or Mobile), all while maintaining strict ISO 27001 security boundaries.

## 2. Core Philosophy & Security Contract
*   **Privacy-First:** `RESTRICTED` data (raw emails, private logs) NEVER leaves the **Working Memory** layer. It is RAM-based/Transient and excluded from all sync processes.
*   **Idea Extraction:** The **Reflection Engine** analyzes `RESTRICTED` content in the Working layer to extract abstract insights, which are then promoted to the **Reflective/Semantic** layers as `INTERNAL` or `CONFIDENTIAL` data.
*   **Mesh Ready:** Data exchange between RAE instances requires explicit user consent and adheres to the "Zero Leak" security policy.

## 3. Architecture (The "Ecosystem" Stack)

### 3.1. Components
*   **Brain (RAE-Core):** Embedded library mode.
    *   `ReflectionEngineV2`: Actor-Evaluator-Reflector pattern for automated idea extraction.
    *   `MathController`: Multi-layer ranking (Episodic, Semantic, Reflective).
*   **Storage (Local Adapters):**
    *   `SQLiteStorage`: Metadata & Content (FTS5).
    *   `LocalQdrant`: Named vector spaces for multi-model agnosticism.
*   **Sync (RAE-Sync):** Foundation for P2P/Mesh communication (E2E Encrypted).

### 3.2. Universal Connectors (Ingestor)
The ingestor is expanded to monitor active communication channels:
*   **Email Connector:** IMAP/Office365 (read-only) for capturing context.
*   **Chat Connector:** Local logs or API-based ingestion of private LLM chats.
*   **File Parsers:** PDF, TXT, DOCX, ODT, MD, Code.

## 4. Implementation Phases

### Phase 1: Infrastructure & Security Hardening
**Goal:** Establish the "Secure Cage" for data.
*   [x] **Task:** Initialize `RAECoreService` with local SQLite/Qdrant.
*   [ ] **Task:** Implement `InfoClassGuard` (Strictly block `RESTRICTED` data from Episodic/Semantic layers).
*   [ ] **Task:** Configure `WorkingLayer` encryption (Transient storage).

### Phase 2: Universal Channel Ingestor
**Goal:** Capture the "Daily Flow" of information.
*   [ ] **Task:** Implement `ChannelWatcher` (Folder watching + Email/Chat stubs).
*   [ ] **Task:** Implement `SemanticSplitter` (Context-aware chunking for different file types).
*   [ ] **Task:** Automatic Metadata tagging (Source, Timestamp, Security Classification).

### Phase 3: The Reflective Pipeline (The "Idea Engine")
**Goal:** Automate the extraction of insights.
*   [ ] **Task:** Schedule `ReflectionCycles` on raw `Working` data.
*   [ ] **Task:** Prompt Engineering for "Idea Extraction" (Transforming logs into abstract principles).
*   [ ] **Task:** Promote extracted ideas to `Reflective` layer.

### Phase 4: Mesh Connectivity (RAE-Sync)
**Goal:** Enable collaboration between RAE-Lite and RAE-Server.
*   [ ] **Task:** Implement `SyncManager` for RAE-Lite.
*   [ ] **Task:** "Share with Team" feature (Explicitly promote specific memories to the Mesh).
*   [ ] **Task:** E2E Encryption for shared memories.

## 5. Success Metrics
1.  **Insight Generation:** System automatically identifies a trend in emails (e.g., "French team consistently asks about VAT") and creates a Reflective Memory.
2.  **Safety:** Zero `RESTRICTED` items found in persistent Semantic/Episodic storage.
3.  **Cross-Platform Sync:** RAE-Lite successfully pushes an "Idea" to RAE-Server (with consent).

## 6. Next Steps
1.  **Implement `scripts/bootstrap_lite.py`** (Done - Initial Wiring confirmed).
2.  **Build `ChannelIngestor`** with support for PDF, DOCX, ODT, and Email stubs.
3.  **Activate Reflection Cycle** on ingested data.