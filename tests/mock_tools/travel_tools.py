"""旅行规划类工具 - Mock 实现."""

from typing import Any


class TravelTripPlanTool:
    """行程规划工具."""

    def get_schema(self) -> dict[str, Any]:
        return {
            "name": "travel_trip_plan",
            "description": "制定旅行行程安排",
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {"type": "string", "description": "目的地"},
                    "duration": {"type": "integer", "description": "旅行天数"},
                    "travel_style": {"type": "string", "description": "旅行风格"},
                },
            },
        }

    def execute(self, destination: str = None, duration: int = None, travel_style: str = None) -> dict[str, Any]:
        dest = destination or "日本东京"
        days = duration or 5

        return {
            "success": True,
            "trip_summary": {
                "destination": dest,
                "duration": f"{days}天{days-1}晚",
                "best_season": "春秋两季",
                "estimated_budget": "¥15,000-25,000/人",
            },
            "daily_itinerary": [
                {
                    "day": 1,
                    "theme": "抵达+市区初探",
                    "morning": {"activity": "乘飞机抵达", "duration": "3小时", "tips": "选择早班机"},
                    "afternoon": {"activity": "酒店入住+休息", "duration": "2小时", "tips": "酒店通常14:00后才能入住"},
                    "evening": {"activity": "银座逛街", "duration": "3小时", "tips": "购物天堂"},
                    "meals": {"breakfast": "机上", "lunch": "机场", "dinner": "银座"},
                },
                {
                    "day": 2,
                    "theme": "传统文化体验",
                    "morning": {"activity": "浅草寺+仲见世街", "duration": "2小时", "tips": "早点去人少"},
                    "afternoon": {"activity": "上野公园+博物馆", "duration": "3小时", "tips": "提前查好展览"},
                    "evening": {"activity": "秋叶原", "duration": "2小时", "tips": "电子产品爱好者天堂"},
                    "meals": {"breakfast": "酒店", "lunch": "上野", "dinner": "秋叶原"},
                },
                {
                    "day": 3,
                    "theme": "现代都市风光",
                    "morning": {"activity": "东京塔", "duration": "1.5小时", "tips": "天气好时登塔"},
                    "afternoon": {"activity": "涩谷+原宿", "duration": "4小时", "tips": "潮流文化"},
                    "evening": {"activity": "六本木夜景", "duration": "2小时", "tips": "欣赏东京夜景"},
                    "meals": {"breakfast": "酒店", "lunch": "涩谷", "dinner": "六本木"},
                },
                {
                    "day": 4,
                    "theme": "周边游览",
                    "morning": {"activity": "镰仓一日游", "duration": "5小时", "tips": "乘坐江之岛电铁"},
                    "afternoon": {"activity": "灌篮高手打卡地", "duration": "2小时", "tips": "热门拍照点"},
                    "evening": {"activity": "返回东京", "duration": "1小时", "tips": "购买伴手礼"},
                    "meals": {"breakfast": "酒店", "lunch": "镰仓", "dinner": "东京"},
                },
                {
                    "day": 5,
                    "theme": "返程日",
                    "morning": {"activity": "整理行李+最后购物", "duration": "2小时", "tips": "机场免税店较贵"},
                    "afternoon": {"activity": "前往机场", "duration": "1.5小时", "tips": "建议提前2.5小时到机场"},
                    "evening": {"activity": "乘飞机返回", "duration": "3小时", "tips": "愉快结束旅程"},
                    "meals": {"breakfast": "酒店", "lunch": "机场", "dinner": "机上"},
                },
            ],
            "transportation_guide": [
                {"route": "上海市区-浦东机场", "method": "地铁2号线/磁悬浮", "duration": "约1小时", "cost": "¥50-60"},
                {"route": "东京市内交通", "method": "地铁+JR", "duration": "按需", "cost": "建议购买西瓜卡"},
                {"route": "东京-镰仓", "method": "JR东海道线", "duration": "约1小时", "cost": "¥920"},
            ],
            "packing_checklist": [
                "护照+签证",
                "日元现金（约3-5万日元）",
                "信用卡（支持日元）",
                "随身WiFi/流量卡",
                "转换插头",
                "换洗衣物",
                "常备药品",
                "充电宝（不能托运）",
            ],
            "budget_breakdown": {
                "accommodation": "¥4,000-8,000（4晚）",
                "food": "¥3,000-5,000",
                "transportation": "¥1,500-2,000",
                "tickets": "¥1,000-1,500",
                "misc": "¥2,000-3,000",
            },
            "important_notes": [
                "日本电压100V，插头为两孔",
                "很多地方不能使用现金，需带足现金或信用卡",
                "日本时间比中国快1小时",
                "公交车和地铁保持安静",
                "垃圾要分类处理",
            ],
        }


