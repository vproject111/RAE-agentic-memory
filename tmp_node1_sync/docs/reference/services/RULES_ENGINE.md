# Rules Engine - Event-Driven Automation

## Overview

The Rules Engine is RAE's event-driven automation system that allows you to define triggers, conditions, and actions that execute automatically when specific events occur in the memory system.

## Architecture

```
┌──────────────────────────────────────────────────────┐
│              Event Processing Pipeline                │
├──────────────────────────────────────────────────────┤
│                                                       │
│  1. Event Reception                                   │
│     └─ Event published by system component           │
│                                                       │
│  2. Trigger Matching                                  │
│     ├─ Fetch active triggers for event type          │
│     └─ Match tenant/project scope                    │
│                                                       │
│  3. Condition Evaluation                              │
│     ├─ AND/OR logic support                          │
│     ├─ Nested condition groups                       │
│     ├─ 12+ comparison operators                      │
│     └─ Dot notation for nested fields                │
│                                                       │
│  4. Rate Limiting & Cooldown                          │
│     ├─ Per-trigger execution limits                  │
│     └─ Cooldown period enforcement                   │
│                                                       │
│  5. Action Execution                                  │
│     ├─ Execute configured actions                    │
│     ├─ Retry on failure (exponential backoff)        │
│     └─ Track execution history                       │
│                                                       │
└──────────────────────────────────────────────────────┘
```

## Core Concepts

### 1. Events

Events are occurrences in the system that can trigger automation rules.

**Supported Event Types**:
- `MEMORY_CREATED` - New memory stored
- `MEMORY_UPDATED` - Memory modified
- `MEMORY_DELETED` - Memory removed
- `REFLECTION_GENERATED` - Reflection created
- `SEMANTIC_EXTRACTED` - Semantic nodes extracted
- `GRAPH_UPDATED` - Knowledge graph changed
- `THRESHOLD_EXCEEDED` - Metric threshold crossed
- `DRIFT_DETECTED` - Semantic drift detected
- `BUDGET_WARNING` - Cost budget threshold reached
- `EVALUATION_COMPLETED` - Search evaluation finished

**Event Structure**:
```python
from apps.memory_api.models.event_models import Event, EventType

event = Event(
    event_id="evt_123",
    event_type=EventType.MEMORY_CREATED,
    tenant_id="my-tenant",
    project_id="my-project",
    timestamp=datetime.now(),
    payload={
        "memory_id": "mem_456",
        "content": "User reported bug in auth",
        "importance": 0.8,
        "tags": ["bug", "auth"]
    }
)
```

### 2. Triggers

Triggers define when rules should fire.

**Trigger Components**:
- **Event Type**: Which event to listen for
- **Condition**: When to fire (optional)
- **Actions**: What to do when fired
- **Rate Limiting**: Max executions per hour
- **Cooldown**: Minimum time between executions

**Example Trigger**:
```python
from apps.memory_api.models.event_models import TriggerRule, TriggerCondition, ActionConfig

trigger = TriggerRule(
    trigger_id="trg_001",
    name="High Importance Memory Alert",
    tenant_id="my-tenant",
    project_id="my-project",
    event_type=EventType.MEMORY_CREATED,
    condition=TriggerCondition(
        condition_group=ConditionGroup(
            operator="AND",
            conditions=[
                Condition(
                    field="payload.importance",
                    operator=ConditionOperator.GREATER_THAN,
                    value=0.8
                ),
                Condition(
                    field="payload.tags",
                    operator=ConditionOperator.CONTAINS,
                    value="critical"
                )
            ]
        ),
        max_executions_per_hour=10,
        cooldown_seconds=60
    ),
    actions=[
        ActionConfig(
            action_type=ActionType.SEND_WEBHOOK,
            config={
                "url": "https://api.example.com/alerts",
                "method": "POST"
            },
            retry_on_failure=True,
            max_retries=3
        )
    ],
    status=TriggerStatus.ACTIVE
)
```

### 3. Conditions

Conditions determine whether a trigger should fire.

**Supported Operators**:
- `EQUALS`, `NOT_EQUALS`
- `GREATER_THAN`, `LESS_THAN`, `GREATER_EQUAL`, `LESS_EQUAL`
- `CONTAINS`, `NOT_CONTAINS`
- `IN`, `NOT_IN`
- `MATCHES_REGEX`
- `IS_NULL`, `IS_NOT_NULL`

