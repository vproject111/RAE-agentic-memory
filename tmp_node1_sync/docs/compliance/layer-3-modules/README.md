# Layer 3: Compliance Modules (Policy Packs)

This layer contains concrete, runtime-enforceable policy packs for specific regulatory frameworks.

## 🎯 Purpose

Policy packs are **modular, pluggable compliance implementations** that can be enabled/disabled per deployment based on jurisdiction and use case.

**Key principle:** RAE core remains jurisdiction-agnostic. Compliance is a plugin, not hardcoded.

## 📦 Available Policy Packs

### HIPAA (Health Insurance Portability and Accountability Act)
**Location:** `hipaa/`
**Target:** US healthcare organizations

**Enforces:**
- PHI (Protected Health Information) detection and anonymization
- Audit logging for all PHI access
- Encryption requirements (AES-256 at rest, TLS 1.3 in transit)
- Access controls and minimum necessary principle
- Breach notification requirements

**Status:** 🔄 In development

---

### NIST AI RMF (AI Risk Management Framework)
**Location:** `nist-ai-rmf/`
**Target:** US federal agencies and organizations following NIST guidance

**Enforces:**
- **GOVERN**: Policy documentation, roles, risk management
- **MAP**: AI risk categorization and context
- **MEASURE**: Metrics collection, bias testing
- **MANAGE**: Risk mitigation, incident response

**Status:** 🔄 In development

---

### FedRAMP (Federal Risk and Authorization Management Program)
**Location:** `fedramp/`
**Target:** US federal government cloud services

**Enforces:**
- NIST 800-53 control implementation (Moderate/High baseline)
- Continuous monitoring requirements
- Incident reporting to FedRAMP PMO
- SSP (System Security Plan) artifacts

**Status:** 🔄 Planned

---

### GDPR (General Data Protection Regulation)
**Location:** `gdpr/`
**Target:** EU data protection compliance

**Enforces:**
- Data protection by design and default (Art. 25)
- Right to erasure (Art. 17)
- Data minimization principles
- DPIA (Data Protection Impact Assessment) triggers
- Consent management

**Status:** 🔄 In development

---

### EU AI Act
**Location:** `ai-act/`
**Target:** EU AI system providers and deployers

**Enforces:**
- Risk classification (unacceptable, high, limited, minimal)
- High-risk system requirements (Art. 8-15)
- Transparency obligations (Art. 13, 50)
- Human oversight mechanisms (Art. 14)
- Quality management system

**Status:** 🔄 Planned

---

### ISO 27001 (Information Security Management)
**Location:** `iso-27001/`
**Target:** Organizations seeking ISO 27001 certification

**Enforces:**
- Annex A control implementation
- Information security policy
- Asset management
- Access control policies
- Cryptographic controls

**Status:** 🔄 Planned

## 📂 Policy Pack Structure

Each policy pack follows this standard structure:

```
module-name/
├── README.md                # Overview and usage guide
├── policy-pack.yaml         # Declarative policy definition
├── implementation.md        # Technical implementation details
├── tests/                   # Compliance test suite
│   ├── test_*.py           # pytest tests
│   └── fixtures/           # Test data
└── docs/                    # Additional documentation
    ├── controls.md         # Control mapping
    └── evidence.md         # Audit evidence guide
```

### `policy-pack.yaml` Format

```yaml
name: hipaa-data-handling
version: "1.0.0"
description: "HIPAA compliance for PHI handling"
jurisdiction: "US"
standard: "HIPAA"

# Guardrails to enforce
guardrails:
  - name: phi_detection
    type: input_validator
    action: scrub
    patterns:
      - ssn
      - medical_record_number
      - health_plan_number

  - name: encryption_enforcement
    type: storage_validator
    action: enforce
    algorithms:
      at_rest: AES-256
      in_transit: TLS-1.3

# Audit requirements
audit:
  log_level: detailed
  retention_days: 2555  # 7 years per HIPAA
  immutable: true

# Access controls
access:
  minimum_necessary: true
  role_based: true
  mfa_required: true
```

