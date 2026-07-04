# Event Triggers & Automation Guide

**Enterprise Feature** | **Version**: 2.2.0-enterprise

## Overview

Event Triggers enable automated workflows based on system events. When specific conditions are met, predefined actions execute automatically—no manual intervention required.

**Use Cases**:
- 🔄 Auto-generate reflections when memory count reaches threshold
- 📧 Send alerts when quality metrics degrade
- 📸 Create periodic snapshots
- 🔗 Trigger external webhooks on important events
- 🗑️ Apply decay policies on schedule
- 🚨 Fire compliance workflows on sensitive data access

**Key Concepts**:
- **Events**: Something that happens in the system (memory created, search executed, etc.)
- **Triggers**: Rules that match events to conditions
- **Actions**: What to execute when trigger fires
- **Workflows**: Chains of actions with dependencies

---

## Quick Start

### 1. Create Your First Trigger

Auto-generate reflections when 100+ memories exist:

```bash
curl -X POST http://localhost:8000/v1/triggers/create \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo" \
  -H "X-API-Key: your-key" \
  -d '{
    "tenant_id": "demo",
    "project_id": "my-app",
    "rule_name": "Auto-Reflection Generator",
    "description": "Generate reflections when memory count exceeds 100",
    "event_types": ["memory_created"],
    "conditions": {
      "memory_count": {"operator": ">=", "value": 100}
    },
    "actions": [
      {
        "action_type": "generate_reflection",
        "parameters": {
          "level": "L1",
          "min_importance": 0.5
        }
      }
    ],
    "created_by": "admin",
    "priority": 5,
    "status": "active"
  }'
```

**Response**:
```json
{
  "trigger_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Trigger rule 'Auto-Reflection Generator' created successfully"
}
```

### 2. Emit an Event to Test

```bash
curl -X POST http://localhost:8000/v1/triggers/events/emit \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo" \
  -H "X-API-Key: your-key" \
  -d '{
    "tenant_id": "demo",
    "project_id": "my-app",
    "event_type": "memory_created",
    "payload": {
      "memory_id": "123",
      "memory_count": 105
    }
  }'
```

**Response**:
```json
{
  "event_id": "660e8400-e29b-41d4-a716-446655440001",
  "triggers_matched": 1,
  "actions_queued": 1,
  "message": "Event processed: 1 triggers matched"
}
```

Your trigger fired! ✅

---

## Event Types

### Available Event Types

| Event Type | Description | Typical Payload |
|------------|-------------|-----------------|
| `memory_created` | New memory stored | `{memory_id, content, layer}` |
| `memory_updated` | Memory modified | `{memory_id, changes}` |
| `memory_deleted` | Memory removed | `{memory_id}` |
| `memory_accessed` | Memory retrieved | `{memory_id, query}` |
| `reflection_generated` | New reflection created | `{reflection_id, level}` |
| `semantic_node_created` | Graph node added | `{node_id, type}` |
| `semantic_node_degraded` | Node importance decayed | `{node_id, old_score, new_score}` |
| `search_executed` | Search query performed | `{query, k, results_count}` |
| `query_analyzed` | Query intent analyzed | `{query, intent, confidence}` |
| `drift_detected` | Data distribution shifted | `{metric, severity}` |
| `quality_degraded` | Quality below threshold | `{metric, value, threshold}` |
| `threshold_exceeded` | Metric exceeded limit | `{metric, value, limit}` |
| `schedule_triggered` | Scheduled event fired | `{schedule_id, cron}` |

**List event types**:
```bash
curl http://localhost:8000/v1/triggers/events/types \
  -H "X-API-Key: your-key"
```

---

## Conditions

Triggers use conditions to match events. Use operators to define matching logic.

### Condition Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `==` | Equals | `{"status": {"operator": "==", "value": "active"}}` |
| `!=` | Not equals | `{"status": {"operator": "!=", "value": "archived"}}` |
| `>` | Greater than | `{"count": {"operator": ">", "value": 100}}` |
| `>=` | Greater or equal | `{"score": {"operator": ">=", "value": 0.8}}` |
| `<` | Less than | `{"importance": {"operator": "<", "value": 0.3}}` |
| `<=` | Less or equal | `{"age_days": {"operator": "<=", "value": 7}}` |
| `in` | Value in list | `{"layer": {"operator": "in", "value": ["episodic", "ltm"]}}` |
| `contains` | String contains | `{"content": {"operator": "contains", "value": "error"}}` |
| `exists` | Field exists | `{"metadata.user_id": {"operator": "exists"}}` |

