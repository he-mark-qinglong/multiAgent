"""SSE流式输出测试 - 验证客户端实时接收事件."""
import asyncio
import sys
sys.path.insert(0, '.')

import httpx
from sse_starlette.sse import AppStatus


async def test_sse_streaming():
    """测试SSE流式输出是否实时."""
    print("=" * 60)
    print("SSE 流式输出测试")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=60.0) as client:
        # 重置 SSE AppStatus
        AppStatus.should_exit_event = asyncio.Event()

        print("\n发送请求: '打开空调'")
        print("-" * 40)

        async with client.stream(
            "GET",
            "http://localhost:8000/api/chat",
            params={"message": "打开空调"},
        ) as response:
            print(f"状态码: {response.status_code}")
            print("\n收到的事件流:")
            print("-" * 40)

            event_times = []
            async for line in response.aiter_lines():
                if line.startswith("event:"):
                    event_type = line.replace("event:", "").strip()
                    print(f"\n[{asyncio.get_event_loop().time():.2f}] 事件: {event_type}")
                elif line.startswith("data:"):
                    data = line.replace("data:", "").strip()
                    print(f"  数据: {data[:100]}...")

            print("\n" + "=" * 60)
            print("流式输出完成!")
            print("=" * 60)


async def test_sse_multiple_commands():
    """测试多个指令的SSE输出."""
    print("\n" + "=" * 60)
    print("多指令测试: '打开空调、播放音乐、查询天气'")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=120.0) as client:
        AppStatus.should_exit_event = asyncio.Event()

        async with client.stream(
            "GET",
            "http://localhost:8000/api/chat",
            params={"message": "打开空调、播放音乐、查询天气"},
        ) as response:
            event_count = 0
            async for line in response.aiter_lines():
                if line.startswith("event:"):
                    event_count += 1
                    event_type = line.replace("event:", "").strip()
                    print(f"事件 {event_count}: {event_type}")

            print(f"\n总共收到 {event_count} 个事件")


if __name__ == "__main__":
    print("启动SSE流式输出测试...")
    print("注意: 需要后端服务运行在 http://localhost:8000")
    print()

    try:
        asyncio.run(test_sse_streaming())
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"\n测试失败: {e}")
