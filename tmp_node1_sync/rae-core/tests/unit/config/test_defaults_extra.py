from rae_core.config import RAESettings
from rae_core.config.defaults import (
    get_default_llm_config,
    get_default_memory_layer_config,
    get_default_reflection_config,
    get_default_search_config,
)


def test_defaults_functions():
    assert isinstance(get_default_memory_layer_config(), dict)
    assert isinstance(get_default_llm_config(), dict)
    assert isinstance(get_default_search_config(), dict)
    assert isinstance(get_default_reflection_config(), dict)


def test_settings_helpers():
    """Test helper methods in RAESettings."""
    settings = RAESettings()

    # Test get_layer_config
    sensory = settings.get_layer_config("sensory")
    assert sensory["max_size"] == 100
    assert sensory["decay_rate"] == 0.95

    semantic = settings.get_layer_config("semantic")
    assert semantic["decay_rate"] == 1.0  # No decay

    unknown = settings.get_layer_config("unknown")
    assert unknown == {}

    # Test get_llm_config
    llm = settings.get_llm_config()
    assert "temperature" in llm
    assert "max_tokens" in llm

    # Test get_search_config
    search = settings.get_search_config()
    assert "top_k" in search

    # Test get_reflection_config
    reflection = settings.get_reflection_config()
    assert "min_memories" in reflection
