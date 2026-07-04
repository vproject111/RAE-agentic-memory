# ISO/IEC 42001 Compliance API Guide

**Enterprise Feature** | **Version**: 2.2.0-enterprise

## Overview

The Compliance API implements **ISO/IEC 42001** requirements for AI Management Systems. It provides human oversight, decision traceability, fail-safe mechanisms, and policy enforcement—critical for enterprise AI deployments.

**ISO/IEC 42001 Coverage**:
- ✅ **Clause 6.1.2**: Risk assessment for AI operations
- ✅ **Clause 6.1.3**: Opportunity identification
- ✅ **Clause 8.2**: Human oversight and approval workflows
- ✅ **Clause 8.3**: AI system documentation (provenance)
- ✅ **Clause 9.1**: Performance monitoring (circuit breakers)
- ✅ **Clause 10.2**: Continual improvement (policy versioning)

**Key Features**:
- 👤 **Human-in-the-Loop**: Approval workflows for high-risk operations
- 📜 **Provenance Tracking**: Full decision lineage from query → context → output
- 🔌 **Circuit Breakers**: Fail-fast protection for dependencies
- 📋 **Policy Management**: Versioned, enforceable policies

---

## Quick Start

### 1. Request Approval for High-Risk Operation

```bash
curl -X POST http://localhost:8000/v1/compliance/approvals \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo" \
  -H "X-API-Key: your-key" \
  -d '{
    "tenant_id": "demo",
    "project_id": "my-app",
    "operation_type": "data_deletion",
    "operation_description": "Delete all user memories for GDPR request",
    "risk_level": "critical",
    "resource_type": "memory",
    "resource_id": "user_123_memories",
    "requested_by": "admin@example.com",
    "metadata": {
      "reason": "GDPR right to erasure",
      "ticket_id": "GDPR-2025-001"
    }
  }'
```

**Response**:
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "risk_level": "critical",
  "expires_at": "2025-12-07T10:00:00Z",
  "min_approvals": 2,
  "current_approvals": 0,
  "approvers": []
}
```

**Risk level** determines approval requirements:
- `none`, `low`: Auto-approved immediately
- `medium`: 1 approval, 24h timeout
- `high`: 1 approval, 48h timeout
- `critical`: 2 approvals, 72h timeout

### 2. Check Approval Status

```bash
curl http://localhost:8000/v1/compliance/approvals/550e8400-e29b-41d4-a716-446655440000 \
  -H "X-API-Key: your-key"
```

### 3. Approve the Request

```bash
curl -X POST http://localhost:8000/v1/compliance/approvals/550e8400-e29b-41d4-a716-446655440000/decide \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{
    "approver_id": "manager@example.com",
    "decision": "approved",
    "reason": "Verified GDPR request with legal team"
  }'
```

**Response**:
```json
{
  "request_id": "550e8400-...",
  "status": "pending",
  "risk_level": "critical",
  "min_approvals": 2,
  "current_approvals": 1,
  "approvers": ["manager@example.com"]
}
```

After 2nd approval, status becomes `"approved"` and operation can proceed.

---

## Human Approval Workflows

### Risk-Based Approval Requirements

| Risk Level | Min Approvals | Timeout | Auto-Approved |
|------------|---------------|---------|---------------|
| none | 0 | N/A | ✅ Yes |
| low | 0 | N/A | ✅ Yes |
| medium | 1 | 24 hours | ❌ No |
| high | 1 | 48 hours | ❌ No |
| critical | 2 | 72 hours | ❌ No |

### Operation Types

Common operation types requiring approval:

| Operation Type | Typical Risk Level | Example |
|----------------|-------------------|---------|
| `data_deletion` | critical | Delete user memories (GDPR) |
| `model_deployment` | high | Deploy new LLM to production |
| `policy_change` | high | Change retention policy |
| `bulk_export` | medium | Export memories to external system |
| `configuration_change` | medium | Change system configuration |
| `data_access` | low | Read non-sensitive data |

### Request Approval

```bash
curl -X POST http://localhost:8000/v1/compliance/approvals \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo" \
  -H "X-API-Key: your-key" \
  -d '{
    "tenant_id": "demo",
    "project_id": "my-app",
    "operation_type": "model_deployment",
    "operation_description": "Deploy GPT-4 to production environment",
    "risk_level": "high",
    "resource_type": "model",
    "resource_id": "gpt-4-deployment",
    "requested_by": "engineer@example.com",
    "required_approvers": ["manager@example.com", "director@example.com"],
    "metadata": {
      "model_version": "gpt-4-0125-preview",
      "deployment_environment": "production"
    }
  }'
