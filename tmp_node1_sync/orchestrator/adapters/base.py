"""Base adapter interface for AI model CLI interactions."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class ModelType(Enum):
    """Supported AI model types."""

    CLAUDE_SONNET = "claude-sonnet-4-5"
    GEMINI_PRO = "gemini-2.0-pro"
    GEMINI_FLASH = "gemini-2.0-flash"


class TaskComplexity(Enum):
    """Task complexity levels for routing."""

    TRIVIAL = "trivial"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class TaskRisk(Enum):
    """Task risk levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class AgentContext:
    """Context information for agent execution."""

    task_description: str
    task_type: str  # e.g., "plan", "implement", "review"
    complexity: TaskComplexity
    risk: TaskRisk
    working_directory: str
    files_to_read: List[str] = None
    additional_context: Dict[str, Any] = None

    def __post_init__(self):
        if self.files_to_read is None:
            self.files_to_read = []
        if self.additional_context is None:
            self.additional_context = {}


@dataclass
class AgentResult:
    """Result from agent execution."""

    success: bool
    output: str
    error: Optional[str] = None
    files_changed: List[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.files_changed is None:
            self.files_changed = []
        if self.metadata is None:
            self.metadata = {}


class ModelAdapter(ABC):
    """Abstract base class for AI model CLI adapters."""

    def __init__(self, model_type: ModelType, working_dir: str):
        """Initialize adapter.

        Args:
            model_type: Type of AI model
            working_dir: Working directory for operations
        """
        self.model_type = model_type
        self.working_dir = working_dir

    @abstractmethod
    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute task with the AI model.

        Args:
            context: Agent execution context

        Returns:
            Result of execution
        """
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the model CLI is available and configured.

        Returns:
            True if model is ready to use
        """
        pass

    @abstractmethod
    async def get_cost_per_1k_tokens(self) -> float:
        """Get cost per 1K tokens for this model.

        Returns:
            Cost in USD per 1K tokens
        """
        pass

    def get_model_name(self) -> str:
        """Get human-readable model name."""
        return self.model_type.value
