"""工具层 - 复用 tests/mock_tools，复用不复制。

KISS: 所有工具实现都在 tests/mock_tools/，这里只做 HTTP 适配。
"""
import sys
import os

# 复用 tests/mock_tools（不复制代码）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.mock_tools import (
    ToolResult,
    ClimateTool,
    NavigationTool,
    MusicTool,
    VehicleStatusTool,
    WeatherTool,
    DoorTool,
    EmergencyTool,
    NewsTool,
    LegalContractReviewTool,
    LegalRightsProtectionTool,
    LegalComplianceCheckTool,
    MedicalSymptomAnalysisTool,
    MedicalDiseaseInfoTool,
    MedicalHospitalRecommendTool,
    EmotionalEmotionListenTool,
    EmotionalRelationshipConsultTool,
    EmotionalFamilyCommunicationTool,
    EmotionalSocialAdviceTool,
    EmotionalSelfDiscoveryTool,
    FinanceInvestmentAnalysisTool,
    FinanceBudgetPlanningTool,
    FinanceTaxConsultTool,
    FinanceRetirementPlanTool,
    LearningStudyPlanTool,
    LearningSkillLearningTool,
    LearningExamPrepareTool,
    LearningTimeManagementTool,
    TravelTripPlanTool,
    TravelHotelBookTool,
    TravelVisaConsultTool,
    TravelSpotRecommendTool,
    MCP_TOOLS,
)


# ============================================================================
# 工具注册表 (单例，跨请求共享状态)
# ============================================================================

