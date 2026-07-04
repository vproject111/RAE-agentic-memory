# HIPAA Compliance Module

**Target:** US Healthcare organizations handling Protected Health Information (PHI)
**Regulation:** Health Insurance Portability and Accountability Act (HIPAA)
**Status:** 🔄 In Development
**Version:** 0.1.0 (Draft)

## Overview

This policy pack implements HIPAA compliance controls for RAE deployments in US healthcare environments.

**Key Requirements:**
- Privacy Rule (45 CFR §164.5XX)
- Security Rule (45 CFR §164.3XX)
- Breach Notification Rule (45 CFR §164.4XX)
- HITECH Act enforcement

## HIPAA Compliance Framework

### 1. Protected Health Information (PHI)

**Definition:** Any information that can identify a patient and relates to:
- Past, present, or future physical/mental health
- Provision of healthcare
- Payment for healthcare

**PHI Identifiers (18 types):**
1. Names
2. Geographic subdivisions smaller than state
3. Dates (except year)
4. Phone numbers
5. Fax numbers
6. Email addresses
7. Social Security Numbers
8. Medical Record Numbers
9. Health Plan Numbers
10. Account numbers
11. Certificate/license numbers
12. Vehicle identifiers
13. Device IDs
14. URLs
15. IP addresses
16. Biometric identifiers
17. Full-face photos
18. Any other unique identifier

### 2. HIPAA Security Rule Requirements

| Requirement | RAE Implementation | Status |
|-------------|-------------------|--------|
| **Administrative Safeguards** | | |
| Security Management Process | Risk register, policy versioning | ✅ |
| Workforce Security | RBAC with RLS | ✅ |
| Information Access Management | Tenant isolation, minimum necessary | ✅ |
| Security Awareness Training | Documentation | 📝 |
| Security Incident Procedures | Incident response plan | ✅ |
| **Physical Safeguards** | | |
| Facility Access Controls | Deployment-specific | N/A (SaaS) |
| Workstation Security | Deployment-specific | N/A (SaaS) |
| Device and Media Controls | Encryption at rest | ✅ |
| **Technical Safeguards** | | |
| Access Control | Authentication, authorization | ✅ |
| Audit Controls | Immutable audit logs | ✅ |
| Integrity | Checksums, version control | ✅ |
| Transmission Security | TLS 1.3 | ✅ |

## Policy Pack Configuration

### `policy-pack.yaml`

```yaml
name: hipaa-phi-handling
version: "0.1.0"
description: "HIPAA compliance for Protected Health Information"
jurisdiction: "US"
standard: "HIPAA"
enabled: true

# Guardrails for PHI detection and handling
guardrails:
  # Input validation: Detect PHI before storage
  - name: phi_detection
    type: input_validator
    enabled: true
    action: scrub  # Options: scrub, reject, flag
    patterns:
      - name: ssn
        regex: '\b\d{3}-\d{2}-\d{4}\b'
        replacement: '[SSN-REDACTED]'

      - name: mrn
        regex: '\b(?:MRN|Medical Record)[:\s#-]*\d{6,}\b'
        replacement: '[MRN-REDACTED]'

      - name: phone
        regex: '\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'
        replacement: '[PHONE-REDACTED]'

      - name: email
        regex: '\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        replacement: '[EMAIL-REDACTED]'

  # Output validation: Prevent PHI leakage
  - name: phi_leakage_prevention
    type: output_validator
    enabled: true
    action: scrub
    patterns: # Same patterns as input

  # Encryption enforcement
  - name: encryption_enforcement
    type: storage_validator
    enabled: true
    action: enforce
    requirements:
      at_rest: AES-256-GCM
      in_transit: TLS-1.3
      key_management: FIPS-140-2

# Audit logging requirements
audit:
  enabled: true
  log_level: detailed  # minimal | standard | detailed
  retention_days: 2555  # 7 years per HIPAA
  immutable: true
  fields:
    - timestamp
    - user_id
    - tenant_id
    - operation
    - resource_id
    - resource_type
    - ip_address
    - user_agent
    - phi_accessed: true

# Access controls
access:
  minimum_necessary: true  # Enforce minimum necessary principle
  role_based: true
  mfa_required: true
  session_timeout_minutes: 15
  automatic_logout: true

# Breach notification
breach:
  enabled: true
  notification_threshold: 1  # Notify after any PHI access
  notification_methods:
    - email
    - dashboard_alert
  escalation_hours: 24  # Escalate if not addressed

# Business Associate Agreement (BAA)
baa:
  required: true
  template_path: "docs/compliance/layer-3-modules/hipaa/BAA-template.md"
```

## Implementation

### 1. PHI Detection (Presidio-based)

