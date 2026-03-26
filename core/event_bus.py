"""Event Bus - Pub/Sub for external notifications.

Layer 2: DeltaUpdate + EventBus for external component notifications.
External components (WebSocket UI, monitoring) subscribe to state changes.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Any, Callable
from collections import defaultdict

logger = logging.getLogger(__name__)


DeltaHandler = Callable[[dict[str, Any]], None]


@dataclass
class EventSubscription:
    """Event subscription."""
    subscriber_id: str
    topic: str | None  # None = subscribe to all
    handler: DeltaHandler


class EventBus:
    """Event bus for external notifications.

    Layer 2: DeltaUpdate + EventBus
    - External components subscribe to state changes
    - UI updates, monitoring systems, etc.

    Usage:
        event_bus = EventBus()

        # Subscribe
        event_bus.subscribe("my_subscriber", "Goal", handle_goal_change)

        # Publish
        event_bus.publish_delta(
            entity_type="Goal",
            entity_id="goal_123",
            operation="update",
            delta={"status": "completed"},
            source_agent="executor_1",
        )
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._subscriptions: list[EventSubscription] = []
        self._topic_subscribers: dict[str, list[DeltaHandler]] = defaultdict(list)
        self._global_subscribers: list[DeltaHandler] = []

    def subscribe(
        self,
        subscriber_id: str,
        topic: str | None,
        handler: DeltaHandler,
    ) -> None:
        """Subscribe to events.

        Args:
            subscriber_id: Unique subscriber identifier.
            topic: Entity type to subscribe to (None = all events).
            handler: Callback function for events.
        """
        with self._lock:
            subscription = EventSubscription(
                subscriber_id=subscriber_id,
                topic=topic,
                handler=handler,
            )
            self._subscriptions.append(subscription)

            if topic:
                self._topic_subscribers[topic].append(handler)
            else:
                self._global_subscribers.append(handler)

        logger.debug("Subscribed %s to topic=%s", subscriber_id, topic)

    def unsubscribe(self, subscriber_id: str) -> None:
        """Unsubscribe by subscriber ID.

        Args:
            subscriber_id: Subscriber identifier.
        """
        with self._lock:
            self._subscriptions = [
                s for s in self._subscriptions
                if s.subscriber_id != subscriber_id
            ]

            # Rebuild topic mappings
            self._topic_subscribers.clear()
            self._global_subscribers.clear()
            for sub in self._subscriptions:
                if sub.topic:
                    self._topic_subscribers[sub.topic].append(sub.handler)
                else:
                    self._global_subscribers.append(sub.handler)

        logger.debug("Unsubscribed %s", subscriber_id)

    def publish_delta(
        self,
        entity_type: str,
        entity_id: str,
        operation: str,
        delta: dict[str, Any],
        source_agent: str,
    ) -> None:
        """Publish delta update to all subscribers.

        Args:
            entity_type: Entity type (Intent, Goal, Plan, Status).
            entity_id: Entity identifier.
            operation: Operation type (create, update, delete).
            delta: Changed data.
            source_agent: Source agent ID.
        """
        event = {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "operation": operation,
            "delta": delta,
            "source_agent": source_agent,
        }

        # Get handlers for this topic
        with self._lock:
            handlers = list(self._topic_subscribers.get(entity_type, []))
            handlers.extend(self._global_subscribers)

        # Notify all handlers
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error("Event handler error: %s", e)

    def publish_event(
        self,
        event_type: str,
        data: dict[str, Any],
    ) -> None:
        """Publish a generic event.

        Args:
            event_type: Event type.
            data: Event data.
        """
        event = {
            "event_type": event_type,
            "data": data,
        }

        with self._lock:
            handlers = list(self._global_subscribers)

        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error("Event handler error: %s", e)

    def get_subscriber_count(self) -> int:
        """Get total subscriber count."""
        with self._lock:
            return len(self._subscriptions)


# Global event bus instance
_event_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Get the global event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus
