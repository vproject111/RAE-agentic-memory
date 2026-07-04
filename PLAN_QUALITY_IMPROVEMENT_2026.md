# RAE Quality Improvement Plan (2026-01-15)

## 📊 Performance Baseline
- **Scale:** 10,000 memories (Industrial Extreme)
- **Current MRR:** 0.4932
- **Current Hit Rate @5:** 53.5%
- **Insertion Latency:** 214ms (Node3 CPU)
- **Query Latency:** 150ms

## 🚀 Improvement Phases

### Phase 1: Infrastructure Stabilization (Critical)
- [ ] **Database Migration:** Restore missing `compute_nodes` table to unblock task delegation.
- [ ] **Compute Offloading:** Move embedding generation from Node3 (CPU) to Node1 (RTX 4080 GPU) via ML-Service.
- [ ] **Model Upgrade:** Switch from `nomic-embed-text` to `bge-m3` or `stella` for higher retrieval precision.

### Phase 2: Semantic & Reflective Layer Optimization
- [ ] **Consolidation Cycle:** Trigger a full reflection cycle on the 10k dataset to generate high-level semantic insights.
- [ ] **Threshold Calibration:** Tune `RAE_SIMILARITY_THRESHOLD` based on extreme benchmark results (Target: ~0.4 - 0.45).
- [ ] **Graph Enrichment:** Enhance triple extraction during memory insertion to build a denser Knowledge Graph.

### Phase 3: Hybrid Reranking Implementation
- [ ] **SmartReranker:** Enable the hybrid reranking strategy (Math + LLM).
- [ ] **Fast Scoring:** Use Math-1 structural metrics to pre-rank results before LLM verification.
- [ ] **Context Windowing:** Optimize memory retrieval to provide better context for the Reranker.

### Phase 4: UI/UX & Visibility
- [ ] **Dashboard Pagination:** Implement lazy loading/pagination for "Recent Activity" to handle datasets > 10k memories.
- [ ] **Real-time Monitoring:** Stabilize WebSocket connection for live quality metric updates.

## 🎯 Target Metrics
- **MRR:** > 0.80
- **Hit Rate @5:** > 90%
- **Query Time:** < 100ms
