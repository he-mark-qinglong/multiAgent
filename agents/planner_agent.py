"""Planner Agent - L1: Task planning using ReAct."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from agents.langgraph_agents import BaseReActAgent
from core.models import AgentState, Plan, Goal, GoalStatus

logger = logging.getLogger(__name__)


PLANNER_SYSTEM_PROMPT = """你是一个Planner Agent (L1)。你的任务是根据意图链创建任务计划。

对于每个意图，创建一个或多个目标(Goal)。目标应该：
1. 有明确的类型 (climate, navigation, music, vehicle_status, etc.)
2. 有清晰的描述
3. 有执行顺序

分析意图链中的所有意图，为每个意图分配合适的目标。"""


class PlannerAgent(BaseReActAgent):
    """L1 Agent for task planning using MiniMax LLM."""

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

        num_intents = len(intent_chain.nodes)
        return f"Creating plan for {num_intents} intents"

    async def act(self, state: AgentState, thought: str) -> dict[str, Any]:
        """Create goals and plan from intent chain."""
        intent_chain = state.intent_chain
        if not intent_chain:
            return {"plan": None, "goals": {}}

        goals = self._create_goals_from_intents(intent_chain.nodes)

        plan = Plan(
            intent_chain_ref=intent_chain.chain_id,
            execution_order=[g.id for g in goals],
            dependencies={g.id: [] for g in goals},
        )

        goals_dict = {g.id: g for g in goals}
        logger.info("PlannerAgent: created %d goals", len(goals))
        for g in goals:
            logger.info("  - %s: %s", g.type, g.description)

        return {
            "plan": plan,
            "goals": goals_dict,
            "metadata": {"_finished": True},
        }

    def _create_goals_from_intents(self, intent_nodes: list) -> list[Goal]:
        """Create goals based on intent nodes.

        Each intent node becomes one or more goals.
        """
        goals = []

        # Intent type to goal type mapping
        intent_to_goal_type = {
            "climate": "climate_control",
            "navigation": "navigation",
            "music": "music_control",
            "vehicle_status": "vehicle_status",
            "door": "door_control",
            "news": "news",
            "emergency": "emergency",
            "general": "general",
        }

        for node in intent_nodes:
            intent_type = node.intent
            entities = node.entities or {}
            goal_type = intent_to_goal_type.get(intent_type, "general")

            # Create goal description
            desc = self._make_description(intent_type, entities)

            goal = Goal(
                type=goal_type,
                description=desc,
            )

            # Attach intent info to goal for executor
            goal.result = {"intent": intent_type, "entities": entities}

            goals.append(goal)

        return goals

    def _make_description(self, intent_type: str, entities: dict) -> str:
        """Create goal description from intent type and entities."""
        if intent_type == "climate":
            temp = entities.get("temperature")
            fan = entities.get("fan_speed")
            parts = ["空调控制"]
            if temp:
                parts.append(f"{temp}度")
            if fan:
                parts.append(f"风速{fan}")
            return "、".join(parts)
        elif intent_type == "navigation":
            dest = entities.get("destination", "")
            return f"导航到{dest}" if dest else "导航"
        elif intent_type == "music":
            return "播放音乐"
        elif intent_type == "vehicle_status":
            return "查询车辆状态"
        elif intent_type == "door":
            return "控制车门"
        elif intent_type == "news":
            return "获取新闻"
        elif intent_type == "emergency":
            return "紧急救援"
        return f"执行{intent_type}"


def create_planner_agent(llm: Any = None) -> PlannerAgent:
    """Factory function to create PlannerAgent."""
    return PlannerAgent(llm=llm)
