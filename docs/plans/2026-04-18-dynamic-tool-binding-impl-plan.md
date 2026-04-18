# Dynamic Tool Binding Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace hardcoded goal_type → tool/action mapping in executor_agent.py with dynamic JSON binding configuration.

**Architecture:** BindingManager loads JSON configs from configs/bindings/. ConditionEvaluator evaluates nested condition expressions. ParamMapper resolves params from context. BindingExecutor orchestrates primary/secondary execution with retry logic.

**Tech Stack:** Python 3.11+, JSON Schema for validation, inotify/watchdog for hot reload.

---

## Phase 1: Core Infrastructure

### Task 1: Create Project Structure

**Files:**
- Create: `core/binding_manager.py`
- Create: `core/condition_evaluator.py`
- Create: `core/param_mapper.py`
- Create: `core/binding_executor.py`
- Create: `core/binding_schema.py`
- Create: `tools/__init__.py`
- Create: `tools/cli.py`

**Step 1: Create empty module files**

```bash
touch core/binding_manager.py core/condition_evaluator.py core/param_mapper.py core/binding_executor.py core/binding_schema.py tools/__init__.py tools/cli.py
```

**Step 2: Verify structure**

Run: `find core tools -name "*.py" | sort`
Expected: 7 files listed

**Step 3: Commit**

```bash
git add core/binding_manager.py core/condition_evaluator.py core/param_mapper.py core/binding_executor.py core/binding_schema.py tools/__init__.py tools/cli.py
git commit -m "feat: create dynamic binding module structure"
```

---

### Task 2: Implement ConditionEvaluator

**Files:**
- Create: `core/condition_evaluator.py`
- Test: `tests/unit/test_condition_evaluator.py`

**Step 1: Write failing tests**

```python
# tests/unit/test_condition_evaluator.py
import pytest
from core.condition_evaluator import ConditionEvaluator

class TestConditionEvaluator:
    def setup_method(self):
        self.evaluator = ConditionEvaluator()
        self.context = {
            "entities": {"power": True, "temperature": 25, "destination": "机场"},
            "session": {"user_id": "user_1"},
            "query": {"query_id": "q_1"},
            "custom": {},
            "runtime": {}
        }

    def test_var_resolution(self):
        """Test { var: path.to.value } resolution"""
        result = self.evaluator._resolve_var("entities.power", self.context)
        assert result == True

    def test_exists_true(self):
        condition = {"exists": {"var": "entities.temperature"}}
        assert self.evaluator.evaluate(condition, self.context) == True

    def test_exists_false(self):
        condition = {"exists": {"var": "entities.missing"}}
        assert self.evaluator.evaluate(condition, self.context) == False

    def test_eq_true(self):
        condition = {"==": [{"var": "entities.destination"}, "机场"]}
        assert self.evaluator.evaluate(condition, self.context) == True

    def test_eq_false(self):
        condition = {"==": [{"var": "entities.destination"}, "公司"]}
        assert self.evaluator.evaluate(condition, self.context) == False

    def test_and(self):
        condition = {"and": [
            {"exists": {"var": "entities.power"}},
            {"exists": {"var": "entities.temperature"}}
        ]}
        assert self.evaluator.evaluate(condition, self.context) == True

    def test_or(self):
        condition = {"or": [
            {"==": [{"var": "entities.destination"}, "公司"]},
            {"exists": {"var": "entities.temperature"}}
        ]}
        assert self.evaluator.evaluate(condition, self.context) == True

    def test_not(self):
        condition = {"not": {"==": [{"var": "entities.destination"}, "公司"]}}
        assert self.evaluator.evaluate(condition, self.context) == True

    def test_in(self):
        condition = {"in": [{"var": "entities.destination"}, ["机场", "公司", "天安门"]]}
        assert self.evaluator.evaluate(condition, self.context) == True

    def test_comparison_greater(self):
        condition = {">": [{"var": "entities.temperature"}, 24]}
        assert self.evaluator.evaluate(condition, self.context) == True

    def test_comparison_less(self):
        condition = {"<": [{"var": "entities.temperature"}, 30]}
        assert self.evaluator.evaluate(condition, self.context) == True
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/test_condition_evaluator.py -v`
Expected: FAIL - module not found

**Step 3: Write minimal ConditionEvaluator**

```python
# core/condition_evaluator.py
"""Condition expression evaluator for dynamic tool binding."""
from typing import Any


class ConditionEvaluator:
    """Evaluates nested condition expressions against context."""

    def evaluate(self, condition: dict, context: dict) -> bool:
        """Evaluate a condition expression."""
        if not condition:
            return True

        op = list(condition.keys())[0]
        args = condition[op]

        if op == "var":
            return self._resolve_var(args, context) is not None

        elif op == "and":
            return all(self.evaluate(c, context) for c in args)

        elif op == "or":
            return any(self.evaluate(c, context) for c in args)

        elif op == "not":
            return not self.evaluate(args, context)

        elif op == "==":
            return self._resolve(args[0], context) == self._resolve(args[1], context)

        elif op == "!=":
            return self._resolve(args[0], context) != self._resolve(args[1], context)

        elif op == ">":
            return self._resolve(args[0], context) > self._resolve(args[1], context)

        elif op == "<":
            return self._resolve(args[0], context) < self._resolve(args[1], context)

        elif op == ">=":
            return self._resolve(args[0], context) >= self._resolve(args[1], context)

        elif op == "<=":
            return self._resolve(args[0], context) <= self._resolve(args[1], context)

        elif op == "exists":
            return self._resolve_var(args, context) is not None

        elif op == "not_exists":
            return self._resolve_var(args, context) is None

        elif op == "in":
            value = self._resolve(args[0], context)
            return value in args[1]

        elif op == "startswith":
            value = self._resolve(args[0], context)
            return isinstance(value, str) and value.startswith(args[1])

        elif op == "endswith":
            value = self._resolve(args[0], context)
            return isinstance(value, str) and value.endswith(args[1])

        return False

    def _resolve_var(self, path: str, context: dict) -> Any:
        """Resolve { var: path.to.value } reference."""
        keys = path.split(".")
        value = context
        for key in keys:
            if not isinstance(value, dict):
                return None
            value = value.get(key)
            if value is None:
                return None
        return value

    def _resolve(self, value: Any, context: dict) -> Any:
        """Resolve a value - literal or variable reference."""
        if isinstance(value, dict) and "var" in value:
            return self._resolve_var(value["var"], context)
        return value
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_condition_evaluator.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/test_condition_evaluator.py core/condition_evaluator.py
git commit -m "feat: implement ConditionEvaluator with nested condition support"
```

---

### Task 3: Implement ParamMapper

**Files:**
- Create: `core/param_mapper.py`
- Test: `tests/unit/test_param_mapper.py`

**Step 1: Write failing tests**

```python
# tests/unit/test_param_mapper.py
import pytest
from core.param_mapper import ParamMapper

class TestParamMapper:
    def setup_method(self):
        self.mapper = ParamMapper()
        self.context = {
            "entities": {"temperature": "25", "fan_speed": 3, "mode": "cool"},
            "session": {},
            "query": {},
            "custom": {},
            "runtime": {}
        }

    def test_simple_param(self):
        param_defs = {
            "temperature": {"from": "entities.temperature"}
        }
        result = self.mapper.map_params(param_defs, self.context)
        assert result["temperature"] == "25"

    def test_type_conversion(self):
        param_defs = {
            "temperature": {"from": "entities.temperature", "type": "int"}
        }
        result = self.mapper.map_params(param_defs, self.context)
        assert result["temperature"] == 25
        assert isinstance(result["temperature"], int)

    def test_default_value(self):
        param_defs = {
            "power": {"from": "entities.power", "default": True}
        }
        result = self.mapper.map_params(param_defs, self.context)
        assert result["power"] == True

    def test_default_when_missing(self):
        param_defs = {
            "volume": {"from": "entities.volume", "default": 50}
        }
        result = self.mapper.map_params(param_defs, self.context)
        assert result["volume"] == 50

    def test_when_condition(self):
        param_defs = {
            "temp": {
                "from": "entities.temperature",
                "when": {"exists": {"var": "entities.temperature"}},
                "default": 24
            }
        }
        result = self.mapper.map_params(param_defs, self.context)
        assert result["temp"] == "25"

    def test_when_condition_false_uses_default(self):
        param_defs = {
            "temp": {
                "from": "entities.missing",
                "when": {"exists": {"var": "entities.missing"}},
                "default": 24
            }
        }
        result = self.mapper.map_params(param_defs, self.context)
        assert result["temp"] == 24

    def test_transform_celsius_to_fahrenheit(self):
        param_defs = {
            "temp_f": {
                "from": "entities.temperature",
                "transform": "celsius_to_fahrenheit"
            }
        }
        result = self.mapper.map_params(param_defs, self.context)
        assert result["temp_f"] == 77  # 25°C = 77°F

    def test_omit_if_missing(self):
        param_defs = {
            "missing_param": {
                "from": "entities.does_not_exist",
                "omit_if_missing": True
            }
        }
        result = self.mapper.map_params(param_defs, self.context)
        assert "missing_param" not in result
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/test_param_mapper.py -v`
Expected: FAIL - module not found

**Step 3: Write minimal ParamMapper**

