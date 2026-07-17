import time
from unittest.mock import MagicMock

from rae_core.math.bandit.arm import Arm
from rae_core.math.bandit.bandit import BanditConfig, MultiArmedBandit
from rae_core.math.bandit.monitor import BanditMonitor, MonitorAlert


def test_monitor_alert_to_dict():
    alert = MonitorAlert(
        severity="warning",
        category="test",
        message="test message",
        timestamp=123.456,
        metadata={"key": "value"},
    )
    d = alert.to_dict()
    assert d == {
        "severity": "warning",
        "category": "test",
        "message": "test message",
        "timestamp": 123.456,
        "metadata": {"key": "value"},
    }


def test_monitor_init():
    bandit = MagicMock(spec=MultiArmedBandit)
    monitor = BanditMonitor(bandit, window_size=50, alert_history_size=20)
    assert monitor.bandit == bandit
    assert monitor.window_size == 50
    assert monitor.alert_history_size == 20
    assert len(monitor.alerts) == 0
    assert len(monitor.reward_window) == 0


def test_check_health_all_ok():
    bandit = MagicMock(spec=MultiArmedBandit)
    bandit.config = MagicMock(spec=BanditConfig)
    bandit.check_degradation.return_value = (False, 0.0)
    bandit.config.exploration_rate = 0.1
    bandit.config.max_exploration_rate = 0.5
    bandit.total_pulls = 10
    bandit.arms = []

    monitor = BanditMonitor(bandit)
    alerts = monitor.check_health()
    assert len(alerts) == 0
    assert len(monitor.alerts) == 0


def test_check_degradation_alert():
    bandit = MagicMock(spec=MultiArmedBandit)
    bandit.check_degradation.return_value = (True, 0.25)
    bandit.baseline_mean_reward = 0.8
    bandit.last_100_rewards = [0.6] * 10

    monitor = BanditMonitor(bandit)
    alert = monitor._check_degradation()
    assert alert.severity == "critical"
    assert alert.category == "degradation"
    assert "25.0%" in alert.message
    assert alert.metadata["drop"] == 0.25
    assert alert.metadata["baseline"] == 0.8
    assert alert.metadata["current"] == 0.6


def test_check_degradation_no_rewards():
    bandit = MagicMock(spec=MultiArmedBandit)
    bandit.check_degradation.return_value = (True, 0.25)
    bandit.baseline_mean_reward = 0.8
    bandit.last_100_rewards = []

    monitor = BanditMonitor(bandit)
    alert = monitor._check_degradation()
    assert alert.metadata["current"] == 0.0


def test_check_excessive_exploration_critical():
    bandit = MagicMock(spec=MultiArmedBandit)
    bandit.config = MagicMock(spec=BanditConfig)
    bandit.config.exploration_rate = 0.6
    bandit.config.max_exploration_rate = 0.5

    monitor = BanditMonitor(bandit)
    alert = monitor._check_excessive_exploration()
    assert alert.severity == "critical"
    assert "exceeds maximum" in alert.message


def test_check_excessive_exploration_warning():
    bandit = MagicMock(spec=MultiArmedBandit)
    bandit.config = MagicMock(spec=BanditConfig)
    bandit.config.exploration_rate = 0.45
    bandit.config.max_exploration_rate = 0.5

    monitor = BanditMonitor(bandit)
    alert = monitor._check_excessive_exploration()
    assert alert.severity == "warning"
    assert "approaching maximum" in alert.message


def test_check_excessive_exploration_ok():
    bandit = MagicMock(spec=MultiArmedBandit)
    bandit.config = MagicMock(spec=BanditConfig)
    bandit.config.exploration_rate = 0.1
    bandit.config.max_exploration_rate = 0.5

    monitor = BanditMonitor(bandit)
    assert monitor._check_excessive_exploration() is None


def test_check_arm_imbalance_early_return():
    bandit = MagicMock(spec=MultiArmedBandit)
    bandit.total_pulls = 10
    monitor = BanditMonitor(bandit)
    assert monitor._check_arm_imbalance() is None


