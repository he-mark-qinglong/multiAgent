"""Synthesizer Agent - L1: Result synthesis using ReAct."""

from __future__ import annotations

import logging
from typing import Any

from agents.langgraph_agents import BaseReActAgent
from core.models import AgentState, FinalResponse

logger = logging.getLogger(__name__)


SYNTHESIZER_SYSTEM_PROMPT = """You are a Synthesizer Agent (L1).
Your task is to synthesize results from all executors:
1. Aggregate execution results
2. Map goals to results
3. Generate final response

Create a clear, comprehensive response for the user."""


class SynthesizerAgent(BaseReActAgent):
    """L1 Agent for result synthesis.

    Uses ReAct pattern to reason about result aggregation.
    """

    def __init__(self, llm: Any | None = None):
        super().__init__(
            agent_id="synthesizer_agent",
            name="Result Synthesizer",
            role="L1",
            system_prompt=SYNTHESIZER_SYSTEM_PROMPT,
        )
        self.llm = llm

    async def think(self, state: AgentState) -> str:
        """Analyze execution results."""
        results = state.execution_results
        goals = state.goals

        completed = sum(1 for g in goals.values() if g.status.value == "completed")
        failed = sum(1 for g in goals.values() if g.status.value == "failed")

        return f"Synthesizing {len(results)} results: {completed} completed, {failed} failed"

    async def act(self, state: AgentState, thought: str) -> dict[str, Any]:
        """Generate final response."""
        results = state.execution_results
        goals = state.goals
        intent_chain = state.intent_chain

        # Count results
        completed = sum(1 for g in goals.values() if g.status.value == "completed")
        failed = sum(1 for g in goals.values() if g.status.value == "failed")

        # Generate response
        response_parts = [f"完成了 {completed}/{len(goals)} 个任务。"]
        for goal_id, result in results.items():
            if result:
                response_parts.append(f"- {goal_id}: {result.get('result', result.get('output', 'Done'))}")

        if failed > 0:
            response_parts.append(f"\n⚠️ {failed} 个任务失败。")

        final_response = " ".join(response_parts)

        logger.info("SynthesizerAgent: %s", final_response[:100])

        return {
            "final_response": final_response,
            "metadata": {"_finished": True},
        }


def create_synthesizer_agent(llm: Any = None) -> SynthesizerAgent:
    """Factory function to create SynthesizerAgent."""
    return SynthesizerAgent(llm=llm)