```python
# core/param_mapper.py
"""Parameter mapper for dynamic tool binding."""
from typing import Any
from core.condition_evaluator import ConditionEvaluator


class ParamMapper:
    """Maps parameters from context according to param definitions."""

    TRANSFORMS = {
        "celsius_to_fahrenheit": lambda c: float(c) * 9/5 + 32 if c is not None else None,
        "km_to_miles": lambda km: float(km) * 0.621371 if km is not None else None,
    }

    def __init__(self, evaluator: ConditionEvaluator | None = None):
        self.evaluator = evaluator or ConditionEvaluator()

    def map_params(self, param_defs: dict, context: dict) -> dict:
        """Map parameters according to definitions."""
        result = {}

        for param_name, param_def in param_defs.items():
            mapped = self._map_single(param_name, param_def, context)
            if mapped is not None or not param_def.get("omit_if_missing", False):
                if mapped is not None:
                    result[param_name] = mapped

        return result

    def _map_single(self, param_name: str, param_def: dict, context: dict) -> Any:
        """Map a single parameter."""
        # Check when condition
        if "when" in param_def:
            if not self.evaluator.evaluate(param_def["when"], context):
                if "default" in param_def:
                    return param_def["default"]
                return None

        # Get value from source
        value = None
        if "from" in param_def:
            value = self.evaluator._resolve_var(param_def["from"], context)

        # Apply type conversion
        if value is not None and "type" in param_def:
            value = self._convert(value, param_def["type"])

        # Apply transform
        if value is not None and "transform" in param_def:
            transform = self.TRANSFORMS.get(param_def["transform"])
            if transform:
                value = transform(value)

        # Use default if no value
        if value is None:
            if "default" in param_def:
                return param_def["default"]
            return None

        return value

    def _convert(self, value: Any, type_name: str) -> Any:
        """Convert value to specified type."""
        if type_name == "int":
            return int(value)
        elif type_name == "float":
            return float(value)
        elif type_name == "str":
            return str(value)
        elif type_name == "bool":
            return bool(value)
        return value
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_param_mapper.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/test_param_mapper.py core/param_mapper.py
git commit -m "feat: implement ParamMapper with type conversion and transforms"
```

---

### Task 4: Implement BindingConfig Dataclass

**Files:**
- Create: `core/binding_schema.py`
- Test: `tests/unit/test_binding_schema.py`

**Step 1: Write failing tests**

```python
# tests/unit/test_binding_schema.py
import pytest
from core.binding_schema import BindingConfig, ActionSelector, ActionDef

class TestBindingSchema:
    def test_load_from_dict(self):
        data = {
            "goal_type": "climate_control",
            "version": "v1",
            "primary": {
                "tool": "climate_control",
                "action_selector": [
                    {"when": {"==": [{"var": "entities.power"}, False]}, "action": "off"},
                    {"default": "on"}
                ],
                "actions": {
                    "off": {"params": {}, "idempotent": True},
                    "on": {"params": {"temp": {"from": "entities.temp", "default": 24}}, "idempotent": True}
                }
            },
            "secondary": [
                {"description": "fallback", "tool": "climate_control", "action": "get_status", "params": {}}
            ],
            "retry": {"enabled": True, "max_attempts": 3},
            "error_strategy": "fallback_then_error"
        }
        config = BindingConfig.from_dict(data)
        assert config.goal_type == "climate_control"
        assert config.version == "v1"
        assert config.primary.tool == "climate_control"
        assert len(config.primary.action_selector) == 2
        assert config.error_strategy == "fallback_then_error"

    def test_action_selector_first_match(self):
        data = {
            "goal_type": "test",
            "version": "v1",
            "primary": {
                "tool": "test_tool",
                "action_selector": [
                    {"when": {"==": [1, 1]}, "action": "first"},
                    {"when": {"==": [1, 1]}, "action": "second"},
                    {"default": "default_action"}
                ],
                "actions": {}
            }
        }
        config = BindingConfig.from_dict(data)
        selector = config.primary.action_selector
        assert selector[0].action == "first"
        assert selector[1].action == "second"
        assert selector[2].default == "default_action"
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/test_binding_schema.py -v`
Expected: FAIL - module not found

**Step 3: Write minimal BindingConfig**

```python
# core/binding_schema.py
"""Binding configuration schema definitions."""
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ActionSelector:
    """Single action selector entry."""
    when: Optional[dict] = None
    action: Optional[str] = None
    default: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> "ActionSelector":
        return cls(
            when=data.get("when"),
            action=data.get("action"),
            default=data.get("default")
        )


@dataclass
class ActionDef:
    """Action definition with params."""
    params: dict = field(default_factory=dict)
    required_params: list = field(default_factory=list)
    idempotent: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> "ActionDef":
        return cls(
            params=data.get("params", {}),
            required_params=data.get("required_params", []),
            idempotent=data.get("idempotent", False)
        )


@dataclass
class PrimaryConfig:
    """Primary binding configuration."""
    tool: str
    action_selector: list = field(default_factory=list)
    actions: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "PrimaryConfig":
        return cls(
            tool=data["tool"],
            action_selector=[ActionSelector.from_dict(a) for a in data.get("action_selector", [])],
            actions={k: ActionDef.from_dict(v) for k, v in data.get("actions", {}).items()}
        )


@dataclass
class SecondaryConfig:
    """Secondary/fallback binding configuration."""
    description: str = ""
    tool: str = ""
    action: str = ""
    params: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "SecondaryConfig":
        return cls(
            description=data.get("description", ""),
            tool=data.get("tool", ""),
            action=data.get("action", ""),
            params=data.get("params", {})
        )


@dataclass
class RetryConfig:
    """Retry configuration."""
    enabled: bool = False
    max_attempts: int = 3
    delay_ms: int = 100
    backoff: str = "exponential"
    retry_on: list = field(default_factory=list)
    stop_early_if: list = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "RetryConfig":
        if not data:
            return cls()
        return cls(
            enabled=data.get("enabled", False),
            max_attempts=data.get("max_attempts", 3),
            delay_ms=data.get("delay_ms", 100),
            backoff=data.get("backoff", "exponential"),
            retry_on=data.get("retry_on", []),
            stop_early_if=data.get("stop_early_if", [])
        )


@dataclass
class BindingConfig:
    """Complete binding configuration."""
    goal_type: str
    version: str
    description: str = ""
    metadata: dict = field(default_factory=dict)
    primary: Optional[PrimaryConfig] = None
    secondary: list = field(default_factory=list)
    retry: RetryConfig = field(default_factory=RetryConfig)
    error_strategy: str = "fallback_then_error"

    @classmethod
    def from_dict(cls, data: dict) -> "BindingConfig":
        primary_data = data.get("primary", {})
        secondary_list = [SecondaryConfig.from_dict(s) for s in data.get("secondary", [])]

        return cls(
            goal_type=data["goal_type"],
            version=data.get("version", "v1"),
            description=data.get("description", ""),
            metadata=data.get("metadata", {}),
            primary=PrimaryConfig.from_dict(primary_data) if primary_data else None,
            secondary=secondary_list,
            retry=RetryConfig.from_dict(data.get("retry", {})),
            error_strategy=data.get("error_strategy", "fallback_then_error")
        )

    @classmethod
    def from_json(cls, json_str: str) -> "BindingConfig":
        import json
        return cls.from_dict(json.loads(json_str))

    @classmethod
    def from_file(cls, file_path: str) -> "BindingConfig":
        import json
        with open(file_path) as f:
            return cls.from_dict(json.load(f))
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_binding_schema.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/test_binding_schema.py core/binding_schema.py
git commit -m "feat: implement BindingConfig dataclass schema"
```

