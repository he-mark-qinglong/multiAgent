"""CompositeTeam - 复合 Team，支持多层协作."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Optional

from .types import QueryRequest, RunResult, QueryStatus, TeamConfig
from .team import AgentTeam

logger = logging.getLogger(__name__)


class CompositeTeam:
    """复合 Team - 包含多个 SubTeam 的高层级 Team.

    架构：
    ┌─────────────────────────────────────┐
    │          CompositeTeam (Layer 2)      │
    │                                       │
    │  ┌─────────┐  ┌─────────┐           │
    │  │SubTeam A │  │SubTeam B│  ...      │
    │  │(Layer1) │  │(Layer1) │           │
    │  └────┬────┘  └────┬────┘           │
    │       │            │                 │
    │       └─────┬──────┘                 │
    │             ↓                        │
    │      ┌────────────┐                  │
    │      │Synthesizer│ (跨 Team 汇总)    │
    │      └────────────┘                  │
    └─────────────────────────────────────┘

    特性：
    - 多个 SubTeam 并行执行不同子任务
    - SubTeam 之间通过 EventBus 通信
    - 跨级协调
    """

    def __init__(
        self,
        team_id: str,
        sub_team_configs: list[TeamConfig],
        sub_team_keywords: Optional[dict[str, list[str]]] = None,
        result_callback: Optional[callable] = None,
        sub_team_data: Optional[list[dict]] = None,
    ):
        self.team_id = team_id
        self.sub_teams: dict[str, AgentTeam] = {}
        self.sub_team_keywords = sub_team_keywords or {}
        self.sub_team_data = sub_team_data or []  # 完整配置（含task_templates）
        self.result_callback = result_callback  # 流式回调：每个 SubTeam 完成后立即调用
        self._cancelled = False

        # 创建 SubTeam
        for config in sub_team_configs:
            self.sub_teams[config.team_id] = AgentTeam(config)

        logger.info(f"CompositeTeam {team_id} created with {len(self.sub_teams)} sub-teams")

    async def run_async(self, query: QueryRequest) -> RunResult:
        """运行复合 Team.

        流程：
        1. 分析 Query，确定需要哪些 SubTeam
        2. 并行调用各 SubTeam
        3. 汇总结果

        Args:
            query: QueryRequest 对象

        Returns:
            RunResult 运行结果
        """
        start_time = time.time()
        self._cancelled = False

        try:
            # 分析 Query，决定使用哪些 SubTeam
            sub_team_ids = self._plan_sub_teams(query.content)

            # 提取每个 SubTeam 对应的子任务
            sub_queries = self._extract_sub_tasks(query.content, sub_team_ids)

            # 并行执行 SubTeam
            coros = []  # [(coroutine, team_id)]
            sub_results: dict[str, Any] = {}
            for team_id in sub_team_ids:
                if team_id in self.sub_teams:
                    sub_team = self.sub_teams[team_id]
                    sub_content = sub_queries.get(team_id, query.content)
                    # 创建子 Query
                    sub_query = QueryRequest(
                        id=f"{query.id}_{team_id}",
                        content=sub_content,
                        team_id=team_id,
                        metadata=query.metadata,
                    )
                    coros.append((sub_team.run_async(sub_query), team_id))

            # 使用 asyncio.gather 等待所有完成（保持原有逻辑）
            if coros:
                results = await asyncio.gather(*[c[0] for c in coros])
                for result, (coro, team_id) in zip(results, coros):
                    sub_results[team_id] = result
                    if self.result_callback:
                        self.result_callback(team_id, result)

            # 汇总结果
            final_response = self._synthesize(sub_results, sub_queries)

            duration_ms = (time.time() - start_time) * 1000

            return RunResult(
                team_id=self.team_id,
                query_id=query.id,
                status=QueryStatus.COMPLETED,
                final_response=final_response,
                goals={"sub_teams": sub_team_ids},
                execution_results=sub_results,
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"CompositeTeam {self.team_id} error: {e}")

            return RunResult(
                team_id=self.team_id,
                query_id=query.id,
                status=QueryStatus.FAILED,
                error=str(e),
                duration_ms=duration_ms,
            )

    def _plan_sub_teams(self, query: str) -> list[str]:
        """分析 Query，决定使用哪些 SubTeam.

        基于配置文件中关键词的任务分解策略。

        Args:
            query: 用户 Query

        Returns:
            使用的 SubTeam ID 列表
        """
        query_lower = query.lower()

        # 根据配置文件中的关键词选择需要的 SubTeam
        needed = set()

        for team_id, keywords in self.sub_team_keywords.items():
            if any(k.lower() in query_lower for k in keywords):
                needed.add(team_id)

        # 默认使用所有 SubTeam（如果没有匹配到）
        if not needed:
            return list(self.sub_teams.keys())

        return list(needed)

    def _extract_sub_tasks(self, query: str, team_ids: list[str]) -> dict[str, str]:
        """从原始 Query 中提取每个 SubTeam 对应的子任务（配置驱动）。

        根据 sub_team_data 中的 task_templates 进行匹配，
        支持动态参数提取（如目的地）。

        Args:
            query: 原始 Query
            team_ids: 需要的 SubTeam ID 列表

        Returns:
            team_id -> 子任务内容的字典
        """
        result = {}
        query_lower = query.lower()

        # 建立 team_id -> config 的映射
        config_map = {st["team_id"]: st for st in self.sub_team_data}

        for team_id in team_ids:
            config = config_map.get(team_id, {})
            task_templates = config.get("task_templates", {})

            matched_task = None

            # 遍历 task_templates 匹配关键词
            for task_name, task_info in task_templates.items():
                # 检查关键词是否在query中
                if self._task_matches_query(task_name, query, query_lower, task_info):
                    matched_task = task_name
                    # 处理动态参数（如目的地）
                    if task_info.get("extract_dest"):
                        dest = self._extract_destination(query, query_lower)
                        if dest:
                            matched_task = task_name.replace("{dest}", dest)
                    break

            # 未匹配到则使用默认任务
            result[team_id] = matched_task or config.get("default_task", query)

        return result

    def _task_matches_query(self, task_name: str, query: str, query_lower: str, task_info: dict) -> bool:
        """检查 task 是否匹配 query"""
        # 检查task名称中的关键词是否在query中
        keywords = []
        for key in ["打开", "调节", "关闭", "播放", "暂停", "切歌", "查询", "导航"]:
            if key in task_name:
                keywords.append(key)

        # 检查主要动作词
        action = task_info.get("action", "")
        if action:
            keywords.append(action)

        return any(k in query_lower for k in keywords)

    def _extract_destination(self, query: str, query_lower: str) -> str:
        """从query中提取目的地"""
        for keyword in ["机场", "公司", "家", "去"]:
            if keyword in query:
                # 提取关键词后的内容
                parts = query.split(keyword)
                if len(parts) > 1:
                    dest = parts[-1].split("、")[0].split("，")[0].split("。")[0].strip()
                    if dest:
                        return dest
        return ""

    def _synthesize(self, sub_results: dict[str, Any], sub_tasks: dict[str, str]) -> str:
        """汇总 SubTeam 结果生成最终响应.

        Args:
            sub_results: SubTeam ID -> RunResult 的字典
            sub_tasks: SubTeam ID -> 子任务内容的字典

        Returns:
            汇总后的自然语言响应
        """
        parts = []

        for team_id, result in sub_results.items():
            task = sub_tasks.get(team_id, "未知任务")

            if isinstance(result, dict) and "error" in result:
                parts.append(f"❌ [{team_id}] {task} → 失败: {result['error']}")
            elif isinstance(result, RunResult):
                parts.append(f"✅ [{team_id}] {task} → {result.final_response}")

        if not parts:
            return "处理中..."

        return "\n".join(parts)

    def get_sub_team(self, team_id: str) -> Optional[AgentTeam]:
        """获取 SubTeam."""
        return self.sub_teams.get(team_id)

    def add_sub_team(self, config: TeamConfig) -> AgentTeam:
        """动态添加 SubTeam.

        Args:
            config: SubTeam 配置

        Returns:
            创建的 AgentTeam
        """
        if config.team_id in self.sub_teams:
            logger.warning(f"SubTeam {config.team_id} already exists")
            return self.sub_teams[config.team_id]

        team = AgentTeam(config)
        self.sub_teams[config.team_id] = team
        logger.info(f"Added sub-team {config.team_id} to {self.team_id}")
        return team

    def remove_sub_team(self, team_id: str) -> bool:
        """移除 SubTeam.

        Args:
            team_id: SubTeam ID

        Returns:
            是否成功移除
        """
        if team_id not in self.sub_teams:
            return False

        del self.sub_teams[team_id]
        logger.info(f"Removed sub-team {team_id} from {self.team_id}")
        return True

    def cancel(self) -> None:
        """取消当前执行."""
        self._cancelled = True
        for team in self.sub_teams.values():
            team.cancel()
