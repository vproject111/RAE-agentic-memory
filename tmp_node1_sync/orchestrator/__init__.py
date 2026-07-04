"""Multi-agent orchestrator for intelligent code development.

Coordinates Claude and Gemini CLI for high-quality autonomous development
with smart routing, cross-review, and quality gates.
"""

__version__ = "0.1.0"

from .main import Orchestrator, TaskStatus

__all__ = ["Orchestrator", "TaskStatus", "__version__"]
