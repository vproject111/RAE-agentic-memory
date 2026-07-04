from unittest.mock import MagicMock, patch

from apps.memory_api.services.context_cache import ContextCache


@patch("apps.memory_api.services.context_cache.get_redis_client")
def test_context_cache_flow(mock_get_redis):
    mock_redis_instance = MagicMock()
    mock_get_redis.return_value = mock_redis_instance

    cache = ContextCache()
    cache.set_context("t1", "p1", "semantic", "data")
    mock_redis_instance.setex.assert_called_once()