### Condition Logic

**AND logic** (all conditions must match):
```json
{
  "condition_operator": "AND",
  "conditions": {
    "memory_count": {"operator": ">=", "value": 100},
    "project_id": {"operator": "==", "value": "prod"}
  }
}
```

**OR logic** (any condition matches):
```json
{
  "condition_operator": "OR",
  "conditions": {
    "importance": {"operator": ">=", "value": 0.9},
    "tag": {"operator": "in", "value": ["critical", "urgent"]}
  }
}
```

### Complex Example

```json
{
  "event_types": ["memory_created", "memory_updated"],
  "condition_operator": "AND",
  "conditions": {
    "layer": {"operator": "in", "value": ["episodic", "semantic"]},
    "importance": {"operator": ">=", "value": 0.7},
    "project_id": {"operator": "==", "value": "production"},
    "content": {"operator": "contains", "value": "customer"}
  }
}
```

---

## Actions

Actions define what happens when a trigger fires.

### Available Action Types

#### 1. Generate Reflection
```json
{
  "action_type": "generate_reflection",
  "parameters": {
    "level": "L1",
    "min_importance": 0.5,
    "lookback_hours": 24
  }
}
```

#### 2. Create Graph Snapshot
```json
{
  "action_type": "create_snapshot",
  "parameters": {
    "name": "auto-snapshot-${timestamp}",
    "description": "Automated snapshot",
    "include_metrics": true
  }
}
```

#### 3. Send Webhook
```json
{
  "action_type": "webhook",
  "parameters": {
    "url": "https://api.example.com/alerts",
    "method": "POST",
    "headers": {
      "Authorization": "Bearer ${WEBHOOK_TOKEN}"
    },
    "body": {
      "event": "${event_type}",
      "tenant": "${tenant_id}",
      "message": "Quality degraded below threshold"
    }
  }
}
```

#### 4. Apply Decay
```json
{
  "action_type": "apply_decay",
  "parameters": {
    "layer": "episodic",
    "decay_factor": 0.95,
    "min_importance": 0.1
  }
}
```

#### 5. Send Email Alert
```json
{
  "action_type": "email",
  "parameters": {
    "to": ["admin@example.com"],
    "subject": "Alert: ${event_type}",
    "body": "Event triggered at ${timestamp}"
  }
}
```

#### 6. Log to External System
```json
{
  "action_type": "log",
  "parameters": {
    "destination": "syslog",
    "level": "warning",
    "message": "${event_type} occurred: ${payload}"
  }
}
```

#### 7. Execute Custom Function
```json
{
  "action_type": "function",
  "parameters": {
    "function_name": "custom_handler",
    "args": {
      "event": "${event}",
      "metadata": "${payload}"
    }
  }
}
```

---

## Workflows

Workflows chain multiple actions together with dependencies and execution modes.

### Sequential Workflow

Actions execute one after another:

```bash
curl -X POST http://localhost:8000/v1/triggers/workflows/create \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo" \
  -H "X-API-Key: your-key" \
  -d '{
    "tenant_id": "demo",
    "project_id": "my-app",
    "workflow_name": "Nightly Maintenance",
    "description": "Generate reflections, apply decay, create snapshot",
    "execution_mode": "sequential",
    "steps": [
      {
        "step_id": "step1",
        "action_type": "generate_reflection",
        "parameters": {"level": "L1"},
        "on_failure": "abort"
      },
      {
        "step_id": "step2",
        "action_type": "apply_decay",
        "parameters": {"layer": "episodic"},
        "depends_on": ["step1"],
        "on_failure": "continue"
      },
      {
        "step_id": "step3",
        "action_type": "create_snapshot",
        "parameters": {"name": "nightly-snapshot"},
        "depends_on": ["step2"],
        "on_failure": "abort"
      }
    ],
    "created_by": "admin"
  }'
```

### Parallel Workflow

Actions execute simultaneously:

```json
{
  "workflow_name": "Parallel Alerts",
  "execution_mode": "parallel",
  "steps": [
    {
      "step_id": "email",
      "action_type": "email",
      "parameters": {"to": ["admin@example.com"]}
    },
    {
      "step_id": "webhook",
      "action_type": "webhook",
      "parameters": {"url": "https://api.slack.com/webhook"}
    },
    {
      "step_id": "log",
      "action_type": "log",
      "parameters": {"destination": "syslog"}
    }
  ]
}
```

### Get Workflow
```bash
curl http://localhost:8000/v1/triggers/workflows/{workflow_id} \
  -H "X-API-Key: your-key"
```

### List Workflows
```bash
curl "http://localhost:8000/v1/triggers/workflows?tenant_id=demo&project_id=my-app" \
  -H "X-API-Key: your-key"
```

---

## Trigger Templates

Use pre-built templates for common scenarios.

### Available Templates

```bash
curl http://localhost:8000/v1/triggers/templates \
  -H "X-API-Key: your-key"
```

**Response**:
```json
{
  "templates": [
    {
      "template_id": "auto_reflection",
      "template_name": "Auto Reflection Generator",
      "description": "Generate reflections when memory count threshold reached",
      "category": "maintenance",
      "required_parameters": ["memory_threshold", "reflection_level"]
    },
    {
      "template_id": "quality_alert",
      "template_name": "Quality Degradation Alert",
      "description": "Send alert when quality metrics drop",
      "category": "monitoring",
      "required_parameters": ["quality_threshold", "alert_email"]
    }
  ]
}
```

### Instantiate Template

```bash
curl -X POST "http://localhost:8000/v1/triggers/templates/auto_reflection/instantiate?tenant_id=demo&project_id=my-app&rule_name=My%20Reflection%20Rule&created_by=admin" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{
    "parameters": {
      "memory_threshold": 100,
      "reflection_level": "L1"
    }
  }'
```

---

## Managing Triggers

### List Triggers

```bash
curl "http://localhost:8000/v1/triggers/list?tenant_id=demo&project_id=my-app&status_filter=active&limit=50" \
  -H "X-API-Key: your-key"
```

**Response**:
```json
{
  "triggers": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "rule_name": "Auto-Reflection Generator",
      "status": "active",
      "priority": 5,
      "event_types": ["memory_created"],
      "created_at": "2025-12-04T10:00:00Z"
    }
  ],
  "total_count": 1
}
```

### Get Trigger Details

```bash
curl http://localhost:8000/v1/triggers/{trigger_id} \
  -H "X-API-Key: your-key"
```

### Update Trigger

```bash
curl -X PUT http://localhost:8000/v1/triggers/{trigger_id} \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{
    "rule_name": "Updated Rule Name",
    "priority": 10,
    "conditions": {
      "memory_count": {"operator": ">=", "value": 200}
    }
  }'
```

### Enable/Disable Trigger

```bash
# Enable
curl -X POST http://localhost:8000/v1/triggers/{trigger_id}/enable \
  -H "X-API-Key: your-key"

# Disable
curl -X POST http://localhost:8000/v1/triggers/{trigger_id}/disable \
  -H "X-API-Key: your-key"
```

### Delete Trigger

```bash
curl -X DELETE http://localhost:8000/v1/triggers/{trigger_id} \
  -H "X-API-Key: your-key"
```

---

## Execution History

Monitor trigger executions to debug and optimize automation.

### Get Execution History

```bash
curl -X POST http://localhost:8000/v1/triggers/executions \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{
    "trigger_id": "550e8400-e29b-41d4-a716-446655440000",
    "limit": 50,
    "status_filter": "success"
  }'
```

**Response**:
```json
{
  "executions": [
    {
      "execution_id": "exec-001",
      "trigger_id": "550e8400-e29b-41d4-a716-446655440000",
      "event_id": "evt-001",
      "status": "success",
      "started_at": "2025-12-04T10:15:00Z",
      "completed_at": "2025-12-04T10:15:02Z",
      "duration_ms": 2000,
      "actions_executed": 1,
      "result": {
        "reflection_id": "refl-123",
        "memories_processed": 105
      }
    }
  ],
  "total_count": 1,
  "summary": {
    "trigger_name": "Auto-Reflection Generator",
    "period_start": "2025-11-27T10:00:00Z",
    "period_end": "2025-12-04T10:00:00Z",
    "total_executions": 15,
    "success_count": 14,
    "failure_count": 1,
    "avg_duration_ms": 1850
  }
}
```

