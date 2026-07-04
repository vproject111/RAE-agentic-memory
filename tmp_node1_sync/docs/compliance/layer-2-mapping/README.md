# Layer 2: Regulation Compatibility Mapping

This layer provides documentation mapping ISO 42001 controls (Layer 1) to requirements of other regulatory frameworks.

## 🎯 Purpose

**Documentation-only layer** that shows how RAE's ISO 42001 implementation satisfies requirements of various jurisdictional regulations.

**Key principle:** ISO 42001 is a meta-framework. Most modern AI regulations align with ISO 42001 principles:
- Risk management
- Transparency and explainability
- Human oversight
- Accountability and audit trails
- Data governance

## 📚 Available Mappings

### `iso42001-to-nist.md`
**Target:** NIST AI Risk Management Framework (AI RMF 1.0)

Maps ISO 42001 controls to NIST AI RMF functions:
- **GOVERN**: Organizational structures and policies
- **MAP**: Context and categorization of AI risks
- **MEASURE**: Assessment and analysis of risks
- **MANAGE**: Prioritization and response to risks

**Status:** 🔄 In progress

### `iso42001-to-hipaa.md`
**Target:** Health Insurance Portability and Accountability Act

Maps ISO 42001 to HIPAA requirements for:
- PHI (Protected Health Information) handling
- Security Rule (45 CFR §164.3XX)
- Privacy Rule (45 CFR §164.5XX)
- Breach Notification Rule

**Status:** 🔄 In progress

### `iso42001-to-fedramp.md`
**Target:** Federal Risk and Authorization Management Program

Maps ISO 42001 to FedRAMP baselines:
- **Moderate Baseline**: NIST 800-53 controls
- **High Baseline**: Enhanced security requirements
- Continuous monitoring requirements

**Status:** 🔄 In progress

### `iso42001-to-gdpr.md`
**Target:** General Data Protection Regulation (EU)

Maps ISO 42001 to GDPR requirements:
- Data protection by design and default (Art. 25)
- Data Protection Impact Assessment (Art. 35)
- Records of processing activities (Art. 30)
- Right to explanation (Art. 13-15, 22)

**Status:** 🔄 In progress

### `iso42001-to-ai-act.md`
**Target:** EU AI Act (Regulation 2024/1689)

Maps ISO 42001 to AI Act requirements:
- Risk classification (Art. 6-7)
- High-risk AI system requirements (Art. 8-15)
- Transparency obligations (Art. 13, 50)
- Human oversight (Art. 14)
- Quality management system (Art. 17)

**Status:** 🔄 In progress

### `iso42001-to-iso27001.md`
**Target:** ISO/IEC 27001:2022 (Information Security)

Maps ISO 42001 to ISO 27001 controls:
- Annex A controls mapping
- ISMS integration points
- Risk assessment alignment

**Status:** 🔄 In progress

## 📊 Mapping Format

Each mapping document follows this structure:

```markdown
# ISO 42001 to [Framework] Mapping

## Overview
Brief description of the target framework and its relevance to RAE.

## Control Mapping Table

| ISO 42001 Control | [Framework] Requirement | RAE Implementation | Evidence |
|-------------------|------------------------|-------------------|----------|
| ... | ... | ... | ... |

## Implementation Notes
Details on how RAE satisfies each requirement.

## Gaps & Roadmap
Any gaps in coverage and plans to address them.

## Testing
How to verify compliance.
```

## 🎯 How to Use These Mappings

### For Compliance Officers:
1. Identify your target regulatory framework
2. Review the mapping document
3. Check implementation status in "RAE Implementation" column
4. Gather evidence from "Evidence" column for audits

### For Auditors:
1. Use mappings to understand control coverage
2. Cross-reference with Layer 1 (ISO 42001) implementation
3. Verify evidence in Layer 3 (compliance tests)
4. Review audit logs in `certifications/audit-reports/`

### For Developers:
1. Understand which ISO 42001 controls support your target regulation
2. Ensure new features don't violate mapped requirements
3. Add tests to Layer 3 modules when implementing new controls

## 🔗 Relationship to Other Layers

```
Layer 1 (ISO 42001)
    ↓ maps to
Layer 2 (Mappings) ← YOU ARE HERE
    ↓ informs
Layer 3 (Policy Packs)
    ↓ enforced by
Layer 4 (Policy Engine)
```

**Layer 2 is documentation-only.** It doesn't contain code or runtime artifacts.

**Purpose:** Show that RAE's ISO 42001 implementation already satisfies multiple frameworks.

## 📈 Coverage Dashboard

| Framework | Coverage | Status |
|-----------|----------|--------|
| NIST AI RMF | ~90% | 🔄 Mapping complete, attestation pending |
| HIPAA | ~85% | 🔄 PHI handling implemented, audit pending |
| FedRAMP | ~80% | 🔄 Moderate baseline mapped |
| GDPR | ~90% | 🔄 PII scrubbing done, DPIA pending |
| EU AI Act | ~70% | 🔄 Risk classification ready |
| ISO 27001 | ~95% | 🔄 ISMS controls implemented |

**Note:** Percentages are estimates based on control mapping. Formal certification requires independent audit.

## 🚀 Adding New Mappings

To add a new regulatory framework mapping:

1. Create `iso42001-to-[framework].md` in this directory
2. Use the mapping format template above
3. Map each relevant ISO 42001 control to framework requirements
4. Identify implementation in RAE
5. Link to evidence (tests, logs, documentation)
6. Submit PR for review

## 📚 Related Documentation

- **Layer 1 (Foundation)**: `docs/compliance/layer-1-foundation/`
- **Layer 3 (Policy Packs)**: `docs/compliance/layer-3-modules/`
- **ISO 42001 Implementation**: `docs/reference/iso-security/`
- **4-Layer Architecture**: `docs/RAE-security-Architektura-4-warstwy-zgodnosci.md`

---

**Status:** 🔄 In progress (documentation-only)
**Last Updated:** 2025-12-03
**Maintainer:** RAE Compliance Team
