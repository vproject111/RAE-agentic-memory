"""
Cost Controller - Unified Cost Calculation for All LLM Providers

This module provides enterprise-grade cost calculation for LLM API calls across
all supported providers (OpenAI, Anthropic, Google, Ollama).

Key Features:
- Unified calculate_cost() function for all providers
- Detailed cost breakdown with per-million token rates
- Graceful handling of unknown models
- Comprehensive logging and error handling
- Support for cache hit cost calculations

Usage:
    from services.cost_controller import calculate_cost

    cost_info = calculate_cost(
        model_name="gpt-4o-mini",
        input_tokens=1500,
        output_tokens=500
    )

    print(f"Total cost: ${cost_info['total_cost_usd']:.6f}")
    print(f"Input rate: ${cost_info['input_cost_per_million']}/M tokens")
"""

from typing import Any, Dict, Optional

import structlog

from .. import cost_model

logger = structlog.get_logger(__name__)


# ============================================================================
# Cost Calculation Functions
# ============================================================================


def calculate_cost(
    model_name: str, input_tokens: int, output_tokens: int, cache_hit: bool = False
) -> Dict[str, Any]:
    """
    Calculates the estimated cost for an LLM API call across all providers.

    This is the primary cost calculation function used throughout the RAE system.
    It replaces litellm.completion_cost() which was returning 0.0.

    Args:
        model_name: Full model identifier (e.g., "gpt-4o-mini", "claude-3.5-sonnet-20240620")
        input_tokens: Number of input tokens consumed
        output_tokens: Number of output tokens generated
        cache_hit: Whether this was a cache hit (affects cost calculation)

    Returns:
        Dictionary with detailed cost breakdown:
        {
            "total_cost_usd": float,
            "input_cost_per_million": float,
            "output_cost_per_million": float,
            "input_tokens": int,
            "output_tokens": int,
            "total_tokens": int,
            "model_name": str,
            "cache_hit": bool,
            "cost_known": bool  # False if model not in cost database
        }

    Example:
        >>> cost_info = calculate_cost("gpt-4o-mini", 1500, 500)
        >>> print(f"${cost_info['total_cost_usd']:.6f}")
        $0.001500

        >>> # Calculate cost for unknown model (returns 0)
        >>> cost_info = calculate_cost("unknown-model", 1000, 500)
        >>> # Logs warning and returns cost_known=False
    """
    logger.info(
        "calculate_cost",
        model_name=model_name,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_hit=cache_hit,
    )

    # Get cost rates from cost model
    costs = cost_model.get_model_cost(model_name)

    if not costs:
        logger.warning(
            "unknown_model_cost",
            model_name=model_name,
            message=f"Model '{model_name}' not found in cost database. Cost will be $0.00. "
            f"Add this model to apps/memory_api/cost_model.py",
        )
        return {
            "total_cost_usd": 0.0,
            "input_cost_per_million": 0.0,
            "output_cost_per_million": 0.0,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "model_name": model_name,
            "cache_hit": cache_hit,
            "cost_known": False,
        }

    input_cost_per_million = costs.get("input", 0.0)
    output_cost_per_million = costs.get("output", 0.0)

    # Calculate costs
    input_cost = (input_tokens / 1_000_000) * input_cost_per_million
    output_cost = (output_tokens / 1_000_000) * output_cost_per_million
    total_cost = input_cost + output_cost

    # If cache hit, cost is typically 0 (or heavily reduced)
    if cache_hit:
        total_cost = 0.0
        logger.info(
            "cache_hit_zero_cost",
            model_name=model_name,
            tokens_saved=input_tokens + output_tokens,
        )

    cost_info = {
        "total_cost_usd": total_cost,
        "input_cost_per_million": input_cost_per_million,
        "output_cost_per_million": output_cost_per_million,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "model_name": model_name,
        "cache_hit": cache_hit,
        "cost_known": True,
    }

    logger.info(
        "cost_calculated",
        model_name=model_name,
        total_cost_usd=total_cost,
        total_tokens=input_tokens + output_tokens,
        cost_known=True,
    )

    return cost_info


def estimate_cost(
    model_name: str, estimated_input_tokens: int, estimated_output_tokens: int
) -> float:
    """
    Estimates cost for pre-flight budget checks.

    This is a lightweight version of calculate_cost() that returns only the total USD cost.
    Used by CostGuardMiddleware for budget enforcement before making LLM calls.

    Args:
        model_name: Full model identifier
        estimated_input_tokens: Estimated input tokens
        estimated_output_tokens: Estimated output tokens

    Returns:
        Estimated total cost in USD

    Example:
        >>> estimated_cost = estimate_cost("gpt-4o", 2000, 1000)
        >>> if estimated_cost > budget_remaining:
        ...     raise HTTPException(402, "Budget exceeded")
    """
    cost_info = calculate_cost(
        model_name, estimated_input_tokens, estimated_output_tokens
    )
    return float(cost_info["total_cost_usd"])


