from typing import Any, Optional

from apps.llm.broker.orchestrator import LLMOrchestrator

from .base import LLMProvider
from .orchestrator_adapter import OrchestratorAdapter


def get_llm_provider(task_repo: Optional[Any] = None) -> LLMProvider:
    """
    Factory function to get the configured LLM provider.
    Uses the LLM Orchestrator to manage model selection and strategies.
    """
    # Initialize Orchestrator
    # It will load configuration from apps/llm/config/llm_config.yaml
    orchestrator = LLMOrchestrator(task_repo=task_repo)

    # Return Adapter that satisfies the LLMProvider protocol
    return OrchestratorAdapter(orchestrator)
