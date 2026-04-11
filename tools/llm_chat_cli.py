#!/usr/bin/env python3
"""LLM驱动的车载助手 CLI - 展示真实多轮对话效果。

直接调用 llm_reasoning() 函数，无需启动 FastAPI 服务器。

用法:
    python tools/llm_chat_cli.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import llm_reasoning


def print_event(event: dict):
    """格式化输出 SSE 事件。"""
    event_type = event.get("event", "?")
    data = event.get("data", "")

    # 解析 JSON data
    try:
        import json
        content = json.loads(data)
    except:
        content = {"content": data}

    prefix = {
        "think": "🤔",
        "action": "🔧",
        "observation": "📊",
        "result": "✅",
        "done": "🏁",
    }.get(event_type, "❓")

    if event_type == "observation":
        # 详细诊断信息
        tool = content.get("tool", "?")
        action = content.get("action", "?")
        success = content.get("success", "?")
        state = content.get("state", {})
        desc = content.get("description", "")
        error = content.get("error", "")

        print(f"  {prefix} [{event_type.upper():12}]")
        print(f"       ├─ 工具: {tool}")
        print(f"       ├─ 动作: {action}")
        print(f"       ├─ 参数: {content.get('params', {})}")
        print(f"       ├─ 状态: {state}")
        print(f"       ├─ 成功: {success}")
        if error:
            print(f"       └─ 错误: {error}")
        print(f"       └─ 结果: {desc}")

    elif event_type == "action":
        # 操作信息
        content_text = content.get("content", "")
        params = content.get("params", {})
        if params:
            print(f"  {prefix} [{event_type.upper():12}] {content_text}")
            print(f"       └─ 参数: {params}")
        else:
            print(f"  {prefix} [{event_type.upper():12}] {content_text}")

    elif event_type == "think":
        # 思考信息
        content_text = content.get("content", "")
        print(f"  {prefix} [{event_type.upper():12}] {content_text}")

    elif event_type == "done":
        print(f"  {prefix} [{event_type.upper():12}] 完成")
    else:
        # 其他事件
        text = content.get("content", str(content))
        print(f"  {prefix} [{event_type.upper():12}] {text}")


async def chat_loop():
    """交互式对话循环。"""
    print("\n" + "=" * 60)
    print("  🚗 LLM 车载助手 CLI (MiniMax API)")
    print("  输入 'quit' 或 'exit' 退出")
    print("=" * 60 + "\n")

    session_id = "cli_session"

    while True:
        try:
            user_input = input("👤 你: ").strip()
        except EOFError:
            break

        if not user_input:
            continue

        if user_input.lower() in ["quit", "exit", "q"]:
            print("👋 再见!")
            break

        print()

        async for event in llm_reasoning(user_input, session_id):
            print_event(event)

        print()


async def demo_mode():
    """演示模式 - 展示多轮对话效果。"""
    print("\n" + "=" * 60)
    print("  🚗 LLM 车载助手 CLI - 演示模式")
    print("=" * 60 + "\n")

    session_id = "demo_session"
    queries = [
        "你好",
        "开空调，24度",
        "我想回家",
        "有什么新闻",
        "播放音乐",
        "车辆状态怎么样",
    ]

    for i, query in enumerate(queries, 1):
        print(f"\n{'=' * 60}")
        print(f"  演示 {i}/{len(queries)}: {query}")
        print(f"{'=' * 60}\n")

        async for event in llm_reasoning(query, session_id):
            print_event(event)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        asyncio.run(demo_mode())
    else:
        asyncio.run(chat_loop())


if __name__ == "__main__":
    main()
