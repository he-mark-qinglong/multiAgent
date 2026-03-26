"""Intent Agent - L0: Intent recognition using ReAct."""

from __future__ import annotations

import logging
from typing import Any

from agents.langgraph_agents import BaseReActAgent
from core.models import AgentState, IntentChain, IntentNode, IntentStatus

logger = logging.getLogger(__name__)


INTENT_SYSTEM_PROMPT = """You are an Intent Recognition Agent (L0).
Your task is to understand the user's query and extract:
1. The primary intent
2. Key entities mentioned
3. The confidence level

Think step by step about what the user wants.
Output a clear intent description and extracted entities."""


class IntentAgent(BaseReActAgent):
    """L0 Agent for intent recognition.

    Uses ReAct pattern internally for reasoning about user intent.
    """

    def __init__(self, llm: Any | None = None):
        super().__init__(
            agent_id="intent_agent",
            name="Intent Recognition",
            role="L0",
            system_prompt=INTENT_SYSTEM_PROMPT,
        )
        self.llm = llm

    async def think(self, state: AgentState) -> str:
        """Analyze user query to extract intent."""
        query = state.user_query

        # Simple keyword-based intent extraction
        # In production, this would use LLM
        keywords = self._extract_intent_keywords(query)

        return f"Analyzing query: '{query[:50]}...'. Keywords: {keywords}"

    def _extract_intent_keywords(self, query: str) -> dict[str, Any]:
        """Extract intent keywords from query.

        Stub implementation - in production use LLM.
        """
        query_lower = query.lower()
        intent = "general_query"
        entities = {}

        # Simple keyword extraction
        if any(w in query_lower for w in ["search", "find", "look up", "搜索", "查找"]):
            intent = "search"
        elif any(w in query_lower for w in ["create", "make", "generate", "创建", "生成"]):
            intent = "create"
        elif any(w in query_lower for w in ["update", "modify", "change", "修改"]):
            intent = "update"
        elif any(w in query_lower for w in ["delete", "remove", "删除"]):
            intent = "delete"
        elif any(w in query_lower for w in ["explain", "what", "how", "解释", "什么", "怎么"]):
            intent = "explanation"

        # Extract entities (simple)
        words = query.split()
        entities["word_count"] = len(words)

        return {"intent": intent, "entities": entities}

    async def act(self, state: AgentState, thought: str) -> dict[str, Any]:
        """Create intent chain from extracted intent."""
        query = state.user_query
        extracted = self._extract_intent_keywords(query)

        intent_node = IntentNode(
            intent=extracted["intent"],
            entities=extracted["entities"],
            confidence=0.9,
        )

        intent_chain = IntentChain(
            nodes=[intent_node],
            current_node_id=intent_node.id,
        )

        logger.info("IntentAgent: %s (confidence: %.2f)", intent_node.intent, intent_node.confidence)

        return {
            "intent_chain": intent_chain,
            "metadata": {"_finished": True},  # End ReAct loop
        }


def create_intent_agent(llm: Any = None) -> IntentAgent:
    """Factory function to create IntentAgent."""
    return IntentAgent(llm=llm)
