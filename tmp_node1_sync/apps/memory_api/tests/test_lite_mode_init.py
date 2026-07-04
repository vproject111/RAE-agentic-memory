from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from apps.memory_api.main import app


@pytest.mark.smoke
def test_lite_mode_initialization():
    """Test that the app starts in Lite mode without failing."""
    with patch.dict("os.environ", {"RAE_PROFILE": "lite", "RAE_DB_MODE": "ignore"}):
        # We need to force settings to reload if possible,
        # but since settings is a singleton, let's just mock it
        with patch("apps.memory_api.config.settings.RAE_PROFILE", "lite"):
            with patch("apps.memory_api.config.settings.RAE_DB_MODE", "ignore"):
                with TestClient(app) as client:
                    response = client.get("/health")
                    assert response.status_code == 200

                    # Verify RAECoreService is initialized
                    assert hasattr(app.state, "rae_core_service")
                    assert app.state.rae_core_service is not None

                    # Verify it uses fallbacks
                    from rae_adapters.memory.storage import InMemoryStorage

                    assert isinstance(
                        app.state.rae_core_service.postgres_adapter, InMemoryStorage
                    )