```

**Fields**:
- `operation_type`: Category of operation
- `operation_description`: Human-readable description
- `risk_level`: none, low, medium, high, critical
- `resource_type`: What's being modified (memory, model, policy, etc.)
- `resource_id`: Identifier for the resource
- `requested_by`: Who requested the operation
- `required_approvers`: (Optional) Specific approvers required
- `metadata`: Additional context

### Check Status

```bash
curl http://localhost:8000/v1/compliance/approvals/{request_id} \
  -H "X-API-Key: your-key"
```

**Response Statuses**:
- `pending`: Awaiting approvals
- `approved`: All required approvals received
- `rejected`: Approval denied
- `expired`: Timeout reached without approval

### Approve or Reject

```bash
# Approve
curl -X POST http://localhost:8000/v1/compliance/approvals/{request_id}/decide \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{
    "approver_id": "manager@example.com",
    "decision": "approved",
    "reason": "Risk assessment completed. Deployment approved."
  }'

# Reject
curl -X POST http://localhost:8000/v1/compliance/approvals/{request_id}/decide \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{
    "approver_id": "manager@example.com",
    "decision": "rejected",
    "reason": "Model not sufficiently tested. Need more evaluation."
  }'
```

### Timeout Handling

If approval timeout expires:
1. Status changes to `"expired"`
2. Operation is automatically rejected
3. Audit log records expiration
4. Requester is notified (if configured)

---

## Context Provenance

Track full decision lineage: query → context → decision → output.

### Why Provenance?

**ISO/IEC 42001 Requirements**:
- Document AI system decisions
- Enable explainability and auditability
- Track data sources and quality
- Support regulatory compliance

**Use Cases**:
- Regulatory audits
- Debugging unexpected outputs
- Quality assurance
- Trust verification

### Create Context Record

Record the context used for a decision:

```bash
curl -X POST http://localhost:8000/v1/compliance/provenance/context \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo" \
  -H "X-API-Key: your-key" \
  -d '{
    "tenant_id": "demo",
    "project_id": "my-app",
    "query": "What are the user'\''s dietary preferences?",
    "sources": [
      {
        "source_type": "memory",
        "source_id": "mem-123",
        "content": "User prefers vegetarian meals",
        "relevance_score": 0.95,
        "timestamp": "2025-11-15T10:00:00Z",
        "trust_level": "verified",
        "metadata": {
          "layer": "episodic",
          "importance": 0.9
        }
      },
      {
        "source_type": "memory",
        "source_id": "mem-456",
        "content": "User allergic to nuts",
        "relevance_score": 0.88,
        "timestamp": "2025-10-20T14:30:00Z",
        "trust_level": "verified",
        "metadata": {
          "layer": "semantic",
          "importance": 0.95
        }
      }
    ]
  }'
```

**Response**:
```json
{
  "context_id": "660e8400-e29b-41d4-a716-446655440001",
  "tenant_id": "demo",
  "project_id": "my-app",
  "query": "What are the user's dietary preferences?",
  "sources_count": 2,
  "quality_metrics": {
    "avg_relevance": 0.915,
    "avg_trust": "verified",
    "coverage": 0.87,
    "recency_score": 0.92
  },
  "created_at": "2025-12-04T10:00:00Z"
}
```

**Source Types**:
- `memory`: From memory store
- `document`: From document index
- `external_api`: External service
- `knowledge_base`: Static knowledge base
- `cache`: Cached result

**Trust Levels**:
- `verified`: Manually verified, high trust
- `high`: System-verified, reliable
- `medium`: Standard quality
- `low`: Potentially unreliable
- `unverified`: Not verified

### Record Decision

Link decision to context:

```bash
curl -X POST http://localhost:8000/v1/compliance/provenance/decision \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo" \
  -H "X-API-Key: your-key" \
  -d '{
    "tenant_id": "demo",
    "project_id": "my-app",
    "decision_type": "recommendation",
    "decision_description": "Recommend vegetarian restaurant",
    "context_id": "660e8400-e29b-41d4-a716-446655440001",
    "output": "I recommend \"Green Garden\" - a vegetarian restaurant with nut-free options.",
    "confidence": 0.92,
    "model_name": "gpt-4-0125-preview",
    "human_approved": false,
    "metadata": {
      "temperature": 0.7,
      "max_tokens": 150,
      "execution_time_ms": 850
    }
  }'
