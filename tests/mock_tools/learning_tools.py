"""学习教练类工具 - Mock 实现."""

from typing import Any


class LearningStudyPlanTool:
    """学习规划工具."""

    def get_schema(self) -> dict[str, Any]:
        return {
            "name": "learning_study_plan",
            "description": "制定学习计划和目标",
            "parameters": {
                "type": "object",
                "properties": {
                    "subject": {"type": "string", "description": "学习科目"},
                    "target_level": {"type": "string", "description": "目标水平"},
                    "available_time": {"type": "string", "description": "可用时间"},
                },
            },
        }

    def execute(self, subject: str = None, target_level: str = None, available_time: str = None) -> dict[str, Any]:
        return {
            "success": True,
            "plan_type": "学习规划",
            "goal_summary": f"职业资格考试，计划{target_level or '通过考试'}",
            "current_level": "零基础或有一定基础",
            "target_level": target_level or "通过考试",
            "learning_path": {
                "phase1": {
                    "duration": "第1-2周（入门期）",
                    "objectives": ["了解考试大纲", "掌握基础知识框架", "熟悉考试题型"],
                    "weekly_topics": ["考试介绍与备考策略", "基础知识梳理"],
                    "daily_time": "1.5-2小时",
                },
                "phase2": {
                    "duration": "第3-8周（基础期）",
                    "objectives": ["系统学习各章节", "完成配套练习", "建立知识体系"],
                    "weekly_topics": ["第1-5章", "第6-10章", "第11-15章"],
                    "daily_time": "2-3小时",
                },
                "phase3": {
                    "duration": "第9-12周（冲刺期）",
                    "objectives": ["重点难点突破", "真题练习", "查漏补缺"],
                    "weekly_topics": ["错题回顾", "模拟考试", "考前冲刺"],
                    "daily_time": "3-4小时",
                },
            },
            "methods_recommended": [
                {
                    "method": "费曼学习法",
                    "description": "用简单的话向他人讲解所学内容",
                    "applicable_to": "理解核心概念",
                },
                {
                    "method": "间隔重复",
                    "description": "利用遗忘曲线定期复习",
                    "applicable_to": "记忆大量知识点",
                },
                {
                    "method": "番茄工作法",
                    "description": "25分钟专注学习，5分钟休息",
                    "applicable_to": "保持专注力",
                },
            ],
            "resources_suggested": [
                "官方教材/考试大纲",
                "历年真题集",
                "视频课程",
                "学习打卡群",
            ],
            "milestones": [
                {"week": 2, "milestone": "完成基础知识框架图"},
                {"week": 5, "milestone": "完成第一轮系统学习"},
                {"week": 8, "milestone": "正确率达到70%"},
                {"week": 12, "milestone": "真题模拟达到及格线"},
            ],
            "success_criteria": [
                "完成全部章节学习",
                "正确率达到75%以上",
                "能够讲解核心知识点",
                "模拟考试连续3次及格",
            ],
        }


class LearningSkillLearningTool:
    """技能学习工具."""

    def get_schema(self) -> dict[str, Any]:
        return {
            "name": "learning_skill_learning",
            "description": "制定技能学习路径",
            "parameters": {
                "type": "object",
                "properties": {
                    "skill_name": {"type": "string", "description": "技能名称"},
                    "target_level": {"type": "string", "description": "目标水平"},
                },
            },
        }

    def execute(self, skill_name: str = None, target_level: str = None) -> dict[str, Any]:
        skill = skill_name or "编程"

        return {
            "success": True,
            "skill_type": "技能学习",
            "skill_name": skill,
            "learning_objective": f"达到{target_level or '能够独立完成项目'}水平",
            "current_proficiency": "零基础",
            "target_proficiency": target_level or "中级水平",
            "learning_stages": [
                {
                    "stage": "入门阶段",
                    "duration": "1-2周",
                    "core_content": ["基本概念", "开发环境搭建", "Hello World"],
                    "practice_methods": ["跟着教程敲代码", "完成简单练习"],
                    "assessment": "能写出简单程序",
                },
                {
                    "stage": "基础阶段",
                    "duration": "3-8周",
                    "core_content": ["核心语法", "数据结构", "常用库"],
                    "practice_methods": ["大量编码练习", "完成小项目"],
                    "assessment": "能独立完成简单功能",
                },
                {
                    "stage": "进阶阶段",
                    "duration": "2-3个月",
                    "core_content": ["框架使用", "项目架构", "最佳实践"],
                    "practice_methods": ["参与实际项目", "代码审查"],
                    "assessment": "能负责项目模块",
                },
            ],
            "resources": {
                "beginner": ["官方教程", "基础课程"],
                "intermediate": ["进阶书籍", "实战项目"],
                "advanced": ["源码学习", "技术博客", "社区交流"],
            },
            "certification_guidance": {
                "recommended_certs": [f"{skill}相关认证"],
                "exam_preparation": "建议学完基础后备考",
                "timeline": "可安排在3-6个月后",
            },
            "daily_practice": {
                "duration": "1-2小时",
                "focus_areas": ["新知识学习", "编码练习", "项目实战"],
                "exercise_types": ["跟敲代码", "独立实现", "改写优化"],
            },
            "common_pitfalls": [
                "只看不练",
                "追求新技术忽视基础",
                "遇到困难容易放弃",
                "学习没有系统性",
            ],
            "tips": [
                "每天坚持编码，哪怕30分钟",
                "学会提问和搜索",
                "加入学习社区互相督促",
                "给自己设置阶段性奖励",
            ],
        }


