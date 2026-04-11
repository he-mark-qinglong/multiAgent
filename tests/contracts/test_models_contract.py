"""Model contract tests - verify all Pydantic models match their spec."""

import sys
sys.path.insert(0, '.')

import pytest
from core.models import (
    UserQuery,
    FinalResponse,
    IntentChain,
    IntentNode,
    Goal,
    Plan,
    ExecutionStatus,
    DeltaUpdate,
    AgentState,
    StreamChunk,
    EntityType,
    IntentStatus,
    GoalStatus,
    ExecutionStatusValue,
)


class TestUserQueryModel:
    """UserQuery model contract."""

    def test_accepts_query_str(self):
        """UserQuery(query='...') works."""
        q = UserQuery(query="test query")
        assert q.query == "test query"

    def test_generates_session_id(self):
        """Auto-generates session_id if not provided."""
        q = UserQuery(query="test")
        assert q.session_id is not None
        assert isinstance(q.session_id, str)

    def test_accepts_custom_session_id(self):
        """Accepts custom session_id."""
        q = UserQuery(query="test", session_id="custom_id")
        assert q.session_id == "custom_id"


class TestIntentNodeModel:
    """IntentNode model contract."""

    def test_required_fields(self):
        """IntentNode has required intent field."""
        node = IntentNode(intent="search")
        assert node.intent == "search"

    def test_confidence_default(self):
        """Confidence defaults to 1.0."""
        node = IntentNode(intent="search")
        assert node.confidence == 1.0

    def test_confidence_validation_range(self):
        """Confidence must be 0-1."""
        node = IntentNode(intent="search", confidence=0.5)
        assert 0.0 <= node.confidence <= 1.0

    def test_confidence_validation_invalid_low(self):
        """Confidence rejects value below 0."""
        with pytest.raises(ValueError):
            IntentNode(intent="search", confidence=-0.1)

    def test_confidence_validation_invalid_high(self):
        """Confidence rejects value above 1."""
        with pytest.raises(ValueError):
            IntentNode(intent="search", confidence=1.5)

    def test_generates_id(self):
        """Auto-generates id."""
        node = IntentNode(intent="test")
        assert node.id is not None

    def test_has_entities_dict(self):
        """Has entities dict field."""
        node = IntentNode(intent="test", entities={"key": "value"})
        assert node.entities == {"key": "value"}

    def test_has_parent_id(self):
        """Has parent_id field."""
        node = IntentNode(intent="test", parent_id="parent_123")
        assert node.parent_id == "parent_123"

    def test_has_status(self):
        """Has status field with default."""
        node = IntentNode(intent="test")
        assert node.status == IntentStatus.ACTIVE

    def test_has_created_at(self):
        """Has created_at timestamp."""
        node = IntentNode(intent="test")
        assert isinstance(node.created_at, int)


class TestIntentChainModel:
    """IntentChain model contract."""

    def test_has_chain_id(self):
        """Has chain_id field."""
        chain = IntentChain()
        assert chain.chain_id is not None

    def test_has_nodes_list(self):
        """Has nodes list field."""
        chain = IntentChain(nodes=[])
        assert isinstance(chain.nodes, list)

    def test_has_current_node_id(self):
        """Has current_node_id field."""
        chain = IntentChain()
        assert chain.current_node_id is None

    def test_has_cross_topic_refs(self):
        """Has cross_topic_refs list."""
        chain = IntentChain()
        assert isinstance(chain.cross_topic_refs, list)

    def test_accepts_intent_nodes(self):
        """Accepts IntentNode list."""
        node = IntentNode(intent="test")
        chain = IntentChain(nodes=[node])
        assert len(chain.nodes) == 1