```

**Response**:
```json
{
  "decision_id": "770e8400-e29b-41d4-a716-446655440002",
  "context_id": "660e8400-...",
  "decision_type": "recommendation",
  "confidence": 0.92,
  "created_at": "2025-12-04T10:00:05Z"
}
```

**Decision Types**:
- `classification`: Categorize input
- `recommendation`: Suggest action
- `generation`: Generate content
- `extraction`: Extract information
- `transformation`: Transform data

### Get Decision Lineage

Retrieve full provenance chain:

```bash
curl http://localhost:8000/v1/compliance/provenance/lineage/770e8400-e29b-41d4-a716-446655440002 \
  -H "X-API-Key: your-key"
```

**Response**:
```json
{
  "decision": {
    "decision_id": "770e8400-...",
    "decision_type": "recommendation",
    "output": "I recommend \"Green Garden\" - a vegetarian restaurant with nut-free options.",
    "confidence": 0.92,
    "model_name": "gpt-4-0125-preview",
    "human_approved": false,
    "created_at": "2025-12-04T10:00:05Z"
  },
  "context": {
    "context_id": "660e8400-...",
    "query": "What are the user's dietary preferences?",
    "sources_count": 2,
    "quality_metrics": {
      "avg_relevance": 0.915,
      "avg_trust": "verified"
    },
    "created_at": "2025-12-04T10:00:00Z"
  },
  "sources": [
    {
      "source_type": "memory",
      "source_id": "mem-123",
      "content": "User prefers vegetarian meals",
      "relevance_score": 0.95,
      "trust_level": "verified"
    },
    {
      "source_type": "memory",
      "source_id": "mem-456",
      "content": "User allergic to nuts",
      "relevance_score": 0.88,
      "trust_level": "verified"
    }
  ],
  "lineage_complete": true
}
```

---

## Circuit Breakers

Fail-fast protection for system dependencies.

### Why Circuit Breakers?

**ISO/IEC 42001 Requirement**: Monitor and manage AI system performance

**Benefits**:
- Prevent cascading failures
- Fast failure detection
- Automatic recovery
- System resilience

### Circuit Breaker States

```
CLOSED → OPEN → HALF_OPEN → CLOSED
  ↑                            ↓
  └────────────────────────────┘
```

- **CLOSED**: Normal operation, requests pass through
- **OPEN**: Failures exceeded threshold, requests blocked
- **HALF_OPEN**: Testing recovery, limited requests allowed

### Available Circuit Breakers

| Breaker Name | Protects | Threshold | Timeout |
|--------------|----------|-----------|---------|
| `database` | PostgreSQL | 5 failures | 60s |
| `vector_store` | Qdrant | 5 failures | 60s |
| `llm_service` | LLM API | 5 failures | 120s |
| `ml_service` | ML Service | 5 failures | 60s |
| `cache` | Redis | 5 failures | 30s |

### List All Circuit Breakers

```bash
curl http://localhost:8000/v1/compliance/circuit-breakers \
  -H "X-API-Key: your-key"
```

**Response**:
```json
[
  {
    "name": "database",
    "state": "CLOSED",
    "failure_threshold": 5,
    "recovery_timeout": 60,
    "metrics": {
      "total_calls": 1547,
      "successful_calls": 1542,
      "failed_calls": 5,
      "failure_rate": 0.003,
      "last_failure": null,
      "consecutive_failures": 0
    }
  },
  {
    "name": "vector_store",
    "state": "CLOSED",
    "failure_threshold": 5,
    "recovery_timeout": 60,
    "metrics": {
      "total_calls": 892,
      "successful_calls": 892,
      "failed_calls": 0,
      "failure_rate": 0.0,
      "last_failure": null,
      "consecutive_failures": 0
    }
  }
]
```

### Get Specific Circuit Breaker

```bash
curl http://localhost:8000/v1/compliance/circuit-breakers/database \
  -H "X-API-Key: your-key"
