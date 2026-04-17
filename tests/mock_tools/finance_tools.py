"""财务规划类工具 - Mock 实现."""

from typing import Any


class FinanceInvestmentAnalysisTool:
    """投资分析工具."""

    def get_schema(self) -> dict[str, Any]:
        return {
            "name": "finance_investment_analysis",
            "description": "分析投资产品，评估风险收益",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_type": {"type": "string", "description": "产品类型"},
                    "amount": {"type": "number", "description": "投资金额"},
                },
            },
        }

    def execute(self, product_type: str = None, amount: float = None) -> dict[str, Any]:
        return {
            "success": True,
            "analysis_type": "投资分析",
            "product_summary": f"{product_type or '基金'}投资分析",
            "risk_rating": "中",
            "return_expectation": "年化收益5-8%",
            "suitable_investors": "追求稳健收益，能承受一定波动",
            "pros": ["专业管理", "分散风险", "流动性好", "监管严格"],
            "cons": ["存在亏损可能", "费用较高", "收益不确定"],
            "allocation_suggestion": "建议占比20-30%",
            "key_metrics": {
                "expected_return": "5-8%年化",
                "max_drawdown": "可能回撤15-20%",
                "volatility": "中等波动",
            },
            "risk_disclosure": "投资有风险，入市需谨慎。过往业绩不代表未来表现。",
        }


class FinanceBudgetPlanningTool:
    """预算规划工具."""

    def get_schema(self) -> dict[str, Any]:
        return {
            "name": "finance_budget_planning",
            "description": "制定收支预算，规划储蓄",
            "parameters": {
                "type": "object",
                "properties": {
                    "monthly_income": {"type": "number", "description": "月收入"},
                    "monthly_expenses": {"type": "number", "description": "月支出"},
                },
            },
        }

    def execute(self, monthly_income: float = None, monthly_expenses: float = None) -> dict[str, Any]:
        income = monthly_income or 30000
        expenses = monthly_expenses or 20000
        savings = income - expenses

        return {
            "success": True,
            "plan_type": "预算规划",
            "current_financial_snapshot": {
                "monthly_income": f"¥{income:,.0f}",
                "monthly_expenses": f"¥{expenses:,.0f}",
                "savings_rate": f"{(savings/income)*100:.0f}%",
            },
            "budget_allocation": {
                "necessities": {"amount": f"¥{income*0.5:,.0f}", "percentage": "50%"},
                "wants": {"amount": f"¥{income*0.2:,.0f}", "percentage": "20%"},
                "savings": {"amount": f"¥{income*0.2:,.0f}", "percentage": "20%"},
                "debt_repayment": {"amount": f"¥{income*0.1:,.0f}", "percentage": "10%"},
            },
            "recommendations": [
                {
                    "category": "住房支出",
                    "current": "¥8,000",
                    "suggested": "¥6,000",
                    "action": "考虑合租或稍远区域节省租金",
                },
                {
                    "category": "餐饮",
                    "current": "¥5,000",
                    "suggested": "¥4,000",
                    "action": "减少外卖，自己做饭",
                },
                {
                    "category": "娱乐",
                    "current": "¥3,000",
                    "suggested": "¥2,000",
                    "action": "选择低成本娱乐方式",
                },
            ],
            "debt_management_plan": {
                "total_debt": "¥0",
                "monthly_payment": "¥0",
                "strategy": "无负债，保持良好信用",
                "payoff_timeline": "N/A",
            },
            "savings_goals": [
                "3-6个月应急基金（约¥9-18万）",
                "购置房产首付款",
                "养老储备",
            ],
            "action_items": [
                "开通自动转账，每月收入到账先存20%",
                "记录每日开支，找出非必要支出",
                "取消不用的订阅服务",
            ],
        }


