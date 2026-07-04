# ISO 42001 to NIST AI RMF Mapping

**Target Framework:** NIST AI Risk Management Framework (AI RMF 1.0)
**Last Updated:** 2025-12-03
**Status:** 🔄 In Progress

## Overview

NIST AI RMF provides a structured approach to AI risk management through four core functions: GOVERN, MAP, MEASURE, and MANAGE. This document maps RAE's ISO 42001 implementation to NIST AI RMF requirements.

**Key alignment:** ISO 42001's governance framework naturally aligns with NIST AI RMF's risk-based approach.

## Control Mapping

| NIST Function | NIST Subcategory | ISO 42001 Control | RAE Implementation | Evidence |
|---------------|------------------|-------------------|-------------------|----------|
| **GOVERN** | | | | |
| GOVERN-1.1 | Legal and regulatory requirements mapped | ISO 42001: 4.2 | Multi-jurisdictional compliance framework | `docs/compliance/layer-2-mapping/` |
| GOVERN-1.2 | Roles and responsibilities defined | ISO 42001: 5.3 | RBAC system with tenant isolation | `docs/compliance/layer-1-foundation/iso-42001/RAE-Roles.md` |
| GOVERN-1.3 | AI governance policies | ISO 42001: 5.2 | Policy versioning service | `PolicyVersioningService` |
| GOVERN-1.4 | Risk management framework | ISO 42001: 6.1 | Risk register and mitigation | `docs/compliance/layer-1-foundation/iso-42001/RAE-Risk-Register.md` |
| **MAP** | | | | |
| MAP-1.1 | AI system context documented | ISO 42001: 4.1 | Tenant configuration and metadata | `ContextProvenanceService` |
| MAP-1.2 | AI capabilities and limitations | ISO 42001: 8.2 | LLM profiles and cost controller | `apps/memory_api/services/cost_controller_v2.py` |
| MAP-2.1 | Risks and impacts categorized | ISO 42001: 6.1.2 | Risk classification (Low/Med/High/Critical) | `RiskController`, `HumanApprovalService` |
| MAP-3.1 | Transparency requirements | ISO 42001: 8.3 | Decision provenance tracking | `ContextProvenanceService` |
| **MEASURE** | | | | |
| MEASURE-1.1 | Performance metrics | ISO 42001: 9.1 | Analytics and metrics service | `AnalyticsService`, `MetricsRepository` |
| MEASURE-2.1 | Testing and validation | ISO 42001: 8.5 | Comprehensive test suite (82 ISO tests) | `apps/memory_api/tests/test_iso42001_*.py` |
| MEASURE-2.2 | Bias and fairness | ISO 42001: 6.1.3 | Planned (Layer 3 module) | 🔄 Roadmap |
| MEASURE-3.1 | Model monitoring | ISO 42001: 9.2 | Cost logs, access logs | `CostLogsRepository`, `access_logs` table |
| **MANAGE** | | | | |
| MANAGE-1.1 | Risk response documented | ISO 42001: 6.1.4 | Risk mitigation strategies | `CircuitBreaker`, `DegradedModeService` |
| MANAGE-1.2 | Human oversight | ISO 42001: 8.4 | HIL approval workflows | `HumanApprovalService` |
| MANAGE-2.1 | Incident response | ISO 42001: 10.2 | Incident response procedures | `docs/operations/security-policies/` |
| MANAGE-3.1 | Continuous improvement | ISO 42001: 10.3 | Reflection engine, policy iteration | `ReflectionPipelineService` |

## Implementation Notes

### GOVERN Function

RAE's ISO 42001 foundation provides comprehensive governance:
- **Legal/Regulatory**: Modular compliance via Layer 3 policy packs
- **Roles**: RBAC with tenant isolation (RLS)
- **Policies**: Versioned, auditable, rollback-capable
- **Risk Management**: Proactive risk identification and mitigation

**Status:** ✅ Fully Implemented

### MAP Function

Context and risk mapping are core RAE capabilities:
- **System Context**: Full provenance tracking for all decisions
- **Capabilities**: Well-documented LLM profiles with cost models
- **Risk Categorization**: 4-level classification (Low/Med/High/Critical)
- **Transparency**: Complete audit trails

**Status:** ✅ Fully Implemented

### MEASURE Function

Comprehensive measurement and monitoring:
- **Performance**: Real-time metrics and analytics
- **Testing**: 82 ISO 42001 tests + integration tests
- **Bias**: Planned for NIST AI RMF policy pack (Layer 3)
- **Monitoring**: Cost logs, access logs, decision logs

**Status:** ⚠️ Partially Implemented (bias testing pending)

### MANAGE Function

Risk management and continuous improvement:
- **Risk Response**: Circuit breakers, graceful degradation
- **Human Oversight**: Multi-level approval workflows
- **Incident Response**: Documented procedures
- **Improvement**: Reflection engine enables continuous learning

**Status:** ✅ Fully Implemented

## Coverage Summary

| NIST Function | Coverage | Notes |
|---------------|----------|-------|
| GOVERN | 100% | Full ISO 42001 governance |
| MAP | 100% | Complete context and risk mapping |
| MEASURE | 90% | Bias testing planned |
| MANAGE | 100% | Full risk management lifecycle |

**Overall:** ~97% coverage

## Gaps & Roadmap

### Current Gaps

1. **Bias and Fairness Testing (MEASURE-2.2)**
   - **Gap:** No automated bias detection in LLM outputs
   - **Plan:** Add bias detection to NIST AI RMF policy pack (Layer 3)
   - **Timeline:** Q1 2025

2. **Formal NIST Assessment**
   - **Gap:** No independent NIST AI RMF assessment
   - **Plan:** Engage with NIST-certified assessor
   - **Timeline:** Q2 2025

### Enhancement Opportunities

- **Enhanced transparency**: Add explainability for LLM decisions
- **Adversarial testing**: Add red-team testing framework
- **Stakeholder engagement**: Formalize feedback mechanisms

## Testing

### Unit Tests

```bash
# Run NIST-related tests
pytest -m nist
```

### Compliance Verification

```bash
# Generate NIST compliance report
python scripts/generate_compliance_report.py --standard nist --output docs/.auto-generated/compliance/nist-coverage.md
```

### Evidence Collection

All NIST AI RMF evidence is available in:
- ISO 42001 test results
- Audit logs (`access_logs`, `cost_logs` tables)
- Policy documentation (`docs/compliance/`)
- System documentation (`docs/reference/`)

## Related Documentation

- **ISO 42001 Foundation**: `docs/compliance/layer-1-foundation/`
- **NIST Policy Pack**: `docs/compliance/layer-3-modules/nist-ai-rmf/`
- **Risk Register**: `docs/compliance/layer-1-foundation/iso-42001/RAE-Risk-Register.md`
- **NIST AI RMF 1.0**: https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf

---

**Status:** 🔄 Mapping complete, formal assessment pending
**Maintained by:** RAE Compliance Team
**Next Review:** 2025-03-01
