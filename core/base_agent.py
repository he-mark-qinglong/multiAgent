"""BaseAgent abstract class for the Multi-Agent Collaboration System.

All agents inherit from this base class, which provides:
- Identity management (ID, name, role)
- State store integration for delta updates
- Event bus integration for publish/subscribe
- Scoped context assembly for context isolation
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable

from core.event_bus import EventBus, Event
from core.models import (
    DeltaUpdate,
    DeltaHandler,
    EntityType,
    IntentChain,
    Goal,
    GoalTree,
    Plan,
)
from core.state_store import StateStore

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# Agent Role Enum
# ------------------------------------------------------------------------------


class AgentRole(str):
    """Role identifiers for agents."""

    INTENT = "intent"
    PLANNER = "planner"
    EXECUTOR = "executor"
    MONITOR = "monitor"
    SYNTHESIZER = "synthesizer"


# ------------------------------------------------------------------------------
# Scoped Context
# ------------------------------------------------------------------------------


@dataclass
class ScopedContext:
    """Scoped context assembled for an agent's execution.

    Attributes:
        agent_id: ID of the agent this context is for.
        intent_chain: Relevant intent chain for this context.
        goal_state: Current goal state relevant to this agent.
        recent_results: Recent execution results.
        system_prefix: Cached system instructions.
        assembled: Fully assembled context string.
        token_count: Estimated token count of the assembled context.
    """

    agent_id: str
    intent_chain: IntentChain | None
    goal_state: GoalTree | None
    recent_results: list[Any]
    system_prefix: str
    assembled: str
    token_count: int


# ------------------------------------------------------------------------------
# Context Assembler
# ------------------------------------------------------------------------------


class ContextAssembler:
    """Assembles minimal context for each agent based on their role.

    Implements context isolation - each agent only sees what it needs.
    """

    # Token cost estimates (approximate)
    TOKEN_PER_CHAR = 0.25

    @staticmethod
    def assemble_for_intent_agent(
        state_store: StateStore,
        current_query: str,
        history_limit: int = 5,
    ) -> ScopedContext:
        """Assemble context for the Intent Agent.

        Intent Agent needs: current query + recent intent chain + history summary.

        Args:
            state_store: The state store to read from.
            current_query: The current user query.
            history_limit: Maximum number of recent intents to include.

        Returns:
            ScopedContext with intent-relevant data.
        """
        recent_intents = state_store.list_by_type(EntityType.INTENT)[-history_limit:]
        intent_data = recent_intents[-1] if recent_intents else None

        system_prefix = (
            "You are the Intent Recognition Agent. "
            "Your task is to identify the user's intent from the query. "
            "Return an IntentNode with the recognized intent, entities, and confidence."
        )

        assembled = f"{system_prefix}\n\nCurrent Query: {current_query}\n"
        if intent_data:
            assembled += f"\nRecent Intent: {intent_data}\n"

        return ScopedContext(
            agent_id="intent",
            intent_chain=intent_data,
            goal_state=None,
            recent_results=[],
            system_prefix=system_prefix,
            assembled=assembled,
            token_count=int(len(assembled) * ContextAssembler.TOKEN_PER_CHAR),
        )

    @staticmethod
    def assemble_for_planner_agent(
        state_store: StateStore,
        intent_chain: IntentChain,
    ) -> ScopedContext:
        """Assemble context for the Planner Agent.

        Planner Agent needs: IntentChain + current goal status + available executors.

        Args:
            state_store: The state store to read from.
            intent_chain: The intent chain to plan from.

        Returns:
            ScopedContext with planner-relevant data.
        """
        all_goals = state_store.list_by_type(EntityType.GOAL)
        active_goals = [g for g in all_goals if g.status not in ("completed", "failed")]

        system_prefix = (
            "You are the Planner Agent. "
            "Your task is to create a Plan with GoalTree based on the IntentChain. "
            "Return a Plan with execution order and dependencies."
        )

        assembled = f"{system_prefix}\n\nIntent Chain:\n{intent_chain}\n"
        if active_goals:
            assembled += f"\nActive Goals: {len(active_goals)}\n"

        return ScopedContext(
            agent_id="planner",
            intent_chain=intent_chain,
            goal_state=None,
            recent_results=[],
            system_prefix=system_prefix,
            assembled=assembled,
            token_count=int(len(assembled) * ContextAssembler.TOKEN_PER_CHAR),
        )

    @staticmethod
    def assemble_for_executor_agent(
        state_store: StateStore,
        goal: Goal,
        max_log_steps: int = 3,
    ) -> ScopedContext:
        """Assemble context for an Executor Agent.

        Executor Agent needs: assigned goal + recent process log.

        Args:
            state_store: The state store to read from.
            goal: The goal assigned to this executor.
            max_log_steps: Maximum number of recent log steps to include.

        Returns:
            ScopedContext with executor-relevant data.
        """
        recent_logs = goal.process_log[-max_log_steps:] if goal.process_log else []

        system_prefix = (
            f"You are the Executor Agent for goal: {goal.description}. "
            "Execute the task and report the result. "
            "Log each step using _emit_delta."
        )

        assembled = f"{system_prefix}\n\nGoal:\n{goal}\n"
        if recent_logs:
            assembled += f"\nRecent Steps:\n{recent_logs}\n"

        return ScopedContext(
            agent_id=goal.assigned_to or "executor",
            intent_chain=None,
            goal_state=None,
            recent_results=[],
            system_prefix=system_prefix,
            assembled=assembled,
            token_count=int(len(assembled) * ContextAssembler.TOKEN_PER_CHAR),
        )

    @staticmethod
    def assemble_for_synthesizer_agent(
        state_store: StateStore,
        goal_tree: GoalTree,
    ) -> ScopedContext:
        """Assemble context for the Synthesizer Agent.

        Synthesizer Agent needs: complete GoalTree + all sub-goal results.

        Args:
            state_store: The state store to read from.
            goal_tree: The complete goal tree with results.

        Returns:
            ScopedContext with synthesizer-relevant data.
        """
        results = [g.result for g in goal_tree.goals.values() if g.result is not None]

        system_prefix = (
            "You are the Synthesizer Agent. "
            "Your task is to aggregate sub-goal results into a final response. "
            "Return a synthesized result that addresses the original intent."
        )

        assembled = f"{system_prefix}\n\nGoal Tree:\n{goal_tree}\n"
        if results:
            assembled += f"\nResults: {results}\n"

        return ScopedContext(
            agent_id="synthesizer",
            intent_chain=None,
            goal_state=goal_tree,
            recent_results=results,
            system_prefix=system_prefix,
            assembled=assembled,
            token_count=int(len(assembled) * ContextAssembler.TOKEN_PER_CHAR),
        )


# ------------------------------------------------------------------------------
# Base Agent
# ------------------------------------------------------------------------------


from dataclasses import dataclass


class BaseAgent(ABC):
    """Abstract base class for all agents in the collaboration system.

    Provides common functionality for identity, state management,
    event communication, and context assembly.

    Attributes:
        agent_id: Unique identifier for this agent instance.
        name: Human-readable name for this agent.
        role: Role this agent plays in the system.
        state_store: Shared state store for persistence.
        event_bus: Shared event bus for communication.

    Example:
        class IntentAgent(BaseAgent):
            def run(self, input: str) -> IntentChain:
                # Implementation here
                pass

        agent = IntentAgent(
            agent_id="intent-1",
            name="Intent Recognition",
            state_store=StateStore(),
            event_bus=EventBus(),
        )
        result = agent.run("What is the weather?")
    """

    def __init__(
        self,
        agent_id: str,
        name: str,
        role: str,
        state_store: StateStore | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        """Initialize the BaseAgent.

        Args:
            agent_id: Unique identifier for this agent.
            name: Human-readable name for this agent.
            role: Role this agent plays (from AgentRole).
            state_store: Optional shared state store. Creates new if not provided.
            event_bus: Optional shared event bus. Creates new if not provided.
        """
        self.agent_id = agent_id
        self.name = name
        self.role = role
        self._state_store = state_store or StateStore()
        self._event_bus = event_bus or EventBus()
        self._subscriptions: list[str] = []
        self._logger = logging.getLogger(f"{__name__}.{role}.{agent_id}")

        self._logger.info("Agent initialized: %s (%s)", name, role)

    # --------------------------------------------------------------------------
    # Identity Properties
    # --------------------------------------------------------------------------

    @property
    def state_store(self) -> StateStore:
        """Get the state store for this agent."""
        return self._state_store

    @property
    def event_bus(self) -> EventBus:
        """Get the event bus for this agent."""
        return self._event_bus

    # --------------------------------------------------------------------------
    # Abstract Methods
    # --------------------------------------------------------------------------

    @abstractmethod
    def run(self, input: Any) -> Any:
        """Execute the agent's primary task.

        This is the main entry point for agent execution.

        Args:
            input: The input data for this agent's task.

        Returns:
            The result of the agent's execution.

        Raises:
            NotImplementedError: Must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement run()")

    # --------------------------------------------------------------------------
    # Delta Update Helpers
    # --------------------------------------------------------------------------

    def _emit_delta(
        self,
        entity_type: EntityType,
        entity_id: str,
        changes: dict[str, Any],
    ) -> DeltaUpdate:
        """Emit a delta update to the state store.

        This is the primary method for agents to update shared state.
        Changes are automatically dispatched to subscribers.

        Args:
            entity_type: Type of entity being updated.
            entity_id: Unique ID of the entity.
            changes: Dictionary of changed field names and values.

        Returns:
            The created DeltaUpdate.
        """
        delta = self._state_store.delta_update(
            entity_type=entity_type,
            entity_id=entity_id,
            changes=changes,
            source_agent=self.agent_id,
        )

        self._event_bus.publish_delta(
            entity_type=entity_type.value,
            entity_id=entity_id,
            operation=delta.operation.value,
            delta=delta.delta,
            source_agent=self.agent_id,
        )

        self._logger.debug(
            "Emitted delta: %s/%s [%s] keys=%s",
            entity_type.value,
            entity_id,
            delta.operation.value,
            list(changes.keys()),
        )

        return delta

    def _store_entity(
        self,
        entity_type: EntityType,
        entity_id: str,
        entity: Any,
    ) -> DeltaUpdate:
        """Store an entity in the state store.

        Args:
            entity_type: Type of the entity.
            entity_id: Unique ID of the entity.
            entity: The entity data to store.

        Returns:
            The created DeltaUpdate.
        """
        delta = self._state_store.set(
            entity_type=entity_type,
            entity_id=entity_id,
            value=entity,
            source_agent=self.agent_id,
        )

        self._logger.debug("Stored entity: %s/%s", entity_type.value, entity_id)
        return delta

    def _delete_entity(
        self,
        entity_type: EntityType,
        entity_id: str,
    ) -> DeltaUpdate | None:
        """Delete an entity from the state store.

        Args:
            entity_type: Type of the entity.
            entity_id: Unique ID of the entity.

        Returns:
            The DeltaUpdate if deleted, None if not found.
        """
        delta = self._state_store.delete(
            entity_type=entity_type,
            entity_id=entity_id,
            source_agent=self.agent_id,
        )

        if delta:
            self._logger.debug("Deleted entity: %s/%s", entity_type.value, entity_id)
        return delta

    # --------------------------------------------------------------------------
    # Context Assembly
    # --------------------------------------------------------------------------

    def _request_context(
        self,
        context_type: str,
        **kwargs: Any,
    ) -> ScopedContext:
        """Request a scoped context for this agent's execution.

        This method handles context isolation - the agent only receives
        the data it needs based on its role.

        Args:
            context_type: Type of context to assemble.
            **kwargs: Additional parameters specific to the context type.

        Returns:
            ScopedContext with the assembled data.

        Raises:
            ValueError: If the context type is unknown.
        """
        if context_type == "intent":
            return ContextAssembler.assemble_for_intent_agent(
                self._state_store,
                current_query=kwargs.get("current_query", ""),
                history_limit=kwargs.get("history_limit", 5),
            )
        elif context_type == "planner":
            return ContextAssembler.assemble_for_planner_agent(
                self._state_store,
                intent_chain=kwargs.get("intent_chain"),
            )
        elif context_type == "executor":
            return ContextAssembler.assemble_for_executor_agent(
                self._state_store,
                goal=kwargs.get("goal"),
                max_log_steps=kwargs.get("max_log_steps", 3),
            )
        elif context_type == "synthesizer":
            return ContextAssembler.assemble_for_synthesizer_agent(
                self._state_store,
                goal_tree=kwargs.get("goal_tree"),
            )
        else:
            raise ValueError(f"Unknown context type: {context_type}")

    # --------------------------------------------------------------------------
    # Event Subscription Helpers
    # --------------------------------------------------------------------------

    def subscribe_to(
        self,
        topic_pattern: str,
        callback: Callable[[Event], None],
    ) -> str:
        """Subscribe to events matching a topic pattern.

        Args:
            topic_pattern: Pattern to match topics against.
            callback: Function to call for matching events.

        Returns:
            Handler ID for unsubscribing.
        """
        handler_id = self._event_bus.subscribe(
            topic_pattern=topic_pattern,
            callback=callback,
        )
        self._subscriptions.append(handler_id)
        self._logger.debug("Subscribed to topic: %s", topic_pattern)
        return handler_id

    def subscribe_to_entity(
        self,
        entity_type: EntityType,
        callback: Callable[[DeltaUpdate], None],
    ) -> str:
        """Subscribe to state changes for an entity type.

        Args:
            entity_type: Type of entity to subscribe to.
            callback: Function to call for each change.

        Returns:
            Handler ID for unsubscribing.
        """
        def event_to_delta(event: Event) -> None:
            if hasattr(event.payload, "get"):
                delta = DeltaUpdate.create(
                    entity_type=EntityType(event.topic.split(".")[1]),
                    entity_id=event.payload.get("entity_id", ""),
                    operation=__import__("core.models", fromlist=["DeltaOperation"]).DeltaOperation(event.topic.split(".")[2]),
                    changed_keys=list(event.payload.get("delta", {}).keys()),
                    delta=event.payload.get("delta", {}),
                    source_agent=event.source_agent,
                )
                callback(delta)

        handler_id = self._event_bus.subscribe(
            topic_pattern=f"state.{entity_type.value}.*",
            callback=event_to_delta,
        )
        self._subscriptions.append(handler_id)
        return handler_id

    def unsubscribe_all(self) -> None:
        """Unsubscribe from all topics this agent is subscribed to."""
        for handler_id in self._subscriptions:
            self._event_bus.unsubscribe(handler_id)
        self._subscriptions.clear()
        self._logger.debug("Unsubscribed from all topics")

    # --------------------------------------------------------------------------
    # Lifecycle
    # --------------------------------------------------------------------------

    def __repr__(self) -> str:
        """String representation of the agent."""
        return f"{self.__class__.__name__}(id={self.agent_id}, name={self.name}, role={self.role})"
