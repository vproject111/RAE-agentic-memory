- 🧠 **Multi-Layer Memory Architecture**: STM, LTM, Episodic, and Reflective layers governed by a **3-layer Math Engine (Match Layers)**.
- 🚀 **Distributed Compute**: Control Plane API for offloading heavy tasks (embeddings, LLM) to remote GPU nodes.
- 🔍 **Hybrid Search**: Combining vector, semantic, and graph-based retrieval.
*(czyt. „Rej”)*

[![DOI](https://zenodo.org/badge/1088095844.svg)](https://zenodo.org/badge/latestdoi/1088095844)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-892%20passing-brightgreen.svg)]()
[![Coverage](https://img.shields.io/badge/coverage-73.3%25-green.svg)]()
[![Build](https://img.shields.io/badge/build-passing-brightgreen.svg)]()
[![Tests](https://img.shields.io/badge/tests-931%20passed-brightgreen.svg)]()
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

> **💡 New to RAE? Start Here:** [**What is RAE? Architecture & Philosophy**](docs/CONCEPT.md)  
> *Learn why RAE is not just a Vector DB, how the "Hive Mind" works, and the "RAE-First" workflow.*

RAE is an open-source reference architecture for **long-term memory and reasoning continuity** in complex systems. It addresses the fundamental problem of **Reasoning Drift**—the gradual loss of alignment between past decisions, their original rationales, and present system behavior.

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

## The Core Idea: Structured Memory

Long-term reasoning continuity cannot be achieved with undifferentiated memory (e.g., logs, embeddings). It requires an explicit architectural separation of memory into functionally distinct layers.

RAE models memory as **four functionally distinct layers**:

1.  **Episodic Memory** – What happened
2.  **Semantic Memory** – What is known
3.  **Working Memory** – What is currently relevant
4.  **Reflective Memory** – Why decisions were made and whether they remain valid

This separation prevents reasoning drift.
It is governed by a 3-layer Mathematical Verification Engine (Logic, Set Theory, Graph) that ensures retrieved context is not just semantically similar, but logically consistent

---

## 3x First Philosophy

RAE is built on three core principles:

-   🔐 **Privacy-first**: Designed for full control over data. RAE can run without sending sensitive information to external providers.
-   🏠 **Local-first**: Supports fully on-premise or air-gapped deployments. The cloud is an option, not a requirement.
-   👐 **Open-Source-first**: The core of RAE is and will remain available under the Apache-2.0 license as an open standard.

---

## What RAE Is (and Is Not)

**RAE is:**
- An architectural model for cognitive memory.
- A framework for preserving decision rationale.
- A reference implementation for research and engineering.

**RAE is not:**
- A chatbot framework.
- A simple LLM wrapper.
- A vector database replacement.

---

- **Multi-Tenant & Secure**: Row-level security (RLS) ensures data isolation between projects and users.
- **Local & Hybrid LLM Support**: Run completely offline with Ollama or in hybrid mode with Gemini/Claude.
- **Distributed Memory Architecture**: Run RAE as a central memory engine on Linux while connecting agents from Windows, Mac, or Cloud environments.
- **Forensic Intelligence**: Reconstruct agent knowledge and reasoning paths at any point in time using temporal graph snapshots.

## 🔬 OpenScience & Benchmarking

RAE is committed to **Full OpenScience Transparency**. We publish not only our best results but also our current failures and scaling limits. Benchmarking is integrated into every stage of RAE's development to ensure mathematical rigor and prevent reasoning drift.

### 📊 Benchmark Performance (Current Baseline)

| Suite | Scale | MRR | Status | Note |
| :--- | :--- | :--- | :--- | :--- |
| **Academic Lite** | 10 mems | **1.0000** | ✅ PASS | Stable Baseline |
| **Industrial Large** | 1k mems | **0.7634** | ✅ PASS | Recovered from 0.015 |
| **Industrial Extreme** | 10k mems | **0.8200** | ✅ PASS | **New (2026-01-03)** |
| **Industrial Ultra** | 100k mems| **0.0000** | ❌ FAIL | Scale issue: Ground Truth Drift |

> **OpenScience Alert:** As of **2026-01-03**, the `Industrial Ultra` (100k) benchmark shows 0.0 MRR. This is a known limitation in our automated ground truth generation logic for ultra-scale datasets, currently under investigation. [See scaling research logs](benchmarking/results/industrial_ultra_20260103_093152.md).

> **🔬 Deep Dive for Researchers:** For a comprehensive overview of our MDP formalization, Information Bottleneck implementation, and the 9/5 methodology, see the **[RAE for Scientists & Researchers](docs/paths/scientist.md)** guide.

### 🧪 Research Benchmarks (The 9/5 Suite)

For researchers and scientists, RAE provides the **9/5 Suite**—specialized tests for cognitive architecture:

- **LECT** (Long-term Episodic Consistency): **0.9995** stability over 10,000+ cycles.
- **MMIT** (Multi-Layer Interference): **0.0000** interference (Perfect layer isolation).
- **GRDT** (Graph Reasoning Depth): Validated up to **10-hop** reasoning chains.
- **RST** (Reflective Stability): Measures insight robustness under noise.
- **MPEB** (Math-3 Policy Evolution): Evaluates how the system adapts its retrieval policy.

> For detailed methodology and latest execution logs, see **[RAE Benchmarking Suite - Complete Guide](benchmarking/README.md)**.

---

## 📐 The "Match Layers" Architecture (Refactored 2026-01-02)

RAE uses a unified mathematical engine to prevent Reasoning Drift. Following the **January 2026 refactoring**, the scoring logic is partitioned into three pure mathematical components:

1.  **Relevance (Math-1)**: Semantic similarity using vector embeddings.
2.  **Importance (Math-2)**: Intrinsic content value and structural graph centrality.
3.  **Dynamics (Math-3)**: Temporal decay and access frequency (Recency).

**Unified Scoring Formula:**
`S(m, q, t) = α·Relevance(m, q) + β·Importance(m) + γ·Dynamics(m, t)`

This multi-objective ranking ensures that retrieved context is not just "similar" but **logically and temporally coherent** with the current reasoning path.

---

## 🚀 Key Use Cases

- **Cross-Platform Knowledge Bridge**: Connect a Windows-based AI agent (like Cursor or Claude) to a high-performance RAE instance running on a Linux server.
- **Persistent Project Context**: Ensure your agent remembers architectural decisions across sessions and model switches.
- **Autonomous Quality Maintenance**: Periodic "Dreaming" cycles that compress and optimize memory for better retrieval.

## Choose Your Path

- 👨‍💻 **For Developers** – See [Quick Start & API Integration](docs/paths/developer.md)
- 🔬 **For Scientists/Researchers** – See [Mathematical Layers, Benchmarks & Telemetry](docs/paths/scientist.md)
- 🏭 **For Industry** – See [Industrial Use Cases & ROI](docs/paths/industry.md)
- 🏥 **For Healthcare** – See [Data Security & On-Premise Deployments](docs/paths/healthcare.md)
- 🏛️ **For Public Administration** – See [Transparency, Audit & Policies](docs/paths/public-sector.md)
- 🤝 **For Philanthropists or VCs** – See [Research Partnerships & Pilots](docs/paths/partners.md)

*
---

## Quick Start

The easiest way to run RAE is with Docker Compose, now simplified with profiles.

First, clone the repository if you haven't already:
```bash
git clone https://github.com/dreamsoft-pro/RAE-agentic-memory.git
cd RAE-agentic-memory
```

### 1. Development Environment (Hot-Reload)
This is the **recommended setup for local development**. It enables hot-reloading for your code changes. The "Standard Profile" mentioned previously corresponds to this dev setup.
```bash
# Starts the full environment with hot-reload on port 8000
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```
*(Note: This command will be simplified to `docker compose --profile dev up -d` in a future step).*

### 2. Lite Environment (Minimal, Sandboxed)
A self-contained, minimal environment. Ideal for lightweight tasks or running in parallel with the main dev environment.
```bash
# Starts the lite environment on port 8008
docker compose --profile lite up -d
```

### 3. Standard Environment (Production-like)
This runs the base services without any development overrides (no hot-reload).
```bash
# Starts the base environment on port 8000
docker compose up -d
```

**For Developers (Hot-Reload & Autostart):**
You can set up RAE to start automatically on system boot with hot-reload enabled:
```bash
./scripts/setup_autostart.sh
```

For more detailed instructions, see the [Getting Started Guide](docs/LOCAL_SETUP.md).

---

## RAE in Action

Don't just store text. Store the *context* and *reasoning*.

```python
from rae_sdk import RAEClient

client = RAEClient()

# 1. Store memory with semantic importance
await client.store(
    content="User prefers local processing for PII data.",
    layer="semantic",  # Logic layer
    importance=0.9,
    tags=["privacy", "gdpr"]
)

# 2. Agent retrieves with reasoning trace
response = await client.agent.execute(
    "Should I upload the payroll file to the public cloud?",
    project="finance-bot"
)

# Result: "No. Strict Block. Rationale: User prefers local processing for PII data."
```

### 🔬 Scientific Use Case: Dynamic Hypothesis Refinement

This example demonstrates how RAE's 4-layer memory and 3-layer Math Control Plane enable autonomous scientific discovery.

**Scenario:** An agent is testing a new catalyst (Compound X) and encounters unexpected results.

1.  **Semantic Memory Retrieval (Math-1)**:
    *   *Agent Query:* "Expected reaction rate for Compound X?"
    *   *RAE:* Retrieves established theory: "Compound X should accelerate reaction at > 50°C." (Confidence: 0.95)

2.  **Episodic Memory Recording (Sensory -> Episodic)**:
    *   *Experiment:* Agent runs test at 60°C. Reaction fails.
    *   *RAE:* Records: `Episode(Action="Test 60C", Outcome="Failure", Surprise=High)`

3.  **Reflective Loop (Math-3 + Reflection)**:
    *   *Trigger:* `Surprise > Threshold`. The **Math-3** layer detects high Information Entropy (Theory vs. Observation divergence).
    *   *Reflection Engine:* Activates. It correlates this failure with a past vague episode "Compound X degrades in high humidity."
    *   *Consolidation:* RAE updates Semantic Memory: "Compound X is humidity-sensitive." (New Rule).

4.  **Policy Update (Math-2)**:
    *   *Adaptation:* The **Math-2 Controller** updates the retrieval policy for future chemistry queries to prioritize "Environmental Conditions" (Beta weight increased).

```python
# Detailed simulation available in: examples/scientific_discovery_simulation.py
```

---

## API Documentation

Full API reference is available in [API_DOCUMENTATION.md](API_DOCUMENTATION.md).

It includes comprehensive details on:
- **Memory & Agent APIs** (Store, Query, Execute)
- **GraphRAG & Hybrid Search**
- **Governance & Monitoring**
- **Interactive Swagger UI** (available locally at `http://localhost:8000/docs`)

---

## Project Status

RAE is an active research and engineering project. The architecture is stable, and the implementation is "Enterprise Ready" for many use cases.

-   **Core Functionality**: 4-layer memory, hybrid search, JWT authentication, and multi-tenancy are stable.
-   **Maturity**: Test coverage is actively being increased. Production deployment guides are in development.
-   **See [STATUS.md](docs/.auto-generated/status/STATUS.md)** for a detailed feature breakdown.

---

## Open Source and Collaboration

RAE is and will remain a fully open-source project under the Apache-2.0 license. We aim to create an open, auditable standard for agent memory.

Commercial services and extensions (e.g., enterprise support, specialized integrations) may be developed around the open-source core. This does not change the fact that the RAE engine itself is available to everyone under the same permissive license.

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md).

---


## Filesystem Portability

RAE does not rely on hardcoded filesystem paths.
All paths are resolved relative to `PROJECT_ROOT` and can be overridden
using the `RAE_PROJECT_ROOT` environment variable.

### Directory Structure
- `data/` - Persistent storage (memory, logs)
- `config/` - Configuration files
- `core/paths.py` - Single source of truth for paths

To override the root directory (e.g., in Docker):
```bash
export RAE_PROJECT_ROOT=/app
```

## Contributing


This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.
