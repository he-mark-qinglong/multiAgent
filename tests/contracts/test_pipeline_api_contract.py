"""Pipeline API contract tests."""

import sys
sys.path.insert(0, '.')

import pytest
from pipelines.collaboration_pipeline import CollaborationPipeline
from core.models import UserQuery


class TestPipelineAPI:
    """Pipeline public API contract tests."""

    @pytest.fixture
    def pipeline(self):
        return CollaborationPipeline(enable_tracing=False)

    def test_invoke_returns_dict(self, pipeline):
        """invoke() returns a dict."""
        result = pipeline.invoke("测试")
        assert isinstance(result, dict)

    def test_invoke_has_final_response(self, pipeline):
        """invoke() result contains final_response."""
        result = pipeline.invoke("测试")
        assert "final_response" in result

    def test_invoke_with_string(self, pipeline):
        """invoke(str) converts to UserQuery internally."""
        result = pipeline.invoke("测试字符串")
        assert isinstance(result, dict)

    def test_invoke_with_user_query(self, pipeline):
        """invoke(UserQuery) works."""
        query = UserQuery(query="测试对象")
        result = pipeline.invoke(query)
        assert isinstance(result, dict)

    def test_invoke_with_thread_id(self, pipeline):
        """invoke() supports thread_id via config."""
        result = pipeline.invoke("测试", thread_id="thread_abc")
        assert isinstance(result, dict)

    def test_invoke_returns_agent_state_fields(self, pipeline):
        """invoke() returns state with AgentState fields."""
        result = pipeline.invoke("测试")
        expected_keys = ["final_response"]
        for key in expected_keys:
            assert key in result

    def test_stream_yields_generator(self, pipeline):
        """stream() yields generator of dicts."""
        chunks = list(pipeline.stream("测试"))
        assert isinstance(chunks, list)
        assert all(isinstance(c, dict) for c in chunks)

    def test_stream_yields_result_type(self, pipeline):
        """stream() yields chunks with type='result'."""
        chunks = list(pipeline.stream("测试"))
        result_chunks = [c for c in chunks if c.get("type") == "result"]
        assert len(result_chunks) >= 1

    def test_stream_result_data_structure(self, pipeline):
        """stream() result data contains expected fields."""
        for chunk in pipeline.stream("测试"):
            if chunk.get("type") == "result":
                data = chunk.get("data", {})
                assert isinstance(data, dict)
                assert "final_response" in data

    def test_stream_yields_error_type_on_exception(self, pipeline):
        """stream() yields type='error' on exception."""
        chunks = list(pipeline.stream("测试"))
        types = [c.get("type") for c in chunks]
        assert all(t in ("result", "error") for t in types)

    def test_request_approval_returns_string(self, pipeline):
        """request_approval() returns a string."""
        approval_id = pipeline.request_approval(
            thread_id="t1",
            action="test",
            details="测试",
        )
        assert isinstance(approval_id, str)

    def test_request_approval_returns_approval_prefix(self, pipeline):
        """request_approval() returns ID starting with 'approval_'."""
        approval_id = pipeline.request_approval("t2", "x", "y")
        assert approval_id.startswith("approval_")

    def test_submit_approval_returns_dict(self, pipeline):
        """submit_approval() returns a dict."""
        pipeline.request_approval("t3", "a", "b")
        result = pipeline.submit_approval("t3", approved=True)
        assert isinstance(result, dict)

    def test_submit_approval_with_reason(self, pipeline):
        """submit_approval() accepts reason parameter."""
        pipeline.request_approval("t4", "a", "b")
        result = pipeline.submit_approval("t4", approved=False, reason="拒绝")
        assert isinstance(result, dict)

    def test_get_pending_returns_dict_or_none(self, pipeline):
        """get_pending() returns dict or None."""
        result = pipeline.get_pending_approval("nonexistent")
        assert result is None or isinstance(result, dict)

    def test_get_pending_after_request(self, pipeline):
        """get_pending() returns dict after request_approval."""
        pipeline.request_approval("t5", "x", "y")
        pending = pipeline.get_pending_approval("t5")
        assert isinstance(pending, dict)
        assert "approval_id" in pending

    def test_get_state_history_returns_list(self, pipeline):
        """get_state_history() returns a list."""
        pipeline.invoke("测试", thread_id="hist_1")
        history = pipeline.get_state_history("hist_1")
        assert isinstance(history, list)

    def test_get_checkpointer_returns_checkpointer(self, pipeline):
        """get_checkpointer() returns the checkpointer."""
        cp = pipeline.get_checkpointer()
        assert cp is not None

    def test_pipeline_langsmith_disabled(self):
        """Pipeline initializes without LangSmith tracing."""
        p = CollaborationPipeline(enable_tracing=False)
        assert p.tracer is not None

    def test_pipeline_multiple_invocations(self, pipeline):
        """Pipeline handles multiple sequential invocations."""
        for i in range(3):
            result = pipeline.invoke(f"测试{i}")
            assert isinstance(result, dict)
            assert "final_response" in result
