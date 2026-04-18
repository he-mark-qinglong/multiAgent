"""Tests for binding_manager.py - BindingManager for loading and executing bindings."""

import json
import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock

from core.binding_manager import (
    BindingManager,
    DEFAULT_BINDINGS_DIR,
    get_binding_manager,
    set_binding_manager,
    init_binding_manager,
)
from core.binding_schema import BindingConfig, PrimaryConfig, ActionDef, ActionSelector
from core.binding_executor import set_tool_registry, ExecutionResult


class MockToolResult:
    """Mock tool result."""
    def __init__(self, description="ok", state=None):
        self.description = description
        self.state = state or {}


class TestBindingManager:
    """Tests for BindingManager."""

    def setup_method(self):
        """Set up fresh manager for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = BindingManager(bindings_dir=self.temp_dir)
        set_tool_registry(None)

    def teardown_method(self):
        """Clean up temp dir."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_binding_file(self, goal_type: str, data: dict) -> Path:
        """Create a binding JSON file."""
        file_path = Path(self.temp_dir) / f"{goal_type}.json"
        with open(file_path, "w") as f:
            json.dump(data, f)
        return file_path

    def test_load_bindings_from_dir_empty(self):
        """Load from empty directory."""
        results = self.manager.load_bindings_from_dir(silent=True)
        assert results == {}
        assert self.manager.get_binding_count() == 0

    def test_load_bindings_from_dir_single(self):
        """Load single binding."""
        self._create_binding_file("climate_control", {
            "goal_type": "climate_control",
            "version": "v1",
            "primary": {
                "tool": "climate_control",
                "action_selector": [
                    {"default": "get_status"}
                ],
                "actions": {
                    "get_status": {"params": {}}
                }
            }
        })

        results = self.manager.load_bindings_from_dir()
        assert results["climate_control"] is True
        assert self.manager.get_binding_count() == 1

        binding = self.manager.get_binding("climate_control")
        assert binding is not None
        assert binding.goal_type == "climate_control"
        assert binding.primary.tool == "climate_control"

    def test_load_bindings_from_dir_multiple(self):
        """Load multiple bindings."""
        self._create_binding_file("climate_control", {
            "goal_type": "climate_control", "primary": {"tool": "climate"}
        })
        self._create_binding_file("navigation", {
            "goal_type": "navigation", "primary": {"tool": "nav"}
        })
        self._create_binding_file("music", {
            "goal_type": "music", "primary": {"tool": "music"}
        })

        results = self.manager.load_bindings_from_dir()
        assert results["climate_control"] is True
        assert results["navigation"] is True
        assert results["music"] is True
        assert self.manager.get_binding_count() == 3

    def test_load_bindings_invalid_json(self):
        """Invalid JSON file fails gracefully."""
        bad_file = Path(self.temp_dir) / "bad.json"
        bad_file.write_text("{ invalid json }")

        results = self.manager.load_bindings_from_dir()
        assert results["bad"] is False
        assert self.manager.get_binding_count() == 0

    def test_register_binding(self):
        """Register binding in memory."""
        binding = BindingConfig(
            goal_type="test",
            primary=PrimaryConfig(
                tool="test_tool",
                action_selector=[ActionSelector(default="action")],
                actions={"action": ActionDef(params={})}
            )
        )

        self.manager.register_binding(binding)
        assert self.manager.get_binding("test") is binding

    def test_register_binding_from_dict(self):
        """Register binding from dict."""
        data = {
            "goal_type": "test_from_dict",
            "primary": {
                "tool": "test_tool",
                "action_selector": [{"default": "action"}],
                "actions": {"action": {"params": {}}}
            }
        }

        binding = self.manager.register_binding_from_dict(data)
        assert binding.goal_type == "test_from_dict"
        assert self.manager.get_binding("test_from_dict") is binding

    def test_list_bindings(self):
        """List all registered bindings."""
        self._create_binding_file("a", {"goal_type": "a", "primary": {"tool": "a"}})
        self._create_binding_file("b", {"goal_type": "b", "primary": {"tool": "b"}})
        self._create_binding_file("c", {"goal_type": "c", "primary": {"tool": "c"}})

        self.manager.load_bindings_from_dir()
        bindings = self.manager.list_bindings()

        assert len(bindings) == 3
        assert set(bindings) == {"a", "b", "c"}

    def test_execute_binding_success(self):
        """Execute binding successfully."""
        # Create mock registry
        registry = Mock()
        registry.call_tool = Mock(return_value=MockToolResult("AC on", {"temp": 24}))
        set_tool_registry(registry)

        # Create manager with test dir
        manager = BindingManager(bindings_dir=self.temp_dir)
        self._create_binding_file("climate", {
            "goal_type": "climate",
            "primary": {
                "tool": "climate_control",
                "action_selector": [{"default": "control"}],
                "actions": {"control": {"params": {}}}
            }
        })
        manager.load_bindings_from_dir()

        # Execute
        result = manager.execute_binding("climate", {"entities": {}})

        assert result.success is True
        assert result.tool == "climate_control"
        assert result.action == "control"

    def test_execute_binding_not_found(self):
        """Execute non-existent binding."""
        result = self.manager.execute_binding("nonexistent", {"entities": {}})

        assert result.success is False
        assert "No binding found" in result.state["error"]

    def test_reload_bindings(self):
        """Reload bindings from disk."""
        self._create_binding_file("first", {
            "goal_type": "first", "primary": {"tool": "first"}
        })
        self.manager.load_bindings_from_dir()
        assert self.manager.get_binding_count() == 1

        # Add another file
        self._create_binding_file("second", {
            "goal_type": "second", "primary": {"tool": "second"}
        })

        # Reload
        results = self.manager.reload_bindings()
        assert results["first"] is True
        assert results["second"] is True
        assert self.manager.get_binding_count() == 2

    def test_execute_binding_with_context(self):
        """Execute binding with proper context passing."""
        captured_params = {}

        def capture_call(t, a, **kw):
            captured_params.update(kw)
            return MockToolResult("Done", {})

        registry = Mock()
        registry.call_tool = capture_call
        set_tool_registry(registry)

        manager = BindingManager(bindings_dir=self.temp_dir)
        self._create_binding_file("test", {
            "goal_type": "test",
            "primary": {
                "tool": "test_tool",
                "action_selector": [{"default": "do_it"}],
                "actions": {
                    "do_it": {
                        "params": {
                            "temp": {"from": "entities.temperature"},
                            "loc": {"from": "entities.location"}
                        }
                    }
                }
            }
        })
        manager.load_bindings_from_dir()

        context = {
            "entities": {
                "temperature": 25,
                "location": "Beijing"
            }
        }
        result = manager.execute_binding("test", context)

        assert result.success is True
        assert captured_params.get("temp") == 25
        assert captured_params.get("loc") == "Beijing"


