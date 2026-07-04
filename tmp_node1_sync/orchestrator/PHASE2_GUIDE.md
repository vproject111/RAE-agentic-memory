# Phase 2 - Production Features Guide

Phase 2 adds state persistence, retry logic, structured logging, and multi-task processing to the orchestrator.

## New Components

### 1. State Machine (`core/state_machine.py`)

Manages task lifecycle with persistence to JSON files.

**States**:
- `NEW` - Task just created
- `PLANNING` - Creating plan
- `PLAN_REVIEW` - Reviewing plan
- `PLAN_APPROVED` - Plan approved, ready for implementation
- `PLAN_REJECTED` - Plan rejected
- `IMPLEMENTING` - Executing steps
- `CODE_REVIEW` - Reviewing code
- `QUALITY_GATE` - Running quality checks
- `AWAITING_HUMAN` - Needs human review
- `DONE` - Successfully completed
- `FAILED` - Failed after retries

**Usage**:
```python
from orchestrator.core import StateMachine, TaskState

# Initialize
state_machine = StateMachine(state_dir="orchestrator/state")

# Create task
task_exec = state_machine.create_task(task_def)

# Update state
state_machine.update_task_state(
    task_id="RAE-001",
    new_state=TaskState.PLANNING
)

# Add steps
step = state_machine.add_step(
    task_id="RAE-001",
    step_id="S1",
    max_attempts=3
)

# Update step
state_machine.update_step_state(
    task_id="RAE-001",
    step_id="S1",
    new_state=StepState.IMPLEMENTING,
    implementer_model="gemini-2.0-flash"
)

# Get tasks needing human review
tasks = state_machine.get_tasks_needing_human_review()
```

**State Files**:
- Saved to: `orchestrator/state/{task_id}.json`
- Auto-loaded on startup
- Survive orchestrator restarts

### 2. Retry Handler (`core/retry_handler.py`)

Automatic retry with exponential backoff.

**Strategies**:
- `IMMEDIATE` - Retry immediately
- `EXPONENTIAL_BACKOFF` - Wait 2^attempt seconds (default)
- `FIXED_DELAY` - Fixed delay

**Usage**:
```python
from orchestrator.core import RetryHandler, RetryConfig, RetryStrategy

# Configure
config = RetryConfig(
    max_attempts=3,
    strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
    base_delay=1.0,  # 1s, 2s, 4s, 8s, ...
    max_delay=60.0,  # cap at 60s
    timeout=300.0    # per-attempt timeout
)

handler = RetryHandler(config)

# Execute with retry
result = await handler.execute_with_retry(
    some_async_function,
    arg1, arg2,
    context={"task_id": "RAE-001", "step_id": "S2"}
)

# Or use decorator
@retry_on_failure(max_attempts=3)
async def flaky_operation():
    # Your code here
    pass
```

**Error Classification**:
```python
from orchestrator.core import ErrorClassifier, RetryableError, NonRetryableError

# Automatically classify errors
try:
    result = await some_operation()
except Exception as e:
    wrapped = ErrorClassifier.wrap_error(e)
    # Returns RetryableError or NonRetryableError
    raise wrapped
```

**Non-retryable errors**:
- Authentication failed
- Invalid API key
- Permission denied
- Not found
- Bad request
- Validation error

**Retryable errors**:
- Timeout
- Connection error
- Rate limit
- Service unavailable
- Internal server error

### 3. Run Logger (`core/run_logger.py`)

Structured logging to `ORCHESTRATOR_RUN_LOG.md`.

