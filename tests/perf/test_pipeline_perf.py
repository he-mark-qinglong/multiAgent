"""Pipeline performance benchmarks."""

import sys
sys.path.insert(0, '.')

import pytest
import time
import tracemalloc
from pipelines.collaboration_pipeline import CollaborationPipeline


class TestPipelinePerformance:
    """Pipeline performance benchmarks."""

    @pytest.fixture
    def pipeline(self):
        return CollaborationPipeline(enable_tracing=False)

    def test_pipeline_invoke_latency(self, pipeline):
        """Measure invoke() latency."""
        times = []
        for _ in range(5):
            start = time.perf_counter()
            pipeline.invoke("测试查询")
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        avg_ms = sum(times) / len(times)
        print(f"\n  invoke() avg latency: {avg_ms:.2f}ms")
        assert avg_ms < 1000, f"invoke() too slow: {avg_ms:.2f}ms"

    def test_pipeline_throughput(self, pipeline):
        """Run N invocations sequentially, report ops/sec."""
        n = 5
        start = time.perf_counter()
        for i in range(n):
            pipeline.invoke(f"查询{i}")
        elapsed = time.perf_counter() - start

        ops_per_sec = n / elapsed
        print(f"\n  Throughput: {ops_per_sec:.2f} ops/sec ({elapsed:.3f}s for {n} calls)")
        assert ops_per_sec > 0.1, f"Throughput too low: {ops_per_sec:.2f} ops/sec"

    def test_stream_chunk_timing(self, pipeline):
        """Measure time per stream chunk."""
        times = []
        for _ in range(3):
            start = time.perf_counter()
            chunks = list(pipeline.stream("测试"))
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        avg_ms = sum(times) / len(times)
        print(f"\n  stream() avg latency: {avg_ms:.2f}ms")
        assert avg_ms < 2000, f"stream() too slow: {avg_ms:.2f}ms"

    def test_multiple_thread_ids_performance(self, pipeline):
        """Multiple threads don't degrade performance catastrophically."""
        thread_ids = [f"perf_thread_{i}" for i in range(3)]
        times = []

        for tid in thread_ids:
            start = time.perf_counter()
            pipeline.invoke("测试", thread_id=tid)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        max_ms = max(times)
        print(f"\n  Max thread invoke: {max_ms:.2f}ms")
        assert max_ms < 2000, f"Threaded invoke too slow: {max_ms:.2f}ms"

    def test_memory_usage_during_invoke(self, pipeline):
        """Track memory before/after invoke."""
        tracemalloc.start()
        pipeline.invoke("内存测试")

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        current_mb = current / (1024 * 1024)
        peak_mb = peak / (1024 * 1024)
        print(f"\n  Memory: current={current_mb:.2f}MB, peak={peak_mb:.2f}MB")

        assert peak_mb < 500, f"Peak memory too high: {peak_mb:.2f}MB"

    def test_state_history_performance(self, pipeline):
        """get_state_history() performance."""
        pipeline.invoke("历史测试", thread_id="perf_history")

        start = time.perf_counter()
        history = pipeline.get_state_history("perf_history")
        elapsed = (time.perf_counter() - start) * 1000

        print(f"\n  get_state_history() latency: {elapsed:.2f}ms")
        assert elapsed < 500, f"get_state_history() too slow: {elapsed:.2f}ms"

    def test_approval_flow_performance(self, pipeline):
        """Approval flow performance."""
        thread_id = "perf_approval"

        start = time.perf_counter()
        approval_id = pipeline.request_approval(thread_id, "test", "details")
        elapsed1 = (time.perf_counter() - start) * 1000

        start = time.perf_counter()
        pipeline.get_pending_approval(thread_id)
        elapsed2 = (time.perf_counter() - start) * 1000

        start = time.perf_counter()
        pipeline.submit_approval(thread_id, True)
        elapsed3 = (time.perf_counter() - start) * 1000

        print(f"\n  Approval flow: request={elapsed1:.2f}ms, get={elapsed2:.2f}ms, submit={elapsed3:.2f}ms")
        total = elapsed1 + elapsed2 + elapsed3
        assert total < 50, f"Approval flow too slow: {total:.2f}ms"
