"""Orchestration Engine - 编排引擎.

提供：
- QueryQueue: 优先级队列
- AgentTeam: 钻石形态 agent team
- OrchestrationEngine: 全局调度器

用法:
    from core.orchestration import OrchestrationEngine, QueryQueue, AgentTeam

    engine = OrchestrationEngine()
    await engine.start()

    # 入队 query
    query_id = engine.enqueue("打开空调", priority=QueryPriority.HIGH)

    # 产卵新 team
    team = engine.spawn_team("research_team")

    # 停止
    await engine.stop()
"""

from .types import (
    EngineConfig,
    EventHandler,
    QueryPriority,
    QueryRequest,
    QueryStatus,
    QueryType,
    QueueStats,
    RunResult,
    TeamConfig,
)
from .queue import QueryQueue
from .team import AgentTeam
from .engine import OrchestrationEngine, get_engine, start_engine, stop_engine
from .composite import CompositeTeam

__all__ = [
    # Types
    "EngineConfig",
    "EventHandler",
    "QueryPriority",
    "QueryRequest",
    "QueryStatus",
    "QueryType",
    "QueueStats",
    "RunResult",
    "TeamConfig",
    # Core classes
    "QueryQueue",
    "AgentTeam",
    "CompositeTeam",
    "OrchestrationEngine",
    # Global engine helpers
    "get_engine",
    "start_engine",
    "stop_engine",
]