---

### Task 5: Implement BindingExecutor

**Files:**
- Create: `core/binding_executor.py`
- Test: `tests/unit/test_binding_executor.py`

**Step 1: Write failing tests**

```python
# tests/unit/test_binding_executor.py
import pytest
from unittest.mock import Mock, MagicMock
from core.binding_executor import BindingExecutor, ExecutionResult
from core.binding_manager import BindingManager
from core.binding_schema import BindingConfig

class TestBindingExecutor:
    def setup_method(self):
        self.mock_registry = Mock()
        self.mock_registry.call_tool.return_value = Mock(
            success=True,
            description="OK",
            state={}
        )

    def test_execute_primary_success(self):
        binding_data = {
            "goal_type": "climate_control",
            "version": "v1",
            "primary": {
                "tool": "climate_control",
                "action_selector": [
                    {"default": "on"}
                ],
                "actions": {
                    "on": {
                        "params": {"temp": {"from": "entities.temp", "default": 24}},
                        "idempotent": True
                    }
                }
            }
        }
        config = BindingConfig.from_dict(binding_data)
        manager = Mock()
        manager.get.return_value = config
        executor = BindingExecutor(manager, self.mock_registry)

        result = executor.execute(
            goal_type="climate_control",
            entities={"temp": 25},
            context={}
        )
        assert result.success == True
        self.mock_registry.call_tool.assert_called_once()

    def test_execute_binding_not_found(self):
        manager = Mock()
        manager.get.return_value = None
        executor = BindingExecutor(manager, self.mock_registry)

        result = executor.execute(
            goal_type="nonexistent",
            entities={},
            context={}
        )
        assert result.success == False
        assert result.error == "BINDING_NOT_FOUND"

    def test_execute_with_fallback(self):
        # Primary fails, fallback succeeds
        binding_data = {
            "goal_type": "climate_control",
            "version": "v1",
            "primary": {
                "tool": "climate_control",
                "action_selector": [
                    {"when": {"==": [1, 0]}, "action": "fail_action"}
                ],
                "actions": {
                    "fail_action": {
                        "params": {},
                        "idempotent": False
                    }
                }
            },
            "secondary": [
                {
                    "description": "fallback",
                    "tool": "climate_control",
                    "action": "get_status",
                    "params": {}
                }
            ],
            "error_strategy": "fallback_then_error"
        }
        config = BindingConfig.from_dict(binding_data)
        manager = Mock()
        manager.get.return_value = config
        executor = BindingExecutor(manager, self.mock_registry)

        # First call fails, second succeeds
        self.mock_registry.call_tool.side_effect = [
            Mock(success=False, error="TOOL_NOT_FOUND", description="fail", state={}),
            Mock(success=True, description="fallback OK", state={})
        ]

        result = executor.execute(
            goal_type="climate_control",
            entities={},
            context={}
        )
        assert result.success == True
        assert self.mock_registry.call_tool.call_count == 2
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/test_binding_executor.py -v`
Expected: FAIL - module not found

**Step 3: Write minimal BindingExecutor**

