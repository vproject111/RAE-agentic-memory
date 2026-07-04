"""Base agent class and common functionality."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from orchestrator.adapters.base import (
    AgentContext,
    AgentResult,
    ModelAdapter,
    TaskComplexity,
    TaskRisk,
)


@dataclass
class AgentTask:
    """Task for an agent to execute."""

    task_id: str
    description: str
    context: Dict[str, Any]
    complexity: TaskComplexity
    risk: TaskRisk
    working_directory: str
    files_to_read: List[str] = None

    def __post_init__(self):
        if self.files_to_read is None:
            self.files_to_read = []


@dataclass
class AgentResponse:
    """Response from an agent."""

    success: bool
    result: Any
    error: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaseAgent(ABC):
    """Base class for all orchestrator agents."""

    def __init__(self, name: str, role: str):
        """Initialize base agent.

        Args:
            name: Name of this agent instance
            role: Role of this agent (planner, reviewer, implementer, etc.)
        """
        self.name = name
        self.role = role
        self.adapter: Optional[ModelAdapter] = None

    def set_adapter(self, adapter: ModelAdapter):
        """Set the model adapter for this agent.

        Args:
            adapter: Model adapter to use
        """
        self.adapter = adapter

    @abstractmethod
    async def execute(self, task: AgentTask) -> AgentResponse:
        """Execute the agent's task.

        Args:
            task: Task to execute

        Returns:
            Agent response
        """
        pass

    async def _call_model(
        self,
        prompt: str,
        task_type: str,
        complexity: TaskComplexity,
        risk: TaskRisk,
        working_dir: str,
    ) -> AgentResult:
        """Call the underlying model adapter.

        Args:
            prompt: Prompt to send to model
            task_type: Type of task
            complexity: Task complexity
            risk: Task risk
            working_dir: Working directory

        Returns:
            Agent result from model
        """
        if not self.adapter:
            raise RuntimeError(f"No adapter set for agent {self.name}")

        context = AgentContext(
            task_description=prompt,
            task_type=task_type,
            complexity=complexity,
            risk=risk,
            working_directory=working_dir,
        )

        return await self.adapter.execute(context)

    def _build_base_prompt(self, task: AgentTask) -> str:
        """Build base prompt with common context and project rules.

        Args:
            task: Agent task

        Returns:
            Base prompt string with project guidelines
        """
        parts = [
            f"You are {self.name}, a {self.role} agent in a multi-agent orchestrator.",
            "",
            f"Task: {task.description}",
            f"Complexity: {task.complexity.value}",
            f"Risk: {task.risk.value}",
        ]

        # Add project rules and guidelines
        rules_section = self._load_project_rules(task.working_directory)
        if rules_section:
            parts.append(f"\n{rules_section}")

        if task.files_to_read:
            parts.append("\nRelevant files:")
            for file in task.files_to_read:
                parts.append(f"- {file}")

        if task.context:
            parts.append("\nAdditional context:")
            for key, value in task.context.items():
                parts.append(f"- {key}: {value}")

        return "\n".join(parts)

    def _load_project_rules(self, working_dir: str) -> str:
        """Load project rules and guidelines from documentation.

        Args:
            working_dir: Project working directory

        Returns:
            Formatted rules section for prompt
        """
        # DISABLED: Project rules cause issues with LLM prompts
        # Keep prompts minimal for better reliability
        return ""
