"""Executor Agent - L2+ Goal Execution."""

from __future__ import annotations

import logging
import time
from typing import Any

from core.base_agent import BaseAgent, AgentRole
from core.event_bus import EventBus
from core.models import (
    EntityType,
    Goal,
    GoalStatus,
    ProcessStep,
)
from core.state_store import StateStore

from agents.types import ExecutionResult

logger = logging.getLogger(__name__)


class ExecutorAgent(BaseAgent):
    """L2+ - Goal Execution Agent.

    Executes assigned goals and reports results.
    """

    def __init__(
        self,
        executor_id: int,
        state_store: StateStore | None = None,
        event_bus: EventBus | None = None,
    ):
        super().__init__(
            agent_id=f"executor_{executor_id}",
            name=f"Executor {executor_id}",
            role=AgentRole.EXECUTOR,
            state_store=state_store,
            event_bus=event_bus,
        )
        self.executor_id = executor_id

    def run(self, goal: Goal) -> ExecutionResult:
        """Execute an assigned goal.

        Args:
            goal: Goal to execute.

        Returns:
            ExecutionResult with goal result and logs.
        """
        start_time = time.time()
        logs: list[dict] = []

        try:
            # Update status to in_progress
            self._emit_delta(
                EntityType.GOAL,
                goal.id,
                {"status": GoalStatus.IN_PROGRESS.value, "assigned_to": self.agent_id},
            )

            # Execute goal steps (stub implementation)
            result = self._execute_goal_stub(goal, logs)

            # Final status update
            status = "completed" if result else "failed"
            self._emit_delta(
                EntityType.GOAL,
                goal.id,
                {
                    "status": status,
                    "result": result,
                    "completed_at": int(time.time()),
                },
            )

            duration_ms = int((time.time() - start_time) * 1000)
            logger.info("Goal %s %s in %dms", goal.id, status, duration_ms)

            return ExecutionResult(
                goal_id=goal.id,
                status=status,
                result=result,
                logs=logs,
                duration_ms=duration_ms,
            )

        except Exception as e:
            logger.error("Executor error for goal %s: %s", goal.id, e)
            self._emit_delta(
                EntityType.GOAL,
                goal.id,
                {"status": GoalStatus.FAILED.value, "error": str(e)},
            )
            return ExecutionResult(
                goal_id=goal.id,
                status="failed",
                result=str(e),
                logs=logs,
                duration_ms=int((time.time() - start_time) * 1000),
            )

    def _execute_goal_stub(self, goal: Goal, logs: list[dict]) -> Any:
        """Stub goal execution for Phase 2.

        In Phase 3+, this will call actual tools/services.
        """
        # Simulate execution steps
        step = ProcessStep.create(
            goal_id=goal.id,
            action=f"Executing {goal.type}",
            input_data=goal.params,
            agent_id=self.agent_id,
            output=f"Result for {goal.description}",
        )
        logs.append({"step": step.step_id, "action": step.action, "output": step.output})

        # Return a mock result based on goal type
        return {
            "goal_type": goal.type,
            "description": goal.description,
            "params": goal.params,
            "executed_by": self.agent_id,
        }
