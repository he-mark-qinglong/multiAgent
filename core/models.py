"""Data models for the Multi-Agent Collaboration System.

All models use frozen dataclasses to ensure immutability and prevent
accidental mutations that could cause side effects in concurrent contexts.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


# ------------------------------------------------------------------------------
# Enums
# ------------------------------------------------------------------------------


class IntentStatus(str, Enum):
    """Status of an intent node in the chain."""

    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class GoalStatus(str, Enum):
    """Status of a goal in the goal tree."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ExecutionStatusValue(str, Enum):
    """Status of a goal execution by an executor."""

    QUEUED = "queued"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"


class DeltaOperation(str, Enum):
    """Type of operation in a delta update."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


class EntityType(str, Enum):
    """Type of entity being updated."""

    INTENT = "Intent"
    GOAL = "Goal"
    PLAN = "Plan"
    STATUS = "Status"


# ------------------------------------------------------------------------------
# Intent Models
# ------------------------------------------------------------------------------


@dataclass(frozen=True)
class IntentNode:
    """A single node in the intent chain representing a recognized intent.

    Attributes:
        id: Unique identifier for this intent node.
        intent: Textual description of the intent.
        entities: Extracted entities from the user query.
        confidence: Confidence score between 0 and 1.
        parent_id: ID of the parent intent node, if any.
        created_at: Unix timestamp when this node was created.
        status: Current status of this intent.
    """

    id: str
    intent: str
    entities: dict[str, Any]
    confidence: float
    parent_id: str | None
    created_at: int
    status: IntentStatus

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be between 0 and 1, got {self.confidence}")
        if not self.id:
            raise ValueError("id cannot be empty")
        if not self.intent:
            raise ValueError("intent cannot be empty")

    @staticmethod
    def create(
        intent: str,
        entities: dict[str, Any] | None = None,
        confidence: float = 1.0,
        parent_id: str | None = None,
        status: IntentStatus = IntentStatus.ACTIVE,
    ) -> IntentNode:
        """Factory method to create a new IntentNode with auto-generated ID and timestamp.

        Args:
            intent: Textual description of the intent.
            entities: Extracted entities from the user query.
            confidence: Confidence score between 0 and 1.
            parent_id: ID of the parent intent node, if any.
            status: Initial status of this intent.

        Returns:
            A new IntentNode instance.
        """
        return IntentNode(
            id=str(uuid.uuid4()),
            intent=intent,
            entities=entities or {},
            confidence=confidence,
            parent_id=parent_id,
            created_at=int(time.time()),
            status=status,
        )


@dataclass(frozen=True)
class IntentChain:
    """A chain of intent nodes tracking the conversation flow.

    Attributes:
        chain_id: Unique identifier for this intent chain.
        nodes: List of intent nodes in chronological order.
        current_node_id: ID of the currently active intent node.
        cross_topic_refs: IDs of intent nodes from other topics that are referenced.
    """

    chain_id: str
    nodes: tuple[IntentNode, ...]
    current_node_id: str
    cross_topic_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        if not self.chain_id:
            raise ValueError("chain_id cannot be empty")
        node_ids = {n.id for n in self.nodes}
        if self.current_node_id not in node_ids:
            raise ValueError(f"current_node_id '{self.current_node_id}' not in nodes")

    @staticmethod
    def create(current_node: IntentNode) -> IntentChain:
        """Factory method to create a new IntentChain with a single node.

        Args:
            current_node: The initial intent node.

        Returns:
            A new IntentChain instance.
        """
        return IntentChain(
            chain_id=str(uuid.uuid4()),
            nodes=(current_node,),
            current_node_id=current_node.id,
            cross_topic_refs=(),
        )

    def with_node(self, node: IntentNode) -> IntentChain:
        """Return a new IntentChain with an additional node.

        Args:
            node: The new intent node to append.

        Returns:
            A new IntentChain instance with the node appended.
        """
        return IntentChain(
            chain_id=self.chain_id,
            nodes=self.nodes + (node,),
            current_node_id=node.id,
            cross_topic_refs=self.cross_topic_refs,
        )

    def get_node(self, node_id: str) -> IntentNode | None:
        """Get an intent node by ID.

        Args:
            node_id: The ID of the node to retrieve.

        Returns:
            The IntentNode if found, None otherwise.
        """
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None


# ------------------------------------------------------------------------------
# Goal Models
# ------------------------------------------------------------------------------


@dataclass(frozen=True)
class ProcessStep:
    """A single step in the execution process of a goal.

    Attributes:
        step_id: Unique identifier for this step.
        goal_id: ID of the goal this step belongs to.
        action: Description of the action taken.
        input: Input data for this step.
        output: Output data from this step, if completed.
        timestamp: Unix timestamp when this step occurred.
        agent_id: ID of the agent that performed this step.
    """

    step_id: str
    goal_id: str
    action: str
    input: Any
    output: Any | None
    timestamp: int
    agent_id: str

    @staticmethod
    def create(
        goal_id: str,
        action: str,
        input_data: Any,
        agent_id: str,
        output: Any | None = None,
    ) -> ProcessStep:
        """Factory method to create a new ProcessStep.

        Args:
            goal_id: ID of the goal this step belongs to.
            action: Description of the action taken.
            input_data: Input data for this step.
            agent_id: ID of the agent that performed this step.
            output: Output data from this step, if completed.

        Returns:
            A new ProcessStep instance.
        """
        return ProcessStep(
            step_id=str(uuid.uuid4()),
            goal_id=goal_id,
            action=action,
            input=input_data,
            output=output,
            timestamp=int(time.time()),
            agent_id=agent_id,
        )


@dataclass(frozen=True)
class Goal:
    """A goal in the goal tree that needs to be accomplished.

    Attributes:
        id: Unique identifier for this goal.
        type: Type or category of the goal.
        description: Human-readable description of the goal.
        params: Parameters required to execute this goal.
        parent_id: ID of the parent goal, if any (for sub-goals).
        status: Current status of this goal.
        assigned_to: ID of the executor assigned to this goal.
        result: Result of goal execution, if completed.
        process_log: Sequence of process steps taken.
        created_at: Unix timestamp when this goal was created.
        completed_at: Unix timestamp when this goal was completed.
    """

    id: str
    type: str
    description: str
    params: dict[str, Any]
    parent_id: str | None
    status: GoalStatus
    assigned_to: str | None
    result: Any | None
    process_log: tuple[ProcessStep, ...]
    created_at: int
    completed_at: int | None

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        if not self.id:
            raise ValueError("id cannot be empty")
        if not self.type:
            raise ValueError("type cannot be empty")

    @staticmethod
    def create(
        type: str,
        description: str,
        params: dict[str, Any] | None = None,
        parent_id: str | None = None,
    ) -> Goal:
        """Factory method to create a new Goal.

        Args:
            type: Type or category of the goal.
            description: Human-readable description of the goal.
            params: Parameters required to execute this goal.
            parent_id: ID of the parent goal, if any.

        Returns:
            A new Goal instance.
        """
        return Goal(
            id=str(uuid.uuid4()),
            type=type,
            description=description,
            params=params or {},
            parent_id=parent_id,
            status=GoalStatus.PENDING,
            assigned_to=None,
            result=None,
            process_log=(),
            created_at=int(time.time()),
            completed_at=None,
        )

    def with_status(self, status: GoalStatus) -> Goal:
        """Return a new Goal with an updated status.

        Args:
            status: The new status.

        Returns:
            A new Goal instance with the updated status.
        """
        return Goal(
            id=self.id,
            type=self.type,
            description=self.description,
            params=self.params,
            parent_id=self.parent_id,
            status=status,
            assigned_to=self.assigned_to,
            result=self.result,
            process_log=self.process_log,
            created_at=self.created_at,
            completed_at=self.completed_at if status not in (GoalStatus.COMPLETED, GoalStatus.FAILED) else int(time.time()),
        )

    def with_assignment(self, executor_id: str) -> Goal:
        """Return a new Goal assigned to an executor.

        Args:
            executor_id: ID of the executor to assign.

        Returns:
            A new Goal instance assigned to the executor.
        """
        return Goal(
            id=self.id,
            type=self.type,
            description=self.description,
            params=self.params,
            parent_id=self.parent_id,
            status=GoalStatus.IN_PROGRESS if self.status == GoalStatus.PENDING else self.status,
            assigned_to=executor_id,
            result=self.result,
            process_log=self.process_log,
            created_at=self.created_at,
            completed_at=self.completed_at,
        )

    def with_result(self, result: Any) -> Goal:
        """Return a new Goal with a result.

        Args:
            result: The execution result.

        Returns:
            A new Goal instance with the result.
        """
        return Goal(
            id=self.id,
            type=self.type,
            description=self.description,
            params=self.params,
            parent_id=self.parent_id,
            status=GoalStatus.COMPLETED,
            assigned_to=self.assigned_to,
            result=result,
            process_log=self.process_log,
            created_at=self.created_at,
            completed_at=int(time.time()),
        )

    def with_step(self, step: ProcessStep) -> Goal:
        """Return a new Goal with an appended process step.

        Args:
            step: The process step to append.

        Returns:
            A new Goal instance with the step appended.
        """
        return Goal(
            id=self.id,
            type=self.type,
            description=self.description,
            params=self.params,
            parent_id=self.parent_id,
            status=self.status,
            assigned_to=self.assigned_to,
            result=self.result,
            process_log=self.process_log + (step,),
            created_at=self.created_at,
            completed_at=self.completed_at,
        )


@dataclass(frozen=True)
class GoalTree:
    """A tree of goals representing the execution plan.

    Attributes:
        root_goal_id: ID of the root goal in the tree.
        goals: Dictionary mapping goal IDs to Goal objects.
        dependencies: Mapping of goal IDs to lists of dependent goal IDs.
    """

    root_goal_id: str
    goals: dict[str, Goal]
    dependencies: dict[str, tuple[str, ...]]

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        if self.root_goal_id not in self.goals:
            raise ValueError(f"root_goal_id '{self.root_goal_id}' not in goals")

    def get_goal(self, goal_id: str) -> Goal | None:
        """Get a goal by ID.

        Args:
            goal_id: The ID of the goal to retrieve.

        Returns:
            The Goal if found, None otherwise.
        """
        return self.goals.get(goal_id)

    def get_children(self, goal_id: str) -> list[Goal]:
        """Get all direct child goals of a given goal.

        Args:
            goal_id: The ID of the parent goal.

        Returns:
            List of child goals.
        """
        return [g for g in self.goals.values() if g.parent_id == goal_id]

    def get_execution_order(self) -> list[str]:
        """Get a topologically sorted list of goal IDs for execution.

        Returns:
            List of goal IDs in execution order.

        Raises:
            ValueError: If there are circular dependencies.
        """
        in_degree: dict[str, int] = {gid: 0 for gid in self.goals}
        for deps in self.dependencies.values():
            for dep in deps:
                if dep in in_degree:
                    in_degree[dep] += 1

        queue: list[str] = [gid for gid, degree in in_degree.items() if degree == 0]
        result: list[str] = []

        while queue:
            current = queue.pop(0)
            result.append(current)
            for gid, deps in self.dependencies.items():
                if current in deps:
                    in_degree[gid] -= 1
                    if in_degree[gid] == 0:
                        queue.append(gid)

        if len(result) != len(self.goals):
            raise ValueError("Circular dependency detected in goal tree")

        return result


@dataclass(frozen=True)
class Plan:
    """A task execution plan derived from an intent chain.

    Attributes:
        plan_id: Unique identifier for this plan.
        intent_chain_ref: Reference to the originating intent chain ID.
        execution_order: List of goal IDs in execution order.
        dependencies: Mapping of goal IDs to lists of dependent goal IDs.
        estimated_cost: Estimated token consumption for execution.
        created_at: Unix timestamp when this plan was created.
    """

    plan_id: str
    intent_chain_ref: str
    execution_order: tuple[str, ...]
    dependencies: dict[str, tuple[str, ...]]
    estimated_cost: int
    created_at: int

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        if not self.plan_id:
            raise ValueError("plan_id cannot be empty")
        if not self.intent_chain_ref:
            raise ValueError("intent_chain_ref cannot be empty")

    @staticmethod
    def create(
        intent_chain_ref: str,
        execution_order: list[str],
        dependencies: dict[str, list[str]] | None = None,
        estimated_cost: int = 0,
    ) -> Plan:
        """Factory method to create a new Plan.

        Args:
            intent_chain_ref: Reference to the originating intent chain ID.
            execution_order: List of goal IDs in execution order.
            dependencies: Mapping of goal IDs to lists of dependent goal IDs.
            estimated_cost: Estimated token consumption for execution.

        Returns:
            A new Plan instance.
        """
        return Plan(
            plan_id=str(uuid.uuid4()),
            intent_chain_ref=intent_chain_ref,
            execution_order=tuple(execution_order),
            dependencies={k: tuple(v) for k, v in (dependencies or {}).items()},
            estimated_cost=estimated_cost,
            created_at=int(time.time()),
        )


# ------------------------------------------------------------------------------
# Execution Status Models
# ------------------------------------------------------------------------------


@dataclass(frozen=True)
class ExecutionStatus:
    """Status tracking for a goal execution by an executor.

    Attributes:
        goal_id: ID of the goal being executed.
        executor_id: ID of the executor running this goal.
        status: Current execution status.
        progress: Progress percentage from 0 to 100.
        last_update: Unix timestamp of the last update.
    """

    goal_id: str
    executor_id: str
    status: ExecutionStatusValue
    progress: int
    last_update: int

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        if not self.goal_id:
            raise ValueError("goal_id cannot be empty")
        if not self.executor_id:
            raise ValueError("executor_id cannot be empty")
        if not 0 <= self.progress <= 100:
            raise ValueError(f"progress must be between 0 and 100, got {self.progress}")

    @staticmethod
    def create(goal_id: str, executor_id: str) -> ExecutionStatus:
        """Factory method to create a new ExecutionStatus.

        Args:
            goal_id: ID of the goal being executed.
            executor_id: ID of the executor running this goal.

        Returns:
            A new ExecutionStatus instance.
        """
        return ExecutionStatus(
            goal_id=goal_id,
            executor_id=executor_id,
            status=ExecutionStatusValue.QUEUED,
            progress=0,
            last_update=int(time.time()),
        )

    def with_progress(self, progress: int) -> ExecutionStatus:
        """Return a new ExecutionStatus with updated progress.

        Args:
            progress: New progress percentage.

        Returns:
            A new ExecutionStatus instance.
        """
        return ExecutionStatus(
            goal_id=self.goal_id,
            executor_id=self.executor_id,
            status=self.status,
            progress=progress,
            last_update=int(time.time()),
        )

    def with_status(self, status: ExecutionStatusValue) -> ExecutionStatus:
        """Return a new ExecutionStatus with updated status.

        Args:
            status: New execution status.

        Returns:
            A new ExecutionStatus instance.
        """
        return ExecutionStatus(
            goal_id=self.goal_id,
            executor_id=self.executor_id,
            status=status,
            progress=self.progress,
            last_update=int(time.time()),
        )


# ------------------------------------------------------------------------------
# Delta Update Model
# ------------------------------------------------------------------------------


@dataclass(frozen=True)
class DeltaUpdate:
    """Incremental state update for synchronization between agents.

    This is the core mechanism for delta sync - agents only receive
    the changed fields, not the entire state.

    Attributes:
        event_id: Unique identifier for this update event.
        timestamp: Unix timestamp of the update.
        entity_type: Type of entity being updated.
        entity_id: ID of the entity being updated.
        operation: Type of operation (create, update, delete).
        changed_keys: List of field names that changed.
        delta: Dictionary of changed values.
        source_agent: ID of the agent that initiated this update.
    """

    event_id: str
    timestamp: int
    entity_type: EntityType
    entity_id: str
    operation: DeltaOperation
    changed_keys: tuple[str, ...]
    delta: dict[str, Any]
    source_agent: str

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        if not self.event_id:
            raise ValueError("event_id cannot be empty")
        if not self.entity_id:
            raise ValueError("entity_id cannot be empty")
        if not self.source_agent:
            raise ValueError("source_agent cannot be empty")

    @staticmethod
    def create(
        entity_type: EntityType,
        entity_id: str,
        operation: DeltaOperation,
        changed_keys: list[str],
        delta: dict[str, Any],
        source_agent: str,
    ) -> DeltaUpdate:
        """Factory method to create a new DeltaUpdate.

        Args:
            entity_type: Type of entity being updated.
            entity_id: ID of the entity being updated.
            operation: Type of operation (create, update, delete).
            changed_keys: List of field names that changed.
            delta: Dictionary of changed values.
            source_agent: ID of the agent that initiated this update.

        Returns:
            A new DeltaUpdate instance.
        """
        return DeltaUpdate(
            event_id=str(uuid.uuid4()),
            timestamp=int(time.time()),
            entity_type=entity_type,
            entity_id=entity_id,
            operation=operation,
            changed_keys=tuple(changed_keys),
            delta=delta,
            source_agent=source_agent,
        )


# ------------------------------------------------------------------------------
# Subscription Handler Type
# ------------------------------------------------------------------------------

DeltaHandler = Callable[[DeltaUpdate], None]
EventHandler = Callable[[Any], None]
