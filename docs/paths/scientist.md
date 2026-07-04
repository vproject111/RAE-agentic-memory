# RAE: Reflective Agentic-memory Architecture (Scientific Manifesto)

*System Version: 5.2.0 (Silicon Oracle)*  
*Core Paradigm: Deterministic Agentic Information Processing*

This document formalizes the RAE (Reflective Agentic-memory Engine) as a modular cognitive architecture that bridges Information Theory, Graph Dynamics, and Quantum Field Theory (QFT) concepts into a production-ready engineering framework.

### 5. Knowledge Graph (GraphRAG)
-   **Purpose:** Captures structural relationships between entities that are often missed by vector similarity.
-   **Extraction:** Uses LLM-based information extraction to identify triples (Subject, Predicate, Object) from episodic memories.
-   **Traversal:** Supports advanced algorithms like **PageRank** for node importance and **Shortest Path** for finding connections between distant concepts.
-   **Hybrid Search:** Combines vector search results with graph traversal results using a weighted fusion algorithm.

### 6. Scientific Evaluation Framework
RAE includes a comprehensive **Evaluation API** for rigorous scientific testing.
-   **Drift Detection:** Uses statistical tests (Kolmogorov-Smirnov, PSI) to detect when the distribution of memory scores shifts significantly over time.
-   **A/B Testing:** Native support for running experiments with different retrieval strategies (e.g., Vector vs. Hybrid) and comparing metrics.
-   **IR Metrics:** Built-in calculation of MRR, NDCG, Precision, and Recall for every query.

---

## Architecture & Mathematical Deep Dive

For researchers requiring a granular understanding of the system's theoretical underpinning and design evolution, we provide detailed internal documentation.

### Core Mathematical Specification
- **[RAE Mathematical Refactoring Guide](../../docs/RAE_MATHEMATICAL_REFACTORING_GUIDE.md)**: A comprehensive definition of RAE as a **Markov Decision Process (MDP)**. It details the state space representation, action space formalization, and the **Information Bottleneck** implementation for context selection.

### Architectural Decision Records (ADR)
A series of reports documenting the key architectural decisions, trade-offs, and philosophies behind RAE:

| Report | Topic | Description |
| :--- | :--- | :--- |
| **[REPORT_01](../../REPORT_01_ARCH_AGNOSTICISM.md)** | **Arch Agnosticism** | Decoupling logic from specific LLM providers and frameworks. |
| **[REPORT_02](../../REPORT_02_ASYNC_EXECUTION.md)** | **Async Execution** | Handling long-running cognitive tasks and parallel processing. |
| **[REPORT_03](../../REPORT_03_COLD_START.md)** | **Cold Start** | Strategies for system bootstrapping and initial memory seeding. |
| **[REPORT_04](../../REPORT_04_MIGRATIONS.md)** | **Migrations** | Evolution of memory schemas without data loss. |
| **[REPORT_05](../../REPORT_05_DATA_CONSISTENCY.md)** | **Data Consistency** | Managing distributed state across SQL, Vector, and Graph stores. |
| **[REPORT_06](../../REPORT_06_TEST_PHILOSOPHY.md)** | **Test Philosophy** | Strategy for testing non-deterministic agents. |
| **[REPORT_07](../../REPORT_07_FAILURE_RECOVERY.md)** | **Failure Recovery** | Self-healing mechanisms and circuit breakers. |
| **[REPORT_08](../../REPORT_08_CONCEPTUAL_COHERENCE.md)** | **Conceptual Coherence** | Maintaining logical integrity across all system layers. |

---

## 🔬 1. Knowledge Classification (5-Layer Model)
RAE enforces a strict taxonomy of information based on its lifecycle and sensitivity (aligned with ISO 42001/27001):

1.  **Sensory (Input):** Raw perception stream, pre-processing stage.
2.  **Working (Transient):** Active task state ($O(1)$). High volatility; restricted to `RESTRICTED` data isolation.
3.  **Episodic (Temporal):** Chronological event stream $(e_t)$. Preserves temporal precision and sequential logic.
4.  **Semantic (Relational):** Permanent Knowledge Graph $G(V, E)$. Abstracted entities and topological relations.
5.  **Reflective (Meta):** Systemic self-knowledge. Stores performance metrics, strategy weights (MAB), and audit trails.

---