## 🔌 How Policy Packs Work

### 1. Configuration (`.env` or deployment config)

```bash
# Enable specific policy packs
RAE_COMPLIANCE_MODULES=iso42001.core,nist_ai_rmf.baseline,hipaa.data_handling

# Enforcement level
RAE_COMPLIANCE_ENFORCEMENT=strict  # strict | permissive | audit-only
```

### 2. Runtime Loading

```python
# Policy engine loads modules at startup
from apps.memory_api.services.policy_engine import PolicyEngine

engine = PolicyEngine()
engine.load_modules([
    "iso42001.core",
    "nist_ai_rmf.baseline",
    "hipaa.data_handling"
])
```

### 3. Request Processing

```python
# Guardrails are applied to every request
async def process_memory_storage(content: str, metadata: dict):
    # Policy engine intercepts
    validated_content = await policy_engine.validate_input(content)
    validated_metadata = await policy_engine.validate_metadata(metadata)

    # Storage with compliance controls
    memory_id = await memory_repo.create(validated_content, validated_metadata)

    # Audit logging (automatic)
    await policy_engine.log_operation("memory.create", memory_id)

    return memory_id
```

## ✅ Testing Policy Packs

Each policy pack includes a test suite:

```bash
# Test specific module
pytest -m hipaa

# Test all compliance modules
pytest -m compliance

# Generate compliance report
python scripts/generate_compliance_report.py --standard hipaa
```

### Test Categories

- **Unit tests**: Individual control validation
- **Integration tests**: End-to-end policy enforcement
- **Regression tests**: Ensure updates don't break compliance
- **Negative tests**: Verify violations are caught

## 📊 Compliance Dashboard

View policy pack status:

```bash
# Check which modules are active
python scripts/compliance_status.py

# Output:
# ✅ ISO 42001 Core - Active (v1.0.0)
# ✅ NIST AI RMF Baseline - Active (v1.0.0)
# 🔄 HIPAA Data Handling - Loading...
# ⚪ FedRAMP Moderate - Disabled
```

## 🚀 Creating a New Policy Pack

1. **Create directory structure:**
   ```bash
   mkdir -p docs/compliance/layer-3-modules/my-regulation/{tests,docs}
   ```

2. **Define `policy-pack.yaml`:**
   - Specify guardrails
   - Define audit requirements
   - Set access controls

3. **Write implementation:**
   - Create `implementation.md`
   - Document technical approach
   - Link to code references

4. **Add tests:**
   - Create `tests/test_my_regulation.py`
   - Test all controls
   - Aim for 100% coverage

5. **Map controls:**
   - Create `docs/controls.md`
   - Map to Layer 2 (ISO 42001)
   - Identify any gaps

6. **Submit PR:**
   - All policy packs are open source
   - Community review encouraged
   - Maintainer approval required

## 🔐 Security & Privacy

Policy packs themselves are:
- **Open source**: MIT/Apache 2.0 license
- **Auditable**: Full transparency
- **Versioned**: Semantic versioning
- **Tested**: CI/CD enforced coverage

**Why open source?**
- Trust through transparency
- Community review improves quality
- Faster adoption in regulated industries
- Easier audit by compliance officers

## 📚 Related Documentation

- **Layer 1 (Foundation)**: `docs/compliance/layer-1-foundation/`
- **Layer 2 (Mapping)**: `docs/compliance/layer-2-mapping/`
- **Layer 4 (Enforcement)**: `docs/compliance/layer-4-enforcement/`
- **Policy Engine Code**: `apps/memory_api/services/policy_engine.py`
- **4-Layer Architecture**: `docs/RAE-security-Architektura-4-warstwy-zgodnosci.md`

## 🤝 Contributing

We welcome contributions:
- New policy packs for additional regulations
- Improvements to existing packs
- Test coverage enhancements
- Documentation updates

See `CONTRIBUTING.md` for guidelines.

---

**Status:** 🔄 Active development
**License:** MIT (policy packs are open source)
**Last Updated:** 2025-12-03
