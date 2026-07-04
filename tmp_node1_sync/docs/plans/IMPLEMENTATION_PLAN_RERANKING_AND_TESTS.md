# Implementation Plan: Reranking & Testing

## Phase 1: Test Profiles (Immediate)
- [ ] Define Markers in `pytest.ini`.
- [ ] Update `Makefile` with `test-lite`, `test-int`, `test-gpu`.
- [ ] Tag existing tests with appropriate markers.

## Phase 2: Hybrid Reranker (Core)
- [ ] Define `RerankerStrategy` Interface in `apps/memory_api/services/reranking/base.py`.
- [ ] Implement `MathRerankerStrategy` (MMR + Keyword Boost).
- [ ] Implement `LlmRerankerStrategy` (Listwise Prompting).
- [ ] Create `RerankerFactory` in `apps/memory_api/services/reranking/factory.py`.

## Phase 3: Integration
- [ ] Update `SmartReranker` service to use the Factory.
- [ ] Configure `config.py` with `RAE_RERANKER_MODE`.
- [ ] Verify behavior in `LITE` vs `FULL_GPU` modes.