class TravelHotelBookTool:
    """酒店预订工具."""

    def get_schema(self) -> dict[str, Any]:
        return {
            "name": "travel_hotel_book",
            "description": "推荐和预订酒店",
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {"type": "string", "description": "目的地"},
                    "check_in": {"type": "string", "description": "入住日期"},
                    "check_out": {"type": "string", "description": "退房日期"},
                    "budget": {"type": "number", "description": "预算"},
                },
            },
        }

    def execute(self, destination: str = None, check_in: str = None, check_out: str = None, budget: float = None) -> dict[str, Any]:
        dest = destination or "日本东京"
        budget_val = budget or 1000

        return {
            "success": True,
            "booking_type": "酒店预订",
            "search_criteria": {
                "destination": dest,
                "check_in": check_in or "待确认",
                "check_out": check_out or "待确认",
                "budget_range": f"¥{budget_val}/晚",
                "special_requirements": "交通便利、设施齐全",
            },
            "hotel_recommendations": [
                {
                    "name": "东京王子花园塔酒店",
                    "location": "港区芝公园",
                    "rating": "4.5星",
                    "price_range": f"¥{budget_val}/晚",
                    "pros": ["东京塔景观", "交通便利", "设施豪华"],
                    "cons": ["价格较高", "周边餐饮较贵"],
                    "suitable_for": "商务出行、情侣出游",
                    "booking_platforms": ["携程", "Booking.com", "酒店官网"],
                },
                {
                    "name": "新宿格拉斯丽酒店",
                    "location": "新宿区的黄金位置",
                    "rating": "4.3星",
                    "price_range": f"¥{budget_val*0.8:.0f}/晚",
                    "pros": ["购物方便", "交通枢纽", "24小时前台"],
                    "cons": ["老城区", "房间较小"],
                    "suitable_for": "首次赴日、观光游客",
                    "booking_platforms": ["去哪儿", "携程", "Agoda"],
                },
            ],
            "transportation_options": [
                {
                    "type": "飞机",
                    "route": "上海-东京",
                    "options": [
                        {"provider": "全日空ANA", "departure": "08:00", "arrival": "11:00", "price": "¥2,500-3,500", "notes": "含行李额"},
                        {"provider": "东航", "departure": "14:00", "arrival": "17:00", "price": "¥1,800-2,800", "notes": "性价比较高"},
                        {"provider": "日航JAL", "departure": "10:00", "arrival": "13:00", "price": "¥2,800-3,800", "notes": "服务优质"},
                    ],
                },
                {
                    "type": "火车",
                    "route": "机场-市区",
                    "options": [
                        {"provider": "JR Narita Express", "departure": "每30分钟", "arrival": "约60分钟", "price": "¥3,070", "notes": "最方便"},
                        {"provider": "京成电铁", "departure": "每20分钟", "arrival": "约40-50分钟", "price": "¥930", "notes": "便宜但需换乘"},
                    ],
                },
            ],
            "price_comparison": {
                "hotel": {"platform": "携程/Booking/去哪儿对比", "tip": "同一酒店不同平台价格可能不同"},
                "flights": {"platform": "携程/去哪儿/航司官网", "tip": "提前1-2个月预订较便宜"},
            },
            "booking_tips": [
                "酒店官网价格往往最低，且可免费取消",
                "日本酒店按人数收费，儿童同价",
                "Check-in时间通常14:00后，Check-out 10:00-11:00",
                "携带酒店确认单以便沟通",
            ],
            "cancellation_policy": "注意查看各平台取消政策，一般提前3-7天免费取消",
            "important_notices": [
                "日本酒店房间普遍较小",
                "儿童住宿政策各不同，提前确认",
                "部分酒店不提供一次性洗漱用品",
            ],
        }


