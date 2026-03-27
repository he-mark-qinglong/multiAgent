"""Mock Tools Module - 模拟 MCP/Skill 工具调用。

每个工具返回结构化结果，包含:
- success: 操作是否成功
- state: 当前设备状态
- description: 人类可读的状态描述
- timestamp: 时间戳

MCP/Skill 工具定义格式:
{
    "name": "climate_control",
    "description": "控制空调温度、风速、模式",
    "parameters": {...},
    "returns": {...}
}
"""

from dataclasses import dataclass, field
from typing import Any
import time
import random


@dataclass
class ToolResult:
    """工具执行结果 - MCP/Skill 标准返回格式。"""
    success: bool
    state: dict[str, Any]
    description: str
    timestamp: float = field(default_factory=time.time)
    error: str | None = None
    tool_name: str = ""


# ============================================================================
# MCP Tool Definitions (用于 LLM 理解工具接口)
# ============================================================================

MCP_TOOLS = {
    "climate_control": {
        "name": "climate_control",
        "description": "控制车载空调系统",
        "category": "vehicle_control",
        "parameters": {
            "action": {
                "type": "string",
                "enum": ["turn_on", "turn_off", "set_temperature", "set_fan_speed", "get_status"],
                "description": "操作类型"
            },
            "value": {
                "type": "number | string",
                "description": "操作值 (温度: 16-30, 风速: low/medium/high/auto)"
            }
        },
        "returns": {
            "success": "bool",
            "state": {
                "power": "bool",
                "temperature": "number (16-30)",
                "fan_speed": "string",
                "mode": "string"
            },
            "description": "string (中文状态描述)"
        }
    },
    "navigation": {
        "name": "navigation",
        "description": "导航到目的地或查询路线",
        "category": "navigation",
        "parameters": {
            "action": {
                "type": "string",
                "enum": ["navigate", "get_traffic", "cancel"],
                "description": "操作类型"
            },
            "destination": {
                "type": "string",
                "description": "目的地名称"
            }
        },
        "returns": {
            "success": "bool",
            "state": {
                "active": "bool",
                "destination": "string",
                "eta_minutes": "number",
                "traffic": "string (畅通/缓慢/拥堵)"
            },
            "description": "string"
        }
    },
    "music_player": {
        "name": "music_player",
        "description": "控制音乐播放",
        "category": "entertainment",
        "parameters": {
            "action": {
                "type": "string",
                "enum": ["play", "pause", "skip", "set_volume", "get_status"],
                "description": "操作类型"
            },
            "value": {
                "type": "number | string",
                "description": "操作值 (音量: 0-100)"
            }
        },
        "returns": {
            "success": "bool",
            "state": {
                "playing": "bool",
                "current_song": "[title, artist, duration]",
                "volume": "number (0-100)"
            },
            "description": "string"
        }
    },
    "vehicle_status": {
        "name": "vehicle_status",
        "description": "查询车辆状态",
        "category": "vehicle_info",
        "parameters": {},
        "returns": {
            "success": "bool",
            "state": {
                "battery": "number (0-100)",
                "range_km": "number",
                "tire_pressure": "string",
                "doors_locked": "bool"
            },
            "description": "string"
        }
    },
    "door_control": {
        "name": "door_control",
        "description": "控制车门锁定",
        "category": "vehicle_control",
        "parameters": {
            "action": {
                "type": "string",
                "enum": ["lock", "unlock", "get_status"]
            }
        },
        "returns": {
            "success": "bool",
            "state": {"locked": "bool"},
            "description": "string"
        }
    },
    "emergency": {
        "name": "emergency",
        "description": "发起紧急救援",
        "category": "safety",
        "parameters": {
            "reason": {"type": "string", "description": "紧急原因"}
        },
        "returns": {
            "success": "bool",
            "state": {
                "emergency_called": "bool",
                "contact": "string",
                "estimated_arrival": "string"
            },
            "description": "string"
        }
    },
    "news": {
        "name": "news",
        "description": "获取新闻资讯",
        "category": "information",
        "parameters": {
            "category": {"type": "string", "description": "新闻类别"}
        },
        "returns": {
            "success": "bool",
            "items": ["string"],
            "description": "string"
        }
    }
}


# ============================================================================
# Tool Implementations
# ============================================================================

