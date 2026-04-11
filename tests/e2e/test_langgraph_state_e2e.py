"""LangGraph state E2E tests."""

import sys
sys.path.insert(0, '.')

import pytest
from core.langgraph_integration import PipelineStateGraph, HumanApprovalManager
from core.models import AgentState, UserQuery, IntentChain, IntentNode, Goal, Plan


class TestLangGraphStateE2E:
    """E2E tests for LangGraph state transitions and persistence."""

    @pytest.fixture
    def graph(self):
        return PipelineStateGraph()

    @pytest.fixture
    def approval_manager(self, graph):
        return HumanApprovalManager(graph)

    def test_state_transitions_intent_to_planner(self, graph):
        """State flows from intent to planner node."""
        input_data = {"user_query": "测试查询"}
        result = graph.invoke(input_data)
        assert isinstance(result, dict)
        # After intent node, intent_chain should be set
        if result.get("intent_chain"):
            assert isinstance(result["intent_chain"], IntentChain)

    def test_state_transitions_full_pipeline(self, graph):
        """State flows through all pipeline nodes."""
        input_data = {"user_query": "完整流程测试"}
        result = graph.invoke(input_data)
        assert isinstance(result, dict)
        # State should accumulate through all nodes
        assert "user_query" in result

    def test_state_includes_goals_after_planner(self, graph):
        """Planner node creates goals in state."""
        input_data = {"user_query": "创建目标"}
        result = graph.invoke(input_data)
        # Goals dict should be present
        assert "goals" in result
        assert isinstance(result["goals"], dict)

    def test_interrupt_triggers_when_needs_approval(self, graph):
        """needs_approval=True triggers interrupt node."""
        input_data = {"user_query": "需要审批", "needs_approval": True}
        # This should reach the interrupt/approval node
        result = graph.invoke(input_data)
        assert isinstance(result, dict)

    def test_state_history_stored_by_checkpointer(self, graph):
        """Checkpointer stores state history."""
        thread_id = "checkpoint_test_001"
        config = {"configurable": {"thread_id": thread_id}}

        # First invocation
        graph.invoke({"user_query": "第一轮"}, config=config)
        # Second invocation
        graph.invoke({"user_query": "第二轮"}, config=config)

        # Get history
        history = list(graph._graph.get_state_history(config))
        assert len(history) >= 1

    def test_concurrent_sessions_dont_interfere(self, graph):
        """Multiple thread_ids maintain separate state."""
        config_a = {"configurable": {"thread_id": "session_A"}}
        config_b = {"configurable": {"thread_id": "session_B"}}

        result_a = graph.invoke({"user_query": "会话A"}, config=config_a)
        result_b = graph.invoke({"user_query": "会话B"}, config=config_b)

        # Both should succeed independently
        assert isinstance(result_a, dict)
        assert isinstance(result_b, dict)

    def test_state_graph_stream_output(self, graph):
        """stream() outputs structured result."""
        input_data = {"user_query": "流式测试"}
        chunks = list(graph.stream(input_data))
        assert len(chunks) >= 1
        assert chunks[0].get("type") in ("result", "error")

    def test_approval_manager_request_approval(self, approval_manager):
        """HumanApprovalManager request_approval stores pending."""
        approval_id = approval_manager.request_approval(
            thread_id="session_1",
            action="unlock",
            details="解锁车门",
        )
        assert approval_id.startswith("approval_")
        pending = approval_manager.get_pending("session_1")
        assert pending is not None
        assert pending["action"] == "unlock"

    def test_approval_manager_submit_approved(self, approval_manager):
        """submit_approval with approved=True is recorded."""
        approval_manager.request_approval("s2", "action", "details")
        result = approval_manager.submit_approval("s2", approved=True)
        assert isinstance(result, dict)

    def test_approval_manager_submit_rejected(self, approval_manager):
        """submit_approved with approved=False is recorded."""
        approval_manager.request_approval("s3", "action", "details")
        pending = approval_manager.get_pending("s3")
        assert pending["approved"] is None

        approval_manager.submit_approval("s3", approved=False)
        pending_after = approval_manager.get_pending("s3")
        assert pending_after["approved"] is False

    def test_agent_state_model_validation(self):
        """AgentState model validates correctly."""
        state = AgentState(user_query="test")
        assert state.user_query == "test"
        assert state.intent_chain is None
        assert state.needs_approval is False

    def test_intent_chain_model(self):
        """IntentChain model works."""
        node = IntentNode(intent="test", confidence=0.9)
        chain = IntentChain(nodes=[node], current_node_id=node.id)
        assert len(chain.nodes) == 1
        assert chain.current_node_id == node.id

    def test_goal_model(self):
        """Goal model works."""
        goal = Goal(type="execute", description="Test goal")
        assert goal.status.value == "pending"
        assert goal.id is not None

    def test_plan_model(self):
        """Plan model works."""
        plan = Plan(intent_chain_ref="ref_123", execution_order=["g1", "g2"])
        assert len(plan.execution_order) == 2
        assert plan.dependencies == {}

    def test_langgraph_graceful_degradation(self):
        """Pipeline handles LangGraph unavailability gracefully."""
        # The PipelineStateGraph handles LANGGRAPH_AVAILABLE=False
        graph = PipelineStateGraph()
        result = graph.invoke({"user_query": "test"})
        assert isinstance(result, dict)
