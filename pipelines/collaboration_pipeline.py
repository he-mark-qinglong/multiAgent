"""Collaboration Pipeline - Orchestrates the full agent pipeline."""

from __future__ import annotations

import concurrent.futures
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from core.event_bus import EventBus
from core.models import Goal, GoalStatus
from core.state_store import StateStore

from agents import (
    IntentAgent,
    PlannerAgent,
    ExecutorAgent,
    SynthesizerAgent,
    ExecutionResult,
    FinalResponse,
)

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """Configuration for the collaboration pipeline."""

    max_parallel_executors: int = 3
    executor_pool_size: int = 5
    timeout_seconds: float = 30.0
    retry_on_failure: bool = True
    max_retries: int = 2


@dataclass
class PipelineStats:
    """Statistics from pipeline execution."""

    total_goals: int = 0
    goals_completed: int = 0
    goals_failed: int = 0
    total_duration_ms: int = 0
    errors: list[str] = field(default_factory=list)


class CollaborationPipeline:
    """Orchestrates the full Intent → Plan → Execute → Synthesize pipeline."""

    def __init__(
        self,
        state_store: StateStore | None = None,
        event_bus: EventBus | None = None,
        config: PipelineConfig | None = None,
    ):
        self.state_store = state_store or StateStore()
        self.event_bus = event_bus or EventBus()
        self.config = config or PipelineConfig()

        # Initialize agents
        self.intent_agent = IntentAgent(self.state_store, self.event_bus)
        self.planner_agent = PlannerAgent(self.state_store, self.event_bus)
        self.synthesizer = SynthesizerAgent(self.state_store, self.event_bus)

        # Executor pool - created lazily
        self._executor_pool: list[ExecutorAgent] = []
        self._executor_pool_size = config.executor_pool_size if config else 5

        logger.info("Pipeline initialized with config: max_parallel=%d, pool_size=%d",
                    self.config.max_parallel_executors, self._executor_pool_size)

    def run(self, query: str) -> tuple[FinalResponse, PipelineStats]:
        """Execute the full pipeline.

        Args:
            query: User query string.

        Returns:
            Tuple of (FinalResponse, PipelineStats).
        """
        start_time = time.time()
        stats = PipelineStats()

        try:
            # Phase 1: Intent Recognition
            logger.info("Phase 1: Intent Recognition")
            intent_chain = self.intent_agent.run(query)

            # Phase 2: Planning
            logger.info("Phase 2: Planning")
            goal_tree, plan = self.planner_agent.run(intent_chain)
            stats.total_goals = len(goal_tree.goals)

            # Phase 3: Parallel Execution
            logger.info("Phase 3: Parallel Execution")
            results = self._execute_parallel(list(goal_tree.goals.values()))

            # Count results
            stats.goals_completed = sum(1 for r in results if r.status == "completed")
            stats.goals_failed = sum(1 for r in results if r.status == "failed")

            # Phase 4: Synthesis
            logger.info("Phase 4: Synthesis")
            final_response = self.synthesizer.run(results)

        except Exception as e:
            logger.error("Pipeline error: %s", e)
            stats.errors.append(str(e))
            final_response = FinalResponse(
                response=f"Error: {str(e)}",
                metadata={"error": True},
                goals_achieved=[],
                goals_failed=[],
            )

        stats.total_duration_ms = int((time.time() - start_time) * 1000)
        logger.info("Pipeline completed in %dms: %d/%d goals",
                    stats.total_duration_ms, stats.goals_completed, stats.total_goals)

        return final_response, stats

    def _get_executor_pool(self) -> list[ExecutorAgent]:
        """Get or create executor pool."""
        if not self._executor_pool:
            self._executor_pool = [
                ExecutorAgent(i, self.state_store, self.event_bus)
                for i in range(self._executor_pool_size)
            ]
        return self._executor_pool

    def _execute_parallel(self, goals: list[Goal]) -> list[ExecutionResult]:
        """Execute goals in parallel with concurrency limit."""
        executors = self._get_executor_pool()
        assignments = list(zip(goals, executors[:len(goals)]))

        results: list[ExecutionResult] = []

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.config.max_parallel_executors
        ) as executor:
            futures = {
                executor.submit(exec.run, goal): (goal, exec)
                for goal, exec in assignments
            }

            for future in concurrent.futures.as_completed(futures):
                goal, exec = futures[future]
                try:
                    result = future.result(timeout=self.config.timeout_seconds)
                    results.append(result)
                except Exception as e:
                    logger.error("Executor error for goal %s: %s", goal.id, e)
                    results.append(ExecutionResult(
                        goal_id=goal.id,
                        status="failed",
                        result=str(e),
                        logs=[],
                        duration_ms=0,
                    ))

        return results
