"""
LLM Response data models.
Unified response format for all LLM providers.
"""

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class TokenUsage:
    """Token usage information from an LLM call."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass
class LLMChunk:
    """A chunk of streaming response from an LLM."""

    text: str
    finish_reason: Optional[str] = None
    usage: Optional[TokenUsage] = None


@dataclass
class LLMResponse:
    """
    Standardized response format for all LLM providers.

    Each provider maps their native response to this format.
    """

    text: str
    usage: TokenUsage
    finish_reason: str
    raw: dict[str, Any]  # Raw response from provider for debugging
    model_name: Optional[str] = None
    tool_calls: Optional[list[dict[str, Any]]] = None
