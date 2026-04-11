"""Agent Factory - Creates LLM-powered agents for the pipeline.

Factory function to create agents with MiniMax LLM client.
"""

from __future__ import annotations

from typing import Any

from core.minimax_client import get_minimax_client
from agents.intent_agent import IntentAgent
from agents.planner_agent import PlannerAgent
from agents.executor_agent import ExecutorAgent
from agents.synthesizer_agent import SynthesizerAgent


def create_agents() -> dict[str, Any]:
    """Create all pipeline agents with MiniMax LLM client.

    Returns:
        Dict mapping agent name to agent instance.
    """
    client = get_minimax_client()

    return {
        "intent": IntentAgent(llm=client),
        "planner": PlannerAgent(llm=client),
        "executor": ExecutorAgent(executor_id="main", llm=client),
        "synthesizer": SynthesizerAgent(llm=client),
    }


# Singleton cache
_agents: dict[str, Any] | None = None


def get_agents() -> dict[str, Any]:
    """Get or create singleton agents instance."""
    global _agents
    if _agents is None:
        _agents = create_agents()
    return _agents
