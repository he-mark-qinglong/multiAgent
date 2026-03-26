"""Collaboration Pipeline - Orchestrates the full agent pipeline."""

from __future__ import annotations

import concurrent.futures
import logging
import time
from dataclasses import dataclass, field

from core.event_bus import EventBus
from core.models import Goal
from core.state_store import StateStore

from agents.intent_agent import IntentAgent
from agents.planner_agent import PlannerAgent
from agents.executor_agent import ExecutorAgent
from agents.synthesizer_agent import SynthesizerAgent
from agents.types import ExecutionResult, FinalResponse

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
    """Orchestrates the full Intent → Plan → Execute → Synthesize pipeline.

    Example:
        pipeline = CollaborationPipeline()
        response, stats = pipeline.run("Search for weather in Beijing")
    """

    def __init__(
        self,
        state_store: StateStore | None = None,
        event_bus: EventBus | None = None,
        config: PipelineConfig | None = None,
    ):
        """Initialize the pipeline."""
        self.state_store = state_store or StateStore()
        self.event_bus = event_bus or EventBus()
        self.config = config or PipelineConfig()

        self.intent_agent = IntentAgent(self.state_store, self.event_bus)
        self.planner_agent = PlannerAgent(self.state_store, self.event_bus)
        self.synthesizer = SynthesizerAgent(self.state_store, self.event_bus)

        self._executor_pool: list[ExecutorAgent] = []
        self._executor_pool_size = self.config.executor_pool_size

        logger.info(
            "Pipeline: max_parallel=%d, pool_size=%d, timeout=%.1fs",
            self.config.max_parallel_executors,
            self._executor_pool_size,
            self.config.timeout_seconds,
        )

    def run(self, query: str) -> tuple[FinalResponse, PipelineStats]:
        """Execute the full collaboration pipeline."""
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
            results = self._execute_parallel(list(goal_tree.goals.values()), stats)

            stats.goals_completed = sum(1 for r in results if r.status == "completed")
            stats.goals_failed = sum(1 for r in results if r.status == "failed")

            # Phase 4: Synthesis
            logger.info("Phase 4: Synthesis")
            final_response = self.synthesizer.run(results)

        except Exception as e:
            logger.error("Pipeline error: %s", e, exc_info=True)
            stats.errors.append(str(e))
            final_response = FinalResponse(
                response=f"Pipeline error: {str(e)}",
                metadata={"error": True},
                goals_achieved=[],
                goals_failed=[],
            )

        stats.total_duration_ms = int((time.time() - start_time) * 1000)
        logger.info(
            "Pipeline: %dms, %d/%d goals",
            stats.total_duration_ms,
            stats.goals_completed,
            stats.total_goals,
        )

        return final_response, stats

    def _get_executor_pool(self) -> list[ExecutorAgent]:
        """Get or create the executor pool."""
        if not self._executor_pool:
            self._executor_pool = [
                ExecutorAgent(i, self.state_store, self.event_bus)
                for i in range(self._executor_pool_size)
            ]
        return self._executor_pool

    def _execute_parallel(
        self,
        goals: list[Goal],
        stats: PipelineStats,
    ) -> list[ExecutionResult]:
        """Execute goals in parallel with concurrency control."""
        if not goals:
            return []

        executors = self._get_executor_pool()
        assignments = list(zip(goals, executors[:len(goals)]))
        results: list[ExecutionResult] = []

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.config.max_parallel_executors
        ) as executor:
            futures = {
                executor.submit(exec.run, goal): goal
                for goal, exec in assignments
            }

            for future in concurrent.futures.as_completed(futures):
                goal = futures[future]
                try:
                    result = future.result(timeout=self.config.timeout_seconds)
                    results.append(result)
                except concurrent.futures.TimeoutError:
                    logger.warning("Goal %s timed out", goal.id)
                    stats.errors.append(f"Timeout: {goal.id}")
                    results.append(ExecutionResult(
                        goal_id=goal.id,
                        status="failed",
                        result="Execution timeout",
                        logs=[],
                        duration_ms=int(self.config.timeout_seconds * 1000),
                    ))
                except Exception as e:
                    logger.error("Goal %s failed: %s", goal.id, e)
                    stats.errors.append(f"{goal.id}: {str(e)}")
                    results.append(ExecutionResult(
                        goal_id=goal.id,
                        status="failed",
                        result=str(e),
                        logs=[],
                        duration_ms=0,
                    ))

        return results
