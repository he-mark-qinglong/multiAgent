"""Monitor Agent - XL: Cross-layer oversight and health monitoring.

Subscribes to all DeltaUpdate events via EventBus.
Detects failures, timeouts, and coordinates recovery.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from core.event_bus import EventBus, get_event_bus

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecoveryAction(Enum):
    """Recovery strategies."""
    RETRY = "retry"
    SKIP = "skip"
    FALLBACK = "fallback"
    ABORT = "abort"


@dataclass
class HealthMetrics:
    """System health metrics."""
    total_goals: int = 0
    completed: int = 0
    failed: int = 0
    skipped: int = 0
    avg_execution_time_ms: float = 0.0
    active_executors: list[str] = field(default_factory=list)
    last_update: float = field(default_factory=time.time)


@dataclass
class Alert:
    """Alert record."""
    alert_id: str
    severity: AlertSeverity
    source_agent: str
    message: str
    timestamp: float = field(default_factory=time.time)
    recovered: bool = False


class MonitorAgent:
    """XL Agent for cross-layer oversight.

    Responsibilities:
    - Subscribe to ALL status changes via EventBus
    - Detect goal failures or timeouts
    - Notify Planner for recovery decisions
    - Report system health metrics

    Recovery Strategies:
    - RETRY: Same executor, same goal
    - SKIP: Mark goal as SKIPPED, continue
    - FALLBACK: Different executor or approach
    - ABORT: Stop plan, notify user
    """

    def __init__(self, event_bus: EventBus | None = None):
        """Initialize MonitorAgent.

        Args:
            event_bus: EventBus instance for subscriptions.
        """
        self.agent_id = "monitor"
        self.name = "Monitor Agent"
        self.role = "XL"
        self.event_bus = event_bus or get_event_bus()

        # Internal state
        self._lock = threading.RLock()
        self._metrics = HealthMetrics()
        self._alerts: list[Alert] = []
        self._executor_states: dict[str, str] = {}  # executor_id -> status
        self._goal_states: dict[str, str] = {}  # goal_id -> status
        self._failure_count: dict[str, int] = {}  # goal_id -> failure count

        # Circuit breaker
        self._consecutive_failures = 0
        self._circuit_open = False
        self._circuit_open_time: float | None = None

        # Subscribers for alerts (callbacks)
        self._alert_subscribers: list[callable] = []

        # Subscribe to EventBus
        self._subscribe()

    def _subscribe(self) -> None:
        """Subscribe to EventBus for all entity types."""
        # Subscribe to all topics (topic=None means all)
        self.event_bus.subscribe(
            subscriber_id=self.agent_id,
            topic=None,  # All events
            handler=self._handle_delta,
        )
        logger.info("MonitorAgent subscribed to EventBus")

    def _handle_delta(self, event: dict[str, Any]) -> None:
        """Handle incoming DeltaUpdate from EventBus.

        Args:
            event: DeltaUpdate event dict.
        """
        entity_type = event.get("entity_type", "")
        entity_id = event.get("entity_id", "")
        operation = event.get("operation", "")
        delta = event.get("delta", {})
        source = event.get("source_agent", "")

        with self._lock:
            if entity_type == "Goal" or entity_type == "Status":
                self._track_goal(entity_id, operation, delta, source)
            elif entity_type == "ExecutionStatus":
                self._track_executor(entity_id, delta, source)

    def _track_goal(
        self,
        goal_id: str,
        operation: str,
        delta: dict[str, Any],
        source: str,
    ) -> None:
        """Track goal status changes."""
        self._metrics.total_goals += 1

        status = delta.get("status", "")
        if status == "completed":
            self._metrics.completed += 1
            self._goal_states[goal_id] = "completed"
            self._failure_count.pop(goal_id, None)
        elif status == "failed":
            self._metrics.failed += 1
            self._goal_states[goal_id] = "failed"
            self._handle_failure(goal_id, source, delta)
        elif status == "skipped":
            self._metrics.skipped += 1
            self._goal_states[goal_id] = "skipped"

        self._metrics.last_update = time.time()

    def _track_executor(
        self,
        executor_id: str,
        delta: dict[str, Any],
        source: str,
    ) -> None:
        """Track executor status changes."""
        status = delta.get("status", "")
        self._executor_states[executor_id] = status

        # Update active executors
        if status == "running":
            if executor_id not in self._metrics.active_executors:
                self._metrics.active_executors.append(executor_id)
        elif status in ("completed", "failed", "idle"):
            if executor_id in self._metrics.active_executors:
                self._metrics.active_executors.remove(executor_id)

    def _handle_failure(self, goal_id: str, source: str, delta: dict[str, Any]) -> None:
        """Handle goal failure and decide recovery action."""
        failure_count = self._failure_count.get(goal_id, 0) + 1
        self._failure_count[goal_id] = failure_count

        # Check circuit breaker
        self._consecutive_failures += 1
        if self._consecutive_failures >= 3:
            self._open_circuit(f"3+ consecutive failures (goal: {goal_id})")
            return

        # Determine severity and action
        severity = AlertSeverity.HIGH if failure_count == 1 else AlertSeverity.CRITICAL

        if failure_count <= 2:
            action = RecoveryAction.RETRY
            alert_msg = f"Goal {goal_id} failed (attempt {failure_count}), recommend RETRY"
        else:
            action = RecoveryAction.SKIP
            alert_msg = f"Goal {goal_id} failed {failure_count} times, recommend SKIP"

        alert = Alert(
            alert_id=f"alert_{goal_id}_{int(time.time())}",
            severity=severity,
            source_agent=source,
            message=alert_msg,
        )
        self._alerts.append(alert)

        # Notify subscribers
        self._notify_subscribers(alert, action)

        logger.warning(
            "Monitor: goal=%s failed from=%s severity=%s action=%s",
            goal_id, source, severity.value, action.value,
        )

    def _open_circuit(self, reason: str) -> None:
        """Open circuit breaker."""
        self._circuit_open = True
        self._circuit_open_time = time.time()
        logger.error("Monitor: CIRCUIT OPEN - %s", reason)

        alert = Alert(
            alert_id=f"circuit_{int(time.time())}",
            severity=AlertSeverity.CRITICAL,
            source_agent="circuit_breaker",
            message=f"Circuit breaker opened: {reason}",
        )
        self._alerts.append(alert)
        self._notify_subscribers(alert, RecoveryAction.ABORT)

    def _notify_subscribers(self, alert: Alert, action: RecoveryAction) -> None:
        """Notify all subscribers of alert and recovery action."""
        payload = {
            "alert": alert,
            "recommended_action": action.value,
            "metrics": self.get_metrics(),
        }
        for callback in self._alert_subscribers:
            try:
                callback(payload)
            except Exception as e:
                logger.error("Monitor subscriber error: %s", e)

    def subscribe_alerts(self, callback: callable) -> None:
        """Subscribe to alert notifications.

        Args:
            callback: Function called with (alert, action) on each alert.
        """
        with self._lock:
            self._alert_subscribers.append(callback)

    def is_circuit_open(self) -> bool:
        """Check if circuit breaker is open."""
        with self._lock:
            if not self._circuit_open:
                return False

            # Auto-reset after 60 seconds
            if self._circuit_open_time and time.time() - self._circuit_open_time > 60:
                self._circuit_open = False
                self._consecutive_failures = 0
                logger.info("Monitor: circuit breaker auto-reset")
                return False
            return True

    def get_metrics(self) -> dict[str, Any]:
        """Get current health metrics.

        Returns:
            Health metrics as dict.
        """
        with self._lock:
            return {
                "total_goals": self._metrics.total_goals,
                "completed": self._metrics.completed,
                "failed": self._metrics.failed,
                "skipped": self._metrics.skipped,
                "active_executors": list(self._metrics.active_executors),
                "circuit_open": self._circuit_open,
                "last_update": self._metrics.last_update,
            }

    def get_active_alerts(self) -> list[dict[str, Any]]:
        """Get active (unrecovered) alerts.

        Returns:
            List of active alert dicts.
        """
        with self._lock:
            active = [a for a in self._alerts if not a.recovered]
            return [
                {
                    "alert_id": a.alert_id,
                    "severity": a.severity.value,
                    "source_agent": a.source_agent,
                    "message": a.message,
                    "timestamp": a.timestamp,
                }
                for a in active
            ]

    def get_goal_state(self, goal_id: str) -> str | None:
        """Get current state of a goal.

        Args:
            goal_id: Goal identifier.

        Returns:
            Goal state or None.
        """
        with self._lock:
            return self._goal_states.get(goal_id)

    def reset(self) -> None:
        """Reset all metrics and alerts."""
        with self._lock:
            self._metrics = HealthMetrics()
            self._alerts.clear()
            self._executor_states.clear()
            self._goal_states.clear()
            self._failure_count.clear()
            self._consecutive_failures = 0
            self._circuit_open = False
            self._circuit_open_time = None
        logger.info("MonitorAgent reset")