```python
# core/binding_executor.py
"""Binding executor for dynamic tool binding."""
from typing import Any
from dataclasses import dataclass, field
from core.binding_manager import BindingManager
from core.condition_evaluator import ConditionEvaluator
from core.param_mapper import ParamMapper


@dataclass
class ExecutionResult:
    """Result of binding execution."""
    success: bool
    description: str = ""
    state: dict = field(default_factory=dict)
    error: str = ""
    error_message: str = ""
    goal_type: str = ""
    tool: str = ""
    action: str = ""
    params: dict = field(default_factory=dict)
    fallback_attempted: bool = False
    fallback_results: list = field(default_factory=list)

    @classmethod
    def error(cls, error_type: str, message: str, **kwargs) -> "ExecutionResult":
        return cls(
            success=False,
            error=error_type,
            error_message=message,
            **kwargs
        )


class BindingExecutor:
    """Executes bindings with primary/secondary/fallback logic."""

    def __init__(
        self,
        binding_manager: BindingManager,
        registry: Any,
        evaluator: ConditionEvaluator | None = None,
        mapper: ParamMapper | None = None
    ):
        self.bindings = binding_manager
        self.registry = registry
        self.evaluator = evaluator or ConditionEvaluator()
        self.mapper = mapper or ParamMapper(self.evaluator)

    def execute(
        self,
        goal_type: str,
        entities: dict,
        context: dict
    ) -> ExecutionResult:
        """Execute a binding."""
        binding = self.bindings.get(goal_type)
        if not binding:
            return ExecutionResult.error(
                "BINDING_NOT_FOUND",
                f"未找到 binding: {goal_type}",
                goal_type=goal_type
            )

        full_context = {
            "entities": entities,
            "session": context.get("session", {}),
            "query": context.get("query", {}),
            "custom": context.get("custom", {}),
            "runtime": {}
        }

        # Execute primary
        result = self._execute_primary(binding, full_context)

        # Handle fallback if needed
        if not result.success:
            if binding.secondary and binding.error_strategy != "error_only":
                result = self._execute_with_fallback(binding, full_context, result)
            elif binding.error_strategy == "error_only":
                pass

        return result

    def _execute_primary(
        self,
        binding: BindingManager,
        context: dict
    ) -> ExecutionResult:
        """Execute primary binding."""
        # Select action
        action_name = self._select_action(binding.primary.action_selector, context)
        if not action_name:
            return ExecutionResult.error(
                "INVALID_ACTION_SELECTION",
                f"无法为 {binding.goal_type} 选择 action"
            )

        # Get action definition
        action_def = binding.primary.actions.get(action_name)
        if not action_def:
            return ExecutionResult.error(
                "INVALID_ACTION",
                f"action 不存在: {action_name}"
            )

        # Map params
        params = self.mapper.map_params(action_def.params, context)

        # Check required params
        for required in action_def.required_params:
            if required not in params:
                return ExecutionResult.error(
                    "VALIDATION_ERROR",
                    f"缺少必需参数: {required}"
                )

        # Call tool
        tool_result = self.registry.call_tool(
            binding.primary.tool,
            action_name,
            **params
        )

        return ExecutionResult(
            success=tool_result.success,
            description=getattr(tool_result, "description", str(tool_result)),
            state=getattr(tool_result, "state", {}),
            goal_type=binding.goal_type,
            tool=binding.primary.tool,
            action=action_name,
            params=params
        )

    def _select_action(
        self,
        action_selector: list,
        context: dict
    ) -> str | None:
        """Select action from selector using first-match-wins."""
        default_action = None
        for selector in action_selector:
            if selector.default is not None:
                default_action = selector.default
                continue
            if selector.when:
                if self.evaluator.evaluate(selector.when, context):
                    return selector.action
        return default_action

    def _execute_with_fallback(
        self,
        binding: BindingManager,
        context: dict,
        primary_result: ExecutionResult
    ) -> ExecutionResult:
        """Execute with fallback chain."""
        fallback_results = []

        for sec in binding.secondary:
            tool_result = self.registry.call_tool(
                sec.tool,
                sec.action,
                **sec.params
            )
            fallback_results.append({
                "description": sec.description,
                "tool": sec.tool,
                "action": sec.action,
                "result": tool_result
            })

            if tool_result.success:
                return ExecutionResult(
                    success=True,
                    description=getattr(tool_result, "description", "OK"),
                    state=getattr(tool_result, "state", {}),
                    goal_type=binding.goal_type,
                    tool=sec.tool,
                    action=sec.action,
                    params=sec.params,
                    fallback_attempted=True,
                    fallback_results=fallback_results
                )

        # All fallbacks failed
        return ExecutionResult(
            success=False,
            error=primary_result.error or "EXECUTION_ERROR",
            error_message=primary_result.error_message or "Primary and all fallbacks failed",
            goal_type=binding.goal_type,
            fallback_attempted=True,
            fallback_results=fallback_results
        )
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_binding_executor.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/test_binding_executor.py core/binding_executor.py
git commit -m "feat: implement BindingExecutor with primary/secondary execution"
```

---

### Task 6: Implement BindingManager

**Files:**
- Create: `core/binding_manager.py`
- Test: `tests/unit/test_binding_manager.py`

**Step 1: Write failing tests**

