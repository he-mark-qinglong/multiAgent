"""BaseReActAgent - LangGraph StateGraph ReAct Agent.

ReAct Pattern:
    Thought → Action → Observation → ... → Output

Design Principles:
- ReAct loop runs FULLY internally for consistency
- stream() outputs final structured result, NOT per-step tokens
- Interrupt points pause execution for HITL
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Generator, Callable

logger = logging.getLogger(__name__)

# LangGraph imports - graceful degradation
try:
    from langgraph.graph import StateGraph, END, START
    from langgraph.types import interrupt, Command
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    interrupt = None
    StateGraph = None

from core.models import AgentState
from core.langsmith_integration import LangSmithTracer

# LangSmith traceable - graceful degradation
try:
    from langsmith import traceable
except ImportError:
    traceable = None

logger = logging.getLogger(__name__)


class BaseReActAgent(ABC):
    """Base class for LangGraph ReAct agents.

    Each agent implements:
    - think(): Reasoning step
    - act(): Action step with tool calls

    The agent runs a ReAct loop internally, then outputs
    the final structured result via run() or stream().
    """

    def __init__(
        self,
        agent_id: str,
        name: str,
        role: str,
        system_prompt: str,
        tools: list[Any] | None = None,
        max_iterations: int = 10,
    ):
        """Initialize ReAct agent.

        Args:
            agent_id: Unique agent identifier.
            name: Human-readable name.
            role: Agent role (L0, L1, L2+, XL).
            system_prompt: System instructions.
            tools: Available tools for this agent.
            max_iterations: Max ReAct loop iterations.
        """
        self.agent_id = agent_id
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.tools = tools or []
        self.max_iterations = max_iterations
        self.tracer = LangSmithTracer()
        self._graph = None

        if LANGGRAPH_AVAILABLE:
            self._graph = self._build_graph()

    @abstractmethod
    @traceable(name="agent.think") if traceable else lambda fn: fn
    async def think(self, state: AgentState) -> str:
        """Reasoning step - returns thought string.

        Args:
            state: Current agent state.

        Returns:
            Thought string describing reasoning.
        """
        pass

    @abstractmethod
    @traceable(name="agent.act") if traceable else lambda fn: fn
    async def act(self, state: AgentState, thought: str) -> dict[str, Any]:
        """Action step - returns state updates.

        Args:
            state: Current agent state.
            thought: Thought from think() step.

        Returns:
            State updates dict.
        """
        pass

    def _should_finish(self, state: AgentState) -> bool:
        """Check if ReAct loop should finish."""
        messages = state.messages
        if len(messages) >= self.max_iterations * 2:
            logger.warning("Max iterations reached for %s", self.agent_id)
            return True
        return state.metadata.get("_finished", False)

    def _build_graph(self) -> Any:
        """Build ReAct loop graph.

        Graph structure:
            START -> think -> [continue?] -> act -> think
                                          ↓
                                         END
        """
        graph = StateGraph(AgentState)

        graph.add_node("think", self._think_node)
        graph.add_node("act", self._act_node)

        graph.add_edge(START, "think")

        # Conditional edge from think
        graph.add_conditional_edges(
            "think",
            self._should_finish,
            {True: END, False: "act"}
        )

        graph.add_edge("act", "think")

        return graph.compile()

    async def _think_node(self, state: AgentState) -> dict[str, Any]:
        """Think node - runs internal reasoning."""
        thought = await self.think(state)

        messages = list(state.messages)
        messages.append({
            "role": "assistant",
            "content": f"Thought: {thought}",
            "agent_id": self.agent_id,
        })

        return {"messages": messages}

    async def _act_node(self, state: AgentState) -> dict[str, Any]:
        """Act node - runs internal action."""
        messages = state.messages
        thought = messages[-1]["content"] if messages else ""

        updates = await self.act(state, thought)

        # Add action to messages
        messages = list(state.messages)
        messages.append({
            "role": "system",
            "content": f"Action result: {updates}",
            "agent_id": self.agent_id,
        })

        return {"messages": messages, **updates}

    @traceable(name="agent.run") if traceable else lambda fn: fn
    async def run(self, input: str, config: dict[str, Any] | None = None) -> dict[str, Any]:
        """Run agent - full ReAct cycle.

        Args:
            input: User input.
            config: Optional config with thread_id.

        Returns:
            Final state with output.
        """
        if not LANGGRAPH_AVAILABLE:
            return await self._run_mock(input)

        state = {
            "user_query": input,
            "messages": [],
            "metadata": {"agent_id": self.agent_id},
        }

        try:
            result = await self._graph.ainvoke(state, config=config)
            return result
        except Exception as e:
            logger.error("Agent run error: %s", e)
            raise

    async def _run_mock(self, input: str) -> dict[str, Any]:
        """Mock run when LangGraph not available."""
        state = AgentState(user_query=input)
        thought = await self.think(state)
        updates = await self.act(state, thought)
        return {
            "user_query": input,
            "messages": [
                {"role": "assistant", "content": f"Thought: {thought}"},
                {"role": "system", "content": f"Action: {updates}"},
            ],
            **updates,
        }

    def stream(
        self,
        input: str,
        config: dict[str, Any] | None = None,
    ) -> Generator[dict[str, Any], None, None]:
        """Stream agent output - outputs FINAL structured result only.

        IMPORTANT: This does NOT stream intermediate ReAct steps.
        It runs the full ReAct cycle internally, then yields
        the final structured output.

        This preserves ReAct consistency - internal reasoning
        is complete before output is streamed.

        Args:
            input: User input.
            config: Optional config.

        Yields:
            Stream chunks with final result.
        """
        import asyncio

        # Run full cycle
        try:
            if LANGGRAPH_AVAILABLE:
                result = asyncio.run(self.run(input, config))
            else:
                result = asyncio.run(self._run_mock(input))

            # Stream structured output
            yield {
                "type": "complete",
                "data": result,
                "agent_id": self.agent_id,
            }
        except Exception as e:
            yield {
                "type": "error",
                "error": str(e),
                "agent_id": self.agent_id,
            }

    def interrupt_and_wait(
        self,
        message: str,
        state: AgentState,
    ) -> dict[str, Any]:
        """Interrupt execution and wait for human input.

        Usage in act():
            if needs_approval:
                return self.interrupt_and_wait("请确认操作", state)

        Args:
            message: Message to show user.
            state: Current state.

        Returns:
            Interrupt result.
        """
        if LANGGRAPH_AVAILABLE and interrupt:
            try:
                return interrupt(message)
            except RuntimeError as e:
                # Not in LangGraph run context - return fallback
                logger.warning("interrupt_and_wait called outside run context: %s", e)
                return {"approved": True}
        return {"approved": True}  # Fallback: auto-approve
