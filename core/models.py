"""Data models using Pydantic for LangGraph compatibility."""

from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any, Annotated

from pydantic import BaseModel, Field, field_validator


class IntentStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class GoalStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ExecutionStatusValue(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"


class EntityType(str, Enum):
    INTENT = "Intent"
    GOAL = "Goal"
    PLAN = "Plan"
    STATUS = "Status"


class IntentNode(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    intent: str
    entities: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0
    parent_id: str | None = None
    created_at: int = Field(default_factory=lambda: int(time.time()))
    status: IntentStatus = IntentStatus.ACTIVE

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        return v


class IntentChain(BaseModel):
    chain_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    nodes: list[IntentNode] = Field(default_factory=list)
    current_node_id: str | None = None
    cross_topic_refs: list[str] = Field(default_factory=list)


class Goal(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str
    description: str
    params: dict[str, Any] = Field(default_factory=dict)
    parent_id: str | None = None
    status: GoalStatus = GoalStatus.PENDING
    assigned_to: str | None = None
    result: Any | None = None
    process_log: list[dict[str, Any]] = Field(default_factory=list)
    created_at: int = Field(default_factory=lambda: int(time.time()))
    completed_at: int | None = None


class Plan(BaseModel):
    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    intent_chain_ref: str
    execution_order: list[str] = Field(default_factory=list)
    dependencies: dict[str, list[str]] = Field(default_factory=dict)
    estimated_cost: int = 0
    created_at: int = Field(default_factory=lambda: int(time.time()))


class ExecutionStatus(BaseModel):
    goal_id: str
    executor_id: str
    status: ExecutionStatusValue = ExecutionStatusValue.QUEUED
    progress: int = 0
    last_update: int = Field(default_factory=lambda: int(time.time()))


class DeltaUpdate(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: int = Field(default_factory=lambda: int(time.time()))
    entity_type: EntityType
    entity_id: str
    operation: str  # 'create' | 'update' | 'delete'
    changed_keys: list[str] = Field(default_factory=list)
    delta: dict[str, Any] = Field(default_factory=dict)
    source_agent: str


# LangGraph State types
class AgentState(BaseModel):
    """LangGraph shared state."""

    user_query: str = ""
    intent_chain: IntentChain | None = None
    plan: Plan | None = None
    goals: dict[str, Goal] = Field(default_factory=dict)
    execution_results: dict[str, Any] = Field(default_factory=dict)
    final_response: str = ""
    messages: Annotated[list[dict[str, Any]], lambda a, b: a + b] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    needs_approval: bool = False
    interrupted: bool = False


class UserQuery(BaseModel):
    query: str
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class FinalResponse(BaseModel):
    response: str
    intent_chain: IntentChain | None = None
    goals_completed: int = 0
    goals_failed: int = 0
    token_usage: dict[str, int] = Field(default_factory=dict)


class StreamChunk(BaseModel):
    type: str  # 'result' | 'progress' | 'approval_required' | 'error' | 'interrupt'
    data: dict[str, Any] | None = None
    error: str | None = None


class ExecutionResult(BaseModel):
    """Result from an executor agent."""
    agent_id: str
    status: str  # 'success' | 'partial' | 'failed' | 'stub'
    output: str
    artifacts: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
