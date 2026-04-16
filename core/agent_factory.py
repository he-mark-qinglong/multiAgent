"""Agent Factory - Creates LLM-powered agents for the pipeline.

Factory function to create agents with MiniMax LLM client.
Supports both:
1. Legacy agents (IntentAgent, PlannerAgent, etc.)
2. Prompt-driven agents via GenericAgentRunner
"""

from __future__ import annotations

from typing import Any, Optional

from core.minimax_client import get_minimax_client, MiniMaxClient
from agents.intent_agent import IntentAgent
from agents.planner_agent import PlannerAgent
from agents.executor_agent import ExecutorAgent
from agents.synthesizer_agent import SynthesizerAgent
from agents.base.agent_runner import GenericAgentRunner


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


def create_prompt_agent(
    prompt_file: str,
    llm_client: Optional[MiniMaxClient] = None,
    tools: Optional[list[Any]] = None,
    variables: Optional[dict[str, Any]] = None,
) -> GenericAgentRunner:
    """
    Create a prompt-driven agent from markdown file.

    Args:
        prompt_file: Path to prompt markdown file (with frontmatter)
        llm_client: Optional LLM client (uses default if not provided)
        tools: Optional list of tools available to agent
        variables: Optional variables for prompt substitution

    Returns:
        GenericAgentRunner instance
    """
    return GenericAgentRunner.from_prompt_file(
        prompt_file=prompt_file,
        llm_client=llm_client,
        variables=variables,
    )


# Singleton cache
_agents: dict[str, Any] | None = None


def get_agents() -> dict[str, Any]:
    """Get or create singleton agents instance."""
    global _agents
    if _agents is None:
        _agents = create_agents()
    return _agents


def reset_agents():
    """Reset agents cache (useful for testing)."""
    global _agents
    _agents = None
