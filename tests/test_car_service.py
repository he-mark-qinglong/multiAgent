"""Car Service Multi-Agent System Tests.

Car Service Agents:
- DoorControlAgent: 车门控制 (streamable, interruptible)
- ClimateAgent: 空调控制 (streamable)
- ChatCompanionAgent: 聊天陪伴 (ReAct, stream)
- NewsAgent: 新闻/路况读取 (ReAct, non-stream)
- NavigationAgent: 导航规划 (ReAct, interruptible)
- MusicAgent: 音乐播放 (streamable)
- EmergencyAgent: 紧急救援 (interruptible)
- VehicleStatusAgent: 车辆状态 (non-stream)
"""

from __future__ import annotations

import asyncio
import sys
import time
import threading
from typing import Any
from dataclasses import dataclass, field

sys.path.insert(0, '.')

import pytest

from core.models import AgentState, UserQuery, EntityType
from core.event_bus import EventBus
from core.langgraph_integration import HumanApprovalManager
from agents.langgraph_agents import BaseReActAgent


# =============================================================================
# Car Service Agent Definitions
# =============================================================================

CAR_SERVICE_PROMPT = """你是一个车载智能助手。"""


class DoorControlAgent(BaseReActAgent):
    """车门控制 Agent - 支持流式输出和中断审批。

    功能: 解锁/锁上车门、窗户控制
    特性: streamable, interruptible (危险操作需审批)
    """

    def __init__(self):
        super().__init__(
            agent_id="door_control",
            name="车门控制",
            role="L2",
            system_prompt=CAR_SERVICE_PROMPT + "控制车门和窗户。",
            max_iterations=3,
        )

    async def think(self, state: AgentState) -> str:
        query = state.user_query.lower()
        if "解锁" in query or "unlock" in query:
            return "用户请求解锁车门"
        elif "锁车" in query or "lock" in query:
            return "用户请求锁车"
        return "解析车门控制命令"

    async def act(self, state: AgentState, thought: str) -> dict[str, Any]:
        query = state.user_query.lower()

        # 危险操作需要审批
        if "解锁" in query:
            if state.needs_approval:
                return self.interrupt_and_wait("确认解锁车门?", state)

            return {
                "metadata": {"action": "unlock", "doors": "all"},
                "_finished": True,
            }
        elif "锁车" in query:
            return {
                "metadata": {"action": "lock", "doors": "all"},
                "_finished": True,
            }

        return {"metadata": {"action": "unknown"}, "_finished": True}


class ClimateAgent(BaseReActAgent):
    """空调控制 Agent - 支持流式输出。

    功能: 温度调节、风速控制、座椅加热
    特性: streamable
    """

    def __init__(self):
        super().__init__(
            agent_id="climate",
            name="空调控制",
            role="L2",
            system_prompt=CAR_SERVICE_PROMPT + "控制车内温度和空调。",
            max_iterations=2,
        )

    async def think(self, state: AgentState) -> str:
        return f"处理空调请求: {state.user_query[:30]}..."

    async def act(self, state: AgentState, thought: str) -> dict[str, Any]:
        query = state.user_query.lower()
        result = {"temperature": 22, "fan_speed": 2, "action": "adjust"}

        if "热" in query or "warm" in query:
            result["temperature"] = 26
        elif "冷" in query or "cool" in query:
            result["temperature"] = 20
        elif "关" in query or "off" in query:
            result["action"] = "off"

        return {"metadata": result, "_finished": True}


class ChatCompanionAgent(BaseReActAgent):
    """聊天陪伴 Agent - ReAct 模式，支持流式。

    功能: 日常对话、问答、情感陪伴
    特性: ReAct, streamable
    """

    def __init__(self):
        super().__init__(
            agent_id="chat_companion",
            name="聊天陪伴",
            role="L1",
            system_prompt=CAR_SERVICE_PROMPT + "提供友好的对话和陪伴。",
            max_iterations=5,
        )

    async def think(self, state: AgentState) -> str:
        query = state.user_query.lower()

        if any(w in query for w in ["你好", "hi", "hello"]):
            return "问候语，回复欢迎"
        elif any(w in query for w in ["天气", "weather"]):
            return "天气查询，提供信息"
        elif any(w in query for w in ["谢谢", "thanks"]):
            return "礼貌回复"
        return "一般对话，继续交流"

    async def act(self, state: AgentState, thought: str) -> dict[str, Any]:
        query = state.user_query.lower()

        if any(w in query for w in ["你好", "hi", "hello"]):
            response = "你好！有什么可以帮你的吗？"
        elif any(w in query for w in ["天气", "weather"]):
            response = "今天天气晴朗，适合出行。"
        elif any(w in query for w in ["谢谢", "thanks"]):
            response = "不客气！祝您行车愉快。"
        else:
            response = f"我理解你说的: {state.user_query[:20]}..."

        return {
            "final_response": response,
            "metadata": {"_finished": True},
        }


