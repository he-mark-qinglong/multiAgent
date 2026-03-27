"""Monitor Agent tests."""

import pytest
import time
from core.event_bus import EventBus
from agents.monitor_agent import MonitorAgent, AlertSeverity, RecoveryAction


class TestMonitorAgent:
    """Monitor Agent unit tests."""

    @pytest.fixture
    def event_bus(self):
        return EventBus()

    @pytest.fixture
    def monitor(self, event_bus):
        return MonitorAgent(event_bus=event_bus)

    def test_subscribe_to_event_bus(self, monitor, event_bus):
        """Monitor should subscribe to EventBus on init."""
        assert event_bus.get_subscriber_count() >= 1

    def test_track_goal_completion(self, monitor, event_bus):
        """Should track goal completion."""
        # Simulate goal completion event
        event_bus.publish_delta(
            entity_type="Goal",
            entity_id="goal_1",
            operation="update",
            delta={"status": "completed"},
            source_agent="executor_1",
        )

        state = monitor.get_goal_state("goal_1")
        assert state == "completed"

    def test_track_goal_failure(self, monitor, event_bus):
        """Should track goal failure and create alert."""
        alerts_before = len(monitor.get_active_alerts())

        event_bus.publish_delta(
            entity_type="Goal",
            entity_id="goal_fail_1",
            operation="update",
            delta={"status": "failed", "error": "timeout"},
            source_agent="executor_1",
        )

        alerts_after = monitor.get_active_alerts()
        assert len(alerts_after) > alerts_before
        assert alerts_after[0]["severity"] == "high"

    def test_circuit_breaker(self, monitor, event_bus):
        """Circuit breaker should open after 3 consecutive failures."""
        for i in range(3):
            event_bus.publish_delta(
                entity_type="Goal",
                entity_id=f"goal_circuit_{i}",
                operation="update",
                delta={"status": "failed"},
                source_agent="executor_1",
            )

        assert monitor.is_circuit_open() is True

    def test_circuit_breaker_auto_reset(self, monitor):
        """Circuit breaker auto-resets after 60 seconds (simulated)."""
        monitor._circuit_open = True
        monitor._circuit_open_time = time.time() - 61

        assert monitor.is_circuit_open() is False

    def test_get_metrics(self, monitor, event_bus):
        """Should return health metrics."""
        event_bus.publish_delta(
            entity_type="Goal",
            entity_id="goal_metric_1",
            operation="update",
            delta={"status": "completed"},
            source_agent="executor_1",
        )

        metrics = monitor.get_metrics()
        assert "total_goals" in metrics
        assert "completed" in metrics
        assert "circuit_open" in metrics

    def test_recovery_action_retry(self, monitor, event_bus):
        """First failure should recommend RETRY."""
        recommendations = []

        def capture_alert(payload):
            recommendations.append(payload["recommended_action"])

        monitor.subscribe_alerts(capture_alert)

        event_bus.publish_delta(
            entity_type="Goal",
            entity_id="goal_retry_1",
            operation="update",
            delta={"status": "failed"},
            source_agent="executor_1",
        )

        assert len(recommendations) == 1
        assert recommendations[0] == RecoveryAction.RETRY.value

    def test_reset(self, monitor, event_bus):
        """Reset should clear all state."""
        event_bus.publish_delta(
            entity_type="Goal",
            entity_id="goal_reset",
            operation="update",
            delta={"status": "completed"},
            source_agent="executor_1",
        )

        monitor.reset()

        metrics = monitor.get_metrics()
        assert metrics["total_goals"] == 0
        assert metrics["completed"] == 0
