"""
LLM Request data models.
Unified request format for all LLM providers.
"""

from dataclasses import dataclass, field
from typing import Any, Literal, Optional


@dataclass
class LLMMessage:
    """A single message in a conversation."""

    role: Literal["system", "user", "assistant"]
    content: str
    name: Optional[str] = None  # Optional name for the message sender


@dataclass
class LLMTool:
    """Definition of a tool/function that can be called by the LLM."""

    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema definition of parameters


@dataclass
class LLMRequest:
    """
    Standardized request format for all LLM providers.

    Each provider is responsible for mapping this to their native format.
    """

    model: str
    messages: list[LLMMessage]
    temperature: float = 0.2
    max_tokens: Optional[int] = None
    json_mode: bool = False
    tools: Optional[list[LLMTool]] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    # Orchestration parameters
    tags: Optional[list[str]] = None
    strategy: Optional[str] = None

    # Additional provider-specific parameters
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    stop_sequences: Optional[list[str]] = None
