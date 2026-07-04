# RAE Compliance Framework

**4-Layer Compliance Architecture**

This directory implements a modular, jurisdiction-agnostic compliance framework for RAE based on the 4-layer architecture described in `RAE-security-Architektura-4-warstwy-zgodnosci.md`.

## 🏗️ Architecture Overview

RAE's compliance framework is designed to be:
- **Modular**: Policy packs can be enabled/disabled per deployment
- **Jurisdiction-agnostic**: Support for multiple regulatory frameworks
- **Auditable**: Full transparency for compliance audits
- **Open source**: Policy packs are public for community review

## 📚 The 4 Layers

### Layer 1: Foundation (ISO 42001)
**Location:** `layer-1-foundation/`

The foundational governance layer based on ISO 42001 (AI Management System).

**Key elements:**
- Risk management framework
- Human-in-the-loop (HIL) workflows
- Audit trail and logging
- Access controls
- Model lifecycle management

**Status:** ✅ Implemented (see `docs/reference/iso-security/`)

This layer serves as the meta-governance foundation that all other compliance modules build upon.

### Layer 2: Mapping (Regulation Compatibility)
**Location:** `layer-2-mapping/`

Documentation mapping ISO 42001 controls to other regulatory frameworks.

**Mappings:**
- ISO 42001 → NIST AI RMF
- ISO 42001 → HIPAA
- ISO 42001 → FedRAMP
- ISO 42001 → GDPR
- ISO 42001 → EU AI Act
- ISO 42001 → ISO 27001/27701

**Purpose:** Shows how RAE's ISO 42001 implementation satisfies requirements of other frameworks.

**Status:** 🔄 In progress (documentation-only, no code impact)

### Layer 3: Compliance Modules (Policy Packs)
**Location:** `layer-3-modules/`

Concrete, runtime-enforceable policy packs for specific regulations.

**Available modules:**
- **HIPAA**: PHI protection, audit logs, encryption
- **NIST AI RMF**: Govern, Map, Measure, Manage
- **FedRAMP**: Moderate/High baseline controls
- **GDPR**: Data protection and privacy
- **AI Act**: Risk classification and requirements
- **ISO 27001**: Information security controls

**Structure per module:**
```
module-name/
├── policy-pack.yaml      # Declarative policy definition
├── implementation.md     # Implementation guide
├── tests/                # Compliance tests
└── README.md            # Module overview
```

**Status:** 🔄 In progress (templates and frameworks)

### Layer 4: Enforcement (Policy Engine)
**Location:** `layer-4-enforcement/`

Runtime enforcement mechanisms that ensure policies are followed.

**Components:**
- **Guardrails**: Input/output validators
- **Cost controllers**: Budget and spend limits
- **Risk controllers**: Risk-based throttling

**Integration:** These connect to RAE's existing policy engine (`apps/memory_api/services/policy_engine.py`).

**Status:** ✅ Partially implemented (core engine exists, compliance integration pending)

## 🔄 How It Works

1. **RAE Core** remains jurisdiction-agnostic
2. **Policy packs** are loaded at runtime based on configuration
3. **Policy engine** enforces rules during request processing
4. **Audit logs** record all compliance-relevant events

Example configuration:
```yaml
compliance:
  enabled_modules:
    - iso42001.core
    - nist_ai_rmf.baseline
    - hipaa.data_handling
  enforcement_level: strict
```

## 📁 Directory Structure

```
compliance/
├── README.md                    # This file
├── layer-1-foundation/
│   └── iso-42001/              # ISO 42001 implementation
├── layer-2-mapping/            # Regulatory mappings
│   ├── iso42001-to-nist.md
│   ├── iso42001-to-hipaa.md
│   └── ...
├── layer-3-modules/            # Policy packs
│   ├── hipaa/
│   ├── nist-ai-rmf/
│   ├── fedramp/
│   ├── gdpr/
│   ├── ai-act/
│   └── iso-27001/
├── layer-4-enforcement/        # Runtime enforcement
│   ├── guardrails/
│   ├── cost-controllers/
│   └── risk-controllers/
└── certifications/             # Certification artifacts
    └── audit-reports/
```

## 🎯 Certification Readiness

### Current Status:
- ✅ **ISO 42001**: 100% compliant (full implementation + tests)
- 🔄 **NIST AI RMF**: Mapping complete, formal attestation pending
- 🔄 **HIPAA**: Policy pack in development
- 🔄 **FedRAMP**: Controls mapping in progress
- 🔄 **GDPR**: PII scrubbing implemented, full assessment pending
- 🔄 **AI Act**: Risk classification framework ready

### Certification Artifacts:
See `certifications/` directory for:
- Audit reports
- Compliance matrices
- Test results
- Attestation documents

## 🚀 Usage

### For Developers:
1. Read Layer 1 (ISO 42001) to understand the foundation
2. Review Layer 2 mappings for your target jurisdiction
3. Enable relevant Layer 3 modules in configuration
4. Layer 4 enforcement is automatic

### For Auditors:
1. All policy packs are open source (transparency)
2. Test suites provide evidence of compliance
3. Audit logs are immutable and comprehensive
4. Mappings show how controls relate across frameworks

### For Compliance Officers:
1. Use Layer 2 mappings to understand coverage
2. Run compliance test suites: `pytest -m <standard>`
3. Generate reports: `python scripts/generate_compliance_report.py`
4. Review audit logs in `certifications/audit-reports/`

## 🔐 Security & Privacy

- **PII Scrubbing**: Automatic PII detection and redaction (Presidio-based)
- **Encryption**: Data at rest (AES-256), in transit (TLS 1.3)
- **Access Controls**: RBAC with tenant isolation (RLS)
- **Audit Logs**: Immutable logs in `access_logs` table

## 📚 Related Documentation

- **ISO 42001 Implementation**: `docs/reference/iso-security/`
- **Security Architecture**: `docs/security/`
- **Testing Policy**: `docs/AGENTS_TEST_POLICY.md`
- **4-Layer Architecture Plan**: `docs/RAE-security-Architektura-4-warstwy-zgodnosci.md`

## 🤝 Contributing

Policy packs are open source. To contribute:
1. Fork the repository
2. Add/modify policy pack in `layer-3-modules/`
3. Write tests in `tests/` subdirectory
4. Submit PR with evidence of testing

## 📄 License

- **Policy packs**: MIT License (open source)
- **RAE Core**: See project LICENSE
- **Enterprise features**: See commercial licensing

---

**Last Updated:** 2025-12-03
**Status:** 🔄 In active development
**Maintainer:** RAE Team