**Usage**:
```python
from orchestrator.core import RunLogger

logger = RunLogger("ORCHESTRATOR_RUN_LOG.md")

# Start run
logger.start_run(
    run_id="2025-12-10T10:30:00",
    tasks=["RAE-001", "RAE-002"]
)

# Log task start
logger.log_task_start(
    task_id="RAE-001",
    goal="Implement search strategies",
    risk="high",
    area="core"
)

# Log routing decision
logger.log_routing_decision(
    role="planner",
    model="claude-sonnet-4-5",
    reason="High-risk core task requires best reasoning",
    task_id="RAE-001"
)

# Log LLM call
logger.log_llm_call(
    provider="claude_api",
    model="claude-sonnet-4-5",
    role="planner",
    task_id="RAE-001",
    success=True,
    cost_usd=0.0045,
    duration=12.3
)

# Log quality gate
logger.log_quality_gate(
    task_id="RAE-001",
    passed=False,
    checks={
        "pytest": True,
        "mypy": False,
        "ruff": True,
        "coverage": True
    },
    duration=45.2
)

# Log retry
logger.log_retry(
    task_id="RAE-001",
    step_id="S2",
    attempt=2,
    max_attempts=3,
    reason="Type checking failed, re-implementing with fixes"
)

# Log human review needed
logger.log_human_review_required(
    task_id="RAE-001",
    reason="Plan rejected by reviewer 3 times",
    details={"last_review": {...}}
)

# Log task completion
logger.log_task_complete(
    task_id="RAE-001",
    status="done",
    duration=1234.5,
    cost_usd=0.38
)

# End run
logger.end_run(
    run_id="2025-12-10T10:30:00",
    summary={
        "duration": 1500.0,
        "total_cost_usd": 0.85,
        "completed": 2,
        "failed": 0,
        "needs_review": 0
    }
)
```

**Log Format** (markdown):
```markdown
## Run: 2025-12-10T10:30:00

**Started**: 2025-12-10T10:30:00.123Z

**Tasks**: RAE-001, RAE-002

### Execution Log

- `10:30:01` ℹ️  **task**: Task RAE-001 started: Implement search strategies
- `10:30:02` ℹ️  **routing**: Routing [planner] → claude-sonnet-4-5: High-risk core task (task=RAE-001)
- `10:30:15` ℹ️  **llm_call**: ✅ LLM call [planner] claude_api/claude-sonnet-4-5 (task=RAE-001, cost=$0.0045, 12.3s)
- `10:32:45` ❌ **quality_gate**: Quality Gate ❌ FAILED (task=RAE-001, 45.2s)
  - ❌ mypy failed
- `10:32:46` ⚠️  **retry**: ⚠️  Retry attempt 2/3 for step S2 (task=RAE-001): Type checking failed
- `10:45:20` ✅ **task**: ✅ Task RAE-001 completed with status: done (duration=900.5s, cost=$0.38)

### Run Summary

**Ended**: 2025-12-10T11:00:00.456Z

**Total Duration**: 1500.0s

**Total Cost**: $0.85

**Tasks Completed**: 2

**Tasks Failed**: 0

**Tasks Needing Review**: 0

---
```

## Integration Example

```python
import asyncio
from orchestrator.core import (
    StateMachine, TaskState, StepState,
    RetryHandler, RetryConfig,
    RunLogger
)

async def execute_task_with_phase2(task_def):
    """Execute task with Phase 2 features."""

    # Initialize components
    state_machine = StateMachine()
    retry_handler = RetryHandler(RetryConfig(max_attempts=3))
    run_logger = RunLogger()

    # Create task execution
    task_exec = state_machine.create_task(task_def)
    task_id = task_def["id"]

    # Log task start
    run_logger.log_task_start(
        task_id=task_id,
        goal=task_def["goal"],
        risk=task_def["risk"],
        area=task_def["area"]
    )

    try:
        # Phase 1: Planning with retry
        state_machine.update_task_state(task_id, TaskState.PLANNING)

        plan = await retry_handler.execute_with_retry(
            create_plan,
            task_def,
            context={"task_id": task_id}
        )

        state_machine.update_task_state(
            task_id,
            TaskState.PLAN_APPROVED,
            plan=plan
        )

        # Phase 2: Implementation with retry for each step
        state_machine.update_task_state(task_id, TaskState.IMPLEMENTING)

        for step in plan["steps"]:
            # Add step to state
            step_exec = state_machine.add_step(
                task_id=task_id,
                step_id=step["id"]
            )

            # Try implementation with retries
            attempt = 1
            while attempt <= 3:
                try:
                    state_machine.update_step_state(
                        task_id, step["id"],
                        StepState.IMPLEMENTING,
                        attempt=attempt
                    )

                    impl = await implement_step(step)

                    state_machine.update_step_state(
                        task_id, step["id"],
                        StepState.COMPLETED,
                        implementation=impl
                    )
                    break  # Success

                except Exception as e:
                    if attempt >= 3:
                        # Max retries exhausted
                        state_machine.update_step_state(
                            task_id, step["id"],
                            StepState.FAILED,
                            error=str(e)
                        )
                        run_logger.log_retry(
                            task_id, step["id"],
                            attempt, 3,
                            "Max retries exhausted"
                        )
                        raise

                    # Retry
                    run_logger.log_retry(
                        task_id, step["id"],
                        attempt, 3,
                        str(e)
                    )
                    attempt += 1
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff

        # Phase 3: Quality Gate
        state_machine.update_task_state(task_id, TaskState.QUALITY_GATE)

        gate_result = await run_quality_gate(task_id)

        state_machine.add_quality_gate_result(task_id, gate_result)

        if gate_result["passed"]:
            state_machine.update_task_state(task_id, TaskState.DONE)
            run_logger.log_task_complete(
                task_id, "done",
                duration=120.0,
                cost_usd=0.15
            )
        else:
            state_machine.update_task_state(task_id, TaskState.FAILED)
            run_logger.log_quality_gate(
                task_id, False,
                gate_result["checks"],
                duration=30.0
            )

    except Exception as e:
        state_machine.update_task_state(
            task_id, TaskState.FAILED,
            error=str(e)
        )
        run_logger.log_task_complete(
            task_id, "failed",
            duration=60.0,
            cost_usd=0.05
        )
```

## Benefits

### 1. Crash Recovery

If orchestrator crashes mid-task:
```bash
# Restart orchestrator
python -m orchestrator.main

# State is automatically reloaded from orchestrator/state/*.json
# Tasks can be resumed from where they left off
```

### 2. Human Review Workflow

Check tasks needing review:
```python
from orchestrator.core import StateMachine

state_machine = StateMachine()
tasks = state_machine.get_tasks_needing_human_review()

for task in tasks:
    print(f"Task {task.task_id}: {task.error}")
    print(f"Plan: {task.plan}")
    print(f"Last review: {task.plan_review}")

    # Decision:
    # 1. Approve manually → update state to IMPLEMENTING
    # 2. Reject → update state to FAILED
    # 3. Modify plan → update plan, set to PLANNING
```

### 3. Cost Tracking

```python
# Per-task costs tracked automatically
task_exec = state_machine.get_task("RAE-001")
print(f"Total cost: ${task_exec.total_cost_usd:.4f}")

# Models used
print(f"Planner: {task_exec.planner_model}")
print(f"Plan Reviewer: {task_exec.plan_reviewer_model}")
for step in task_exec.steps:
    print(f"Step {step.step_id}: {step.implementer_model} → {step.reviewer_model}")
```

### 4. Detailed Audit Trail

All actions logged to `ORCHESTRATOR_RUN_LOG.md`:
- Every model routing decision
- Every LLM call (model, cost, duration)
- Every quality gate run (passed/failed, which checks)
- Every retry attempt (reason, attempt number)
- Full task lifecycle

## CLI Commands

```bash
# Run tasks with Phase 2
python -m orchestrator.main --tasks .orchestrator/tasks.yaml

# Resume failed tasks
python -m orchestrator.main --resume

# Show tasks needing review
python -m orchestrator.main --review

# Get run summary
python -m orchestrator.main --summary

# Clean state (start fresh)
python -m orchestrator.main --clean-state
```

## Next: Phase 3

Phase 3 will add:
- RAE memory integration
- Historical performance tracking
- Dynamic routing optimization based on past results
- Automatic task generation from analysis
