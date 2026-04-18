"""Tests for binding_executor.py - BindingExecutor with fallback and retry."""

import pytest
from unittest.mock import Mock, MagicMock
from core.binding_executor import (
    BindingExecutor,
    ExecutionResult,
    ToolExecutionError,
    set_tool_registry,
    get_tool_registry,
)
from core.binding_schema import (
    BindingConfig,
    PrimaryConfig,
    SecondaryConfig,
    RetryConfig,
    ActionSelector,
    ActionDef,
)


class MockToolResult:
    """Mock tool result object."""
    def __init__(self, description="ok", state=None):
        self.description = description
        self.state = state or {}


class TestBindingExecutor:
    """Tests for BindingExecutor."""

    def setup_method(self):
        """Set up fresh executor for each test."""
        self.executor = BindingExecutor()
        # Reset registry
        set_tool_registry(None)

    def teardown_method(self):
        """Clean up registry after each test."""
        set_tool_registry(None)

    def _make_registry(self, results=None):
        """Create a mock registry.

        Args:
            results: dict of {(tool, action): result_or_exception}

        Returns:
            Mock registry with call_tool method
        """
        registry = Mock()
        registry.call_tool = Mock(side_effect=lambda t, a, **kw: self._get_result(t, a, results or {}))
        set_tool_registry(registry)
        return registry

    def _get_result(self, tool, action, results):
        """Get result from mock results dict."""
        key = (tool, action)
        if key in results:
            val = results[key]
            if isinstance(val, Exception):
                raise val
            return val
        return MockToolResult(f"{tool}.{action} result")

    def test_execute_success_simple(self):
        """Simple successful execution."""
        registry = self._make_registry({
            ("climate_control", "control"): MockToolResult("AC on", {"temp": 24})
        })

        binding = BindingConfig(
            goal_type="climate_control",
            primary=PrimaryConfig(
                tool="climate_control",
                action_selector=[
                    ActionSelector(when=None, action=None, default="control")
                ],
                actions={"control": ActionDef(params={})}
            )
        )

        context = {"entities": {}}
        result = self.executor.execute(binding, context)

        assert result.success is True
        assert result.tool == "climate_control"
        assert result.action == "control"

    def test_execute_with_condition_matching(self):
        """Action selection based on condition matching."""
        registry = self._make_registry({
            ("climate_control", "control"): MockToolResult("Cooling", {"mode": "cool"})
        })

        binding = BindingConfig(
            goal_type="climate_control",
            primary=PrimaryConfig(
                tool="climate_control",
                action_selector=[
                    ActionSelector(when={"==": [{"var": "intent.action"}, "turn_on"]}, action="control"),
                    ActionSelector(when=None, action=None, default="get_status")
                ],
                actions={
                    "control": ActionDef(params={}),
                    "get_status": ActionDef(params={})
                }
            )
        )

        context = {"intent": {"action": "turn_on"}, "entities": {}}
        result = self.executor.execute(binding, context)

        assert result.success is True
        assert result.action == "control"

    def test_execute_condition_not_matched_uses_default(self):
        """When condition doesn't match, default is selected."""
        registry = self._make_registry({
            ("climate_control", "get_status"): MockToolResult("Status: off", {})
        })

        binding = BindingConfig(
            goal_type="climate_control",
            primary=PrimaryConfig(
                tool="climate_control",
                action_selector=[
                    ActionSelector(when={"==": [{"var": "intent.action"}, "turn_on"]}, action="control"),
                    ActionSelector(when=None, action=None, default="get_status")
                ],
                actions={
                    "control": ActionDef(params={}),
                    "get_status": ActionDef(params={})
                }
            )
        )

        context = {"intent": {"action": "unknown"}, "entities": {}}
        result = self.executor.execute(binding, context)

        assert result.success is True
        assert result.action == "get_status"

    def test_execute_no_primary_uses_secondary(self):
        """When no primary config, secondary is used."""
        registry = self._make_registry({
            ("fallback_tool", "fallback"): MockToolResult("Fallback worked", {})
        })

        binding = BindingConfig(
            goal_type="orphan_goal",
            primary=None,
            secondary=[
                SecondaryConfig(tool="fallback_tool", action="fallback", params={})
            ]
        )

        context = {"entities": {}}
        result = self.executor.execute(binding, context)

        assert result.success is True
        assert result.tool == "fallback_tool"

    def test_execute_primary_failure_uses_secondary(self):
        """Primary failure triggers secondary fallback."""
        registry = self._make_registry({
            ("primary_tool", "action"): Exception("Primary failed"),
            ("fallback_tool", "fallback"): MockToolResult("Fallback succeeded", {})
        })

        binding = BindingConfig(
            goal_type="with_fallback",
            primary=PrimaryConfig(
                tool="primary_tool",
                action_selector=[ActionSelector(when=None, action=None, default="action")],
                actions={"action": ActionDef(params={})}
            ),
            secondary=[
                SecondaryConfig(tool="fallback_tool", action="fallback", params={})
            ]
        )

        context = {"entities": {}}
        result = self.executor.execute(binding, context)

        assert result.success is True
        assert result.tool == "fallback_tool"

    def test_execute_all_fail_then_error(self):
        """All primary and secondary fail, error_strategy applied."""
        registry = self._make_registry({
            ("primary_tool", "action"): Exception("Primary failed"),
            ("fallback_tool", "fallback"): Exception("Fallback also failed")
        })

        binding = BindingConfig(
            goal_type="all_fail",
            primary=PrimaryConfig(
                tool="primary_tool",
                action_selector=[ActionSelector(when=None, action=None, default="action")],
                actions={"action": ActionDef(params={})}
            ),
            secondary=[
                SecondaryConfig(tool="fallback_tool", action="fallback", params={})
            ],
            error_strategy="fallback_then_error"
        )

        context = {"entities": {}}
        result = self.executor.execute(binding, context)

        assert result.success is False
        assert "failed" in result.state.get("error", "").lower()

    def test_execute_with_retry(self):
        """Retry logic on transient failure."""
        call_count = {"count": 0}

        def mock_call(t, a, **kw):
            call_count["count"] += 1
            if call_count["count"] < 3:
                raise Exception("Transient error")
            return MockToolResult("Succeeded on retry", {})

        registry = Mock()
        registry.call_tool = mock_call
        set_tool_registry(registry)

        binding = BindingConfig(
            goal_type="retry_test",
            primary=PrimaryConfig(
                tool="some_tool",
                action_selector=[ActionSelector(when=None, action=None, default="action")],
                actions={"action": ActionDef(params={})}
            ),
            retry=RetryConfig(
                enabled=True,
                max_attempts=5,
                delay_ms=1,  # minimal delay for test
                backoff="fixed",
                retry_on=["Transient"]  # match on "Transient" in error
            )
        )

        context = {"entities": {}}
        result = self.executor.execute(binding, context)

        assert result.success is True
        assert call_count["count"] == 3

    def test_execute_no_matching_action(self):
        """Action referenced but not in actions block."""
        registry = self._make_registry({})

        binding = BindingConfig(
            goal_type="missing_action",
            primary=PrimaryConfig(
                tool="some_tool",
                action_selector=[ActionSelector(when=None, action=None, default="nonexistent_action")],
                actions={"existing": ActionDef(params={})}
            )
        )

        context = {"entities": {}}
        result = self.executor.execute(binding, context)

        assert result.success is False
        assert "not found" in result.state.get("error", "").lower()

    def test_execute_with_param_mapping(self):
        """Parameters are mapped from context."""
        captured_params = {}

        def capture_call(t, a, **kw):
            captured_params.update(kw)
            return MockToolResult("Done", {})

        registry = Mock()
        registry.call_tool = capture_call
        set_tool_registry(registry)

        binding = BindingConfig(
            goal_type="param_test",
            primary=PrimaryConfig(
                tool="test_tool",
                action_selector=[ActionSelector(when=None, action=None, default="do_it")],
                actions={
                    "do_it": ActionDef(params={
                        "temperature": {"from": "entities.temperature"},
                        "location": {"from": "entities.city", "default": "Beijing"}
                    })
                }
            )
        )

        context = {"entities": {"temperature": 25, "city": "Shanghai"}}
        result = self.executor.execute(binding, context)

        assert result.success is True
        assert captured_params.get("temperature") == 25
        assert captured_params.get("location") == "Shanghai"


