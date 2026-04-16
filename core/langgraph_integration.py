"""LangGraph StateGraph definitions with ReAct + Interrupt + HITL + EventBus.

Layer 1: LangGraph StateGraph (orchestration + persistence)
Layer 2: DeltaUpdate + EventBus (external notifications)
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)

# LangGraph imports - graceful degradation
try:
    from langgraph.graph import StateGraph, END, START
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.store.memory import InMemoryStore
    from langgraph.types import interrupt, Command
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    interrupt = None

from core.models import AgentState, UserQuery, EntityType
from core.event_bus import EventBus, get_event_bus
from core.langsmith_integration import LangSmithTracer

logger = logging.getLogger(__name__)


class PipelineStateGraph:
    """LangGraph StateGraph for the collaboration pipeline.

    Layer 1: LangGraph (orchestration + Checkpointer)
    Layer 2: EventBus (external notifications)

    Architecture:
        START -> intent -> planner -> executor
                                               |
                           [needs_approval?]    |
                              ↓ yes            ↓ no
                          human_approval -> synthesizer -> END
    """

    def __init__(
        self,
        checkpointer: Any = None,
        store: Any = None,
        event_bus: EventBus | None = None,
    ):
        self.checkpointer = checkpointer or (MemorySaver() if LANGGRAPH_AVAILABLE else None)
        self.store = store or (InMemoryStore() if LANGGRAPH_AVAILABLE else None)
        self.event_bus = event_bus or get_event_bus()
        self.tracer = LangSmithTracer()
        self._graph = None

        # Create agents with MiniMax LLM
        self._agents = None

        if LANGGRAPH_AVAILABLE:
            self._graph = self._build_graph()

    def _get_agents(self) -> dict[str, Any]:
        """Lazy load agents to avoid circular imports."""
        if self._agents is None:
            from core.agent_factory import get_agents
            self._agents = get_agents()
        return self._agents

    async def _emit_delta(
        self,
        entity_type: EntityType,
        entity_id: str,
        operation: str,
        changes: dict[str, Any],
        source_agent: str,
    ) -> None:
        """Publish delta update to EventBus for external notifications.

        Args:
            entity_type: Entity type.
            entity_id: Entity ID.
            operation: Operation (create, update, delete).
            changes: Changed data.
            source_agent: Source agent ID.
        """
        if self.event_bus:
            self.event_bus.publish_delta(
                entity_type=entity_type.value,
                entity_id=entity_id,
                operation=operation,
                delta=changes,
                source_agent=source_agent,
            )

    def _build_graph(self) -> Any:
        """Build the pipeline StateGraph."""
        graph = StateGraph(AgentState)

        graph.add_node("intent", self._intent_node)
        graph.add_node("planner", self._planner_node)
        graph.add_node("executor", self._executor_node)
        graph.add_node("human_approval", self._human_approval_node)
        graph.add_node("synthesizer", self._synthesizer_node)

        graph.add_edge(START, "intent")
        graph.add_edge("intent", "planner")
        graph.add_edge("planner", "executor")

        graph.add_conditional_edges(
            "executor",
            self._should_interrupt,
            {True: "human_approval", False: "synthesizer"}
        )

        graph.add_edge("human_approval", "executor")
        graph.add_edge("synthesizer", END)

        return graph.compile(
            checkpointer=self.checkpointer,
            store=self.store,
        )

    def _should_interrupt(self, state: AgentState) -> bool:
        """Check if execution should be interrupted for human approval."""
        return state.needs_approval and not state.interrupted

    async def _intent_node(self, state: AgentState) -> dict[str, Any]:
        """Intent recognition node - uses IntentAgent with MiniMax LLM."""
        logger.info("Intent node: %s", state.user_query[:50])

        # Use IntentAgent with MiniMax LLM
        agents = self._get_agents()
        intent_agent = agents["intent"]

        # Run intent agent's think and act
        thought = await intent_agent.think(state)
        result = await intent_agent.act(state, thought)
        intent_chain = result.get("intent_chain")

        if intent_chain:
            # Emit delta for external notifications
            for node in intent_chain.nodes:
                await self._emit_delta(
                    entity_type=EntityType.INTENT,
                    entity_id=intent_chain.chain_id,
                    operation="create",
                    changes={"intent": node.intent, "confidence": node.confidence},
                    source_agent="intent_agent",
                )

        return {"intent_chain": intent_chain}

    async def _planner_node(self, state: AgentState) -> dict[str, Any]:
        """Planning node - uses PlannerAgent to create multiple goals."""
        if not state.intent_chain:
            return {"plan": None, "goals": {}}

        # Use PlannerAgent with MiniMax LLM
        agents = self._get_agents()
        planner_agent = agents["planner"]

        # Run planner agent's think and act
        thought = await planner_agent.think(state)
        result = await planner_agent.act(state, thought)
        plan = result.get("plan")
        goals = result.get("goals", {})

        # Emit delta for each goal
        for goal_id, goal in goals.items():
            await self._emit_delta(
                entity_type=EntityType.GOAL,
                entity_id=goal_id,
                operation="create",
                changes={"description": goal.description, "type": goal.type},
                source_agent="planner_agent",
            )

        return {"plan": plan, "goals": goals}

    async def _executor_node(self, state: AgentState) -> dict[str, Any]:
        """Execution node with interrupt support - uses ExecutorAgent with ToolRegistry."""
        goals = state.goals

        if not goals:
            return {"execution_results": {}}

        if state.needs_approval and not state.interrupted:
            if LANGGRAPH_AVAILABLE and interrupt:
                result = interrupt("等待用户审批: 是否继续执行?")
                if not result.get("approved", False):
                    return {
                        "execution_results": {},
                        "needs_approval": False,
                        "interrupted": True,
                        "metadata": {"reason": result.get("reason", "用户拒绝")},
                    }

        # Use ExecutorAgent with ToolRegistry
        agents = self._get_agents()
        executor_agent = agents["executor"]

        # Run executor agent's think and act
        thought = await executor_agent.think(state)
        result = await executor_agent.act(state, thought)
        execution_results = result.get("execution_results", {})

        # Emit delta for each result
        for goal_id, result_data in execution_results.items():
            await self._emit_delta(
                entity_type=EntityType.STATUS,
                entity_id=goal_id,
                operation="update",
                changes={"status": result_data.get("status", "completed"), "result": result_data},
                source_agent="executor_agent",
            )

        return {"execution_results": execution_results}

    async def _human_approval_node(self, state: AgentState) -> dict[str, Any]:
        """Human-in-the-Loop approval node."""
        return {
            "metadata": {
                "interrupt_type": "human_approval",
                "message": "请确认是否继续执行",
            }
        }

    async def _synthesizer_node(self, state: AgentState) -> dict[str, Any]:
        """Synthesis node - uses SynthesizerAgent for natural language summary."""
        # Use SynthesizerAgent for natural language response
        agents = self._get_agents()
        synthesizer_agent = agents["synthesizer"]

        # Run synthesizer agent's think and act
        thought = await synthesizer_agent.think(state)
        result = await synthesizer_agent.act(state, thought)
        final_response = result.get("final_response", "")

        return {"final_response": final_response}

    def invoke(
        self,
        input: UserQuery | dict[str, Any],
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Synchronous invoke (bridges to async for LangGraph)."""
        if not LANGGRAPH_AVAILABLE:
            return {"final_response": "LangGraph not available"}

        if isinstance(input, UserQuery):
            input = {"user_query": input.query}

        config = config or {}
        if "configurable" not in config:
            config["configurable"] = {}

        try:
            # Bridge sync -> async since nodes are async functions
            # Use run_until_complete if event loop exists, otherwise use run
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # No running loop, safe to use asyncio.run()
                return asyncio.run(self._graph.ainvoke(input, config=config))
            else:
                # Already in async context, create a future and run it
                async def _invoke():
                    return await self._graph.ainvoke(input, config=config)
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, _invoke())
                    return future.result()
        except Exception as e:
            logger.error("Graph invoke error: %s", e)
            raise

    def stream(
        self,
        input: UserQuery | dict[str, Any],
        config: dict[str, Any] | None = None,
    ):
        """Streaming invoke - outputs final structured result only."""
        if not LANGGRAPH_AVAILABLE:
            yield {"type": "error", "error": "LangGraph not available"}
            return

        if isinstance(input, UserQuery):
            input = {"user_query": input.query}

        try:
            result = self.invoke(input, config)
            yield {"type": "result", "data": result}
        except Exception as e:
            yield {"type": "error", "error": str(e)}


