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
                        intent_type = intent_data.get("type") or intent_data.get("name") or intent_data.get("category") or intent_data.get("intent", "unknown")
                        params = intent_data.get("params", {}) or intent_data.get("parameters", {})
                        confidence = intent_data.get("confidence", 0.9)

                        # 过滤低置信度意图（避免 LLM 返回过多无关意图）
                        if confidence < 0.5:
                            logger.debug(f"  Filtered intent {intent_type}: confidence {confidence} < 0.5")
                            continue

                        # Map category/name to standard intent types
                        intent_type = self._normalize_intent_type(intent_type)

                        logger.debug(f"  Intent: type={intent_type}, normalized={intent_type}, confidence={confidence}")
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

        # Enhancement: Always merge keyword intents that LLM didn't find
        # This ensures consultation-type intents (legal, medical, etc.) are captured
        keyword_intents = self._keyword_intents(query)
        existing_types = {n.intent for n in intent_nodes}
        merged_count = 0
        for node in keyword_intents:
            if node.intent not in existing_types:
                intent_nodes.append(node)
                merged_count += 1
        if merged_count > 0:
            logger.info(f"IntentAgent: Merged {merged_count} keyword intents not found by LLM")

        # 限制意图总数（避免过多无关意图）
        MAX_INTENTS = 5
        if len(intent_nodes) > MAX_INTENTS:
            # 按置信度排序，保留最高的
            intent_nodes = sorted(intent_nodes, key=lambda n: n.confidence, reverse=True)[:MAX_INTENTS]
            logger.info(f"IntentAgent: Limited intents to {MAX_INTENTS}")

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
        if any(w in raw for w in ["天气", "weather", "气温", "温度", "forecast"]):
            return "weather"

        # ========== 咨询团队类型 ==========
        # Legal
        if any(w in raw for w in ["法律", "legal", "合同", "contract", "协议", "条款", "违约金", "维权", "rights", "protection", "compliance", "合规", "资质"]):
            return "legal"
        # Medical
        if any(w in raw for w in ["医疗", "medical", "医院", "hospital", "医生", "doctor", "挂号", "registration", "症状", "symptom", "疾病", "disease", "治疗", "treatment", "药品", "medicine", "体检"]):
            return "medical"
        # Emotional
        if any(w in raw for w in ["情绪", "emotion", "心情", "压力", "stress", "焦虑", "anxiety", "抑郁", "depression", "孤独", "lonely", "恋爱", "love", "relationship", "分手", "divorce", "婚姻", "marriage", "夫妻", "感情", "沟通", "communication", "吵架", "fight", "冷战", "家庭", "family", "亲子", "parenting", "父母", "朋友", "friend", "社交", "social", "自我", "self", "成长", "growth", "自信", "confidence", "价值", "value", "意义", "meaning", "迷茫", "lost", "职业", "career", "人生", "life"]):
            return "emotional"
        # Finance
        if any(w in raw for w in ["投资", "investment", "理财", "financial", "基金", "fund", "股票", "stock", "债券", "bond", "收益", "return", "预算", "budget", "开销", "expense", "支出", "spending", "收入", "income", "储蓄", "savings", "负债", "debt", "贷款", "loan", "税务", "tax", "个税", "income_tax", "抵扣", "deduction", "报税", "tax_return", "退休", "retirement", "养老金", "pension", "社保", "social_insurance", "公积金", "housing_fund"]):
            return "finance"
        # Learning
        if any(w in raw for w in ["学习", "learning", "study", "计划", "plan", "规划", "planning", "目标", "goal", "效率", "efficiency", "考试", "exam", "备考", "preparation", "复习", "review", "技能", "skill", "编程", "programming", "语言", "language", "英语", "english", "时间管理", "time_management", "拖延", "procrastination", "专注", "focus"]):
            return "learning"
        # Travel
        if any(w in raw for w in ["旅行", "travel", "trip", "旅游", "tourism", "行程", "itinerary", "攻略", "guide", "酒店", "hotel", "机票", "flight", "预订", "booking", "签证", "visa", "护照", "passport", "景点", "attraction", "景区", "spot", "餐厅", "restaurant", "美食", "food", "打卡", "check-in"]):
            return "travel"

        return "unknown"

    def _keyword_intents(self, query: str) -> list[IntentNode]:
        """Extract intents using keyword matching - detect ALL matching intents."""
        nodes = []
        query_lower = query.lower()

        # ========== 车载相关意图 ==========
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
            # Match "去" followed by destination, stop at comma, punctuation, or end
            m = re_module.search(r'去([^\s,，。；]+)', query)
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

        # Weather
        if any(w in query_lower for w in ["天气", "气温", "明天"]):
            params = {}
            if "明天" in query:
                params["forecast_days"] = 2
            nodes.append(IntentNode(intent="weather", entities=params, confidence=0.9))

        # Door
        if any(w in query_lower for w in ["锁", "车门"]):
            nodes.append(IntentNode(intent="door", entities={}, confidence=0.9))

        # ========== 咨询团队意图 ==========
        # Legal - 法律、合同、维权、合规
        if any(w in query_lower for w in ["合同", "协议", "条款", "违约金", "签约", "法务", "legal", "维权", "投诉", "侵权", "合规", "资质", "许可"]):
            nodes.append(IntentNode(intent="legal", entities={"query": query}, confidence=0.9))

        # Medical - 医疗、症状、医院、挂号
        if any(w in query_lower for w in ["症状", "不舒服", "难受", "疼痛", "发烧", "医院", "挂号", "医生", "科室", "疾病", "病因", "治疗", "药品", "药物", "手术", "体检", "medical", "头晕", "失眠", "头疼", "胸闷", "咳嗽", "腹痛", "疲劳", "血糖", "血压"]):
            import re as re_module
            params = {"query": query}
            # 提取症状关键词
            symptom_keywords = ["血糖", "头疼", "胸闷", "咳嗽", "发烧", "腹痛", "疲劳", "失眠"]
            for kw in symptom_keywords:
                if kw in query:
                    params["symptom"] = kw
                    break
            # 提取时间信息
            duration_match = re_module.search(r'(\d+)天|住院|持续|一段时间', query)
            if duration_match:
                params["duration"] = duration_match.group()
            nodes.append(IntentNode(intent="medical", entities=params, confidence=0.9))

        # Emotional - 情绪、压力、恋爱、家庭、人际
        if any(w in query_lower for w in ["情绪", "心情", "难过", "焦虑", "压力", "抑郁", "孤独", "崩溃", "恋爱", "分手", "婚姻", "夫妻", "感情", "沟通", "吵架", "冷战", "家庭", "亲子", "父母", "孩子", "朋友", "友谊", "同事", "社交", "人际关系", "自我", "成长", "自信", "价值", "意义", "迷茫", "职业", "人生"]):
            nodes.append(IntentNode(intent="emotional", entities={"query": query}, confidence=0.9))

        # Finance - 投资、理财、预算、税务、退休
        if any(w in query_lower for w in ["投资", "理财", "基金", "股票", "债券", "收益", "预算", "开销", "支出", "收入", "储蓄", "负债", "贷款", "税务", "个税", "抵扣", "报税", "退休", "养老金", "社保", "公积金"]):
            nodes.append(IntentNode(intent="finance", entities={"query": query}, confidence=0.9))

        # Learning - 学习、考试、备考、技能、时间管理
        if any(w in query_lower for w in ["学习", "计划", "规划", "目标", "效率", "考试", "备考", "复习", "技能", "编程", "语言", "英语", "日语", "考证", "时间管理", "拖延", "专注", "学习方法"]):
            nodes.append(IntentNode(intent="learning", entities={"query": query}, confidence=0.9))

        # Travel - 旅行、酒店、签证、景点
        if any(w in query_lower for w in ["旅行", "旅游", "行程", "攻略", "酒店", "机票", "预订", "订票", "签证", "护照", "景点", "景区", "餐厅", "美食", "打卡", "推荐", "旅行计划"]):
            nodes.append(IntentNode(intent="travel", entities={"query": query}, confidence=0.9))

        if not nodes:
            nodes.append(IntentNode(intent="general", entities={"query": query}, confidence=0.5))

        return nodes


def create_intent_agent(llm: Any = None) -> IntentAgent:
    """Factory function to create IntentAgent."""
    return IntentAgent(llm=llm)
