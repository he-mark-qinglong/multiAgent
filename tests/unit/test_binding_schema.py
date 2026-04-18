"""Tests for binding_schema.py - BindingConfig dataclass schema."""

import pytest
import json
import tempfile
import os
from pathlib import Path


class TestActionSelector:
    """Tests for ActionSelector dataclass."""

    def test_from_dict_minimal(self):
        """Minimal when/default entry."""
        from core.binding_schema import ActionSelector

        data = {"when": {"==": [{"var": "intent.type"}, "climate"]}, "action": "control"}
        selector = ActionSelector.from_dict(data)

        assert selector.when is not None
        assert selector.action == "control"
        assert selector.default is None

    def test_from_dict_default_only(self):
        """Default-only selector (no when condition)."""
        from core.binding_schema import ActionSelector

        data = {"default": "get_status"}
        selector = ActionSelector.from_dict(data)

        assert selector.when is None
        assert selector.action is None
        assert selector.default == "get_status"

    def test_from_dict_empty(self):
        """Empty dict returns defaults."""
        from core.binding_schema import ActionSelector

        selector = ActionSelector.from_dict({})

        assert selector.when is None
        assert selector.action is None
        assert selector.default is None


class TestActionDef:
    """Tests for ActionDef dataclass."""

    def test_from_dict_with_params(self):
        """Action with parameter definitions."""
        from core.binding_schema import ActionDef

        data = {
            "params": {
                "temperature": {"type": "int", "default": 24},
                "fan_speed": {"type": "int", "default": 2}
            },
            "required_params": ["temperature"],
            "idempotent": True
        }
        action = ActionDef.from_dict(data)

        assert action.params["temperature"]["type"] == "int"
        assert action.params["fan_speed"]["default"] == 2
        assert action.required_params == ["temperature"]
        assert action.idempotent is True

    def test_from_dict_defaults(self):
        """Defaults when params not provided."""
        from core.binding_schema import ActionDef

        action = ActionDef.from_dict({})

        assert action.params == {}
        assert action.required_params == []
        assert action.idempotent is False


class TestPrimaryConfig:
    """Tests for PrimaryConfig dataclass."""

    def test_from_dict_with_action_selector(self):
        """Primary config with action_selector and actions."""
        from core.binding_schema import PrimaryConfig

        data = {
            "tool": "climate_control",
            "action_selector": [
                {"when": {"==": [{"var": "intent.action"}, "turn_on"]}, "action": "control"},
                {"default": "get_status"}
            ],
            "actions": {
                "control": {
                    "params": {"temperature": {"type": "int"}, "fan_speed": {"type": "int"}},
                    "idempotent": False
                },
                "get_status": {
                    "params": {},
                    "idempotent": True
                }
            }
        }
        config = PrimaryConfig.from_dict(data)

        assert config.tool == "climate_control"
        assert len(config.action_selector) == 2
        assert config.action_selector[0].action == "control"
        assert config.action_selector[1].default == "get_status"
        assert "control" in config.actions
        assert config.actions["control"].params["temperature"]["type"] == "int"

    def test_from_dict_empty(self):
        """Empty config with defaults."""
        from core.binding_schema import PrimaryConfig

        config = PrimaryConfig.from_dict({})

        assert config.tool == ""
        assert config.action_selector == []
        assert config.actions == {}


class TestSecondaryConfig:
    """Tests for SecondaryConfig dataclass."""

    def test_from_dict_full(self):
        """Full secondary config."""
        from core.binding_schema import SecondaryConfig

        data = {
            "description": "Fallback navigation",
            "tool": "navigation",
            "action": "navigate",
            "params": {"destination": "home"}
        }
        secondary = SecondaryConfig.from_dict(data)

        assert secondary.description == "Fallback navigation"
        assert secondary.tool == "navigation"
        assert secondary.action == "navigate"
        assert secondary.params["destination"] == "home"

    def test_from_dict_defaults(self):
        """Defaults when not provided."""
        from core.binding_schema import SecondaryConfig

        secondary = SecondaryConfig.from_dict({})

        assert secondary.description == ""
        assert secondary.tool == ""
        assert secondary.action == ""
        assert secondary.params == {}