**Condition Groups** (AND/OR Logic):
```python
ConditionGroup(
    operator="OR",  # or "AND"
    conditions=[
        Condition(field="importance", operator="GREATER_THAN", value=0.8),
        Condition(field="tags", operator="CONTAINS", value="urgent")
    ],
    groups=[  # Nested groups
        ConditionGroup(
            operator="AND",
            conditions=[
                Condition(field="layer", operator="EQUALS", value="episodic"),
                Condition(field="metadata.source", operator="EQUALS", value="slack")
            ]
        )
    ]
)
```

**Dot Notation for Nested Fields**:
```python
# Access nested payload fields
Condition(field="payload.metadata.source", operator="EQUALS", value="github")
Condition(field="payload.user.role", operator="IN", value=["admin", "moderator"])
```

### 4. Actions

Actions are operations executed when triggers fire.

**Supported Action Types**:
- `SEND_NOTIFICATION` - Send notification (email, Slack, etc.)
- `SEND_WEBHOOK` - HTTP POST to external URL
- `GENERATE_REFLECTION` - Trigger reflection generation
- `EXTRACT_SEMANTICS` - Extract semantic nodes
- `APPLY_DECAY` - Apply temporal decay to memories
- `CREATE_SNAPSHOT` - Create graph snapshot
- `RUN_EVALUATION` - Trigger search evaluation

**Action Configuration**:
```python
ActionConfig(
    action_type=ActionType.SEND_WEBHOOK,
    config={
        "url": "https://hooks.slack.com/services/XXX/YYY/ZZZ",
        "body": {
            "text": "High importance memory created",
            "memory_id": "${event.payload.memory_id}"
        }
    },
    retry_on_failure=True,
    max_retries=3,
    retry_delay_seconds=5
)
```

## API Usage

### Processing Events

```python
from apps.memory_api.services.rules_engine import RulesEngine

engine = RulesEngine(pool=db_pool)

# Process an event
result = await engine.process_event(event)

# Returns:
# {
#     "event_id": "evt_123",
#     "triggers_matched": 2,
#     "actions_executed": 3,
#     "executions": [
#         ActionExecution(...),
#         ...
#     ]
# }
```

### Creating Triggers (via API)

```bash
POST /v1/automation/triggers

{
  "name": "Critical Memory Alert",
  "event_type": "memory_created",
  "condition": {
    "condition_group": {
      "operator": "AND",
      "conditions": [
        {
          "field": "payload.importance",
          "operator": "greater_than",
          "value": 0.9
        },
        {
          "field": "payload.tags",
          "operator": "contains",
          "value": "critical"
        }
      ]
    },
    "max_executions_per_hour": 100,
    "cooldown_seconds": 30
  },
  "actions": [
    {
      "action_type": "send_webhook",
      "config": {
        "url": "https://api.example.com/alerts"
      },
      "retry_on_failure": true,
      "max_retries": 3
    }
  ]
}
```

## Common Use Cases

### 1. Automatic Reflection Generation

Trigger reflection when enough new memories accumulate:

```python
TriggerRule(
    name="Auto Reflection - 50 Memories",
    event_type=EventType.MEMORY_CREATED,
    condition=TriggerCondition(
        # Uses internal counter
        max_executions_per_hour=1
    ),
    actions=[
        ActionConfig(
            action_type=ActionType.GENERATE_REFLECTION,
            config={"min_memories": 50}
        )
    ]
)
```

### 2. Budget Alerts

Send alert when cost threshold is exceeded:

```python
TriggerRule(
    name="Budget Alert - 80% Threshold",
    event_type=EventType.BUDGET_WARNING,
    condition=TriggerCondition(
        condition_group=ConditionGroup(
            operator="AND",
            conditions=[
                Condition(
                    field="payload.percent_used",
                    operator=ConditionOperator.GREATER_EQUAL,
                    value=0.8
                )
            ]
        )
    ),
    actions=[
        ActionConfig(
            action_type=ActionType.SEND_NOTIFICATION,
            config={
                "channel": "email",
                "recipients": ["admin@example.com"],
                "subject": "Budget Alert: 80% Threshold Exceeded"
            }
        )
    ]
)
```

### 3. Drift Detection Response

Automatically re-evaluate search quality when drift is detected:

