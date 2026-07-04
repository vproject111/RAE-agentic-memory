"""
Task context for Math Layer Controller decisions

TaskContext: Complete context for making a math level decision
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..base import MemorySnapshot
from .types import TaskType


@dataclass
class TaskContext:
    """
    Complete context for making a math level decision.

    This is the input to MathLayerController.decide().
    It contains everything the controller needs to make an informed decision.

    Attributes:
        task_type: Type of operation being performed
        memory_snapshot: Current state of memory (optional, for metrics)
        previous_snapshot: Previous state (optional, for drift detection)
        query_results: Recent query results (optional, for ORR calculation)
        session_metadata: Information about current session
        budget_constraints: Cost and latency limits
        config_overrides: Per-request config overrides
    """

    # Required
    task_type: TaskType

    # Memory state (optional)
    memory_snapshot: Optional[MemorySnapshot] = None
    previous_snapshot: Optional[MemorySnapshot] = None

    # Recent performance (optional)
    query_results: Optional[List[Dict[str, Any]]] = None

    # Session context
    session_metadata: Dict[str, Any] = field(
        default_factory=lambda: {
            "session_id": None,
            "turn_number": 0,
            "agent_id": None,
            "tenant_id": None,
        }
    )

    # Constraints
    budget_constraints: Dict[str, Any] = field(
        default_factory=lambda: {
            "max_cost_usd": None,
            "max_latency_ms": None,
            "prefer_cheap": False,
        }
    )

    # Config overrides
    config_overrides: Dict[str, Any] = field(default_factory=dict)

    @property
    def turn_number(self) -> int:
        """Current turn in session"""
        return int(self.session_metadata.get("turn_number", 0))

    @property
    def is_first_turn(self) -> bool:
        """Whether this is the first turn"""
        return self.turn_number <= 1
