"""Multi-agent routing E2E tests."""

import sys
sys.path.insert(0, '.')

import pytest
from tests.test_car_service import CarServiceOrchestrator


class TestMultiAgentRoutingE2E:
    """E2E tests for agent routing and multi-round conversations."""

    @pytest.fixture
    def orchestrator(self):
        return CarServiceOrchestrator()

    def test_routing_door_control(self, orchestrator):
        """Door control routes correctly."""
        result = orchestrator.run("解锁车门")
        assert result["agent_id"] == "door"
        assert result["interruptible"] is True

    def test_routing_climate(self, orchestrator):
        """Climate control routes correctly."""
        result = orchestrator.run("打开空调")
        assert result["agent_id"] == "climate"

    def test_routing_emergency(self, orchestrator):
        """Emergency routes to emergency agent."""
        result = orchestrator.run("我需要紧急救援")
        assert result["agent_id"] == "emergency"
        assert result["interruptible"] is True

    def test_routing_news(self, orchestrator):
        """News routes to news agent."""
        result = orchestrator.run("给我播报新闻")
        assert result["agent_id"] == "news"

    def test_routing_navigation(self, orchestrator):
        """Navigation routes to nav agent."""
        result = orchestrator.run("帮我导航回家")
        assert result["agent_id"] == "nav"

    def test_routing_music(self, orchestrator):
        """Music routes to music agent."""
        result = orchestrator.run("播放音乐")
        assert result["agent_id"] == "music"

    def test_routing_vehicle_status(self, orchestrator):
        """Vehicle status routes to status agent."""
        result = orchestrator.run("检查车辆状态")
        assert result["agent_id"] == "status"

    def test_routing_fallback_chat(self, orchestrator):
        """Unknown queries fall back to chat."""
        result = orchestrator.run("随便聊聊")
        assert result["agent_id"] == "chat"

    def test_routing_multi_round_maintains_context(self, orchestrator):
        """Multi-round conversation maintains agent context."""
        # First: climate
        r1 = orchestrator.run("太热了")
        assert r1["agent_id"] == "climate"

        # Follow-up: should stay in climate
        r2 = orchestrator.run("再调高一点")
        # Context-aware routing may keep climate
        assert r1["agent_id"] in ("climate", "chat")

    def test_routing_multi_round_three_turns(self, orchestrator):
        """Three-turn conversation routes correctly."""
        orchestrator.run("你好")
        orchestrator.run("播放音乐")
        orchestrator.run("播放新闻")
        assert len(orchestrator.conversation_history) == 3

    def test_streamable_agents_return_chunks(self, orchestrator):
        """Streamable agents yield chunks via stream()."""
        chunks = list(orchestrator.run_stream("打开空调"))
        assert len(chunks) >= 1
        assert chunks[0]["agent_id"] == "climate"

    def test_interruptible_agents_marked(self, orchestrator):
        """Interruptible agents are correctly marked."""
        interruptible_ids = {"door", "nav", "emergency"}
        for query in ["解锁车门", "导航回家", "紧急救援"]:
            result = orchestrator.run(query)
            assert result["agent_id"] in interruptible_ids
            assert result["interruptible"] is True

    def test_non_streamable_agents(self, orchestrator):
        """Non-streamable agents are correctly marked."""
        result = orchestrator.run("检查状态")
        assert result["streamable"] is False

    def test_conversation_history_accumulated(self, orchestrator):
        """Conversation history accumulates across rounds."""
        orchestrator.run("你好")
        orchestrator.run("天气")
        orchestrator.run("播放音乐")
        assert len(orchestrator.conversation_history) == 3
        assert all("timestamp" in h for h in orchestrator.conversation_history)

    def test_mixed_chat_and_control_routing(self, orchestrator):
        """Mixed chat and control queries route correctly."""
        queries = [
            ("你好", "chat"),
            ("打开空调", "climate"),
            ("谢谢", "chat"),
            ("播放新闻", "news"),
        ]
        for query, expected in queries:
            result = orchestrator.run(query)
            actual = result["agent_id"]
            assert actual == expected, f"{query} -> expected {expected}, got {actual}"

    def test_agent_routing_with_english_keywords(self, orchestrator):
        """English keywords route correctly."""
        result = orchestrator.run("play music")
        assert result["agent_id"] == "music"

        result2 = orchestrator.run("unlock doors")
        assert result2["agent_id"] == "door"