```python
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

class HIPAAPHIDetector:
    def __init__(self):
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()

        # HIPAA-specific recognizers
        self.phi_types = [
            "PERSON",
            "PHONE_NUMBER",
            "EMAIL_ADDRESS",
            "US_SSN",
            "MEDICAL_LICENSE",
            "DATE_TIME",
            "LOCATION",
            "IP_ADDRESS",
            "CREDIT_CARD",
        ]

    def detect_phi(self, text: str) -> List[RecognizerResult]:
        """Detect PHI in text."""
        results = self.analyzer.analyze(
            text=text,
            entities=self.phi_types,
            language="en"
        )
        return results

    def anonymize_phi(self, text: str) -> str:
        """Anonymize detected PHI."""
        results = self.detect_phi(text)
        anonymized = self.anonymizer.anonymize(
            text=text,
            analyzer_results=results
        )
        return anonymized.text
```

### 2. Audit Logging

```python
class HIPAAAuditLogger:
    async def log_phi_access(
        self,
        user_id: str,
        tenant_id: str,
        operation: str,
        resource_id: str,
        phi_accessed: bool = False,
    ):
        """Log PHI access per HIPAA requirements."""
        await db.execute(
            """
            INSERT INTO hipaa_audit_logs (
                timestamp, user_id, tenant_id, operation,
                resource_id, phi_accessed, ip_address, user_agent
            ) VALUES (
                NOW(), $1, $2, $3, $4, $5, $6, $7
            )
            """,
            user_id, tenant_id, operation, resource_id,
            phi_accessed, request.client.host, request.headers.get("user-agent")
        )
```

### 3. Minimum Necessary Principle

```python
class MinimumNecessaryEnforcement:
    def filter_phi(self, data: dict, user_role: str) -> dict:
        """Return only PHI necessary for user's role."""
        phi_fields = ["ssn", "dob", "address", "medical_history"]

        # Role-based field access
        allowed_fields = {
            "physician": phi_fields,  # Full access
            "nurse": ["dob", "medical_history"],  # Partial
            "billing": ["ssn", "address"],  # Billing only
            "researcher": [],  # No PHI
        }

        fields = allowed_fields.get(user_role, [])

        # Filter data
        filtered = {k: v for k, v in data.items() if k not in phi_fields or k in fields}
        return filtered
```

## Testing

### Unit Tests

```bash
# Test PHI detection
pytest apps/memory_api/tests/test_hipaa_phi_detection.py

# Test audit logging
pytest apps/memory_api/tests/test_hipaa_audit.py

# Test minimum necessary
pytest apps/memory_api/tests/test_hipaa_minimum_necessary.py
```

### Integration Tests

```bash
# Full HIPAA compliance test
pytest -m hipaa
```

### Mock PHI Dataset

**DO NOT use real PHI in tests.** Use synthetic data:

```python
MOCK_PHI = {
    "name": "John Doe",
    "ssn": "123-45-6789",
    "mrn": "MRN-123456",
    "dob": "1980-01-15",
    "phone": "555-123-4567",
    "diagnosis": "Type 2 Diabetes",
}
```

## Deployment

### Configuration

```bash
# Enable HIPAA module
RAE_COMPLIANCE_MODULES=iso42001.core,hipaa.phi_handling

# Set enforcement level
RAE_COMPLIANCE_ENFORCEMENT=strict

# Enable PHI scrubbing
HIPAA_PHI_SCRUBBING=true
HIPAA_PHI_ACTION=scrub  # scrub | reject | flag
```

### BAA Requirements

Before deploying RAE in healthcare environment:
1. Execute Business Associate Agreement (BAA)
2. Complete HIPAA Security Risk Assessment
3. Train workforce on HIPAA policies
4. Enable audit logging
5. Configure encryption (at rest + in transit)

## Breach Notification

Per 45 CFR §164.404, notify within **60 days** of breach discovery.

**RAE Breach Detection:**
- Automated PHI access monitoring
- Alerting on suspicious patterns
- Dashboard for compliance officers

**Notification Process:**
1. Detect breach (automated)
2. Assess scope (manual)
3. Notify affected individuals (email)
4. Notify HHS (if >500 individuals)
5. Document incident

## Related Documentation

- **ISO 42001 Mapping**: `docs/compliance/layer-2-mapping/iso42001-to-hipaa.md`
- **PII Scrubber**: `apps/memory_api/observability/pii_scrubber.py`
- **Audit Logs**: Database `access_logs` table
- **HIPAA Security Rule**: https://www.hhs.gov/hipaa/for-professionals/security/

---

**Status:** 🔄 In Development
**Target Release:** Q1 2025
**Maintainer:** RAE Compliance Team