### Filter by Status

```bash
# Get only failed executions
curl -X POST http://localhost:8000/v1/triggers/executions \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{
    "trigger_id": "550e8400-e29b-41d4-a716-446655440000",
    "status_filter": "failed",
    "limit": 10
  }'
```

---

## Real-World Examples

### Example 1: Slack Alerts on Quality Degradation

```bash
curl -X POST http://localhost:8000/v1/triggers/create \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo" \
  -H "X-API-Key: your-key" \
  -d '{
    "tenant_id": "demo",
    "project_id": "production",
    "rule_name": "Slack Quality Alert",
    "event_types": ["quality_degraded"],
    "conditions": {
      "metric": {"operator": "in", "value": ["precision", "recall"]},
      "value": {"operator": "<", "value": 0.7}
    },
    "actions": [
      {
        "action_type": "webhook",
        "parameters": {
          "url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
          "method": "POST",
          "body": {
            "text": "⚠️ *Quality Alert*\nMetric: ${payload.metric}\nValue: ${payload.value}\nThreshold: 0.7"
          }
        }
      }
    ],
    "created_by": "admin",
    "priority": 10
  }'
```

### Example 2: Scheduled Nightly Backup

```bash
curl -X POST http://localhost:8000/v1/triggers/create \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo" \
  -H "X-API-Key: your-key" \
  -d '{
    "tenant_id": "demo",
    "project_id": "my-app",
    "rule_name": "Nightly Snapshot",
    "event_types": ["schedule_triggered"],
    "conditions": {
      "schedule_id": {"operator": "==", "value": "nightly-backup"},
      "cron": {"operator": "==", "value": "0 2 * * *"}
    },
    "actions": [
      {
        "action_type": "create_snapshot",
        "parameters": {
          "name": "nightly-${timestamp}",
          "description": "Automated nightly backup"
        }
      }
    ],
    "created_by": "admin",
    "priority": 5
  }'
```

### Example 3: Multi-Action Compliance Workflow

```bash
curl -X POST http://localhost:8000/v1/triggers/workflows/create \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo" \
  -H "X-API-Key: your-key" \
  -d '{
    "tenant_id": "demo",
    "project_id": "my-app",
    "workflow_name": "Compliance Alert Chain",
    "execution_mode": "sequential",
    "steps": [
      {
        "step_id": "log",
        "action_type": "log",
        "parameters": {
          "destination": "compliance-log",
          "level": "warning"
        }
      },
      {
        "step_id": "email",
        "action_type": "email",
        "parameters": {
          "to": ["compliance@example.com"],
          "subject": "Compliance Event Detected"
        },
        "depends_on": ["log"]
      },
      {
        "step_id": "webhook",
        "action_type": "webhook",
        "parameters": {
          "url": "https://api.compliance-system.com/events"
        },
        "depends_on": ["log"]
      }
    ],
    "created_by": "admin"
  }'
```

---

## Retry Configuration

Configure automatic retries for failed actions:

```json
{
  "retry_config": {
    "max_retries": 3,
    "retry_delay_seconds": 60,
    "backoff_multiplier": 2.0,
    "retry_on_errors": ["timeout", "connection_error", "503"]
  }
}
```

**Example**:
- Attempt 1: Immediate
- Attempt 2: After 60 seconds
- Attempt 3: After 120 seconds (60 * 2.0)
- Attempt 4: After 240 seconds (120 * 2.0)

---

## Priority System

Triggers have priority levels (1-10):
- **1-3**: Low priority (background tasks)
- **4-7**: Medium priority (normal automation)
- **8-10**: High priority (critical alerts)

When multiple triggers match an event, they execute in priority order.

---

## Best Practices

### 1. Use Specific Event Types
❌ **Bad**: Listen to all events
```json
{"event_types": ["*"]}
```

✅ **Good**: Listen to specific events
```json
{"event_types": ["memory_created", "memory_updated"]}
```

### 2. Add Meaningful Conditions
❌ **Bad**: Trigger on everything
```json
{"conditions": {}}
```

