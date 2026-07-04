from rae_core.llm.config import LLMConfig, LLMProviderType, ProviderConfig


def test_llm_config_methods():
    config = LLMConfig()

    # Test list_providers (empty)
    assert config.list_providers() == []

    # Test add_provider
    p1 = ProviderConfig(provider_type=LLMProviderType.OPENAI, model="gpt-4")
    config.add_provider("openai", p1)

    assert config.list_providers() == ["openai"]
    assert config.default_provider == "openai"
    assert config.get_provider("openai") == p1

    # Test add second provider (default should not change)
    p2 = ProviderConfig(provider_type=LLMProviderType.ANTHROPIC, model="claude-3")
    config.add_provider("anthropic", p2)
    assert config.default_provider == "openai"
    assert config.get_provider("anthropic") == p2

    # Test get_provider (non-existent)
    assert config.get_provider("nonexistent") is None
