# RAE Scientific Experiment: Calibration Impact Study (Final Results)
**Date:** 2026-01-04
**Node:** Node1 Lumina (Compute)
**Model:** Ollama / Nomic-embed-text (dim: 768)

## Executive Summary
This experiment confirms that Piotrek's calibration logic provides a **14.9% improvement in retrieval precision (MRR)** when using instruction-aware models like Nomic.

## Final Results (Node1 / Nomic)

| Metric | Phase 1 (Baseline) | Phase 2 (Calibrated) | Delta |
|--------|-------------------|----------------------|-------|
| **MRR** | 0.5753 | **0.6613** | **+14.9%** |
| **Hit Rate @5** | 0.6022 | **0.6882** | **+14.3%** |
| **Avg Latency** | 142.58ms | 146.93ms | +3% |

## Interpretation
- **Without Calibration:** The Nomic model treats queries and documents as the same type of data, leading to suboptimal embedding clustering and lower precision (MRR 0.57).
- **With Calibration:** By prepending `search_query:` and `search_document:`, we guide the model's internal attention mechanism. This results in much tighter relevance mapping, pushing MRR to **0.66** on the challenging `industrial_large` dataset.
- **Latency Trade-off:** The 3% latency increase is negligible compared to the massive quality gain.

## Impact on RAE Layers
1. **Math-2 (SCS)**: The higher precision ensures that the Semantic Coherence Score is calculated based on truly relevant memories, making the "reasoning guardrail" more robust.
2. **Reflective Memory**: Higher retrieval quality leads to more accurate reflection synthesis, as the LLM receives less "noise" in the context window.
3. **Math-3 (Policy)**: The controller can now make more confident decisions about memory pruning and consolidation based on reliable retrieval scores.

## Final Status
**EXPERIMENT SUCCESSFUL.** Piotrek's calibration is now a permanent core feature of the RAE embedding pipeline.