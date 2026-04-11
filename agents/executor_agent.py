"""Executor Agent - L2+: Task execution using ToolRegistry."""

from __future__ import annotations

import logging
from typing import Any

from agents.langgraph_agents import BaseReActAgent
from core.models import AgentState, Goal, GoalStatus

logger = logging.getLogger(__name__)


EXECUTOR_SYSTEM_PROMPT = """你是一个Executor Agent (L2+)。你的任务是执行分配的目标。

根据目标类型调用相应的工具：
- climate_control: 调用空调控制
- navigation: 调用导航
- music_control: 调用音乐播放
- vehicle_status: 查询车辆状态
- door_control: 车门控制
- news: 获取新闻
- emergency: 紧急救援

执行后记录结果。"""


class ExecutorAgent(BaseReActAgent):
    """L2+ Agent for task execution using ToolRegistry."""

    def __init__(self, executor_id: str, llm: Any | None = None):
        super().__init__(
            agent_id=f"executor_{executor_id}",
            name=f"Executor {executor_id}",
            role="L2+",
            system_prompt=EXECUTOR_SYSTEM_PROMPT,
        )
        self.executor_id = executor_id
        self.llm = llm
        self._registry = None

    def _get_registry(self):
        """Lazy load ToolRegistry to avoid circular import."""
        if self._registry is None:
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from backend.tools import registry
            self._registry = registry
        return self._registry

    async def think(self, state: AgentState) -> str:
        """Analyze assigned goal."""
        goals = state.goals
        if not goals:
            return "No goals assigned"

        goal_ids = list(goals.keys())
        return f"Executing {len(goal_ids)} goals"

    async def act(self, state: AgentState, thought: str) -> dict[str, Any]:
        """Execute the goals using ToolRegistry."""
        goals = state.goals
        if not goals:
            return {"execution_results": {}}

        registry = self._get_registry()
        execution_results = {}

        for goal_id, goal in goals.items():
            try:
                result = self._execute_goal(goal, registry)
                goal.status = GoalStatus.COMPLETED
                execution_results[goal_id] = {
                    "status": "completed",
                    "output": result.description,
                    "state": result.state,
                }
            except Exception as e:
                goal.status = GoalStatus.FAILED
                execution_results[goal_id] = {
                    "status": "failed",
                    "output": str(e),
                    "error": str(e),
                }
                logger.error("Goal %s failed: %s", goal_id, e)

        completed = sum(1 for r in execution_results.values() if r.get("status") == "completed")
        logger.info("Executor %s: completed %d/%d goals", self.executor_id, completed, len(goals))

        return {
            "execution_results": execution_results,
            "metadata": {"_finished": True},
        }

    def _execute_goal(self, goal: Goal, registry) -> Any:
        """Execute a single goal using ToolRegistry."""
        goal_type = goal.type
        intent_info = getattr(goal, 'result', {}) or {}
        entities = intent_info.get("entities", {})

        # Map goal type to tool and action
        if goal_type == "climate_control":
            # Use control action with compound params
            params = {}
            if entities.get("temperature"):
                params["temperature"] = entities["temperature"]
            if entities.get("fan_speed"):
                params["fan_speed"] = entities["fan_speed"]
            params["power"] = True  # Turn on by default
            return registry.call_tool("climate_control", "control", **params)

        elif goal_type == "navigation":
            destination = entities.get("destination", "")
            return registry.call_tool("navigation", "navigate", destination=destination)

        elif goal_type == "music_control":
            return registry.call_tool("music_player", "play")

        elif goal_type == "vehicle_status":
            return registry.call_tool("vehicle_status", "get_status")

        elif goal_type == "door_control":
            return registry.call_tool("door_control", "lock")

        elif goal_type == "news":
            return registry.call_tool("news", "get_news")

        elif goal_type == "emergency":
            return registry.call_tool("emergency", "call", reason=entities.get("reason", ""))

        else:
            # Generic fallback
            return registry.call_tool("vehicle_status", "get_status")


def create_executor_agent(executor_id: str, llm: Any = None) -> ExecutorAgent:
    """Factory function to create ExecutorAgent."""
    return ExecutorAgent(executor_id=executor_id, llm=llm)
