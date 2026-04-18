"""BindingExecutor - executes bindings with fallback, retry, and error handling.

This module provides the core execution logic for dynamic tool bindings.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Optional

from core.binding_schema import (
    BindingConfig,
    PrimaryConfig,
    SecondaryConfig,
    RetryConfig,
    ActionSelector,
)
from core.condition_evaluator import ConditionEvaluator
from core.param_mapper import ParamMapper

logger = logging.getLogger(__name__)


# Registry for tool execution - injected at runtime
_tool_registry: Any = None


def set_tool_registry(registry: Any) -> None:
    """Set the global tool registry for execution.

    Args:
        registry: ToolRegistry instance with call_tool method
    """
    global _tool_registry
    _tool_registry = registry


def get_tool_registry() -> Any:
    """Get the global tool registry."""
    global _tool_registry
    return _tool_registry


class ToolExecutionError(Exception):
    """Error during tool execution."""

    def __init__(self, tool: str, action: str, reason: str, is_retryable: bool = False):
        super().__init__(f"{tool}.{action} failed: {reason}")
        self.tool = tool
        self.action = action
        self.reason = reason
        self.is_retryable = is_retryable


class BindingExecutor:
    """Executes binding configurations with fallback, retry, and error handling.

    Usage:
        executor = BindingExecutor()
        result = executor.execute(binding_config, context)

    The executor:
    1. Uses ConditionEvaluator to find first matching action_selector
    2. Uses ParamMapper to extract and transform parameters
    3. Calls the tool via registry.call_tool()
    4. On failure, applies retry logic (if configured)
    5. On persistent failure, tries secondary fallbacks
    6. Finally applies error_strategy (fallback_then_error or error_only)
    """

    def __init__(self, evaluator: Optional[ConditionEvaluator] = None, param_mapper: Optional[ParamMapper] = None):
        self.evaluator = evaluator or ConditionEvaluator()
        self.param_mapper = param_mapper or ParamMapper()

    def execute(self, binding: BindingConfig, context: dict) -> ExecutionResult:
        """Synchronous execute a binding.

        Args:
            binding: BindingConfig to execute
            context: Execution context with intent info, entities, etc.

        Returns:
            ExecutionResult with output/state or error info
        """
        if not binding.primary:
            return self._execute_secondary_fallback(binding, context)

        # Select action using action_selector
        selected_action = self._select_action(binding.primary, context)
        if not selected_action:
            logger.warning(f"No action selected for {binding.goal_type}, trying fallback")
            return self._execute_secondary_fallback(binding, context)

        # Get action definition
        action_def = binding.primary.actions.get(selected_action)
        if not action_def:
            return self._error_result(
                binding.primary.tool,
                selected_action,
                f"Action '{selected_action}' not found in actions block"
            )

        # Map parameters
        try:
            params = self.param_mapper.map_params(action_def.params, context)
        except Exception as e:
            return self._error_result(binding.primary.tool, selected_action, f"Param mapping failed: {e}")

        # Execute with retry
        retry_config = binding.retry
        last_error: Optional[Exception] = None

        max_attempts = retry_config.max_attempts if retry_config.enabled else 1
        for attempt in range(1, max_attempts + 1):
            try:
                result = self._call_tool(binding.primary.tool, selected_action, params)
                return self._success_result(binding.primary.tool, selected_action, result)

            except ToolExecutionError as e:
                last_error = e
                if retry_config.enabled and attempt < retry_config.max_attempts:
                    # Check if this error type should retry
                    if e.is_retryable or self._should_retry(e, retry_config):
                        delay = self._calculate_delay(retry_config, attempt)
                        logger.info(f"Retrying {binding.primary.tool}.{selected_action} in {delay}ms (attempt {attempt + 1})")
                        time.sleep(delay / 1000)
                        continue
                break

            except Exception as e:
                last_error = e
                break

        # Primary failed - try secondary fallback
        if last_error:
            if retry_config.enabled:
                logger.info(f"Primary failed after {retry_config.max_attempts} attempts, trying fallback")
            return self._execute_secondary_fallback(binding, context)

        return self._error_result(
            binding.primary.tool,
            selected_action,
            str(last_error) if last_error else "Unknown error"
        )

    def _select_action(self, primary: PrimaryConfig, context: dict) -> Optional[str]:
        """Select the first matching action from action_selector.

        Args:
            primary: PrimaryConfig with action_selector
            context: Execution context

        Returns:
            Selected action name or None if no match
        """
        for selector in primary.action_selector:
            # Check if 'when' condition matches
            if selector.when is not None:
                if self.evaluator.evaluate(selector.when, context):
                    return selector.action
            # Check if this is a default (no when condition)
            elif selector.default is not None:
                return selector.default

        # No matching selector found
        return None

    def _call_tool(self, tool: str, action: str, params: dict) -> Any:
        """Call a tool via the registry.

        Args:
            tool: Tool name
            action: Action name
            params: Parameters to pass

        Returns:
            Tool result

        Raises:
            ToolExecutionError: If tool call fails
        """
        registry = get_tool_registry()
        if not registry:
            raise ToolExecutionError(tool, action, "Tool registry not configured", is_retryable=False)

        try:
            result = registry.call_tool(tool, action, **params)
            return result
        except Exception as e:
            is_retryable = self._is_retryable_error(e)
            raise ToolExecutionError(tool, action, str(e), is_retryable=is_retryable)

    def _should_retry(self, error: ToolExecutionError, retry_config: RetryConfig) -> bool:
        """Check if error should be retried based on retry_on whitelist.

        Args:
            error: The ToolExecutionError
            retry_config: Retry configuration

        Returns:
            True if should retry
        """
        if not retry_config.retry_on:
            return error.is_retryable

        # Check if error reason matches any retry_on patterns
        error_str = error.reason.lower()
        for pattern in retry_config.retry_on:
            if pattern.lower() in error_str:
                return True
        return False

    def _is_retryable_error(self, error: Exception) -> bool:
        """Determine if an exception is retryable based on its type.

        Args:
            error: The exception

        Returns:
            True if retryable
        """
        error_type = type(error).__name__
        retryable_types = {"TimeoutError", "ConnectionError", "NetworkError", "TemporaryError"}
        return error_type in retryable_types

    def _calculate_delay(self, retry_config: RetryConfig, attempt: int) -> float:
        """Calculate delay before next retry attempt.

        Args:
            retry_config: Retry configuration
            attempt: Current attempt number (1-based)

        Returns:
            Delay in milliseconds
        """
        base_delay = retry_config.delay_ms

        if retry_config.backoff == "exponential":
            return base_delay * (2 ** (attempt - 1))
        elif retry_config.backoff == "linear":
            return base_delay * attempt
        else:  # fixed
            return base_delay

    def _execute_secondary_fallback(self, binding: BindingConfig, context: dict) -> ExecutionResult:
        """Execute secondary/fallback configurations in order.

        Args:
            binding: BindingConfig with secondary list
            context: Execution context

        Returns:
            ExecutionResult from first successful secondary or error
        """
        for secondary in binding.secondary:
            try:
                params = self.param_mapper.map_params(secondary.params, context)
                result = self._call_tool(secondary.tool, secondary.action, params)
                return self._success_result(secondary.tool, secondary.action, result)
            except ToolExecutionError as e:
                logger.warning(f"Secondary fallback {secondary.tool}.{secondary.action} failed: {e}")
                continue

        # All secondary failed - apply error strategy
        if binding.error_strategy == "fallback_then_error":
            return self._error_result(
                binding.goal_type,
                "fallback",
                "All primary and secondary actions failed"
            )
        else:
            return self._error_result(
                binding.goal_type,
                "execute",
                "Execution failed with error_only strategy"
            )

    def _success_result(self, tool: str, action: str, result: Any) -> ExecutionResult:
        """Create a success execution result."""
        output = getattr(result, 'description', str(result)) if result else ""
        state = getattr(result, 'state', {}) if result else {}
        return ExecutionResult(
            success=True,
            tool=tool,
            action=action,
            output=output,
            state=state
        )

    def _error_result(self, tool: str, action: str, error: str) -> ExecutionResult:
        """Create an error execution result."""
        return ExecutionResult(
            success=False,
            tool=tool,
            action=action,
            output="",
            state={"error": error}
        )


class ExecutionResult:
    """Result of a binding execution.

    Attributes:
        success: Whether execution succeeded
        tool: Tool that was called
        action: Action that was called
        output: Human-readable output/description
        state: Structured state data
    """

    def __init__(
        self,
        success: bool,
        tool: str = "",
        action: str = "",
        output: str = "",
        state: Optional[dict] = None
    ):
        self.success = success
        self.tool = tool
        self.action = action
        self.output = output
        self.state = state or {}

    def __repr__(self) -> str:
        status = "SUCCESS" if self.success else "FAILED"
        return f"<ExecutionResult {status} {self.tool}.{self.action}>"

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "success": self.success,
            "tool": self.tool,
            "action": self.action,
            "output": self.output,
            "state": self.state
        }