```python
TriggerRule(
    name="Drift Response - Re-evaluate",
    event_type=EventType.DRIFT_DETECTED,
    actions=[
        ActionConfig(
            action_type=ActionType.RUN_EVALUATION,
            config={"test_set": "standard_queries"}
        ),
        ActionConfig(
            action_type=ActionType.SEND_WEBHOOK,
            config={
                "url": "https://monitoring.example.com/drift",
                "method": "POST"
            }
        )
    ]
)
```

### 4. Semantic Extraction Pipeline

Extract semantics from high-importance memories:

```python
TriggerRule(
    name="Auto Semantic Extraction",
    event_type=EventType.MEMORY_CREATED,
    condition=TriggerCondition(
        condition_group=ConditionGroup(
            operator="OR",
            conditions=[
                Condition(
                    field="payload.importance",
                    operator=ConditionOperator.GREATER_THAN,
                    value=0.7
                ),
                Condition(
                    field="payload.layer",
                    operator=ConditionOperator.EQUALS,
                    value="semantic"
                )
            ]
        )
    ),
    actions=[
        ActionConfig(
            action_type=ActionType.EXTRACT_SEMANTICS,
            config={"extract_entities": True, "extract_relations": True}
        )
    ]
)
```

## Rate Limiting & Cooldown

### Rate Limiting

Prevents trigger from firing too many times within a time window:

```python
TriggerCondition(
    max_executions_per_hour=10  # Max 10 times per hour
)
```

- Uses sliding window
- Counter resets every hour
- Prevents runaway automation

### Cooldown

Minimum time between executions:

```python
TriggerCondition(
    cooldown_seconds=300  # Wait 5 minutes between fires
)
```

- Prevents rapid re-firing
- Applies per trigger instance
- Useful for expensive operations

## Retry Logic

Actions can be configured to retry on failure:

```python
ActionConfig(
    action_type=ActionType.SEND_WEBHOOK,
    config={"url": "https://api.example.com/endpoint"},
    retry_on_failure=True,
    max_retries=3,
    retry_delay_seconds=5  # Wait 5 seconds between retries
)
```

**Retry Behavior**:
1. Action fails on first attempt
2. Wait `retry_delay_seconds`
3. Retry (attempt 2)
4. If fails, wait again
5. Retry (attempt 3)
6. If fails, mark as permanently failed

## Execution Tracking

Every action execution is tracked:

```python
ActionExecution(
    execution_id="exec_789",
    trigger_id="trg_001",
    event_id="evt_123",
    action_type=ActionType.SEND_WEBHOOK,
    status=ExecutionStatus.COMPLETED,  # or FAILED
    started_at=datetime(...),
    completed_at=datetime(...),
    duration_ms=234,
    success=True,
    result={"status_code": 200},
    error_message=None,
    attempt_number=1,
    max_attempts=3
)
```

**Query Execution History**:
```bash
GET /v1/automation/executions?trigger_id=trg_001&limit=100
```

## Best Practices

1. **Use Rate Limiting**: Prevent runaway automation costs
2. **Add Cooldowns**: Avoid rapid re-triggers
3. **Enable Retries**: Handle transient failures gracefully
4. **Test Conditions**: Verify logic with test events before enabling
5. **Monitor Executions**: Track success/failure rates
6. **Use Webhooks for Integration**: Integrate with external systems via webhooks
7. **Structured Logging**: All executions logged with structlog

## Monitoring

### Key Metrics
- Triggers matched per event type
- Action success/failure rates
- Retry frequency
- Average execution duration
- Rate limit hits

### Logging

```python
logger.info(
    "action_executed_successfully",
    execution_id=execution_id,
    action_type=action_type.value,
    duration_ms=duration_ms,
    attempt_number=attempt
)
```

## Troubleshooting

### Trigger Not Firing
- Check trigger status (must be `ACTIVE`)
- Verify event type matches
- Check condition logic
- Verify rate limit not exceeded
- Check cooldown period

### Action Failing
- Check action configuration
- Verify retry settings
- Review execution logs
- Test webhook URLs manually

### Performance Issues
- Reduce max_executions_per_hour
- Increase cooldown
- Optimize action implementations
- Use async actions when possible

## Future Enhancements

- [ ] Scheduled triggers (cron-like)
- [ ] Trigger templates/marketplace
- [ ] Action chaining (workflows)
- [ ] Conditional action execution
- [ ] Action result variables
- [ ] Trigger analytics dashboard
- [ ] Visual trigger builder UI