class TestRetryConfig:
    """Tests for RetryConfig dataclass."""

    def test_from_dict_full_retry_config(self):
        """Full retry configuration."""
        from core.binding_schema import RetryConfig

        data = {
            "enabled": True,
            "max_attempts": 5,
            "delay_ms": 200,
            "backoff": "linear",
            "retry_on": ["NetworkError", "TimeoutError"],
            "stop_early_if": ["AuthenticationError"]
        }
        retry = RetryConfig.from_dict(data)

        assert retry.enabled is True
        assert retry.max_attempts == 5
        assert retry.delay_ms == 200
        assert retry.backoff == "linear"
        assert retry.retry_on == ["NetworkError", "TimeoutError"]
        assert retry.stop_early_if == ["AuthenticationError"]

    def test_from_dict_none_returns_defaults(self):
        """None input returns default RetryConfig."""
        from core.binding_schema import RetryConfig

        retry = RetryConfig.from_dict(None)

        assert retry.enabled is False
        assert retry.max_attempts == 3
        assert retry.delay_ms == 100
        assert retry.backoff == "exponential"
        assert retry.retry_on == []
        assert retry.stop_early_if == []

    def test_from_dict_empty_dict(self):
        """Empty dict also returns defaults."""
        from core.binding_schema import RetryConfig

        retry = RetryConfig.from_dict({})

        assert retry.enabled is False


class TestBindingConfig:
    """Tests for BindingConfig dataclass."""

    def test_from_dict_complete_config(self):
        """Complete binding config with all fields."""
        from core.binding_schema import BindingConfig

        data = {
            "goal_type": "climate_control",
            "version": "v1.0",
            "description": "Climate control binding",
            "metadata": {"author": "system", "created": "2026-04-18"},
            "primary": {
                "tool": "climate_control",
                "action_selector": [
                    {"when": {"==": [{"var": "intent.action"}, "turn_on"]}, "action": "control"}
                ],
                "actions": {
                    "control": {"params": {"temperature": {"type": "int"}}, "idempotent": False}
                }
            },
            "secondary": [
                {"description": "Fallback", "tool": "mock_climate", "action": "fallback"}
            ],
            "retry": {
                "enabled": True,
                "max_attempts": 3
            },
            "error_strategy": "fallback_then_error"
        }

        config = BindingConfig.from_dict(data)

        assert config.goal_type == "climate_control"
        assert config.version == "v1.0"
        assert config.description == "Climate control binding"
        assert config.metadata["author"] == "system"
        assert config.primary is not None
        assert config.primary.tool == "climate_control"
        assert len(config.secondary) == 1
        assert config.secondary[0].tool == "mock_climate"
        assert config.retry.enabled is True
        assert config.retry.max_attempts == 3
        assert config.error_strategy == "fallback_then_error"

    def test_from_dict_minimal(self):
        """Minimal config uses defaults."""
        from core.binding_schema import BindingConfig

        data = {
            "goal_type": "weather",
            "primary": {"tool": "get_weather"}
        }
        config = BindingConfig.from_dict(data)

        assert config.goal_type == "weather"
        assert config.version == "v1"
        assert config.primary.tool == "get_weather"
        assert config.secondary == []
        assert config.retry.enabled is False
        assert config.error_strategy == "fallback_then_error"

    def test_from_json(self):
        """Parse from JSON string."""
        from core.binding_schema import BindingConfig

        json_str = json.dumps({
            "goal_type": "navigation",
            "primary": {"tool": "navigation"}
        })
        config = BindingConfig.from_json(json_str)

        assert config.goal_type == "navigation"
        assert config.primary.tool == "navigation"

    def test_from_file(self):
        """Load from JSON file."""
        from core.binding_schema import BindingConfig

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({
                "goal_type": "music_control",
                "primary": {"tool": "music_control"}
            }, f)
            temp_path = f.name

        try:
            config = BindingConfig.from_file(temp_path)
            assert config.goal_type == "music_control"
            assert config.primary.tool == "music_control"
        finally:
            os.unlink(temp_path)

    def test_from_file_not_found(self):
        """File not found raises error."""
        from core.binding_schema import BindingConfig

        with pytest.raises(FileNotFoundError):
            BindingConfig.from_file("/nonexistent/path/config.json")


