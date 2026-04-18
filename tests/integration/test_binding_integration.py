"""Integration tests for the complete binding flow.

These tests verify that:
1. Bindings load correctly from disk
2. BindingExecutor correctly executes bindings
3. The full flow from goal_type to execution result works
"""

import json
import os
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock

from core.binding_manager import BindingManager
from core.binding_schema import BindingConfig
from core.binding_executor import BindingExecutor, set_tool_registry
from core.condition_evaluator import ConditionEvaluator
from core.param_mapper import ParamMapper


class MockToolResult:
    """Mock tool result with description and state."""
    def __init__(self, description="ok", state=None):
        self.description = description
        self.state = state or {}


class TestClimateControlBinding:
    """Integration tests for climate_control binding."""

    def setup_method(self):
        """Set up test with climate_control binding."""
        self.temp_dir = tempfile.mkdtemp()
        self.bindings_dir = Path(self.temp_dir) / "bindings"
        self.bindings_dir.mkdir()

        # Create climate_control binding
        self._create_climate_binding()

        # Create mock registry
        self.registry = Mock()
        self.registry.call_tool = Mock(side_effect=self._mock_call)
        set_tool_registry(self.registry)

        # Create manager
        self.manager = BindingManager(bindings_dir=str(self.bindings_dir))
        self.manager.load_bindings_from_dir()

    def teardown_method(self):
        """Clean up."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        set_tool_registry(None)

    def _create_climate_binding(self):
        """Create the climate_control binding JSON."""
        binding_data = {
            "goal_type": "climate_control",
            "version": "v1",
            "description": "Climate control binding",
            "primary": {
                "tool": "climate_control",
                "action_selector": [
                    {
                        "when": {
                            "in": [
                                {"var": "intent.action"},
                                ["turn_on", "turn_off", "set_temperature"]
                            ]
                        },
                        "action": "control"
                    },
                    {"default": "get_status"}
                ],
                "actions": {
                    "control": {
                        "params": {
                            "temperature": {"from": "entities.temperature", "type": "int", "default": 24},
                            "fan_speed": {"from": "entities.fan_speed", "type": "int", "default": 2},
                            "power": {"from": "intent.action"},
                            "mode": {"from": "entities.mode", "type": "str", "default": "auto"}
                        },
                        "idempotent": True
                    },
                    "get_status": {
                        "params": {},
                        "idempotent": True
                    }
                }
            },
            "secondary": [
                {
                    "description": "Fallback",
                    "tool": "mock_climate",
                    "action": "control",
                    "params": {}
                }
            ],
            "retry": {
                "enabled": True,
                "max_attempts": 3,
                "delay_ms": 10,
                "backoff": "fixed",
                "retry_on": ["NetworkError"]
            },
            "error_strategy": "fallback_then_error"
        }

        file_path = self.bindings_dir / "climate_control.json"
        with open(file_path, "w") as f:
            json.dump(binding_data, f)

    def _mock_call(self, tool, action, **params):
        """Mock tool call."""
        if tool == "climate_control" and action == "control":
            return MockToolResult(
                description=f"Climate set to {params.get('temperature', '?')}C, mode {params.get('mode', 'auto')}",
                state={"temperature": params.get("temperature", 24), "mode": params.get("mode", "auto")}
            )
        elif tool == "climate_control" and action == "get_status":
            return MockToolResult(
                description="Climate: 24C, auto mode, fan speed 2",
                state={"temperature": 24, "mode": "auto", "fan_speed": 2}
            )
        else:
            return MockToolResult(
                description=f"{tool}.{action} result",
                state={"tool": tool, "action": action}
            )

    def test_binding_loaded(self):
        """Binding loaded from disk."""
        assert self.manager.get_binding_count() == 1
        binding = self.manager.get_binding("climate_control")
        assert binding is not None
        assert binding.goal_type == "climate_control"
        assert binding.primary.tool == "climate_control"

    def test_execute_with_temperature(self):
        """Execute with temperature parameter."""
        context = {
            "intent": {"action": "set_temperature"},
            "entities": {"temperature": 26, "mode": "cool"}
        }

        result = self.manager.execute_binding("climate_control", context)

        assert result.success is True
        assert result.tool == "climate_control"
        assert result.action == "control"
        assert "26" in result.output

    def test_execute_get_status(self):
        """Execute get_status (default action)."""
        context = {
            "intent": {"action": "query_status"},
            "entities": {}
        }

        result = self.manager.execute_binding("climate_control", context)

        assert result.success is True
        assert result.action == "get_status"

    def test_execute_with_mock_fallback(self):
        """Primary fails, fallback to mock."""
        # Track call count to differentiate primary vs fallback
        call_count = {"count": 0}

        def selective_mock(tool, action, **params):
            call_count["count"] += 1
            if call_count["count"] == 1:
                raise Exception("Primary failed")
            # Second call is the fallback
            return MockToolResult("Fallback succeeded", {})

        self.registry.call_tool = Mock(side_effect=selective_mock)

        context = {
            "intent": {"action": "turn_on"},
            "entities": {"temperature": 22}
        }

        result = self.manager.execute_binding("climate_control", context)

        assert result.success is True
        assert result.tool == "mock_climate"


class TestNavigationBinding:
    """Integration tests for navigation binding."""

    def setup_method(self):
        """Set up test with navigation binding."""
        self.temp_dir = tempfile.mkdtemp()
        self.bindings_dir = Path(self.temp_dir) / "bindings"
        self.bindings_dir.mkdir()

        self._create_navigation_binding()

        self.registry = Mock()
        self.registry.call_tool = Mock(return_value=MockToolResult("Navigation set", {}))
        set_tool_registry(self.registry)

        self.manager = BindingManager(bindings_dir=str(self.bindings_dir))
        self.manager.load_bindings_from_dir()

    def teardown_method(self):
        """Clean up."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        set_tool_registry(None)

    def _create_navigation_binding(self):
        """Create the navigation binding JSON."""
        binding_data = {
            "goal_type": "navigation",
            "version": "v1",
            "primary": {
                "tool": "navigation",
                "action_selector": [
                    {"when": {"==": [{"var": "intent.action"}, "navigate"]}, "action": "navigate"},
                    {"default": "get_directions"}
                ],
                "actions": {
                    "navigate": {
                        "params": {
                            "destination": {"from": "entities.destination", "type": "str"}
                        }
                    },
                    "get_directions": {"params": {}}
                }
            }
        }

        file_path = self.bindings_dir / "navigation.json"
        with open(file_path, "w") as f:
            json.dump(binding_data, f)

    def test_navigation_binding_loads(self):
        """Navigation binding loads correctly."""
        assert self.manager.get_binding_count() == 1
        binding = self.manager.get_binding("navigation")
        assert binding is not None

    def test_navigate_execute(self):
        """Navigate action executes."""
        context = {
            "intent": {"action": "navigate"},
            "entities": {"destination": "Airport"}
        }

        result = self.manager.execute_binding("navigation", context)

        assert result.success is True
        assert result.tool == "navigation"


