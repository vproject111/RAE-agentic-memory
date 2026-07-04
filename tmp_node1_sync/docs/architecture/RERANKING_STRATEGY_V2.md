# RAE Hybrid Reranking Strategy V2

## Executive Summary
This document outlines the "Hybrid Lightweight Reranking" strategy. We are moving away from heavy, dedicated Cross-Encoder containers (bert/nvidia) in favor of a flexible approach that utilizes existing resources:
1.  **Generative Reranking (LLM-based):** Used when a local GPU/LLM is available.
2.  **Math Reranking (Algorithmic):** Used in CPU-only/Lite environments.

## Architecture

### 1. The Problem
*   Vector search (Cosine Similarity) is fast but lacks deep semantic understanding (context blindness).
*   Dedicated Rerankers (Cross-Encoders) are accurate but computationally heavy and require large docker images.

### 2. The Solution: Adaptive Strategy Pattern
The system will detect available resources (Config/Env) and inject the appropriate `RerankingStrategy`.

#### Strategy A: Generative Reranking (GPU/LLM Present)
*   **Mechanism:** Listwise Reranking via LLM Prompting.
*   **Flow:**
    1.  Retrieve Top-N (e.g., 20) results from Vector Store.
    2.  Construct a prompt: *"Rank these snippets by relevance to query '{query}'. Return JSON."*
    3.  Send to the **existing** Local LLM (Ollama/vLLM) sharing the VRAM.
*   **Pros:** High accuracy, zero added memory footprint (reuses loaded model).
*   **Cons:** Higher latency than BERT, context window usage.

#### Strategy B: Math Reranking (CPU / Lite)
*   **Mechanism:** Algorithmic refinement of vector results.
*   **Components:**
    *   **MMR (Maximal Marginal Relevance):** Balances relevance (vector score) with diversity. penalizes redundancy.
        *   `Score = lambda * Sim(q, d) - (1 - lambda) * max(Sim(d, selected))`
    *   **Keyword Boosting (BM25-lite):** Simple exact-match boosting for critical keywords found in the query.
*   **Pros:** Extremely fast, runs on CPU, no extra dependencies.
*   **Cons:** Lower semantic understanding than LLM.

## Implementation Plan
1.  **Interface:** `RerankerStrategy` (Abstract Base Class).
2.  **Implementations:**
    *   `LlmRerankerStrategy`: Uses `LLMService` to rank.
    *   `MathRerankerStrategy`: Uses `numpy` / `sklearn` for MMR.
3.  **Factory:** `RerankerFactory` decides based on `RAE_RERANKER_MODE` (auto/llm/math).
