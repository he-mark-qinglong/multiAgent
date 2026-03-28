#!/usr/bin/env python3
"""聊天对话框 + 推理过程展示 - 人机交互界面测试。

功能:
1. 流式显示 Agent 推理过程 (Think → Action → Result)
2. 多轮对话支持
3. 终端彩色输出
4. 可自动运行用于 CI/UI 测试

用法:
    python tests/demo_chat_ui.py          # 交互模式
    python tests/demo_chat_ui.py --auto  # 自动演示模式
"""

import sys
import os
import time
import argparse
from dataclasses import dataclass, field
from typing import Literal
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mock_tools import (
    ClimateTool, NavigationTool, MusicTool, NewsTool,
    VehicleStatusTool, DoorTool, EmergencyTool, ToolResult
)


# ============================================================================
# Terminal UI Colors (ANSI)
# ============================================================================

class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


def color(text: str, c: str) -> str:
    return f"{c}{text}{Colors.RESET}"


def print_banner():
    print(f"""
{Colors.CYAN}{'='*65}
  🚗 智能车载助手 - 推理过程展示
{'='*65}{Colors.RESET}
{Colors.DIM}  输入消息与 Agent 交互，查看完整推理链路
  输入 'quit' 或 'exit' 退出，输入 'auto' 运行自动演示
{Colors.RESET}
""")


# ============================================================================
# Message Types
# ============================================================================

@dataclass
class ChatMessage:
    role: Literal["user", "agent", "system"]
    content: str
    timestamp: float = field(default_factory=time.time)
    thinking: str = ""           # 推理过程
    tool_call: str = ""          # 工具调用
    tool_result: str = ""        # 工具结果
    state: dict = field(default_factory=dict)


@dataclass
class ReasoningStep:
    step_type: Literal["think", "action", "observation", "result"]
    content: str
    timestamp: float = field(default_factory=time.time)


# ============================================================================
# Chat UI Renderer
# ============================================================================

class ChatRenderer:
    """渲染聊天消息和推理过程。"""

    @staticmethod
    def print_message(msg: ChatMessage):
        """打印单条消息。"""
        ts = time.strftime("%H:%M:%S", time.localtime(msg.timestamp))

        if msg.role == "user":
            print(f"\n{Colors.GREEN}{'─'*65}")
            print(f"  👤 用户  [{ts}]")
            print(f"  {msg.content}")
            print(f"{Colors.RESET}")

        elif msg.role == "agent":
            print(f"{Colors.BLUE}{'─'*65}")
            print(f"  🤖 助手  [{ts}]")
            print(f"{Colors.RESET}")

            # 推理过程
            if msg.thinking:
                print(f"{Colors.DIM}  💭 推理:{Colors.RESET}")
                for line in msg.thinking.split('\n'):
                    print(f"  {Colors.DIM}     {line}{Colors.RESET}")

            # 工具调用
            if msg.tool_call:
                print(f"{Colors.YELLOW}  🔧 工具:{Colors.RESET}")
                print(f"  {Colors.YELLOW}     {msg.tool_call}{Colors.RESET}")

            # 工具结果
            if msg.tool_result:
                print(f"{Colors.CYAN}  📊 结果:{Colors.RESET}")
                for line in msg.tool_result.split('\n'):
                    print(f"  {Colors.CYAN}     {line}{Colors.RESET}")

            # 最终回复
            print(f"{Colors.BOLD}  {msg.content}{Colors.RESET}")
            print(f"{Colors.BLUE}{'─'*65}{Colors.RESET}\n")

        elif msg.role == "system":
            print(f"{Colors.DIM}  [系统] {msg.content}{Colors.RESET}\n")

    @staticmethod
    def print_reasoning_steps(steps: list[ReasoningStep]):
        """流式打印推理步骤。"""
        print(f"\n{Colors.CYAN}{'─'*65}")
        print(f"  🔄 推理过程{Colors.RESET}")

        for step in steps:
            icon = {
                "think": "💭",
                "action": "🔧",
                "observation": "👁️",
                "result": "✅",
            }.get(step.step_type, "•")

            label = {
                "think": "思考",
                "action": "执行",
                "observation": "观察",
                "result": "结果",
            }.get(step.step_type, step.step_type)

            print(f"  {icon} [{label}] {step.content}")

        print(f"{Colors.CYAN}{'─'*65}{Colors.RESET}\n")

    @staticmethod
    def print_thinking_animation(thought: str):
        """打印思考动画。"""
        print(f"\n{Colors.DIM}  💭 {thought}{Colors.RESET}")
        print(f"{Colors.DIM}     {'.' * 40}{Colors.RESET}")

    @staticmethod
    def print_streaming_result(text: str, color: str = Colors.BOLD):
        """流式打印结果文本。"""
        print(f"  {color}{text}{Colors.RESET}", end="", flush=True)

    @staticmethod
    def clear_line():
        """清除当前行。"""
        print("\033[2K\r", end="")


