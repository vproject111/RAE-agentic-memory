# RAE for Scientists & Researchers

This document provides a comprehensive, code-first overview of the RAE (Reasoning and Action Engine) for researchers in AI, cognitive science, reinforcement learning, and advanced memory systems. It is designed to be a technical deep-dive, with every claim and formula directly traceable to the production source code.

## The Reasoning Drift Problem

Reasoning Drift is a phenomenon observed in large language models (LLMs) where the model's reasoning process deviates from an optimal path over long conversations or complex, multi-step tasks. This can manifest as:

-   **Loss of Context:** Forgetting critical information from earlier in the interaction.
-   **Attentional Misallocation:** Focusing on irrelevant details while ignoring key facts.
-   **Hallucination:** Inventing facts or relationships that are not grounded in the provided context.
-   **Goal Decay:** Losing track of the original user intent or primary objective.

RAE is architected to mitigate Reasoning Drift through a structured, multi-layer memory system and a continuous process of self-evaluation and reflection.

## 4-Layer Memory Architecture

RAE employs a 4-layer memory architecture inspired by human cognitive systems. Each layer serves a distinct purpose and operates on a different timescale.

### 1. Episodic Memory
-   **Purpose:** Records a raw, chronological log of all events, interactions, and observations. This is the "ground truth" of the agent's experience.
-   **Mathematical Model:** A time-series database of immutable events `E = {e_1, e_2, ..., e_t}`.
-   **Storage Mechanism:** Stored in a PostgreSQL database, preserving the exact sequence and content of events.

### 2. Semantic Memory
-   **Purpose:** Extracts and consolidates factual knowledge, entities, and relationships from episodic memory. It represents what the agent *knows*.
-   **Consolidation Algorithm:** A background process periodically analyzes recent episodic events, performs entity extraction (e.g., identifying people, places, concepts), and creates or updates nodes in a knowledge graph.
-   **Storage Mechanism:** Stored as both structured data in PostgreSQL and as vector embeddings in Qdrant for semantic search.

### 3. Working Memory
-   **Purpose:** Holds the current context selected for a specific task. This is the information that is actively "in mind" and passed to the LLM for reasoning.
-   **Context Selection:** The process of selecting memories from the other layers to populate the working memory is governed by the **Information Bottleneck Theory**.
-   **Token Budget:** Working memory is constrained by a token budget (e.g., 4000 tokens), making the context selection process a critical optimization problem.

### 4. Reflective Memory
-   **Purpose:** Stores higher-order insights, learned strategies, and "lessons learned" from past successes and failures. It is the basis for meta-learning and self-improvement.
-   **Generation Pattern:** Reflections are generated via the **Actor-Evaluator-Reflector** pattern. After an action is taken, the `Evaluator` assesses the outcome. If the outcome is significant (a notable success or failure), the `Reflector` is triggered to generate a new reflection.
-   **Storage Mechanism:** Stored as distinct memory items with high importance scores, often including actionable strategies.

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

## Mathematical Foundations

This section details the core mathematical models implemented in RAE. Each formula is directly extracted from the source code and includes references to the relevant files and line numbers.

### 1. Information Bottleneck Theory for Context Selection

The selection of which memories to place into the limited working context is framed as an optimization problem using the Information Bottleneck (IB) principle.

**Code Reference:** [`apps/memory_api/core/information_bottleneck.py`](../../apps/memory_api/core/information_bottleneck.py)

**Theoretical Formulation (Lines 1-7):**

The goal is to find a compressed context `Z` from the full memory `X` that remains maximally informative about the desired output `Y`. This trade-off is captured by the Lagrangian:

```
L = I(Z; Y) - β·I(Z; X)
```

Where:
-   `I(Z; Y)` is the mutual information between the context `Z` and the output `Y`. This term represents the **relevance** of the context.
-   `I(Z; X)` is the mutual information between the context `Z` and the full memory `X`. This term represents the **compression cost**.
-   `β` is a hyperparameter that controls the trade-off. A higher `β` favors more compression, while a lower `β` favors more relevance.

**Practical Implementation (Lines 56-181):**

RAE implements a greedy algorithm to approximate the IB objective. For each individual memory item `m`, the objective is calculated, and the items with the best scores are selected until the token budget is filled.

**1.1. Relevance Score: `I(m; Y)` Approximation**

The relevance of a single memory `m` to the query `Y` is not just a simple cosine similarity. It's a weighted combination that also considers the memory's intrinsic importance.

*   **File:** `apps/memory_api/core/information_bottleneck.py`
*   **Function:** `_compute_relevance_scores` (Lines 205-228)
*   **Formula:** `relevance = 0.8 * cosine_similarity(m.embedding, query.embedding) + 0.2 * m.importance`

This implementation acknowledges that some memories are inherently more important, regardless of the immediate query.

**1.2. Compression Cost: `I(m; X)` Approximation**

The compression cost of including a memory `m` is approximated by its normalized token count, adjusted by a penalty based on its memory layer.