```

### Reset Circuit Breaker

Manually reset after fixing issues:

```bash
curl -X POST http://localhost:8000/v1/compliance/circuit-breakers/database/reset \
  -H "X-API-Key: your-key"
```

**Response**:
```json
{
  "name": "database",
  "state": "CLOSED",
  "message": "Circuit breaker reset successfully"
}
```

### Monitoring Circuit Breakers

**Set up alerts** when circuit breakers open:

```bash
# Using Event Triggers
curl -X POST http://localhost:8000/v1/triggers/create \
  -d '{
    "rule_name": "Circuit Breaker Alert",
    "event_types": ["circuit_breaker_opened"],
    "actions": [
      {
        "action_type": "webhook",
        "parameters": {
          "url": "https://api.pagerduty.com/incidents",
          "body": {
            "incident": {
              "type": "incident",
              "title": "Circuit Breaker ${payload.breaker_name} OPEN",
              "urgency": "high"
            }
          }
        }
      }
    ]
  }'
```

---

## Policy Management

Versioned, enforceable policies for governance.

### Why Policy Versioning?

**ISO/IEC 42001 Requirement**: Documented, versioned policies

**Benefits**:
- Track policy evolution
- Rollback capability
- Audit compliance
- Enforce rules consistently

### Policy Types

| Policy Type | Description | Example Rules |
|-------------|-------------|---------------|
| `data_retention` | How long to keep data | "Delete episodic memories after 90 days" |
| `access_control` | Who can access what | "Only admins can delete memories" |
| `quality_threshold` | Quality requirements | "Confidence must be >0.8 for auto-actions" |
| `rate_limiting` | Usage limits | "Max 100 queries/min per user" |
| `data_governance` | Data handling rules | "PII must be encrypted" |

### Create Policy

```bash
curl -X POST http://localhost:8000/v1/compliance/policies \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo" \
  -H "X-API-Key: your-key" \
  -d '{
    "tenant_id": "demo",
    "policy_id": "retention-policy",
    "policy_type": "data_retention",
    "policy_name": "Memory Retention Policy",
    "policy_description": "Standard retention for episodic memories",
    "rules": {
      "episodic_retention_days": 90,
      "semantic_retention_days": 365,
      "ltm_retention_days": null,
      "auto_delete_enabled": true,
      "exceptions": ["critical", "legal_hold"]
    },
    "created_by": "admin@example.com",
    "metadata": {
      "approved_by": "legal_team",
      "effective_date": "2025-01-01"
    }
  }'
```

**Response**:
```json
{
  "policy_id": "retention-policy",
  "version": 1,
  "status": "draft",
  "created_at": "2025-12-04T10:00:00Z",
  "message": "Policy version 1 created"
}
```

### List Policies

```bash
curl "http://localhost:8000/v1/compliance/policies?tenant_id=demo" \
  -H "X-API-Key: your-key"
```

**Response**:
```json
{
  "policies": [
    {
      "policy_id": "retention-policy",
      "policy_name": "Memory Retention Policy",
      "policy_type": "data_retention",
      "latest_version": 2,
      "active_version": 1,
      "created_at": "2025-12-04T10:00:00Z"
    }
  ],
  "total_count": 1
}
```

### Activate Policy Version

```bash
curl -X POST http://localhost:8000/v1/compliance/policies/retention-policy/activate?version=2 \
  -H "X-Tenant-ID: demo" \
  -H "X-API-Key: your-key"
```

**Response**:
```json
{
  "policy_id": "retention-policy",
  "version": 2,
  "status": "active",
  "previous_version": 1,
  "activated_at": "2025-12-04T10:05:00Z",
  "message": "Policy version 2 activated"
}
```

### Enforce Policy

Check if operation complies with policy:

```bash
curl -X POST http://localhost:8000/v1/compliance/policies/retention-policy/enforce \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{
    "context": {
      "operation": "delete_memory",
      "memory_layer": "episodic",
      "memory_age_days": 95,
      "has_exception_tag": false
    }
  }'