class TestGoalModel:
    """Goal model contract."""

    def test_has_required_fields(self):
        """Goal has required type and description."""
        goal = Goal(type="execute", description="Do something")
        assert goal.type == "execute"
        assert goal.description == "Do something"

    def test_generates_id(self):
        """Auto-generates id."""
        goal = Goal(type="x", description="y")
        assert goal.id is not None

    def test_has_status_default(self):
        """Status defaults to PENDING."""
        goal = Goal(type="x", description="y")
        assert goal.status == GoalStatus.PENDING

    def test_has_params_dict(self):
        """Has params dict."""
        goal = Goal(type="x", description="y", params={"k": "v"})
        assert goal.params == {"k": "v"}

    def test_has_process_log(self):
        """Has process_log list."""
        goal = Goal(type="x", description="y")
        assert isinstance(goal.process_log, list)

    def test_has_parent_id(self):
        """Has parent_id field."""
        goal = Goal(type="x", description="y", parent_id="p123")
        assert goal.parent_id == "p123"

    def test_has_assigned_to(self):
        """Has assigned_to field."""
        goal = Goal(type="x", description="y", assigned_to="agent_1")
        assert goal.assigned_to == "agent_1"


class TestPlanModel:
    """Plan model contract."""

    def test_has_required_fields(self):
        """Plan has intent_chain_ref and execution_order."""
        plan = Plan(intent_chain_ref="ref_123", execution_order=["g1", "g2"])
        assert plan.intent_chain_ref == "ref_123"
        assert len(plan.execution_order) == 2

    def test_generates_plan_id(self):
        """Auto-generates plan_id."""
        plan = Plan(intent_chain_ref="r", execution_order=[])
        assert plan.plan_id is not None

    def test_has_dependencies(self):
        """Has dependencies dict."""
        plan = Plan(intent_chain_ref="r", execution_order=[], dependencies={"g1": ["g0"]})
        assert plan.dependencies == {"g1": ["g0"]}

    def test_has_estimated_cost(self):
        """Has estimated_cost int."""
        plan = Plan(intent_chain_ref="r", execution_order=[], estimated_cost=100)
        assert plan.estimated_cost == 100


class TestDeltaUpdateModel:
    """DeltaUpdate model contract."""

    def test_has_required_fields(self):
        """DeltaUpdate has all required fields."""
        du = DeltaUpdate(
            entity_type=EntityType.GOAL,
            entity_id="goal_1",
            operation="update",
            changed_keys=["status"],
            delta={"status": "completed"},
            source_agent="executor",
        )
        assert du.entity_id == "goal_1"
        assert du.operation == "update"
        assert du.source_agent == "executor"

    def test_generates_event_id(self):
        """Auto-generates event_id."""
        du = DeltaUpdate(
            entity_type=EntityType.INTENT,
            entity_id="x",
            operation="create",
            changed_keys=[],
            delta={},
            source_agent="test",
        )
        assert du.event_id is not None

    def test_generates_timestamp(self):
        """Auto-generates timestamp."""
        du = DeltaUpdate(
            entity_type=EntityType.INTENT,
            entity_id="x",
            operation="create",
            changed_keys=[],
            delta={},
            source_agent="test",
        )
        assert isinstance(du.timestamp, int)


class TestAgentStateModel:
    """AgentState model contract."""

    def test_has_user_query(self):
        """Has user_query str field."""
        state = AgentState(user_query="test")
        assert state.user_query == "test"

    def test_has_intent_chain(self):
        """Has intent_chain field."""
        state = AgentState()
        assert state.intent_chain is None

    def test_has_plan(self):
        """Has plan field."""
        state = AgentState()
        assert state.plan is None

    def test_has_goals_dict(self):
        """Has goals dict field."""
        state = AgentState()
        assert isinstance(state.goals, dict)

    def test_has_execution_results(self):
        """Has execution_results dict."""
        state = AgentState()
        assert isinstance(state.execution_results, dict)

    def test_has_final_response(self):
        """Has final_response str."""
        state = AgentState()
        assert isinstance(state.final_response, str)

    def test_has_messages_list(self):
        """Has messages list."""
        state = AgentState()
        assert isinstance(state.messages, list)

    def test_has_metadata(self):
        """Has metadata dict."""
        state = AgentState()
        assert isinstance(state.metadata, dict)

    def test_has_needs_approval(self):
        """Has needs_approval bool."""
        state = AgentState()
        assert state.needs_approval is False

    def test_has_interrupted(self):
        """Has interrupted bool."""
        state = AgentState()
        assert state.interrupted is False


