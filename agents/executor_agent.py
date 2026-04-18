"""Executor Agent - L2+: Task execution using ToolRegistry."""

from __future__ import annotations

import logging
from typing import Any

from agents.langgraph_agents import BaseReActAgent
from core.models import AgentState, Goal, GoalStatus

logger = logging.getLogger(__name__)


EXECUTOR_SYSTEM_PROMPT = """你是一个Executor Agent (L2+)。你的任务是执行分配的目标。

根据目标类型调用相应的工具：
- climate_control: 调用空调控制
- navigation: 调用导航
- music_control: 调用音乐播放
- vehicle_status: 查询车辆状态
- door_control: 车门控制
- news: 获取新闻
- weather: 查询天气
- emergency: 紧急救援
- legal_*: 法律顾问工具
- medical_*: 医疗顾问工具
- emotional_*: 情绪支持工具
- finance_*: 财务规划工具
- learning_*: 学习教练工具
- travel_*: 旅行规划工具

执行后记录结果。"""

# 配置哪些工具类型使用LLM生成自然语言描述
USE_LLM_RESPONSE_TYPES = {
    "weather", "news", "vehicle_status", "music_control",
    # 咨询类工具也使用LLM生成
    "legal_contract_review", "legal_rights_protection", "legal_compliance_check",
    "medical_symptom_analysis", "medical_disease_info", "medical_hospital_recommend",
    "emotional_emotion_listen", "emotional_relationship_consult", "emotional_family_communication",
    "emotional_social_advice", "emotional_self_discovery",
    "finance_investment_analysis", "finance_budget_planning", "finance_tax_consult", "finance_retirement_plan",
    "learning_study_plan", "learning_skill_learning", "learning_exam_prepare", "learning_time_management",
    "travel_trip_plan", "travel_hotel_book", "travel_visa_consult", "travel_spot_recommend",
}


LLM_DESCRIPTION_PROMPT = """你是一个车载助手。请根据以下工具执行结果，用自然流畅的中文描述：

工具类型: {tool_type}
执行参数: {params}
返回状态: {state}

请生成一段简洁自然的描述，用于告诉用户执行结果（50字以内）。格式示例：
- 空调："已开启空调，温度24°C，制冷模式"
- 导航："已规划前往机场的路线，预计35分钟，畅通"
- 天气："北京今天晴天，25°C，适合出行"

直接返回描述文字，不要加引号或前缀。"""


