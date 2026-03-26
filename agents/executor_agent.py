"""Executor Agent - L2+: Task execution using ReAct."""

from __future__ import annotations

import logging
from typing import Any

from agents.langgraph_agents import BaseReActAgent
from core.models import AgentState, Goal, GoalStatus

logger = logging.getLogger(__name__)


EXECUTOR_SYSTEM_PROMPT = """You are an Executor Agent (L2+).
Your task is to execute assigned goals:
1. Execute the goal action
2. Report status updates
3. Return execution results

Be thorough and report your progress."""


class ExecutorAgent(BaseReActAgent):
    """L2+ Agent for task execution.

    Uses ReAct pattern to reason about goal execution.
    Supports HITL interrupts for dangerous operations.
    """

    def __init__(self, executor_id: str, llm: Any | None = None):
        super().__init__(
            agent_id=f"executor_{executor_id}",
            name=f"Executor {executor_id}",
            role="L2+",
            system_prompt=EXECUTOR_SYSTEM_PROMPT,
        )
        self.executor_id = executor_id
        self.llm = llm

    async def think(self, state: AgentState) -> str:
        """Analyze assigned goal."""
        goals = state.goals
        if not goals:
            return "No goals assigned"

        goal_ids = list(goals.keys())
        return f"Executing goals: {goal_ids}"

    async def act(self, state: AgentState, thought: str) -> dict[str, Any]:
        """Execute the goals.

        Checks for approval requirements before execution.
        """
        goals = state.goals
        if not goals:
            return {"execution_results": {}}

        # Check if approval needed (dangerous operations)
        if self._needs_approval(state):
            if state.needs_approval:
                result = self.interrupt_and_wait("需要审批才能执行", state)
                if not result.get("approved", False):
                    return {
                        "execution_results": {},
                        "metadata": {"_finished": True, "interrupted": True},
                    }

        # Execute goals (stub)
        execution_results = {}
        for goal_id, goal in goals.items():
            # Update goal status
            goal.status = GoalStatus.COMPLETED
            result = {"status": "completed", "output": f"Executed: {goal.description}"}
            execution_results[goal_id] = result

        logger.info("Executor %s: completed %d goals", self.executor_id, len(execution_results))

        return {
            "execution_results": execution_results,
            "metadata": {"_finished": True},
        }

    def _needs_approval(self, state: AgentState) -> bool:
        """Check if operation needs human approval."""
        goals = state.goals
        dangerous_types = {"delete", "execute_command", "rm", "危险操作"}

        for goal in goals.values():
            if goal.type.lower() in dangerous_types:
                return True
        return False


def create_executor_agent(executor_id: str, llm: Any = None) -> ExecutorAgent:
    """Factory function to create ExecutorAgent."""
    return ExecutorAgent(executor_id=executor_id, llm=llm)