```python
# tests/unit/test_binding_manager.py
import pytest
import tempfile
import os
import json
from pathlib import Path
from core.binding_manager import BindingManager

class TestBindingManager:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_load_single_binding(self):
        # Create a test binding file
        binding_data = {
            "goal_type": "test_tool",
            "version": "v1",
            "primary": {
                "tool": "test_tool",
                "action_selector": [{"default": "do_it"}],
                "actions": {"do_it": {"params": {}, "idempotent": True}}
            }
        }
        test_file = os.path.join(self.temp_dir, "test_tool.json")
        with open(test_file, "w") as f:
            json.dump(binding_data, f)

        manager = BindingManager(self.temp_dir)
        manager.load_all()

        assert "test_tool" in manager.bindings
        assert manager.bindings["test_tool"].goal_type == "test_tool"

    def test_load_multiple_bindings(self):
        # Create multiple binding files
        for name in ["tool_a", "tool_b", "tool_c"]:
            binding_data = {
                "goal_type": name,
                "version": "v1",
                "primary": {
                    "tool": name,
                    "action_selector": [{"default": "run"}],
                    "actions": {"run": {"params": {}, "idempotent": True}}
                }
            }
            test_file = os.path.join(self.temp_dir, f"{name}.json")
            with open(test_file, "w") as f:
                json.dump(binding_data, f)

        manager = BindingManager(self.temp_dir)
        manager.load_all()

        assert len(manager.bindings) == 3
        assert "tool_a" in manager.bindings
        assert "tool_b" in manager.bindings
        assert "tool_c" in manager.bindings

    def test_get_binding(self):
        binding_data = {
            "goal_type": "my_tool",
            "version": "v1",
            "primary": {
                "tool": "my_tool",
                "action_selector": [{"default": "run"}],
                "actions": {"run": {"params": {}, "idempotent": True}}
            }
        }
        test_file = os.path.join(self.temp_dir, "my_tool.json")
        with open(test_file, "w") as f:
            json.dump(binding_data, f)

        manager = BindingManager(self.temp_dir)
        manager.load_all()

        binding = manager.get("my_tool")
        assert binding is not None
        assert binding.goal_type == "my_tool"

        missing = manager.get("nonexistent")
        assert missing is None

    def test_skip_index_files(self):
        # Create _index.json - should be skipped
        index_data = {"bindings": []}
        index_file = os.path.join(self.temp_dir, "_index.json")
        with open(index_file, "w") as f:
            json.dump(index_data, f)

        binding_data = {
            "goal_type": "real_tool",
            "version": "v1",
            "primary": {
                "tool": "real_tool",
                "action_selector": [{"default": "run"}],
                "actions": {"run": {"params": {}, "idempotent": True}}
            }
        }
        real_file = os.path.join(self.temp_dir, "real_tool.json")
        with open(real_file, "w") as f:
            json.dump(binding_data, f)

        manager = BindingManager(self.temp_dir)
        manager.load_all()

        assert "real_tool" in manager.bindings
        assert "_index" not in manager.bindings
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/test_binding_manager.py -v`
Expected: FAIL - module not found

**Step 3: Write minimal BindingManager**

```python
# core/binding_manager.py
"""Binding manager for loading and managing binding configurations."""
import json
from pathlib import Path
from typing import Optional
from core.binding_schema import BindingConfig


class BindingManager:
    """Manages binding configurations."""

    def __init__(self, bindings_dir: str = "configs/bindings/"):
        self.bindings_dir = Path(bindings_dir).expanduser()
        self.bindings: dict[str, BindingConfig] = {}

    def load_all(self) -> None:
        """Load all binding configurations from directory."""
        self.bindings.clear()

        if not self.bindings_dir.exists():
            return

        for file_path in self.bindings_dir.rglob("*.json"):
            # Skip index and schema files
            if file_path.name.startswith("_"):
                continue

            try:
                binding = BindingConfig.from_file(str(file_path))
                self.bindings[binding.goal_type] = binding
            except Exception as e:
                print(f"Failed to load {file_path}: {e}")

    def get(self, goal_type: str) -> Optional[BindingConfig]:
        """Get binding by goal_type."""
        return self.bindings.get(goal_type)

    def reload(self, file_path: str) -> None:
        """Reload a specific binding file."""
        try:
            binding = BindingConfig.from_file(file_path)
            self.bindings[binding.goal_type] = binding
        except Exception as e:
            print(f"Failed to reload {file_path}: {e}")

    def list_goal_types(self) -> list[str]:
        """List all loaded goal_types."""
        return list(self.bindings.keys())
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_binding_manager.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/test_binding_manager.py core/binding_manager.py
git commit -m "feat: implement BindingManager with directory scanning"
```

---

## Phase 2: Integration

### Task 7: Create First Binding Config (climate_control)

**Files:**
- Create: `configs/bindings/vehicle/climate_control.json`

**Step 1: Create binding file**