class TestExecutionResult:
    """Tests for ExecutionResult."""

    def test_success_result(self):
        """Create and verify success result."""
        result = ExecutionResult(
            success=True,
            tool="test_tool",
            action="test_action",
            output="Test passed",
            state={"key": "value"}
        )

        assert result.success is True
        assert result.tool == "test_tool"
        assert result.action == "test_action"
        assert result.output == "Test passed"
        assert result.state["key"] == "value"

    def test_error_result(self):
        """Create and verify error result."""
        result = ExecutionResult(
            success=False,
            tool="test_tool",
            action="test_action",
            output="",
            state={"error": "Something went wrong"}
        )

        assert result.success is False
        assert result.state["error"] == "Something went wrong"

    def test_to_dict(self):
        """Convert to dictionary."""
        result = ExecutionResult(
            success=True,
            tool="tool",
            action="action",
            output="out",
            state={"a": 1}
        )

        d = result.to_dict()
        assert d["success"] is True
        assert d["tool"] == "tool"
        assert d["action"] == "action"
        assert d["output"] == "out"
        assert d["state"]["a"] == 1

    def test_repr(self):
        """String representation."""
        success = ExecutionResult(success=True, tool="t", action="a")
        failed = ExecutionResult(success=False, tool="t", action="a")

        assert "SUCCESS" in repr(success)
        assert "FAILED" in repr(failed)