def get_model_rates(model_name: str) -> Optional[Dict[str, float]]:
    """
    Gets the cost rates (per million tokens) for a model.

    Useful for displaying pricing information in UIs and documentation.

    Args:
        model_name: Full model identifier

    Returns:
        Dictionary with "input" and "output" rates, or None if model unknown

    Example:
        >>> rates = get_model_rates("gpt-4o-mini")
        >>> print(f"Input: ${rates['input']}/M, Output: ${rates['output']}/M")
        Input: $0.5/M, Output: $1.5/M
    """
    costs = cost_model.get_model_cost(model_name)

    if not costs:
        logger.warning("model_rates_not_found", model_name=model_name)
        return None

    return {"input": costs.get("input", 0.0), "output": costs.get("output", 0.0)}


def calculate_cache_savings(
    model_name: str, tokens_saved: int, token_type: str = "input"
) -> float:
    """
    Calculates estimated cost savings from cache hits.

    Used for ROI analysis of caching infrastructure.

    Args:
        model_name: Full model identifier
        tokens_saved: Number of tokens saved by cache hit
        token_type: Either "input" or "output" (default "input")

    Returns:
        Estimated cost saved in USD

    Example:
        >>> savings = calculate_cache_savings("gpt-4o", 5000, "input")
        >>> print(f"Cache saved ${savings:.4f}")
        Cache saved $0.0250
    """
    costs = cost_model.get_model_cost(model_name)

    if not costs:
        logger.warning("cache_savings_unknown_model", model_name=model_name)
        return 0.0

    cost_per_million = costs.get(token_type, 0.0)
    savings = (tokens_saved / 1_000_000) * cost_per_million

    logger.info(
        "cache_savings_calculated",
        model_name=model_name,
        tokens_saved=tokens_saved,
        token_type=token_type,
        savings_usd=savings,
    )

    return savings


def is_model_known(model_name: str) -> bool:
    """
    Checks if a model is in the cost database.

    Useful for validation before making LLM calls.

    Args:
        model_name: Full model identifier

    Returns:
        True if model cost is known, False otherwise

    Example:
        >>> if not is_model_known("gpt-7"):
        ...     logger.warning("Using unknown model, cost tracking will be inaccurate")
    """
    costs = cost_model.get_model_cost(model_name)
    return costs is not None


# ============================================================================
# Legacy Function (for backwards compatibility)
# ============================================================================


def calculate_gemini_cost(
    model_name: str, input_tokens: int, output_tokens: int
) -> float:
    """
    DEPRECATED: Use calculate_cost() instead.

    Legacy function for Gemini cost calculation. Kept for backwards compatibility.
    """
    logger.warning(
        "deprecated_function_used",
        function="calculate_gemini_cost",
        message="Use calculate_cost() instead for unified cost calculation",
    )

    cost_info = calculate_cost(model_name, input_tokens, output_tokens)
    return float(cost_info["total_cost_usd"])


# ============================================================================
# Cost Summary Utilities
# ============================================================================


def format_cost_summary(cost_info: Dict[str, Any]) -> str:
    """
    Formats cost information into a human-readable string.

    Useful for logging and debugging.

    Args:
        cost_info: Cost information dictionary from calculate_cost()

    Returns:
        Formatted string with cost breakdown

    Example:
        >>> cost_info = calculate_cost("gpt-4o-mini", 1500, 500)
        >>> print(format_cost_summary(cost_info))
        Model: gpt-4o-mini | Tokens: 2000 (1500 in, 500 out) | Cost: $0.001500
    """
    return (
        f"Model: {cost_info['model_name']} | "
        f"Tokens: {cost_info['total_tokens']} "
        f"({cost_info['input_tokens']} in, {cost_info['output_tokens']} out) | "
        f"Cost: ${cost_info['total_cost_usd']:.6f}"
    )


def validate_cost_calculation(
    model_name: str,
    input_tokens: int,
    output_tokens: int,
    llm_reported_cost: float,
    tolerance: float = 0.0001,
) -> bool:
    """
    Validates LLM-reported cost against our cost model.

    Helps identify when LLM providers change pricing or when litellm returns incorrect costs.

    Args:
        model_name: Model identifier
        input_tokens: Input tokens used
        output_tokens: Output tokens generated
        llm_reported_cost: Cost reported by LLM provider (e.g., from litellm)
        tolerance: Acceptable difference in USD (default $0.0001)

    Returns:
        True if costs match within tolerance, False otherwise

    Example:
        >>> is_valid = validate_cost_calculation("gpt-4o-mini", 1000, 500, 0.0)
        >>> if not is_valid:
        ...     logger.error("Cost mismatch detected! Using our cost model instead.")
    """
    our_cost = float(
        calculate_cost(model_name, input_tokens, output_tokens)["total_cost_usd"]
    )
    difference = abs(our_cost - llm_reported_cost)

    is_valid = bool(difference <= tolerance)

    if not is_valid:
        logger.warning(
            "cost_calculation_mismatch",
            model_name=model_name,
            our_cost=our_cost,
            llm_reported_cost=llm_reported_cost,
            difference=difference,
            tolerance=tolerance,
        )

    return is_valid