class TestFinalResponseModel:
    """FinalResponse model contract."""

    def test_has_response(self):
        """Has response str."""
        fr = FinalResponse(response="Done")
        assert fr.response == "Done"

    def test_has_intent_chain(self):
        """Has intent_chain field."""
        fr = FinalResponse(response="x")
        assert fr.intent_chain is None

    def test_has_goals_counts(self):
        """Has goals_completed and goals_failed."""
        fr = FinalResponse(response="x", goals_completed=2, goals_failed=0)
        assert fr.goals_completed == 2
        assert fr.goals_failed == 0

    def test_has_token_usage(self):
        """Has token_usage dict."""
        fr = FinalResponse(response="x", token_usage={"prompt": 100})
        assert fr.token_usage == {"prompt": 100}


class TestEnumContracts:
    """Enum value contracts."""

    def test_entity_type_values(self):
        """EntityType has INTENT, GOAL, PLAN, STATUS."""
        assert EntityType.INTENT.value == "Intent"
        assert EntityType.GOAL.value == "Goal"
        assert EntityType.PLAN.value == "Plan"
        assert EntityType.STATUS.value == "Status"

    def test_intent_status_values(self):
        """IntentStatus has expected values."""
        assert IntentStatus.ACTIVE.value == "active"
        assert IntentStatus.COMPLETED.value == "completed"
        assert IntentStatus.ABANDONED.value == "abandoned"

    def test_goal_status_values(self):
        """GoalStatus has expected values."""
        assert GoalStatus.PENDING.value == "pending"
        assert GoalStatus.IN_PROGRESS.value == "in_progress"
        assert GoalStatus.COMPLETED.value == "completed"
        assert GoalStatus.FAILED.value == "failed"

    def test_execution_status_values(self):
        """ExecutionStatusValue has expected values."""
        assert ExecutionStatusValue.QUEUED.value == "queued"
        assert ExecutionStatusValue.RUNNING.value == "running"
        assert ExecutionStatusValue.WAITING.value == "waiting"
        assert ExecutionStatusValue.COMPLETED.value == "completed"
        assert ExecutionStatusValue.FAILED.value == "failed"


class TestStreamChunkModel:
    """StreamChunk model contract."""

    def test_has_type_field(self):
        """Has type str field."""
        chunk = StreamChunk(type="result")
        assert chunk.type == "result"

    def test_has_data_field(self):
        """Has data optional dict."""
        chunk = StreamChunk(type="result", data={"key": "value"})
        assert chunk.data == {"key": "value"}

    def test_has_error_field(self):
        """Has error optional str."""
        chunk = StreamChunk(type="error", error="Something went wrong")
        assert chunk.error == "Something went wrong"


class TestExecutionStatusModel:
    """ExecutionStatus model contract."""

    def test_has_required_fields(self):
        """Has goal_id, executor_id, status."""
        es = ExecutionStatus(goal_id="g1", executor_id="e1")
        assert es.goal_id == "g1"
        assert es.executor_id == "e1"

    def test_status_defaults_to_queued(self):
        """Status defaults to QUEUED."""
        es = ExecutionStatus(goal_id="g1", executor_id="e1")
        assert es.status == ExecutionStatusValue.QUEUED

    def test_has_progress(self):
        """Has progress int."""
        es = ExecutionStatus(goal_id="g1", executor_id="e1", progress=50)
        assert es.progress == 50

    def test_has_last_update(self):
        """Has last_update timestamp."""
        es = ExecutionStatus(goal_id="g1", executor_id="e1")
        assert isinstance(es.last_update, int)
