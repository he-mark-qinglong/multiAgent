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
