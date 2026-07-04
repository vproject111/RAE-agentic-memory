# Rules Engine – Event-Driven Automation

## Overview

The Rules Engine implements event-driven automation in RAE, allowing automatic actions to be triggered based on system events (e.g., new memories, budget exceeded, specific queries).

**Implementation**: `apps/memory_api/services/rules_engine.py`

## Key Features

- **Event Matching**: Complex condition evaluation (AND/OR groups)
- **Action Execution**: Automated responses with retry logic
- **Rate Limiting**: Prevents action flooding
- **Cooldown Periods**: Time-based action throttling
- **Execution Tracking**: Full audit trail of rule executions

## Architecture

### Core Components

| Component | Purpose |
|-----------|---------|
| `RulesEngine` | Main engine for event processing |
| `TriggerRule` | Rule definition (conditions + actions) |
| `Event` | Incoming event to be processed |
| `ActionExecutor` | Executes actions with retry logic |
| `ConditionEvaluator` | Evaluates complex conditions |

### Event Flow

```
Event → Rules Engine → Match Triggers → Evaluate Conditions → Execute Actions
```

## Event Types

Supported event types (from `EventType` enum):

- `MEMORY_CREATED` - New memory stored
- `MEMORY_ACCESSED` - Memory retrieved
- `MEMORY_DELETED` - Memory removed
- `BUDGET_EXCEEDED` - Cost limit reached
- `QUERY_EXECUTED` - Search query performed
- `REFLECTION_GENERATED` - Reflection created
- `DECAY_COMPLETED` - Decay cycle finished
- `CUSTOM` - User-defined events

## Trigger Rules

### Rule Structure

```python
class TriggerRule:
    trigger_id: str
    tenant_id: str
    project_id: str
    name: str
    description: str
    event_type: EventType
    condition: Condition
    actions: List[ActionConfig]
    enabled: bool
    priority: int
    rate_limit: Optional[Dict]
    cooldown_seconds: int
    metadata: Dict[str, Any]
```

### Condition Structure

```python
class ConditionGroup:
    operator: ConditionOperator  # AND, OR, NOT
    conditions: List[Condition]

class Condition:
    field: str  # e.g., "payload.importance"
    operator: str  # "eq", "gt", "lt", "contains", "regex"
    value: Any
    condition_group: Optional[ConditionGroup]
```

### Example Rules

#### Rule 1: Alert on High-Importance Memory

```json
{
  "name": "Alert on critical memory",
  "event_type": "MEMORY_CREATED",
  "condition": {
    "condition_group": {
      "operator": "AND",
      "conditions": [
        {"field": "payload.importance", "operator": "gt", "value": 0.9},
        {"field": "payload.layer", "operator": "eq", "value": "em"}
      ]
    }
  },
  "actions": [
    {
      "action_type": "WEBHOOK",
      "config": {
        "url": "https://alerts.example.com/webhook",
        "method": "POST",
        "payload": {"message": "Critical memory created"}
      }
    }
  ]
}
```

#### Rule 2: Trigger Reflection on Failure Pattern

```json
{
  "name": "Auto-reflect on repeated errors",
  "event_type": "MEMORY_CREATED",
  "condition": {
    "field": "payload.tags",
    "operator": "contains",
    "value": "error"
  },
  "actions": [
    {
      "action_type": "GENERATE_REFLECTION",
      "config": {
        "outcome": "failure",
        "min_importance": 0.7
      }
    }
  ]
}
```

## Action Types

| Action Type | Description | Config Parameters |
|-------------|-------------|-------------------|
| `WEBHOOK` | Call external webhook | `url`, `method`, `headers`, `payload` |
| `EMAIL` | Send email notification | `to`, `subject`, `body` |
| `GENERATE_REFLECTION` | Trigger reflection generation | `outcome`, `min_importance` |
| `RUN_DECAY` | Execute decay cycle | `decay_rate`, `tenant_id` |
| `RUN_SUMMARIZATION` | Create session summary | `session_id`, `min_events` |
| `CUSTOM_FUNCTION` | Execute custom code | `function_name`, `args` |

## API Usage

### Process Event

```python
from apps.memory_api.services.rules_engine import RulesEngine
from apps/memory_api/models.event_models import Event, EventType

# Initialize engine
engine = RulesEngine(pool)

# Create event
event = Event(
    event_id=str(uuid4()),
    event_type=EventType.MEMORY_CREATED,
    timestamp=datetime.now(timezone.utc),
    tenant_id="tenant-123",
    project_id="default",
    payload={
        "memory_id": "mem-456",
        "importance": 0.95,
        "layer": "em",
        "tags": ["critical", "error"]
    }
)

# Process event (will match and execute triggers)
result = await engine.process_event(event)

# Returns:
# {
#   "event_id": "...",
#   "triggers_matched": 2,
#   "actions_executed": 3,
#   "executions": [...]
# }
```

### Create Trigger Rule

```python
from apps.memory_api.repositories.trigger_repository import TriggerRepository

repo = TriggerRepository(pool)

trigger = await repo.create_trigger(
    tenant_id="tenant-123",
    project_id="default",
    name="Budget alert",
    event_type=EventType.BUDGET_EXCEEDED,
    condition={
        "field": "payload.budget_percent",
        "operator": "gt",
        "value": 0.9
    },
    actions=[
        {
            "action_type": "EMAIL",
            "config": {
                "to": "admin@example.com",
                "subject": "Budget Alert: 90% exceeded",
                "body": "Cost budget has reached 90%"
            }
        }
    ]
)
```

## Rate Limiting

Triggers support rate limiting to prevent excessive actions:

```json
{
  "rate_limit": {
    "max_executions": 10,
    "time_window_seconds": 3600
  },
  "cooldown_seconds": 300
}
```

## Integration with ISO 42001

Rules Engine supports governance and compliance:

- **Audit Trail**: All rule executions are logged
- **Access Control**: Rules are tenant-isolated
- **Risk Management**: Rules can enforce risk policies
- **Retention Policies**: Rules can trigger data deletion

See: `docs/RAE-ISO_42001.md` for compliance mapping.

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `RULES_ENGINE_ENABLED` | `True` | Enable rules engine |
| `RULES_ENGINE_MAX_ACTIONS` | `10` | Max actions per trigger |
| `RULES_ENGINE_RETRY_ATTEMPTS` | `3` | Action retry count |

## Monitoring

### Structured Logs

```python
logger.info("processing_event", event_id=..., event_type=...)
logger.info("triggers_matched", count=2)
logger.info("action_executed", action_type=..., status=...)
logger.error("action_failed", action_type=..., error=...)
```

### Metrics

- `rae_rules_events_processed_total` - Total events processed
- `rae_rules_triggers_matched_total` - Triggers matched
- `rae_rules_actions_executed_total` - Actions executed
- `rae_rules_action_failures_total` - Failed actions

## Related Documentation

- [Background Workers](./BACKGROUND_WORKERS.md) - Integration with maintenance tasks
- [Reflection Engine V2](./REFLECTION_ENGINE_V2_IMPLEMENTATION.md) - Reflection actions
- [ISO 42001 Implementation](./ISO42001_IMPLEMENTATION_MAP.md) - Compliance rules
