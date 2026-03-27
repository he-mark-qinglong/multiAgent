#!/usr/bin/env python3
"""多轮对话测试脚本 v3 - Agent + MCP Tools 集成。

展示完整的 Agent → Tool → Result 链路:
1. Agent (ReAct) 接收用户输入
2. Agent 调用 MCP/Skill Tool
3. Tool 返回结构化结果
4. Agent 解析结果生成回复

用法:
    python tests/demo_tools.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mock_tools import (
    ClimateTool, NavigationTool, MusicTool, NewsTool,
    VehicleStatusTool, DoorTool, EmergencyTool, ToolResult, MCP_TOOLS
)


# ============================================================================
# MCP Tool Registry - 工具注册表
# ============================================================================

class ToolRegistry:
    """MCP/Skill 工具注册表。"""

    def __init__(self):
        # 初始化所有工具实例
        self.climate = ClimateTool()
        self.nav = NavigationTool()
        self.music = MusicTool()
        self.news = NewsTool()
        self.status = VehicleStatusTool()
        self.door = DoorTool()
        self.emergency = EmergencyTool()

        # 工具描述 (用于 LLM 理解工具接口)
        self._tool_schemas = MCP_TOOLS

    def get_schema(self, tool_name: str) -> dict | None:
        """获取工具 schema (用于 LLM 提示)。"""
        return self._tool_schemas.get(tool_name)

    def list_tools(self) -> list[str]:
        """列出所有可用工具。"""
        return list(self._tool_schemas.keys())

    def call(self, tool_name: str, action: str, **kwargs) -> ToolResult:
        """调用工具。"""
        # 工具路由
        tool_map = {
            "climate_control": self.climate,
            "navigation": self.nav,
            "music_player": self.music,
            "news": self.news,
            "vehicle_status": self.status,
            "door_control": self.door,
            "emergency": self.emergency,
        }

        tool = tool_map.get(tool_name)
        if not tool:
            return ToolResult(success=False, state={}, description=f"❌ 未知工具: {tool_name}")

        # 动作路由
        action_map = {
            "turn_on": lambda: tool.turn_on(int(kwargs.get("value", 24))),
            "turn_off": lambda: tool.turn_off(),
            "set_temperature": lambda: tool.set_temperature(int(kwargs.get("value", 24))),
            "set_fan_speed": lambda: tool.set_fan_speed(str(kwargs.get("value", "auto"))),
            "get_status": lambda: tool.get_status(),
            "navigate": lambda: tool.navigate_to(kwargs.get("destination", "")),
            "get_traffic": lambda: tool.get_traffic(),
            "cancel": lambda: tool.cancel(),
            "play": lambda: tool.play(),
            "pause": lambda: tool.pause(),
            "skip": lambda: tool.skip(),
            "set_volume": lambda: tool.set_volume(int(kwargs.get("value", 50))),
            "lock": lambda: tool.lock(),
            "unlock": lambda: tool.unlock(),
            "get_news": lambda: tool.get_news(),
            "call": lambda: tool.call(),
        }

        handler = action_map.get(action)
        if not handler:
            return ToolResult(success=False, state={}, description=f"❌ 未知动作: {action}")

        try:
            return handler()
        except Exception as e:
            return ToolResult(success=False, state={}, description=f"❌ 工具执行错误: {e}")


# ============================================================================
# ReAct Agent with Tools - 带工具的 Agent
# ============================================================================

class AgentWithTools:
    """集成 MCP Tools 的 ReAct Agent。"""

    def __init__(self, agent_id: str, name: str, primary_tools: list[str]):
        self.agent_id = agent_id
        self.name = name
        self.primary_tools = primary_tools  # 主要使用的工具
        self.tools = ToolRegistry()

    def think(self, query: str) -> str:
        """ReAct Think: 分析意图，决定使用哪个工具。"""
        q = query.lower()

        # 意图分析 → 工具选择
        if self.agent_id == "climate":
            if any(w in q for w in ["关", "关闭"]):
                return "action: climate_control, turn_off"
            if "风速" in q:
                return "action: climate_control, set_fan_speed, value=high"
            if any(w in q for w in ["开", "开启"]):
                import re
                m = re.search(r'\d+', query)
                temp = int(m.group()) if m else 24
                return f"action: climate_control, turn_on, value={temp}"
            if "温度" in q or "调" in q:
                import re
                m = re.search(r'\d+', query)
                temp = int(m.group()) if m else 24
                return f"action: climate_control, turn_on, value={temp}"
            return "action: climate_control, get_status"

        elif self.agent_id == "nav":
            if any(w in q for w in ["取消", "停止", "算了"]):
                return "action: navigation, cancel"
            if any(w in q for w in ["堵", "路况", "多久", "预计"]):
                return "action: navigation, get_traffic"
            # 提取目的地
            import re
            dest = re.search(r'去([^\s的]+)', query)
            destination = dest.group(1) if dest else query.strip()
            return f"action: navigation, navigate, destination={destination}"

        elif self.agent_id == "music":
            if any(w in q for w in ["暂停"]):
                return "action: music_player, pause"
            if any(w in q for w in ["下一首", "换一首", "换", "切"]):
                return "action: music_player, skip"
            if any(w in q for w in ["音量"]):
                vol = 80 if "大" in q else 30 if "小" in q else 50
                return f"action: music_player, set_volume, value={vol}"
            return "action: music_player, play"

        elif self.agent_id == "status":
            return "action: vehicle_status, get_status"

        elif self.agent_id == "news":
            return "action: news, get_news"

        elif self.agent_id == "door":
            if "解" in q:
                return "action: door_control, unlock"
            return "action: door_control, lock"

        elif self.agent_id == "emergency":
            return "action: emergency, call"

        return "no_action"

    def execute(self, thought: str) -> ToolResult:
        """ReAct Act: 执行工具调用。"""
        if not thought.startswith("action:"):
            return ToolResult(success=True, state={}, description="好的，已收到。")

        # 解析 action 指令
        parts = thought.replace("action:", "").split(",")
        tool_name = parts[0].strip()
        action = parts[1].strip() if len(parts) > 1 else ""

        kwargs = {}
        for part in parts[2:]:
            if "=" in part:
                k, v = part.split("=", 1)
                kwargs[k.strip()] = v.strip()

        return self.tools.call(tool_name, action, **kwargs)

    def run(self, query: str) -> dict:
        """运行完整的 ReAct 循环。"""
        # Think
        thought = self.think(query)

        # Act
        result = self.execute(thought)

        return {
            "agent_id": self.agent_id,
            "thought": thought,
            "tool_result": result,
            "response": result.description,
            "state": result.state,
        }


# ============================================================================
# Router
# ============================================================================

class Router:
    """用户意图路由。"""

    def __init__(self):
        self._last_agent = None

    def route(self, query: str) -> str:
        q = query.lower()
        if any(w in q for w in ["门", "锁"]): return "door"
        if any(w in q for w in ["紧急", "救援"]): return "emergency"
        if any(w in q for w in ["状态", "电量", "怎么样"]): return "status"
        if any(w in q for w in ["空调", "热", "冷", "温度", "风速"]): return "climate"
        if any(w in q for w in ["新闻"]): return "news"
        if any(w in q for w in ["音乐", "播放", "这首", "不错", "下一首", "暂停", "换一首", "音量"]): return "music"
        if any(w in q for w in ["导航", "去", "机场", "堵", "多久", "路况"]): return "nav"
        return "chat"


# ============================================================================
# Orchestrator
# ============================================================================

class Orchestrator:
    """编排器 - 路由 + Agent + Tools"""

    def __init__(self):
        self.router = Router()
        self.agents = {
            "climate": AgentWithTools("climate", "空调控制", ["climate_control"]),
            "nav": AgentWithTools("nav", "导航", ["navigation"]),
            "music": AgentWithTools("music", "音乐", ["music_player"]),
            "news": AgentWithTools("news", "新闻", ["news"]),
            "status": AgentWithTools("status", "车辆状态", ["vehicle_status"]),
            "door": AgentWithTools("door", "车门", ["door_control"]),
            "emergency": AgentWithTools("emergency", "紧急救援", ["emergency"]),
            "chat": AgentWithTools("chat", "闲聊", []),
        }

    def run(self, query: str) -> dict:
        agent_id = self.router.route(query)
        agent = self.agents.get(agent_id, self.agents["chat"])
        result = agent.run(query)
        return result


# ============================================================================
# 演示
# ============================================================================

def print_sep(title):
    print(f"\n{'='*65}\n  {title}\n{'='*65}")


def demo_climate():
    """空调控制演示"""
    print_sep("🌡️ 空调控制 - Agent + MCP Tool")
    orch = Orchestrator()

    queries = [
        "开空调，23度",
        "温度调低到20度",
        "风速调大",
        "太冷了，调到26度",
        "关闭空调",
    ]

    for i, q in enumerate(queries, 1):
        r = orch.run(q)
        print(f"\n[轮次 {i}]")
        print(f"  👤 用户: {q}")
        print(f"  🔧 路由: {r['agent_id']}")
        print(f"  💭 Think: {r['thought']}")
        print(f"  🔧 Tool: {r['tool_result'].tool_name}")
        print(f"  📊 State: {r['state']}")
        print(f"  🤖 回复:")
        for line in r['response'].split('\n'):
            print(f"       {line}")


def demo_navigation():
    """导航演示"""
    print_sep("🧭 导航控制 - Agent + MCP Tool")
    orch = Orchestrator()

    queries = [
        "我要去北京站",
        "路上堵吗",
        "改去机场吧",
        "预计多久能到",
        "取消导航",
    ]

    for i, q in enumerate(queries, 1):
        r = orch.run(q)
        print(f"\n[轮次 {i}]")
        print(f"  👤 用户: {q}")
        print(f"  🔧 路由: {r['agent_id']}")
        print(f"  💭 Think: {r['thought']}")
        print(f"  🔧 Tool: {r['tool_result'].tool_name}")
        print(f"  📊 State: {r['state']}")
        print(f"  🤖 回复:")
        for line in r['response'].split('\n'):
            print(f"       {line}")


def demo_music():
    """音乐演示"""
    print_sep("🎵 音乐控制 - Agent + MCP Tool")
    orch = Orchestrator()

    queries = [
        "播放点音乐",
        "这首歌不错",
        "换下一首",
        "音量调大",
        "暂停",
    ]

    for i, q in enumerate(queries, 1):
        r = orch.run(q)
        print(f"\n[轮次 {i}]")
        print(f"  👤 用户: {q}")
        print(f"  💭 Think: {r['thought']}")
        print(f"  🔧 Tool: {r['tool_result'].tool_name}")
        print(f"  🤖 回复: {r['response'][:60]}{'...' if len(r['response']) > 60 else ''}")


def demo_mixed():
    """混合场景"""
    print_sep("🚗 混合场景 - Agent + MCP Tools")
    orch = Orchestrator()

    conv = [
        "开空调到24度",
        "有什么新闻",
        "我想回家",
        "播放音乐",
        "车辆状态怎么样",
    ]

    for i, q in enumerate(conv, 1):
        r = orch.run(q)
        print(f"\n[轮次 {i}] {q}")
        print(f"  路由:{r['agent_id']} | 工具:{r['tool_result'].tool_name} | 状态:{r['state']}")
        print(f"  回复: {r['response'][:70]}{'...' if len(r['response']) > 70 else ''}")


def demo_tool_schemas():
    """MCP 工具 Schema 展示"""
    print_sep("📋 MCP Tool Schemas - LLM 看到的工具定义")

    registry = ToolRegistry()
    for name, schema in MCP_TOOLS.items():
        print(f"\n🔧 {schema['name']} ({schema['category']})")
        print(f"   描述: {schema['description']}")
        params = schema['parameters']
        print(f"   参数: {list(params.keys())}")


def main():
    print("""
╔════════════════════════════════════════════════════════════════╗
║    🚗 Agent + MCP Tools 集成演示 v3                         ║
║                                                              ║
║    Agent → Tool → Result 完整链路                           ║
║    用于 LangSmith tracing 对照                               ║
╚════════════════════════════════════════════════════════════════╝
    """)

    demos = [
        ("空调控制", demo_climate),
        ("导航控制", demo_navigation),
        ("音乐控制", demo_music),
        ("混合场景", demo_mixed),
        ("MCP Schemas", demo_tool_schemas),
    ]

    for name, demo in demos:
        try:
            demo()
        except Exception as e:
            print(f"\n❌ 错误: {e}")

    print(f"\n{'='*65}\n  ✅ 完成\n{'='*65}")
    print("""
下一步:
  1. 在 LangSmith 查看完整 trace: Agent.think() → Agent.execute() → Tool.call()
  2. 对比 state 状态是否一致
  3. 验证 MCP 工具定义是否完整
    """)


if __name__ == "__main__":
    main()
