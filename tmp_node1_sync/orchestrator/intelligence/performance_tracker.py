"""Performance tracking for orchestrator executions.

Tracks model performance, costs, success rates, and failure patterns.
Integrates with RAE memory for persistent storage and querying.
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class TaskOutcome(Enum):
    """Outcome of task execution."""

    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    HUMAN_REVIEW = "human_review"
    CANCELLED = "cancelled"


@dataclass
class ExecutionRecord:
    """Record of a single task execution.

    Stores all metadata needed for performance analysis and learning.
    """

    # Task metadata
    task_id: str
    task_area: str
    task_risk: str
    task_complexity: str

    # Model choices
    planner_model: str
    planner_provider: str
    implementer_model: str
    implementer_provider: str

    # Execution results
    outcome: TaskOutcome
    duration_seconds: float
    total_cost_usd: float

    # Performance metrics
    num_steps: int
    num_retries: int
    quality_gate_passed: bool
    code_review_passed: bool
    plan_review_passed: bool

    # Error information
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    failed_step: Optional[str] = None

    # Timestamps
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None

    # Additional context
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        data = asdict(self)
        data["outcome"] = self.outcome.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionRecord":
        """Create from dictionary."""
        data = data.copy()
        data["outcome"] = TaskOutcome(data["outcome"])
        return cls(**data)


class PerformanceTracker:
    """Tracks and persists orchestrator performance data.

    Stores execution records locally and syncs with RAE memory for
    distributed access and historical analysis.
    """

    def __init__(
        self,
        storage_dir: str = "orchestrator/intelligence/data",
        rae_integration: bool = False,
    ):
        """Initialize performance tracker.

        Args:
            storage_dir: Directory for local storage
            rae_integration: Whether to sync with RAE memory
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.rae_integration = rae_integration
        self._records: List[ExecutionRecord] = []

        # Load existing records
        self._load_records()

    def _load_records(self):
        """Load existing records from storage."""
        records_file = self.storage_dir / "execution_records.jsonl"

        if not records_file.exists():
            return

        try:
            with open(records_file, "r") as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        record = ExecutionRecord.from_dict(data)
                        self._records.append(record)

            logger.info(f"Loaded {len(self._records)} execution records")
        except Exception as e:
            logger.error(f"Failed to load execution records: {e}")

    def _save_record(self, record: ExecutionRecord):
        """Append record to storage file."""
        records_file = self.storage_dir / "execution_records.jsonl"

        try:
            with open(records_file, "a") as f:
                json.dump(record.to_dict(), f)
                f.write("\n")
        except Exception as e:
            logger.error(f"Failed to save execution record: {e}")

    def record_execution(
        self,
        task_id: str,
        task_area: str,
        task_risk: str,
        task_complexity: str,
        planner_model: str,
        planner_provider: str,
        implementer_model: str,
        implementer_provider: str,
        outcome: TaskOutcome,
        duration_seconds: float,
        total_cost_usd: float,
        num_steps: int,
        num_retries: int = 0,
        quality_gate_passed: bool = True,
        code_review_passed: bool = True,
        plan_review_passed: bool = True,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
        failed_step: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ExecutionRecord:
        """Record a task execution.

        Args:
            task_id: Task identifier
            task_area: Task area (core, api, docs, etc.)
            task_risk: Risk level (low, medium, high)
            task_complexity: Complexity level
            planner_model: Model used for planning
            planner_provider: Provider of planner model
            implementer_model: Model used for implementation
            implementer_provider: Provider of implementer model
            outcome: Task outcome
            duration_seconds: Total execution duration
            total_cost_usd: Total cost in USD
            num_steps: Number of implementation steps
            num_retries: Number of retry attempts
            quality_gate_passed: Whether quality gate passed
            code_review_passed: Whether code review passed
            plan_review_passed: Whether plan review passed
            error_type: Type of error if failed
            error_message: Error message if failed
            failed_step: Step that failed
            metadata: Additional context

        Returns:
            Created execution record
        """
        record = ExecutionRecord(
            task_id=task_id,
            task_area=task_area,
            task_risk=task_risk,
            task_complexity=task_complexity,
            planner_model=planner_model,
            planner_provider=planner_provider,
            implementer_model=implementer_model,
            implementer_provider=implementer_provider,
            outcome=outcome,
            duration_seconds=duration_seconds,
            total_cost_usd=total_cost_usd,
            num_steps=num_steps,
            num_retries=num_retries,
            quality_gate_passed=quality_gate_passed,
            code_review_passed=code_review_passed,
            plan_review_passed=plan_review_passed,
            error_type=error_type,
            error_message=error_message,
            failed_step=failed_step,
            completed_at=datetime.utcnow().isoformat(),
            metadata=metadata or {},
        )

        # Store in memory
        self._records.append(record)

        # Persist to disk
        self._save_record(record)

        # Sync with RAE if enabled
        if self.rae_integration:
            self._sync_to_rae(record)

        logger.info(
            f"Recorded execution: task={task_id}, outcome={outcome.value}, "
            f"cost=${total_cost_usd:.4f}, duration={duration_seconds:.1f}s"
        )

        return record

    def _sync_to_rae(self, record: ExecutionRecord):
        """Sync execution record to RAE memory.

        TODO: Implement RAE integration once RAE core is ready.
        """
        # Placeholder for RAE integration
        logger.debug(f"RAE sync: {record.task_id}")

    def get_all_records(self) -> List[ExecutionRecord]:
        """Get all execution records.

        Returns:
            List of execution records
        """
        return self._records.copy()

    def get_records_by_outcome(self, outcome: TaskOutcome) -> List[ExecutionRecord]:
        """Get records by outcome.

        Args:
            outcome: Desired outcome

        Returns:
            Matching execution records
        """
        return [r for r in self._records if r.outcome == outcome]

    def get_records_by_area(self, area: str) -> List[ExecutionRecord]:
        """Get records by task area.

        Args:
            area: Task area (core, api, docs, etc.)

        Returns:
            Matching execution records
        """
        return [r for r in self._records if r.task_area == area]

    def get_records_by_model(
        self, model: str, role: str = "any"
    ) -> List[ExecutionRecord]:
        """Get records where a model was used.

        Args:
            model: Model identifier
            role: Role filter ('planner', 'implementer', 'any')

        Returns:
            Matching execution records
        """
        if role == "planner":
            return [r for r in self._records if r.planner_model == model]
        elif role == "implementer":
            return [r for r in self._records if r.implementer_model == model]
        else:
            return [
                r
                for r in self._records
                if r.planner_model == model or r.implementer_model == model
            ]

    def get_records_by_provider(
        self, provider: str, role: str = "any"
    ) -> List[ExecutionRecord]:
        """Get records where a provider was used.

        Args:
            provider: Provider name
            role: Role filter ('planner', 'implementer', 'any')

        Returns:
            Matching execution records
        """
        if role == "planner":
            return [r for r in self._records if r.planner_provider == provider]
        elif role == "implementer":
            return [r for r in self._records if r.implementer_provider == provider]
        else:
            return [
                r
                for r in self._records
                if r.planner_provider == provider or r.implementer_provider == provider
            ]

    def get_recent_records(self, limit: int = 100) -> List[ExecutionRecord]:
        """Get most recent execution records.

        Args:
            limit: Maximum number of records

        Returns:
            Recent execution records (newest first)
        """
        return sorted(self._records, key=lambda r: r.started_at, reverse=True)[:limit]

    def get_statistics(self) -> Dict[str, Any]:
        """Get overall performance statistics.

        Returns:
            Statistics dictionary
        """
        if not self._records:
            return {
                "total_tasks": 0,
                "success_rate": 0.0,
                "total_cost": 0.0,
                "avg_duration": 0.0,
            }

        successful = len([r for r in self._records if r.outcome == TaskOutcome.SUCCESS])
        total_cost = sum(r.total_cost_usd for r in self._records)
        total_duration = sum(r.duration_seconds for r in self._records)

        return {
            "total_tasks": len(self._records),
            "successful": successful,
            "failed": len(
                [r for r in self._records if r.outcome == TaskOutcome.FAILED]
            ),
            "partial": len(
                [r for r in self._records if r.outcome == TaskOutcome.PARTIAL]
            ),
            "human_review": len(
                [r for r in self._records if r.outcome == TaskOutcome.HUMAN_REVIEW]
            ),
            "success_rate": successful / len(self._records) if self._records else 0.0,
            "total_cost": total_cost,
            "avg_cost": total_cost / len(self._records),
            "total_duration": total_duration,
            "avg_duration": total_duration / len(self._records),
        }