class ExecutorAgent(BaseReActAgent):
    """L2+ Agent for task execution using ToolRegistry.

    Supports HYBRID mode: tries dynamic binding first, falls back to hardcoded.
    """

    def __init__(self, executor_id: str, llm: Any | None = None, binding_manager: Any = None):
        super().__init__(
            agent_id=f"executor_{executor_id}",
            name=f"Executor {executor_id}",
            role="L2+",
            system_prompt=EXECUTOR_SYSTEM_PROMPT,
        )
        self.executor_id = executor_id
        self.llm = llm
        self._registry = None
        self._binding_manager = binding_manager

    def _get_registry(self):
        """Lazy load ToolRegistry to avoid circular import."""
        if self._registry is None:
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from backend.tools import registry
            self._registry = registry
        return self._registry

    def _get_binding_manager(self):
        """Lazy load BindingManager to avoid circular import."""
        if self._binding_manager is None:
            try:
                from core.binding_manager import get_binding_manager
                self._binding_manager = get_binding_manager()
            except ImportError:
                logger.warning("BindingManager not available, using hardcoded fallback only")
                return None
        return self._binding_manager

    def set_binding_manager(self, manager: Any) -> None:
        """Set the binding manager for dynamic binding."""
        self._binding_manager = manager
        logger.info(f"Executor {self.executor_id} binding manager set")

    async def think(self, state: AgentState) -> str:
        """Analyze assigned goal."""
        goals = state.goals
        if not goals:
            return "No goals assigned"

        goal_ids = list(goals.keys())
        return f"Executing {len(goal_ids)} goals"

    async def act(self, state: AgentState, thought: str) -> dict[str, Any]:
        """Execute the goals using ToolRegistry."""
        goals = state.goals
        if not goals:
            return {"execution_results": {}}

        registry = self._get_registry()
        execution_results = {}

        for goal_id, goal in goals.items():
            try:
                result = self._execute_goal(goal, registry)
                goal.status = GoalStatus.COMPLETED

                # 如果是LLM增强类型，生成自然语言描述
                if goal.type in USE_LLM_RESPONSE_TYPES and self.llm:
                    description = await self._generate_llm_description(goal, result)
                else:
                    description = result.description

                execution_results[goal_id] = {
                    "status": "completed",
                    "output": description,
                    "state": result.state,
                }
            except Exception as e:
                goal.status = GoalStatus.FAILED
                execution_results[goal_id] = {
                    "status": "failed",
                    "output": str(e),
                    "error": str(e),
                }
                logger.error("Goal %s failed: %s", goal_id, e)

        completed = sum(1 for r in execution_results.values() if r.get("status") == "completed")
        logger.info("Executor %s: completed %d/%d goals", self.executor_id, completed, len(goals))

        return {
            "execution_results": execution_results,
            "metadata": {"_finished": True},
        }

    async def _generate_llm_description(self, goal: Goal, tool_result: Any) -> str:
        """用LLM生成自然语言描述"""
        if not self.llm:
            return tool_result.description

        intent_info = getattr(goal, 'result', {}) or {}
        entities = intent_info.get("entities", {})

        prompt = LLM_DESCRIPTION_PROMPT.format(
            tool_type=goal.type,
            params=entities,
            state=tool_result.state,
        )

        try:
            # 调用LLM生成描述
            messages = [{"role": "user", "content": prompt}]
            response = await self.llm.chat(messages, tools=[])
            # 解析 LLM 响应
            if isinstance(response, dict):
                content = response.get("content", [])
                for block in content:
                    if block.get("type") == "text":
                        return block.get("text", "").strip()
            return str(response).strip() if response else tool_result.description
        except Exception as e:
            logger.warning(f"LLM description failed, using fallback: {e}")
            return tool_result.description

    def _execute_goal(self, goal: Goal, registry) -> Any:
        """Execute a single goal using ToolRegistry.

        HYBRID MODE: Tries dynamic binding first, falls back to hardcoded.
        """
        goal_type = goal.type
        intent_info = getattr(goal, 'result', {}) or {}
        entities = intent_info.get("entities", {})

        # Build context for binding execution
        context = {
            "goal_type": goal_type,
            "intent": intent_info.get("intent", {}),
            "entities": entities,
        }

        # Try dynamic binding first (HYBRID mode)
        binding_manager = self._get_binding_manager()
        if binding_manager is not None:
            binding = binding_manager.get_binding(goal_type)
            if binding is not None:
                try:
                    from core.binding_executor import set_tool_registry
                    set_tool_registry(registry)
                    result = binding_manager.execute_binding(goal_type, context)
                    if result.success:
                        logger.info(f"Executed {goal_type} via dynamic binding")
                        # Convert ExecutionResult to tool result format
                        class BindingResult:
                            def __init__(self, exec_result):
                                self.description = exec_result.output
                                self.state = exec_result.state
                        return BindingResult(result)
                    else:
                        logger.warning(f"Dynamic binding failed for {goal_type}: {result.state.get('error')}, trying hardcoded fallback")
                except Exception as e:
                    logger.warning(f"Dynamic binding error for {goal_type}: {e}, trying hardcoded fallback")

        # Fall back to hardcoded mapping
        if goal_type == "climate_control":
            # Use control action with compound params
            params = {}
            if entities.get("temperature"):
                params["temperature"] = entities["temperature"]
            if entities.get("fan_speed"):
                params["fan_speed"] = entities["fan_speed"]
            params["power"] = True  # Turn on by default
            return registry.call_tool("climate_control", "control", **params)

        elif goal_type == "navigation":
            destination = entities.get("destination", "")
            return registry.call_tool("navigation", "navigate", destination=destination)

        elif goal_type == "music_control":
            return registry.call_tool("music_player", "play")

        elif goal_type == "vehicle_status":
            return registry.call_tool("vehicle_status", "get_status")

        elif goal_type == "door_control":
            return registry.call_tool("door_control", "lock")

        elif goal_type == "news":
            return registry.call_tool("news", "get_news")

        elif goal_type == "weather":
            location = entities.get("location", "北京")
            forecast_days = entities.get("forecast_days", 1)
            return registry.call_tool("get_weather", "get_weather", location=location, forecast_days=forecast_days)

        elif goal_type == "emergency":
            return registry.call_tool("emergency", "call", reason=entities.get("reason", ""))

        # ========== 法律顾问工具 ==========
        elif goal_type == "legal_contract_review":
            return registry.call_tool("legal_contract_review", "execute",
                contract_type=entities.get("contract_type"),
                risk_level=entities.get("risk_level"),
                issues=entities.get("issues"))

        elif goal_type == "legal_rights_protection":
            return registry.call_tool("legal_rights_protection", "execute",
                situation_summary=entities.get("situation_summary"),
                rights_analysis=entities.get("rights_analysis"))

        elif goal_type == "legal_compliance_check":
            return registry.call_tool("legal_compliance_check", "execute",
                check_target=entities.get("check_target"),
                compliance_status=entities.get("compliance_status"))

        # ========== 医疗顾问工具 ==========
        elif goal_type == "medical_symptom_analysis":
            return registry.call_tool("medical_symptom_analysis", "execute",
                symptom=entities.get("symptom"),
                duration=entities.get("duration"),
                severity=entities.get("severity"))

        elif goal_type == "medical_disease_info":
            return registry.call_tool("medical_disease_info", "execute",
                disease_name=entities.get("disease_name"),
                info_type=entities.get("info_type"))

        elif goal_type == "medical_hospital_recommend":
            return registry.call_tool("medical_hospital_recommend", "execute",
                symptom=entities.get("symptom"),
                location=entities.get("location"))

        # ========== 情绪支持工具 ==========
        elif goal_type == "emotional_emotion_listen":
            return registry.call_tool("emotional_emotion_listen", "execute",
                emotion_type=entities.get("emotion_type"),
                intensity=entities.get("intensity"))

        elif goal_type == "emotional_relationship_consult":
            return registry.call_tool("emotional_relationship_consult", "execute",
                relationship_type=entities.get("relationship_type"),
                issue=entities.get("issue"))

        elif goal_type == "emotional_family_communication":
            return registry.call_tool("emotional_family_communication", "execute",
                family_role=entities.get("family_role"),
                challenge=entities.get("challenge"))

        elif goal_type == "emotional_social_advice":
            return registry.call_tool("emotional_social_advice", "execute",
                situation=entities.get("situation"),
                goal=entities.get("goal"))

        elif goal_type == "emotional_self_discovery":
            return registry.call_tool("emotional_self_discovery", "execute",
                exploration_area=entities.get("exploration_area"),
                current_stage=entities.get("current_stage"))

        # ========== 财务规划工具 ==========
        elif goal_type == "finance_investment_analysis":
            return registry.call_tool("finance_investment_analysis", "execute",
                product_type=entities.get("product_type"),
                amount=entities.get("amount"))

        elif goal_type == "finance_budget_planning":
            return registry.call_tool("finance_budget_planning", "execute",
                monthly_income=entities.get("monthly_income"),
                monthly_expenses=entities.get("monthly_expenses"))

        elif goal_type == "finance_tax_consult":
            return registry.call_tool("finance_tax_consult", "execute",
                income=entities.get("income"),
                tax_type=entities.get("tax_type"))

        elif goal_type == "finance_retirement_plan":
            return registry.call_tool("finance_retirement_plan", "execute",
                current_age=entities.get("current_age"),
                retirement_age=entities.get("retirement_age"),
                current_savings=entities.get("current_savings"))

        # ========== 学习教练工具 ==========
        elif goal_type == "learning_study_plan":
            return registry.call_tool("learning_study_plan", "execute",
                subject=entities.get("subject"),
                target_level=entities.get("target_level"),
                available_time=entities.get("available_time"))

        elif goal_type == "learning_skill_learning":
            return registry.call_tool("learning_skill_learning", "execute",
                skill_name=entities.get("skill_name"),
                target_level=entities.get("target_level"))

        elif goal_type == "learning_exam_prepare":
            return registry.call_tool("learning_exam_prepare", "execute",
                exam_name=entities.get("exam_name"),
                exam_date=entities.get("exam_date"),
                days_remaining=entities.get("days_remaining"))

        elif goal_type == "learning_time_management":
            return registry.call_tool("learning_time_management", "execute",
                current_challenge=entities.get("current_challenge"),
                work_style=entities.get("work_style"))

        # ========== 旅行规划工具 ==========
        elif goal_type == "travel_trip_plan":
            return registry.call_tool("travel_trip_plan", "execute",
                destination=entities.get("destination"),
                duration=entities.get("duration"),
                travel_style=entities.get("travel_style"))

        elif goal_type == "travel_hotel_book":
            return registry.call_tool("travel_hotel_book", "execute",
                destination=entities.get("destination"),
                check_in=entities.get("check_in"),
                check_out=entities.get("check_out"),
                budget=entities.get("budget"))

        elif goal_type == "travel_visa_consult":
            return registry.call_tool("travel_visa_consult", "execute",
                destination=entities.get("destination"),
                visa_type=entities.get("visa_type"))

        elif goal_type == "travel_spot_recommend":
            return registry.call_tool("travel_spot_recommend", "execute",
                destination=entities.get("destination"),
                travel_style=entities.get("travel_style"))

        else:
            # Generic fallback - return error result
            class ErrorResult:
                def __init__(self):
                    self.description = f"Unknown goal type: {goal_type}"
                    self.state = {"error": f"Unsupported goal type: {goal_type}"}
            return ErrorResult()


def create_executor_agent(executor_id: str, llm: Any = None) -> ExecutorAgent:
    """Factory function to create ExecutorAgent."""
    return ExecutorAgent(executor_id=executor_id, llm=llm)
