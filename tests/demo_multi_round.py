#!/usr/bin/env python3
"""多轮对话测试脚本 v2 - 集成 Mock Tools.

展示工具调用 + 状态返回，用于对照 LangSmith tracing。

用法:
    python tests/demo_multi_round.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mock_tools import (
    ClimateTool,
    NavigationTool,
    MusicTool,
    NewsTool,
    VehicleStatusTool,
    DoorTool,
    EmergencyTool,
    ToolResult,
)


# ============================================================================
# Tool Executor - 工具执行器
# ============================================================================

class ToolExecutor:
    """工具执行器 - 根据查询执行对应工具。"""

    def __init__(self):
        self.climate = ClimateTool()
        self.nav = NavigationTool()
        self.music = MusicTool()
        self.news = NewsTool()
        self.status = VehicleStatusTool()
        self.door = DoorTool()
        self.emergency = EmergencyTool()

    def execute(self, agent_id: str, query: str) -> ToolResult:
        """执行工具并返回结果。"""
        query_lower = query.lower()

        if agent_id == "climate":
            # 空调控制
            if any(w in query_lower for w in ["开", "开启", "启动"]):
                # 提取温度
                temp = self._extract_number(query)
                return self.climate.turn_on(temp)

            elif any(w in query_lower for w in ["关", "关闭", "关掉", "停"]):
                return self.climate.turn_off()

            elif "温度" in query_lower or "调" in query_lower:
                temp = self._extract_number(query)
                if temp:
                    return self.climate.set_temperature(temp)
                return self.climate.get_status()

            else:
                return self.climate.get_status()

        elif agent_id == "nav":
            # 导航控制
            if any(w in query_lower for w in ["去", "到", "导航", "回家", "机场", "站"]):
                dest = self._extract_destination(query)
                return self.nav.navigate_to(dest)

            elif any(w in query_lower for w in ["堵", "路况", "交通"]):
                return self.nav.get_traffic()

            elif any(w in query_lower for w in ["取消", "停止", "算了"]):
                return self.nav.cancel()

            else:
                return self.nav.get_traffic() if self.nav.state["active"] else ToolResult(
                    success=False,
                    state={},
                    description="❌ 当前没有进行中的导航"
                )

        elif agent_id == "music":
            # 音乐控制
            if any(w in query_lower for w in ["播放", "放", "听"]):
                return self.music.play()

            elif any(w in query_lower for w in ["暂停", "停"]):
                return self.music.pause()

            elif any(w in query_lower for w in ["下一首", "换一首", "切"]):
                return self.music.skip()

            elif any(w in query_lower for w in ["这首", "不错", "好听", "继续"]):
                return self.music.play()

            elif any(w in query_lower for w in ["音量", "大声", "小声"]):
                vol = self._extract_volume(query)
                return self.music.set_volume(vol)

            else:
                return self.music.play()

        elif agent_id == "news":
            return self.news.get_news()

        elif agent_id == "status":
            return self.status.get_status()

        elif agent_id == "door":
            if "解" in query_lower or "开" in query_lower:
                return self.door.unlock()
            elif "锁" in query_lower:
                return self.door.lock()
            else:
                return self.door.get_status()

        elif agent_id == "emergency":
            return self.emergency.call_emergency(query)

        else:
            return ToolResult(
                success=True,
                state={},
                description="好的，已收到您的请求"
            )

    def _extract_number(self, text: str) -> int | None:
        """从文本中提取数字。"""
        import re
        match = re.search(r'\d+', text)
        return int(match.group()) if match else None

    def _extract_volume(self, text: str) -> int:
        """提取音量设置。"""
        vol = self._extract_number(text)
        if vol is None:
            if "大声" in text:
                return 80
            elif "小声" in text:
                return 30
            return 50
        return min(100, max(0, vol))

    def _extract_destination(self, text: str) -> str:
        """提取目的地。"""
        # 简单提取
        if "回家" in text:
            return "家"
        if "机场" in text:
            return "机场"
        if "北京站" in text:
            return "北京站"
        if "超市" in text:
            return "超市"

        # 提取"去"后面的内容
        import re
        match = re.search(r'去([^\s的]+)', text)
        if match:
            return match.group(1)

        return text.strip()


# ============================================================================
# Orchestrator with Tools
# ============================================================================

class CarServiceOrchestrator:
    """车载服务编排器 - 集成工具执行。"""

    def __init__(self):
        self.router = _SimpleRouter()
        self.tools = ToolExecutor()

    def run(self, query: str) -> dict:
        """执行单轮对话。"""
        agent_id = self.router.route(query)
        result = self.tools.execute(agent_id, query)

        return {
            "agent_id": agent_id,
            "success": result.success,
            "response": result.description,
            "state": result.state,
        }


class _SimpleRouter:
    """简单路由。"""

    def __init__(self):
        self._last_agent = None

    def route(self, query: str) -> str:
        """路由到合适的 Agent。"""
        query_lower = query.lower()

        # 优先级1: 明确指令
        if any(w in query_lower for w in ["门", "锁", "解锁"]):
            return "door"
        elif any(w in query_lower for w in ["紧急", "救援", "help"]):
            return "emergency"
        elif any(w in query_lower for w in ["状态", "电量", "检查", "怎么样"]):
            return "status"
        elif any(w in query_lower for w in ["空调", "热", "冷", "温度"]):
            return "climate"
        elif any(w in query_lower for w in ["新闻", "路况"]):
            return "news"
        elif any(w in query_lower for w in ["音乐", "播放", "这首", "不错", "好听", "暂停", "换", "下一首"]):
            return "music"
        elif any(w in query_lower for w in ["导航", "路线", "去", "机场", "堵", "多久"]):
            return "nav"

        # 优先级2: 上下文感知
        if self._last_agent:
            followups = {
                "climate": ["调", "关", "开", "高", "低", "太", "冷", "热"],
                "music": ["这首", "暂停", "继续", "换", "好听", "不错", "音量"],
                "nav": ["堵", "改", "算", "取消", "导航", "多久", "预计"],
            }
            if self._last_agent in followups:
                if any(w in query_lower for w in followups[self._last_agent]):
                    return self._last_agent

            if self._last_agent == "chat":
                return "chat"

        return "chat"


# ============================================================================
# 演示函数
# ============================================================================

def print_separator(title: str):
    print("\n" + "=" * 65)
    print(f"  {title}")
    print("=" * 65)


def demo_climate():
    """演示: 空调控制 - 展示状态变化"""
    print_separator("🌡️ 演示1: 空调多轮控制")

    orch = CarServiceOrchestrator()
    queries = [
        "开空调",
        "调低温度到20度",
        "风速调大一点",
        "太冷了，调高到26度",
        "关闭空调",
    ]

    for i, q in enumerate(queries, 1):
        r = orch.run(q)
        print(f"\n[轮次 {i}]")
        print(f"  👤 用户: {q}")
        print(f"  🔧 工具: {r['agent_id']}")
        print(f"  📊 状态: {r['state']}")
        print(f"  🤖 回复:")
        for line in r['response'].split('\n'):
            print(f"       {line}")


def demo_navigation():
    """演示: 导航控制"""
    print_separator("🧭 演示2: 导航多轮控制")

    orch = CarServiceOrchestrator()
    queries = [
        "我要去北京站",
        "路上堵车吗",
        "改去机场吧",
        "预计多久能到",
        "取消导航",
    ]

    for i, q in enumerate(queries, 1):
        r = orch.run(q)
        print(f"\n[轮次 {i}]")
        print(f"  👤 用户: {q}")
        print(f"  🔧 工具: {r['agent_id']}")
        if r['state']:
            print(f"  📊 状态: {r['state']}")
        print(f"  🤖 回复:")
        for line in r['response'].split('\n'):
            print(f"       {line}")


def demo_music():
    """演示: 音乐控制"""
    print_separator("🎵 演示3: 音乐多轮控制")

    orch = CarServiceOrchestrator()
    queries = [
        "播放点音乐",
        "这首歌不错",
        "换下一首",
        "音量调大一点",
        "暂停播放",
    ]

    for i, q in enumerate(queries, 1):
        r = orch.run(q)
        print(f"\n[轮次 {i}]")
        print(f"  👤 用户: {q}")
        print(f"  🔧 工具: {r['agent_id']}")
        print(f"  📊 状态: {r['state']}")
        print(f"  🤖 回复: {r['response']}")


def demo_news():
    """演示: 新闻获取"""
    print_separator("📰 演示4: 新闻获取")

    orch = CarServiceOrchestrator()
    r = orch.run("有什么新闻")
    print(f"\n  👤 用户: 有什么新闻")
    print(f"  🤖 回复:")
    for line in r['response'].split('\n'):
        print(f"       {line}")


def demo_vehicle_status():
    """演示: 车辆状态"""
    print_separator("🚗 演示5: 车辆状态查询")

    orch = CarServiceOrchestrator()
    r = orch.run("现在车辆状态怎么样")
    print(f"\n  👤 用户: 现在车辆状态怎么样")
    print(f"  🤖 回复:")
    for line in r['response'].split('\n'):
        print(f"       {line}")


def demo_emergency():
    """演示: 紧急救援"""
    print_separator("🚨 演示6: 紧急救援")

    orch = CarServiceOrchestrator()
    queries = [
        "我需要紧急救援",
        "谢谢",
    ]

    for q in queries:
        r = orch.run(q)
        print(f"\n  👤 用户: {q}")
        print(f"  🔧 工具: {r['agent_id']}")
        if r['response']:
            print(f"  🤖 回复:")
            for line in r['response'].split('\n'):
                print(f"       {line}")


def demo_mixed():
    """演示: 混合场景"""
    print_separator("🚗 演示7: 混合场景多轮对话")

    orch = CarServiceOrchestrator()
    conversation = [
        ("你好", "chat"),
        ("帮我开空调，23度", "climate"),
        ("现在有什么新闻", "news"),
        ("我想回家", "nav"),
        ("路上堵吗", "nav"),
        ("播放点音乐", "music"),
        ("车辆状态怎么样", "status"),
    ]

    for i, (q, expected) in enumerate(conversation, 1):
        r = orch.run(q)
        print(f"\n[轮次 {i}]")
        print(f"  👤 用户: {q}")
        print(f"  🔧 工具: {r['agent_id']} ({'✓' if r['agent_id'] == expected else '~'})")
        print(f"  🤖 回复: {r['response'][:80]}{'...' if len(r['response']) > 80 else ''}")


def demo_all_tools_state():
    """演示: 所有工具当前状态"""
    print_separator("📋 演示8: 所有工具状态总览")

    tools = ToolExecutor()
    print("\n  各工具当前状态:")
    print(f"  ├─ 🌡️  空调: {tools.climate.state}")
    print(f"  ├─ 🧭  导航: {tools.nav.state}")
    print(f"  ├─ 🎵  音乐: {tools.music.state}")
    print(f"  ├─ 🚪  车门: {'已锁' if tools.door._locked else '未锁'}")
    print(f"  └─ 📊  状态查询工具: 可用")


# ============================================================================
# 主函数
# ============================================================================

def main():
    print("""
╔════════════════════════════════════════════════════════════════╗
║     🚗 多轮对话测试演示 v2 - 集成 Mock Tools                  ║
║                                                              ║
║  展示工具调用 + 状态返回                                      ║
║  可与 LangSmith tracing 进行对照验证                          ║
╚════════════════════════════════════════════════════════════════╝
    """)

    demos = [
        ("空调控制", demo_climate),
        ("导航控制", demo_navigation),
        ("音乐控制", demo_music),
        ("新闻获取", demo_news),
        ("车辆状态", demo_vehicle_status),
        ("紧急救援", demo_emergency),
        ("混合场景", demo_mixed),
        ("状态总览", demo_all_tools_state),
    ]

    # 运行所有演示
    for name, demo in demos:
        try:
            demo()
        except Exception as e:
            print(f"\n❌ 演示 '{name}' 出错: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 65)
    print("  ✅ 演示完成")
    print("=" * 65)
    print("""
下一步:
  1. 检查 LangSmith tracing 查看工具调用链路
  2. 对比 state 状态是否一致
  3. 验证 MCP/Skill 接口是否正确集成
    """)


if __name__ == "__main__":
    main()
