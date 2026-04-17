"""医疗健康类工具 - Mock 实现."""

from typing import Any


class MedicalSymptomAnalysisTool:
    """医疗症状分析工具."""

    def get_schema(self) -> dict[str, Any]:
        return {
            "name": "medical_symptom_analysis",
            "description": "分析症状可能原因，提供就医建议",
            "parameters": {
                "type": "object",
                "properties": {
                    "symptom": {"type": "string", "description": "主要症状"},
                    "duration": {"type": "string", "description": "持续时间"},
                    "severity": {"type": "string", "description": "严重程度"},
                },
            },
        }

    def execute(self, symptom: str = None, duration: str = None, severity: str = None) -> dict[str, Any]:
        return {
            "success": True,
            "analysis_type": "症状分析",
            "symptom_summary": symptom or "需要了解具体症状",
            "possible_causes": [
                {
                    "condition": "工作压力过大导致的躯体反应",
                    "likelihood": "高",
                    "typical_signs": "伴随失眠、食欲改变、情绪波动",
                },
                {
                    "condition": "焦虑状态",
                    "likelihood": "中",
                    "typical_signs": "过度担心、心慌、出汗",
                },
                {
                    "condition": "建议排除器质性疾病",
                    "likelihood": "低",
                    "typical_signs": "持续不缓解或加重",
                },
            ],
            "severity_assessment": severity or "中",
            "self_care_tips": [
                "保证充足睡眠（7-8小时）",
                "适度运动缓解压力",
                "深呼吸放松练习",
                "与朋友倾诉交流",
            ],
            "recommended_department": "建议先到全科医学科或心理科就诊",
            "urgency_note": "如果出现胸痛、呼吸困难、意识模糊等，请立即就医",
        }


class MedicalDiseaseInfoTool:
    """医疗疾病了解工具."""

    def get_schema(self) -> dict[str, Any]:
        return {
            "name": "medical_disease_info",
            "description": "提供疾病相关知识的科普介绍",
            "parameters": {
                "type": "object",
                "properties": {
                    "disease_name": {"type": "string", "description": "疾病名称"},
                    "info_type": {"type": "string", "description": "信息类型"},
                },
            },
        }

    def execute(self, disease_name: str = None, info_type: str = None) -> dict[str, Any]:
        return {
            "success": True,
            "info_type": "疾病了解",
            "disease_name": disease_name or "高血糖",
            "overview": "血糖升高是糖尿病的早期信号，需要重视",
            "details": {
                "causes": ["遗传因素", "不良饮食习惯", "缺乏运动", "肥胖", "年龄增长"],
                "symptoms": ["多饮多尿", "体重下降", "乏力", "视力模糊", "伤口愈合慢"],
                "diagnosis": ["空腹血糖检测", "糖化血红蛋白", "口服葡萄糖耐量试验"],
                "treatment_options": [
                    {
                        "method": "生活方式干预",
                        "description": "饮食控制+运动",
                        "side_effects": "无",
                    },
                    {
                        "method": "药物治疗",
                        "description": "口服降糖药或胰岛素",
                        "side_effects": "低血糖风险",
                    },
                ],
                "medications": [
                    {"name": "二甲双胍", "purpose": "一线用药", "notes": "餐后服用，定期复查肝肾功能"},
                    {"name": "阿卡波糖", "purpose": "餐后血糖控制", "notes": "随第一口饭服用"},
                ],
            },
            "recovery_outlook": "早期发现可通过生活方式干预控制，长期高血糖可能引发并发症",
            "prevention_tips": ["控制饮食", "适度运动", "定期体检", "保持健康体重"],
            "lifestyle_adjustments": ["少油少盐", "粗细粮搭配", "每天快走30分钟", "保证7小时睡眠"],
        }


class MedicalHospitalRecommendTool:
    """医疗资源推荐工具."""

    def get_schema(self) -> dict[str, Any]:
        return {
            "name": "medical_hospital_recommend",
            "description": "推荐合适的医疗机构和科室",
            "parameters": {
                "type": "object",
                "properties": {
                    "symptom": {"type": "string", "description": "主要症状"},
                    "location": {"type": "string", "description": "所在地区"},
                },
            },
        }

    def execute(self, symptom: str = None, location: str = None) -> dict[str, Any]:
        return {
            "success": True,
            "recommendation_type": "医疗资源推荐",
            "case_summary": symptom or "血糖异常需要进一步检查",
            "recommended_department": "内分泌科",
            "hospital_selection_principles": [
                "选择有内分泌专科的二级及以上医院",
                "优先选择三甲医院内分泌科",
                "考虑医保定点医院",
            ],
            "appointment_tips": [
                {
                    "method": "网上预约",
                    "steps": ["关注医院公众号", "选择科室和医生", "按时就诊"],
                    "notes": "提前7天放号，建议提前预约",
                },
                {
                    "method": "现场挂号",
                    "steps": ["早7点前到达", "凭身份证自助机挂号", "候诊等待"],
                    "notes": "热门科室可能号源紧张",
                },
            ],
            "documents_to_prepare": ["身份证", "医保卡", "既往检查报告", "病历本"],
            "questions_to_ask": [
                "需要做哪些检查？",
                "饮食有什么禁忌？",
                "多久复查一次？",
                "是否需要住院？",
            ],
            "cost_estimate": "初诊费用约200-500元，检查费用另计",
        }