class ToolRegistry:
    """全局工具注册表。"""

    def __init__(self) -> None:
        # 车载控制类
        self.climate = ClimateTool()
        self.navigation = NavigationTool()
        self.music = MusicTool()
        self.vehicle = VehicleStatusTool()
        self.weather = WeatherTool()
        self.door = DoorTool()
        self.emergency = EmergencyTool()
        self.news = NewsTool()
        # 法律类
        self.legal_contract_review = LegalContractReviewTool()
        self.legal_rights_protection = LegalRightsProtectionTool()
        self.legal_compliance_check = LegalComplianceCheckTool()
        # 医疗类
        self.medical_symptom_analysis = MedicalSymptomAnalysisTool()
        self.medical_disease_info = MedicalDiseaseInfoTool()
        self.medical_hospital_recommend = MedicalHospitalRecommendTool()
        # 情绪类
        self.emotional_emotion_listen = EmotionalEmotionListenTool()
        self.emotional_relationship_consult = EmotionalRelationshipConsultTool()
        self.emotional_family_communication = EmotionalFamilyCommunicationTool()
        self.emotional_social_advice = EmotionalSocialAdviceTool()
        self.emotional_self_discovery = EmotionalSelfDiscoveryTool()
        # 财务类
        self.finance_investment_analysis = FinanceInvestmentAnalysisTool()
        self.finance_budget_planning = FinanceBudgetPlanningTool()
        self.finance_tax_consult = FinanceTaxConsultTool()
        self.finance_retirement_plan = FinanceRetirementPlanTool()
        # 学习类
        self.learning_study_plan = LearningStudyPlanTool()
        self.learning_skill_learning = LearningSkillLearningTool()
        self.learning_exam_prepare = LearningExamPrepareTool()
        self.learning_time_management = LearningTimeManagementTool()
        # 旅行类
        self.travel_trip_plan = TravelTripPlanTool()
        self.travel_hotel_book = TravelHotelBookTool()
        self.travel_visa_consult = TravelVisaConsultTool()
        self.travel_spot_recommend = TravelSpotRecommendTool()

    def list_tools(self) -> list[dict]:
        """返回所有工具定义（MCP 格式）。"""
        # MCP_TOOLS is already a list of tool schemas
        return MCP_TOOLS if isinstance(MCP_TOOLS, list) else list(MCP_TOOLS.values())

    def call_tool(self, name: str, action: str, **kwargs) -> ToolResult:
        """统一调用接口。"""
        tool_map = {
            # 车载控制类
            "climate_control": self.climate,
            "navigation": self.navigation,
            "music_control": self.music,
            "vehicle_status": self.vehicle,
            "get_weather": self.weather,
            "door_control": self.door,
            "emergency": self.emergency,
            "news": self.news,
            # 法律类
            "legal_contract_review": self.legal_contract_review,
            "legal_rights_protection": self.legal_rights_protection,
            "legal_compliance_check": self.legal_compliance_check,
            # 医疗类
            "medical_symptom_analysis": self.medical_symptom_analysis,
            "medical_disease_info": self.medical_disease_info,
            "medical_hospital_recommend": self.medical_hospital_recommend,
            # 情绪类
            "emotional_emotion_listen": self.emotional_emotion_listen,
            "emotional_relationship_consult": self.emotional_relationship_consult,
            "emotional_family_communication": self.emotional_family_communication,
            "emotional_social_advice": self.emotional_social_advice,
            "emotional_self_discovery": self.emotional_self_discovery,
            # 财务类
            "finance_investment_analysis": self.finance_investment_analysis,
            "finance_budget_planning": self.finance_budget_planning,
            "finance_tax_consult": self.finance_tax_consult,
            "finance_retirement_plan": self.finance_retirement_plan,
            # 学习类
            "learning_study_plan": self.learning_study_plan,
            "learning_skill_learning": self.learning_skill_learning,
            "learning_exam_prepare": self.learning_exam_prepare,
            "learning_time_management": self.learning_time_management,
            # 旅行类
            "travel_trip_plan": self.travel_trip_plan,
            "travel_hotel_book": self.travel_hotel_book,
            "travel_visa_consult": self.travel_visa_consult,
            "travel_spot_recommend": self.travel_spot_recommend,
        }
        tool = tool_map.get(name)
        if not tool:
            return ToolResult(
                success=False,
                state={},
                description=f"❌ 未知工具: {name}",
                tool_name=name,
            )

        # 动作映射 - 使用统一的 execute 方法
        action_map = {
            # ClimateTool: execute(action, temperature, wind_speed, mode)
            "turn_on": lambda: tool.execute(action="on", temperature=kwargs.get("temperature", 24), wind_speed=kwargs.get("wind_speed", 3), mode=kwargs.get("mode", "auto")),
            "turn_off": lambda: tool.execute(action="off"),
            "set_temperature": lambda: tool.execute(action="set_temp", temperature=int(kwargs.get("value", 24))),
            "set_fan_speed": lambda: tool.execute(action="set_wind", wind_speed=int(kwargs.get("value", 3))),
            "get_status": lambda: tool.get_status() if hasattr(tool, 'get_status') else tool.execute(),  # WeatherTool/VehicleStatusTool 有 get_status()
            "control": lambda: self._climate_control(tool, kwargs),
            # NavigationTool: execute(destination, route_preference)
            "navigate": lambda: tool.execute(destination=kwargs.get("destination", "")),
            "get_traffic": lambda: tool.execute(destination=kwargs.get("destination", "当前位置")),
            "cancel": lambda: tool.cancel() if hasattr(tool, 'cancel') else None,
            # MusicTool: execute(action, song, volume)
            "play": lambda: tool.execute(action="play", song=kwargs.get("song"), volume=kwargs.get("volume")),
            "pause": lambda: tool.execute(action="pause"),
            "skip": lambda: tool.execute(action="next"),
            "set_volume": lambda: tool.execute(action="volume", volume=int(kwargs.get("value", 50))),
            "pause": lambda: tool.pause(),
            "skip": lambda: tool.skip(),
            "set_volume": lambda: tool.set_volume(int(kwargs.get("value", 50))),
            # DoorTool: execute(action, door)
            "lock": lambda: tool.execute(action="lock", door=kwargs.get("door", "all")),
            "unlock": lambda: tool.execute(action="unlock", door=kwargs.get("door", "all")),
            # EmergencyTool
            "call": lambda: tool.execute(emergency_type=kwargs.get("reason", "紧急求助")),
            # NewsTool / VehicleStatusTool
            "get_news": lambda: tool.get_news(simulate_delay=True),
            # WeatherTool
            "get_weather": lambda: tool.get_weather(
                location=kwargs.get("location", "北京"),
                forecast_days=int(kwargs.get("forecast_days", 1))
            ),
            # 新工具通用 execute 方法
            "execute": lambda: tool.execute(**kwargs) if hasattr(tool, 'execute') else ToolResult(
                success=False, state={}, description=f"工具 {name} 不支持 execute 方法", tool_name=name
            ),
        }

        handler = action_map.get(action)
        if not handler:
            return ToolResult(
                success=False,
                state={},
                description=f"❌ 未知动作: {action}",
                tool_name=name,
            )

        try:
            result = handler()
            # 如果返回的是 dict，转换为 ToolResult
            if isinstance(result, dict):
                # 尝试从多个可能的字段中提取 description
                description = (
                    result.get("description") or
                    result.get("message") or
                    result.get("summary") or
                    result.get("symptom_summary") or
                    result.get("opinion_type") or
                    result.get("analysis_type") or
                    result.get("consultation_type") or
                    result.get("plan_type") or
                    result.get("recommendation_type") or
                    result.get("info_type") or
                    result.get("response_type") or
                    result.get("skill_type") or
                    result.get("trip_summary") or
                    result.get("learning_path") or
                    str(result.get("success", ""))
                )
                return ToolResult(
                    success=result.get("success", True),
                    state=result.get("data", result.get("state", {})),
                    description=description,
                    tool_name=name,
                    error=result.get("error"),
                )
            return result
        except Exception as e:
            return ToolResult(
                success=False,
                state={},
                description=f"❌ 执行失败: {e}",
                tool_name=name,
                error=str(e),
            )

    def _climate_control(self, tool, kwargs) -> ToolResult:
        """处理 climate_control 的复合参数 (power, temperature, fan_speed)。

        ClimateTool uses execute(action, temperature, wind_speed, mode) interface.
        """
        power = kwargs.get("power")
        temperature = kwargs.get("temperature")
        fan_speed = kwargs.get("fan_speed")
        mode = kwargs.get("mode", "auto")

        # 如果指定了 power，决定 action
        if power is not None:
            action = "on" if power else "off"
        else:
            action = "on"  # 默认开

        # 如果同时指定了温度，用 set_temp
        if temperature is not None:
            action = "set_temp"

        # 使用统一的 execute 方法
        result = tool.execute(
            action=action,
            temperature=temperature if temperature is not None else 24,
            wind_speed=fan_speed if fan_speed is not None else 3,
            mode=mode
        )

        if isinstance(result, dict):
            return ToolResult(
                success=result.get("success", True),
                state=result.get("data", {}),
                description=result.get("message", ""),
                tool_name="climate_control",
                error=result.get("error"),
            )
        return result


