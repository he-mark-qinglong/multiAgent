"""工具层 - 复用 tests/mock_tools，复用不复制。

KISS: 所有工具实现都在 tests/mock_tools/，这里只做 HTTP 适配。
"""
import sys
import os

# 复用 tests/mock_tools（不复制代码）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.mock_tools import (
    ToolResult,
    ClimateTool,
    NavigationTool,
    MusicTool,
    VehicleStatusTool,
    DoorTool,
    EmergencyTool,
    NewsTool,
    MCP_TOOLS,
)


# ============================================================================
# 工具注册表 (单例，跨请求共享状态)
# ============================================================================

class ToolRegistry:
    """全局工具注册表。"""

    def __init__(self) -> None:
        self.climate = ClimateTool()
        self.navigation = NavigationTool()
        self.music = MusicTool()
        self.vehicle = VehicleStatusTool()
        self.door = DoorTool()
        self.emergency = EmergencyTool()
        self.news = NewsTool()

    def list_tools(self) -> list[dict]:
        """返回所有工具定义（MCP 格式）。"""
        return list(MCP_TOOLS.values())

    def call_tool(self, name: str, action: str, **kwargs) -> ToolResult:
        """统一调用接口。"""
        tool_map = {
            "climate_control": self.climate,
            "navigation": self.navigation,
            "music_player": self.music,
            "vehicle_status": self.vehicle,
            "door_control": self.door,
            "emergency": self.emergency,
            "news": self.news,
        }
        tool = tool_map.get(name)
        if not tool:
            return ToolResult(
                success=False,
                state={},
                description=f"❌ 未知工具: {name}",
                tool_name=name,
            )

        # 动作映射
        action_map = {
            # ClimateTool
            "turn_on": lambda: tool.turn_on(kwargs.get("value")),
            "turn_off": lambda: tool.turn_off(),
            "set_temperature": lambda: tool.set_temperature(int(kwargs.get("value", 24))),
            "set_fan_speed": lambda: tool.set_fan_speed(str(kwargs.get("value", "auto"))),
            "get_status": lambda: tool.get_status(),
            # NavigationTool
            "navigate": lambda: tool.navigate_to(kwargs.get("destination", "")),
            "get_traffic": lambda: tool.get_traffic(),
            "cancel": lambda: tool.cancel(),
            # MusicTool
            "play": lambda: tool.play(),
            "pause": lambda: tool.pause(),
            "skip": lambda: tool.skip(),
            "set_volume": lambda: tool.set_volume(int(kwargs.get("value", 50))),
            # DoorTool
            "lock": lambda: tool.lock(),
            "unlock": lambda: tool.unlock(),
            # EmergencyTool
            "call": lambda: tool.call(kwargs.get("reason", "")),
            # NewsTool / VehicleStatusTool
            "get_news": lambda: tool.get_news(simulate_delay=True),
        }

        handler = action_map.get(action)
        if not handler:
            return ToolResult(
                success=False,
                state={},
                description=f"❌ 未知动作: {action}",
                tool_name=name,
            )

        try:
            return handler()
        except Exception as e:
            return ToolResult(
                success=False,
                state={},
                description=f"❌ 执行失败: {e}",
                tool_name=name,
                error=str(e),
            )


# 全局单例
registry = ToolRegistry()
