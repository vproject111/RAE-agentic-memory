from unittest.mock import patch

import pytest

from rae_core.math.controller import MathLayerController


@pytest.fixture
def controller():
    return MathLayerController()


def test_math_controller_similarity_fallback_exception(controller):
    # Mock cosine_similarity to raise exception and trigger fallback logic
    with patch(
        "rae_core.math.controller.cosine_similarity",
        side_effect=Exception("Mocked error"),
    ):
        v1 = [1.0, 0.0]
        v2 = [1.0, 0.0]
        v3 = [0.0, 1.0]

        # Fallback logic should correctly compute similarity
        assert controller.compute_similarity(v1, v2) == pytest.approx(1.0)
        assert controller.compute_similarity(v1, v3) == pytest.approx(0.0)


def test_math_controller_similarity_zero_vector(controller):
    # Test fallback with zero vectors
    with patch(
        "rae_core.math.controller.cosine_similarity",
        side_effect=Exception("Mocked error"),
    ):
        v1 = [0.0, 0.0]
        v2 = [1.0, 0.0]
        assert controller.compute_similarity(v1, v2) == 0.0
