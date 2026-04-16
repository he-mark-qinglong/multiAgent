"""飞书消息处理模拟测试.

模拟 Feishu WebSocket 消息处理链路，测试 OrchestrationEngine → CompositeTeam → SubTeams.

用法:
    python tests/test_orchestration_sim.py
    python tests/test_orchestration_sim.py --query "打开空调、播放音乐、查询天气"
"""
import asyncio
import argparse
import json
import time
from typing import Any


async def simulate_feishu_message(query: str) -> dict[str, Any]:
    """模拟飞书消息处理流程.

    1. 消息入队到 OrchestrationEngine
    2. Engine spawns CompositeTeam
    3. CompositeTeam.run_async() 并行执行 SubTeams
    4. 流式回调 result_callback
    5. 汇总结果

    Returns:
        包含执行结果的 dict
    """
    from core.orchestration import OrchestrationEngine, QueryPriority, QueryType
    from core.orchestration.types import QueryRequest

    # 收集结果
    stream_results = []
    final_result = None

    # 创建引擎
    engine = OrchestrationEngine()
    await engine.start()

    # 设置流式回调
    def on_subteam_result(team_id: str, result: Any) -> None:
        """流式回调：SubTeam 完成后立即调用."""
        if hasattr(result, 'final_response'):
            stream_results.append({
                "team": team_id,
                "response": result.final_response,
                "status": result.status.value,
            })
        else:
            stream_results.append({
                "team": team_id,
                "response": str(result),
                "status": "unknown",
            })

    # 设置事件处理器
    def on_event(event_type: str, data: dict) -> None:
        if event_type == "subteam_stream":
            print(f"  [Stream] {data.get('team_id')}: {data.get('response', '')[:50]}...")
        elif event_type == "query_completed":
            print(f"  [Event] query_completed: {data.get('query_id')}")

    engine.event_handler = on_event

    # 获取或创建 team
    team_id = "feishu"
    team = engine.get_or_create_team(team_id)

    # 设置 result_callback
    if hasattr(team, 'result_callback'):
        team.result_callback = on_subteam_result

    # 创建 QueryRequest
    query_req = QueryRequest(
        id=f"test_{int(time.time())}",
        content=query,
        team_id=team_id,
        metadata={"test": True},
    )

    print(f"\n{'='*60}")
    print(f"模拟飞书消息: {query}")
    print(f"{'='*60}")

    # 执行
    print(f"\n[1] 开始执行 CompositeTeam...")
    start = time.time()
    result = await team.run_async(query_req)
    elapsed = (time.time() - start) * 1000

    print(f"\n[2] 执行完成，耗时 {elapsed:.0f}ms")

    # 打印流式结果
    if stream_results:
        print(f"\n[3] 流式结果 ({len(stream_results)} 个 SubTeam):")
        for r in stream_results:
            status_icon = "✅" if r["status"] == "completed" else "❌"
            print(f"  {status_icon} [{r['team']}] {r['response'][:60]}...")

    # 打印最终结果
    print(f"\n[4] 最终汇总:")
    print(f"  {result.final_response[:200]}...")
    print(f"  Status: {result.status.value}")
    print(f"  Goals: {list(result.goals.keys()) if result.goals else 'none'}")
    print(f"  SubTeams: {result.goals.get('sub_teams', [])}")

    await engine.stop()

    return {
        "query": query,
        "stream_results": stream_results,
        "final_response": result.final_response,
        "status": result.status.value,
        "elapsed_ms": elapsed,
    }


async def test_single_intent():
    """测试单个意图."""
    print("\n" + "="*60)
    print("测试: 单个意图")
    print("="*60)
    return await simulate_feishu_message("打开空调")


async def test_multiple_intents():
    """测试多个意图."""
    print("\n" + "="*60)
    print("测试: 多个意图")
    print("="*60)
    return await simulate_feishu_message("打开空调、播放音乐、查询天气、导航去机场")


async def test_weather_only():
    """测试天气查询."""
    print("\n" + "="*60)
    print("测试: 天气查询")
    print("="*60)
    return await simulate_feishu_message("查询天气")


async def test_all():
    """运行所有测试."""
    results = []

    results.append(await test_single_intent())
    results.append(await test_multiple_intents())
    results.append(await test_weather_only())

    # 打印总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    for r in results:
        status_icon = "✅" if r["status"] == "completed" else "❌"
        print(f"\n{status_icon} {r['query']}")
        print(f"   流式结果: {len(r['stream_results'])} 个")
        print(f"   耗时: {r['elapsed_ms']:.0f}ms")
        print(f"   响应: {r['final_response'][:80]}...")

    return results


def main():
    parser = argparse.ArgumentParser(description="飞书消息处理模拟测试")
    parser.add_argument("--query", "-q", type=str, help="自定义查询内容")
    parser.add_argument("--all", "-a", action="store_true", help="运行所有测试")
    args = parser.parse_args()

    if args.query:
        asyncio.run(simulate_feishu_message(args.query))
    elif args.all:
        asyncio.run(test_all())
    else:
        # 默认运行多意图测试
        asyncio.run(test_multiple_intents())


if __name__ == "__main__":
    main()
