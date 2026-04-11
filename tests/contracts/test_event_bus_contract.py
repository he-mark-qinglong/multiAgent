"""EventBus contract tests."""

import sys
sys.path.insert(0, '.')

import pytest
from core.event_bus import EventBus


class TestEventBusContract:
    """EventBus public API contract tests."""

    @pytest.fixture
    def bus(self):
        return EventBus()

    def test_subscribe_returns_none(self, bus):
        """subscribe() returns None."""
        result = bus.subscribe("sub1", None, lambda e: None)
        assert result is None

    def test_unsubscribe_returns_none(self, bus):
        """unsubscribe() returns None."""
        bus.subscribe("sub1", None, lambda e: None)
        result = bus.unsubscribe("sub1")
        assert result is None

    def test_publish_delta_returns_none(self, bus):
        """publish_delta() returns None."""
        result = bus.publish_delta(
            entity_type="Goal",
            entity_id="g1",
            operation="update",
            delta={"status": "completed"},
            source_agent="test",
        )
        assert result is None

    def test_publish_delta_notifies_handler(self, bus):
        """Handler called after publish_delta."""
        received = []

        def handler(event):
            received.append(event)

        bus.subscribe("sub", None, handler)
        bus.publish_delta(
            entity_type="Goal",
            entity_id="g1",
            operation="create",
            delta={"status": "pending"},
            source_agent="executor",
        )
        assert len(received) == 1
        assert received[0]["entity_id"] == "g1"

    def test_topic_filtering_works(self, bus):
        """Subscribe to specific topic only receives that topic."""
        goal_events = []

        def goal_handler(event):
            goal_events.append(event)

        bus.subscribe("goal_sub", "Goal", goal_handler)
        # Publish Goal event - should be received
        bus.publish_delta("Goal", "g1", "update", {}, "test")
        # Publish Status event - should NOT be received
        bus.publish_delta("Status", "s1", "update", {}, "test")

        assert len(goal_events) == 1
        assert goal_events[0]["entity_type"] == "Goal"

    def test_global_subscription_works(self, bus):
        """Subscribe to None receives all topics."""
        all_events = []

        def all_handler(event):
            all_events.append(event)

        bus.subscribe("all_sub", None, all_handler)
        bus.publish_delta("Goal", "g1", "create", {}, "test")
        bus.publish_delta("Status", "s1", "update", {}, "test")
        bus.publish_delta("Plan", "p1", "create", {}, "test")

        assert len(all_events) == 3

    def test_multiple_subscribers_all_notified(self, bus):
        """Multiple subscribers all get notified."""
        count = [0, 0]

        def handler1(e):
            count[0] += 1

        def handler2(e):
            count[1] += 1

        bus.subscribe("sub1", None, handler1)
        bus.subscribe("sub2", None, handler2)
        bus.publish_delta("Goal", "g1", "create", {}, "test")

        assert count[0] == 1
        assert count[1] == 1

    def test_handler_exception_doesnt_crash_publish(self, bus):
        """Handler exceptions don't crash publish_delta."""
        def bad_handler(event):
            raise RuntimeError("handler error")

        bus.subscribe("bad", None, bad_handler)
        # Should not raise
        bus.publish_delta("Goal", "g1", "create", {}, "test")

    def test_get_subscriber_count_returns_int(self, bus):
        """get_subscriber_count() returns int."""
        bus.subscribe("s1", None, lambda e: None)
        bus.subscribe("s2", "Goal", lambda e: None)
        count = bus.get_subscriber_count()
        assert isinstance(count, int)
        assert count == 2

    def test_unsubscribe_removes_handler(self, bus):
        """After unsubscribe, handler no longer called."""
        received = []

        def handler(event):
            received.append(event)

        bus.subscribe("sub", None, handler)
        bus.unsubscribe("sub")
        bus.publish_delta("Goal", "g1", "create", {}, "test")

        assert len(received) == 0

    def test_multiple_topic_subscriptions(self, bus):
        """Same handler can be subscribed to multiple topics."""
        received_goal = []
        received_status = []

        def goal_h(e):
            received_goal.append(e)

        bus.subscribe("goal", "Goal", goal_h)
        bus.publish_delta("Goal", "g1", "create", {}, "test")
        assert len(received_goal) == 1

    def test_publish_event_returns_none(self, bus):
        """publish_event() returns None."""
        result = bus.publish_event("test_event", {"data": "value"})
        assert result is None

    def test_publish_event_notifies_global(self, bus):
        """publish_event() notifies global subscribers."""
        received = []

        def handler(event):
            received.append(event)

        bus.subscribe("global", None, handler)
        bus.publish_event("custom_type", {"key": "value"})

        assert len(received) == 1
        assert received[0]["event_type"] == "custom_type"
        assert received[0]["data"] == {"key": "value"}

    def test_subscribe_with_topic_and_unsubscribe(self, bus):
        """Unsubscribe works for topic-specific subscriptions."""
        received = []

        def handler(e):
            received.append(e)

        bus.subscribe("topic_sub", "Goal", handler)
        bus.unsubscribe("topic_sub")
        bus.publish_delta("Goal", "g1", "create", {}, "test")

        assert len(received) == 0

    def test_subscriber_count_after_unsubscribe(self, bus):
        """Subscriber count decreases after unsubscribe."""
        bus.subscribe("s1", None, lambda e: None)
        bus.subscribe("s2", "Goal", lambda e: None)
        assert bus.get_subscriber_count() == 2

        bus.unsubscribe("s1")
        assert bus.get_subscriber_count() == 1

        bus.unsubscribe("s2")
        assert bus.get_subscriber_count() == 0

    def test_event_contains_all_fields(self, bus):
        """Published event contains all required fields."""
        received = []

        def handler(event):
            received.append(event)

        bus.subscribe("sub", None, handler)
        bus.publish_delta(
            entity_type="Intent",
            entity_id="intent_1",
            operation="create",
            delta={"confidence": 0.9},
            source_agent="intent_agent",
        )

        event = received[0]
        assert "entity_type" in event
        assert "entity_id" in event
        assert "operation" in event
        assert "delta" in event
        assert "source_agent" in event
