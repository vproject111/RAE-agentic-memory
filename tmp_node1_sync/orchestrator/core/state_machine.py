"""State machine for task lifecycle with persistence."""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class TaskState(Enum):
    """Task lifecycle states."""

    NEW = "new"
    PLANNING = "planning"
    PLAN_REVIEW = "plan_review"
    PLAN_APPROVED = "plan_approved"
    PLAN_REJECTED = "plan_rejected"
    IMPLEMENTING = "implementing"
    CODE_REVIEW = "code_review"
    QUALITY_GATE = "quality_gate"
    AWAITING_HUMAN = "awaiting_human_review"
    DONE = "done"
    FAILED = "failed"


class StepState(Enum):
    """Step execution states."""

    PENDING = "pending"
    IMPLEMENTING = "implementing"
    CODE_REVIEW = "code_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    RETRY = "retry"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class StepExecution:
    """State of a single step execution."""

    step_id: str
    state: StepState
    attempt: int = 1
    max_attempts: int = 3
    implementation: Optional[Dict[str, Any]] = None
    code_review: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    implementer_model: Optional[str] = None
    reviewer_model: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        d = asdict(self)
        d["state"] = self.state.value
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StepExecution":
        """Create from dictionary."""
        data["state"] = StepState(data["state"])
        return cls(**data)


@dataclass
class TaskExecution:
    """State of a task execution."""

    task_id: str
    state: TaskState
    task_def: Dict[str, Any]
    plan: Optional[Dict[str, Any]] = None
    plan_review: Optional[Dict[str, Any]] = None
    steps: List[StepExecution] = field(default_factory=list)
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    quality_gate_results: List[Dict[str, Any]] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3

    # Metadata
    planner_model: Optional[str] = None
    plan_reviewer_model: Optional[str] = None
    total_cost_usd: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        d = asdict(self)
        d["state"] = self.state.value
        d["steps"] = [step.to_dict() for step in self.steps]
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskExecution":
        """Create from dictionary."""
        data["state"] = TaskState(data["state"])
        data["steps"] = [StepExecution.from_dict(s) for s in data.get("steps", [])]
        return cls(**data)

    def get_current_step(self) -> Optional[StepExecution]:
        """Get currently executing step."""
        for step in self.steps:
            if step.state in [
                StepState.PENDING,
                StepState.IMPLEMENTING,
                StepState.CODE_REVIEW,
            ]:
                return step
        return None

    def can_retry(self) -> bool:
        """Check if task can be retried."""
        return self.retry_count < self.max_retries

    def get_failed_steps(self) -> List[StepExecution]:
        """Get list of failed steps."""
        return [step for step in self.steps if step.state == StepState.FAILED]


