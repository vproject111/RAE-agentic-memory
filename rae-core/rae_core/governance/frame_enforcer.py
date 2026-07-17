import logging
from rae_core.models.contracts import AutonomyState
from rae_core.exceptions.base import ContractViolationError

logger = logging.getLogger("rae_core.governance.frame_enforcer")

class HardFrameEnforcer:
    """
    Enforces the Sequence of Autonomy state transitions programmatically in code.
    Blocks any tool execution or final answer return if states are out of sequence.
    """

    def __init__(self, mode: str = "hard"):
        self.mode = mode.lower()  # "hard" or "ordinary"
        self._current_state = AutonomyState.INIT
        self._journal = [AutonomyState.INIT]

    @property
    def current_state(self) -> AutonomyState:
        return self._current_state

    def transition_to(self, target_state: AutonomyState):
        """Transitions the agent to a target state, verifying compliance."""
        if self.mode != "hard":
            # Ordinary Mode: log transitions but do not enforce them strictly in code
            logger.info(f"ordinary_transition: from_state={self._current_state.value}, to_state={target_state.value}")
            self._current_state = target_state
            self._journal.append(target_state)
            return

        # Hard Frames Mode: Strict validation map
        valid_transitions = {
            AutonomyState.INIT: [AutonomyState.INTENT_DECLARED],
            AutonomyState.INTENT_DECLARED: [AutonomyState.RISK_ASSESSED],
            AutonomyState.RISK_ASSESSED: [AutonomyState.CAPABILITY_GRANTED],
            AutonomyState.CAPABILITY_GRANTED: [AutonomyState.SANDBOX_READY],
            AutonomyState.SANDBOX_READY: [AutonomyState.DRY_RUN_PASSED],
            AutonomyState.DRY_RUN_PASSED: [AutonomyState.QUALITY_GATE_PASSED],
            AutonomyState.QUALITY_GATE_PASSED: [AutonomyState.EVIDENCE_PACKED],
            AutonomyState.EVIDENCE_PACKED: [AutonomyState.DECISION_RECORDED],
            AutonomyState.DECISION_RECORDED: [AutonomyState.MEMORY_COMMITTED],
        }

        # Any state can transition to ROLLBACK_TRIGGERED on failure/error
        if target_state == AutonomyState.ROLLBACK_TRIGGERED:
            logger.warning(f"rollback_triggered: current_state={self._current_state.value}")
            self._current_state = target_state
            self._journal.append(target_state)
            return

        allowed = valid_transitions.get(self._current_state, [])
        if target_state not in allowed:
            err_msg = (
                f"Hard Frames Violation: Invalid state transition requested from "
                f"'{self._current_state.value}' to '{target_state.value}'. "
                f"Allowed target states are: {[s.value for s in allowed]}. "
                f"Flow Sequence MUST follow the Sequence of Autonomy contract."
            )
            logger.error(f"hard_frame_violation: from_state={self._current_state.value}, to_state={target_state.value}")
            raise ContractViolationError(err_msg)

        logger.info(f"hard_frame_transition: from_state={self._current_state.value}, to_state={target_state.value}")
        self._current_state = target_state
        self._journal.append(target_state)

    def get_journal(self):
        return [s.value for s in self._journal]