# ============================================================================
# Streaming Chat Agent
# ============================================================================

class StreamingChatAgent:
    """流式聊天 Agent - 展示完整推理过程。"""

    def __init__(self):
        self.orchestrator_async = AsyncOrchestrator()
        self._history: list[ChatMessage] = []

    @property
    def history(self) -> list[ChatMessage]:
        return self._history

    def _infer_agent(self, query: str) -> str:
        """推断路由目标。"""
        q = query.lower()
        if any(w in q for w in ["门", "锁"]):
            return "door"
        if any(w in q for w in ["紧急", "救援"]):
            return "emergency"
        if any(w in q for w in ["状态", "电量"]):
            return "status"
        if any(w in q for w in ["空调", "热", "冷", "温度", "风速"]):
            return "climate"
        if any(w in q for w in ["新闻"]):
            return "news"
        if any(w in q for w in ["音乐", "播放", "这首", "不错", "好听", "暂停", "换", "下一首"]):
            return "music"
        if any(w in q for w in ["导航", "去", "机场", "堵", "多久", "回家"]):
            return "nav"
        return "chat"

    def run(self, query: str) -> ChatMessage:
        """同步运行 - 返回完整消息。"""
        msg = ChatMessage(role="user", content=query)
        self._history.append(msg)

        # 1. Think: 路由 + 意图识别
        print(f"\n{Colors.DIM}  💭 分析用户意图...{Colors.RESET}")
        time.sleep(0.3)

        # 获取 ReAct 结果
        result = self.orchestrator_async.run(query)
        thought = f"路由到 {self._infer_agent(query)}"
        agent_id = self._infer_agent(query)
        tool_result = result
        response = result.description

        # 构建 Agent 消息
        agent_msg = ChatMessage(
            role="agent",
            content=response,
            thinking=f"[路由] {agent_id} | [推理] {thought}",
            tool_call=f"{tool_result.tool_name if tool_result else 'N/A'}",
            tool_result=f"{tool_result.description if tool_result else ''}",
            state=result.state if hasattr(result, 'state') else {},
        )
        self._history.append(agent_msg)
        return agent_msg

    async def run_async(self, query: str) -> ChatMessage:
        """异步运行 - 支持流式输出。"""
        msg = ChatMessage(role="user", content=query)
        self._history.append(msg)

        # 推理步骤
        steps = [
            ReasoningStep("think", "分析用户意图..."),
        ]
        renderer = ChatRenderer()
        renderer.print_reasoning_steps(steps)

        # 获取结果
        result = self.orchestrator_async.run(query)

        # 更新推理步骤
        steps.append(ReasoningStep("action", f"调用 {result.tool_name}"))
        if result.success:
            steps.append(ReasoningStep("observation", "工具执行成功"))
        else:
            steps.append(ReasoningStep("observation", f"工具执行失败: {result.error}"))

        steps.append(ReasoningStep("result", "生成回复"))

        renderer.print_reasoning_steps(steps)

        # 构建消息
        agent_msg = ChatMessage(
            role="agent",
            content=result.description,
            thinking="\n".join(s.content for s in steps),
            tool_call=result.tool_name,
            tool_result=result.description,
            state=result.state,
        )
        self._history.append(agent_msg)
        return agent_msg


class AsyncOrchestrator:
    """异步编排器 - 支持慢速工具流式响应。"""

    def __init__(self):
        self.tools = ToolExecutor()

    def run(self, query: str) -> ToolResult:
        """执行查询（支持异步工具）。"""
        q = query.lower()
        if any(w in q for w in ["门", "锁"]):
            agent_id = "door"
        elif any(w in q for w in ["紧急", "救援"]):
            agent_id = "emergency"
        elif any(w in q for w in ["状态", "电量", "怎么样"]):
            agent_id = "status"
        elif any(w in q for w in ["空调", "热", "冷", "温度", "风速"]):
            agent_id = "climate"
        elif any(w in q for w in ["新闻"]):
            agent_id = "news"
        elif any(w in q for w in ["音乐", "播放", "这首", "不错", "好听", "暂停", "换", "下一首"]):
            agent_id = "music"
        elif any(w in q for w in ["导航", "去", "机场", "堵", "多久", "回家"]):
            agent_id = "nav"
        else:
            agent_id = "chat"
        return self.tools.execute(agent_id, query)


