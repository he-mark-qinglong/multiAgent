"""Synthesizer Agent - L1: Result synthesis using ReAct."""

from __future__ import annotations

import logging
from typing import Any

from agents.langgraph_agents import BaseReActAgent
from core.models import AgentState, FinalResponse

logger = logging.getLogger(__name__)


SYNTHESIZER_SYSTEM_PROMPT = """你是一个Synthesizer Agent (L1)。你的任务是将执行结果汇总成自然语言回复。

根据执行结果生成友好的中文回复，包括：
1. 总结完成的任务
2. 简要说明结果（如温度、目的地等）
3. 友好的结束语

保持回复简洁、自然。"""


class SynthesizerAgent(BaseReActAgent):
    """L1 Agent for result synthesis."""

    def __init__(self, llm: Any | None = None):
        super().__init__(
            agent_id="synthesizer_agent",
            name="Result Synthesizer",
            role="L1",
            system_prompt=SYNTHESIZER_SYSTEM_PROMPT,
        )
        self.llm = llm

    async def think(self, state: AgentState) -> str:
        """Analyze execution results."""
        results = state.execution_results
        goals = state.goals

        completed = sum(1 for g in goals.values() if g.status.value == "completed")
        failed = sum(1 for g in goals.values() if g.status.value == "failed")

        return f"Synthesizing {len(results)} results: {completed} completed, {failed} failed"

    async def act(self, state: AgentState, thought: str) -> dict[str, Any]:
        """Generate final response."""
        results = state.execution_results
        goals = state.goals

        completed = sum(1 for g in goals.values() if g.status.value == "completed")
        failed = sum(1 for g in goals.values() if g.status.value == "failed")
        total = len(goals)

        # Generate natural language response
        response = self._build_response(results, goals, completed, failed, total)

        logger.info("SynthesizerAgent: %s", response[:100])

        return {
            "final_response": response,
            "metadata": {"_finished": True},
        }

    def _build_response(self, results: dict, goals: dict, completed: int, failed: int, total: int) -> str:
        """Build natural language response from results."""
        if not results:
            return "没有可用的执行结果。"

        # Intent type to Chinese name mapping
        intent_names = {
            "climate": "空调",
            "navigation": "导航",
            "music": "音乐",
            "vehicle_status": "车辆状态",
            "door": "车门",
            "news": "新闻",
            "emergency": "紧急救援",
            "general": "任务",
        }

        parts = []

        # Process each goal in order
        for goal_id, goal in goals.items():
            result = results.get(goal_id, {})
            output = result.get("output", "")
            status = result.get("status", "")

            if status == "failed":
                parts.append(f"❌ {goal.description}失败")
                continue

            # Get intent type from goal's stored result
            intent_info = getattr(goal, 'result', {}) or {}
            intent_type = intent_info.get("intent", "general")
            intent_name = intent_names.get(intent_type, goal.description)

            # Build descriptive response based on intent type
            if intent_type == "climate":
                state = result.get("state", {})
                temp = state.get("temperature", "N/A")
                mode = state.get("mode", "")
                parts.append(f"✅ 已开启{intent_name}，温度{temp}°C，{mode}模式")
            elif intent_type == "navigation":
                state = result.get("state", {})
                dest = state.get("destination", "目的地")
                # duration can be "25分钟" (already formatted) or number
                duration = state.get("duration", "N/A")
                if duration != "N/A" and not duration.endswith("分钟"):
                    duration = f"{duration}分钟"
                traffic = state.get("traffic", "")
                parts.append(f"🧭 已规划前往「{dest}」的路线，预计{duration}，{traffic}")
            elif intent_type == "music":
                state = result.get("state", {})
                song = state.get("current_song", ["未知歌曲"])[0] if state.get("current_song") else "未知歌曲"
                parts.append(f"🎵 正在播放「{song}」")
            elif intent_type == "vehicle_status":
                state = result.get("state", {})
                battery = state.get("battery", "N/A")
                range_km = state.get("range_km", "N/A")
                parts.append(f"🚗 车辆状态：电量{battery}%，续航约{range_km}km")
            elif intent_type == "news":
                parts.append(f"📰 {output}")
            elif intent_type == "door":
                parts.append(f"🔒 {output}")
            else:
                parts.append(f"✅ {output}")

        # Build final response
        if completed == total:
            if len(parts) == 1:
                response = parts[0]
            else:
                response = "，".join(parts[:-1]) + "，" + parts[-1]
            response = "已为您" + response.lstrip("已为您")
        else:
            response = "，".join(parts)
            if failed > 0:
                response += f"\n⚠️ {failed}个任务失败"

        return response


def create_synthesizer_agent(llm: Any = None) -> SynthesizerAgent:
    """Factory function to create SynthesizerAgent."""
    return SynthesizerAgent(llm=llm)