```bash
mkdir -p configs/bindings/vehicle
cat > configs/bindings/vehicle/climate_control.json << 'EOF'
{
  "$schema": "./_schema.json",
  "goal_type": "climate_control",
  "version": "v1",
  "description": "空调控制 - 支持开关，温度调节、风速控制",

  "metadata": {
    "author": "system",
    "created": "2026-04-18",
    "category": "vehicle",
    "tags": ["vehicle", "hvac"]
  },

  "primary": {
    "tool": "climate_control",

    "action_selector": [
      {
        "when": {"==": [{"var": "entities.power"}, false]},
        "action": "off"
      },
      {
        "when": {"exists": {"var": "entities.temperature"}},
        "action": "set_temp"
      },
      {
        "when": {"exists": {"var": "entities.fan_speed"}},
        "action": "set_wind"
      },
      {
        "when": {"==": [{"var": "entities.mode"}, "heat"]},
        "action": "heat"
      },
      {
        "default": "on"
      }
    ],

    "actions": {
      "off": {
        "params": {},
        "idempotent": true
      },
      "on": {
        "params": {
          "temperature": {
            "from": "entities.temperature",
            "type": "int",
            "default": 24
          },
          "mode": {
            "from": "entities.mode",
            "default": "auto"
          }
        },
        "idempotent": true
      },
      "set_temp": {
        "required_params": ["temperature"],
        "params": {
          "temperature": {
            "from": "entities.temperature",
            "type": "int",
            "default": 24
          },
          "mode": {
            "from": "entities.mode",
            "default": "auto"
          }
        },
        "idempotent": true
      },
      "set_wind": {
        "required_params": ["fan_speed"],
        "params": {
          "fan_speed": {
            "from": "entities.fan_speed",
            "type": "int",
            "default": 3
          }
        },
        "idempotent": true
      },
      "heat": {
        "params": {
          "mode": {"default": "heat"},
          "temperature": {
            "from": "entities.temperature",
            "type": "int",
            "default": 26
          }
        },
        "idempotent": true
      }
    }
  },

  "secondary": [
    {
      "description": "降级: 获取状态",
      "tool": "climate_control",
      "action": "get_status",
      "params": {}
    }
  ],

  "retry": {
    "enabled": true,
    "max_attempts": 3,
    "delay_ms": 100,
    "backoff": "exponential",
    "retry_on": ["EXECUTION_ERROR", "TIMEOUT", "RATE_LIMIT"],
    "stop_early_if": [
      {"==": [{"var": "runtime.error_type"}, "VALIDATION_ERROR"]},
      {"==": [{"var": "runtime.error_type"}, "TOOL_NOT_FOUND"]}
    ]
  },

  "error_strategy": "fallback_then_error"
}
EOF
```

**Step 2: Validate JSON syntax**

Run: `python -c "import json; json.load(open('configs/bindings/vehicle/climate_control.json'))"`
Expected: No output (success)

**Step 3: Commit**

```bash
git add configs/bindings/vehicle/climate_control.json
git commit -m "feat: add climate_control binding config"
```

---

### Task 8: Integrate into ExecutorAgent (Hybrid Mode)

**Files:**
- Modify: `agents/executor_agent.py`

**Step 1: Read current executor_agent.py**

```bash
head -100 agents/executor_agent.py
```

**Step 2: Add hybrid execution mode**

Add at top of executor_agent.py:
```python
# Try dynamic binding first, fallback to hardcoded
try:
    from core.binding_manager import BindingManager
    from core.binding_executor import BindingExecutor
    _binding_executor = None
    def get_binding_executor():
        global _binding_executor
        if _binding_executor is None:
            from backend.tools import registry
            manager = BindingManager("configs/bindings/")
            manager.load_all()
            _binding_executor = BindingExecutor(manager, registry)
        return _binding_executor
except ImportError:
    get_binding_executor = None
```

**Step 3: Modify _execute_goal to try binding first**

Replace the start of `_execute_goal` method:
```python
def _execute_goal(self, goal: Goal, registry) -> Any:
    """Execute a single goal using ToolRegistry."""
    goal_type = goal.type
    intent_info = getattr(goal, 'result', {}) or {}
    entities = intent_info.get("entities", {})

    # Try dynamic binding first
    if get_binding_executor is not None:
        executor = get_binding_executor()
        if executor and executor.bindings.get(goal_type):
            result = executor.execute(goal_type, entities, {})
            # Convert BindingExecutor result to ToolResult-like object
            class ResultWrapper:
                def __init__(self, r):
                    self.description = r.description
                    self.state = r.state
                    self.success = r.success
                    self.error = r.error
            return ResultWrapper(result)

    # Fallback to hardcoded logic
    # ... rest of existing hardcoded logic
```

**Step 4: Test the hybrid mode**

Run: `python -c "from agents.executor_agent import ExecutorAgent; print('Import OK')"`
Expected: No errors

**Step 5: Commit**

```bash
git add agents/executor_agent.py
git commit -m "feat: add hybrid binding mode to ExecutorAgent"
```

---

### Task 9: Add Integration Test

**Files:**
- Create: `tests/integration/test_binding_integration.py`

**Step 1: Write integration test**

```python
# tests/integration/test_binding_integration.py
import pytest
from unittest.mock import Mock
from core.binding_manager import BindingManager
from core.binding_executor import BindingExecutor
from backend.tools import registry

class TestBindingIntegration:
    def test_climate_control_binding(self):
        """Test climate_control binding end-to-end."""
        manager = BindingManager("configs/bindings/")
        manager.load_all()

        assert "climate_control" in manager.bindings

        executor = BindingExecutor(manager, registry)

        # Test: turn on with temperature
        result = executor.execute(
            goal_type="climate_control",
            entities={"power": True, "temperature": 24},
            context={}
        )
        assert result.success == True
        assert "温度" in result.description or "24" in result.description

    def test_climate_control_fallback(self):
        """Test climate_control fallback when primary fails."""
        # This would require mocking the registry to fail
        pass
```

