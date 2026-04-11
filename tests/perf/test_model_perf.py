"""Model serialization performance benchmarks."""

import sys
sys.path.insert(0, '.')

import pytest
import time
from core.models import (
    AgentState,
    IntentChain,
    IntentNode,
    Goal,
    Plan,
    DeltaUpdate,
    EntityType,
)


class TestModelPerformance:
    """Model serialization and creation performance."""

    def test_agent_state_serialization_speed(self):
        """Serialize/deserialize AgentState."""
        times = []
        for _ in range(100):
            state = AgentState(user_query="test query")

            start = time.perf_counter()
            # Simulate serialization: model_dump
            serialized = state.model_dump()
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        avg_ms = sum(times) / len(times)
        print(f"\n  AgentState serialization avg: {avg_ms:.4f}ms")
        assert avg_ms < 10, f"AgentState serialization too slow: {avg_ms:.4f}ms"

    def test_intent_chain_serialization(self):
        """Serialize/deserialize IntentChain with many nodes."""
        nodes = [IntentNode(intent=f"intent_{i}", confidence=0.9) for i in range(10)]
        chain = IntentChain(nodes=nodes)

        times = []
        for _ in range(50):
            start = time.perf_counter()
            serialized = chain.model_dump()
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        avg_ms = sum(times) / len(times)
        print(f"\n  IntentChain (10 nodes) serialization avg: {avg_ms:.4f}ms")
        assert avg_ms < 5, f"IntentChain serialization too slow: {avg_ms:.4f}ms"

    def test_delta_update_creation_speed(self):
        """Create many DeltaUpdate objects rapidly."""
        times = []
        for _ in range(500):
            start = time.perf_counter()
            du = DeltaUpdate(
                entity_type=EntityType.GOAL,
                entity_id=f"goal_{_}",
                operation="update",
                changed_keys=["status"],
                delta={"status": "completed"},
                source_agent="executor",
            )
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        avg_ms = sum(times) / len(times)
        print(f"\n  DeltaUpdate creation avg: {avg_ms:.4f}ms")
        assert avg_ms < 1, f"DeltaUpdate creation too slow: {avg_ms:.4f}ms"

    def test_goal_creation_speed(self):
        """Create many Goal objects rapidly."""
        times = []
        for i in range(200):
            start = time.perf_counter()
            goal = Goal(type="execute", description=f"Goal {i}")
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        avg_ms = sum(times) / len(times)
        print(f"\n  Goal creation avg: {avg_ms:.4f}ms")
        assert avg_ms < 1, f"Goal creation too slow: {avg_ms:.4f}ms"

    def test_plan_creation_speed(self):
        """Create many Plan objects rapidly."""
        times = []
        for i in range(200):
            start = time.perf_counter()
            plan = Plan(
                intent_chain_ref=f"ref_{i}",
                execution_order=[f"g1_{i}", f"g2_{i}"],
            )
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        avg_ms = sum(times) / len(times)
        print(f"\n  Plan creation avg: {avg_ms:.4f}ms")
        assert avg_ms < 1, f"Plan creation too slow: {avg_ms:.4f}ms"

    def test_agent_state_with_large_messages(self):
        """AgentState with large messages list."""
        messages = [{"role": "user", "content": f"message {i}"} for i in range(100)]
        state = AgentState(user_query="test", messages=messages)

        times = []
        for _ in range(50):
            start = time.perf_counter()
            serialized = state.model_dump()
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        avg_ms = sum(times) / len(times)
        print(f"\n  AgentState (100 messages) serialization avg: {avg_ms:.4f}ms")
        assert avg_ms < 20, f"Large AgentState too slow: {avg_ms:.4f}ms"

    def test_many_goals_dict_access(self):
        """Access many goals in a dict."""
        goals = {
            f"goal_{i}": Goal(type="execute", description=f"Goal {i}")
            for i in range(50)
        }

        times = []
        for _ in range(100):
            start = time.perf_counter()
            for gid, goal in goals.items():
                _ = goal.status
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        avg_ms = sum(times) / len(times)
        print(f"\n  50-goal dict access avg: {avg_ms:.4f}ms")
        assert avg_ms < 10, f"Goals dict access too slow: {avg_ms:.4f}ms"