class FinanceTaxConsultTool:
    """税务咨询工具."""

    def get_schema(self) -> dict[str, Any]:
        return {
            "name": "finance_tax_consult",
            "description": "提供税务规划和节税建议",
            "parameters": {
                "type": "object",
                "properties": {
                    "income": {"type": "number", "description": "年收入"},
                    "tax_type": {"type": "string", "description": "税务类型"},
                },
            },
        }

    def execute(self, income: float = None, tax_type: str = None) -> dict[str, Any]:
        annual_income = income or 360000  # 月入3万，年收入36万

        return {
            "success": True,
            "consultation_type": "税务咨询",
            "topic_summary": f"年收入{annual_income:,.0f}元的个税规划",
            "relevant_policies": [
                {
                    "policy": "个人所得税专项附加扣除",
                    "content": "子女教育、继续教育、大病医疗、住房租金、住房贷款、赡养老人、3岁以下婴幼儿照护",
                    "effective_date": "2023年1月1日起",
                },
            ],
            "analysis": f"按年收入{annual_income:,.0f}元估算，不考虑专项附加扣除的情况下，应缴纳个税约{(annual_income-60000)*0.2-16920:,.0f}元",
            "tax_saving_tips": [
                {
                    "method": "子女教育扣除",
                    "applicable_condition": "有3岁以上子女",
                    "estimated_saving": "每年可扣除¥12,000（¥1,000/月）",
                    "implementation": "在个税APP填报子女信息",
                },
                {
                    "method": "住房贷款利息扣除",
                    "applicable_condition": "有首套房贷",
                    "estimated_saving": "每年可扣除¥12,000（¥1,000/月）",
                    "implementation": "在个税APP填报房贷信息",
                },
                {
                    "method": "赡养老人扣除",
                    "applicable_condition": "赡养60岁以上父母",
                    "estimated_saving": "每年可扣除¥24,000（¥2,000/月）",
                    "implementation": "在个税APP填报被赡养人信息",
                },
                {
                    "method": "继续教育扣除",
                    "applicable_condition": "正在接受学历教育或职业资格",
                    "estimated_saving": "学历教育¥400/月，职业资格当年¥3,600",
                    "implementation": "在个税APP填报继续教育信息",
                },
            ],
            "deduction_checklist": [
                "✓ 子女教育（3岁以上）",
                "✓ 住房贷款（首套房）",
                "✓ 住房租金（无自有住房）",
                "✓ 赡养老人（60岁以上）",
                "✓ 继续教育（学历或资格）",
                "✓ 大病医疗（年自付超1.5万）",
                "✓ 3岁以下婴幼儿照护",
            ],
            "compliance_notes": [
                "确保填报信息真实有效",
                "年度汇算清缴时统一申报",
                "留存相关凭证以备核查",
            ],
            "warning": "复杂税务情况建议咨询专业税务师",
        }


class FinanceRetirementPlanTool:
    """退休规划工具."""

    def get_schema(self) -> dict[str, Any]:
        return {
            "name": "finance_retirement_plan",
            "description": "规划退休储蓄和养老金",
            "parameters": {
                "type": "object",
                "properties": {
                    "current_age": {"type": "integer", "description": "当前年龄"},
                    "retirement_age": {"type": "integer", "description": "目标退休年龄"},
                    "current_savings": {"type": "number", "description": "当前储蓄"},
                },
            },
        }

    def execute(self, current_age: int = None, retirement_age: int = None, current_savings: float = None) -> dict[str, Any]:
        age = current_age or 35
        retire_age = retirement_age or 60
        savings = current_savings or 500000
        years_to_retire = retire_age - age

        # 估算
        monthly_expense = 10000  # 退休后月支出
        pension_estimation = 5000  # 社保养老金预估
        gap = monthly_expense - pension_estimation

        return {
            "success": True,
            "plan_type": "退休规划",
            "current_status": {
                "age": f"{age}岁",
                "retirement_age": f"{retire_age}岁",
                "years_to_retirement": f"{years_to_retire}年",
                "current_savings": f"¥{savings:,.0f}",
                "monthly_contribution": "建议¥3,000-5,000",
            },
            "pension_estimation": {
                "social_pension": f"约¥{pension_estimation:,}/月（以实际为准）",
                "housing_fund": f"退休时可提取约¥{savings*0.3:,.0f}",
                "personal_savings_needed": f"需准备约¥{gap*12*20:,.0f}",
                "retirement_readiness": f"当前准备度约{(savings/(gap*12*20))*100:.0f}%",
            },
            "gap_analysis": {
                "estimated_expenses": f"约¥{monthly_expense:,}/月",
                "estimated_income": f"约¥{pension_estimation:,}/月（社保）",
                "monthly_gap": f"约¥{gap:,}",
                "total_gap": f"30年约需¥{gap*12*30:,.0f}",
            },
            "recommendations": [
                {
                    "action": "提高公积金缴存比例",
                    "amount": "可增加¥2,000-3,000/月",
                    "priority": "高",
                },
                {
                    "action": "配置养老目标基金",
                    "amount": "建议¥2,000/月",
                    "priority": "高",
                },
                {
                    "action": "商业养老保险",
                    "amount": "可选¥1,000/月",
                    "priority": "中",
                },
                {
                    "action": "继续缴纳社保",
                    "amount": "不要断缴",
                    "priority": "高",
                },
            ],
            "milestones": [
                {"age": 40, "target": "储蓄达到50万"},
                {"age": 45, "target": "养老金准备过半"},
                {"age": 50, "target": "明确退休计划"},
                {"age": 55, "target": "完成主要积累"},
                {"age": 60, "target": "优雅退休"},
            ],
        }
