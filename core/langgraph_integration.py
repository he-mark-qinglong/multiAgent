"""LangGraph StateGraph definitions with ReAct + Interrupt + HITL + EventBus.

Layer 1: LangGraph StateGraph (orchestration + persistence)
Layer 2: DeltaUpdate + EventBus (external notifications)
"""

from __future__ import annotations

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

        if LANGGRAPH_AVAILABLE:
            self._graph = self._build_graph()

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
        """Intent recognition node."""
        from core.models import IntentChain, IntentNode

        logger.info("Intent node: %s", state.user_query[:50])

        intent_node = IntentNode(
            intent="analyze",
            entities={"query": state.user_query},
            confidence=0.9,
        )
        intent_chain = IntentChain(
            nodes=[intent_node],
            current_node_id=intent_node.id,
        )

        # Emit delta for external notifications
        await self._emit_delta(
            entity_type=EntityType.INTENT,
            entity_id=intent_chain.chain_id,
            operation="create",
            changes={"intent": intent_node.intent, "confidence": intent_node.confidence},
            source_agent="intent_agent",
        )

        return {"intent_chain": intent_chain}

    async def _planner_node(self, state: AgentState) -> dict[str, Any]:
        """Planning node."""
        from core.models import Goal, Plan

        if not state.intent_chain:
            return {"plan": None, "goals": {}}

        current_intent = state.intent_chain.nodes[-1].intent
        goal = Goal(
            type="execute",
            description=f"Execute: {current_intent}",
        )

        plan = Plan(
            intent_chain_ref=state.intent_chain.chain_id,
            execution_order=[goal.id],
        )

        # Emit delta
        await self._emit_delta(
            entity_type=EntityType.GOAL,
            entity_id=goal.id,
            operation="create",
            changes={"description": goal.description, "type": goal.type},
            source_agent="planner_agent",
        )

        return {"plan": plan, "goals": {goal.id: goal}}

    async def _executor_node(self, state: AgentState) -> dict[str, Any]:
        """Execution node with interrupt support."""
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

        execution_results = {}
        for goal_id, goal in goals.items():
            execution_results[goal_id] = {
                "status": "completed",
                "result": f"Executed: {goal.description}",
            }

        # Emit delta
        await self._emit_delta(
            entity_type=EntityType.STATUS,
            entity_id=goal_id,
            operation="update",
            changes={"status": "completed", "result": execution_results[goal_id]},
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
        """Synthesis node."""
        results = state.execution_results
        goal_count = len(results)
        completed = sum(1 for r in results.values() if r.get("status") == "completed")

        response = f"完成了 {completed}/{goal_count} 个任务。"
        for goal_id, result in results.items():
            if result:
                response += f"\n- {goal_id}: {result.get('result', 'Done')}"

        return {"final_response": response}

    def invoke(
        self,
        input: UserQuery | dict[str, Any],
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Synchronous invoke."""
        if not LANGGRAPH_AVAILABLE:
            return {"final_response": "LangGraph not available"}

        if isinstance(input, UserQuery):
            input = {"user_query": input.query}

        config = config or {}
        if "configurable" not in config:
            config["configurable"] = {}

        try:
            return self._graph.invoke(input, config=config)
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