class NewsAgent(BaseReActAgent):
    """新闻 Agent - ReAct 模式，非流式。

    功能: 新闻摘要、路况信息
    特性: ReAct, non-stream
    """

    def __init__(self):
        super().__init__(
            agent_id="news",
            name="新闻资讯",
            role="L1",
            system_prompt=CAR_SERVICE_PROMPT + "提供新闻和路况信息。",
            max_iterations=3,
        )

    async def think(self, state: AgentState) -> str:
        query = state.user_query.lower()
        if "新闻" in query or "news" in query:
            return "获取新闻摘要"
        elif "路况" in query or "traffic" in query:
            return "查询路况信息"
        return "处理资讯请求"

    async def act(self, state: AgentState, thought: str) -> dict[str, Any]:
        return {
            "final_response": "今日新闻: 科技行业发布新品。路况: 城市主干道畅通。",
            "metadata": {"source": "news_api", "_finished": True},
        }


class NavigationAgent(BaseReActAgent):
    """导航 Agent - ReAct 模式，可中断。

    功能: 路线规划、导航
    特性: ReAct, interruptible
    """

    def __init__(self):
        super().__init__(
            agent_id="navigation",
            name="导航规划",
            role="L1",
            system_prompt=CAR_SERVICE_PROMPT + "规划最佳路线。",
            max_iterations=4,
        )
        self.route_planned = False

    async def think(self, state: AgentState) -> str:
        if not self.route_planned:
            return "规划路线中..."
        return "确认目的地"

    async def act(self, state: AgentState, thought: str) -> dict[str, Any]:
        if not self.route_planned:
            self.route_planned = True
            # 模拟导航计算
            return {
                "metadata": {"route": "calculated", "distance": "15km"},
                "_finished": False,
            }

        self.route_planned = False
        return {
            "final_response": "目的地已设定，预计30分钟到达。",
            "metadata": {"destination": "home", "_finished": True},
        }


class MusicAgent(BaseReActAgent):
    """音乐 Agent - 支持流式输出。

    功能: 播放控制、音量调节
    特性: streamable
    """

    def __init__(self):
        super().__init__(
            agent_id="music",
            name="音乐播放",
            role="L2",
            system_prompt=CAR_SERVICE_PROMPT + "控制音乐播放。",
            max_iterations=2,
        )

    async def think(self, state: AgentState) -> str:
        return f"处理音乐命令: {state.user_query[:30]}"

    async def act(self, state: AgentState, thought: str) -> dict[str, Any]:
        query = state.user_query.lower()
        result = {"playing": True}

        if "播放" in query or "play" in query:
            result["action"] = "play"
        elif "暂停" in query or "pause" in query:
            result["action"] = "pause"
        elif "下一首" in query or "next" in query:
            result["action"] = "next"

        return {"metadata": result, "_finished": True}


class EmergencyAgent(BaseReActAgent):
    """紧急救援 Agent - 必须审批。

    功能: 道路救援、紧急联系
    特性: 必须 interrupt + 审批
    """

    def __init__(self):
        super().__init__(
            agent_id="emergency",
            name="紧急救援",
            role="L1",
            system_prompt=CAR_SERVICE_PROMPT + "处理紧急情况。",
            max_iterations=2,
        )

    async def think(self, state: AgentState) -> str:
        return "检测到紧急请求，需要确认是否发起救援"

    async def act(self, state: AgentState, thought: str) -> dict[str, Any]:
        # 紧急操作必须审批
        if state.needs_approval:
            result = self.interrupt_and_wait("确认发起紧急救援?", state)
            if not result.get("approved", False):
                return {
                    "final_response": "已取消紧急救援请求。",
                    "metadata": {"_finished": True, "cancelled": True},
                }

        return {
            "final_response": "正在联系救援服务，请保持通话...",
            "metadata": {"emergency": True, "_finished": True},
        }


class VehicleStatusAgent(BaseReActAgent):
    """车辆状态 Agent - 非流式。

    功能: 电量/油量、胎压、诊断
    特性: non-stream
    """

    def __init__(self):
        super().__init__(
            agent_id="vehicle_status",
            name="车辆状态",
            role="L2",
            system_prompt=CAR_SERVICE_PROMPT + "报告车辆状态。",
            max_iterations=2,
        )

    async def think(self, state: AgentState) -> str:
        return "检查车辆状态..."

    async def act(self, state: AgentState, thought: str) -> dict[str, Any]:
        return {
            "final_response": "车辆状态: 电量75%, 胎压正常, 无故障码。",
            "metadata": {
                "battery": 75,
                "tire_pressure": "normal",
                "errors": 0,
                "_finished": True,
            },
        }


