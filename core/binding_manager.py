"""BindingManager - manages all binding configurations and provides execution.

This module provides the main interface for loading and executing dynamic tool bindings.
"""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any, Optional

from core.binding_schema import BindingConfig
from core.binding_executor import BindingExecutor, set_tool_registry, ExecutionResult

logger = logging.getLogger(__name__)

# Default bindings directory
DEFAULT_BINDINGS_DIR = "~/.multiagent/bindings"


class BindingManager:
    """Manages binding configurations and executes bindings.

    Usage:
        manager = BindingManager()
        manager.load_bindings_from_dir()
        result = manager.execute_binding("climate_control", context)

    The manager:
    1. Loads binding configs from JSON files
    2. Caches bindings for fast lookup
    3. Provides execute_binding() interface for ExecutorAgent
    4. Supports hot reload via reload_bindings()
    """

    def __init__(
        self,
        bindings_dir: Optional[str] = None,
        executor: Optional[BindingExecutor] = None,
    ):
        """Initialize BindingManager.

        Args:
            bindings_dir: Directory containing binding JSON files. Defaults to ~/.multiagent/bindings
            executor: BindingExecutor instance. Creates one if not provided.
        """
        self.bindings_dir = Path(bindings_dir or DEFAULT_BINDINGS_DIR).expanduser()
        self.executor = executor or BindingExecutor()
        self._bindings: dict[str, BindingConfig] = {}
        self._lock = threading.RLock()

    def load_bindings_from_dir(self, silent: bool = False) -> dict[str, bool]:
        """Load all binding configs from the bindings directory.

        Args:
            silent: If True, don't log warnings for missing directory

        Returns:
            Dict mapping goal_type to whether it loaded successfully
        """
        results = {}

        if not self.bindings_dir.exists():
            if not silent:
                logger.warning(f"Bindings directory does not exist: {self.bindings_dir}")
            return results

        for file_path in self.bindings_dir.glob("*.json"):
            goal_type = file_path.stem  # filename without extension
            try:
                binding = BindingConfig.from_file(str(file_path))
                self._bindings[goal_type] = binding
                results[goal_type] = True
                logger.debug(f"Loaded binding: {goal_type}")
            except Exception as e:
                logger.error(f"Failed to load binding {goal_type}: {e}")
                results[goal_type] = False

        if not silent:
            logger.info(f"Loaded {len(self._bindings)} bindings from {self.bindings_dir}")

        return results

    def get_binding(self, goal_type: str) -> Optional[BindingConfig]:
        """Get a binding config by goal type.

        Args:
            goal_type: The goal type to look up

        Returns:
            BindingConfig or None if not found
        """
        return self._bindings.get(goal_type)

    def register_binding(self, binding: BindingConfig) -> None:
        """Register a binding config in memory.

        Args:
            binding: BindingConfig to register
        """
        with self._lock:
            self._bindings[binding.goal_type] = binding
        logger.debug(f"Registered binding: {binding.goal_type}")

    def register_binding_from_dict(self, data: dict) -> BindingConfig:
        """Register a binding config from a dict.

        Args:
            data: Dict containing binding configuration

        Returns:
            The registered BindingConfig
        """
        binding = BindingConfig.from_dict(data)
        self.register_binding(binding)
        return binding

    def execute_binding(self, goal_type: str, context: dict) -> ExecutionResult:
        """Execute a binding by goal type.

        Args:
            goal_type: The goal type to execute
            context: Execution context with intent info, entities, etc.

        Returns:
            ExecutionResult from the binding execution
        """
        binding = self.get_binding(goal_type)
        if not binding:
            logger.warning(f"No binding found for goal_type: {goal_type}")
            return ExecutionResult(
                success=False,
                tool=goal_type,
                action="lookup",
                output="",
                state={"error": f"No binding found for {goal_type}"}
            )

        return self.executor.execute(binding, context)

    def reload_bindings(self) -> dict[str, bool]:
        """Hot reload all bindings from disk.

        Returns:
            Dict mapping goal_type to whether it reloaded successfully
        """
        with self._lock:
            self._bindings.clear()
        return self.load_bindings_from_dir()

    def list_bindings(self) -> list[str]:
        """List all registered goal types.

        Returns:
            List of goal type strings
        """
        return list(self._bindings.keys())

    def get_binding_count(self) -> int:
        """Get the number of registered bindings."""
        return len(self._bindings)


# Global manager instance
_manager: Optional[BindingManager] = None
_manager_lock = threading.Lock()


def get_binding_manager() -> BindingManager:
    """Get the global BindingManager instance.

    Returns:
        The global BindingManager
    """
    global _manager
    with _manager_lock:
        if _manager is None:
            _manager = BindingManager()
        return _manager


def set_binding_manager(manager: BindingManager) -> None:
    """Set the global BindingManager instance.

    Args:
        manager: The BindingManager to set as global
    """
    global _manager
    with _manager_lock:
        _manager = manager


def init_binding_manager(
    bindings_dir: Optional[str] = None,
    tool_registry: Any = None,
) -> BindingManager:
    """Initialize the global BindingManager with tool registry.

    Args:
        bindings_dir: Optional custom bindings directory
        tool_registry: Tool registry to use for execution

    Returns:
        The initialized global BindingManager
    """
    manager = BindingManager(bindings_dir=bindings_dir)

    if tool_registry is not None:
        set_tool_registry(tool_registry)

    manager.load_bindings_from_dir()
    set_binding_manager(manager)

    return manager
