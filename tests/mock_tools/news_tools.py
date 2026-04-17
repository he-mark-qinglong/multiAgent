"""新闻查询类工具 - Mock 实现."""

from typing import Any


class NewsTool:
    """新闻查询工具."""

    def get_schema(self) -> dict[str, Any]:
        return {
            "name": "get_news",
            "description": "获取最新新闻资讯，支持分类筛选",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["general", "tech", "business", "entertainment", "sports", "world"],
                        "description": "新闻分类",
                        "default": "general",
                    },
                    "count": {"type": "integer", "description": "返回条数", "default": 5},
                },
            },
        }

    def execute(self, category: str = "general", count: int = 5) -> dict[str, Any]:
        # 模拟新闻数据
        news_data = {
            "general": [
                {"title": "全国两会圆满闭幕", "summary": "会议讨论了多项民生议题"},
                {"title": "春季气温多变注意保暖", "summary": "气象部门发布降温预警"},
                {"title": "清明假期旅游市场火爆", "summary": "多地景区游客量创新高"},
            ],
            "tech": [
                {"title": "AI大模型新突破", "summary": "多模态理解能力大幅提升"},
                {"title": "新能源车销量增长", "summary": "比亚迪销量再创新高"},
                {"title": "6G技术研发进展", "summary": "预计2030年商用部署"},
            ],
            "business": [
                {"title": "A股三大指数上涨", "summary": "沪指重回3400点"},
                {"title": "央行降准释放流动性", "summary": "市场资金面保持宽松"},
                {"title": "房地产政策优化", "summary": "多城市取消限购令"},
            ],
            "entertainment": [
                {"title": "新剧热播引关注", "summary": "收视率突破2%"},
                {"title": "演唱会门票秒光", "summary": "粉丝热情高涨"},
                {"title": "电影票房破纪录", "summary": "国产科幻片表现亮眼"},
            ],
            "sports": [
                {"title": "中超联赛开赛", "summary": "首轮进球数创新高"},
                {"title": "马拉松赛事报名", "summary": "多地同时举办"},
                {"title": "国乒队备战奥运", "summary": "封闭训练进行中"},
            ],
            "world": [
                {"title": "国际会议召开", "summary": "多国领导人出席"},
                {"title": "全球经济复苏", "summary": "IMF上调增长预期"},
                {"title": "气候变化协议", "summary": "各国达成减排共识"},
            ],
        }

        articles = news_data.get(category, news_data["general"])[:count]

        return {
            "success": True,
            "message": f"为您带来{len(articles)}条最新资讯",
            "data": {"category": category, "articles": articles},
        }