class StateMachine:
    """Manages task state with persistence."""

    def __init__(self, state_dir: str = "orchestrator/state"):
        """Initialize state machine.

        Args:
            state_dir: Directory to store state files
        """
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)

        # In-memory cache
        self._tasks: Dict[str, TaskExecution] = {}

        # Load existing state
        self._load_all_state()

    def _load_all_state(self):
        """Load all task state from disk."""
        for state_file in self.state_dir.glob("*.json"):
            try:
                with open(state_file) as f:
                    data = json.load(f)
                    task = TaskExecution.from_dict(data)
                    self._tasks[task.task_id] = task
            except Exception as e:
                print(f"Failed to load state from {state_file}: {e}")

    def _save_state(self, task: TaskExecution):
        """Save task state to disk.

        Args:
            task: Task execution to save
        """
        state_file = self.state_dir / f"{task.task_id}.json"
        with open(state_file, "w") as f:
            json.dump(task.to_dict(), f, indent=2)

    def create_task(self, task_def: Dict[str, Any]) -> TaskExecution:
        """Create new task execution.

        Args:
            task_def: Task definition

        Returns:
            Task execution object
        """
        task = TaskExecution(
            task_id=task_def["id"],
            state=TaskState.NEW,
            task_def=task_def,
            started_at=datetime.utcnow().isoformat(),
        )

        self._tasks[task.task_id] = task
        self._save_state(task)

        return task

    def get_task(self, task_id: str) -> Optional[TaskExecution]:
        """Get task execution by ID.

        Args:
            task_id: Task identifier

        Returns:
            Task execution or None
        """
        return self._tasks.get(task_id)

    def update_task_state(
        self, task_id: str, new_state: TaskState, **kwargs
    ) -> TaskExecution:
        """Update task state.

        Args:
            task_id: Task identifier
            new_state: New state
            **kwargs: Additional fields to update

        Returns:
            Updated task execution
        """
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        task.state = new_state

        # Update additional fields
        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)

        # Mark completion time
        if new_state in [TaskState.DONE, TaskState.FAILED]:
            task.completed_at = datetime.utcnow().isoformat()

        self._save_state(task)
        return task

    def add_step(
        self, task_id: str, step_id: str, max_attempts: int = 3
    ) -> StepExecution:
        """Add step to task.

        Args:
            task_id: Task identifier
            step_id: Step identifier
            max_attempts: Maximum retry attempts

        Returns:
            Step execution object
        """
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        step = StepExecution(
            step_id=step_id,
            state=StepState.PENDING,
            max_attempts=max_attempts,
            started_at=datetime.utcnow().isoformat(),
        )

        task.steps.append(step)
        self._save_state(task)

        return step

    def update_step_state(
        self, task_id: str, step_id: str, new_state: StepState, **kwargs
    ) -> StepExecution:
        """Update step state.

        Args:
            task_id: Task identifier
            step_id: Step identifier
            new_state: New state
            **kwargs: Additional fields to update

        Returns:
            Updated step execution
        """
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        step = None
        for s in task.steps:
            if s.step_id == step_id:
                step = s
                break

        if not step:
            raise ValueError(f"Step {step_id} not found in task {task_id}")

        step.state = new_state

        # Update additional fields
        for key, value in kwargs.items():
            if hasattr(step, key):
                setattr(step, key, value)

        # Mark completion time
        if new_state in [StepState.COMPLETED, StepState.FAILED]:
            step.completed_at = datetime.utcnow().isoformat()

        self._save_state(task)
        return step

    def increment_step_attempt(self, task_id: str, step_id: str) -> StepExecution:
        """Increment step retry attempt.

        Args:
            task_id: Task identifier
            step_id: Step identifier

        Returns:
            Updated step execution
        """
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        for step in task.steps:
            if step.step_id == step_id:
                step.attempt += 1
                step.state = StepState.RETRY
                self._save_state(task)
                return step

        raise ValueError(f"Step {step_id} not found in task {task_id}")

    def get_tasks_by_state(self, state: TaskState) -> List[TaskExecution]:
        """Get all tasks in a specific state.

        Args:
            state: Task state to filter by

        Returns:
            List of task executions
        """
        return [task for task in self._tasks.values() if task.state == state]

    def get_active_tasks(self) -> List[TaskExecution]:
        """Get all active (not completed/failed) tasks.

        Returns:
            List of active task executions
        """
        active_states = [
            TaskState.NEW,
            TaskState.PLANNING,
            TaskState.PLAN_REVIEW,
            TaskState.PLAN_APPROVED,
            TaskState.IMPLEMENTING,
            TaskState.CODE_REVIEW,
            TaskState.QUALITY_GATE,
        ]
        return [task for task in self._tasks.values() if task.state in active_states]

    def get_tasks_needing_human_review(self) -> List[TaskExecution]:
        """Get tasks awaiting human review.

        Returns:
            List of tasks needing review
        """
        return self.get_tasks_by_state(TaskState.AWAITING_HUMAN)

    def add_quality_gate_result(self, task_id: str, result: Dict[str, Any]):
        """Add quality gate result to task.

        Args:
            task_id: Task identifier
            result: Quality gate result
        """
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        task.quality_gate_results.append(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "result": result,
            }
        )

        self._save_state(task)

    def add_cost(self, task_id: str, cost_usd: float):
        """Add cost to task total.

        Args:
            task_id: Task identifier
            cost_usd: Cost in USD to add
        """
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        task.total_cost_usd += cost_usd
        self._save_state(task)

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all tasks.

        Returns:
            Summary dictionary
        """
        total_tasks = len(self._tasks)
        by_state = {}

        for state in TaskState:
            count = len(self.get_tasks_by_state(state))
            if count > 0:
                by_state[state.value] = count

        total_cost = sum(task.total_cost_usd for task in self._tasks.values())

        return {
            "total_tasks": total_tasks,
            "by_state": by_state,
            "total_cost_usd": round(total_cost, 4),
            "active_tasks": len(self.get_active_tasks()),
            "needs_human_review": len(self.get_tasks_needing_human_review()),
        }
