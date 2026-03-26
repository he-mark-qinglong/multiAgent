"""Planner Agent - L1: Task planning using ReAct."""

from __future__ import annotations

import logging
from typing import Any

from agents.langgraph_agents import BaseReActAgent
from core.models import AgentState, Plan, Goal, GoalStatus

logger = logging.getLogger(__name__)


PLANNER_SYSTEM_PROMPT = """You are a Planner Agent (L1).
Your task is to create a task plan based on the intent chain:
1. Decompose the intent into specific goals
2. Define execution order
3. Identify dependencies between goals

Think about the best way to accomplish the user's intent."""


class PlannerAgent(BaseReActAgent):
    """L1 Agent for task planning.

    Uses ReAct pattern to reason about goal decomposition.
    """

    def __init__(self, llm: Any | None = None):
        super().__init__(
            agent_id="planner_agent",
            name="Task Planner",
            role="L1",
            system_prompt=PLANNER_SYSTEM_PROMPT,
        )
        self.llm = llm

    async def think(self, state: AgentState) -> str:
        """Analyze intent to create plan."""
        intent_chain = state.intent_chain
        if not intent_chain:
            return "No intent chain found, creating general plan"

        current_intent = intent_chain.nodes[-1].intent if intent_chain.nodes else "unknown"
        return f"Creating plan for intent: {current_intent}"

    async def act(self, state: AgentState, thought: str) -> dict[str, Any]:
        """Create goals and plan."""
        intent_chain = state.intent_chain
        if not intent_chain:
            return {"plan": None, "goals": {}}

        current_intent = intent_chain.nodes[-1].intent
        chain_id = intent_chain.chain_id

        # Create goals based on intent type
        goals = self._create_goals_for_intent(current_intent)

        plan = Plan(
            intent_chain_ref=chain_id,
            execution_order=[g.id for g in goals],
            dependencies={g.id: [] for g in goals},
        )

        goals_dict = {g.id: g for g in goals}
        logger.info("PlannerAgent: created %d goals", len(goals))

        return {
            "plan": plan,
            "goals": goals_dict,
            "metadata": {"_finished": True},
        }

    def _create_goals_for_intent(self, intent: str) -> list[Goal]:
        """Create goals based on intent type."""
        if intent == "search":
            return [
                Goal(type="search", description="Search for relevant information"),
                Goal(type="format", description="Format search results"),
            ]
        elif intent == "create":
            return [
                Goal(type="gather_info", description="Gather information for creation"),
                Goal(type="create", description="Create the requested item"),
            ]
        elif intent == "explanation":
            return [
                Goal(type="analyze", description="Analyze the topic"),
                Goal(type="explain", description="Provide explanation"),
            ]
        else:
            return [Goal(type="general", description=f"Execute task: {intent}")]


def create_planner_agent(llm: Any = None) -> PlannerAgent:
    """Factory function to create PlannerAgent."""
    return PlannerAgent(llm=llm)