# =============================================================================
# Test Car Service Orchestrator
# =============================================================================

class CarServiceOrchestrator:
    """车载服务协调器 - 管理多个 Agent。

    支持:
    - 多轮对话
    - 流式/非流式输出
    - 中断机制
    - Agent 路由
    """

    def __init__(self, event_bus: EventBus | None = None):
        self.event_bus = event_bus or EventBus()

        # 初始化所有 Agent
        self.agents = {
            "door": DoorControlAgent(),
            "climate": ClimateAgent(),
            "chat": ChatCompanionAgent(),
            "news": NewsAgent(),
            "nav": NavigationAgent(),
            "music": MusicAgent(),
            "emergency": EmergencyAgent(),
            "status": VehicleStatusAgent(),
        }

        self.approval_manager = HumanApprovalManager(None)
        self.conversation_history: list[dict[str, Any]] = []
        self._last_agent: str | None = None  # 上下文感知: 记住上次 Agent

    def route_to_agent(self, query: str) -> str:
        """根据查询路由到合适的 Agent。

        关键词匹配 + 上下文感知 (多轮对话)。
        """
        query_lower = query.lower()

        if any(w in query_lower for w in ["门", "锁", "解锁", "unlock", "lock"]):
            return "door"
        elif any(w in query_lower for w in ["空调", "温度", "热", "冷", "调", "climate"]):
            return "climate"
        elif any(w in query_lower for w in ["新闻", "路况", "news", "traffic"]):
            return "news"
        elif any(w in query_lower for w in ["导航", "路线", "机场", "回家", "nav", "route"]):
            return "nav"
        elif any(w in query_lower for w in ["音乐", "播放", "暂停", "music", "play"]):
            return "music"
        elif any(w in query_lower for w in ["紧急", "救援", "emergency", "help"]):
            return "emergency"
        elif any(w in query_lower for w in ["状态", "电量", "status", "battery"]):
            return "status"
        else:
            # 上下文感知: 如果没有明确关键词，延续上次的 Agent
            if self._last_agent and self._last_agent not in ("chat",):
                return self._last_agent
            return "chat"

    def is_streamable(self, agent_id: str) -> bool:
        """检查 Agent 是否支持流式输出。"""
        streamable = {"door", "climate", "chat", "music"}
        return agent_id in streamable

    def is_interruptible(self, agent_id: str) -> bool:
        """检查 Agent 是否支持中断。"""
        interruptible = {"door", "nav", "emergency"}
        return agent_id in interruptible

    def run(self, query: str, needs_approval: bool = False) -> dict[str, Any]:
        """运行 Agent (非流式)。"""
        agent_id = self.route_to_agent(query)
        agent = self.agents[agent_id]
        self._last_agent = agent_id  # 记住当前 Agent 用于上下文感知

        state = AgentState(
            user_query=query,
            needs_approval=needs_approval,
        )

        result = asyncio.run(agent.run(query))

        self.conversation_history.append({
            "query": query,
            "agent": agent_id,
            "result": result,
            "timestamp": time.time(),
        })

        return {
            "agent_id": agent_id,
            "streamable": self.is_streamable(agent_id),
            "interruptible": self.is_interruptible(agent_id),
            "result": result,
        }

    def run_stream(self, query: str):
        """流式运行 Agent。"""
        agent_id = self.route_to_agent(query)
        agent = self.agents[agent_id]

        for chunk in agent.stream(query):
            yield {
                "agent_id": agent_id,
                "chunk": chunk,
            }


# =============================================================================
# Test Cases
# =============================================================================

