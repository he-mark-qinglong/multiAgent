"""OrchestrationEngine - 编排引擎主循环."""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any, Callable, Optional

from .queue import QueryQueue
from .team import AgentTeam
from .types import (
    EngineConfig,
    EventHandler,
    QueryPriority,
    QueryRequest,
    QueryType,
    QueryStatus,
    TeamConfig,
    TeamConfig,
)

logger = logging.getLogger(__name__)


class OrchestrationEngine:
    """编排引擎 - 全局调度器.

    特性：
    - While 循环驱动队列处理
    - Spawn 模式可产卵多套 agent team
    - 支持 query preempt（紧急插入）
    - 并发控制（max concurrent teams）
    - 上下文压缩（20000 chars / 200 lines）
    """

    def __init__(
        self,
        config: Optional[EngineConfig] = None,
        event_handler: Optional[EventHandler] = None,
    ):
        self.config = config or EngineConfig()
        self.event_handler = event_handler

        self._queue = QueryQueue(max_size=self.config.max_queue_size)
        self._teams: dict[str, AgentTeam] = {}
        self._running_tasks: dict[str, asyncio.Task] = {}
        self._running_lock = threading.Lock()

        self._engine_task: Optional[asyncio.Task] = None
        self._stop_event = threading.Event()

    async def start(self) -> None:
        """启动编排引擎主循环."""
        if self._engine_task is not None:
            logger.warning("Engine already running")
            return

        self._stop_event.clear()
        self._engine_task = asyncio.create_task(self._run_loop())
        logger.info("OrchestrationEngine started")

    async def stop(self) -> None:
        """停止编排引擎."""
        self._stop_event.set()

        if self._engine_task is not None:
            self._engine_task.cancel()
            try:
                await self._engine_task
            except asyncio.CancelledError:
                pass
            self._engine_task = None

        # 取消所有运行中的任务
        with self._running_lock:
            for task in self._running_tasks.values():
                task.cancel()
            self._running_tasks.clear()

        logger.info("OrchestrationEngine stopped")

    async def _run_loop(self) -> None:
        """主循环."""
        while not self._stop_event.is_set():
            try:
                await self._process_queue()
                await asyncio.sleep(self.config.loop_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Engine loop error: {e}")
                await asyncio.sleep(1)

    async def _process_queue(self) -> None:
        """处理队列."""
        # 检查并发限制
        with self._running_lock:
            running_count = len(self._running_tasks)

        if running_count >= self.config.max_concurrent_teams:
            return  # 达到上限，等待

        # 出队
        query = self._queue.dequeue()
        if query is None:
            return  # 队列空

        # 获取或创建 team
        team_id = query.team_id or self.config.default_team_id
        team = self._get_or_spawn_team(team_id)

        # 创建异步任务
        task = asyncio.create_task(self._run_team(team, query))
        with self._running_lock:
            self._running_tasks[query.id] = task

        # 触发事件
        self._emit("query_started", {"query_id": query.id, "team_id": team_id})

    async def _run_team(self, team: AgentTeam, query: QueryRequest) -> None:
        """运行 team.

        Args:
            team: AgentTeam 实例
            query: QueryRequest 对象
        """
        try:
            result = await team.run_async(query)

            # 更新队列中的状态
            if result.status == QueryStatus.COMPLETED:
                self._queue.complete(query.id, {
                    "final_response": result.final_response,
                    "goals": result.goals,
                    "execution_results": result.execution_results,
                })
            else:
                self._queue.fail(query.id, result.error or "Unknown error")

            self._emit("query_completed", {
                "query_id": query.id,
                "team_id": team.team_id,
                "result": {
                    "status": result.status.value,
                    "final_response": result.final_response,
                    "duration_ms": result.duration_ms,
                },
            })

        except Exception as e:
            logger.error(f"Team {team.team_id} run error: {e}")
            self._queue.fail(query.id, str(e))
            self._emit("query_failed", {"query_id": query.id, "error": str(e)})

        finally:
            with self._running_lock:
                self._running_tasks.pop(query.id, None)

    def enqueue(
        self,
        content: str,
        query_type: QueryType = QueryType.NORMAL,
        priority: QueryPriority = QueryPriority.NORMAL,
        team_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """入队新 query.

        Args:
            content: query 内容
            query_type: query 类型
            priority: 优先级
            team_id: 指定 team（可选）
            metadata: 额外元数据

        Returns:
            query_id
        """
        query_id = self._queue.enqueue(
            content=content,
            query_type=query_type,
            priority=priority,
            team_id=team_id,
            metadata=metadata,
        )

        self._emit("query_enqueued", {"query_id": query_id, "team_id": team_id})
        return query_id

    def cancel(self, query_id: str) -> bool:
        """取消 query.

        Args:
            query_id: query ID

        Returns:
            是否成功取消
        """
        with self._running_lock:
            task = self._running_tasks.get(query_id)

        if task:
            task.cancel()
            return True

        return self._queue.cancel(query_id)

    def spawn_team(self, team_id: str, config: Optional[TeamConfig] = None) -> AgentTeam:
        """产卵模式 - 创建新的 agent team.

        Args:
            team_id: team ID
            config: team 配置（可选）

        Returns:
            AgentTeam 实例
        """
        if team_id in self._teams:
            logger.warning(f"Team {team_id} already exists, returning existing")
            return self._teams[team_id]

        config = config or TeamConfig(team_id=team_id)
        team = AgentTeam(config)
        self._teams[team_id] = team

        self._emit("team_spawned", {"team_id": team_id})
        logger.info(f"Spawned new team: {team_id}")

        return team

    def get_team(self, team_id: str) -> Optional[AgentTeam]:
        """获取 team."""
        return self._teams.get(team_id)

    def get_or_create_team(self, team_id: str) -> AgentTeam:
        """获取或创建 team."""
        return self._teams.get(team_id) or self.spawn_team(team_id)

    def _get_or_spawn_team(self, team_id: str) -> AgentTeam:
        """内部方法：获取或创建 team."""
        return self.get_or_create_team(team_id)

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息."""
        queue_stats = self._queue.get_stats()
        with self._running_lock:
            running_count = len(self._running_tasks)

        return {
            "teams": list(self._teams.keys()),
            "team_count": len(self._teams),
            "running_tasks": running_count,
            "queue": {
                "pending": queue_stats.pending_count,
                "running": queue_stats.running_count,
                "completed": queue_stats.completed_count,
                "failed": queue_stats.failed_count,
                "cancelled": queue_stats.cancelled_count,
            },
        }

    def _emit(self, event_type: str, data: Any) -> None:
        """触发事件."""
        if self.event_handler:
            try:
                self.event_handler(event_type, data)
            except Exception as e:
                logger.error(f"Event handler error: {e}")


# 全局引擎实例
_engine: Optional[OrchestrationEngine] = None
_engine_lock = threading.Lock()


def get_engine() -> OrchestrationEngine:
    """获取全局引擎实例."""
    global _engine
    with _engine_lock:
        if _engine is None:
            _engine = OrchestrationEngine()
        return _engine


async def start_engine() -> OrchestrationEngine:
    """启动全局引擎并返回."""
    engine = get_engine()
    await engine.start()
    return engine


async def stop_engine() -> None:
    """停止全局引擎."""
    global _engine
    with _engine_lock:
        if _engine is not None:
            await _engine.stop()
            _engine = None
