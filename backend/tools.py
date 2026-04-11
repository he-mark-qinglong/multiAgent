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
            # ClimateTool 新格式: power, temperature, fan_speed
            "control": lambda: self._climate_control(tool, kwargs),
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

    def _climate_control(self, tool, kwargs) -> ToolResult:
        """处理 climate_control 的复合参数 (power, temperature, fan_speed)。"""
        power = kwargs.get("power")
        temperature = kwargs.get("temperature")
        fan_speed = kwargs.get("fan_speed")

        # 如果指定了 power，先开/关空调
        if power is not None:
            if power:
                tool.turn_on(temperature)
            else:
                tool.turn_off()

        # 如果指定了温度
        if temperature is not None:
            tool.set_temperature(temperature)

        # 如果指定了风速
        if fan_speed is not None:
            tool.set_fan_speed(fan_speed)

        return tool.get_status()


# 全局单例
registry = ToolRegistry()