## 🧠 2. Memory Scales (Temporal Architecture)
RAE mimics human memory by segregating data into four functional scales:

*   **Short-term (Working Memory):** High-speed, TTL-indexed transient buffer.
*   **Medium-term (Episodic Memory):** Vector-indexed manifold storing $e_t$ as high-dimensional embeddings.
*   **Long-term (Semantic Memory):** Persistent sparse graph structure for ontological stability.
*   **Reflective Memory:** The "System 2" supervisor managing cross-layer consistency.

---

## 📐 3. Mathematical Retrieval Tiers (The Pipeline)
Memory retrieval is treated as a multi-stage optimization problem across three tiers:

### Tier L1: Bayesian Heuristics (Prior Distribution)
RAE estimates the prior probability $P(S|Q)$ using symbolic anchoring and token density. It biases weights between Full-Text Search (FTS) and Vector Space Search:
$$W_{fts} = \frac{\sum \text{keywords}}{\text{total\_tokens}}, \quad W_{vec} = 1 - W_{fts}$$

### Tier L2: Logic Gateway (Reciprocal Rank Fusion)
Divergent search results from multiple strategies are consolidated into a unified probabilistic ranking using **Reciprocal Rank Fusion (RRF)**:
$$RRFScore(d) = \sum_{r \in R} \frac{1}{k + rank(d, r)}$$
where $k$ is a smoothing constant (default $k=60$) and $rank(d, r)$ is the rank of document $d$ in strategy $r$.

### Tier L3: Multi-Armed Bandit (Evolutionary Optimization)
RAE employs **Thompson Sampling** on a Dirichlet-Multinomial distribution to optimize strategy selection. Strategies are treated as "Arms" in a MAB problem:
$$\theta_i \sim \text{Beta}(\alpha_i + \text{successes}, \beta_i + \text{failures})$$
The system maximizes Mean Reciprocal Rank (MRR) by reinforcing successful retrieval patterns.

---

## ⚡ 4. Szubar Mode: Success from Failure
**Szubar Mode** is an implementation of **Emergent Induction**. It is triggered when the standard pipeline yields high uncertainty (Search MISS).

*   **Trigger:** $\max(Score) < \tau$ (Confidence Threshold).
*   **Mechanism (Neighborhood Recruitment):** Instead of returning null, RAE performs an "Inductive Leap" using low-confidence candidates as seeds in the Semantic Graph:
    $$V_{recruited} = \{v \in G \mid \text{dist}(v, v_{seed}) < \delta\}$$
*   **Outcome:** Failure is used as a signal to shift the observation scale, recovering logical connections that vector similarity ($cos(\theta)$) alone would miss.

---

## 🌊 5. Semantic Resonance (Energy Propagation)
RAE models concept relationships via **Heat Kernel Dynamics**. Energy (math_score) injected into "Direct Hit" nodes propagates through the graph edges:
$$E_{target} = E_{source} \cdot w_{ij} \cdot \phi$$
where $\phi$ is the resonance factor. The field state at time $t$ is described by the heat equation on the graph:
$$\frac{\partial \mathbf{u}}{\partial t} = -L \mathbf{u}$$
where $L$ is the graph Laplacian. This enables the discovery of "Hidden Context" through structural energy distribution.

---

## 🌌 6. Triple-Layer Reflection (QFT-Inspired)
The reflection system treats the "Idea Field" as a dynamic manifold requiring renormalization for stability:

1.  **L1 – Operational Reflection (Evidence Check):** Calculates the **Coverage Ratio (CR)**:
    $$CR = \frac{|\text{Source} \cap \text{Answer}|}{|\text{Answer}|}$$
    Responses with $CR < \theta$ are blocked to prevent hallucinations (*Hard Frames*).
2.  **L2 – Structural Reflection (Retrieval Analysis):** Performs post-hoc analysis on failed strategies, generating `insight_candidates` to adjust `top_k` and `epsilon` parameters.
3.  **L3 – Meta-Field Reflection (Renormalization):** Ensures scale-invariance. If macro-conclusions contradict micro-facts, the **Field Stability Index (FSI)** is penalized:
    $$FSI = 1 - \frac{1}{N} \sum | \text{Conclusion}_{macro} - \text{Fact}_{micro} |$$

---
*RAE transforms LLM uncertainty into a deterministic, auditable data structure, targeting MRR 1.0 convergence across all industrial scales.*
