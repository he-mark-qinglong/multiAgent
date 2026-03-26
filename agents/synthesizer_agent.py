"""Synthesizer Agent - L1 Result Synthesis."""

from __future__ import annotations

import logging
from typing import Any

from core.base_agent import BaseAgent, AgentRole
from core.event_bus import EventBus
from core.models import EntityType
from core.state_store import StateStore

from agents.types import ExecutionResult, FinalResponse

logger = logging.getLogger(__name__)


class SynthesizerAgent(BaseAgent):
    """L1 - Result Synthesis Agent.

    Aggregates SubGoal results and generates final responses.
    """

    AGENT_ID = "synthesizer_agent"

    def __init__(
        self,
        state_store: StateStore | None = None,
        event_bus: EventBus | None = None,
    ):
        super().__init__(
            agent_id=self.AGENT_ID,
            name="Result Synthesizer",
            role=AgentRole.SYNTHESIZER,
            state_store=state_store,
            event_bus=event_bus,
        )

    def run(self, results: list[ExecutionResult]) -> FinalResponse:
        """Synthesize final response from execution results.

        Args:
            results: List of ExecutionResults from all Executors.

        Returns:
            FinalResponse with aggregated results.
        """
        # Separate successful and failed
        successful = [r for r in results if r.status == "completed"]
        failed = [r for r in results if r.status == "failed"]

        # Aggregate results
        aggregated = self._aggregate_results(successful)

        # Generate response (stub implementation)
        response = self._synthesize_response_stub(aggregated, failed)

        logger.info(
            "Synthesis complete: %d/%d goals achieved",
            len(successful),
            len(results),
        )

        return FinalResponse(
            response=response,
            metadata={
                "total_goals": len(results),
                "successful": len(successful),
                "failed": len(failed),
                "total_duration_ms": sum(r.duration_ms for r in results),
            },
            goals_achieved=[r.goal_id for r in successful],
            goals_failed=[r.goal_id for r in failed],
        )

    def _aggregate_results(self, results: list[ExecutionResult]) -> dict[str, Any]:
        """Aggregate successful results."""
        aggregated = {
            "results": [],
            "summary": {
                "count": len(results),
                "total_duration_ms": sum(r.duration_ms for r in results),
            },
        }

        for result in results:
            aggregated["results"].append({
                "goal_id": result.goal_id,
                "result": result.result,
                "duration_ms": result.duration_ms,
            })

        return aggregated

    def _synthesize_response_stub(
        self,
        aggregated: dict[str, Any],
        failed: list[ExecutionResult],
    ) -> str:
        """Stub response synthesis for Phase 2.

        In Phase 3+, this will use LLM to generate natural language response.
        """
        parts = []

        if aggregated["results"]:
            parts.append(f"Successfully processed {len(aggregated['results'])} task(s).")
            for r in aggregated["results"]:
                if isinstance(r["result"], dict):
                    parts.append(f"- {r['result'].get('description', 'Task')}")

        if failed:
            parts.append(f"Failed to process {len(failed)} task(s).")

        return " ".join(parts) if parts else "No results to synthesize."
