"""天气查询类工具 - Mock 实现."""

from typing import Any


class WeatherTool:
    """天气查询工具."""

    def get_schema(self) -> dict[str, Any]:
        return {
            "name": "get_weather",
            "description": "查询指定城市或当前位置的天气情况",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "城市名称", "default": "北京"},
                    "forecast_days": {"type": "integer", "description": "预报天数(1-7)", "default": 1},
                },
            },
        }

    def execute(self, location: str = "北京", forecast_days: int = 1) -> dict[str, Any]:
        # 模拟天气数据
        weather_conditions = ["晴", "多云", "阴", "小雨", "雷阵雨"]
        import random

        current_temp = random.randint(15, 32)
        condition = random.choice(weather_conditions)

        result = {
            "success": True,
            "message": f"{location}今日天气：{condition}，气温{current_temp}°C",
            "data": {
                "location": location,
                "condition": condition,
                "temperature": current_temp,
                "humidity": random.randint(40, 80),
                "wind": f"{random.randint(1, 5)}级",
            },
        }

        if forecast_days > 1:
            forecast = []
            for i in range(1, forecast_days + 1):
                forecast.append(
                    {
                        "day": f"第{i}天",
                        "condition": random.choice(weather_conditions),
                        "temp_high": current_temp + random.randint(-3, 5),
                        "temp_low": current_temp - random.randint(5, 10),
                    }
                )
            result["data"]["forecast"] = forecast

        return result

    def get_status(self) -> dict[str, Any]:
        """获取系统状态（用于工具注册）."""
        return self.execute()