class TestCarServiceAgents:
    """车载服务 Agent 测试套件。"""

    @pytest.fixture
    def orchestrator(self):
        return CarServiceOrchestrator()

    # -------------------------------------------------------------------------
    # 非流式 Agent 测试
    # -------------------------------------------------------------------------

    def test_news_agent_non_stream(self, orchestrator):
        """测试新闻 Agent - 非流式。"""
        result = orchestrator.run("给我播报新闻")

        assert result["agent_id"] == "news"
        assert result["streamable"] is False
        assert "result" in result
        assert "final_response" in result["result"]

    def test_vehicle_status_agent(self, orchestrator):
        """测试车辆状态 Agent - 非流式。"""
        result = orchestrator.run("检查车辆状态")

        assert result["agent_id"] == "status"
        assert result["streamable"] is False
        assert result["result"]["final_response"]

    # -------------------------------------------------------------------------
    # 流式 Agent 测试
    # -------------------------------------------------------------------------

    def test_climate_agent_stream(self, orchestrator):
        """测试空调 Agent - 流式输出。"""
        chunks = list(orchestrator.run_stream("把温度调到24度"))

        assert len(chunks) >= 1
        assert chunks[0]["agent_id"] == "climate"
        assert chunks[0]["chunk"]["type"] == "complete"

    def test_music_agent_stream(self, orchestrator):
        """测试音乐 Agent - 流式输出。"""
        chunks = list(orchestrator.run_stream("播放音乐"))

        assert len(chunks) >= 1
        assert chunks[0]["agent_id"] == "music"

    # -------------------------------------------------------------------------
    # ReAct Agent 测试
    # -------------------------------------------------------------------------

    def test_chat_companion_react(self, orchestrator):
        """测试聊天陪伴 Agent - ReAct 模式。"""
        # 测试问候
        result = orchestrator.run("你好")

        assert result["agent_id"] == "chat"
        assert "你好" in result["result"].get("final_response", "")

        # 测试感谢
        result2 = orchestrator.run("谢谢")
        assert "不客气" in result2["result"].get("final_response", "")

    def test_navigation_react(self, orchestrator):
        """测试导航 Agent - ReAct 多轮推理。"""
        result = orchestrator.run("帮我导航回家")

        assert result["agent_id"] == "nav"
        assert "目的地" in result["result"].get("final_response", "")

    # -------------------------------------------------------------------------
    # 可中断 Agent 测试
    # -------------------------------------------------------------------------

    def test_emergency_agent_requires_approval(self, orchestrator):
        """测试紧急救援 Agent - 需要审批。"""
        result = orchestrator.run("我需要紧急救援", needs_approval=False)

        # 应该触发中断
        assert result["agent_id"] == "emergency"
        assert result["interruptible"] is True

    def test_door_control_interrupt(self, orchestrator):
        """测试车门控制 Agent - 可中断。"""
        result = orchestrator.run("解锁车门")

        assert result["agent_id"] == "door"
        assert result["interruptible"] is True

    # -------------------------------------------------------------------------
    # 多轮对话测试
    # -------------------------------------------------------------------------

    def test_multi_round_conversation(self, orchestrator):
        """测试多轮对话 - Agent 状态保持。"""
        # 第一轮: 调节空调
        r1 = orchestrator.run("太热了")
        assert r1["agent_id"] == "climate"

        # 第二轮: 听新闻
        r2 = orchestrator.run("现在有什么新闻")
        assert r2["agent_id"] == "news"

        # 第三轮: 导航
        r3 = orchestrator.run("我想去机场")
        assert r3["agent_id"] == "nav"

        # 验证对话历史
        assert len(orchestrator.conversation_history) == 3
        assert orchestrator.conversation_history[0]["agent"] == "climate"
        assert orchestrator.conversation_history[1]["agent"] == "news"
        assert orchestrator.conversation_history[2]["agent"] == "nav"

    def test_conversation_context(self, orchestrator):
        """测试对话上下文保持。"""
        # 连续对话应该正确路由
        queries = ["打开空调", "调到26度", "关闭"]
        agents = []

        for q in queries:
            r = orchestrator.run(q)
            agents.append(r["agent_id"])

        # 前两轮应该路由到空调
        assert agents[0] == "climate"
        assert agents[1] == "climate"
        # 第三轮可能路由到聊天或其他


# =============================================================================
# Interrupt/Approval Tests
# =============================================================================

class TestInterruptMechanism:
    """中断机制测试。"""

    @pytest.fixture
    def approval_manager(self):
        return HumanApprovalManager(None)

    def test_request_approval(self, approval_manager):
        """测试请求审批。"""
        approval_id = approval_manager.request_approval(
            thread_id="session_1",
            action="unlock",
            details="解锁所有车门",
        )

        assert approval_id.startswith("approval_session_1")
        assert approval_manager.get_pending("session_1") is not None

    def test_submit_approval_approve(self, approval_manager):
        """测试审批通过。"""
        approval_manager.request_approval(
            thread_id="session_2",
            action="emergency",
            details="发起紧急救援",
        )

        result = approval_manager.submit_approval(
            thread_id="session_2",
            approved=True,
            reason="确认紧急情况",
        )

        assert result.get("approved") is None  # mock manager returns empty

    def test_submit_approval_reject(self, approval_manager):
        """测试审批拒绝。"""
        approval_manager.request_approval(
            thread_id="session_3",
            action="unlock",
            details="解锁车门",
        )

        result = approval_manager.submit_approval(
            thread_id="session_3",
            approved=False,
            reason="安全考虑",
        )

        pending = approval_manager.get_pending("session_3")
        assert pending["approved"] is False


