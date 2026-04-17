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
        return list(MCP_TOOLS.values())

    def call_tool(self, name: str, action: str, **kwargs) -> ToolResult:
        """统一调用接口。"""
        tool_map = {
            # 车载控制类
            "climate_control": self.climate,
            "navigation": self.navigation,
            "music_player": self.music,
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

        # 动作映射
        action_map = {
            # ClimateTool
            "turn_on": lambda: tool.turn_on(kwargs.get("value")),
            "turn_off": lambda: tool.turn_off(),
            "set_temperature": lambda: tool.set_temperature(int(kwargs.get("value", 24))),
            "set_fan_speed": lambda: tool.set_fan_speed(str(kwargs.get("value", "auto"))),
            "get_status": lambda: tool.get_status(),
            # ClimateTool 新格式: power, temperature, fan_speed
            "control": lambda: self._climate_control(tool, kwargs),
            # NavigationTool
            "navigate": lambda: tool.execute(destination=kwargs.get("destination", "")),
            "get_traffic": lambda: tool.get_traffic(),
            "cancel": lambda: tool.cancel(),
            # MusicTool
            "play": lambda: tool.play(),
            "pause": lambda: tool.pause(),
            "skip": lambda: tool.skip(),
            "set_volume": lambda: tool.set_volume(int(kwargs.get("value", 50))),
            # DoorTool
            "lock": lambda: tool.lock(),
            "unlock": lambda: tool.unlock(),
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
        """处理 climate_control 的复合参数 (power, temperature, fan_speed)。"""
        power = kwargs.get("power")
        temperature = kwargs.get("temperature")
        fan_speed = kwargs.get("fan_speed")

        # 如果指定了 power，先开/关空调
        if power is not None:
            if power:
                tool.turn_on(temperature)
            else:
                tool.turn_off()

        # 如果指定了温度
        if temperature is not None:
            tool.set_temperature(temperature)

        # 如果指定了风速
        if fan_speed is not None:
            tool.set_fan_speed(fan_speed)

        return tool.get_status()


# 全局单例
registry = ToolRegistry()
