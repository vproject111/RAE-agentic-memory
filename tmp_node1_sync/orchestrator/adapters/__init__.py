"""Adapters for different AI model CLIs/APIs."""

from .base import (
    AgentContext,
    AgentResult,
    ModelAdapter,
    ModelType,
    TaskComplexity,
    TaskRisk,
)
from .claude_adapter import ClaudeAdapter
from .gemini_adapter import GeminiAdapter

__all__ = [
    "ModelAdapter",
    "ModelType",
    "TaskComplexity",
    "TaskRisk",
    "AgentContext",
    "AgentResult",
    "ClaudeAdapter",
    "GeminiAdapter",
]
