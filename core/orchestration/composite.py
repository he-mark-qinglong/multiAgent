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
    ):
        self.team_id = team_id
        self.sub_teams: dict[str, AgentTeam] = {}
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
            tasks = []
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
                    tasks.append(sub_team.run_async(sub_query))

            # 等待所有 SubTeam 完成
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 处理结果
            sub_results: dict[str, Any] = {}
            for i, team_id in enumerate(sub_team_ids):
                if isinstance(results[i], Exception):
                    logger.error(f"SubTeam {team_id} error: {results[i]}")
                    sub_results[team_id] = {"error": str(results[i])}
                else:
                    sub_results[team_id] = results[i]

            # 汇总结果
            final_response = self._synthesize(sub_results)

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

        基于关键词的任务分解策略。

        Args:
            query: 用户 Query

        Returns:
            使用的 SubTeam ID 列表
        """
        query_lower = query.lower()

        # 根据关键词选择需要的 SubTeam
        needed = set()

        if any(k in query_lower for k in ["空调", "温度", "冷", "热", "climate"]):
            needed.add("climate")
        if any(k in query_lower for k in ["导航", "去", "机场", "路线", "nav"]):
            needed.add("nav")
        if any(k in query_lower for k in ["音乐", "播放", "暂停", "切歌", "music"]):
            needed.add("music")

        # 默认使用所有 SubTeam（如果没有匹配到）
        if not needed:
            return list(self.sub_teams.keys())

        return list(needed)

    def _extract_sub_tasks(self, query: str, team_ids: list[str]) -> dict[str, str]:
        """从原始 Query 中提取每个 SubTeam 对应的子任务.

        Args:
            query: 原始 Query
            team_ids: 需要的 SubTeam ID 列表

        Returns:
            team_id -> 子任务内容的字典
        """
        result = {}
        query_lower = query.lower()

        for team_id in team_ids:
            if team_id == "climate":
                # 提取空调相关部分
                if "空调" in query:
                    result[team_id] = "打开空调"
                elif any(k in query_lower for k in ["温度", "冷", "热"]):
                    result[team_id] = "调节温度"
                else:
                    result[team_id] = "空调控制"

            elif team_id == "nav":
                # 提取导航相关部分
                for keyword in ["机场", "公司", "家", "去", "导航"]:
                    if keyword in query:
                        dest = query.split(keyword)[-1].split("、")[0].split("，")[0].strip()
                        if dest:
                            result[team_id] = f"导航去{dest}"
                            break
                else:
                    result[team_id] = "导航"

            elif team_id == "music":
                # 提取音乐相关部分
                if any(k in query_lower for k in ["播放", "音乐"]):
                    result[team_id] = "播放音乐"
                elif "暂停" in query:
                    result[team_id] = "暂停音乐"
                elif "切歌" in query:
                    result[team_id] = "切歌"
                else:
                    result[team_id] = "音乐控制"

            else:
                result[team_id] = query

        return result

    def _synthesize(self, sub_results: dict[str, Any]) -> str:
        """汇总 SubTeam 结果生成最终响应.

        Args:
            sub_results: SubTeam ID -> RunResult 的字典

        Returns:
            汇总后的自然语言响应
        """
        responses = []

        for team_id, result in sub_results.items():
            if isinstance(result, dict) and "error" in result:
                responses.append(f"[{team_id}] 失败: {result['error']}")
            elif isinstance(result, RunResult):
                responses.append(f"[{team_id}] {result.final_response}")

        if not responses:
            return "处理中..."

        return " | ".join(responses)

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
