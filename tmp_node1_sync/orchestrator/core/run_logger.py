"""Structured run logging to markdown file."""

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class RunLogEntry:
    """Single log entry."""

    timestamp: str
    level: str  # INFO, WARNING, ERROR
    category: str  # task, step, llm_call, quality_gate, routing
    message: str
    context: Dict[str, Any]


class RunLogger:
    """Logs orchestrator runs to structured markdown file."""

    def __init__(self, log_file: str = "ORCHESTRATOR_RUN_LOG.md"):
        """Initialize run logger.

        Args:
            log_file: Path to log file
        """
        self.log_file = Path(log_file)
        self.entries: List[RunLogEntry] = []

        # Create file if it doesn't exist
        if not self.log_file.exists():
            self._create_log_file()

    def _create_log_file(self):
        """Create initial log file with header."""
        with open(self.log_file, "w") as f:
            f.write("# Orchestrator Run Log\n\n")
            f.write("Structured log of orchestrator task executions.\n\n")
            f.write("---\n\n")

    def start_run(self, run_id: str, tasks: List[str]):
        """Log start of orchestrator run.

        Args:
            run_id: Unique run identifier
            tasks: List of task IDs to execute
        """
        timestamp = datetime.utcnow().isoformat()

        with open(self.log_file, "a") as f:
            f.write(f"## Run: {run_id}\n\n")
            f.write(f"**Started**: {timestamp}\n\n")
            f.write(f"**Tasks**: {', '.join(tasks)}\n\n")
            f.write("### Execution Log\n\n")

        self.entries = []
        logger.info(f"Started run {run_id} with tasks: {tasks}")

    def log_task_start(self, task_id: str, goal: str, risk: str, area: str):
        """Log task start.

        Args:
            task_id: Task identifier
            goal: Task goal description
            risk: Risk level
            area: Code area
        """
        entry = RunLogEntry(
            timestamp=datetime.utcnow().isoformat(),
            level="INFO",
            category="task",
            message=f"Task {task_id} started: {goal}",
            context={
                "task_id": task_id,
                "goal": goal,
                "risk": risk,
                "area": area,
            },
        )
        self.entries.append(entry)
        self._append_to_file(entry)

    def log_routing_decision(
        self,
        role: str,
        model: str,
        reason: str,
        task_id: str,
        step_id: Optional[str] = None,
    ):
        """Log model routing decision.

        Args:
            role: Agent role
            model: Selected model
            reason: Routing reason
            task_id: Task identifier
            step_id: Step identifier (if applicable)
        """
        context_str = f"task={task_id}"
        if step_id:
            context_str += f" step={step_id}"

        entry = RunLogEntry(
            timestamp=datetime.utcnow().isoformat(),
            level="INFO",
            category="routing",
            message=f"Routing [{role}] → {model}: {reason} ({context_str})",
            context={
                "role": role,
                "model": model,
                "reason": reason,
                "task_id": task_id,
                "step_id": step_id,
            },
        )
        self.entries.append(entry)
        self._append_to_file(entry)

    def log_llm_call(
        self,
        provider: str,
        model: str,
        role: str,
        task_id: str,
        success: bool,
        cost_usd: float = 0.0,
        duration: float = 0.0,
    ):
        """Log LLM call.

        Args:
            provider: LLM provider
            model: Model name
            role: Agent role
            task_id: Task identifier
            success: Whether call succeeded
            cost_usd: Cost in USD
            duration: Duration in seconds
        """
        status = "✅" if success else "❌"

        entry = RunLogEntry(
            timestamp=datetime.utcnow().isoformat(),
            level="INFO" if success else "ERROR",
            category="llm_call",
            message=f"{status} LLM call [{role}] {provider}/{model} (task={task_id}, cost=${cost_usd:.4f}, {duration:.1f}s)",
            context={
                "provider": provider,
                "model": model,
                "role": role,
                "task_id": task_id,
                "success": success,
                "cost_usd": cost_usd,
                "duration": duration,
            },
        )
        self.entries.append(entry)
        self._append_to_file(entry)

    def log_quality_gate(
        self, task_id: str, passed: bool, checks: Dict[str, bool], duration: float = 0.0
    ):
        """Log quality gate execution.

        Args:
            task_id: Task identifier
            passed: Whether gate passed
            checks: Individual check results
            duration: Duration in seconds
        """
        status = "✅ PASSED" if passed else "❌ FAILED"

        entry = RunLogEntry(
            timestamp=datetime.utcnow().isoformat(),
            level="INFO" if passed else "ERROR",
            category="quality_gate",
            message=f"Quality Gate {status} (task={task_id}, {duration:.1f}s)",
            context={
                "task_id": task_id,
                "passed": passed,
                "checks": checks,
                "duration": duration,
            },
        )
        self.entries.append(entry)
        self._append_to_file(entry)

        # Log individual check failures
        if not passed:
            for check_name, check_passed in checks.items():
                if not check_passed:
                    self._append_to_file_raw(f"  - ❌ {check_name} failed\n")

    def log_retry(
        self, task_id: str, step_id: str, attempt: int, max_attempts: int, reason: str
    ):
        """Log retry attempt.

        Args:
            task_id: Task identifier
            step_id: Step identifier
            attempt: Current attempt number
            max_attempts: Maximum attempts
            reason: Reason for retry
        """
        entry = RunLogEntry(
            timestamp=datetime.utcnow().isoformat(),
            level="WARNING",
            category="retry",
            message=f"⚠️  Retry attempt {attempt}/{max_attempts} for step {step_id} (task={task_id}): {reason}",
            context={
                "task_id": task_id,
                "step_id": step_id,
                "attempt": attempt,
                "max_attempts": max_attempts,
                "reason": reason,
            },
        )
        self.entries.append(entry)
        self._append_to_file(entry)

    def log_human_review_required(
        self, task_id: str, reason: str, details: Dict[str, Any]
    ):
        """Log that human review is required.

        Args:
            task_id: Task identifier
            reason: Why human review needed
            details: Additional details
        """
        entry = RunLogEntry(
            timestamp=datetime.utcnow().isoformat(),
            level="WARNING",
            category="human_review",
            message=f"🔍 Human review required for task {task_id}: {reason}",
            context={
                "task_id": task_id,
                "reason": reason,
                "details": details,
            },
        )
        self.entries.append(entry)
        self._append_to_file(entry)

    def log_task_complete(
        self, task_id: str, status: str, duration: float, cost_usd: float
    ):
        """Log task completion.

        Args:
            task_id: Task identifier
            status: Final status
            duration: Total duration in seconds
            cost_usd: Total cost in USD
        """
        if status == "done":
            icon = "✅"
            level = "INFO"
        elif status == "failed":
            icon = "❌"
            level = "ERROR"
        else:
            icon = "⚠️ "
            level = "WARNING"

        entry = RunLogEntry(
            timestamp=datetime.utcnow().isoformat(),
            level=level,
            category="task",
            message=f"{icon} Task {task_id} completed with status: {status} (duration={duration:.1f}s, cost=${cost_usd:.4f})",
            context={
                "task_id": task_id,
                "status": status,
                "duration": duration,
                "cost_usd": cost_usd,
            },
        )
        self.entries.append(entry)
        self._append_to_file(entry)

    def end_run(self, run_id: str, summary: Dict[str, Any]):
        """Log end of orchestrator run.

        Args:
            run_id: Run identifier
            summary: Run summary statistics
        """
        timestamp = datetime.utcnow().isoformat()

        with open(self.log_file, "a") as f:
            f.write("\n### Run Summary\n\n")
            f.write(f"**Ended**: {timestamp}\n\n")
            f.write(f"**Total Duration**: {summary.get('duration', 0):.1f}s\n\n")
            f.write(f"**Total Cost**: ${summary.get('total_cost_usd', 0):.4f}\n\n")
            f.write(f"**Tasks Completed**: {summary.get('completed', 0)}\n\n")
            f.write(f"**Tasks Failed**: {summary.get('failed', 0)}\n\n")
            f.write(f"**Tasks Needing Review**: {summary.get('needs_review', 0)}\n\n")
            f.write("---\n\n")

        logger.info(f"Ended run {run_id}: {summary}")

    def _append_to_file(self, entry: RunLogEntry):
        """Append log entry to file.

        Args:
            entry: Log entry to append
        """
        with open(self.log_file, "a") as f:
            # Format timestamp (just time for brevity)
            time_str = entry.timestamp.split("T")[1][:8]

            # Format level emoji
            level_emoji = {
                "INFO": "ℹ️ ",
                "WARNING": "⚠️ ",
                "ERROR": "❌",
            }.get(entry.level, "")

            # Write entry
            f.write(
                f"- `{time_str}` {level_emoji} **{entry.category}**: {entry.message}\n"
            )

    def _append_to_file_raw(self, text: str):
        """Append raw text to file.

        Args:
            text: Text to append
        """
        with open(self.log_file, "a") as f:
            f.write(text)
