"""Agent performance benchmarks."""

import sys
sys.path.insert(0, '.')

import pytest
import time
import asyncio
from core.models import AgentState
from agents.langgraph_agents import BaseReActAgent


class BenchmarkAgent(BaseReActAgent):
    """Minimal agent for performance testing."""

    def __init__(self):
        super().__init__(
            agent_id="benchmark",
            name="Benchmark",
            role="L1",
            system_prompt="Benchmark agent",
            max_iterations=2,
        )

    async def think(self, state: AgentState) -> str:
        return "benchmark thought"

    async def act(self, state: AgentState, thought: str) -> dict:
        return {"final_response": f"Result: {state.user_query}", "metadata": {"_finished": True}}


class TestAgentPerformance:
    """Agent performance benchmarks."""

    @pytest.fixture
    def agent(self):
        return BenchmarkAgent()

    def test_base_agent_run_latency(self, agent):
        """Measure single run() latency."""
        times = []
        for i in range(10):
            start = time.perf_counter()
            asyncio.run(agent.run(f"query_{i}"))
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        avg_ms = sum(times) / len(times)
        print(f"\n  run() avg latency: {avg_ms:.2f}ms")
        assert avg_ms < 500, f"run() too slow: {avg_ms:.2f}ms"

    def test_base_agent_stream_throughput(self, agent):
        """Measure stream() throughput."""
        n = 10
        start = time.perf_counter()
        for i in range(n):
            list(agent.stream(f"query_{i}"))
        elapsed = time.perf_counter() - start

        rate = n / elapsed
        print(f"\n  stream() throughput: {rate:.2f} calls/sec")
        assert rate > 0.5, f"stream() throughput too low: {rate:.2f}"

    def test_multi_agent_sequential_routing(self):
        """Route N queries sequentially."""
        from tests.test_car_service import CarServiceOrchestrator
        orch = CarServiceOrchestrator()
        queries = ["你好", "播放音乐", "打开空调", "播放新闻", "导航回家"]

        start = time.perf_counter()
        for q in queries:
            orch.run(q)
        elapsed = (time.perf_counter() - start) * 1000

        avg_ms = elapsed / len(queries)
        print(f"\n  Sequential routing avg: {avg_ms:.2f}ms per query")
        assert elapsed < 1000, f"Sequential routing too slow: {elapsed:.2f}ms"

    def test_multi_agent_parallel_routing(self):
        """Route N queries in parallel."""
        from tests.test_car_service import CarServiceOrchestrator
        import concurrent.futures

        orch = CarServiceOrchestrator()
        queries = ["你好", "播放音乐", "打开空调", "播放新闻", "导航回家"]

        start = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            list(executor.map(orch.run, queries))
        elapsed = time.perf_counter() - start

        total_ms = elapsed * 1000
        print(f"\n  Parallel routing ({len(queries)} queries): {total_ms:.2f}ms total")
        # Parallel should be faster than sequential
        assert elapsed < 2.0, f"Parallel routing too slow: {total_ms:.2f}ms"

    def test_agent_stream_chunk_count(self, agent):
        """Measure number of chunks produced by stream()."""
        chunks = list(agent.stream("test query"))
        print(f"\n  stream() produced {len(chunks)} chunks")
        assert len(chunks) >= 1

    def test_agent_conversation_history_performance(self):
        """Adding to conversation history performance."""
        from tests.test_car_service import CarServiceOrchestrator
        import time

        orch = CarServiceOrchestrator()
        queries = [f"查询{i}" for i in range(20)]

        start = time.perf_counter()
        for q in queries:
            orch.run(q)
        elapsed = (time.perf_counter() - start) * 1000

        print(f"\n  20-round conversation: {elapsed:.2f}ms total")
        assert elapsed < 2000, f"20-round conversation too slow: {elapsed:.2f}ms"
        assert len(orch.conversation_history) == 20
