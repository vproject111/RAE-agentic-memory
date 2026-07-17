from rae_core.math.stability import PIDController, SimpleKalmanFilter


class TestPIDController:
    def test_init(self):
        pid = PIDController(kp=1.0, ki=0.1, kd=0.01, setpoint=10.0)
        assert pid.kp == 1.0
        assert pid.ki == 0.1
        assert pid.kd == 0.01
        assert pid.setpoint == 10.0
        assert pid._prev_error == 0.0
        assert pid._integral == 0.0

    def test_update_proportional(self):
        pid = PIDController(kp=1.0, ki=0.0, kd=0.0, setpoint=10.0)
        # Error = 10.0 - 5.0 = 5.0
        # Output = 1.0 * 5.0 = 5.0
        output = pid.update(5.0)
        assert output == 5.0

    def test_update_integral(self):
        pid = PIDController(kp=0.0, ki=1.0, kd=0.0, setpoint=10.0)
        # Error = 10.0 - 8.0 = 2.0
        # Integral = 0.0 + 2.0 * 1.0 = 2.0
        # Output = 1.0 * 2.0 = 2.0
        output1 = pid.update(8.0)
        assert output1 == 2.0

        # Error = 10.0 - 8.0 = 2.0
        # Integral = 2.0 + 2.0 * 1.0 = 4.0
        # Output = 1.0 * 4.0 = 4.0
        output2 = pid.update(8.0)
        assert output2 == 4.0

    def test_update_derivative(self):
        pid = PIDController(kp=0.0, ki=0.0, kd=1.0, setpoint=10.0)
        # Error = 10.0 - 5.0 = 5.0
        # Derivative = (5.0 - 0.0) / 1.0 = 5.0
        # Output = 1.0 * 5.0 = 5.0
        output1 = pid.update(5.0)
        assert output1 == 5.0

        # Error = 10.0 - 8.0 = 2.0
        # Derivative = (2.0 - 5.0) / 1.0 = -3.0
        # Output = 1.0 * -3.0 = -3.0
        output2 = pid.update(8.0)
        assert output2 == -3.0

    def test_update_dt_zero(self):
        pid = PIDController(kp=1.0, ki=1.0, kd=1.0, setpoint=10.0)
        output = pid.update(5.0, dt=0)
        # Error = 5.0
        # P = 5.0
        # I = 0 + 5.0*0 = 0
        # D = 0
        # Total = 5.0
        assert output == 5.0


class TestSimpleKalmanFilter:
    def test_init(self):
        kf = SimpleKalmanFilter(r=0.1, q=0.01, a=1.0, b=1.0, c=1.0)
        assert kf.r == 0.1
        assert kf.q == 0.01
        assert kf.a == 1.0
        assert kf.b == 1.0
        assert kf.c == 1.0
        assert kf.x == 0.0
        assert kf.p == 1.0

    def test_update_smooths_value(self):
        kf = SimpleKalmanFilter(r=1.0, q=0.1)
        # Initial x=0, p=1
        # Update with 10.0
        # Prediction: pred_x = 1*0 + 0*0 = 0, pred_p = 1*1*1 + 0.1 = 1.1
        # K = 1.1*1 / (1*1.1*1 + 1) = 1.1 / 2.1 = 0.5238
        # x = 0 + 0.5238 * (10.0 - 1*0) = 5.238
        # p = (1 - 0.5238*1) * 1.1 = 0.4762 * 1.1 = 0.5238
        output = kf.update(10.0)
        assert 5.0 < output < 6.0
        assert kf.x == output

        # Update again with 10.0
        # x should move closer to 10.0
        output2 = kf.update(10.0)
        assert output2 > output

    def test_update_with_control_input(self):
        kf = SimpleKalmanFilter(r=0.1, q=0.01, b=2.0)
        # x=0, p=1
        # Measurement 0.0, Control 1.0
        output = kf.update(0.0, control_input=1.0)
        # The filter weights measurement vs prediction.
        # With r=0.1, it trusts the measurement 0.0 quite a lot.
        assert output > 0.0
