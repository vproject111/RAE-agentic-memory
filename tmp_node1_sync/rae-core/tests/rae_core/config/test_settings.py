import os

import pytest

from rae_core.config.defaults import (
    DEFAULT_CACHE_MAX_SIZE,
    DEFAULT_CACHE_TTL,
    DEFAULT_CONSOLIDATION_THRESHOLD,
    DEFAULT_DECAY_INTERVAL_HOURS,
    DEFAULT_DECAY_RATE,
    DEFAULT_EPISODIC_SIZE,
    DEFAULT_LLM_MAX_TOKENS,
    DEFAULT_LLM_TEMPERATURE,
    DEFAULT_LLM_TIMEOUT,
    DEFAULT_MIN_IMPORTANCE,
    DEFAULT_MIN_MEMORIES_FOR_REFLECTION,
    DEFAULT_OTEL_ENABLED,
    DEFAULT_OTEL_SERVICE_NAME,
    DEFAULT_OTEL_SERVICE_VERSION,
    DEFAULT_PROMOTION_THRESHOLD,
    DEFAULT_QUALITY_THRESHOLD,
    DEFAULT_REFLECTION_MAX_AGE_HOURS,
    DEFAULT_RERANK_TOP_K,
    DEFAULT_SEMANTIC_SIZE,
    DEFAULT_SENSORY_SIZE,
    DEFAULT_SIMILARITY_THRESHOLD,
    DEFAULT_SYNC_BATCH_SIZE,
    DEFAULT_SYNC_RETRY_ATTEMPTS,
    DEFAULT_SYNC_TIMEOUT,
    DEFAULT_TOP_K,
    DEFAULT_WORKING_SIZE,
)
from rae_core.config.settings import RAESettings


@pytest.fixture(autouse=True)
def clean_env():
    """Fixture to clean environment variables before and after each test."""
    # Store original RAE_ prefixed env vars
    original_rae_env = {k: os.environ[k] for k in os.environ if k.startswith("RAE_")}

    # Clear all RAE_ prefixed env vars
    for k in original_rae_env:
        del os.environ[k]

    yield

    # Restore original RAE_ prefixed env vars
    for k in os.environ:
        if k.startswith("RAE_"):
            del os.environ[k]
    os.environ.update(original_rae_env)


def test_default_settings():
    """Test that RAESettings loads with default values."""
    settings = RAESettings()

    # Memory layer sizes
    assert settings.sensory_max_size == DEFAULT_SENSORY_SIZE
    assert settings.working_max_size == DEFAULT_WORKING_SIZE
    assert settings.episodic_max_size == DEFAULT_EPISODIC_SIZE
    assert settings.semantic_max_size == DEFAULT_SEMANTIC_SIZE

    # Memory decay parameters
    assert settings.decay_rate == DEFAULT_DECAY_RATE
    assert settings.decay_interval_hours == DEFAULT_DECAY_INTERVAL_HOURS

    # Importance thresholds
    assert settings.min_importance == DEFAULT_MIN_IMPORTANCE
    assert settings.promotion_threshold == DEFAULT_PROMOTION_THRESHOLD
    assert settings.consolidation_threshold == DEFAULT_CONSOLIDATION_THRESHOLD

    # Search parameters
    assert settings.search_top_k == DEFAULT_TOP_K
    assert settings.similarity_threshold == DEFAULT_SIMILARITY_THRESHOLD
    assert settings.rerank_top_k == DEFAULT_RERANK_TOP_K

    # Reflection parameters
    assert settings.min_memories_for_reflection == DEFAULT_MIN_MEMORIES_FOR_REFLECTION
    assert settings.reflection_max_age_hours == DEFAULT_REFLECTION_MAX_AGE_HOURS
    assert settings.quality_threshold == DEFAULT_QUALITY_THRESHOLD

    # LLM parameters
    assert settings.llm_temperature == DEFAULT_LLM_TEMPERATURE
    assert settings.llm_max_tokens == DEFAULT_LLM_MAX_TOKENS
    assert settings.llm_timeout == DEFAULT_LLM_TIMEOUT

    # Sync parameters
    assert not settings.sync_enabled  # Default for sync_enabled is False in settings.py
    assert settings.sync_batch_size == DEFAULT_SYNC_BATCH_SIZE
    assert settings.sync_timeout == DEFAULT_SYNC_TIMEOUT
    assert settings.sync_retry_attempts == DEFAULT_SYNC_RETRY_ATTEMPTS
    assert (
        settings.sync_encryption_enabled
    )  # Default for sync_encryption_enabled is True

    # Cache parameters
    assert settings.cache_enabled  # Default for cache_enabled is True
    assert settings.cache_ttl == DEFAULT_CACHE_TTL
    assert settings.cache_max_size == DEFAULT_CACHE_MAX_SIZE

    # OpenTelemetry parameters
    assert settings.otel_enabled == DEFAULT_OTEL_ENABLED
    assert settings.otel_service_name == DEFAULT_OTEL_SERVICE_NAME
    assert settings.otel_service_version == DEFAULT_OTEL_SERVICE_VERSION
    assert settings.otel_endpoint is None  # Default is None

    # Vector backend
    assert settings.vector_backend == "qdrant"  # Default is qdrant


