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
            var_path = args if isinstance(args, str) else args.get("var", "")
            return self._resolve_var(var_path, context) is not None

        elif op == "not_exists":
            var_path = args if isinstance(args, str) else args.get("var", "")
            return self._resolve_var(var_path, context) is None

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