class ClimateTool:
    """空调控制工具 - MCP 实现。"""

    def __init__(self):
        self._state = {
            "power": False,
            "temperature": 24,
            "fan_speed": "auto",
            "mode": "auto",
            "swing": False,
        }

    @property
    def state(self) -> dict[str, Any]:
        return self._state.copy()

    def _format_state(self) -> str:
        power = "开启" if self._state["power"] else "关闭"
        temp = f"{self._state['temperature']}°C"
        fan = {"auto": "自动", "low": "低速", "medium": "中速", "high": "高速"}.get(self._state["fan_speed"], self._state["fan_speed"])
        mode = {"auto": "自动模式", "cooling": "制冷模式", "heating": "制热模式", "fan": "送风模式"}.get(self._state["mode"], self._state["mode"])
        return f"空调{power}，温度{temp}，风量{fan}，{mode}"

    def turn_on(self, temperature: int | None = None) -> ToolResult:
        self._state["power"] = True
        if temperature:
            self._state["temperature"] = temperature
        return ToolResult(
            success=True,
            state=self.state,
            description=f"✅ 已开启空调，{self._format_state()}",
            tool_name="climate_control"
        )

    def turn_off(self) -> ToolResult:
        self._state["power"] = False
        return ToolResult(
            success=True,
            state=self.state,
            description="✅ 空调已关闭",
            tool_name="climate_control"
        )

    def set_temperature(self, temp: int) -> ToolResult:
        if not self._state["power"]:
            return ToolResult(success=False, state=self.state, description="❌ 空调未开启", tool_name="climate_control")
        self._state["temperature"] = temp
        self._state["mode"] = "cooling" if temp < 24 else "heating"
        return ToolResult(
            success=True,
            state=self.state,
            description=f"✅ 温度已调整为 {temp}°C，{'制冷' if temp < 24 else '制热'}模式",
            tool_name="climate_control"
        )

    def set_fan_speed(self, speed: str) -> ToolResult:
        if not self._state["power"]:
            return ToolResult(success=False, state=self.state, description="❌ 空调未开启", tool_name="climate_control")
        self._state["fan_speed"] = speed
        names = {"auto": "自动", "low": "低速", "medium": "中速", "high": "高速"}
        return ToolResult(success=True, state=self.state, description=f"✅ 风速已调整为 {names.get(speed, speed)}", tool_name="climate_control")

    def get_status(self) -> ToolResult:
        return ToolResult(
            success=True,
            state=self.state,
            description=f"📊 {self._format_state()}",
            tool_name="climate_control"
        )


class NavigationTool:
    """导航工具 - MCP 实现。"""

    def __init__(self):
        self._state = {"active": False, "destination": None, "route": None, "eta_minutes": 0, "traffic": "unknown"}

    @property
    def state(self) -> dict[str, Any]:
        return self._state.copy()

    def navigate_to(self, dest: str) -> ToolResult:
        self._state = {
            "active": True,
            "destination": dest,
            "route": f"路线A: 经过{['主路', '高速', '辅路'][random.randint(0, 2)]}",
            "eta_minutes": [25, 35, 45, 55][random.randint(0, 3)],
            "traffic": random.choice(["畅通", "缓慢", "拥堵"]),
        }
        return ToolResult(
            success=True,
            state=self.state,
            description=f"🧭 已规划前往「{dest}」的路线，预计{self._state['eta_minutes']}分钟，{self._state['traffic']}",
            tool_name="navigation"
        )

    def get_traffic(self) -> ToolResult:
        if not self._state["active"]:
            return ToolResult(success=False, state=self.state, description="❌ 当前没有进行中的导航", tool_name="navigation")
        traffic_desc = {"畅通": "路况良好", "缓慢": "部分路段缓慢", "拥堵": "前方拥堵，建议绕行"}
        return ToolResult(
            success=True,
            state=self.state,
            description=f"🚦 前往「{self._state['destination']}」: {self._state['traffic']} - {traffic_desc.get(self._state['traffic'], '')}，预计{self._state['eta_minutes']}分钟",
            tool_name="navigation"
        )

    def cancel(self) -> ToolResult:
        dest = self._state.get("destination")
        self._state = {"active": False, "destination": None, "route": None, "eta_minutes": 0, "traffic": "unknown"}
        return ToolResult(success=True, state=self.state, description=f"✅ 导航已取消{'，原目的地「' + dest + '」' if dest else ''}", tool_name="navigation")