class TravelVisaConsultTool:
    """签证咨询工具."""

    def get_schema(self) -> dict[str, Any]:
        return {
            "name": "travel_visa_consult",
            "description": "提供签证办理咨询",
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {"type": "string", "description": "目的地国家"},
                    "visa_type": {"type": "string", "description": "签证类型"},
                },
            },
        }

    def execute(self, destination: str = None, visa_type: str = None) -> dict[str, Any]:
        dest = destination or "日本"

        return {
            "success": True,
            "consultation_type": "签证咨询",
            "destination": dest,
            "visa_type": "单次旅游签证",
            "visa_requirements": {
                "eligibility": "因私普通护照持有人，因旅游目的访问日本",
                "documents_needed": [
                    "护照原件（有效期6个月以上）",
                    "签证申请表",
                    "2寸白底照片2张",
                    "身份证复印件",
                    "户口本全本复印件",
                    "在职证明/在读证明",
                    "资产证明（年收入10万以上或存款证明）",
                    "行程安排",
                    "往返机票预订单",
                    "酒店预订单",
                ],
                "processing_time": "7-10个工作日",
                "validity": "3个月（停留15天）",
                "stay_duration": "15天",
            },
            "application_process": [
                {"step": 1, "action": "确认出行时间", "note": "提前1-2个月开始办理"},
                {"step": 2, "action": "准备材料", "note": "确保材料真实完整"},
                {"step": 3, "action": "选择送签渠道", "note": "旅行社/领事馆"},
                {"step": 4, "action": "递交材料", "note": "按预约时间递交"},
                {"step": 5, "action": "缴纳费用", "note": "签证费+服务费"},
                {"step": 6, "action": "等待出签", "note": "可加急"},
                {"step": 7, "action": "取回护照", "note": "检查签证信息"},
            ],
            "cost_breakdown": {
                "visa_fee": "¥200（领事馆收取）",
                "service_fee": "¥100-200（旅行社）",
                "insurance": "¥50-100（可选）",
                "total": "约¥350-500",
            },
            "tips": {
                "common_mistakes": [
                    "材料不全或过期",
                    "资产证明不足",
                    "机票酒店预订单与行程不符",
                    "表格填写错误",
                ],
                "success_tips": [
                    "材料准备充分，一次通过",
                    "资产证明越充足越好",
                    "行程安排要合理",
                    "注意接听领馆电话核查",
                ],
            },
            "entry_requirements": {
                "passport": "有效期6个月以上",
                "customs": "需填写入境卡和海关申报单",
                "prohibited_items": ["某些药品", "超过免税额的商品", "肉类制品"],
                "quarantine": "日本对食品入境检查较严",
            },
            "documents_to_print": [
                "护照",
                "签证页打印件",
                "往返机票行程单",
                "酒店确认单",
                "行程安排",
                "紧急联系卡片",
            ],
        }