```

**Response (Compliant)**:
```json
{
  "compliant": true,
  "policy_id": "retention-policy",
  "version": 2,
  "violations": [],
  "warnings": [],
  "message": "Operation complies with policy"
}
```

**Response (Non-Compliant)**:
```json
{
  "compliant": false,
  "policy_id": "retention-policy",
  "version": 2,
  "violations": [
    {
      "rule": "semantic_retention_days",
      "expected": 365,
      "actual": 300,
      "severity": "error",
      "message": "Semantic memory too young for deletion"
    }
  ],
  "warnings": [
    {
      "rule": "auto_delete_enabled",
      "message": "Manual deletion requires approval"
    }
  ],
  "message": "Operation violates policy"
}
```

---

## Real-World Examples

### Example 1: GDPR Right to Erasure

```bash
# 1. Request approval for data deletion
APPROVAL_ID=$(curl -X POST http://localhost:8000/v1/compliance/approvals \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{
    "tenant_id": "demo",
    "project_id": "my-app",
    "operation_type": "data_deletion",
    "operation_description": "GDPR erasure request for user_12345",
    "risk_level": "critical",
    "resource_type": "user_data",
    "resource_id": "user_12345",
    "requested_by": "privacy@example.com"
  }' | jq -r '.request_id')

# 2. First approval (DPO)
curl -X POST http://localhost:8000/v1/compliance/approvals/$APPROVAL_ID/decide \
  -d '{
    "approver_id": "dpo@example.com",
    "decision": "approved",
    "reason": "GDPR request verified"
  }'

# 3. Second approval (Legal)
curl -X POST http://localhost:8000/v1/compliance/approvals/$APPROVAL_ID/decide \
  -d '{
    "approver_id": "legal@example.com",
    "decision": "approved",
    "reason": "Legal review complete"
  }'

# 4. Execute deletion (now approved)
curl -X DELETE http://localhost:8000/v1/memory/delete \
  -d '{
    "tenant_id": "demo",
    "filters": {"user_id": "user_12345"},
    "approval_id": "'$APPROVAL_ID'"
  }'
```

### Example 2: Auditable AI Decision

```bash
# 1. Create context
CONTEXT_ID=$(curl -X POST http://localhost:8000/v1/compliance/provenance/context \
  -d '{
    "tenant_id": "demo",
    "project_id": "loan-approval",
    "query": "Should we approve loan application #12345?",
    "sources": [
      {
        "source_type": "document",
        "source_id": "credit-report-123",
        "content": "Credit score: 720, no defaults",
        "relevance_score": 0.95,
        "trust_level": "verified"
      }
    ]
  }' | jq -r '.context_id')

# 2. Record decision
DECISION_ID=$(curl -X POST http://localhost:8000/v1/compliance/provenance/decision \
  -d '{
    "tenant_id": "demo",
    "project_id": "loan-approval",
    "decision_type": "classification",
    "decision_description": "Loan approval decision",
    "context_id": "'$CONTEXT_ID'",
    "output": "APPROVED",
    "confidence": 0.87,
    "model_name": "loan-classifier-v2",
    "human_approved": true,
    "approval_request_id": "...",
    "metadata": {"loan_amount": 50000}
  }' | jq -r '.decision_id')

# 3. Later: Retrieve full lineage for audit
curl http://localhost:8000/v1/compliance/provenance/lineage/$DECISION_ID
```

### Example 3: Policy Enforcement Pipeline

```bash
# 1. Create quality threshold policy
curl -X POST http://localhost:8000/v1/compliance/policies \
  -d '{
    "tenant_id": "demo",
    "policy_id": "quality-policy",
    "policy_type": "quality_threshold",
    "policy_name": "AI Output Quality Policy",
    "rules": {
      "min_confidence": 0.8,
      "require_human_review_below": 0.6,
      "auto_reject_below": 0.3
    },
    "created_by": "ai-governance@example.com"
  }'

# 2. Activate policy
curl -X POST http://localhost:8000/v1/compliance/policies/quality-policy/activate?version=1