class MusicTool:
    """音乐工具 - MCP 实现。"""

    def __init__(self):
        self._state = {"playing": False, "current_song": None, "volume": 50, "repeat": False}
        self._songs = [("晴天", "周杰伦", "3:42"), ("夜曲", "周杰伦", "4:15"), ("稻香", "周杰伦", "4:02"), ("告白气球", "周杰伦", "3:35"), ("七里香", "周杰伦", "4:58")]

    @property
    def state(self) -> dict[str, Any]:
        return self._state.copy()

    def play(self) -> ToolResult:
        self._state["current_song"] = self._songs[random.randint(0, 4)]
        self._state["playing"] = True
        s = self._state["current_song"]
        return ToolResult(success=True, state=self.state, description=f"🎵 正在播放:「{s[0]}」- {s[1]} ({s[2]})", tool_name="music_player")

    def pause(self) -> ToolResult:
        if not self._state["playing"]:
            return ToolResult(success=False, state=self.state, description="❌ 当前没有在播放", tool_name="music_player")
        self._state["playing"] = False
        return ToolResult(success=True, state=self.state, description="⏸️ 已暂停播放", tool_name="music_player")

    def skip(self) -> ToolResult:
        self._state["current_song"] = self._songs[random.randint(0, 4)]
        self._state["playing"] = True
        s = self._state["current_song"]
        return ToolResult(success=True, state=self.state, description=f"⏭️ 已切换到:「{s[0]}」- {s[1]} ({s[2]})", tool_name="music_player")

    def set_volume(self, vol: int) -> ToolResult:
        self._state["volume"] = max(0, min(100, vol))
        return ToolResult(success=True, state=self.state, description=f"🔊 音量已调整为 {self._state['volume']}%", tool_name="music_player")


class VehicleStatusTool:
    """车辆状态工具 - MCP 实现。"""

    def get_status(self) -> ToolResult:
        return ToolResult(
            success=True,
            state={"battery": 85, "range_km": 320, "tire_pressure": "2.3-2.4 bar", "doors_locked": True},
            description="🚗 车辆状态:\n   ├─ 电量: 85%\n   ├─ 续航: 约 320 km\n   ├─ 胎压: 正常\n   ├─ 车门: 已锁\n   └─ 类型: 电动车",
            tool_name="vehicle_status"
        )


class DoorTool:
    """车门工具 - MCP 实现。"""

    def __init__(self):
        self._locked = True

    def unlock(self) -> ToolResult:
        self._locked = False
        return ToolResult(success=True, state={"locked": False}, description="🔓 车门已解锁，请注意安全", tool_name="door_control")

    def lock(self) -> ToolResult:
        self._locked = True
        return ToolResult(success=True, state={"locked": True}, description="🔒 车门已锁定", tool_name="door_control")

    def get_status(self) -> ToolResult:
        return ToolResult(success=True, state={"locked": self._locked}, description=f"🚪 车门状态: {'已锁定' if self._locked else '未锁定'}", tool_name="door_control")


class EmergencyTool:
    """紧急救援工具 - MCP 实现。"""

    def call(self, reason: str = "") -> ToolResult:
        eta = f"{5 + random.randint(0, 10)}分钟"
        return ToolResult(
            success=True,
            state={"emergency_called": True, "contact": "120/110/122", "estimated_arrival": eta},
            description=f"🚨 紧急救援已启动\n   ├─ 正在联系: 120急救 / 110报警 / 122交警\n   ├─ 预计到达: {eta}\n   ├─ 当前位置: 已自动发送\n   └─ 请保持通话，救援人员正在赶来",
            tool_name="emergency"
        )


class NewsTool:
    """新闻工具 - MCP 实现。"""

    def get_news(self) -> ToolResult:
        items = [
            f"📰 天气: 今日晴朗，气温{22 + random.randint(0, 8)}°C",
            f"🚗 交通: {random.choice(['畅通', '缓慢', '拥堵'])}，预计通勤正常",
            f"📈 股市: 三大指数{random.choice(['上涨', '下跌'])}",
            f"📱 科技: AI技术持续发展，多款新品即将发布",
        ]
        random.shuffle(items)
        return ToolResult(
            success=True,
            state={"items": items, "count": 3},
            description="📰 今日新闻:\n   " + "\n   ".join(items[:3]),
            tool_name="news"
        )
