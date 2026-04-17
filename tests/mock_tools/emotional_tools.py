"""情绪支持类工具 - Mock 实现."""

from typing import Any


class EmotionalEmotionListenTool:
    """情绪疏导工具."""

    def get_schema(self) -> dict[str, Any]:
        return {
            "name": "emotional_emotion_listen",
            "description": "提供情绪疏导和心理支持",
            "parameters": {
                "type": "object",
                "properties": {
                    "emotion_type": {"type": "string", "description": "情绪类型"},
                    "intensity": {"type": "string", "description": "情绪强度"},
                },
            },
        }

    def execute(self, emotion_type: str = None, intensity: str = None) -> dict[str, Any]:
        return {
            "success": True,
            "response_type": "情绪疏导",
            "empathy_statement": "我能感受到你现在的压力和疲惫。你同时面对工作、家庭、健康这么多挑战，真的很不容易。",
            "emotion_identified": ["焦虑", "压力", "疲惫", "无力感"],
            "possible_needs": ["被理解", "放松", "休息", "支持"],
            "self_regulation_tips": [
                {
                    "technique": "深呼吸放松",
                    "description": "4-7-8呼吸法：吸气4秒，屏息7秒，呼气8秒",
                    "when_to_use": "感到焦虑或紧张时",
                },
                {
                    "technique": "接地练习",
                    "description": "感受双脚与地面的接触，慢慢深呼吸",
                    "when_to_use": "情绪激动或恐慌时",
                },
                {
                    "technique": "情绪日记",
                    "description": "记录下当下的感受和想法，帮助理清思路",
                    "when_to_use": "睡前或安静时",
                },
            ],
            "reflective_questions": [
                "如果把这些问题按重要性排序，最紧急的是哪一件？",
                "有哪些事情其实可以放一放或交给别人？",
                "你上一次完全放松是什么时候？",
            ],
            "resources": [
                "正念冥想APP（如Headspace、Insight Timer）",
                "情绪支持热线：400-161-9995",
                "倾诉平台：壹心理、简单心理",
            ],
            "escalation_note": "如果出现持续失眠、自杀念头或严重功能损害，建议寻求专业心理咨询",
        }


class EmotionalRelationshipConsultTool:
    """感情咨询工具."""

    def get_schema(self) -> dict[str, Any]:
        return {
            "name": "emotional_relationship_consult",
            "description": "提供感情和关系方面的咨询建议",
            "parameters": {
                "type": "object",
                "properties": {
                    "relationship_type": {"type": "string", "description": "关系类型"},
                    "issue": {"type": "string", "description": "主要问题"},
                },
            },
        }

    def execute(self, relationship_type: str = None, issue: str = None) -> dict[str, Any]:
        return {
            "success": True,
            "consultation_type": "感情咨询",
            "situation_summary": "工作压力大导致陪伴家人的时间减少，夫妻间沟通不足产生隔阂",
            "key_issues": ["时间分配不均", "沟通方式不当", "双方需求未被满足"],
            "emotional_impact": "双方都感到委屈和不被理解，关系进入冷战模式",
            "communication_tips": [
                {
                    "technique": "非暴力沟通(NVC)",
                    "example": "我感到...（感受），是因为我需要...（需求），能否请你...（请求）",
                    "when_to_use": "表达不满或需求时",
                },
                {
                    "technique": "积极倾听",
                    "example": "复述对方的话：你是说...对吗？",
                    "when_to_use": "对方表达时，先听后回应",
                },
                {
                    "technique": "暂停法",
                    "example": "感觉要争吵时说：我们先冷静一下，10分钟后再谈",
                    "when_to_use": "情绪激动时",
                },
            ],
            "options_considered": [
                {
                    "option": "主动沟通，修复关系",
                    "pros": "可能改善关系，增进理解",
                    "cons": "需要时间和精力，可能碰壁",
                    "considerations": "双方都有改善关系的意愿",
                },
                {
                    "option": "先从自己做起，做出改变",
                    "pros": "影响圈内的可控因素",
                    "cons": "对方可能不回应",
                    "considerations": "长期来看最有效",
                },
            ],
            "questions_for_reflection": [
                "你最希望对方做出什么改变？",
                "你能接受的最坏结果是什么？",
                "如果不为孩子，你自己想维持这段关系吗？",
            ],
            "self_care_reminders": [
                "保持自己的社交圈，不要把所有情感寄托在伴侣身上",
                "继续发展自己的兴趣爱好",
                "与朋友倾诉，获得支持",
            ],
            "professional_help_suggestion": "如果尝试沟通多次仍无改善，可考虑夫妻咨询",
        }


