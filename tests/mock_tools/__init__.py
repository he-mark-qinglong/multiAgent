"""Mock Tools Module - 模拟 MCP/Skill 工具调用。

拆分模块：
- vehicle_tools: 车载控制类（空调、导航、音乐、车门、车辆状态、紧急救援）
- weather_tools: 天气查询
- news_tools: 新闻查询
- legal_tools: 法律顾问
- medical_tools: 医疗健康
- emotional_tools: 情绪支持
- finance_tools: 财务规划
- learning_tools: 学习教练
- travel_tools: 旅行规划
"""

from dataclasses import dataclass, field
from typing import Any
import time


@dataclass
class ToolResult:
    """工具执行结果 - MCP/Skill 标准返回格式。"""
    success: bool
    state: dict[str, Any]
    description: str
    timestamp: float = field(default_factory=time.time)
    error: str | None = None
    tool_name: str = ""


from tests.mock_tools.vehicle_tools import (
    ClimateTool,
    NavigationTool,
    MusicTool,
    DoorTool,
    VehicleStatusTool,
    EmergencyTool,
)
from tests.mock_tools.weather_tools import WeatherTool
from tests.mock_tools.news_tools import NewsTool
from tests.mock_tools.legal_tools import (
    LegalContractReviewTool,
    LegalRightsProtectionTool,
    LegalComplianceCheckTool,
)
from tests.mock_tools.medical_tools import (
    MedicalSymptomAnalysisTool,
    MedicalDiseaseInfoTool,
    MedicalHospitalRecommendTool,
)
from tests.mock_tools.emotional_tools import (
    EmotionalEmotionListenTool,
    EmotionalRelationshipConsultTool,
    EmotionalFamilyCommunicationTool,
    EmotionalSocialAdviceTool,
    EmotionalSelfDiscoveryTool,
)
from tests.mock_tools.finance_tools import (
    FinanceInvestmentAnalysisTool,
    FinanceBudgetPlanningTool,
    FinanceTaxConsultTool,
    FinanceRetirementPlanTool,
)
from tests.mock_tools.learning_tools import (
    LearningStudyPlanTool,
    LearningSkillLearningTool,
    LearningExamPrepareTool,
    LearningTimeManagementTool,
)
from tests.mock_tools.travel_tools import (
    TravelTripPlanTool,
    TravelHotelBookTool,
    TravelVisaConsultTool,
    TravelSpotRecommendTool,
)

# 所有工具实例
TOOLS = {
    # 车载控制类
    "climate_control": ClimateTool(),
    "navigation": NavigationTool(),
    "music_control": MusicTool(),
    "door_control": DoorTool(),
    "vehicle_status": VehicleStatusTool(),
    "emergency": EmergencyTool(),
    # 信息查询类
    "get_weather": WeatherTool(),
    "get_news": NewsTool(),
    # 法律类
    "legal_contract_review": LegalContractReviewTool(),
    "legal_rights_protection": LegalRightsProtectionTool(),
    "legal_compliance_check": LegalComplianceCheckTool(),
    # 医疗类
    "medical_symptom_analysis": MedicalSymptomAnalysisTool(),
    "medical_disease_info": MedicalDiseaseInfoTool(),
    "medical_hospital_recommend": MedicalHospitalRecommendTool(),
    # 情绪类
    "emotional_emotion_listen": EmotionalEmotionListenTool(),
    "emotional_relationship_consult": EmotionalRelationshipConsultTool(),
    "emotional_family_communication": EmotionalFamilyCommunicationTool(),
    "emotional_social_advice": EmotionalSocialAdviceTool(),
    "emotional_self_discovery": EmotionalSelfDiscoveryTool(),
    # 财务类
    "finance_investment_analysis": FinanceInvestmentAnalysisTool(),
    "finance_budget_planning": FinanceBudgetPlanningTool(),
    "finance_tax_consult": FinanceTaxConsultTool(),
    "finance_retirement_plan": FinanceRetirementPlanTool(),
    # 学习类
    "learning_study_plan": LearningStudyPlanTool(),
    "learning_skill_learning": LearningSkillLearningTool(),
    "learning_exam_prepare": LearningExamPrepareTool(),
    "learning_time_management": LearningTimeManagementTool(),
    # 旅行类
    "travel_trip_plan": TravelTripPlanTool(),
    "travel_hotel_book": TravelHotelBookTool(),
    "travel_visa_consult": TravelVisaConsultTool(),
    "travel_spot_recommend": TravelSpotRecommendTool(),
}

# MCP工具定义（用于LLM工具调用）
MCP_TOOLS = [tool.get_schema() for tool in TOOLS.values()]


def get_tool(name: str):
    """获取工具实例."""
    return TOOLS.get(name)


def get_tool_schema(name: str):
    """获取工具schema."""
    tool = TOOLS.get(name)
    return tool.get_schema() if tool else None


def call_tool(name: str, action: str = None, **kwargs):
    """调用工具执行."""
    tool = TOOLS.get(name)
    if not tool:
        return {"success": False, "error": f"Unknown tool: {name}"}

    execute_fn = getattr(tool, "execute", None)
    if not execute_fn:
        return {"success": False, "error": f"Tool {name} has no execute method"}

    return execute_fn(**kwargs)