✅ **Good**: Filter with specific conditions
```json
{
  "conditions": {
    "importance": {"operator": ">=", "value": 0.7},
    "layer": {"operator": "in", "value": ["episodic", "semantic"]}
  }
}
```

### 3. Use Descriptive Names
❌ **Bad**: `"rule_name": "trigger1"`

✅ **Good**: `"rule_name": "Auto-Reflection on 100+ Memories"`

### 4. Test Before Production
Always test triggers with `status: "inactive"` first, then enable after verification.

### 5. Monitor Execution History
Regularly check execution logs for failed actions:
```bash
curl -X POST http://localhost:8000/v1/triggers/executions \
  -d '{"trigger_id": "...", "status_filter": "failed"}'
```

### 6. Use Templates
Start with templates for common patterns, then customize as needed.

### 7. Set Appropriate Priorities
- Critical alerts: Priority 8-10
- Normal automation: Priority 4-7
- Background tasks: Priority 1-3

---

## Troubleshooting

### Trigger Not Firing

**Check 1**: Verify trigger is active
```bash
curl http://localhost:8000/v1/triggers/{trigger_id}
# Check status: "active"
```

**Check 2**: Verify event type matches
```bash
curl http://localhost:8000/v1/triggers/events/types
# Ensure your event_type exists
```

**Check 3**: Test conditions
Emit test event with matching payload:
```bash
curl -X POST http://localhost:8000/v1/triggers/events/emit \
  -d '{
    "event_type": "memory_created",
    "payload": {"memory_count": 105}
  }'
```

**Check 4**: Review execution history
```bash
curl -X POST http://localhost:8000/v1/triggers/executions \
  -d '{"trigger_id": "...", "limit": 10}'
```

### Action Failing

**Check retry configuration**:
```json
{
  "retry_config": {
    "max_retries": 3,
    "retry_delay_seconds": 30
  }
}
```

**Check action logs**:
```bash
curl -X POST http://localhost:8000/v1/triggers/executions \
  -d '{"trigger_id": "...", "status_filter": "failed"}'
```

### Webhook Not Working

**Verify URL is accessible**:
```bash
curl -X POST https://your-webhook-url.com/endpoint \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
```

**Check webhook action configuration**:
```json
{
  "action_type": "webhook",
  "parameters": {
    "url": "https://...",
    "method": "POST",
    "headers": {"Content-Type": "application/json"}
  }
}
```

---

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/triggers/create` | POST | Create trigger |
| `/v1/triggers/{trigger_id}` | GET | Get trigger |
| `/v1/triggers/{trigger_id}` | PUT | Update trigger |
| `/v1/triggers/{trigger_id}` | DELETE | Delete trigger |
| `/v1/triggers/{trigger_id}/enable` | POST | Enable trigger |
| `/v1/triggers/{trigger_id}/disable` | POST | Disable trigger |
| `/v1/triggers/list` | GET | List triggers |
| `/v1/triggers/events/emit` | POST | Emit event |
| `/v1/triggers/events/types` | GET | List event types |
| `/v1/triggers/executions` | POST | Get execution history |
| `/v1/triggers/workflows/create` | POST | Create workflow |
| `/v1/triggers/workflows/{workflow_id}` | GET | Get workflow |
| `/v1/triggers/workflows` | GET | List workflows |
| `/v1/triggers/templates` | GET | List templates |
| `/v1/triggers/templates/{template_id}` | GET | Get template |
| `/v1/triggers/templates/{template_id}/instantiate` | POST | Instantiate template |
| `/v1/triggers/health` | GET | Health check |
| `/v1/triggers/info` | GET | System info |

**Full API documentation**: [API_INDEX.md](../../reference/api/API_INDEX.md#event-triggers--workflows-18)

---

## Further Reading

- [API Cookbook](../../reference/api/API_COOKBOOK.md) - More trigger recipes
- [Workflows Guide](WORKFLOWS_GUIDE.md) - Advanced workflow patterns
- [Webhooks Guide](WEBHOOKS_GUIDE.md) - Webhook integration examples
- [Compliance Guide](COMPLIANCE_GUIDE.md) - ISO/IEC 42001 automation

---

**Last Updated**: 2025-12-04
**API Version**: 2.2.0-enterprise