class TestMultipleBindings:
    """Tests for loading multiple bindings."""

    def setup_method(self):
        """Set up with multiple bindings."""
        self.temp_dir = tempfile.mkdtemp()
        self.bindings_dir = Path(self.temp_dir) / "bindings"
        self.bindings_dir.mkdir()

        for goal_type in ["climate_control", "navigation", "music_control", "weather", "news"]:
            binding_data = {
                "goal_type": goal_type,
                "version": "v1",
                "primary": {
                    "tool": goal_type,
                    "action_selector": [{"default": "get_status"}],
                    "actions": {"get_status": {"params": {}}}
                }
            }
            file_path = self.bindings_dir / f"{goal_type}.json"
            with open(file_path, "w") as f:
                json.dump(binding_data, f)

        registry = Mock()
        registry.call_tool = Mock(return_value=MockToolResult("ok", {}))
        set_tool_registry(registry)

        self.manager = BindingManager(bindings_dir=str(self.bindings_dir))
        self.manager.load_bindings_from_dir()

    def teardown_method(self):
        """Clean up."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        set_tool_registry(None)

    def test_loads_all_bindings(self):
        """All bindings load."""
        assert self.manager.get_binding_count() == 5

    def test_lists_all_bindings(self):
        """List shows all bindings."""
        bindings = self.manager.list_bindings()
        assert len(bindings) == 5
        assert set(bindings) == {"climate_control", "navigation", "music_control", "weather", "news"}

    def test_execute_each_binding(self):
        """Each binding executes correctly."""
        for goal_type in ["climate_control", "navigation", "music_control", "weather", "news"]:
            result = self.manager.execute_binding(goal_type, {"entities": {}})
            assert result.success is True, f"Failed for {goal_type}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