class EmotionalFamilyCommunicationTool:
    """家庭沟通工具."""

    def get_schema(self) -> dict[str, Any]:
        return {
            "name": "emotional_family_communication",
            "description": "改善家庭成员间的沟通和关系",
            "parameters": {
                "type": "object",
                "properties": {
                    "family_role": {"type": "string", "description": "在家庭中的角色"},
                    "challenge": {"type": "string", "description": "主要挑战"},
                },
            },
        }

    def execute(self, family_role: str = None, challenge: str = None) -> dict[str, Any]:
        return {
            "success": True,
            "consultation_type": "家庭沟通",
            "family_context": "作为家庭经济支柱，同时承担照顾父母和维持夫妻关系的责任",
            "relationship_dynamics": {
                "key_members": ["妻子", "父亲", "母亲"],
                "interaction_patterns": [
                    "与妻子：忙碌导致沟通少，容易因小事争吵",
                    "与父亲：关心病情但不知如何表达",
                    "与母亲：被依赖感到压力",
                ],
            },
            "underlying_needs": {
                "user": "被理解、分担、喘息空间",
                "other_members": "妻子需要陪伴、父母需要安心",
            },
            "communication_strategies": [
                {
                    "situation": "与妻子谈心",
                    "strategy": "设定专属时间",
                    "example": "每周六晚上2人约会，不谈孩子和工作，只聊感受",
                },
                {
                    "situation": "与父亲谈病情",
                    "strategy": "接纳情绪，给予支持",
                    "example": "听父亲说说他的担忧，而不是给建议",
                },
            ],
            "relationship_building_tips": [
                "每天给妻子一个拥抱",
                "定期与父母视频，即使只是问候",
                "与孩子单独相处的时间很重要",
            ],
            "boundary_setting": {
                "important": "划清工作和家庭的边界",
                "how_to_communicate": "明确告诉家人：晚上8点后不处理工作，但有紧急情况除外",
            },
            "self_care_for_caregivers": [
                "接受自己不是完美的",
                "允许自己有不耐烦的时候",
                "寻求其他家庭成员或外部资源的帮助",
            ],
            "professional_support_options": [
                "家庭治疗",
                "照护者支持小组",
                "心理咨询",
            ],
        }


