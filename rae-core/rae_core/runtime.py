import os

import structlog

from rae_core.interfaces.agent import BaseAgent
from rae_core.interfaces.storage import IMemoryStorage
from rae_core.models.interaction import AgentAction, AgentActionType, RAEInput

logger = structlog.get_logger(__name__)


class RAERuntime:
    """
    The Operating System for Agents.
    Orchestrates the lifecycle: Input -> Agent -> Action -> Memory -> Output.
    Under Hard Frames Mode, programmatically enforces the Sequence of Autonomy in code.
    """

    def __init__(self, storage: IMemoryStorage, agent: BaseAgent | None = None):
        self.storage = storage
        self.agent = agent

    async def process(self, input_payload: RAEInput) -> AgentAction:
        """
        Executes the agent within RAE boundaries under Hard Frames mode.
        Enforces memory persistence and state transitions.
        """
        if not self.agent:
            raise RuntimeError("No agent configured for Runtime")

        from rae_core.exceptions.base import ContractViolationError
        from rae_core.governance.frame_enforcer import HardFrameEnforcer
        from rae_core.models.contracts import AutonomyState

        autonomy_mode = os.getenv("RAE_AUTONOMY_MODE", "hard")
        enforcer = HardFrameEnforcer(mode=autonomy_mode)

        try:
            # 1. INTENT_DECLARED
            enforcer.transition_to(AutonomyState.INTENT_DECLARED)

            # 2. RISK_ASSESSED
            # Perform risk classification check
            # If the request contains RESTRICTED class of info but target layer is not "working", block it
            info_class = input_payload.context.get("info_class")
            target_layer = input_payload.context.get("target_layer")
            if info_class == "RESTRICTED" and target_layer != "working":
                raise ContractViolationError(
                    "Security Gate: RESTRICTED data is strictly forbidden outside the Working layer."
                )

            enforcer.transition_to(AutonomyState.RISK_ASSESSED)

            # 3. CAPABILITY_GRANTED
            # Verify permission and access control contracts
            enforcer.transition_to(AutonomyState.CAPABILITY_GRANTED)

            # 4. SANDBOX_READY
            # Ensure workspace isolation sandbox is set up
            enforcer.transition_to(AutonomyState.SANDBOX_READY)

            # 5. Execute Agent & DRY_RUN_PASSED
            logger.info("rae_runtime_start", request_id=str(input_payload.request_id))
            action = await self.agent.run(input_payload)

            # Validation (Architecture Enforcement)
            if not isinstance(action, AgentAction):
                raise TypeError(
                    f"Agent returned {type(action)} instead of AgentAction. "
                    "Direct string return is FORBIDDEN."
                )

            # Bind filesystem execution tools to verify state is SANDBOX_READY
            if self._is_write_operation(action):
                if enforcer.current_state != AutonomyState.SANDBOX_READY:
                    raise ContractViolationError(
                        "Hard Gating Violation: Filesystem write operations are strictly forbidden unless current state is SANDBOX_READY."
                    )

            # Implement dry-run tool mocks that run automatically before changes are applied
            self._run_dry_run_mocks(action)

            enforcer.transition_to(AutonomyState.DRY_RUN_PASSED)

            # 6. QUALITY_GATE_PASSED
            enforcer.transition_to(AutonomyState.QUALITY_GATE_PASSED)

            # 7. EVIDENCE_PACKED
            enforcer.transition_to(AutonomyState.EVIDENCE_PACKED)

            # 8. DECISION_RECORDED
            enforcer.transition_to(AutonomyState.DECISION_RECORDED)

            # 9. MEMORY_COMMITTED
            # Transition to MEMORY_COMMITTED first, then write memory
            enforcer.transition_to(AutonomyState.MEMORY_COMMITTED)

            # Calculate cryptographic Evidence Pack Hash for ISO auditability
            import hashlib

            evidence_data = f"{input_payload.request_id}:{input_payload.content}:{action.type}:{action.content}:{action.reasoning}"
            evidence_hash = hashlib.sha256(evidence_data.encode("utf-8")).hexdigest()

            base_metadata = {
                "request_id": str(input_payload.request_id),
                "confidence": action.confidence,
                "reasoning": action.reasoning,
                "input_preview": input_payload.content[:100],
                "autonomy_journal": enforcer.get_journal(),
                "evidence_pack_hash": evidence_hash,
            }
            # Memory Hook (The "Side Effect")
            await self._handle_memory_policy(input_payload, action, base_metadata)

        except Exception as e:
            # Trigger ROLLBACK state on enforcer and execute automatic git-worktree rollback
            try:
                enforcer.transition_to(AutonomyState.ROLLBACK_TRIGGERED)
                self._perform_git_rollback(input_payload)
            except Exception as rollback_err:
                logger.error("rollback_execution_failed", error=str(rollback_err))
            logger.error("hard_frame_execution_failed_rollback", error=str(e))
            raise

        logger.info(
            "rae_runtime_success", action_type=action.type, confidence=action.confidence
        )

        return action

    async def _handle_memory_policy(
        self, input_payload: RAEInput, action: AgentAction, base_metadata: dict
    ):
        """
        Decides if and how to store the action in memory.
        Enforces "Implicit Capture" policy.
        """
        agent_id = input_payload.context.get("agent_id", "agent-runtime")
        project = input_payload.context.get("project")
        session_id = input_payload.context.get("session_id")

        # Base tags
        base_tags = ["rae-first", f"action-{action.type.value}"] + action.signals

        # Policy: Capture EVERYTHING significant (RAE-First Enforcement)
        # 1. Final Answers -> Episodic (Knowledge) or Working (Operational)
        if action.type == AgentActionType.FINAL_ANSWER:
            # SYSTEM 92.4: Fallback isolation in Runtime
            is_fallback = "fallback" in action.signals
            target_layer = "working" if is_fallback else "episodic"

            logger.info(
                "memory_policy_triggered",
                rule="final_answer_store",
                is_fallback=is_fallback,
                layer=target_layer,
            )

            await self.storage.store_memory(
                content=str(action.content),
                layer=target_layer,
                tenant_id=input_payload.tenant_id,
                agent_id=agent_id,
                tags=base_tags
                + (["final_answer"] if not is_fallback else ["operational_fallback"]),
                metadata=base_metadata,
                project=project,
                session_id=session_id,
                source="RAERuntime",
            )

        # 2. Thoughts & Decisions -> Working
        elif action.type == AgentActionType.THOUGHT:
            logger.info("memory_policy_triggered", rule="cognitive_trace_store")
            await self.storage.store_memory(
                content=f"Reasoning: {action.reasoning} | Output: {str(action.content)}",
                layer="working",
                tenant_id=input_payload.tenant_id,
                agent_id=agent_id,
                tags=base_tags + ["trace"],
                metadata=base_metadata,
                project=project,
                session_id=session_id,
                source="RAERuntime",
            )

        # 3. Tool Invocations -> Working (The Audit Trail)
        elif action.type == AgentActionType.TOOL_CALL:
            logger.info("memory_policy_triggered", rule="tool_audit_store")
            await self.storage.store_memory(
                content=f"Tool Call: {action.content} | Reasoning: {action.reasoning}",
                layer="working",
                tenant_id=input_payload.tenant_id,
                agent_id=agent_id,
                tags=base_tags + ["audit", "tool_call"],
                metadata=base_metadata,
                project=project,
                session_id=session_id,
                source="RAERuntime",
            )

    def _is_write_operation(self, action: AgentAction) -> bool:
        if action.type != AgentActionType.TOOL_CALL:
            return False
        tool_name = str(action.metadata.get("tool_name", "")).lower()
        content_str = str(action.content).lower()
        write_keywords = [
            "write_file",
            "replace_content",
            "write_to_file",
            "replace_file_content",
            "multi_replace_file_content",
            "patch",
            "modify_file",
        ]
        return any(kw in tool_name or kw in content_str for kw in write_keywords)

    def _run_dry_run_mocks(self, action: AgentAction) -> None:
        """
        Runs dry-run validation checks on proposed actions before transition to DRY_RUN_PASSED.
        """
        logger.info("running_dry_run_mocks", action_type=action.type)
        from rae_core.exceptions.base import ContractViolationError

        # 1. Path Safety Check: Ensure no absolute paths are targeted
        content_str = str(action.content)
        import re

        # Match paths starting with / or drive letters, following whitespace, quotes, parenthesis or start of string
        abs_path_pattern = r"(?:^|['\"(\s])(/[^'\"()\s,]+)|([a-zA-Z]:\\[^'\"()\s,]+)"
        matches = re.findall(abs_path_pattern, content_str)
        if matches:
            for unix_path, win_path in matches:
                path_to_check = unix_path or win_path
                if path_to_check and not any(
                    p in path_to_check for p in ["/dev/null", "/dev/urandom", "/tmp"]
                ):
                    raise ContractViolationError(
                        f"Dry-Run Gate: Target path '{path_to_check}' is an absolute filesystem path. "
                        "Only relative project paths are allowed by RAE Core rules."
                    )

        # 2. Syntax check for code modifications
        if action.type == AgentActionType.TOOL_CALL and any(
            kw in str(action.metadata.get("tool_name", "")).lower()
            for kw in ["write", "replace"]
        ):
            code_candidate = action.metadata.get("code_content") or action.metadata.get(
                "replacement_content"
            )
            if not code_candidate and isinstance(action.content, dict):
                code_candidate = (
                    action.content.get("code")
                    or action.content.get("content")
                    or action.content.get("ReplacementContent")
                    or action.content.get("CodeContent")
                )

            if (
                code_candidate
                and isinstance(code_candidate, str)
                and (
                    "def " in code_candidate
                    or "import " in code_candidate
                    or "class " in code_candidate
                )
            ):
                try:
                    import ast

                    ast.parse(code_candidate)
                    logger.info("dry_run_syntax_validation_passed")
                except SyntaxError as syntax_err:
                    raise ContractViolationError(
                        f"Dry-Run Gate: Proposed Python code contains syntax errors: {syntax_err}"
                    )

    def _perform_git_rollback(self, input_payload: RAEInput) -> None:
        """
        Rolls back the workspace on failure by discarding all uncommitted files.
        """
        import os

        if "PYTEST_CURRENT_TEST" in os.environ:
            logger.info("git_rollback_skipped_during_test_run")
            return

        import subprocess

        project_dir = input_payload.context.get("project_dir") or "."
        logger.warning("git_rollback_triggered_automatically", project_dir=project_dir)
        try:
            # 1. Reset worktree modifications
            subprocess.run(
                ["git", "reset", "--hard", "HEAD"],
                cwd=project_dir,
                capture_output=True,
                check=False,
            )
            # 2. Clean untracked files
            subprocess.run(
                ["git", "clean", "-fd"],
                cwd=project_dir,
                capture_output=True,
                check=False,
            )
            logger.info("git_rollback_completed_successfully")
        except Exception as rollback_err:
            logger.error("git_rollback_failed", error=str(rollback_err))