class TestBindingConfigRoundTrip:
    """Test serialization/deserialization round trips."""

    def test_dict_roundtrip(self):
        """Test that from_dict -> to_dict preserves data."""
        from core.binding_schema import BindingConfig

        original = {
            "goal_type": "test_goal",
            "version": "v2",
            "description": "Test binding",
            "metadata": {"key": "value"},
            "primary": {
                "tool": "test_tool",
                "action_selector": [
                    {"when": {"==": [{"var": "x"}, 1]}, "action": "do_it"},
                    {"default": "default_action"}
                ],
                "actions": {
                    "do_it": {"params": {"a": {"type": "str"}}, "idempotent": True}
                }
            },
            "secondary": [
                {"description": "backup", "tool": "backup_tool", "action": "backup", "params": {}}
            ],
            "retry": {"enabled": True, "max_attempts": 5},
            "error_strategy": "error_only"
        }

        config = BindingConfig.from_dict(original)

        assert config.goal_type == original["goal_type"]
        assert config.version == original["version"]
        assert config.description == original["description"]
        assert config.metadata == original["metadata"]
        assert config.primary.tool == original["primary"]["tool"]
        assert len(config.primary.action_selector) == len(original["primary"]["action_selector"])
        assert config.error_strategy == original["error_strategy"]


class TestSchemaValidation:
    """Tests for schema validation edge cases."""

    def test_missing_primary_returns_none(self):
        """Missing primary field returns None."""
        from core.binding_schema import BindingConfig

        data = {"goal_type": "orphan_goal"}
        config = BindingConfig.from_dict(data)

        assert config.primary is None

    def test_empty_primary_dict_returns_none(self):
        """Empty primary dict returns None."""
        from core.binding_schema import BindingConfig

        data = {"goal_type": "orphan_goal", "primary": {}}
        config = BindingConfig.from_dict(data)

        assert config.primary is None

    def test_action_selector_with_only_when(self):
        """Selector with only 'when' (no action/default) is valid."""
        from core.binding_schema import BindingConfig

        data = {
            "goal_type": "conditional_goal",
            "primary": {
                "tool": "some_tool",
                "action_selector": [
                    {"when": {"exists": "var.thing"}}
                ],
                "actions": {}
            }
        }
        config = BindingConfig.from_dict(data)

        assert len(config.primary.action_selector) == 1
        assert config.primary.action_selector[0].when is not None

    def test_multiple_action_selectors(self):
        """Multiple action selectors in a chain."""
        from core.binding_schema import BindingConfig

        data = {
            "goal_type": "multi_selector",
            "primary": {
                "tool": "tool",
                "action_selector": [
                    {"when": {"==": [{"var": "priority"}, "high"]}, "action": "priority_action"},
                    {"when": {"==": [{"var": "priority"}, "medium"]}, "action": "medium_action"},
                    {"default": "default_action"}
                ],
                "actions": {
                    "priority_action": {"params": {}},
                    "medium_action": {"params": {}},
                    "default_action": {"params": {}}
                }
            }
        }
        config = BindingConfig.from_dict(data)

        assert len(config.primary.action_selector) == 3
        assert config.primary.action_selector[0].action == "priority_action"
        assert config.primary.action_selector[2].default == "default_action"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