class TestGlobalManager:
    """Tests for global manager functions."""

    def setup_method(self):
        """Reset global manager."""
        set_binding_manager(None)

    def teardown_method(self):
        """Clean up global."""
        set_binding_manager(None)

    def test_get_binding_manager_creates_default(self):
        """Get manager creates default if not set."""
        manager = get_binding_manager()
        assert manager is not None
        assert isinstance(manager, BindingManager)

    def test_get_binding_manager_returns_same(self):
        """Get manager returns same instance."""
        m1 = get_binding_manager()
        m2 = get_binding_manager()
        assert m1 is m2

    def test_set_binding_manager(self):
        """Set custom manager."""
        custom = BindingManager()
        set_binding_manager(custom)
        assert get_binding_manager() is custom

    def test_init_binding_manager(self):
        """Init manager with options."""
        temp_dir = tempfile.mkdtemp()
        try:
            registry = Mock()
            manager = init_binding_manager(
                bindings_dir=temp_dir,
                tool_registry=registry
            )

            assert manager is not None
            assert get_binding_manager() is manager
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestDefaultBindingsDir:
    """Test default bindings directory."""

    def test_default_is_expanded(self):
        """Default dir expands user path."""
        manager = BindingManager()
        assert manager.bindings_dir == Path(DEFAULT_BINDINGS_DIR).expanduser()
        assert manager.bindings_dir.is_absolute()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
