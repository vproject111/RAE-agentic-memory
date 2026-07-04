---
title: "The Reflective Agentic-Memory Engine (RAE): Architectural Foundations of Mathematically Controlled Cognitive Systems"
creators:
  - name: Leśniowski, Grzegorz
    affiliation: Printworks sp. z o.o.
    orcid: 0009-0003-6672-671X
date: 2025-12-26
keywords:
  - Cognitive Architecture
  - Multi-Layered Memory
  - Mathematical Control Theory
  - Multi-Armed Bandits
  - Information Bottleneck
  - Provider-Agnostic Software
license: Apache-2.0
---

# Abstract

Contemporary Large Language Model (LLM) agents suffer from "Reasoning Drift"—the tendency to lose coherent decision-making capabilities over long operational horizons. This paper argues that this failure mode is not a limitation of the model size, but a deficiency in the cognitive architecture: specifically, the lack of a distinct, active memory substrate. We introduce the **Reflective Agentic-Memory Engine (RAE)**, an open-source framework that decouples memory from inference. RAE implements a **Four-Layer Memory Hierarchy** (Sensory, Working, Episodic/Semantic, Reflective) governed strictly by a **Three-Layer Mathematical Control Plane**. Unlike passive vector databases, RAE employs active probabilistic policies (Math-2) and information-theoretic metrics (Math-3) to modulate how information is stored, retrieved, and consolidated. We provide a comprehensive engineering analysis of RAE's provider-agnostic core, detailing the mathematical formulas driving its decision loop and the architectural patterns ensuring full infrastructure independence.

# 1. Introduction

The prevailing paradigm in AI agent design treats memory as a passive storage utility—typically a vector database where text embeddings are retrieved via Cosine Similarity. While effective for simple question-answering (RAG), this approach fails in autonomous agentic workflows where the system must learn from its own actions, correct its errors, and maintain a consistent "self" over time.

We identify three critical flaws in passive memory architectures:
1.  **Context Overload:** Indiscriminate retrieval floods the LLM's context window with noise.
2.  **Static Logic:** Retrieval strategies are hardcoded, failing to adapt when the nature of the task changes (e.g., creative exploration vs. strict fact-checking).
3.  **Lack of Meta-Cognition:** The system does not "know" when its memory is flawed or contradictory.

RAE addresses these by inverting the control flow. Instead of the LLM simply querying a database, RAE acts as an active cognitive engine where a mathematical control plane dictates *what* is worth remembering and *how* it should be retrieved.

# 2. Engineering Philosophy: The Agnostic Core

RAE is engineered on the principle of **Radical Agnosticism**. The core logic of the system—the memory layers and mathematical controllers—is strictly isolated from the infrastructure that supports it. This ensures reproducibility and stability regardless of the hardware or cloud provider.

## 2.1. Core vs. Infrastructure Separation
The architecture follows a strict Hexagonal (Ports and Adapters) pattern:

*   **The RAE Core (Inner Ring):** Contains the Python classes for Memory Nodes, Graphs, Math Controllers, and Reflection Logic. This code has *zero* dependencies on external databases or APIs. It operates on pure data structures (`pydantic` models) and abstract interfaces.
*   **The Infrastructure Adapters (Outer Ring):** Concrete implementations that plug into the Core.
    *   *Storage Adapter:* Can swap between `PostgreSQL` (relational), `Qdrant` (vector), or `SQLite` (local).
    *   *LLM Adapter:* Can swap between `Anthropic Claude`, `Google Gemini`, or local `Ollama` models.
    *   *Cache Adapter:* Can swap between `Redis` (distributed) or `DiskCache` (local).

This design guarantees that the mathematical behavior of the system described in Sections 3 and 4 remains identical whether running on a high-performance cluster or a local laptop (Local-First).

# 3. The Four-Layer Memory Hierarchy

RAE structures memory not by data type (text vs. image), but by cognitive function.

## 3.1. Layer 1: Sensory Memory (The Buffer)
*   **Role:** Noise Filtering & Signal Detection.
*   **Mechanism:** A high-frequency buffer with a strict Time-To-Live (TTL).
*   **Process:** Incoming observations $O_t$ are temporarily held. A cheap L1-heuristic (keyword density or regex) assigns a `Salience Score`. If $Score(O_t) < Threshold$, the observation is discarded before ever touching the database or embedding model.

## 3.2. Layer 2: Working Memory (The Context)
*   **Role:** Task Execution State.
*   **Mechanism:** A dynamic list of "Active Frames" adhering to Miller’s Law (capacity $C oughly 7$).
*   **Eviction Policy:** Unlike LRU (Least Recently Used), RAE uses **LIV (Least Important Value)**. The Math-1 layer continuously re-scores items in working memory. When $N > C$, the item with the lowest weighted importance is evicted to Long-Term Memory.

## 3.3. Layer 3: Long-Term Memory (Episodic & Semantic)
This layer is physically stored in a hybrid Graph-Vector database.
*   **Episodic (The Timeline):** Stores raw experience as linked lists of `(State, Action, Reward, Next_State)`. It answers "What happened?".
*   **Semantic (The Graph):** Stores crystallized facts. Nodes represent concepts (e.g., "Python", "API"), and edges represent relationships. It answers "What is true?".
*   **Consolidation:** A background process migrates repeated patterns from Episodic to Semantic memory, compressing data (e.g., 10 error logs become 1 rule: "System fails at midnight").