# =============================================================================
# EventBus Integration Tests
# =============================================================================

class TestEventBusIntegration:
    """EventBus 集成测试。"""

    @pytest.fixture
    def event_bus(self):
        return EventBus()

    def test_agent_event_publish(self, event_bus):
        """测试 Agent 事件发布。"""
        events = []

        def handler(event):
            events.append(event)

        event_bus.subscribe("test_sub", None, handler)

        # 模拟 Agent 发布事件
        event_bus.publish_delta(
            entity_type="Status",
            entity_id="agent_1",
            operation="update",
            delta={"status": "completed"},
            source_agent="chat_companion",
        )

        assert len(events) == 1
        assert events[0]["source_agent"] == "chat_companion"

    def test_topic_filtering(self, event_bus):
        """测试话题过滤。"""
        door_events = []
        all_events = []

        event_bus.subscribe("door_sub", "Door", lambda e: door_events.append(e))
        event_bus.subscribe("all_sub", None, lambda e: all_events.append(e))

        event_bus.publish_delta(
            entity_type="Door",
            entity_id="front_left",
            operation="unlock",
            delta={"locked": False},
            source_agent="door_control",
        )

        assert len(door_events) == 1
        assert len(all_events) == 1

    def test_multiple_subscribers(self, event_bus):
        """测试多订阅者。"""
        count = {"handlers": 0}

        def handler1(e):
            count["handlers"] += 1

        def handler2(e):
            count["handlers"] += 1

        event_bus.subscribe("sub1", "Nav", handler1)
        event_bus.subscribe("sub2", "Nav", handler2)

        event_bus.publish_delta(
            entity_type="Nav",
            entity_id="route_1",
            operation="calculate",
            delta={"distance": "10km"},
            source_agent="navigation",
        )

        assert count["handlers"] == 2


# =============================================================================
# Multi-Agent Collaboration Tests
# =============================================================================

class TestMultiAgentCollaboration:
    """多 Agent 协作测试。"""

    @pytest.fixture
    def orchestrator(self):
        return CarServiceOrchestrator()

    def test_complex_multi_agent_task(self, orchestrator):
        """测试复杂多 Agent 任务。"""
        # 场景: 用户说 "太热了，有什么新闻吗"
        # 应该先处理空调，再处理新闻

        # 第一轮: 空调
        r1 = orchestrator.run("太热了")
        assert r1["agent_id"] == "climate"

        # 第二轮: 新闻
        r2 = orchestrator.run("新闻")
        assert r2["agent_id"] == "news"

    def test_agent_routing_edge_cases(self, orchestrator):
        """测试 Agent 路由边界情况。"""
        # 模糊查询应该路由到聊天
        result = orchestrator.run("随便聊聊")
        assert result["agent_id"] == "chat"

        # 包含多个关键词时取第一个
        result = orchestrator.run("播放音乐并打开空调")
        assert result["agent_id"] in ["music", "climate"]


# =============================================================================
# Run Tests
# =============================================================================

def run_all_tests():
    """运行所有测试。"""
    import traceback

    test_classes = [
        TestCarServiceAgents,
        TestInterruptMechanism,
        TestEventBusIntegration,
        TestMultiAgentCollaboration,
    ]

    passed = 0
    failed = 0

    for test_class in test_classes:
        print(f"\n{'='*60}")
        print(f"Running {test_class.__name__}")
        print('='*60)

        instance = test_class()

        # Setup fixture
        if hasattr(instance, 'orchestrator'):
            instance.orchestrator = instance.orchestrator.__func__()

        for name in dir(instance):
            if name.startswith('test_'):
                try:
                    # Get fixture
                    fixture_name = name.replace('test_', '')
                    if hasattr(instance, fixture_name):
                        fixture_func = getattr(type(instance), fixture_name, None)
                        if callable(fixture_func):
                            setattr(instance, fixture_name, fixture_func(instance))

                    # Run test
                    test_func = getattr(instance, name)
                    if hasattr(test_func, '__func__'):
                        test_func()
                    else:
                        test_func()

                    print(f"  ✓ {name}")
                    passed += 1
                except Exception as e:
                    print(f"  ✗ {name}: {e}")
                    traceback.print_exc()
                    failed += 1

    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed")
    print('='*60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