class TestToolExecutionError:
    """Tests for ToolExecutionError."""

    def test_error_attributes(self):
        """Error has correct attributes."""
        error = ToolExecutionError("tool", "action", "reason text", is_retryable=True)

        assert error.tool == "tool"
        assert error.action == "action"
        assert error.reason == "reason text"
        assert error.is_retryable is True
        assert "tool.action failed" in str(error)

    def test_non_retryable_error(self):
        """Non-retryable error."""
        error = ToolExecutionError("x", "y", "error", is_retryable=False)
        assert error.is_retryable is False


class TestActionSelection:
    """Tests for action selection logic."""

    def setup_method(self):
        self.executor = BindingExecutor()
        set_tool_registry(None)

    def test_first_matching_wins(self):
        """First matching when clause is selected."""
        primary = PrimaryConfig(
            tool="t",
            action_selector=[
                ActionSelector(when={"==": [{"var": "x"}, 1]}, action="action1"),
                ActionSelector(when={"==": [{"var": "x"}, 2]}, action="action2"),
                ActionSelector(when=None, action=None, default="default")
            ],
            actions={"action1": ActionDef(), "action2": ActionDef(), "default": ActionDef()}
        )

        selected = self.executor._select_action(primary, {"x": 1})
        assert selected == "action1"

        selected = self.executor._select_action(primary, {"x": 2})
        assert selected == "action2"

    def test_no_when_default_used(self):
        """When no when matches, default is selected."""
        primary = PrimaryConfig(
            tool="t",
            action_selector=[
                ActionSelector(when={"==": [{"var": "x"}, 1]}, action="action1"),
                ActionSelector(when=None, action=None, default="fallback")
            ],
            actions={"action1": ActionDef(), "fallback": ActionDef()}
        )

        selected = self.executor._select_action(primary, {"x": 999})
        assert selected == "fallback"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
