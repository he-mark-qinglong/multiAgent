"""AgentTeam - 钻石形态的完整 Agent Team."""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from core.minimax_client import get_minimax_client
from pipelines.collaboration_pipeline import CollaborationPipeline
from .types import QueryRequest, RunResult, QueryStatus, TeamConfig

logger = logging.getLogger(__name__)


class AgentTeam:
    """一套完整的钻石形态 agent team.

    组成：
    - IntentAgent: 意图识别
    - PlannerAgent: 任务规划
    - ExecutorAgent: 工具执行
    - SynthesizerAgent: 响应汇总

    支持上下文压缩（结果压缩到 20000 字符或 200 行以内）
    """

    # 上下文压缩限制
    MAX_RESULT_CHARS = 20000
    MAX_RESULT_LINES = 200

    def __init__(self, config: TeamConfig, progress_callback: Any = None):
        self.config = config
        self.team_id = config.team_id
        self._pipeline: Optional[CollaborationPipeline] = None
        self._cancelled = False
        self._progress_callback = progress_callback

    @property
    def pipeline(self) -> CollaborationPipeline:
        """获取或创建 Pipeline（延迟初始化）."""
        if self._pipeline is None:
            self._pipeline = CollaborationPipeline(
                enable_tracing=self.config.enable_tracing,
                progress_callback=self._progress_callback,
            )
        return self._pipeline

    async def run_async(self, query: QueryRequest) -> RunResult:
        """异步运行 query.

        Args:
            query: QueryRequest 对象

        Returns:
            RunResult 运行结果
        """
        start_time = time.time()
        self._cancelled = False

        try:
            # 调用 pipeline 处理
            result = self.pipeline.invoke(query.content)

            # 压缩结果
            final_response = self._compress_result(
                result.get("final_response", "处理中...")
            )
            goals = result.get("goals", {})
            execution_results = result.get("execution_results", {})

            duration_ms = (time.time() - start_time) * 1000

            return RunResult(
                team_id=self.team_id,
                query_id=query.id,
                status=QueryStatus.COMPLETED,
                final_response=final_response,
                goals=goals,
                execution_results=execution_results,
                iterations=result.get("iterations", 0),
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"Team {self.team_id} error: {e}")

            return RunResult(
                team_id=self.team_id,
                query_id=query.id,
                status=QueryStatus.FAILED,
                error=str(e),
                duration_ms=duration_ms,
            )

    def run(self, query: QueryRequest) -> RunResult:
        """同步运行 query（供外部调用）.

        注意：内部实际是异步实现。

        Args:
            query: QueryRequest 对象

        Returns:
            RunResult 运行结果
        """
        import asyncio

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # 没有运行中的事件循环，使用新的
            return asyncio.run(self._run_async_wrapper(query))

        # 在事件循环中调度
        future = asyncio.ensure_future(self._run_async_wrapper(query))
        return asyncio.get_event_loop().run_until_complete(future)

    async def _run_async_wrapper(self, query: QueryRequest) -> RunResult:
        """异步包装器."""
        return await self.run_async(query)

    def cancel(self) -> None:
        """取消当前执行."""
        self._cancelled = True
        logger.info(f"Team {self.team_id} cancelled")

    def _compress_result(self, text: str) -> str:
        """压缩结果到限制范围内.

        限制：
        - 最多 20000 字符
        - 最多 200 行

        Args:
            text: 原始文本

        Returns:
            压缩后的文本
        """
        if not text:
            return ""

        lines = text.split("\n")

        # 先按行数压缩
        if len(lines) > self.MAX_RESULT_LINES:
            # 保留前 N/2 行和后 N/2 行
            keep = self.MAX_RESULT_LINES // 2
            text = "\n".join(lines[:keep] + ["... (压缩) ..."] + lines[-keep:])

        # 再按字符数压缩
        if len(text) > self.MAX_RESULT_CHARS:
            keep = self.MAX_RESULT_CHARS // 2
            text = text[:keep] + "\n... (压缩) ...\n" + text[-keep:]

        return text

    def reset(self) -> None:
        """重置 team 状态."""
        self._cancelled = False
        self._pipeline = None
