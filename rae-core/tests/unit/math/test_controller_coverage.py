from unittest.mock import MagicMock, patch

from rae_core.math.controller import MathLayerController


class MockConfigDict:
    def dict(self):
        return {"test": "val"}


def test_controller_init_with_dict():
    config = MockConfigDict()
    with patch("rae_core.math.controller.FeatureExtractorV2"):
        ctrl = MathLayerController(config=config)
        assert ctrl.config == {"test": "val"}


def test_get_scoring_params_missing_limit():
    ctrl = MathLayerController()
    # Mock bandit to return an arm without rerank_limit
    mock_arm = MagicMock()
    mock_arm.config = {"weights": {"a": 1}, "params": {}}
    mock_arm.arm_id = "test_arm"
    ctrl.bandit.select = MagicMock(return_value=mock_arm)

    params = ctrl.get_scoring_params("query", 10)
    assert params["_params"]["rerank_limit"] == 10
    assert params["_arm_id"] == "test_arm"


def test_score_memory_anchor_protection():
    ctrl = MathLayerController()
    # query_similarity >= 100.0
    score = ctrl.score_memory({}, 100.0)
    assert score == 100.0

    score = ctrl.score_memory({}, 105.0)
    assert score == 105.0


def test_get_resonance_threshold():
    ctrl = MathLayerController()
    assert ctrl.get_resonance_threshold("query") == 0.5


def test_update_policy_disabled():
    ctrl = MathLayerController(config={"bandit": {"enabled": False}})
    # Should return early
    ctrl.update_policy(True, "query")
    # No calls to bandit.update should happen (it's not even initialized properly if disabled?)
    # Actually it IS initialized.


def test_update_policy_full_flow():
    ctrl = MathLayerController()
    ctrl._last_selected_arm = "arm1"
    ctrl.bandit.update = MagicMock()

    ctrl.update_policy(True, "query", rank=2)
    ctrl.bandit.update.assert_called_once()
    args = ctrl.bandit.update.call_args
    assert args[0][0] == "arm1"  # arm_id
    assert args[0][1] == 0.5  # reward = 1.0 / 2