*   **File:** `apps/memory_api/core/information_bottleneck.py`
*   **Function:** `_compute_compression_costs` (Lines 230-271)
*   **Formula:** `compression_cost = (m.tokens / total_tokens) * layer_penalty`

The `layer_penalty` values reveal a sophisticated understanding of the memory structure:
-   `reflective`: 0.5 (Already compressed, low cost to include)
-   `ltm`: 0.6 (Consolidated, fairly low cost)
-   `semantic`: 0.7 (Mid-level abstraction)
-   `working`: 0.9 (Recent but raw, high cost)
-   `episodic`: 1.0 (Raw experience, highest cost to include)

**1.3. Adaptive Beta**

The trade-off parameter `β` is not always static. It can be adapted based on the context of the query.

*   **File:** `apps/memory_api/core/information_bottleneck.py`
*   **Function:** `adaptive_beta` (Lines 378-422)
*   **Logic:**
    -   Starts with a `base_beta` based on user preference ("quality", "balanced", "efficiency").
    -   **Decreases `β`** for complex queries (to pull in more context).
    -   **Increases `β`** when the token budget is low (to force more compression).

### 2. Reinforcement Learning-Based Reward Function

RAE's policy—what action to take next—is optimized by maximizing a cumulative reward signal. The reward function balances the quality of an action's outcome against its resource costs.

**Code Reference:** [`apps/memory_api/core/reward.py`](../../apps/memory_api/core/reward.py)

**Theoretical Formulation (Lines 1-7):**

The reward `R` for a transition from state `s_t` to `s_{t+1}` via action `a_t` is defined as:

```
R(s_t, a_t, s_{t+1}) = Quality(s_{t+1}) - λ·TokenCost(a_t) - μ·Latency(a_t)
```

Where:
-   `Quality`: A normalized score (0-1) of how well the action's outcome achieved the goal.
-   `TokenCost`: The number of tokens used by the action.
-   `Latency`: The time in milliseconds the action took to execute.
-   `λ` and `μ` are hyperparameters that price the cost of tokens and latency, respectively.

**Default Hyperparameters (Lines 93-98):**
-   `λ (lambda_)`: `0.001` (A cost of 1000 tokens corresponds to a -1 penalty)
-   `μ (mu)`: `0.01` (A latency of 100ms corresponds to a -1 penalty)
-   `γ (discount_factor)`: `0.95`

**2.1. Quality Evaluation (`_evaluate_quality`)**

The `Quality` term is not a single formula but a **heuristic-based dispatcher** that calls a specific evaluation function based on the type of action taken.

*   **File:** `apps/memory_api/core/reward.py`
*   **Function:** `_evaluate_quality` (Lines 186-256)

This is a critical architectural pattern. Here are some of the key quality heuristics:

-   **Retrieval Quality (Lines 258-283):** Quality is a function of the number of memories retrieved (with diminishing returns) and their average relevance. The code includes a `TODO` to incorporate relevance scores, indicating an area of active development.

-   **LLM Quality (Lines 285-316):** This is explicitly a **placeholder** that uses a simple heuristic based on the length of the LLM's output. The comments state that in a production environment, this should be driven by user feedback or other, more direct quality signals.

-   **Reflection Quality (Lines 318-341):** This is more advanced. The quality of generating a reflection is determined by the `composite_score` of the reflection itself, which is calculated based on its novelty, importance, and utility. This creates a tight feedback loop for the meta-learning process.

### 3. Memory Scoring V3 (Match Layers Architecture)

When retrieving memories, RAE needs to score them to determine which are most valuable for the current context. The v3 scoring model (refactored 2026-01-02) is a weighted linear combination of six different factors, grouped into three **Match Layers (Math-1/2/3)**.