# 3. Enforce before using AI output
curl -X POST http://localhost:8000/v1/compliance/policies/quality-policy/enforce \
  -d '{
    "context": {
      "confidence": 0.75,
      "model_output": "..."
    }
  }'

# 4. If confidence < 0.8, trigger human review
# If confidence >= 0.8, proceed automatically
```

---

## Best Practices

### 1. Always Track High-Risk Operations

✅ **Do**: Request approval for:
- Data deletion
- Model deployment
- Policy changes
- Bulk exports
- Configuration changes

### 2. Use Meaningful Risk Levels

- `critical`: Irreversible operations (deletion, deployment)
- `high`: Significant impact (policy change)
- `medium`: Moderate impact (bulk export)
- `low`: Minimal impact (read operations)

### 3. Record Provenance for All AI Decisions

```bash
# Always create context → record decision
CONTEXT_ID=$(curl -X POST .../provenance/context -d '{...}')
curl -X POST .../provenance/decision -d '{"context_id": "'$CONTEXT_ID'", ...}'
```

### 4. Monitor Circuit Breakers

Set up alerts when breakers open:
```bash
curl http://localhost:8000/v1/compliance/circuit-breakers | \
  jq '.[] | select(.state == "OPEN")'
```

### 5. Version All Policies

Never modify existing policy versions. Create new versions:
```bash
# ❌ Don't modify version 1
# ✅ Create version 2
curl -X POST .../policies -d '{"version": 2, ...}'
```

### 6. Use Policy Enforcement

Check compliance before executing operations:
```bash
RESULT=$(curl -X POST .../policies/my-policy/enforce -d '{...}')
if [[ $(echo $RESULT | jq '.compliant') == "true" ]]; then
  # Proceed with operation
fi
```

---

## Troubleshooting

### Approval Request Expired

**Problem**: Request expired before approval

**Solution**:
- Create new approval request
- Consider higher risk level for longer timeout
- Enable approval notifications

### Circuit Breaker Stuck Open

**Problem**: Breaker remains open after fixing issue

**Solution**:
```bash
# Manually reset
curl -X POST http://localhost:8000/v1/compliance/circuit-breakers/database/reset
```

### Provenance Chain Incomplete

**Problem**: `lineage_complete: false` in response

**Solution**:
- Ensure context created before decision
- Verify context_id is correct
- Check for database errors

### Policy Violations

**Problem**: Operation violates policy

**Solution**:
1. Review violations in response
2. Either:
   - Fix operation to comply
   - Create policy exception
   - Update policy (new version)

---

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/compliance/approvals` | POST | Request approval |
| `/v1/compliance/approvals/{request_id}` | GET | Check status |
| `/v1/compliance/approvals/{request_id}/decide` | POST | Approve/reject |
| `/v1/compliance/provenance/context` | POST | Create context |
| `/v1/compliance/provenance/decision` | POST | Record decision |
| `/v1/compliance/provenance/lineage/{decision_id}` | GET | Get lineage |
| `/v1/compliance/circuit-breakers` | GET | List breakers |
| `/v1/compliance/circuit-breakers/{name}` | GET | Get breaker |
| `/v1/compliance/circuit-breakers/{name}/reset` | POST | Reset breaker |
| `/v1/compliance/policies` | GET | List policies |
| `/v1/compliance/policies` | POST | Create policy |
| `/v1/compliance/policies/{policy_id}/activate` | POST | Activate policy |
| `/v1/compliance/policies/{policy_id}/enforce` | POST | Enforce policy |

**Full API documentation**: [API_INDEX.md](../../reference/api/API_INDEX.md#isoiec-42001-compliance-13)

---

## Further Reading

- [ISO/IEC 42001 Standard](https://www.iso.org/standard/81230.html) - Official specification
- [Event Triggers Guide](EVENT_TRIGGERS_GUIDE.md) - Automate compliance workflows
- [Governance Guide](../core/GOVERNANCE_GUIDE.md) - Cost tracking and budgets

---

**Last Updated**: 2025-12-04
**API Version**: 2.2.0-enterprise
**ISO/IEC 42001 Compliant**: ✅ Yes
