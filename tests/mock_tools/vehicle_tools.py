"""车载控制类工具 - Mock 实现."""

from typing import Any


class ClimateTool:
    """空调控制工具."""

    def get_schema(self) -> dict[str, Any]:
        return {
            "name": "climate_control",
            "description": "控制车辆空调：开关、温度、风速、模式",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["on", "off", "set_temp", "set_wind"]},
                    "temperature": {"type": "integer", "description": "目标温度(16-30°C)", "default": 24},
                    "wind_speed": {"type": "integer", "description": "风速(1-5)", "default": 3},
                    "mode": {"type": "string", "enum": ["auto", "cool", "heat", "defrost"], "default": "auto"},
                },
                "required": ["action"],
            },
        }

    def execute(self, action: str, temperature: int = 24, wind_speed: int = 3, mode: str = "auto") -> dict[str, Any]:
        if action == "on":
            return {
                "success": True,
                "message": f"已开启空调，温度{temperature}°C，{mode}模式，风速{wind_speed}档",
                "data": {"status": "on", "temperature": temperature, "wind_speed": wind_speed, "mode": mode},
            }
        elif action == "off":
            return {
                "success": True,
                "message": "已关闭空调",
                "data": {"status": "off"},
            }
        elif action == "set_temp":
            return {
                "success": True,
                "message": f"已调节温度至{temperature}°C",
                "data": {"temperature": temperature, "wind_speed": wind_speed, "mode": mode},
            }
        return {"success": False, "message": f"未知操作: {action}"}


class NavigationTool:
    """导航工具."""

    def get_schema(self) -> dict[str, Any]:
        return {
            "name": "navigation",
            "description": "导航到指定目的地，计算路线和时间",
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {"type": "string", "description": "目的地名称或地址"},
                    "route_preference": {"type": "string", "enum": ["fastest", "shortest", "avoid_highway"], "default": "fastest"},
                },
                "required": ["destination"],
            },
        }

    def execute(self, destination: str, route_preference: str = "fastest") -> dict[str, Any]:
        # 模拟路线计算
        import random

        durations = ["25分钟", "35分钟", "45分钟", "55分钟"]
        traffics = ["畅通", "缓慢", "拥堵", "畅通"]

        duration = random.choice(durations)
        traffic = random.choice(traffics)

        return {
            "success": True,
            "message": f"已为您规划前往「{destination}」的路线，预计{duration}，{traffic}",
            "data": {
                "destination": destination,
                "duration": duration,
                "traffic": traffic,
                "distance": "约15公里",
                "route_preference": route_preference,
            },
        }


class MusicTool:
    """音乐播放工具."""

    def get_schema(self) -> dict[str, Any]:
        return {
            "name": "music_control",
            "description": "控制音乐播放：播放、暂停、切歌、音量调节",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["play", "pause", "next", "prev", "volume"]},
                    "song": {"type": "string", "description": "歌曲名称（play时可选）"},
                    "volume": {"type": "integer", "description": "音量(0-100，volume时必填)"},
                },
                "required": ["action"],
            },
        }

    def execute(self, action: str, song: str = None, volume: int = None) -> dict[str, Any]:
        if action == "play":
            song_name = song or "夜曲"
            return {
                "success": True,
                "message": f"正在播放「{song_name}」",
                "data": {"status": "playing", "song": song_name, "artist": "周杰伦"},
            }
        elif action == "pause":
            return {"success": True, "message": "已暂停播放", "data": {"status": "paused"}}
        elif action == "next":
            return {"success": True, "message": "已切换至下一首", "data": {"status": "playing", "song": "稻香"}}
        elif action == "prev":
            return {"success": True, "message": "已切换至上一首", "data": {"status": "playing", "song": "七里香"}}
        elif action == "volume":
            return {
                "success": True,
                "message": f"音量已调节至{volume}",
                "data": {"status": "playing", "volume": volume},
            }
        return {"success": False, "message": f"未知操作: {action}"}


class DoorTool:
    """车门控制工具."""

    def get_schema(self) -> dict[str, Any]:
        return {
            "name": "door_control",
            "description": "控制车门锁：锁门、解锁",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["lock", "unlock"]},
                    "door": {"type": "string", "description": "车门位置", "default": "all"},
                },
                "required": ["action"],
            },
        }

    def execute(self, action: str, door: str = "all") -> dict[str, Any]:
        if action == "lock":
            return {"success": True, "message": f"已{door}车门", "data": {"status": "locked", "door": door}}
        elif action == "unlock":
            return {"success": True, "message": f"已解锁{door}车门", "data": {"status": "unlocked", "door": door}}
        return {"success": False, "message": f"未知操作: {action}"}


class VehicleStatusTool:
    """车辆状态查询工具."""

    def get_schema(self) -> dict[str, Any]:
        return {
            "name": "vehicle_status",
            "description": "查询车辆当前状态：电量、续航、胎压、车门状态等",
            "parameters": {"type": "object", "properties": {}},
        }

    def execute(self) -> dict[str, Any]:
        return {
            "success": True,
            "message": "车辆状态查询完成",
            "data": {
                "battery": 85,
                "range": "约320km",
                "tire_pressure": "正常",
                "doors": "已锁",
                "type": "电动车",
            },
        }


class EmergencyTool:
    """紧急救援工具."""

    def get_schema(self) -> dict[str, Any]:
        return {
            "name": "emergency",
            "description": "呼叫紧急救援服务",
            "parameters": {
                "type": "object",
                "properties": {
                    "emergency_type": {"type": "string", "enum": ["accident", "medical", "breakdown", "other"]},
                    "location": {"type": "string", "description": "当前位置描述"},
                    "description": {"type": "string", "description": "紧急情况描述"},
                },
                "required": ["emergency_type"],
            },
        }

    def execute(self, emergency_type: str, location: str = None, description: str = None) -> dict[str, Any]:
        services = {
            "accident": "道路救援",
            "medical": "医疗急救",
            "breakdown": "拖车服务",
            "other": "紧急服务",
        }
        service = services.get(emergency_type, "紧急服务")
        return {
            "success": True,
            "message": f"已为您呼叫{service}，救援人员将尽快到达",
            "data": {
                "service": service,
                "eta": "约15分钟",
                "location": location,
                "emergency_type": emergency_type,
            },
        }
