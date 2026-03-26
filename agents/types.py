"""Input/Output types for agents with context isolation.

Context Visibility:
- PUBLIC: IntentChain, GoalTree, Plan, ExecutionResult (all agents)
- PRIVATE: LLM_Prompt, Internal_Reasoning (creator only)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Visibility(str, Enum):
    """Data visibility classification."""
    PUBLIC = "public"      # All agents can access
    PRIVATE = "private"    # Only creator can access


@dataclass
class UserQuery:
    """User query input (always PUBLIC)."""
    query_id: str
    text: str
    timestamp: int


@dataclass
class IntentResult:
    """Intent Agent PUBLIC output.

    Only contains public data. Private reasoning stored separately.
    """
    chain_id: str
    current_intent: str
    entities: dict[str, Any]
    confidence: float
    node_count: int


@dataclass
class PlannerResult:
    """Planner Agent PUBLIC output."""
    plan_id: str
    goal_count: int
    execution_order: list[str]
    estimated_cost: int


@dataclass
class ExecutionResult:
    """Executor Agent PUBLIC output."""
    goal_id: str
    status: str  # completed | failed
    result: Any
    logs: list[dict]
    duration_ms: int


@dataclass
class FinalResponse:
    """Synthesizer Agent PUBLIC output."""
    response: str
    metadata: dict[str, Any]
    goals_achieved: list[str]
    goals_failed: list[str]


@dataclass
class PrivateContext:
    """Private data - not shared with other agents."""
    visibility: Visibility = Visibility.PRIVATE
    llm_prompt: str | None = None
    reasoning: str | None = None
    raw_response: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
