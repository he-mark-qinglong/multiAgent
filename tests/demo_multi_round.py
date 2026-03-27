#!/usr/bin/env python3
"""多轮对话测试脚本 - 用于对照 LangSmith tracing 效果。

用法:
    python tests/demo_multi_round.py
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.event_bus import EventBus
from core.langgraph_integration import HumanApprovalManager
from agents.langgraph_agents import BaseReActAgent
from core.models import AgentState, IntentStatus, GoalStatus
from typing import Any


# ============================================================================
# Mock Agents (简化版，用于演示)
# ============================================================================

class SimpleAgent:
    """简化 Agent，用于演示多轮对话路由。"""

    # Agent 回复模板
    RESPONSES = {
        "chat": [
            "好的，我明白了。",
            "没问题，有什么可以帮您的？",
            "好的，继续说。",
            "明白了，请讲。",
            "收到，还有什么需要吗？",
        ],
        "climate": {
            "开": "好的，已开启空调。",
            "关": "好的，已关闭空调。",
            "调": "已为您调节温度。",
            "热": "已调低温度制冷。",
            "冷": "已调高温度制热。",
            "default": "空调已为您调整到舒适温度。",
        },
        "music": {
            "播放": "好的，正在为您播放音乐。",
            "这首": "谢谢欣赏，这首歌确实不错。",
            "暂停": "已暂停播放。",
            "继续": "已继续播放。",
            "default": "音乐播放中...",
        },
        "nav": {
            "去": "已为您规划路线，正在导航。",
            "堵": "当前路况畅通，预计30分钟到达。",
            "改": "好的，已为您重新规划路线。",
            "取消": "已取消导航。",
            "default": "导航已设置。",
        },
        "news": {
            "default": "今日新闻：1. 天气晴朗 2. 交通顺畅 3. 股市上涨",
        },
        "status": {
            "default": "车辆状态良好：电量 85%，温度 22°C，行驶里程 120km",
        },
        "emergency": {
            "default": "⚠️ 已收到紧急求助请求，正在为您联系紧急救援服务，请保持通话。",
        },
    }

    def __init__(self, agent_id: str, name: str, respond_template: str = ""):
        self.agent_id = agent_id
        self.name = name

    def _get_response(self, query: str) -> str:
        """根据 query 内容和 Agent 类型生成智能回复。"""
        query_lower = query.lower()

        # Chat Agent 随机回复
        if self.agent_id == "chat":
            import random
            return random.choice(self.RESPONSES["chat"])

        # Emergency Agent
        if self.agent_id == "emergency":
            return self.RESPONSES["emergency"]["default"]

        # 其他 Agent 关键词匹配
        agent_responses = self.RESPONSES.get(self.agent_id, {})
        for keyword, response in agent_responses.items():
            if keyword != "default" and keyword in query_lower:
                return response

        return agent_responses.get("default", f"[{self.name}] 已处理: {query}")

    def run(self, query: str) -> dict[str, Any]:
        response = self._get_response(query)
        return {
            "final_response": response,
            "agent_id": self.agent_id,
            "agent_name": self.name,
        }

    def stream(self, query: str):
        result = self.run(query)
        yield {"type": "complete", "data": result, "agent_id": self.agent_id}


# ============================================================================
# Orchestrator
# ============================================================================

class CarServiceOrchestrator:
    """车载服务编排器 - 演示多轮对话路由。"""

    def __init__(self, event_bus: EventBus | None = None):
        self.event_bus = event_bus or EventBus()
        self.approval_manager = HumanApprovalManager(None)
        self.conversation_history: list[dict[str, Any]] = []
        self._last_agent: str | None = None

        # 初始化 Agent
        self.agents = {
            "door": SimpleAgent("door", "车门控制"),
            "climate": SimpleAgent("climate", "空调控制"),
            "chat": SimpleAgent("chat", "闲聊"),
            "news": SimpleAgent("news", "新闻"),
            "nav": SimpleAgent("nav", "导航"),
            "music": SimpleAgent("music", "音乐"),
            "emergency": SimpleAgent("emergency", "紧急救援"),
            "status": SimpleAgent("status", "车辆状态"),
        }

    def route_to_agent(self, query: str) -> str:
        """路由逻辑 + 上下文感知。"""
        query_lower = query.lower()

        # 优先级1: 明确指令
        if any(w in query_lower for w in ["门", "锁", "解锁", "unlock", "lock"]):
            return "door"
        elif any(w in query_lower for w in ["紧急", "救援", "emergency", "help"]):
            return "emergency"
        elif any(w in query_lower for w in ["状态", "电量", "status", "battery", "检查"]):
            return "status"
        elif any(w in query_lower for w in ["怎么样"]):
            return "status"
        elif any(w in query_lower for w in ["空调", "热", "冷", "climate"]):
            return "climate"
        elif any(w in query_lower for w in ["新闻", "路况", "news", "traffic"]):
            return "news"
        elif any(w in query_lower for w in ["音乐", "播放", "暂停", "music", "play"]):
            return "music"
        elif any(w in query_lower for w in ["导航", "路线", "机场", "回家", "nav", "route", "去哪", "去"]):
            return "nav"

        # 优先级2: 上下文感知跟进
        if self._last_agent:
            followups = {
                "climate": ["调", "关闭", "关掉", "开", "高", "低", "太", "冷", "热"],
                "music": ["这首", "暂停", "继续", "换一首", "好听", "不错"],
                "nav": ["堵", "改去", "算了", "取消", "导航"],
            }
            if self._last_agent in followups:
                if any(w in query_lower for w in followups[self._last_agent]):
                    return self._last_agent

        return "chat"

    def run(self, query: str, needs_approval: bool = False) -> dict[str, Any]:
        """运行单轮对话。"""
        agent_id = self.route_to_agent(query)
        self._last_agent = agent_id
        agent = self.agents[agent_id]
        result = agent.run(query)

        self.conversation_history.append({
            "query": query,
            "agent": agent_id,
            "result": result,
        })

        return {
            "agent_id": agent_id,
            "result": result,
        }


# ============================================================================
# 多轮对话演示
# ============================================================================

def print_separator(title: str):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def demo_mixed_conversation():
    """演示: 闲聊 + 车控 混合对话"""
    print_separator("🚗 演示1: 闲聊 + 车控 混合对话")

    orchestrator = CarServiceOrchestrator()

    queries = [
        "今天天气不错",
        "帮我把空调开到24度",
        "谢谢",
        "播放点音乐",
        "这首歌不错",
        "我想回家",
    ]

    for i, query in enumerate(queries, 1):
        r = orchestrator.run(query)
        result = r['result']
        print(f"\n[轮次 {i}]")
        print(f"  👤 用户: {query}")
        print(f"  🤖 路由: {r['agent_id']} ({result.get('agent_name', '')})")
        print(f"  🤖 回复: {result['final_response']}")

    print(f"\n📊 统计: 共 {len(orchestrator.conversation_history)} 轮")


def demo_climate_control():
    """演示: 空调多轮控制"""
    print_separator("🌡️ 演示2: 空调多轮控制")

    orchestrator = CarServiceOrchestrator()

    queries = [
        ("开空调", "开"),
        ("太冷了，调高一点", "调高"),
        ("关掉吧", "关"),
        ("现在舒服多了", "舒适确认"),
    ]

    for i, (query, action) in enumerate(queries, 1):
        r = orchestrator.run(query)
        result = r['result']
        is_context = i > 1 and r["agent_id"] == "climate"
        context_note = " ← 上下文感知" if is_context else ""
        print(f"\n[轮次 {i}] {action}")
        print(f"  👤 用户: {query}")
        print(f"  🤖 路由: {r['agent_id']} ({result.get('agent_name', '')}){context_note}")
        print(f"  🤖 回复: {result['final_response']}")


def demo_navigation():
    """演示: 导航多轮对话"""
    print_separator("🧭 演示3: 导航多轮对话")

    orchestrator = CarServiceOrchestrator()

    queries = [
        ("我要去北京站", "发起导航"),
        ("路上堵车吗", "询问路况"),
        ("算了，改去机场", "改目的地"),
        ("取消导航", "取消"),
    ]

    for i, (query, action) in enumerate(queries, 1):
        r = orchestrator.run(query)
        result = r['result']
        is_context = i > 1 and r["agent_id"] == "nav"
        context_note = " ← 上下文感知" if is_context else ""
        print(f"\n[轮次 {i}] {action}")
        print(f"  👤 用户: {query}")
        print(f"  🤖 路由: {r['agent_id']} ({result.get('agent_name', '')}){context_note}")
        print(f"  🤖 回复: {result['final_response']}")


def demo_long_conversation():
    """演示: 长对话上下文保持"""
    print_separator("💬 演示4: 10轮长对话")

    orchestrator = CarServiceOrchestrator()

    conversation = [
        ("你好", "闲聊"),
        ("帮我开空调", "车控"),
        ("谢谢", "闲聊"),
        ("现在温度怎么样", "查询状态"),
        ("太热了", "车控"),
        ("播放新闻", "车控"),
        ("有什么新闻", "车控"),
        ("导航到超市", "车控"),
        ("关闭导航", "车控"),
        ("再来点音乐", "车控"),
    ]

    for i, (query, purpose) in enumerate(conversation, 1):
        r = orchestrator.run(query)
        result = r['result']
        print(f"\n[轮次 {i}] ({purpose})")
        print(f"  👤 用户: {query}")
        print(f"  🤖 路由: {r['agent_id']} ({result.get('agent_name', '')})")
        print(f"  🤖 回复: {result['final_response']}")

    # 统计
    print("\n" + "-" * 40)
    print("📊 对话统计:")
    agents = {}
    for h in orchestrator.conversation_history:
        agent = h["agent"]
        agents[agent] = agents.get(agent, 0) + 1
    for agent, count in sorted(agents.items(), key=lambda x: -x[1]):
        bar = "█" * count
        print(f"  {agent:10s}: {bar} ({count})")


def demo_emergency_flow():
    """演示: 紧急救援流程"""
    print_separator("🚨 演示5: 紧急救援流程")

    orchestrator = CarServiceOrchestrator()

    # 正常对话
    r = orchestrator.run("播放音乐")
    result = r['result']
    print(f"  👤 用户: 播放音乐")
    print(f"  🤖 路由: {r['agent_id']} ({result.get('agent_name', '')})")
    print(f"  🤖 回复: {result['final_response']}")

    # 紧急情况
    r = orchestrator.run("我需要紧急救援")
    result = r['result']
    print(f"\n  👤 用户: 我需要紧急救援")
    print(f"  🤖 路由: {r['agent_id']} ({result.get('agent_name', '')}) ⚠️ 紧急!")
    print(f"  🤖 回复: {result['final_response']}")

    # 救援后
    r = orchestrator.run("谢谢")
    result = r['result']
    print(f"\n  👤 用户: 谢谢")
    print(f"  🤖 路由: {r['agent_id']} ({result.get('agent_name', '')})")
    print(f"  🤖 回复: {result['final_response']}")


def demo_routing_debug():
    """演示: 路由调试 - 展示路由决策过程"""
    print_separator("🔍 演示6: 路由决策过程")

    orchestrator = CarServiceOrchestrator()

    test_cases = [
        "太热了",           # → climate
        "现在温度怎么样",    # → status (先于 climate)
        "播放新闻",         # → news (先于 music)
        "播放音乐",         # → music
        "这首歌不错",       # → music (上下文)
        "我想回家",         # → nav
    ]

    for query in test_cases:
        r = orchestrator.run(query)
        print(f"\n  '{query}'")
        print(f"    → {r['agent_id']}")


# ============================================================================
# 主函数
# ============================================================================

def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║          🚗 多轮对话测试演示 - LangSmith 对照版              ║
║                                                              ║
║  此脚本用于测试多轮对话路由逻辑，                            ║
║  可与 LangSmith tracing 进行对照验证。                        ║
╚══════════════════════════════════════════════════════════════╝
    """)

    demos = [
        ("混合格话", demo_mixed_conversation),
        ("空调控制", demo_climate_control),
        ("导航对话", demo_navigation),
        ("长对话", demo_long_conversation),
        ("紧急救援", demo_emergency_flow),
        ("路由调试", demo_routing_debug),
    ]

    # 运行所有演示
    for name, demo in demos:
        try:
            demo()
        except Exception as e:
            print(f"\n❌ 演示 '{name}' 出错: {e}")

    print("\n" + "=" * 60)
    print("  ✅ 演示完成")
    print("=" * 60)
    print("""
下一步:
  1. 检查 LangSmith tracing 是否与上述路由一致
  2. 验证 ReAct 推理链路是否正确
  3. 对比 stream() 输出与对话结果
    """)


if __name__ == "__main__":
    main()
