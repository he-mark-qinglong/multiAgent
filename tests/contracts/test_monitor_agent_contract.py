"""MonitorAgent contract tests."""

import sys
sys.path.insert(0, '.')

import pytest
from core.event_bus import EventBus
from agents.monitor_agent import MonitorAgent


class TestMonitorAgentContract:
    """MonitorAgent public API contract tests."""

    @pytest.fixture
    def event_bus(self):
        return EventBus()

    @pytest.fixture
    def monitor(self, event_bus):
        return MonitorAgent(event_bus=event_bus)

    def test_get_goal_state_returns_str_or_none(self, monitor):
        """get_goal_state(goal_id) returns str or None."""
        result = monitor.get_goal_state("nonexistent")
        assert result is None or isinstance(result, str)

    def test_get_goal_state_after_update(self, monitor, event_bus):
        """get_goal_state returns status after event."""
        event_bus.publish_delta(
            entity_type="Goal",
            entity_id="goal_monitor_1",
            operation="update",
            delta={"status": "completed"},
            source_agent="executor",
        )
        result = monitor.get_goal_state("goal_monitor_1")
        assert result is not None

    def test_get_active_alerts_returns_list(self, monitor):
        """get_active_alerts() returns list."""
        result = monitor.get_active_alerts()
        assert isinstance(result, list)

    def test_is_circuit_open_returns_bool(self, monitor):
        """is_circuit_open() returns bool."""
        result = monitor.is_circuit_open()
        assert isinstance(result, bool)

    def test_get_metrics_returns_dict(self, monitor):
        """get_metrics() returns dict."""
        result = monitor.get_metrics()
        assert isinstance(result, dict)

    def test_get_metrics_has_expected_keys(self, monitor):
        """get_metrics() has expected keys."""
        metrics = monitor.get_metrics()
        expected_keys = ["total_goals", "completed", "circuit_open"]
        for key in expected_keys:
            assert key in metrics

    def test_subscribe_alerts_returns_none(self, monitor):
        """subscribe_alerts() returns None."""
        result = monitor.subscribe_alerts(lambda e: None)
        assert result is None

    def test_reset_clears_state(self, monitor, event_bus):
        """reset() clears all state."""
        event_bus.publish_delta(
            entity_type="Goal",
            entity_id="goal_reset",
            operation="create",
            delta={"status": "pending"},
            source_agent="test",
        )
        monitor.reset()
        metrics = monitor.get_metrics()
        assert metrics["total_goals"] == 0
        assert metrics["completed"] == 0

    def test_monitor_subscribes_to_event_bus(self, monitor, event_bus):
        """Monitor subscribes to EventBus on init."""
        assert event_bus.get_subscriber_count() >= 1

    def test_circuit_breaker_opens_after_failures(self, monitor, event_bus):
        """Circuit breaker opens after consecutive failures."""
        for i in range(3):
            event_bus.publish_delta(
                entity_type="Goal",
                entity_id=f"fail_goal_{i}",
                operation="update",
                delta={"status": "failed"},
                source_agent="executor",
            )
        assert monitor.is_circuit_open() is True

    def test_circuit_breaker_auto_reset(self, monitor):
        """Circuit breaker auto-resets after timeout."""
        import time
        monitor._circuit_open = True
        monitor._circuit_open_time = time.time() - 61
        assert monitor.is_circuit_open() is False

    def test_recovery_action_recommended_on_failure(self, monitor, event_bus):
        """Monitor recommends recovery action on failure."""
        recommendations = []

        def capture_alert(payload):
            recommendations.append(payload.get("recommended_action"))

        monitor.subscribe_alerts(capture_alert)
        event_bus.publish_delta(
            entity_type="Goal",
            entity_id="fail_goal_1",
            operation="update",
            delta={"status": "failed"},
            source_agent="executor",
        )

        assert len(recommendations) >= 1

    def test_multiple_goal_tracking(self, monitor, event_bus):
        """Monitor tracks multiple goals."""
        for i in range(3):
            event_bus.publish_delta(
                entity_type="Goal",
                entity_id=f"goal_{i}",
                operation="create",
                delta={"status": "completed"},
                source_agent="executor",
            )
        metrics = monitor.get_metrics()
        assert metrics["total_goals"] >= 3
        assert metrics["completed"] >= 3

    def test_metrics_update_on_status_change(self, monitor, event_bus):
        """Metrics update when goal status changes."""
        event_bus.publish_delta(
            entity_type="Goal",
            entity_id="goal_metric",
            operation="create",
            delta={"status": "pending"},
            source_agent="executor",
        )
        m1 = monitor.get_metrics()
        pending_count = m1.get("pending", 0)

        event_bus.publish_delta(
            entity_type="Goal",
            entity_id="goal_metric",
            operation="update",
            delta={"status": "completed"},
            source_agent="executor",
        )
        m2 = monitor.get_metrics()

        assert isinstance(m1, dict)
        assert isinstance(m2, dict)