class LearningExamPrepareTool:
    """考试备考工具."""

    def get_schema(self) -> dict[str, Any]:
        return {
            "name": "learning_exam_prepare",
            "description": "制定考试备考计划",
            "parameters": {
                "type": "object",
                "properties": {
                    "exam_name": {"type": "string", "description": "考试名称"},
                    "exam_date": {"type": "string", "description": "考试日期"},
                    "days_remaining": {"type": "integer", "description": "剩余天数"},
                },
            },
        }

    def execute(self, exam_name: str = None, exam_date: str = None, days_remaining: int = None) -> dict[str, Any]:
        days = days_remaining or 90

        return {
            "success": True,
            "exam_type": "考试备考",
            "exam_name": exam_name or "职业资格考试",
            "exam_date": exam_date or "约3个月后",
            "days_remaining": days,
            "syllabus_analysis": {
                "total_topics": "20个章节",
                "high_priority": ["重点章节1", "重点章节2", "计算题专题"],
                "medium_priority": ["一般章节1", "一般章节2"],
                "low_priority": ["了解性内容"],
            },
            "preparation_phases": [
                {
                    "phase": "基础阶段",
                    "duration": f"第1-{int(days*0.4)}天",
                    "focus": "全面学习各章节",
                    "daily_tasks": ["看教材/视频1-2章", "做配套练习", "整理笔记"],
                    "success_criteria": "完成全部内容学习",
                },
                {
                    "phase": "强化阶段",
                    "duration": f"第{int(days*0.4)}-{int(days*0.7)}天",
                    "focus": "重点突破+做题",
                    "daily_tasks": ["攻克重难点", "大量做题", "错题整理"],
                    "success_criteria": "正确率达到65%",
                },
                {
                    "phase": "冲刺阶段",
                    "duration": f"第{int(days*0.7)}-{days}天",
                    "focus": "模拟考试+查漏补缺",
                    "daily_tasks": ["全真模拟", "回顾错题", "保持状态"],
                    "success_criteria": "模拟考试及格",
                },
            ],
            "daily_schedule": {
                "morning": ["重点科目学习", "新知识输入"],
                "afternoon": ["做题练习", "巩固应用"],
                "evening": ["错题回顾", "知识整理"],
            },
            "practice_strategy": {
                "past_papers": "每科完成5套以上真题",
                "error_management": "建立错题本，反复练习",
                "mock_exams": "最后两周每周2套全真模拟",
            },
            "psychological_tips": [
                "保持平常心，不要过度紧张",
                "保证充足睡眠，不要熬夜",
                "适当放松，避免过度疲劳",
            ],
            "exam_day_strategy": {
                "before_exam": "提前准备证件文具，熟悉考场",
                "during_exam": "先易后难，合理分配时间",
                "time_allocation": "选择题每题1-2分钟，大题留足时间",
            },
        }


class LearningTimeManagementTool:
    """时间管理工具."""

    def get_schema(self) -> dict[str, Any]:
        return {
            "name": "learning_time_management",
            "description": "提供时间管理和效率提升建议",
            "parameters": {
                "type": "object",
                "properties": {
                    "current_challenge": {"type": "string", "description": "当前挑战"},
                    "work_style": {"type": "string", "description": "工作风格"},
                },
            },
        }

    def execute(self, current_challenge: str = None, work_style: str = None) -> dict[str, Any]:
        return {
            "success": True,
            "assessment": {
                "current_patterns": "白天忙工作，晚上没精力学习",
                "time_wasters": ["无效社交", "手机刷屏", "拖延症"],
                "peak_productivity": "早上6-8点",
            },
            "recommendations": {
                "planning_system": {
                    "method": "四象限法则 + 番茄工作法",
                    "setup": "每天晚上规划第二天任务，按重要紧急分类",
                    "daily_routine": "早起学习1小时 > 白天工作 > 晚上复习1小时",
                },
                "focus_techniques": [
                    {
                        "technique": "番茄工作法",
                        "how_to": "25分钟专注 + 5分钟休息，4个番茄后休息15-30分钟",
                        "benefits": "提高专注力，防止疲劳",
                    },
                    {
                        "technique": "时间块",
                        "how_to": "将一天分成若干时间块，每块专注于一件事",
                        "benefits": "减少切换成本，提高效率",
                    },
                ],
                "habit_building": {
                    "target_habit": "每天早起学习",
                    "cue": "闹钟响起",
                    "routine": "起床 → 简单拉伸 → 学习",
                    "reward": "完成学习后可以享受早餐",
                },
            },
            "daily_schedule_template": {
                "6:00-7:00": "高精力 - 学习新知识（最难的任务）",
                "7:00-8:00": "早餐+通勤",
                "8:00-12:00": "工作（最高效时段处理重要事）",
                "12:00-13:00": "午餐+午休",
                "13:00-18:00": "工作（处理常规任务）",
                "18:00-19:00": "通勤+晚餐",
                "19:00-20:00": "复习+练习（巩固白天学习）",
                "20:00-21:00": "自由时间/陪伴家人",
                "21:00-22:00": "阅读/轻度学习",
                "22:00": "准备睡觉",
            },
            "tools_suggested": [
                "滴答清单（任务管理）",
                "番茄钟APP",
                "Forest（专注森林）",
                "Notion（知识整理）",
            ],
            "anti_procrastination_tips": [
                "2分钟原则：2分钟内能做的事立刻做",
                "先啃最难的任务",
                "把大任务拆成小步骤",
                "给自己设定截止时间",
            ],
            "weekly_review": {
                "when": "每周日晚上的8-9点",
                "questions": [
                    "这周完成了哪些任务？",
                    "哪里可以改进？",
                    "下周的重点是什么？",
                ],
            },
        }