## 3.4. Layer 4: Reflective Memory (The Meta-Cognition)
*   **Role:** System Correction & Policy Storage.
*   **Nature:** This layer does not store external information. It stores **internal state**.
*   **Content:**
    *   *Optimization Rules:* "Increase search depth for query type X."
    *   *Failure Patterns:* "The agent tends to hallucinate on legal queries."
    *   *Ethical Boundaries:* "Never execute shell commands without user approval."

# 4. The Three-Layer Mathematical Control Plane

The brain of RAE is not the LLM, but the Mathematical Control Plane. This component determines the *dynamics* of the system.

## 4.1. Math-1: Operational Control (Deterministic)
This layer handles atomic, per-query operations. Its goal is efficiency.
The core mechanism is the **Unified Scoring Function**. For any memory candidate $m$, its retrieval score $S$ is calculated as:

$$ S(m) = \alpha \cdot \text{Sim}(q, m) + \beta \cdot \text{Imp}(m) + \gamma \cdot \text{Rec}(m) + \delta \cdot \text{Assoc}(m) $$

Where:
*   $\text{Sim}(q, m)$: Cosine similarity between query $q$ and memory $m$ (Vector Search).
*   $\text{Imp}(m)$: Global importance score of the memory node (PageRank-like metric).
*   $\text{Rec}(m)$: Recency decay function, typically $e^{-\lambda \Delta t}$.
*   $\text{Assoc}(m)$: Graph connectivity score (how many active working memory nodes link to this node).
*   $\alpha, \beta, \gamma, \delta$: Dynamic weights controlled by Math-2.

## 4.2. Math-2: Strategic Control (Probabilistic)
This layer optimizes the *strategy* of retrieval over time. It answers: "Should we trust vector search, or look for exact keyword matches?"
RAE formulates this as a **Multi-Armed Bandit (MAB)** problem.
*   **Arms (Strategies):**
    1.  *Deep Semantic:* High $\alpha$, heavy vector usage.
    2.  *Recent Context:* High $\gamma$, looks at immediate history.
    3.  *Graph Walk:* High $\delta$, explores related concepts.
*   **Algorithm:** We utilize the **UCB1 (Upper Confidence Bound)** algorithm to balance Exploration vs. Exploitation. The selection value for strategy $j$ is:

$$ A_j = \bar{X}_j + \sqrt{\frac{2 \ln n}{n_j}} $$

Where:
*   $\bar{X}_j$: Average reward (success rate) of strategy $j$ so far.
*   $n$: Total number of queries performed.
*   $n_j$: Number of times strategy $j$ has been selected.

If a strategy leads to a successful answer (validated by user feedback or Math-3 consistency), $\bar{X}_j$ increases, reinforcing that behavior.

## 4.3. Math-3: Systemic Control (Information Theoretic)
This layer monitors the "health" of the memory system using Information Theory principles.
*   **Entropy ($H$):** Measures the confusion of the retrieval set. If the returned memories have very similar scores (flat distribution), Entropy is high.
    $$ H(P) = - \sum_{i} p_i \log p_i $$
    *Trigger:* High Entropy $\to$ "I am confused" $\to$ Triggers Math-2 to switch strategies (e.g., widen search).
*   **Surprise (KL-Divergence):** Measures the divergence between the *Expected Outcome* (from Semantic Memory) and the *Actual Outcome* (from Sensory/Episodic Memory).
    $$ D_{KL}(P || Q) = \sum_{x} P(x) \log \frac{P(x)}{Q(x)} $$
    *Trigger:* High Divergence $\to$ "Something is wrong" $\to$ Activates the **Reflection Engine**.

# 5. System Dynamics: The Reflective Loop Example

To demonstrate the interaction of all 7 layers (4 Memory + 3 Math), consider a scientific agent testing a hypothesis.

1.  **Hypothesis:** "Compound X is stable." (Stored in **Semantic Memory**).
2.  **Action:** Agent heats Compound X. It explodes.
3.  **Sensory Capture:** "Explosion detected." (**Sensory Layer** validates signal).
4.  **Math-3 Check:**
    *   $P$ (Observed): Instability (Explosion).
    *   $Q$ (Expected): Stability.
    *   $D_{KL}(P||Q)$: **HIGH** (Massive Surprise).
5.  **Reflective Trigger:** The core system pauses. The **Reflection Engine** takes over.
6.  **Math-2 Update:** The bandit algorithm receives a negative reward for the "Trust Semantic Memory" strategy. It updates weights.
7.  **Math-1 Adjustment:** The system increases $\gamma$ (Recency) to prioritize the new explosion event over the old theory.
8.  **Consolidation:** A new rule is written to **Reflective Memory**: "Theory regarding Compound X is unreliable under heat."

# 6. Conclusion

RAE demonstrates that robust autonomous agency cannot be achieved by model scaling alone. It requires a dedicated, mathematically grounded memory architecture. By explicitly defining the layers of storage and, crucially, the layers of mathematical control that govern them, RAE provides a transparent, adaptable, and self-correcting foundation for the next generation of AI systems. The open-source code provides a reference implementation of these concepts, agnostic to the underlying infrastructure, proving that advanced cognition can be achieved with standard engineering primitives.