class HumanApprovalManager:
    """Manages human approval interrupts."""

    def __init__(self, graph: PipelineStateGraph | None = None):
        self.graph = graph
        self._pending_approvals: dict[str, dict[str, Any]] = {}

    def request_approval(
        self,
        thread_id: str,
        action: str,
        details: str,
    ) -> str:
        """Request human approval."""
        approval_id = f"approval_{thread_id}_{len(self._pending_approvals)}"
        self._pending_approvals[thread_id] = {
            "approval_id": approval_id,
            "action": action,
            "details": details,
            "approved": None,
        }
        return approval_id

    def get_pending(self, thread_id: str) -> dict[str, Any] | None:
        """Get pending approval for thread."""
        return self._pending_approvals.get(thread_id)

    def submit_approval(
        self,
        thread_id: str,
        approved: bool,
        reason: str = "",
    ) -> dict[str, Any]:
        """Submit approval and resume execution."""
        self._pending_approvals[thread_id] = {
            "approved": approved,
            "reason": reason,
        }

        if not self.graph or not LANGGRAPH_AVAILABLE:
            return {}

        command = Command(resume={"approved": approved, "reason": reason})
        config = {"configurable": {"thread_id": thread_id}}

        try:
            return self.graph.invoke(command, config=config)
        except Exception as e:
            logger.error("Failed to resume from approval: %s", e)
            return {}
