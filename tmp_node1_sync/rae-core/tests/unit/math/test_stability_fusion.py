"""Unit tests for stability and fusion math modules."""

from uuid import uuid4

from rae_core.math.fusion import reciprocal_rank_fusion
from rae_core.math.stability import PIDController, SimpleKalmanFilter


class TestStabilityFusion:
    """Test suite for math stability and fusion."""

    def test_rrf_basic(self):
        id1, id2, id3 = uuid4(), uuid4(), uuid4()
        list1 = [(id1, 0.9), (id2, 0.8)]
        list2 = [(id2, 0.9), (id3, 0.7)]

        fused = reciprocal_rank_fusion([list1, list2], k=60)

        # id2 is in both, should rank highest
        assert fused[0][0] == id2
        assert fused[0][1] > fused[1][1]

    def test_pid_controller(self):
        pid = PIDController(kp=1.0, ki=0.1, kd=0.05, setpoint=10.0)

        # Initial error 10.0
        output = pid.update(measurement=0.0, dt=1.0)
        assert output > 0

        # Measurement at setpoint
        output = pid.update(measurement=10.0, dt=1.0)
        assert output != 0  # Due to integral term from previous step

    def test_kalman_filter(self):
        kf = SimpleKalmanFilter(r=0.1, q=0.01)

        # Constant signal with noise
        measurements = [1.0, 1.1, 0.9, 1.05, 0.95]
        results = [kf.update(m) for m in measurements]

        # Should converge towards 1.0
        assert 0.8 < results[-1] < 1.2
        assert kf.p < 1.0  # Uncertainty should decrease