**Live Benchmark Data:** For the latest real-time execution results, scale tests (up to 100k memories), and current OpenScience status, refer to the **[Main README - OpenScience Section](../../README.md#benchmarking-performance-current-baseline)**.

**Scoring Formula (Lines 1-8):**



```
score = w1*relevance + w2*importance + w3*recency + w4*graph_centrality + w5*diversity + w6*density
```

**Default Weights (Lines 29-37):**
-   `w1_relevance`: 0.40
-   `w2_importance`: 0.20
-   `w3_recency`: 0.10
-   `w4_centrality`: 0.10
-   `w5_diversity`: 0.10
-   `w6_density`: 0.10

**3.1. Key Sub-Algorithms**

-   **Recency Score (Lines 188-212):** The recency score uses an exponential decay function, but with a crucial modification: the decay rate is slowed by the memory's `access_count`.
    -   `effective_decay = base_decay_rate / (log(1 + access_count) + 1)`
    -   This means frequently accessed memories stay "fresh" for longer, even if they haven't been accessed very recently.

-   **Diversity Score (Lines 215-251):** This score is calculated for a batch of results. For each memory, its diversity is `1.0 - (average cosine similarity to other items in the batch)`. This actively penalizes redundancy in the retrieval results, promoting a more comprehensive context.

-   **Density Score (Lines 254-281):** A heuristic for information density, calculated as `min(1.0, token_count / 500.0)`. This suggests that memories are considered optimally dense around 500 tokens.

---

## Benchmarks & Performance Data

This section summarizes real performance metrics extracted from benchmark runs to provide a transparent view of RAE's capabilities. We analyze two contrasting examples to illustrate performance characteristics.

*> Full datasets and reproduction scripts are available in [benchmarking/README.md](../../benchmarking/README.md).*

### Summary of Key Metrics

| Metric                  | Description                                                  | `industrial_small` (Good Run) | `academic_lite` (Poor Run) |
| ----------------------- | ------------------------------------------------------------ | ----------------------------- | -------------------------- |
| **MRR**                 | Mean Reciprocal Rank. Measures the rank of the first correct answer. Higher is better (1.0 is perfect). | **0.806**                     | 0.0                        |
| **Hit Rate @3**         | % of queries where a correct result was in the top 3.        | **90.0%**                     | 0.0%                       |
| **Hit Rate @10**        | % of queries where a correct result was in the top 10.       | **95.0%**                     | 0.0%                       |
| **Precision @3**        | Of the top 3 results, % that were relevant.                  | 40.0%                         | 0.0%                       |
| **Recall @3**           | Of all possible relevant results, % found in the top 3.      | **72.5%**                     | 0.0%                       |
| **Overall Quality**     | Composite score reflecting overall performance.              | **0.746**                     | 0.0                        |
| **Avg. Query Time**     | Average latency for a retrieval query.                       | 8.1 ms                        | 7.7 ms                     |
| **Avg. Insert Time**    | Average latency for inserting a new memory.                  | 68.6 ms                       | 206.3 ms                   |

### Analysis of a High-Performance Run

The `industrial_small_20251207_131859` benchmark represents a high-performance scenario on a complex, real-world dataset.

-   **Excellent Retrieval Accuracy:** With an **MRR of 0.806** and a **Hit Rate @3 of 90%**, the system consistently ranks correct answers near the top. This demonstrates that the core scoring and retrieval algorithms are effective at identifying relevant memories.

-   **High Recall, Moderate Precision Trade-off:** The system achieved a high **Recall @3 of 72.5%** but a lower **Precision @3 of 40.0%**. This is a classic and important trade-off. It indicates that the system is configured to "cast a wide net" to ensure it doesn't miss relevant information, even if it means including some less relevant results. For many reasoning tasks, maximizing recall is more important than maximizing precision to avoid missing critical context.

-   **Fast Performance:** Query latencies were low (**8.1ms average**), demonstrating the efficiency of the retrieval system even with a complex scoring model.

### Analysis of a Low-Performance Run

The `academic_lite_20251207_114508` benchmark represents a failed or misconfigured run, which is equally instructive.

-   **Total Retrieval Failure:** All quality metrics—MRR, Hit Rate, Precision, and Recall—are **zero**. A look at the `detailed_results` in the JSON file confirms that for every query, the `retrieved` array was empty.

-   **Implications:** This result is not an indictment of the engine itself but highlights the importance of proper data ingestion and configuration. It demonstrates that the benchmarking suite is effective at catching critical failures. The zero-score run provides a valuable baseline and a clear signal that something in the data pipeline or indexing for that specific run was broken.

This transparency in benchmarking, showing both successes and failures, is critical for rigorously evaluating and improving the system.

---

## Implementation Details

### The Actor-Evaluator-Reflector Pattern

RAE's ability to learn and adapt is built on the Actor-Evaluator-Reflector pattern. This is a continuous loop of `Act -> Evaluate -> Reflect`.

**1. Actor:** Any component that performs an action (e.g., calls a tool, queries a database, calls an LLM).

**2. Evaluator:** After an action completes, the `Evaluator` assesses the outcome.

*   **Code Reference:** [`apps/memory_api/services/evaluator.py`](../../apps/memory_api/services/evaluator.py)
*   **Key Implementations:**
    *   `DeterministicEvaluator` (Lines 142-199): A simple, rule-based evaluator that checks for explicit errors or timeouts.
    *   `ThresholdEvaluator` (Lines 202-270): Evaluates based on a quantitative `quality_score` compared against success and failure thresholds.
    *   `LLMEvaluator` (Lines 273-353): A meta-evaluator that uses another LLM to assess the performance of the main agent, asking it to determine success, quality, and the need for reflection.

**3. Reflector:** If the `Evaluator` determines the outcome is significant, it triggers the `Reflector`.

*   **Code Reference:** [`apps/memory_api/services/reflection_engine_v2.py`](../../apps/memory_api/services/reflection_engine_v2.py)
*   **Core Logic:**
    *   The engine uses two different prompts depending on the outcome: `REFLECTION_FAILURE_PROMPT` for errors and `REFLECTION_SUCCESS_PROMPT` for successes.
    *   The LLM is prompted to generate a structured JSON object containing the reflection, a potential strategy, an importance score, and tags.
    - The resulting reflection and strategy are stored as new items in the Reflective Memory layer.