"""EventBus performance benchmarks."""

import sys
sys.path.insert(0, '.')

import pytest
import time
from core.event_bus import EventBus


class TestEventBusPerformance:
    """EventBus performance benchmarks."""

    @pytest.fixture
    def bus(self):
        return EventBus()

    def test_single_publish_latency(self, bus):
        """Publish latency in microseconds."""
        def noop(e):
            pass

        bus.subscribe("perf_sub", None, noop)
        times = []

        for _ in range(100):
            start = time.perf_counter()
            bus.publish_delta("Goal", "g1", "update", {}, "test")
            elapsed = (time.perf_counter() - start) * 1_000_000
            times.append(elapsed)

        avg_us = sum(times) / len(times)
        p95_us = sorted(times)[int(len(times) * 0.95)]
        print(f"\n  publish_delta() avg={avg_us:.0f}us, p95={p95_us:.0f}us")
        assert avg_us < 10_000, f"publish_delta() too slow: {avg_us:.0f}us"

    def test_high_frequency_publish(self, bus):
        """Publish 1000 events, measure time."""
        received = []

        def handler(e):
            received.append(e)

        bus.subscribe("hf_sub", None, handler)
        n = 1000

        start = time.perf_counter()
        for i in range(n):
            bus.publish_delta("Goal", f"g{i}", "create", {}, "test")
        elapsed = time.perf_counter() - start

        rate = n / elapsed
        print(f"\n  {n} publishes in {elapsed*1000:.2f}ms ({rate:.0f} ops/sec)")
        assert elapsed < 1.0, f"1000 publishes took {elapsed*1000:.2f}ms (too slow)"
        assert len(received) == n

    def test_many_subscribers(self, bus):
        """100 subscribers, measure publish time."""
        for i in range(100):
            bus.subscribe(f"sub_{i}", None, lambda e: None)

        start = time.perf_counter()
        bus.publish_delta("Goal", "g1", "create", {}, "test")
        elapsed = time.perf_counter() - start

        print(f"\n  100 subscribers publish: {elapsed*1000:.2f}ms")
        assert elapsed < 0.1, f"100 subscribers too slow: {elapsed*1000:.2f}ms"

    def test_topic_filtering_performance(self, bus):
        """Topic filtering vs global subscription performance."""
        # Setup: 10 topic subscribers + 10 global
        for i in range(10):
            bus.subscribe(f"goal_{i}", "Goal", lambda e: None)
        for i in range(10):
            bus.subscribe(f"global_{i}", None, lambda e: None)

        times = []
        for _ in range(100):
            start = time.perf_counter()
            bus.publish_delta("Goal", "g1", "update", {}, "test")
            elapsed = (time.perf_counter() - start) * 1_000_000
            times.append(elapsed)

        avg_us = sum(times) / len(times)
        print(f"\n  Topic-filtered publish: avg={avg_us:.0f}us")
        assert avg_us < 20_000, f"Filtered publish too slow: {avg_us:.0f}us"

    def test_unsubscribe_performance(self, bus):
        """Unsubscribe performance with many subscriptions."""
        for i in range(50):
            bus.subscribe(f"sub_{i}", None, lambda e: None)

        start = time.perf_counter()
        for i in range(50):
            bus.unsubscribe(f"sub_{i}")
        elapsed = (time.perf_counter() - start) * 1000

        print(f"\n  50 unsubscribes: {elapsed:.2f}ms")
        assert elapsed < 100, f"Unsubscribe too slow: {elapsed:.2f}ms"

    def test_subscriber_count_performance(self, bus):
        """get_subscriber_count() performance."""
        for i in range(20):
            bus.subscribe(f"sub_{i}", None, lambda e: None)

        times = []
        for _ in range(100):
            start = time.perf_counter()
            bus.get_subscriber_count()
            elapsed = (time.perf_counter() - start) * 1_000_000
            times.append(elapsed)

        avg_us = sum(times) / len(times)
        print(f"\n  get_subscriber_count() avg: {avg_us:.0f}us")
        assert avg_us < 500, f"get_subscriber_count() too slow: {avg_us:.0f}us"

    def test_concurrent_publish_simulated(self, bus):
        """Simulate concurrent publishes via rapid sequential calls."""
        import threading
        received = []
        lock = threading.Lock()

        def handler(e):
            with lock:
                received.append(e)

        bus.subscribe("conc_sub", None, handler)

        n = 200
        threads = []
        for i in range(n):
            t = threading.Thread(
                target=bus.publish_delta,
                args=("Goal", f"g{i}", "create", {}, "test"),
            )
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        print(f"\n  {n} concurrent publishes: {len(received)} received")
        assert len(received) == n