class ToolExecutor:
    """工具执行器。"""

    def __init__(self):
        self.climate = ClimateTool()
        self.nav = NavigationTool()
        self.music = MusicTool()
        self.news = NewsTool()
        self.status = VehicleStatusTool()
        self.door = DoorTool()
        self.emergency = EmergencyTool()

    def execute(self, agent_id: str, query: str) -> ToolResult:
        q = query.lower()

        if agent_id == "climate":
            if any(w in q for w in ["开", "开启"]):
                temp = self._extract_number(query) or 24
                return self.climate.turn_on(temp)
            elif any(w in q for w in ["关", "关闭"]):
                return self.climate.turn_off()
            elif "温度" in q or "调" in q:
                temp = self._extract_number(query)
                if temp:
                    return self.climate.set_temperature(temp)
            return self.climate.get_status()

        elif agent_id == "nav":
            if any(w in q for w in ["取消", "停止"]):
                return self.nav.cancel()
            if any(w in q for w in ["堵", "路况"]):
                return self.nav.get_traffic()
            dest = self._extract_destination(query)
            return self.nav.navigate_to(dest)

        elif agent_id == "music":
            if any(w in q for w in ["暂停"]):
                return self.music.pause()
            if any(w in q for w in ["下一首", "换", "切"]):
                return self.music.skip()
            if "音量" in q:
                vol = 80 if "大" in q else 30 if "小" in q else 50
                return self.music.set_volume(vol)
            return self.music.play()

        elif agent_id == "news":
            return self.news.get_news()

        elif agent_id == "status":
            return self.status.get_status()

        elif agent_id == "door":
            if "解" in q:
                return self.door.unlock()
            return self.door.lock()

        elif agent_id == "emergency":
            return self.emergency.call(reason=query)

        return ToolResult(success=True, state={}, description="好的，已收到您的请求")

    def _extract_number(self, text: str) -> int | None:
        import re
        m = re.search(r'\d+', text)
        return int(m.group()) if m else None

    def _extract_destination(self, text: str) -> str:
        import re
        if "回家" in text:
            return "家"
        m = re.search(r'去([^\s的]+)', text)
        return m.group(1) if m else text.strip()


# ============================================================================
# Interactive Chat Session
# ============================================================================

class ChatSession:
    """交互式聊天会话。"""

    def __init__(self, auto_mode: bool = False):
        self.agent = StreamingChatAgent()
        self.auto_mode = auto_mode
        self.renderer = ChatRenderer()

    def run(self):
        """运行会话。"""
        print_banner()

        if self.auto_mode:
            self._run_auto_demo()
        else:
            self._run_interactive()

    def _run_interactive(self):
        """交互模式。"""
        print(f"{Colors.DIM}  提示: 输入 'quit' 退出，输入 'clear' 清屏{Colors.RESET}\n")

        while True:
            try:
                query = input(f"{Colors.GREEN}👤 你: {Colors.RESET}").strip()

                if query.lower() in ["quit", "exit", "q"]:
                    print(f"\n{Colors.DIM}  再见！👋{Colors.RESET}")
                    break

                if query.lower() == "clear":
                    print("\033[2J\033[H")
                    print_banner()
                    continue

                if not query:
                    continue

                # 运行 Agent
                msg = self.agent.run(query)
                self.renderer.print_message(msg)

            except KeyboardInterrupt:
                print(f"\n\n{Colors.DIM}  已退出{Colors.RESET}")
                break
            except Exception as e:
                print(f"\n{Colors.RED}  ❌ 错误: {e}{Colors.RESET}")

    def _run_auto_demo(self):
        """自动演示模式 - 无需用户输入。"""
        print(f"{Colors.YELLOW}  🔄 自动演示模式{Colors.RESET}\n")

        demo_queries = [
            "你好",
            "开空调，24度",
            "温度调低一点",
            "有什么新闻吗",
            "我想回家",
            "播放音乐",
            "车辆状态怎么样",
            "关闭空调",
        ]

        for i, query in enumerate(demo_queries, 1):
            print(f"\n{Colors.BOLD}{'='*65}")
            print(f"  第 {i}/{len(demo_queries)} 轮对话")
            print(f"{'='*65}{Colors.RESET}")

            # 模拟用户输入
            print(f"\n{Colors.GREEN}👤 你: {Colors.RESET}{query}")

            # 思考动画
            self.renderer.print_thinking_animation("分析意图...")
            time.sleep(0.5)

            # 执行
            msg = self.agent.run(query)

            # 打印结果
            self.renderer.print_message(msg)

            # 间隔
            if i < len(demo_queries):
                time.sleep(1)

        print(f"\n{Colors.CYAN}{'='*65}")
        print(f"  ✅ 自动演示完成，共 {len(demo_queries)} 轮对话")
        print(f"{'='*65}{Colors.RESET}")

        # 打印历史摘要
        self._print_history_summary()

    def _print_history_summary(self):
        """打印对话历史摘要。"""
        print(f"\n{Colors.YELLOW}  📋 对话历史摘要{Colors.RESET}")
        print(f"{Colors.DIM}{'─'*65}{Colors.RESET}")

        for i, msg in enumerate(self.agent.history):
            role_icon = "👤" if msg.role == "user" else "🤖"
            role_name = "用户" if msg.role == "user" else "助手"
            preview = msg.content[:40] + "..." if len(msg.content) > 40 else msg.content
            print(f"  {i+1}. {role_icon} [{role_name}] {preview}")

        print(f"{Colors.DIM}{'─'*65}{Colors.RESET}\n")


