"""State store using LangGraph Checkpointer and Store."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# LangGraph imports - graceful degradation
try:
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.store.memory import InMemoryStore
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    MemorySaver = None
    InMemoryStore = None


class StateStore:
    """State storage using LangGraph Checkpointer for persistence.

    This replaces the original DeltaUpdate-based EventBus state management
    with LangGraph's Checkpointer for thread-based persistence.

    Features:
    - Checkpointer: Saves/loads graph state at each checkpoint
    - Store: Cross-thread memory for user preferences and facts
    """

    def __init__(
        self,
        checkpointer: Any = None,
        store: Any = None,
    ):
        if not LANGGRAPH_AVAILABLE:
            logger.warning("LangGraph not available, StateStore is mock")
            self._mock = True
            return

        self._mock = False
        self.checkpointer = checkpointer or MemorySaver()
        self.store = store or InMemoryStore()
        logger.info("StateStore initialized with LangGraph persistence")

    @property
    def is_available(self) -> bool:
        """Check if LangGraph is available."""
        return not self._mock

    def save_state(self, thread_id: str, state: dict[str, Any], metadata: dict[str, Any] | None = None) -> None:
        """Save state to checkpoint.

        Args:
            thread_id: Thread identifier for isolation.
            state: State dict to save.
            metadata: Optional metadata.
        """
        if self._mock:
            return

        config = {"configurable": {"thread_id": thread_id}}
        try:
            self.checkpointer.put(config, state, metadata or {})
        except Exception as e:
            logger.error("Failed to save state: %s", e)

    def load_state(self, thread_id: str) -> dict[str, Any] | None:
        """Load state from checkpoint.

        Args:
            thread_id: Thread identifier.

        Returns:
            Saved state or None.
        """
        if self._mock:
            return None

        config = {"configurable": {"thread_id": thread_id}}
        try:
            return self.checkpointer.get(config)
        except Exception as e:
            logger.error("Failed to load state: %s", e)
            return None

    def save_memory(
        self,
        namespace: tuple[str, ...],
        key: str,
        value: dict[str, Any],
    ) -> None:
        """Save long-term memory.

        Args:
            namespace: Namespace tuple for organization.
            key: Memory key.
            value: Memory value.
        """
        if self._mock:
            return

        try:
            self.store.put(namespace, key, value)
        except Exception as e:
            logger.error("Failed to save memory: %s", e)

    def load_memory(
        self,
        namespace: tuple[str, ...],
        key: str,
    ) -> dict[str, Any] | None:
        """Load long-term memory.

        Args:
            namespace: Namespace tuple.
            key: Memory key.

        Returns:
            Memory value or None.
        """
        if self._mock:
            return None

        try:
            result = self.store.get(namespace, key)
            return result.dict() if result else None
        except Exception as e:
            logger.error("Failed to load memory: %s", e)
            return None

    def search_memory(
        self,
        namespace: tuple[str, ...],
        query: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search memory by query.

        Args:
            namespace: Namespace tuple.
            query: Search query.
            limit: Max results.

        Returns:
            List of matching memory items.
        """
        if self._mock:
            return []

        try:
            return [
                item.dict()
                for item in self.store.search(namespace, query, limit=limit)
            ]
        except Exception as e:
            logger.error("Failed to search memory: %s", e)
            return []

    def delete_memory(
        self,
        namespace: tuple[str, ...],
        key: str,
    ) -> None:
        """Delete memory item.

        Args:
            namespace: Namespace tuple.
            key: Memory key.
        """
        if self._mock:
            return

        try:
            self.store.delete(namespace, key)
        except Exception as e:
            logger.error("Failed to delete memory: %s", e)
