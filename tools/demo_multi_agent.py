#!/usr/bin/env python3
"""多Agent并行任务演示脚本。

用法:
    python tools/demo_multi_agent.py              # 运行演示
    python tools/demo_multi_agent.py --interactive  # 交互模式
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipelines.collaboration_pipeline import CollaborationPipeline


def print_header(title: str) -> None:
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60 + "\n")


def run_demo():
    """运行多Agent并行任务演示"""
    print_header("多Agent并行任务演示")

    pipeline = CollaborationPipeline(enable_tracing=False)

    queries = [
        ("单任务 - 打开空调", "打开空调"),
        ("单任务 - 导航回家", "导航回家"),
        ("双任务 - 播放音乐并打开空调", "播放音乐并打开空调"),
        ("双任务 - 我想回家然后听音乐", "我想回家然后听音乐"),
        ("三任务 - 打开空调、导航去机场、播放音乐", "打开空调、导航去机场、播放音乐"),
        ("四任务 - 查询车辆状态、新闻、空调和音乐", "查询车辆状态和新闻并打开空调播放音乐"),
    ]

    for title, query in queries:
        print(f"[{title}]")
        print(f"用户: {query}")

        result = pipeline.invoke(query, thread_id="demo")
        goals = result.get("goals", {})

        print(f"分解: {len(goals)}个任务")
        for g in goals.values():
            print(f"  - [{g.type}] {g.description}")
        print(f"响应: {result.get('final_response', 'N/A')}")
        print()


async def interactive():
    """交互模式"""
    print_header("多Agent交互模式")
    print("输入 'quit' 退出\n")

    pipeline = CollaborationPipeline(enable_tracing=False)
    session_id = "interactive"

    while True:
        try:
            query = input("👤 你: ").strip()
        except EOFError:
            break

        if not query:
            continue
        if query.lower() in ["quit", "exit", "q"]:
            print("👋 再见!")
            break

        print()
        result = pipeline.invoke(query, thread_id=session_id)
        goals = result.get("goals", {})

        print(f"🔧 分解: {len(goals)}个任务")
        for g in goals.values():
            print(f"   - [{g.type}] {g.description}")
        print(f"✅ 响应: {result.get('final_response', 'N/A')}")
        print()


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        asyncio.run(interactive())
    else:
        run_demo()


if __name__ == "__main__":
    main()