# ============================================================================
# UI Test Runner (用于自动化测试)
# ============================================================================

class ChatUITestRunner:
    """聊天 UI 自动化测试运行器。"""

    def __init__(self):
        self.agent = StreamingChatAgent()
        self.test_results: list[dict] = []

    def run_test_scenario(self, name: str, queries: list[str], expected_routes: list[str]):
        """运行测试场景。"""
        print(f"\n{Colors.CYAN}{'='*65}")
        print(f"  🧪 测试: {name}")
        print(f"{'='*65}{Colors.RESET}")

        passed = 0
        failed = 0

        for i, (query, expected) in enumerate(zip(queries, expected_routes), 1):
            print(f"\n  [{i}] 查询: {query}")

            # 执行
            result = self.agent.run(query)
            msg = self.agent.history[-1]

            # 检查路由（从 tool_call 推断）
            actual = self._infer_route(msg)

            # 比较
            is_pass = actual == expected or expected == "any"
            status = f"{Colors.GREEN}✓ PASS{Colors.RESET}" if is_pass else f"{Colors.RED}✗ FAIL{Colors.RESET}"
            print(f"      期望: {expected} | 实际: {actual} | {status}")

            if is_pass:
                passed += 1
            else:
                failed += 1

            self.test_results.append({
                "name": name,
                "query": query,
                "expected": expected,
                "actual": actual,
                "passed": is_pass,
                "response": msg.content[:60],
            })

        total = len(queries)
        print(f"\n  📊 结果: {passed}/{total} 通过")
        return failed == 0

    def _infer_route(self, msg: ChatMessage) -> str:
        """从消息推断路由目标。"""
        tool = msg.tool_call.lower() if msg.tool_call else ""

        if "climate" in tool:
            return "climate"
        if "nav" in tool:
            return "nav"
        if "music" in tool:
            return "music"
        if "news" in tool:
            return "news"
        if "status" in tool or "vehicle" in tool:
            return "status"
        if "door" in tool:
            return "door"
        if "emergency" in tool:
            return "emergency"
        return "chat"

    def print_test_report(self):
        """打印测试报告。"""
        print(f"\n{Colors.BOLD}{'='*65}")
        print(f"  📊 UI 测试报告")
        print(f"{'='*65}{Colors.RESET}")

        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r["passed"])
        failed = total - passed

        print(f"\n  总计: {total} | {Colors.GREEN}通过: {passed}{Colors.RESET} | {Colors.RED}失败: {failed}{Colors.RESET}\n")

        if failed > 0:
            print(f"  {Colors.RED}失败用例:{Colors.RESET}")
            for r in self.test_results:
                if not r["passed"]:
                    print(f"    - {r['query']}: 期望 {r['expected']}, 得到 {r['actual']}")

        print(f"\n{Colors.BOLD}{'='*65}{Colors.RESET}")

        return failed == 0


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="智能车载助手 - 聊天 UI")
    parser.add_argument("--auto", action="store_true", help="自动演示模式")
    parser.add_argument("--test", action="store_true", help="运行 UI 测试")
    args = parser.parse_args()

    if args.test:
        # 运行自动化测试
        runner = ChatUITestRunner()

        # 测试场景 1: 空调控制
        runner.run_test_scenario(
            "空调控制",
            ["开空调", "温度调低到20度", "关闭空调"],
            ["climate", "climate", "climate"],
        )

        # 测试场景 2: 导航
        runner.run_test_scenario(
            "导航控制",
            ["我想回家", "路上堵吗", "取消导航"],
            ["nav", "nav", "nav"],
        )

        # 测试场景 3: 音乐
        runner.run_test_scenario(
            "音乐控制",
            ["播放音乐", "换下一首", "暂停"],
            ["music", "music", "music"],
        )

        # 测试场景 4: 混合
        runner.run_test_scenario(
            "混合查询",
            ["你好", "有什么新闻", "车辆状态怎么样"],
            ["any", "news", "status"],
        )

        # 打印报告
        success = runner.print_test_report()
        sys.exit(0 if success else 1)

    else:
        # 交互模式
        session = ChatSession(auto_mode=args.auto)
        session.run()


if __name__ == "__main__":
    main()
