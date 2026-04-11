"""Intent Agent - L0: Intent recognition using MiniMax LLM."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from agents.langgraph_agents import BaseReActAgent
from core.models import AgentState, IntentChain, IntentNode, IntentStatus

logger = logging.getLogger(__name__)


INTENT_SYSTEM_PROMPT = """你是一个车载助手意图识别Agent。你的任务是从用户查询中提取多个意图。

用户可能会一次性请求多个操作，例如"打开空调、导航去机场、播放音乐"。

支持的意图类型：
- climate: 空调控制 (温度、风速、开关)
- navigation: 导航 (目的地、路线)
- music: 音乐播放 (播放、暂停、音量)
- vehicle_status: 车辆状态查询
- door: 车门控制 (锁门、解锁)
- news: 新闻查询
- emergency: 紧急救援

对于每个检测到的意图，提取：
1. 意图类型 (intent_type)
2. 关键参数 (params)，如温度、目的地等
3. 置信度 (confidence, 0.0-1.0)

分析用户查询，提取所有意图。"""


INTENT_USER_PROMPT = """用户查询: {message}

请提取所有意图并返回 JSON 格式：
{{
  "intents": [
    {{"type": "climate", "params": {{"temperature": 24}}, "confidence": 0.95}},
    {{"type": "navigation", "params": {{"destination": "机场"}}, "confidence": 0.95}}
  ]
}}"""


class IntentAgent(BaseReActAgent):
    """L0 Agent for intent recognition using MiniMax LLM."""

    def __init__(self, llm: Any | None = None):
        super().__init__(
            agent_id="intent_agent",
            name="Intent Recognition",
            role="L0",
            system_prompt=INTENT_SYSTEM_PROMPT,
        )
        self.llm = llm

    async def think(self, state: AgentState) -> str:
        """Analyze user query to extract intent using MiniMax LLM."""
        if self.llm is None:
            return self._keyword_fallback(state.user_query)

        query = state.user_query
        try:
            # Use MiniMax LLM for intent extraction
            messages = [
                {"role": "user", "content": INTENT_USER_PROMPT.format(message=query)}
            ]
            response = await self.llm.chat(
                messages=messages,
                tools=[],  # No tools needed for intent extraction
                system_prompt=INTENT_SYSTEM_PROMPT,
            )

            # Parse LLM response
            content = response.get("content", [])
            text = ""
            for block in content:
                if block.get("type") == "text":
                    text = block.get("text", "")
                    break

            # Extract intents from text response
            import json
            import re
            match = re.search(r'\{[^{}]*"intents"[^{}]*\}', text, re.DOTALL)
            if match:
                data = json.loads(match.group())
                return f"LLM extracted {len(data.get('intents', []))} intents"
            return "Could not parse LLM response"

        except Exception as e:
            logger.error("LLM intent extraction failed: %s", e)
            return self._keyword_fallback(query)

    def _keyword_fallback(self, query: str) -> str:
        """Fallback keyword-based extraction."""
        query_lower = query.lower()
        intents = []

        if any(w in query_lower for w in ["空调", "温度", "冷", "热", "暖气"]):
            intents.append("climate")
        if any(w in query_lower for w in ["导航", "去", "机场", "回家", "公司"]):
            intents.append("navigation")
        if any(w in query_lower for w in ["音乐", "播放", "暂停", "歌"]):
            intents.append("music")
        if any(w in query_lower for w in ["状态", "电量", "续航", "车况"]):
            intents.append("vehicle_status")
        if any(w in query_lower for w in ["锁", "门"]):
            intents.append("door")
        if any(w in query_lower for w in ["新闻", "资讯"]):
            intents.append("news")

        return f"Keyword fallback: {intents}"

    async def act(self, state: AgentState, thought: str) -> dict[str, Any]:
        """Create intent chain from extracted intents."""
        query = state.user_query
        intent_nodes = []

        # Try LLM-based extraction first
        if self.llm is not None:
            try:
                import json
                import re

                messages = [
                    {"role": "user", "content": INTENT_USER_PROMPT.format(message=query)}
                ]
                response = await self.llm.chat(
                    messages=messages,
                    tools=[],
                    system_prompt=INTENT_SYSTEM_PROMPT,
                )

                content = response.get("content", [])
                text = ""
                for block in content:
                    if block.get("type") == "text":
                        text = block.get("text", "")
                        break

                # Strip code block markers if present
                text = re.sub(r'^```json\s*', '', text.strip(), flags=re.MULTILINE)
                text = re.sub(r'\s*```$', '', text.strip(), flags=re.MULTILINE)

                # Parse JSON response
                data = None

                # Try direct JSON parse first
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    # Try to find JSON block with intents
                    try:
                        # Find {...} containing "intents"
                        for match in re.finditer(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text):
                            try:
                                candidate = json.loads(match.group())
                                if "intents" in candidate:
                                    data = candidate
                                    break
                            except:
                                continue
                    except:
                        pass

                if data and "intents" in data:
                    logger.debug(f"LLM parsed {len(data.get('intents', []))} intents from data: {data}")
                    for intent_data in data.get("intents", []):
                        # Handle various field names from LLM
                        intent_type = intent_data.get("type") or intent_data.get("name") or intent_data.get("category", "unknown")
                        params = intent_data.get("params", {}) or intent_data.get("parameters", {})
                        confidence = intent_data.get("confidence", 0.9)

                        # Map category/name to standard intent types
                        intent_type = self._normalize_intent_type(intent_type)

                        logger.debug(f"  Intent: type={intent_type}, normalized={intent_type}")
                        if intent_type != "unknown":
                            node = IntentNode(
                                intent=intent_type,
                                entities=params,
                                confidence=confidence,
                            )
                            intent_nodes.append(node)
            except Exception as e:
                logger.error("LLM act failed: %s", e)

        # Fallback to keyword-based if no intents found
        if not intent_nodes:
            intent_nodes = self._keyword_intents(query)

        intent_chain = IntentChain(
            nodes=intent_nodes,
            current_node_id=intent_nodes[0].id if intent_nodes else str(uuid.uuid4()),
        )

        logger.info("IntentAgent: %d intents extracted", len(intent_nodes))
        for node in intent_nodes:
            logger.info("  - %s (confidence: %.2f)", node.intent, node.confidence)

        return {
            "intent_chain": intent_chain,
            "metadata": {"_finished": True},
        }

    def _normalize_intent_type(self, raw_type: str) -> str:
        """Normalize LLM intent type to standard types."""
        raw = raw_type.lower()

        # Map various LLM outputs to standard types
        if any(w in raw for w in ["音乐", "media", "播放", "song", "audio", "play_music", "music_play", "music", "music_control"]):
            return "music"
        if any(w in raw for w in ["空调", "climate", "temperature", "温度", "暖", "冷", "control_ac", "ac_control", "ac", "climate_control"]):
            return "climate"
        if any(w in raw for w in ["导航", "navigation", "nav", "route", "路线", "去", "navigate"]):
            return "navigation"
        if any(w in raw for w in ["状态", "vehicle", "status", "电量", "续航", "车", "vehicle_status"]):
            return "vehicle_status"
        if any(w in raw for w in ["门", "door", "锁", "door_control"]):
            return "door"
        if any(w in raw for w in ["新闻", "news", "资讯"]):
            return "news"
        if any(w in raw for w in ["紧急", "emergency", "救援"]):
            return "emergency"

        return "unknown"

    def _keyword_intents(self, query: str) -> list[IntentNode]:
        """Extract intents using keyword matching - detect ALL matching intents."""
        nodes = []
        query_lower = query.lower()

        # Check for each intent type independently
        # Climate
        if any(w in query_lower for w in ["空调", "温度", "冷", "热", "暖气"]):
            params = {}
            import re as re_module
            m = re_module.search(r'(\d+)度', query)
            if m:
                params["temperature"] = int(m.group(1))
            nodes.append(IntentNode(intent="climate", entities=params, confidence=0.9))

        # Navigation
        if any(w in query_lower for w in ["导航", "去", "机场", "回家", "公司"]):
            import re as re_module
            dest = ""
            m = re_module.search(r'去(.+?)(?:的|且|$)', query)
            if m:
                dest = m.group(1).strip()
            nodes.append(IntentNode(intent="navigation", entities={"destination": dest}, confidence=0.9))

        # Music
        if any(w in query_lower for w in ["音乐", "播放", "歌", "听"]):
            nodes.append(IntentNode(intent="music", entities={}, confidence=0.9))

        # Vehicle status
        if any(w in query_lower for w in ["状态", "电量", "续航", "车况"]):
            nodes.append(IntentNode(intent="vehicle_status", entities={}, confidence=0.9))

        # News
        if any(w in query_lower for w in ["新闻", "资讯"]):
            nodes.append(IntentNode(intent="news", entities={}, confidence=0.9))

        # Door
        if any(w in query_lower for w in ["锁", "车门"]):
            nodes.append(IntentNode(intent="door", entities={}, confidence=0.9))

        if not nodes:
            nodes.append(IntentNode(intent="general", entities={"query": query}, confidence=0.5))

        return nodes


def create_intent_agent(llm: Any = None) -> IntentAgent:
    """Factory function to create IntentAgent."""
    return IntentAgent(llm=llm)
