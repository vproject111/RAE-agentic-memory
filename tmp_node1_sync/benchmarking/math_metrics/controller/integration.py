"""
Integration helpers for MathLayerController with RAE systems.

Provides convenience methods for common integration patterns.
"""

from typing import Any, Dict, Optional
from uuid import UUID

from ..base import MemorySnapshot
from .context import TaskContext
from .controller import MathLayerController
from .types import TaskType


class MathControllerIntegration:
    """
    Integration layer between MathLayerController and RAE services.

    Provides convenience methods for common integration patterns.
    """

    def __init__(self, controller: Optional[MathLayerController] = None):
        """
        Initialize integration.

        Args:
            controller: MathLayerController instance, creates default if None
        """
        self.controller = controller or MathLayerController()

    def decide_for_retrieval(
        self,
        tenant_id: UUID,
        query: str,
        memory_snapshot: Optional[MemorySnapshot] = None,
        session_metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Make math level decision for memory retrieval.

        Usage in memory retrieval endpoint:
            integration = MathControllerIntegration()
            decision = integration.decide_for_retrieval(
                tenant_id=tenant_id,
                query=query,
                memory_snapshot=snapshot,
            )

            if decision.selected_level == MathLevel.L1:
                results = l1_retrieval(query, **decision.params)
            elif decision.selected_level == MathLevel.L2:
                results = l2_retrieval(query, **decision.params)
        """
        context = TaskContext(
            task_type=TaskType.MEMORY_RETRIEVE,
            memory_snapshot=memory_snapshot,
            session_metadata={
                "tenant_id": str(tenant_id),
                **(session_metadata or {}),
            },
        )

        return self.controller.decide(context)

    def decide_for_reflection(
        self,
        tenant_id: UUID,
        is_deep: bool,
        memory_snapshot: Optional[MemorySnapshot] = None,
        cost_budget: Optional[float] = None,
    ):
        """
        Make math level decision for reflection operation.
        """
        task_type = TaskType.REFLECTION_DEEP if is_deep else TaskType.REFLECTION_LIGHT

        context = TaskContext(
            task_type=task_type,
            memory_snapshot=memory_snapshot,
            session_metadata={"tenant_id": str(tenant_id)},
            budget_constraints={"max_cost_usd": cost_budget},
        )

        return self.controller.decide(context)

    def decide_for_consolidation(
        self,
        tenant_id: UUID,
        memory_snapshot: MemorySnapshot,
        previous_snapshot: Optional[MemorySnapshot] = None,
    ):
        """
        Make math level decision for memory consolidation.
        """
        context = TaskContext(
            task_type=TaskType.MEMORY_CONSOLIDATE,
            memory_snapshot=memory_snapshot,
            previous_snapshot=previous_snapshot,
            session_metadata={"tenant_id": str(tenant_id)},
        )

        return self.controller.decide(context)


# Singleton instance for easy access
_default_controller: Optional[MathLayerController] = None


def get_math_controller() -> MathLayerController:
    """Get singleton MathLayerController instance"""
    global _default_controller
    if _default_controller is None:
        _default_controller = MathLayerController()
    return _default_controller


def set_math_controller(controller: MathLayerController) -> None:
    """Set singleton instance (for testing/custom configs)"""
    global _default_controller
    _default_controller = controller
