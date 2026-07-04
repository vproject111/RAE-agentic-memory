# Changelog

## [3.7.0] - 2026-07-04

### ✨ Features
- **LLM Agnosticism**: Unified multi-model dynamic resolver runtime (`resolve_llm_runtime`) supporting OpenAI, Anthropic, Google, OpenRouter, and OpenCode across all modules (agentic-memory, quality, hive) in a standalone fashion.
- **Security**: Implemented Iteration 4 Security and Limiters: `SecretRedactor`, `CircuitBreaker`, and `StandaloneRateLimiter` to prevent API credential leakage and endless billing loops.
- **Governance**: Embedded Versioning Validator runtime contract to enforce strict Git Flow branch guards on module startup in development environments.
- **Integrations**: Consolidated and merged legacy RAE-Windows (Universal Node) and NiceGUI dashboard features from `release/v3.0.2` to prevent regressions.

## [3.6.1-LTS] - 2026-03-01

### ✨ Features
- **Core**: Release v3.6.1-LTS with full Quantum Logic implementation (L1-L3).
- **Security**: Implement **Hard Frames 2.1** with Full Decision Provenance and audit trails.
- **Errors**: Deploy **Oracle Error Protocol (OEP) v1.0** for autonomous incident logging.
- **Governance**: Establish **Global Contract Atlas v1.5** for domain-independent memory rules.
- **Infrastructure**: Enable persistent `pgvector` and unified Docker networking.

### 📚 Documentation
- **Architecture**: Expand memory model to 6-layer manifold and 3-tier reflective core.
- **Developer**: Add three methods for enabling Hard Frames (Global, Agent, Infrastructure).
- **Standards**: Operationalize AGENT_CORE_PROTOCOL and RAE_AGENTIC_CONTRACT.

### ♻️ Refactoring
- **Repository**: Modularize RAE-Suite into independent packages (Core, Hive, Phenix).
- **Clean-up**: Removed binary bloat and synchronized source parity between Node 1 and Laptop.

---

## [3.6.0] - 2026-02-08

### ✨ Features
- implement modern NiceGUI desktop interface for RAE-Lite
- implement System 22.1 Neural Scalpel retrieval pipeline
- **db**: Add FTS and performance indices; stabilize parallel retrieval core
- **math**: Implement System 6.5 Hybrid Resilience with Safe Early Exit and Semantic Resonance
- implement Logic-based Math Core (System 4.0) for radical stability
- universal infrastructure launcher, Qdrant auto-healing, and API V2 migration
- **windows**: update rae-lite to v3.5.0 and cleanup legacy windows dir

### 🐛 Bug Fixes
- cross-platform compatibility for RAE Windows and Lite

### 📚 Documentation
- **zenodo**: update metadata for v3.6.0 and add CITATION.cff
- add cluster sync scripts and update agent documentation

## [2026-02-20] - Industrial Analytics Attempt 1 (Heuristic)
### Challenges:
- Model hallucinations regarding machine counts.
- Brittle hardcoded filters.
### Pivot:
- Implementing Agentic Text-to-SQL for dynamic data exploration.

## [2026-03-02] - Industrial Analytics Attempt 2 (Text-to-SQL & Sanity Check)
### Accomplished:
- Implemented **Agentic Text-to-SQL**: Model now generates dynamic parameters (date, machine) instead of relying on brittle heuristic filters.
- **SQL Sanity Guard**: Added hard capping in SQL (value < 450 m2/h) to physically block OCR hallucinations.
- **Improved Grounding**: Enforced 2026 as the default year to prevent '2021' hallucinations.
### Challenges Identified:
- **Calculation Drift**: Simple SQL averages mismatch Grafana metrics because they ignore process 'nuances' (downtime vs work time, hash-based status).
- **Tooling Mismatch**: RAE needs the exact 'WITH RealtimeStatus' logic from Grafana to provide consistent business answers.
### Next Step:
- Synchronize  with Grafana's CTE-based SQL logic (Common Table Expressions) for Net Performance and Downtime calculation.

## [2026-03-02] - Model Selector and UI Overhaul
### Features Added:
- **Model Selector**: Added a dropdown in the Oracle UI to switch between models (Qwen 2.5 3B, Llama 3 8B, etc.).
- **API Model Support**: The `/procedural/query` endpoint now accepts a `model` parameter to route requests to specific LLM backends.
- **UI Refresh**: Modernized the Oracle UI with better layout, iconography, and OEE-specific labels.
### Technical Improvements:
- Stabilized volume mapping for UI code persistence.
- Implemented robust error handling for model switching on CPU (increased timeouts).