**Step 2: Run integration test**

Run: `python -m pytest tests/integration/test_binding_integration.py -v`
Expected: PASS (if registry is available)

**Step 3: Commit**

```bash
git add tests/integration/test_binding_integration.py
git commit -m "test: add binding integration tests"
```

---

## Phase 3: Migration (Remaining Bindings)

### Task 10: Extract and Create Remaining Binding Files

**Files:**
- Create: `configs/bindings/vehicle/*.json` (5 more files)
- Create: `configs/bindings/advisory/**/*.json` (19 files)

**Step 1: Create migration script**

```python
# tools/extract_bindings.py
#!/usr/bin/env python3
"""Extract binding configs from executor_agent.py hardcoded logic."""

EXECUTOR_GOALS = {
    "climate_control": {
        "tool": "climate_control",
        "action": "control",
        "params": ["temperature", "fan_speed", "power"]
    },
    "navigation": {
        "tool": "navigation",
        "action": "navigate",
        "params": ["destination"]
    },
    # ... etc
}

def generate_binding(goal_type: str, config: dict) -> dict:
    """Generate binding config from hardcoded mapping."""
    return {
        "goal_type": goal_type,
        "version": "v1",
        "primary": {
            "tool": config["tool"],
            "action_selector": [{"default": config["action"]}],
            "actions": {
                config["action"]: {
                    "params": {p: {"from": f"entities.{p}"} for p in config["params"]},
                    "idempotent": True
                }
            }
        },
        "error_strategy": "fallback_then_error"
    }
```

**Step 2: Run extraction**

```bash
python tools/extract_bindings.py --output configs/bindings/
```

**Step 3: Validate all bindings**

```bash
python -c "
from core.binding_manager import BindingManager
manager = BindingManager('configs/bindings/')
manager.load_all()
print(f'Loaded {len(manager.bindings)} bindings')
for gt in manager.bindings:
    print(f'  - {gt}')
"
```

**Step 4: Commit all bindings**

```bash
git add configs/bindings/
git commit -m "feat: add all binding configs"
```

---

### Task 11: Remove Hardcoded Fallback

**Files:**
- Modify: `agents/executor_agent.py`

**Step 1: Verify all bindings loaded**

```bash
python -c "
from core.binding_manager import BindingManager
manager = BindingManager('configs/bindings/')
manager.load_all()
print(f'Total bindings: {len(manager.bindings)}')
"
```

**Step 2: Comment out hardcoded fallback**

In `_execute_goal`, after ensuring all goal_types have bindings:
```python
# Remove hardcoded fallback - binding not found means error
if get_binding_executor is not None:
    executor = get_binding_executor()
    if executor and executor.bindings.get(goal_type):
        # ... binding execution
    else:
        class ErrorResult:
            def __init__(self):
                self.description = f"Unknown goal type: {goal_type}"
                self.state = {"error": f"Unsupported goal type: {goal_type}"}
                self.success = False
        return ErrorResult()
```

**Step 3: Commit**

```bash
git add agents/executor_agent.py
git commit -m "refactor: remove hardcoded fallback, use binding-only execution"
```

---

## Phase 4: Validation & Polish

### Task 12: Add CLI Tools

**Files:**
- Create: `tools/cli.py`

**Step 1: Implement CLI**

```python
# tools/cli.py
#!/usr/bin/env python3
"""CLI tools for binding management."""
import argparse
import sys
from core.binding_manager import BindingManager

def main():
    parser = argparse.ArgumentParser(description="Binding tools")
    parser.add_argument("command", choices=["list", "validate", "info"])
    parser.add_argument("goal_type", nargs="?")
    args = parser.parse_args()

    manager = BindingManager("configs/bindings/")
    manager.load_all()

    if args.command == "list":
        for gt in manager.list_goal_types():
            print(gt)
    elif args.command == "info" and args.goal_type:
        binding = manager.get(args.goal_type)
        if binding:
            print(f"goal_type: {binding.goal_type}")
            print(f"version: {binding.version}")
            print(f"tool: {binding.primary.tool}")
        else:
            print(f"Not found: {args.goal_type}", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    main()
```

**Step 2: Test CLI**

```bash
python tools/cli.py list
python tools/cli.py info climate_control
```

**Step 3: Commit**

```bash
git add tools/cli.py
git commit -m "feat: add binding CLI tools"
```

---

## Summary

| Phase | Tasks | Description |
|-------|-------|-------------|
| 1 | 6 | Core infrastructure: ConditionEvaluator, ParamMapper, BindingConfig, BindingExecutor, BindingManager |
| 2 | 3 | Integration: First binding, hybrid ExecutorAgent, integration test |
| 3 | 2 | Migration: Extract remaining bindings, remove hardcoded fallback |
| 4 | 1 | Polish: CLI tools |

**Total: 11 tasks**

---

## Plan Complete

Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

Which approach?