class TravelSpotRecommendTool:
    """景点推荐工具."""

    def get_schema(self) -> dict[str, Any]:
        return {
            "name": "travel_spot_recommend",
            "description": "推荐旅行景点和体验",
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {"type": "string", "description": "目的地"},
                    "travel_style": {"type": "string", "description": "旅行风格"},
                },
            },
        }

    def execute(self, destination: str = None, travel_style: str = None) -> dict[str, Any]:
        dest = destination or "日本东京"
        style = travel_style or "商务+文化体验"

        return {
            "success": True,
            "destination": dest,
            "travel_style": style,
            "recommendations": {
                "must_visit_spots": [
                    {
                        "name": "浅草寺",
                        "rating": "5星",
                        "category": "文化",
                        "highlights": ["雷门", "仲见世街", "五重塔"],
                        "best_time": "建议早上8-9点",
                        "duration": "1.5-2小时",
                        "ticket_info": "免费参观",
                        "tips": ["从雷门进入更有仪式感", "仲见世街的小吃不能错过"],
                    },
                    {
                        "name": "东京塔",
                        "rating": "5星",
                        "category": "地标",
                        "highlights": ["大眺望厅", "特别眺望厅", "海贼王乐园"],
                        "best_time": "日落时分",
                        "duration": "1.5小时",
                        "ticket_info": "大眺望厅¥1,200",
                        "tips": ["可提前网上购票", "晚上灯光很美"],
                    },
                    {
                        "name": "秋叶原",
                        "rating": "4.5星",
                        "category": "购物",
                        "highlights": ["电器店", "动漫周边", "女仆咖啡厅"],
                        "best_time": "下午到晚上",
                        "duration": "2-3小时",
                        "ticket_info": "免费",
                        "tips": ["电子产品货比三家", "动漫店可以逛很久"],
                    },
                    {
                        "name": "镰仓",
                        "rating": "5星",
                        "category": "周边",
                        "highlights": ["大佛", "江之岛电铁", "灌篮高手打卡地"],
                        "best_time": "全天",
                        "duration": "5-6小时",
                        "ticket_info": "江之岛电铁¥260",
                        "tips": ["购买一日通票", "穿舒适的鞋子"],
                    },
                ],
                "local_food": [
                    {
                        "restaurant": "一兰拉面",
                        "dish": "天然豚骨拉面",
                        "price_range": "¥80-100",
                        "location": "新宿、涩谷等多店",
                        "tips": "24小时营业",
                    },
                    {
                        "restaurant": "�的�的寿司",
                        "dish": "时令寿司套餐",
                        "price_range": "¥200-400",
                        "location": "银座",
                        "tips": "提前预约",
                    },
                    {
                        "restaurant": "鸟贵族",
                        "dish": "烤鸡肉串",
                        "price_range": "¥60-80",
                        "location": "各大地铁路线",
                        "tips": "便宜好吃的居酒屋",
                    },
                ],
                "shopping": [
                    {
                        "place": "银座",
                        "specialties": ["高档百货", "国际品牌"],
                        "price_range": "高端",
                        "tips": "三越、伊东屋文具店值得一逛",
                    },
                    {
                        "place": "新宿",
                        "specialties": ["药妆", "电器", "潮流服饰"],
                        "price_range": "中高低都有",
                        "tips": "伊势丹、小田急值得关注",
                    },
                    {
                        "place": "秋叶原",
                        "specialties": ["电子产品", "动漫手办"],
                        "price_range": "中端",
                        "tips": "Yodobashi Camera很大",
                    },
                ],
                "photo_spots": [
                    {"location": "东京塔下的芝公园", "best_time": "日出或日落", "tips": "可拍到塔与绿荫"},
                    {"location": "涩谷十字路口", "best_time": "晚上", "tips": "从星巴克2楼俯拍"},
                    {"location": "镰仓高校前", "best_time": "早晨", "tips": "注意安全，车流较大"},
                ],
            },
            "off_the_beaten_path": [
                "清澄白河（咖啡街区）",
                "神乐坂（老东京风情）",
                "下北泽（复古潮流）",
                "东京晴空塔（比东京塔人少）",
            ],
            "day_trip_options": [
                "镰仓（灌篮高手、富士山景观）",
                "日光（世界遗产、温泉）",
                "轻井泽（避暑胜地、outlet）",
            ],
            "seasonal_tips": "春季赏樱、夏季花火大会、秋季红叶、冬季圣诞市集",
            "budget_estimate": {
                "budget": "机+酒+签¥6,000，自由行¥3,000/天",
                "mid_range": "机+酒+签¥9,000，舒适游¥5,000/天",
                "luxury": "全程高端，¥10,000+/天",
            },
        }
