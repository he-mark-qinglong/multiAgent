#!/usr/bin/env python3
"""异步新闻获取 + UX 优化演示。

问题: 新闻 API 慢 (5秒) + 偶尔失败 (20%)
解决方案对比:
1. 同步阻塞 - 用户等待 5 秒
2. 快速回复 + 后台加载 - 用户立即得到响应
3. 流式进度 - 显示加载中状态
"""

import sys
import os
import asyncio
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mock_tools import NewsTool, ToolResult


def print_sep(title):
    print(f"\n{'='*65}\n  {title}\n{'='*65}")


# ============================================================================
# 方案1: 同步阻塞 (Bad UX)
# ============================================================================

def sync_news_blocking():
    """同步阻塞 - Bad UX。"""
    print_sep("❌ 方案1: 同步阻塞 (Bad UX)")

    tool = NewsTool()
    print(f"\n⏱️  开始: {time.strftime('%H:%M:%S')}")
    print("🔄  正在获取新闻...")

    start = time.time()
    result = tool.get_news(simulate_delay=True)
    elapsed = time.time() - start

    print(f"⏱️  完成: {time.strftime('%H:%M:%S')} (耗时 {elapsed:.1f}秒)")
    print(f"✅ 结果: {result.description[:50]}...")


# ============================================================================
# 方案2: 快速回复 + 后台加载 (Good UX)
# ============================================================================

async def async_news_with_progress():
    """异步 + 进度通知 - Good UX。"""
    print_sep("✅ 方案2: 快速回复 + 后台加载 (Good UX)")

    tool = NewsTool()
    print(f"\n⏱️  开始: {time.strftime('%H:%M:%S')}")

    # Step 1: 立即回复用户
    print("📨  立即回复: 正在为您获取新闻，请稍候...")
    print("🔄  后台加载中...")

    # Step 2: 后台异步获取
    start = time.time()
    result = await tool.get_news_async()

    # Step 3: 结果返回
    elapsed = time.time() - start
    if result.success:
        print(f"⏱️  获取完成 ({elapsed:.1f}秒):")
        for line in result.description.split('\n'):
            print(f"   {line}")
    else:
        print(f"⏱️  获取失败 ({elapsed:.1f}秒):")
        print(f"   ❌ {result.description}")


# ============================================================================
# 方案3: 流式进度 (Best UX)
# ============================================================================

async def async_news_with_stream():
    """异步 + 流式进度 - Best UX。"""
    print_sep("🚀 方案3: 流式进度 (Best UX)")

    tool = NewsTool()
    print(f"\n⏱️  开始: {time.strftime('%H:%M:%S')}")
    print("📨  立即回复: 正在获取新闻...")

    # 模拟流式返回
    async def stream_progress():
        messages = [
            "🔍 正在连接新闻服务器...",
            "📡 正在获取天气资讯...",
            "📡 正在获取交通信息...",
            "📡 正在获取财经新闻...",
            "📡 正在获取科技资讯...",
        ]
        for msg in messages:
            print(f"   {msg}")
            await asyncio.sleep(1)

    # 并行执行: 流式输出 + 后台获取
    print("   📰 正在加载新闻...")

    # 启动后台任务
    news_task = asyncio.create_task(tool.get_news_async())
    progress_task = asyncio.create_task(stream_progress())

    # 等待完成
    result = await news_task
    await progress_task

    # 输出结果
    print()
    if result.success:
        print("📰 新闻获取成功:")
        for line in result.description.split('\n'):
            print(f"   {line}")
    else:
        print(f"❌ {result.description}")


# ============================================================================
# 方案4: 乐观更新 + 失败回退
# ============================================================================

async def optimistic_update():
    """乐观更新 - 先显示缓存/默认内容，失败不影响主流程。"""
    print_sep("💡 方案4: 乐观更新 (Optimistic UI)")

    tool = NewsTool()

    # Step 1: 立即返回缓存/默认内容
    cached_news = [
        "📰 天气: 晴 (缓存)",
        "🚗 交通: 正常 (缓存)",
        "📈 股市: 暂无更新 (缓存)",
    ]
    print("📨  立即回复 (使用缓存):")
    for item in cached_news:
        print(f"   {item}")

    # Step 2: 后台更新
    print("\n🔄  后台更新中...")
    result = await tool.get_news_async()

    # Step 3: 静默更新或提示
    if result.success:
        print("📝  [后台] 新闻已更新至最新")
    else:
        print(f"📝  [后台] 更新失败，保持缓存内容")


# ============================================================================
# 方案5: 超时处理
# ============================================================================

async def timeout_handling():
    """超时处理 - 超过 3 秒则放弃。"""
    print_sep("⏱️ 方案5: 超时处理 (3秒超时)")

    tool = NewsTool()
    print(f"\n⏱️  开始: {time.strftime('%H:%M:%S')}")
    print("🔄  获取新闻 (3秒超时)...")

    try:
        # 3 秒超时
        result = await asyncio.wait_for(
            tool.get_news_async(),
            timeout=3.0
        )
        print(f"✅ 获取成功")
        print(result.description[:80])
    except asyncio.TimeoutError:
        print(f"⏱️  超时! (等待超过3秒)")
        print("📨  返回缓存内容或提示稍后重试")


# ============================================================================
# 主函数
# ============================================================================

async def main():
    print("""
╔════════════════════════════════════════════════════════════════╗
║    异步新闻获取 + UX 优化方案演示                              ║
║                                                              ║
║    问题: API 慢 (5秒) + 20% 失败率                           ║
║    解决: 异步 + 流式 + 乐观更新 + 超时                       ║
╚════════════════════════════════════════════════════════════════╝
    """)

    print("""
┌─────────────────────────────────────────────────────────────┐
│  UX 优化策略                                               │
├─────────────────────────────────────────────────────────────┤
│  1. 同步阻塞: 用户等待 5 秒 ❌                              │
│  2. 快速回复: 立即响应 + 后台加载 ✅                       │
│  3. 流式进度: 实时显示加载状态 🚀                          │
│  4. 乐观更新: 先用缓存，后台更新 ✅                         │
│  5. 超时处理: 超过阈值则放弃 ✅                            │
└─────────────────────────────────────────────────────────────┘
    """)

    demos = [
        ("同步阻塞 (Bad)", sync_news_blocking),
        ("异步+快速回复", async_news_with_progress),
        ("流式进度", async_news_with_stream),
        ("乐观更新", optimistic_update),
        ("超时处理", timeout_handling),
    ]

    for name, demo in demos:
        try:
            if asyncio.iscoroutinefunction(demo):
                await demo()
            else:
                demo()
        except Exception as e:
            print(f"\n❌ 错误: {e}")

    print(f"\n{'='*65}\n  ✅ 完成\n{'='*65}")


if __name__ == "__main__":
    asyncio.run(main())
