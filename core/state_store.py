"""StateStore implementation for the Multi-Agent Collaboration System.

Provides hot and cold storage layers with delta-based synchronization.
Phase 1 implements in-memory hot storage with a stub cold storage interface.
"""

from __future__ import annotations

import logging
import threading
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Any

from core.models import DeltaUpdate, DeltaHandler, EntityType, DeltaOperation

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# Cold Storage Interface (Phase 2+)
# ------------------------------------------------------------------------------


class ColdStorage(ABC):
    """Abstract interface for cold (persistent) storage.

    Phase 1 provides a stub implementation. Phase 2 will implement
    actual file system or S3-based storage.
    """

    @abstractmethod
    def store(self, key: str, data: dict[str, Any]) -> None:
        """Store data to cold storage.

        Args:
            key: Storage key.
            data: Data to store.
        """
        pass

    @abstractmethod
    def retrieve(self, key: str) -> dict[str, Any] | None:
        """Retrieve data from cold storage.

        Args:
            key: Storage key.

        Returns:
            The stored data or None if not found.
        """
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete data from cold storage.

        Args:
            key: Storage key.

        Returns:
            True if deleted, False if not found.
        """
        pass


class StubColdStorage(ColdStorage):
    """Stub implementation of cold storage for Phase 1.

    This is a no-op implementation that logs operations but
    does not persist data. Will be replaced in Phase 2.
    """

    def __init__(self) -> None:
        """Initialize the stub cold storage."""
        self._data: dict[str, dict[str, Any]] = {}

    def store(self, key: str, data: dict[str, Any]) -> None:
        """Store data to stub cold storage (logs only in Phase 1)."""
        self._data[key] = data
        logger.debug("ColdStorage: storing key=%s (stub)", key)

    def retrieve(self, key: str) -> dict[str, Any] | None:
        """Retrieve data from stub cold storage."""
        logger.debug("ColdStorage: retrieving key=%s (stub)", key)
        return self._data.get(key)

    def delete(self, key: str) -> bool:
        """Delete data from stub cold storage."""
        if key in self._data:
            del self._data[key]
            logger.debug("ColdStorage: deleted key=%s (stub)", key)
            return True
        return False


# ------------------------------------------------------------------------------
# Hot Storage (In-Memory)
# ------------------------------------------------------------------------------


class HotStorage:
    """In-memory hot storage for fast read/write operations.

    Thread-safe implementation using a reentrant lock for concurrent access.
    """

    def __init__(self) -> None:
        """Initialize the hot storage."""
        self._data: dict[str, Any] = {}
        self._lock = threading.RLock()

    def get(self, key: str) -> Any | None:
        """Get a value by key.

        Args:
            key: Storage key.

        Returns:
            The stored value or None if not found.
        """
        with self._lock:
            return self._data.get(key)

    def set(self, key: str, value: Any) -> None:
        """Set a value by key.

        Args:
            key: Storage key.
            value: Value to store.
        """
        with self._lock:
            self._data[key] = value

    def delete(self, key: str) -> bool:
        """Delete a value by key.

        Args:
            key: Storage key.

        Returns:
            True if deleted, False if not found.
        """
        with self._lock:
            if key in self._data:
                del self._data[key]
                return True
            return False

    def list_keys(self, prefix: str | None = None) -> list[str]:
        """List all keys, optionally filtered by prefix.

        Args:
            prefix: Optional prefix to filter keys.

        Returns:
            List of matching keys.
        """
        with self._lock:
            if prefix is None:
                return list(self._data.keys())
            return [k for k in self._data.keys() if k.startswith(prefix)]

    def clear(self) -> None:
        """Clear all data from hot storage."""
        with self._lock:
            self._data.clear()


# ------------------------------------------------------------------------------
# StateStore
# ------------------------------------------------------------------------------


class StateStore:
    """Centralized state management with hot/cold storage layers.

    Provides delta-based synchronization through subscriptions.
    Phase 1 uses in-memory hot storage; cold storage is stubbed.

    Thread-safe implementation for concurrent agent access.
    """

    # Storage key prefixes for different entity types
    PREFIX_INTENT = "intent:"
    PREFIX_GOAL = "goal:"
    PREFIX_PLAN = "plan:"
    PREFIX_STATUS = "status:"

    def __init__(self, cold_storage: ColdStorage | None = None) -> None:
        """Initialize the StateStore.

        Args:
            cold_storage: Optional cold storage backend. Uses stub if not provided.
        """
        self._hot = HotStorage()
        self._cold = cold_storage or StubColdStorage()
        self._subscribers: dict[str, list[DeltaHandler]] = defaultdict(list)
        self._lock = threading.RLock()
        logger.info("StateStore initialized")

    # --------------------------------------------------------------------------
    # Core CRUD Operations
    # --------------------------------------------------------------------------

    def get(
        self,
        entity_type: EntityType,
        entity_id: str,
    ) -> Any | None:
        """Get an entity by type and ID.

        Args:
            entity_type: Type of the entity.
            entity_id: Unique identifier of the entity.

        Returns:
            The stored entity or None if not found.
        """
        key = self._make_key(entity_type, entity_id)
        return self._hot.get(key)

    def set(
        self,
        entity_type: EntityType,
        entity_id: str,
        value: Any,
        source_agent: str,
    ) -> DeltaUpdate:
        """Store an entity and return a delta update for subscribers.

        Args:
            entity_type: Type of the entity.
            entity_id: Unique identifier of the entity.
            value: The entity value to store.
            source_agent: ID of the agent making this update.

        Returns:
            A DeltaUpdate describing the changes.
        """
        key = self._make_key(entity_type, entity_id)
        existing = self._hot.get(key)
        operation = DeltaOperation.CREATE if existing is None else DeltaOperation.UPDATE

        changed_keys: list[str] = []
        if existing is None:
            changed_keys = list(value.keys()) if hasattr(value, "keys") else ["_value"]
        elif hasattr(value, "__dict__") and hasattr(existing, "__dict__"):
            changed_keys = [
                k for k in value.__dict__
                if getattr(value, k, None) != getattr(existing, k, None)
            ]

        self._hot.set(key, value)

        delta = DeltaUpdate.create(
            entity_type=entity_type,
            entity_id=entity_id,
            operation=operation,
            changed_keys=changed_keys if changed_keys else ["_value"],
            delta={"value": value},
            source_agent=source_agent,
        )

        self._dispatch_delta(delta)
        logger.debug("StateStore: %s %s/%s", operation.value, entity_type.value, entity_id)
        return delta

    def delete(
        self,
        entity_type: EntityType,
        entity_id: str,
        source_agent: str,
    ) -> DeltaUpdate | None:
        """Delete an entity and return a delta update.

        Args:
            entity_type: Type of the entity.
            entity_id: Unique identifier of the entity.
            source_agent: ID of the agent making this deletion.

        Returns:
            A DeltaUpdate describing the deletion, or None if not found.
        """
        key = self._make_key(entity_type, entity_id)
        existing = self._hot.get(key)

        if existing is None:
            return None

        self._hot.delete(key)

        delta = DeltaUpdate.create(
            entity_type=entity_type,
            entity_id=entity_id,
            operation=DeltaOperation.DELETE,
            changed_keys=[],
            delta={"deleted": True},
            source_agent=source_agent,
        )

        self._dispatch_delta(delta)
        logger.debug("StateStore: delete %s/%s", entity_type.value, entity_id)
        return delta

    # --------------------------------------------------------------------------
    # Delta Update Operations
    # --------------------------------------------------------------------------

    def delta_update(
        self,
        entity_type: EntityType,
        entity_id: str,
        changes: dict[str, Any],
        source_agent: str,
    ) -> DeltaUpdate:
        """Apply incremental changes to an entity.

        This is the primary method for state updates - it only updates
        the specified fields without touching others.

        Args:
            entity_type: Type of the entity.
            entity_id: Unique identifier of the entity.
            changes: Dictionary of field names to new values.
            source_agent: ID of the agent making this update.

        Returns:
            A DeltaUpdate describing the changes.
        """
        key = self._make_key(entity_type, entity_id)
        existing = self._hot.get(key)

        if existing is None:
            logger.warning("delta_update on non-existent entity: %s/%s", entity_type.value, entity_id)
            delta = DeltaUpdate.create(
                entity_type=entity_type,
                entity_id=entity_id,
                operation=DeltaOperation.CREATE,
                changed_keys=list(changes.keys()),
                delta=changes,
                source_agent=source_agent,
            )
            self._hot.set(key, changes)
        else:
            if hasattr(existing, "__dict__"):
                new_data = {**existing.__dict__, **changes}
                for k, v in new_data.items():
                    if hasattr(existing, k):
                        object.__setattr__(existing, k, v)
                self._hot.set(key, existing)
            else:
                self._hot.set(key, {**existing, **changes})

            delta = DeltaUpdate.create(
                entity_type=entity_type,
                entity_id=entity_id,
                operation=DeltaOperation.UPDATE,
                changed_keys=list(changes.keys()),
                delta=changes,
                source_agent=source_agent,
            )

        self._dispatch_delta(delta)
        logger.debug("StateStore: delta_update %s/%s with keys=%s", entity_type.value, entity_id, list(changes.keys()))
        return delta

    # --------------------------------------------------------------------------
    # Subscription Management
    # --------------------------------------------------------------------------

    def subscribe(
        self,
        entity_type: EntityType,
        handler: DeltaHandler,
    ) -> None:
        """Subscribe to delta updates for an entity type.

        Args:
            entity_type: Type of entity to subscribe to.
            handler: Callback function to receive DeltaUpdate events.
        """
        with self._lock:
            self._subscribers[entity_type.value].append(handler)
        logger.debug("Subscribed to %s events", entity_type.value)

    def subscribe_all(self, handler: DeltaHandler) -> None:
        """Subscribe to all delta updates regardless of entity type.

        Args:
            handler: Callback function to receive all DeltaUpdate events.
        """
        with self._lock:
            self._subscribers["*"].append(handler)
        logger.debug("Subscribed to all events")

    def unsubscribe(
        self,
        entity_type: EntityType,
        handler: DeltaHandler,
    ) -> bool:
        """Unsubscribe from delta updates for an entity type.

        Args:
            entity_type: Type of entity to unsubscribe from.
            handler: The callback to remove.

        Returns:
            True if the handler was found and removed.
        """
        with self._lock:
            handlers = self._subscribers[entity_type.value]
            if handler in handlers:
                handlers.remove(handler)
                return True
        return False

    def unsubscribe_all(self, handler: DeltaHandler) -> bool:
        """Unsubscribe from all delta updates.

        Args:
            handler: The callback to remove.

        Returns:
            True if the handler was found and removed from any subscription.
        """
        removed = False
        with self._lock:
            for key in list(self._subscribers.keys()):
                handlers = self._subscribers[key]
                if handler in handlers:
                    handlers.remove(handler)
                    removed = True
        return removed

    # --------------------------------------------------------------------------
    # Query Operations
    # --------------------------------------------------------------------------

    def list_by_type(self, entity_type: EntityType) -> list[Any]:
        """List all entities of a given type.

        Args:
            entity_type: Type of entities to list.

        Returns:
            List of stored entities.
        """
        prefix = self._get_prefix(entity_type)
        keys = self._hot.list_keys(prefix)
        return [self._hot.get(k) for k in keys if self._hot.get(k) is not None]

    def get_intent_chain(self, chain_id: str) -> Any | None:
        """Get an intent chain by ID.

        Args:
            chain_id: The chain identifier.

        Returns:
            The IntentChain or None if not found.
        """
        return self.get(EntityType.INTENT, chain_id)

    def get_goal(self, goal_id: str) -> Any | None:
        """Get a goal by ID.

        Args:
            goal_id: The goal identifier.

        Returns:
            The Goal or None if not found.
        """
        return self.get(EntityType.GOAL, goal_id)

    def get_plan(self, plan_id: str) -> Any | None:
        """Get a plan by ID.

        Args:
            plan_id: The plan identifier.

        Returns:
            The Plan or None if not found.
        """
        return self.get(EntityType.PLAN, plan_id)

    # --------------------------------------------------------------------------
    # Cold Storage Operations
    # --------------------------------------------------------------------------

    def archive_to_cold(
        self,
        entity_type: EntityType,
        entity_id: str,
    ) -> bool:
        """Archive an entity from hot to cold storage.

        Args:
            entity_type: Type of the entity.
            entity_id: Unique identifier of the entity.

        Returns:
            True if archived successfully.
        """
        key = self._make_key(entity_type, entity_id)
        data = self._hot.get(key)

        if data is None:
            return False

        cold_key = f"{key}:archived"
        if hasattr(data, "__dict__"):
            self._cold.store(cold_key, data.__dict__)
        else:
            self._cold.store(cold_key, data)

        self._hot.delete(key)
        logger.info("Archived %s/%s to cold storage", entity_type.value, entity_id)
        return True

    # --------------------------------------------------------------------------
    # Internal Helpers
    # --------------------------------------------------------------------------

    @staticmethod
    def _make_key(entity_type: EntityType, entity_id: str) -> str:
        """Create a storage key from entity type and ID."""
        return f"{entity_type.value}:{entity_id}"

    @staticmethod
    def _get_prefix(entity_type: EntityType) -> str:
        """Get the storage key prefix for an entity type."""
        return f"{entity_type.value}:"

    def _dispatch_delta(self, delta: DeltaUpdate) -> None:
        """Dispatch a delta update to all relevant subscribers.

        Args:
            delta: The delta update to dispatch.
        """
        handlers: list[DeltaHandler] = []
        with self._lock:
            if delta.entity_type.value in self._subscribers:
                handlers.extend(self._subscribers[delta.entity_type.value])
            if "*" in self._subscribers:
                handlers.extend(self._subscribers["*"])

        for handler in handlers:
            try:
                handler(delta)
            except Exception as e:
                logger.error("Error in delta handler: %s", e)