# 全局单例
registry = ToolRegistry()


# ============================================================================
# Goal Type → Tool/Action 映射表 (hardcoded fallback)
# 这是一个简单的映射表，用于在没有binding配置时提供fallback
# 优先使用binding配置，只有在binding失败时才使用此表
# ============================================================================

GOAL_TYPE_TO_TOOL_ACTION = {
    # 车载控制
    "climate_control": ("climate_control", "control"),
    "navigation": ("navigation", "navigate"),
    "music_control": ("music_control", "play"),
    "vehicle_status": ("vehicle_status", "get_status"),
    "door_control": ("door_control", "lock"),
    "news": ("news", "execute"),
    "weather": ("get_weather", "get_weather"),
    "emergency": ("emergency", "call"),
    # 法律顾问
    "legal_contract_review": ("legal_contract_review", "execute"),
    "legal_rights_protection": ("legal_rights_protection", "execute"),
    "legal_compliance_check": ("legal_compliance_check", "execute"),
    # 医疗顾问
    "medical_symptom_analysis": ("medical_symptom_analysis", "execute"),
    "medical_disease_info": ("medical_disease_info", "execute"),
    "medical_hospital_recommend": ("medical_hospital_recommend", "execute"),
    # 情绪支持
    "emotional_emotion_listen": ("emotional_emotion_listen", "execute"),
    "emotional_relationship_consult": ("emotional_relationship_consult", "execute"),
    "emotional_family_communication": ("emotional_family_communication", "execute"),
    "emotional_social_advice": ("emotional_social_advice", "execute"),
    "emotional_self_discovery": ("emotional_self_discovery", "execute"),
    # 财务规划
    "finance_investment_analysis": ("finance_investment_analysis", "execute"),
    "finance_budget_planning": ("finance_budget_planning", "execute"),
    "finance_tax_consult": ("finance_tax_consult", "execute"),
    "finance_retirement_plan": ("finance_retirement_plan", "execute"),
    # 学习教练
    "learning_study_plan": ("learning_study_plan", "execute"),
    "learning_skill_learning": ("learning_skill_learning", "execute"),
    "learning_exam_prepare": ("learning_exam_prepare", "execute"),
    "learning_time_management": ("learning_time_management", "execute"),
    # 旅行规划
    "travel_trip_plan": ("travel_trip_plan", "execute"),
    "travel_hotel_book": ("travel_hotel_book", "execute"),
    "travel_visa_consult": ("travel_visa_consult", "execute"),
    "travel_spot_recommend": ("travel_spot_recommend", "execute"),
}


def get_tool_and_action_for_goal(goal_type: str) -> tuple[str, str] | None:
    """获取goal_type对应的tool名称和action。

    这是最后的fallback，仅在binding配置不存在或失败时使用。

    Args:
        goal_type: 目标类型

    Returns:
        (tool_name, action) tuple 或 None 如果未知
    """
    return GOAL_TYPE_TO_TOOL_ACTION.get(goal_type)