def test_env_var_override():
    """Test that environment variables can override default settings."""
    os.environ["RAE_SENSORY_MAX_SIZE"] = "200"
    os.environ["RAE_DECAY_RATE"] = "0.5"
    os.environ["RAE_SYNC_ENABLED"] = "True"
    os.environ["RAE_OTEL_ENDPOINT"] = "http://localhost:4317"

    settings = RAESettings()

    assert settings.sensory_max_size == 200
    assert settings.decay_rate == 0.5
    assert settings.sync_enabled
    assert settings.otel_endpoint == "http://localhost:4317"

    # Ensure other settings remain at their defaults
    assert settings.working_max_size == DEFAULT_WORKING_SIZE
    assert settings.search_top_k == DEFAULT_TOP_K


def test_get_layer_config():
    """Test get_layer_config method."""
    settings = RAESettings()

    sensory_config = settings.get_layer_config("sensory")
    assert sensory_config["max_size"] == DEFAULT_SENSORY_SIZE
    assert sensory_config["decay_rate"] == DEFAULT_DECAY_RATE
    assert sensory_config["min_importance"] == DEFAULT_MIN_IMPORTANCE

    semantic_config = settings.get_layer_config("semantic")
    assert semantic_config["max_size"] == DEFAULT_SEMANTIC_SIZE
    assert semantic_config["decay_rate"] == 1.0  # Semantic layer has fixed decay
    assert semantic_config["min_importance"] == DEFAULT_PROMOTION_THRESHOLD

    assert settings.get_layer_config("non_existent_layer") == {}


def test_get_llm_config():
    """Test get_llm_config method."""
    settings = RAESettings()
    llm_config = settings.get_llm_config()

    assert llm_config["temperature"] == DEFAULT_LLM_TEMPERATURE
    assert llm_config["max_tokens"] == DEFAULT_LLM_MAX_TOKENS
    assert llm_config["timeout"] == DEFAULT_LLM_TIMEOUT


def test_get_search_config():
    """Test get_search_config method."""
    settings = RAESettings()
    search_config = settings.get_search_config()

    assert search_config["top_k"] == DEFAULT_TOP_K
    assert search_config["similarity_threshold"] == DEFAULT_SIMILARITY_THRESHOLD
    assert search_config["rerank_top_k"] == DEFAULT_RERANK_TOP_K


def test_get_reflection_config():
    """Test get_reflection_config method."""
    settings = RAESettings()
    reflection_config = settings.get_reflection_config()

    assert reflection_config["min_memories"] == DEFAULT_MIN_MEMORIES_FOR_REFLECTION
    assert reflection_config["max_age_hours"] == DEFAULT_REFLECTION_MAX_AGE_HOURS
    assert reflection_config["quality_threshold"] == DEFAULT_QUALITY_THRESHOLD
