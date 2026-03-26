"""EventBus implementation for the Multi-Agent Collaboration System.

Provides a publish/subscribe pattern with topic filtering for agent communication.
In-memory implementation for Phase 1 to minimize external dependencies.
"""

from __future__ import annotations

import fnmatch
import logging
import threading
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable
from enum import Enum

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# Event Types
# ------------------------------------------------------------------------------


class EventPriority(str, Enum):
    """Priority levels for event handling."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


@dataclass
class Event:
    """An event published on the event bus.

    Attributes:
        event_id: Unique identifier for this event.
        topic: Topic this event belongs to.
        payload: Event data.
        priority: Priority level of this event.
        timestamp: Unix timestamp when the event was created.
        source_agent: ID of the agent that published this event.
        metadata: Additional metadata about the event.
    """

    event_id: str
    topic: str
    payload: Any
    priority: EventPriority
    timestamp: int
    source_agent: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def create(
        topic: str,
        payload: Any,
        source_agent: str,
        priority: EventPriority = EventPriority.NORMAL,
        metadata: dict[str, Any] | None = None,
    ) -> Event:
        """Factory method to create a new Event.

        Args:
            topic: Topic this event belongs to.
            payload: Event data.
            source_agent: ID of the agent that published this event.
            priority: Priority level of this event.
            metadata: Additional metadata about the event.

        Returns:
            A new Event instance.
        """
        import time
        return Event(
            event_id=str(uuid.uuid4()),
            topic=topic,
            payload=payload,
            priority=priority,
            timestamp=int(time.time()),
            source_agent=source_agent,
            metadata=metadata or {},
        )


# ------------------------------------------------------------------------------
# Event Handler
# ------------------------------------------------------------------------------


@dataclass
class EventHandler:
    """A handler registration for events.

    Attributes:
        handler_id: Unique identifier for this handler.
        topic_pattern: Topic pattern to match (supports wildcards).
        callback: Function to call when matching events are published.
        priority: Priority level for handler ordering.
        filter_fn: Optional function to filter events before calling callback.
    """

    handler_id: str
    topic_pattern: str
    callback: Callable[[Event], None]
    priority: EventPriority = EventPriority.NORMAL
    filter_fn: Callable[[Event], bool] | None = None

    def matches(self, topic: str) -> bool:
        """Check if this handler matches a given topic.

        Supports wildcards:
        - '*' matches any sequence of characters within a single path segment
        - '**' matches any sequence of path segments

        Args:
            topic: The topic to check.

        Returns:
            True if the topic matches the pattern.
        """
        if self.topic_pattern == "*":
            return True
        if self.topic_pattern.endswith(".**"):
            prefix = self.topic_pattern[:-3]
            return topic.startswith(prefix) or fnmatch.fnmatch(topic, self.topic_pattern)
        return fnmatch.fnmatch(topic, self.topic_pattern)


# ------------------------------------------------------------------------------
# EventBus
# ------------------------------------------------------------------------------


class EventBus:
    """Central event bus for agent communication.

    Provides publish/subscribe pattern with topic filtering and
    priority-based event dispatch. Thread-safe for concurrent access.

    Topics follow a hierarchical naming convention:
        agent.<agent_id>.<event_type>
        state.<entity_type>.<operation>
        pipeline.<stage>.<event>

    Example topics:
        - agent.intent.* - All events from intent agent
        - state.goal.* - All goal state changes
        - pipeline.executor.complete - Executor completion events
    """

    # Well-known topic prefixes
    TOPIC_PREFIX_AGENT = "agent"
    TOPIC_PREFIX_STATE = "state"
    TOPIC_PREFIX_PIPELINE = "pipeline"

    def __init__(self) -> None:
        """Initialize the EventBus."""
        self._handlers: list[EventHandler] = []
        self._lock = threading.RLock()
        self._event_queue: list[Event] = []
        self._dispatch_thread: threading.Thread | None = None
        self._running = False
        logger.info("EventBus initialized")

    # --------------------------------------------------------------------------
    # Publisher API
    # --------------------------------------------------------------------------

    def publish(
        self,
        topic: str,
        payload: Any,
        source_agent: str,
        priority: EventPriority = EventPriority.NORMAL,
        metadata: dict[str, Any] | None = None,
    ) -> Event:
        """Publish an event to the bus.

        Args:
            topic: Topic to publish to.
            payload: Event data.
            source_agent: ID of the publishing agent.
            priority: Priority level for dispatch ordering.
            metadata: Additional event metadata.

        Returns:
            The published Event instance.
        """
        event = Event.create(
            topic=topic,
            payload=payload,
            source_agent=source_agent,
            priority=priority,
            metadata=metadata,
        )

        with self._lock:
            if self._running:
                self._event_queue.append(event)
            self._dispatch_event(event)

        logger.debug("EventBus: published event %s to topic=%s", event.event_id, topic)
        return event

    def publish_delta(
        self,
        entity_type: str,
        entity_id: str,
        operation: str,
        delta: dict[str, Any],
        source_agent: str,
    ) -> Event:
        """Convenience method to publish a state delta event.

        Args:
            entity_type: Type of entity being updated.
            entity_id: ID of the entity.
            operation: Operation type (create, update, delete).
            delta: Changed data.
            source_agent: ID of the publishing agent.

        Returns:
            The published Event instance.
        """
        topic = f"{self.TOPIC_PREFIX_STATE}.{entity_type}.{operation}"
        payload = {
            "entity_id": entity_id,
            "delta": delta,
        }
        return self.publish(topic, payload, source_agent)

    # --------------------------------------------------------------------------
    # Subscriber API
    # --------------------------------------------------------------------------

    def subscribe(
        self,
        topic_pattern: str,
        callback: Callable[[Event], None],
        priority: EventPriority = EventPriority.NORMAL,
        filter_fn: Callable[[Event], bool] | None = None,
    ) -> str:
        """Subscribe to events matching a topic pattern.

        Args:
            topic_pattern: Pattern to match topics against. Supports wildcards.
            callback: Function to call when matching events are published.
            priority: Priority level for handler ordering.
            filter_fn: Optional function to filter events before callback.

        Returns:
            Handler ID that can be used to unsubscribe.

        Example:
            handler_id = event_bus.subscribe(
                "state.goal.*",
                lambda e: handle_goal_update(e),
            )
        """
        handler_id = str(uuid.uuid4())
        handler = EventHandler(
            handler_id=handler_id,
            topic_pattern=topic_pattern,
            callback=callback,
            priority=priority,
            filter_fn=filter_fn,
        )

        with self._lock:
            self._handlers.append(handler)
            self._handlers.sort(
                key=lambda h: list(EventPriority).index(h.priority),
                reverse=True,
            )

        logger.debug("EventBus: subscribed to topic=%s, handler_id=%s", topic_pattern, handler_id)
        return handler_id

    def unsubscribe(self, handler_id: str) -> bool:
        """Unsubscribe a handler from the event bus.

        Args:
            handler_id: ID returned by subscribe().

        Returns:
            True if the handler was found and removed.
        """
        with self._lock:
            for i, handler in enumerate(self._handlers):
                if handler.handler_id == handler_id:
                    del self._handlers[i]
                    logger.debug("EventBus: unsubscribed handler_id=%s", handler_id)
                    return True
        return False

    def unsubscribe_all(self, topic_pattern: str | None = None) -> int:
        """Unsubscribe all handlers matching a pattern, or all if no pattern.

        Args:
            topic_pattern: Optional pattern to filter handlers to remove.

        Returns:
            Number of handlers removed.
        """
        with self._lock:
            if topic_pattern is None:
                count = len(self._handlers)
                self._handlers.clear()
            else:
                count = 0
                self._handlers = [
                    h for h in self._handlers
                    if not fnmatch.fnmatch(h.topic_pattern, topic_pattern)
                    and not h.topic_pattern == topic_pattern
                ]
        logger.debug("EventBus: unsubscribed %d handlers", count)
        return count

    # --------------------------------------------------------------------------
    # Subscription Convenience Methods
    # --------------------------------------------------------------------------

    def subscribe_to_agent(
        self,
        agent_id: str,
        callback: Callable[[Event], None],
    ) -> str:
        """Subscribe to all events from a specific agent.

        Args:
            agent_id: ID of the agent to subscribe to.
            callback: Function to call for each event.

        Returns:
            Handler ID for unsubscribing.
        """
        return self.subscribe(f"{self.TOPIC_PREFIX_AGENT}.{agent_id}.*", callback)

    def subscribe_to_entity(
        self,
        entity_type: str,
        callback: Callable[[Event], None],
        operation: str | None = None,
    ) -> str:
        """Subscribe to state changes for an entity type.

        Args:
            entity_type: Type of entity (e.g., 'goal', 'intent').
            callback: Function to call for each event.
            operation: Optional specific operation to filter on.

        Returns:
            Handler ID for unsubscribing.
        """
        if operation:
            return self.subscribe(f"{self.TOPIC_PREFIX_STATE}.{entity_type}.{operation}", callback)
        return self.subscribe(f"{self.TOPIC_PREFIX_STATE}.{entity_type}.*", callback)

    def subscribe_to_pipeline(
        self,
        stage: str,
        callback: Callable[[Event], None],
    ) -> str:
        """Subscribe to pipeline events at a specific stage.

        Args:
            stage: Pipeline stage (e.g., 'executor', 'planner').
            callback: Function to call for each event.

        Returns:
            Handler ID for unsubscribing.
        """
        return self.subscribe(f"{self.TOPIC_PREFIX_PIPELINE}.{stage}.*", callback)

    # --------------------------------------------------------------------------
    # Query API
    # --------------------------------------------------------------------------

    def get_subscriptions(self, topic_pattern: str | None = None) -> list[str]:
        """Get list of topic patterns currently subscribed.

        Args:
            topic_pattern: Optional filter for specific patterns.

        Returns:
            List of topic patterns.
        """
        with self._lock:
            if topic_pattern is None:
                return [h.topic_pattern for h in self._handlers]
            return [
                h.topic_pattern for h in self._handlers
                if fnmatch.fnmatch(h.topic_pattern, topic_pattern)
            ]

    def count_handlers(self, topic_pattern: str | None = None) -> int:
        """Count the number of handlers registered.

        Args:
            topic_pattern: Optional filter for specific patterns.

        Returns:
            Number of matching handlers.
        """
        with self._lock:
            if topic_pattern is None:
                return len(self._handlers)
            return sum(1 for h in self._handlers if fnmatch.fnmatch(h.topic_pattern, topic_pattern))

    # --------------------------------------------------------------------------
    # Internal Dispatch
    # --------------------------------------------------------------------------

    def _dispatch_event(self, event: Event) -> None:
        """Dispatch an event to all matching handlers.

        Args:
            event: The event to dispatch.
        """
        handlers_to_call: list[EventHandler] = []
        with self._lock:
            for handler in self._handlers:
                if handler.matches(event.topic):
                    handlers_to_call.append(handler)

        for handler in handlers_to_call:
            if handler.filter_fn is None or handler.filter_fn(event):
                try:
                    handler.callback(event)
                except Exception as e:
                    logger.error(
                        "EventBus: error in handler %s for topic=%s: %s",
                        handler.handler_id,
                        event.topic,
                        e,
                    )

    # --------------------------------------------------------------------------
    # Lifecycle
    # --------------------------------------------------------------------------

    def start_async_dispatch(self) -> None:
        """Start asynchronous event dispatch in a background thread.

        Events will be queued and dispatched in order.
        Useful for high-throughput scenarios.
        """
        with self._lock:
            if self._running:
                return
            self._running = True
            self._dispatch_thread = threading.Thread(
                target=self._dispatch_loop,
                daemon=True,
                name="EventBus-Dispatch",
            )
            self._dispatch_thread.start()
        logger.info("EventBus: started async dispatch")

    def stop_async_dispatch(self) -> None:
        """Stop asynchronous event dispatch."""
        with self._lock:
            self._running = False
        if self._dispatch_thread:
            self._dispatch_thread.join(timeout=1.0)
            self._dispatch_thread = None
        logger.info("EventBus: stopped async dispatch")

    def _dispatch_loop(self) -> None:
        """Background dispatch loop for async mode."""
        while self._running:
            event = None
            with self._lock:
                if self._event_queue:
                    event = self._event_queue.pop(0)
            if event:
                self._dispatch_event(event)
            else:
                threading.Event().wait(0.01)