def test_check_arm_imbalance_zero_pulls():
    bandit = MagicMock(spec=MultiArmedBandit)
    bandit.total_pulls = 100
    bandit.arms = []
    monitor = BanditMonitor(bandit)
    assert monitor._check_arm_imbalance() is None


def test_check_arm_imbalance_alert():
    bandit = MagicMock(spec=MultiArmedBandit)
    bandit.total_pulls = 100
    arm1 = MagicMock(spec=Arm)
    arm1.arm_id = "arm1"
    arm1.pulls = 80
    arm2 = MagicMock(spec=Arm)
    arm2.arm_id = "arm2"
    arm2.pulls = 20
    bandit.arms = [arm1, arm2]

    monitor = BanditMonitor(bandit)
    alert = monitor._check_arm_imbalance()
    assert alert.severity == "warning"
    assert alert.category == "arm_imbalance"
    assert "arm1" in alert.message
    assert alert.metadata["ratio"] == 0.8


def test_check_arm_imbalance_ok():
    bandit = MagicMock(spec=MultiArmedBandit)
    bandit.total_pulls = 100
    arm1 = MagicMock(spec=Arm)
    arm1.arm_id = "arm1"
    arm1.pulls = 50
    arm2 = MagicMock(spec=Arm)
    arm2.arm_id = "arm2"
    arm2.pulls = 50
    bandit.arms = [arm1, arm2]

    monitor = BanditMonitor(bandit)
    assert monitor._check_arm_imbalance() is None


def test_check_reward_anomalies_too_few():
    bandit = MagicMock(spec=MultiArmedBandit)
    monitor = BanditMonitor(bandit)
    assert monitor._check_reward_anomalies() is None


def test_check_reward_anomalies_zero_std():
    bandit = MagicMock(spec=MultiArmedBandit)
    monitor = BanditMonitor(bandit)
    monitor.reward_window.extend([1.0] * 20)
    assert monitor._check_reward_anomalies() is None


def test_check_reward_anomalies_alert():
    bandit = MagicMock(spec=MultiArmedBandit)
    monitor = BanditMonitor(bandit, window_size=100)
    # 99 rewards of 1.0, 1 reward of 1e12
    monitor.reward_window.extend([1.0] * 99 + [1e12])
    alert = monitor._check_reward_anomalies()
    assert alert is not None
    assert alert.severity == "warning"
    assert alert.category == "reward_anomaly"
    assert "reward outliers" in alert.message


def test_check_staleness_no_pulls():
    bandit = MagicMock(spec=MultiArmedBandit)
    bandit.arms = []
    monitor = BanditMonitor(bandit)
    assert monitor._check_staleness() is None


def test_check_staleness_alert():
    bandit = MagicMock(spec=MultiArmedBandit)
    arm = MagicMock(spec=Arm)
    arm.last_pulled = time.time() - 4000
    bandit.arms = [arm]

    monitor = BanditMonitor(bandit)
    alert = monitor._check_staleness()
    assert alert.severity == "warning"
    assert alert.category == "staleness"
    assert "minutes" in alert.message


def test_check_staleness_ok():
    bandit = MagicMock(spec=MultiArmedBandit)
    arm = MagicMock(spec=Arm)
    arm.last_pulled = time.time() - 100
    bandit.arms = [arm]

    monitor = BanditMonitor(bandit)
    assert monitor._check_staleness() is None


def test_record_decision():
    bandit = MagicMock(spec=MultiArmedBandit)
    monitor = BanditMonitor(bandit)
    monitor.record_decision("arm1", 0.9)
    assert "arm1" in monitor.arm_selection_window
    assert 0.9 in monitor.reward_window


def test_record_decision_no_reward():
    bandit = MagicMock(spec=MultiArmedBandit)
    monitor = BanditMonitor(bandit)
    monitor.record_decision("arm1")
    assert "arm1" in monitor.arm_selection_window
    assert len(monitor.reward_window) == 0


def test_get_summary():
    bandit = MagicMock(spec=MultiArmedBandit)
    bandit.get_statistics.return_value = {"total_pulls": 0}
    monitor = BanditMonitor(bandit)
    monitor.alerts.append(MonitorAlert("critical", "deg", "msg"))
    monitor.arm_selection_window.append("arm1")
    monitor.reward_window.append(0.5)

    summary = monitor.get_summary()
    assert summary["alert_counts"]["critical"] == 1
    assert summary["arm_distribution"]["arm1"] == 1
    assert summary["reward_stats"]["mean"] == 0.5
    assert summary["reward_stats"]["min"] == 0.5
    assert summary["reward_stats"]["max"] == 0.5
    assert summary["reward_stats"]["count"] == 1


def test_get_summary_no_rewards():
    bandit = MagicMock(spec=MultiArmedBandit)
    bandit.get_statistics.return_value = {"total_pulls": 0}
    monitor = BanditMonitor(bandit)
    summary = monitor.get_summary()
    assert summary["reward_stats"] == {}


def test_get_health_status_healthy():
    bandit = MagicMock(spec=MultiArmedBandit)
    monitor = BanditMonitor(bandit)
    assert monitor.get_health_status() == "healthy"


def test_get_health_status_warning():
    bandit = MagicMock(spec=MultiArmedBandit)
    monitor = BanditMonitor(bandit)
    # Needs > 2 warnings for "warning" status
    monitor.alerts.append(MonitorAlert("warning", "cat", "msg"))
    monitor.alerts.append(MonitorAlert("warning", "cat", "msg"))
    assert monitor.get_health_status() == "healthy"

    monitor.alerts.append(MonitorAlert("warning", "cat", "msg"))
    assert monitor.get_health_status() == "warning"


def test_get_health_status_critical():
    bandit = MagicMock(spec=MultiArmedBandit)
    monitor = BanditMonitor(bandit)
    monitor.alerts.append(MonitorAlert("critical", "cat", "msg"))
    assert monitor.get_health_status() == "critical"


def test_get_health_status_old_alerts():
    bandit = MagicMock(spec=MultiArmedBandit)
    monitor = BanditMonitor(bandit)
    old_alert = MonitorAlert("critical", "cat", "msg")
    old_alert.timestamp = time.time() - 4000  # > 1 hour ago
    monitor.alerts.append(old_alert)
    assert monitor.get_health_status() == "healthy"


def test_check_health_with_alerts():
    bandit = MagicMock(spec=MultiArmedBandit)
    bandit.config = MagicMock(spec=BanditConfig)

    # Trigger degradation alert
    bandit.check_degradation.return_value = (True, 0.3)
    bandit.baseline_mean_reward = 1.0
    bandit.last_100_rewards = [0.7]

    # Trigger excessive exploration alert
    bandit.config.exploration_rate = 0.9
    bandit.config.max_exploration_rate = 0.5

    # Trigger arm imbalance alert
    bandit.total_pulls = 100
    arm1 = MagicMock(spec=Arm)
    arm1.arm_id = "arm1"
    arm1.pulls = 90
    arm2 = MagicMock(spec=Arm)
    arm2.arm_id = "arm2"
    arm2.pulls = 10
    bandit.arms = [arm1, arm2]

    # Trigger reward anomaly alert
    monitor = BanditMonitor(bandit)
    monitor.reward_window.extend(
        [1.0] * 99 + [100.0]
    )  # std will be > 0, 100 is outlier

    # Trigger staleness alert
    arm1.last_pulled = time.time() - 5000
    arm2.last_pulled = time.time() - 5000

    alerts = monitor.check_health()
    assert len(alerts) >= 5
    assert len(monitor.alerts) >= 5


def test_check_reward_anomalies_no_outliers():
    bandit = MagicMock(spec=MultiArmedBandit)
    monitor = BanditMonitor(bandit)
    # 20 rewards, enough variance that 1.1 is not an outlier (> 3 std)
    monitor.reward_window.extend([1.0] * 10 + [1.1] * 10)
    assert monitor._check_reward_anomalies() is None
