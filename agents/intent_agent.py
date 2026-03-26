"""Intent Agent - L0 Intent Recognition."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from core.base_agent import BaseAgent, AgentRole
from core.event_bus import EventBus
from core.models import (
    EntityType,
    IntentNode,
    IntentChain,
    IntentStatus,
)
from core.state_store import StateStore

logger = logging.getLogger(__name__)


class IntentAgent(BaseAgent):
    """L0 - Intent Recognition Agent.

    Extracts user intent from queries and maintains intent chains
    across multi-turn conversations.
    """

    AGENT_ID = "intent_agent"

    # Keyword mapping for stub intent recognition
    INTENT_KEYWORDS = {
        "search": ["search", "find", "look up", "查询", "搜索", "找"],
        "calculate": ["calculate", "compute", "计算", "等于"],
        "create": ["create", "make", "生成", "创建", "新建"],
        "explain": ["explain", "what is", "什么是", "解释", "说明"],
        "list": ["list", "show", "列出", "显示", "有哪些"],
    }

    def __init__(
        self,
        state_store: StateStore | None = None,
        event_bus: EventBus | None = None,
    ):
        super().__init__(
            agent_id=self.AGENT_ID,
            name="Intent Recognition",
            role=AgentRole.INTENT,
            state_store=state_store,
            event_bus=event_bus,
        )

    def run(self, input_text: str) -> IntentChain:
        """Recognize intent from user query.

        Args:
            input_text: User query string.

        Returns:
            IntentChain with recognized intent and entities.
        """
        # Get recent intent history
        recent_chains = self._get_intent_history(limit=5)
        parent_id = recent_chains[-1].current_node_id if recent_chains else None

        # Extract intent (stub implementation)
        intent_node = self._extract_intent_stub(input_text, parent_id)

        # Build or extend intent chain
        if recent_chains:
            chain = recent_chains[-1].with_node(intent_node)
        else:
            chain = IntentChain.create(intent_node)

        # Store in StateStore
        self._store_entity(EntityType.INTENT, chain.chain_id, chain)

        # Publish event
        self._emit_delta(
            EntityType.INTENT,
            chain.chain_id,
            {
                "current_node_id": chain.current_node_id,
                "current_intent": intent_node.intent,
            },
        )

        logger.info("Intent recognized: %s (confidence: %.2f)", intent_node.intent, intent_node.confidence)
        return chain

    def _get_intent_history(self, limit: int = 5) -> list[IntentChain]:
        """Get recent intent chains from StateStore."""
        chains = self.state_store.list_by_type(EntityType.INTENT)
        return chains[-limit:] if chains else []

    def _extract_intent_stub(self, query: str, parent_id: str | None) -> IntentNode:
        """Simple keyword-based intent extraction for Phase 2.

        In Phase 3+, this will be replaced with LLM-based extraction.
        """
        query_lower = query.lower()

        for intent_type, keywords in self.INTENT_KEYWORDS.items():
            if any(kw in query_lower for kw in keywords):
                return IntentNode.create(
                    intent=intent_type,
                    entities={"query": query, "keywords": [kw for kw in keywords if kw in query_lower]},
                    confidence=0.8,
                    parent_id=parent_id,
                    status=IntentStatus.ACTIVE,
                )

        # Default to general intent
        return IntentNode.create(
            intent="general",
            entities={"query": query},
            confidence=0.5,
            parent_id=parent_id,
            status=IntentStatus.ACTIVE,
        )
