# RAE: Reflective Agentic Memory Core
*(read: „Ray”)*

RAE is an open-source cognitive memory system for AI agents. It addresses the fundamental problem of **Reasoning Drift**—the gradual loss of alignment between past decisions and present behavior.

[![DOI](https://zenodo.org/badge/1088095844.svg)](https://zenodo.org/badge/latestdoi/1088095844)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

> **💡 New to RAE? Start Here:** [**What is RAE? Architecture & Philosophy**](docs/CONCEPT.md)  
> *Learn why RAE is not just a Vector DB, how the "Hive Mind" works, and the "RAE-First" workflow.*

---

## 🔬 The Silicon Oracle (Current Performance)

| Suite | Scale | MRR / Score | Status | Device |
| :--- | :--- | :--- | :--- | :--- |
| **Industrial Small** | 100 mems | **1.0000** | ✅ PASS | Laptop CPU |
| **Industrial Large** | 1k mems | **1.0000** | ✅ PASS | Laptop CPU |
| **Industrial Extreme**| 10k mems | **1.0000** | ✅ PASS | Laptop CPU |
| **Industrial Ultra** | 100k mems| **1.0000** | ✅ PASS | Cluster (Lumina) |

*> RAE achieves SOTA performance on standard hardware via Native ONNX, Symbolic Anchoring and Szubar Mode.*

---

## 📊 Benchmarks (State of the Art)

| Metric | System 4.13 | System 4.16 (Silicon Oracle) |
| :--- | :--- | :--- |
| **Academic Lite (MRR)** | 1.0000 | **1.0000** |
| **Industrial Small (MRR)** | 0.8056 | **1.0000** |
| **Industrial Large (1k)** | 0.5842 | **1.0000** |
| **Industrial Scale (100k)** | N/A | **1.0000** |
| **MMIT Interference** | 0.0000 | **0.0000** |
| **LECT Consistency** | 0.9995 | **0.9995** |
| **Avg Latency (100k)** | N/A | **842ms** |

---

## What Problem Does RAE Solve?

Most systems can store information. Few can preserve **why decisions were made**.

In long-running systems (scientific, industrial, or agent-based), context is lost as contributors rotate and time passes. This leads to an inability to audit reasoning paths, an accumulation of contradictory knowledge, and a degradation of decision quality.

RAE solves this by introducing a structured memory architecture that preserves decision rationale as a first-class object.

### Performance Impact

| Metric | Vector DB (Raw) | Standard RAG | RAE (Industrial) |
| :--- | :--- | :--- | :--- |
| **Role** | Storage | Retrieval | **Reasoning Engine** |
| **Recall (Hit Rate)** | High (No Filter) | ~70% | **90%** |
| **Precision** | Low (Noise) | ~65% | **81%** |
| **Reasoning Drift** | N/A | High | **< 1%** |

*> See full [Benchmark Reports](benchmarking/README.md)*

---

## 🧠 Core Architecture: 6 Layers / 3 Math Planes

RAE models memory as **six functionally distinct layers**, governed by a 3-layer Mathematical Verification Engine:

### Time-Domain Layers
1.  **Sensory Memory** – Raw signals and transient context (High noise, short TTL).
2.  **Episodic Memory** – What happened (Immutable stream of events).
3.  **Working Memory** – What is currently relevant (Agent's active context / Hard Frames).
4.  **Semantic Memory** – What is known (Consolidated facts and deep knowledge graph).
5.  **Long-term Memory** – Compressed institutional knowledge (Permanent storage).

### Cognitive-Domain Layer (Reflective Core)
6.  **Reflective Memory** – Why decisions were made. It operates as a 3-tiered QFT-inspired system:
    *   **L1: Operational** – Real-time validation of structural contracts and evidence grounding.
    *   **L2: Structural** – Semantic consistency, model economy, and topological linkage.
    *   **L3: Meta (Supreme)** – Epistemic symmetry, field stabilization, and senioral vision.

It is governed by a 3-layer Mathematical Verification Engine (Logic, Set Theory, Graph) that ensures retrieved context is not just semantically similar, but logically consistent.

---

## 🛡️ Security: Hard Frames & Isolation

RAE physically isolates agents in **Hard Frames**:
- **Network Isolation**: Zero internet access for agent containers.
- **Protocol Exclusivity**: Communication ONLY via the RAE Kernel.
- **Implicit Capture**: Every thought and action is automatically logged into the Working Memory.
- **Privacy-First Mesh**: Asynchronous memory synchronization between instances with explicit User Consent (Trust Handshake).

---

## 3x First Philosophy

- 🔐 **Privacy-first**: Designed for full control over data. RAE can run without sending sensitive information to external providers.
- 🏠 **Local-first**: Supports fully on-premise or air-gapped deployments. The cloud is an option, not a requirement.
- 👐 **Open-Source-first**: Available under the Apache-2.0 license as an open standard.

---

## 🚀 Key Use Cases

- **Cross-Platform Knowledge Bridge**: Connect a Windows-based AI agent (like Cursor or Claude) to a high-performance RAE instance running on a Linux server.
- **Persistent Project Context**: Ensure your agent remembers architectural decisions across sessions and model switches.
- **Autonomous Quality Maintenance**: Periodic "Dreaming" cycles that compress and optimize memory for better retrieval.

---

## 🚀 Quick Start

Get RAE up and running in 2 simple steps:

1.  **Clone & Initialize**:
    ```bash
    git clone https://github.com/vproject111/RAE-agentic-memory.git
    cd RAE-agentic-memory
    chmod +x init.sh
    ./init.sh  # Automatically creates .env and workspaces
    ```

2.  **Launch Profile**:
    ```bash
    # Standard (Core Infrastructure):
    docker compose up -d --build

    # Full Potential (Core + Workers + Neural Reranker):
    docker compose --profile full up -d --build

    # Lightweight (SQLite + In-Memory, no external DB):
    docker compose -f docker-compose.lite.yml up -d
    ```

*API available at http://localhost:8001 (Standard/Dev) or http://localhost:8010 (Lite).*

---

## 🔌 Model Context Protocol (MCP) Integration

RAE includes a built-in MCP server enabling agents (like Cursor, Claude Desktop, etc.) to query and save memories seamlessly. 

Add the following to your MCP settings file (e.g., `claude_desktop_config.json` or Cursor's MCP configuration):

```json
{
  "mcpServers": {
    "rae-memory": {
      "command": "python",
      "args": ["-m", "rae_mcp"],
      "cwd": "/path/to/cloned/RAE-agentic-memory/integrations/mcp/src",
      "env": {
        "RAE_API_URL": "http://localhost:8001",
        "RAE_API_KEY": "dev-key",
        "RAE_PROJECT_ID": "default",
        "RAE_TENANT_ID": "00000000-0000-0000-0000-000000000000"
      }
    }
  }
}
```

Make sure the virtual environment or your python environment has the required dependencies (`httpx`, `mcp`, `structlog`, `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-instrumentation-httpx`, `prometheus_client`). You can install them by running:
```bash
pip install -r integrations/mcp/requirements.txt
```

---

## 🏗️ Architecture & Documentation
RAE is a comprehensive mathematical manifold for agentic memory.

- 📖 **[API Reference V2](docs/API_REFERENCE_V2.md)** – Complete endpoint guide (Swagger/ReDoc).
- 🏛️ **[Architectural Blueprint](docs/RAE_ARCHITECTURAL_BLUEPRINT.md)** – Deep dive into 5 layers and 3 math planes.
- 🧬 **[Theory Atlas](docs/THEORY_ATLAS_GUIDE.md)** – Registry of historical mathematical strategies.
- 🛡️ **[Compliance Guide](docs/COMPLIANCE_AND_AUDIT.md)** – ISO 27001/42001 audit trails.

---

## 🔗 Choose Your Path

- 👨‍💻 **[For Developers](docs/paths/developer.md)** – Quick Start & API Integration.
- 🔬 **[For Scientists](docs/paths/scientist.md)** – Mathematical Foundations & Benchmarks.
- 🏭 **[For Industry](docs/paths/industry.md)** – Use Cases & ROI.
- 🔐 **[Security Guide](docs/guides/SECURE_AGENT_DEPLOYMENT.md)** – Hard Frames & Isolation.

---

RAE is licensed under the Apache-2.0 license. We aim to create an open standard for agent memory.
