# Costs are per million tokens
MODEL_COSTS = {
    # --- OpenAI ---
    "gpt-5.1": {"input": 100.0, "output": 200.0},  # Placeholder
    "gpt-5": {"input": 80.0, "output": 160.0},  # Placeholder
    "gpt-4.1": {"input": 20.0, "output": 40.0},  # Placeholder
    "gpt-4.1-mini": {"input": 5.0, "output": 15.0},  # Placeholder
    "gpt-4o": {"input": 5.0, "output": 15.0},
    "gpt-4o-mini": {"input": 0.5, "output": 1.5},  # Placeholder
    "gpt-4": {"input": 30.0, "output": 60.0},
    "gpt-4-32k": {"input": 60.0, "output": 120.0},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    "o1": {"input": 20.0, "output": 40.0},  # Placeholder for OpenAI o1
    "o1-mini": {"input": 5.0, "output": 15.0},  # Placeholder
    "o1-pro": {"input": 40.0, "output": 80.0},  # Placeholder
    "gpt-4o-code": {"input": 10.0, "output": 30.0},  # Placeholder
    # --- Anthropic ---
    "claude-sonnet-4-5-20250929": {
        "input": 3.0,
        "output": 15.0,
    },  # Placeholder, assuming Sonnet 4.5 is similar to 3.5
    "claude-haiku-4-5-20251001": {
        "input": 0.25,
        "output": 1.25,
    },  # Placeholder, assuming Haiku 4.5 is similar to 3
    "claude-opus-4-1-20250805": {
        "input": 15.0,
        "output": 75.0,
    },  # Placeholder, assuming Opus 4.1 is similar to 4
    "claude-opus-4-20250514": {"input": 15.0, "output": 75.0},  # Placeholder
    "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
    "claude-3.5-sonnet-20240620": {"input": 3.00, "output": 15.00},
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
    # --- Google ---
    "gemini-pro": {"input": 0.50, "output": 1.50},
    "gemini-1.5-pro-001": {"input": 7.0, "output": 21.0},  # Gemini 1.5 Pro
    "models/gemini-1.5-pro-002": {
        "input": 2.0,
        "output": 6.0,
    },  # Placeholder costs, adjust as per actual pricing
    # --- Local / Open Source ---
    "ollama/": {"input": 0.0, "output": 0.0},  # Matches any model served by Ollama
    "phi-3": {"input": 0.0, "output": 0.0},  # Can be served via Ollama
}


def get_model_cost(model_name: str) -> dict[str, float] | None:
    """
    Returns the input and output cost per million tokens for a given model.
    It performs a partial match to handle model variations.
    """
    # Exact match first
    if model_name in MODEL_COSTS:
        return MODEL_COSTS[model_name]

    # Partial match for families of models (e.g., ollama/, gpt-4-)
    for key, cost in MODEL_COSTS.items():
        if model_name.startswith(key):
            return cost

    return None