class EmotionalSocialAdviceTool:
    """人际建议工具."""

    def get_schema(self) -> dict[str, Any]:
        return {
            "name": "emotional_social_advice",
            "description": "提供人际交往和社交技巧建议",
            "parameters": {
                "type": "object",
                "properties": {
                    "situation": {"type": "string", "description": "人际情境"},
                    "goal": {"type": "string", "description": "目标"},
                },
            },
        }

    def execute(self, situation: str = None, goal: str = None) -> dict[str, Any]:
        return {
            "success": True,
            "consultation_type": "人际建议",
            "situation": "职场压力大，与同事关系一般，社交圈较小",
            "relationship_type": "职场关系",
            "challenges_identified": ["时间精力有限", "社交技巧可能不足", "可能有社交焦虑"],
            "analysis": {
                "your_perspective": "觉得社交很耗时，但内心渴望连接",
                "other_side_perspective": "同事可能也忙于自己的事务",
                "hidden_factors": "工作压力已经消耗了大量情绪资源",
            },
            "skill_building": [
                {
                    "skill": "积极倾听",
                    "description": "全神贯注地听对方说话，不打断",
                    "practice_exercise": "下次对话时，复述对方说的关键内容",
                },
                {
                    "skill": "适度自我表露",
                    "description": "分享一些个人的事情，增加亲近感",
                    "practice_exercise": "每天主动与一位同事闲聊几句",
                },
            ],
            "practical_advice": [
                {
                    "action": "从小事开始",
                    "rationale": "大改变很难维持，小习惯容易坚持",
                    "how": "每天午餐时与1位同事多聊5分钟",
                },
                {
                    "action": "找到共同兴趣",
                    "rationale": "共同话题是建立关系的捷径",
                    "how": "观察谁喜欢聊什么，找到共同点",
                },
            ],
            "conversation_starters": [
                "今天有什么安排？",
                "周末过得怎么样？",
                "你觉得这个项目怎么样？",
            ],
            "coping_strategies": [
                "接受社交能量有限的现实，不必强迫自己",
                "质量重于数量，少数深入的关系比泛泛之交更有意义",
            ],
            "when_to_extend_effort": "如果对方也有积极的回应，可以继续投入",
        }


class EmotionalSelfDiscoveryTool:
    """自我成长工具."""

    def get_schema(self) -> dict[str, Any]:
        return {
            "name": "emotional_self_discovery",
            "description": "支持自我探索和个人成长",
            "parameters": {
                "type": "object",
                "properties": {
                    "exploration_area": {"type": "string", "description": "探索领域"},
                    "current_stage": {"type": "string", "description": "当前阶段"},
                },
            },
        }

    def execute(self, exploration_area: str = None, current_stage: str = None) -> dict[str, Any]:
        return {
            "success": True,
            "exploration_type": "自我探索",
            "current_situation": "35岁，职业遇到瓶颈，开始思考人生意义和方向",
            "identified_themes": ["职业意义", "工作生活平衡", "中年危机", "价值实现"],
            "values_assessment": {
                "core_values": ["家庭", "成就感", "自由", "成长"],
                "how_values_show_up": "希望工作能支持家庭，同时有成长空间和一定自由度",
            },
            "strengths_identified": [
                "技术能力强",
                "责任心强",
                "能承受压力",
                "善于解决问题",
            ],
            "areas_for_growth": [
                "工作生活平衡",
                "人际沟通能力",
                "情绪管理",
                "长期规划能力",
            ],
            "reflective_exercises": [
                {
                    "exercise": "人生墓志铭",
                    "description": "想象你离开世界时，希望被记住的是什么",
                    "how_to_do": "安静的环境，写下3-5句话",
                },
                {
                    "exercise": "巅峰故事",
                    "description": "回忆一个你感到最满足、最有成就感的时刻",
                    "how_to_do": "详细描述那个场景、你做了什么、为什么感到满足",
                },
            ],
            "perspective_shifts": [
                {
                    "old_belief": "必须不断升职加薪才是成功",
                    "new_perspective": "成功是按自己的价值观生活",
                },
                {
                    "old_belief": "必须平衡好所有角色",
                    "new_perspective": "在不同时期侧重不同角色是正常的",
                },
            ],
            "action_suggestions": [
                {
                    "action": "探索职业第二曲线",
                    "why": "单一职业路径风险大，且可能遇到瓶颈",
                    "how": "思考有哪些技能可以迁移，哪些新领域感兴趣",
                },
                {
                    "action": "建立微习惯",
                    "why": "大改变容易失败，小习惯容易坚持",
                    "how": "每天早起30分钟用于自我探索和规划",
                },
            ],
            "affirmations": [
                "我现在所做的一切，都是当时最好的选择",
                "我有能力创造想要的生活",
                "迷茫是成长的契机",
            ],
            "resources_for_deeper_work": [
                "书籍：《活出生命的意义》《幸福的方法》",
                "课程：正念冥想、教练对话",
                "练习：瑜伽、太极、书写疗愈",
            ],
        }
