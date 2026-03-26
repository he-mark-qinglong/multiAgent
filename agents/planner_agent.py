"""Planner Agent - L1 Task Planning."""

from __future__ import annotations

import logging

from core.base_agent import BaseAgent, AgentRole
from core.event_bus import EventBus
from core.models import (
    EntityType,
    Goal,
    GoalStatus,
    GoalTree,
    Plan,
    IntentChain,
)
from core.state_store import StateStore

logger = logging.getLogger(__name__)


class PlannerAgent(BaseAgent):
    """L1 - Task Planning Agent.

    Decomposes intent chains into executable goal trees
    and creates execution plans.
    """

    AGENT_ID = "planner_agent"

    # Goal templates by intent type
    GOAL_TEMPLATES = {
        "search": [
            {"type": "query_parse", "description": "Parse search query"},
            {"type": "search", "description": "Execute search"},
            {"type": "format", "description": "Format results"},
        ],
        "calculate": [
            {"type": "parse_expression", "description": "Parse expression"},
            {"type": "compute", "description": "Compute result"},
        ],
        "create": [
            {"type": "validate", "description": "Validate input"},
            {"type": "create", "description": "Create resource"},
            {"type": "verify", "description": "Verify creation"},
        ],
        "explain": [
            {"type": "analyze", "description": "Analyze topic"},
            {"type": "synthesize", "description": "Generate explanation"},
        ],
        "general": [
            {"type": "process", "description": "Process request"},
        ],
    }

    def __init__(
        self,
        state_store: StateStore | None = None,
        event_bus: EventBus | None = None,
    ):
        super().__init__(
            agent_id=self.AGENT_ID,
            name="Task Planner",
            role=AgentRole.PLANNER,
            state_store=state_store,
            event_bus=event_bus,
        )

    def run(self, intent_chain: IntentChain) -> tuple[GoalTree, Plan]:
        """Create execution plan from intent chain.

        Args:
            intent_chain: Intent chain from IntentAgent.

        Returns:
            Tuple of (GoalTree, Plan) for execution.
        """
        # Decompose intent into goals
        current_node = intent_chain.get_node(intent_chain.current_node_id)
        goal_templates = self.GOAL_TEMPLATES.get(current_node.intent, self.GOAL_TEMPLATES["general"])

        # Create goals with parent reference
        goals = self._create_goals(goal_templates, current_node.intent)

        # Build goal tree
        root_goal = goals[0] if goals else None
        goal_map = {g.id: g for g in goals}

        goal_tree = GoalTree(
            root_goal_id=root_goal.id if root_goal else "",
            goals=goal_map,
            dependencies=self._compute_dependencies(goals),
        )

        # Create execution plan
        plan = Plan.create(
            intent_chain_ref=intent_chain.chain_id,
            execution_order=goal_tree.get_execution_order(),
            dependencies={k: list(v) for k, v in goal_tree.dependencies.items()},
        )

        # Store in StateStore
        self._store_entity(EntityType.PLAN, plan.plan_id, plan)
        for goal in goals:
            self._store_entity(EntityType.GOAL, goal.id, goal)

        # Publish plan created event
        self._emit_delta(
            EntityType.PLAN,
            plan.plan_id,
            {
                "goal_count": len(goals),
                "execution_order": list(plan.execution_order),
            },
        )

        logger.info("Plan created: %d goals, plan_id=%s", len(goals), plan.plan_id)
        return goal_tree, plan

    def _create_goals(self, templates: list[dict], parent_intent: str) -> list[Goal]:
        """Create Goal objects from templates."""
        goals = []
        for i, template in enumerate(templates):
            parent_id = goals[-1].id if goals else None
            goal = Goal.create(
                type=template["type"],
                description=template["description"],
                params={"parent_intent": parent_intent},
                parent_id=parent_id,
            )
            goals.append(goal)
        return goals

    def _compute_dependencies(self, goals: list[Goal]) -> dict[str, tuple[str, ...]]:
        """Compute dependencies between goals (sequential by default)."""
        if len(goals) <= 1:
            return {}

        dependencies = {}
        for i in range(1, len(goals)):
            dependencies[goals[i].id] = (goals[i - 1].id,)
        return dependencies
