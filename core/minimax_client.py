"""MiniMax API client for intent recognition and tool selection.

LLM-driven ReAct reasoning for the car assistant backend.
"""

from __future__ import annotations

import os
import json
import logging
import time
from pathlib import Path
from typing import Any

import httpx

# LangSmith tracing
try:
    from langsmith import traceable
    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False
    traceable = None

logger = logging.getLogger(__name__)


def _load_token_from_settings() -> str | None:
    """Load ANTHROPIC_AUTH_TOKEN from ~/.claude/settings.json as fallback."""
    settings_path = Path.home() / ".claude" / "settings.json"
    try:
        if settings_path.exists():
            with open(settings_path) as f:
                settings = json.load(f)
            return settings.get("env", {}).get("ANTHROPIC_AUTH_TOKEN")
    except Exception as e:
        logger.debug("Failed to load token from settings: %s", e)
    return None


class MiniMaxClient:
    """MiniMax API client for intent recognition and tool selection.

    Uses Anthropic-compatible API format via MiniMax gateway.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        # Try env var first, then fall back to settings.json
        env_token = os.environ.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get("MINIMAX_API_KEY")
        settings_token = _load_token_from_settings()
        self.api_key = api_key or env_token or settings_token or ""

        env_base_url = os.environ.get("ANTHROPIC_BASE_URL")
        self.base_url = base_url or env_base_url or "https://api.minimax.io/anthropic"
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Create a new async HTTP client each time to avoid caching issues."""
        return httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01",
            },
            timeout=30.0,
        )

    async def close(self) -> None:
        """Close is a no-op since we don't cache the client."""
        pass

    def format_tools(self, mcp_tools: dict[str, Any]) -> list[dict]:
        """Format MCP tools for Anthropic function calling."""
        formatted = []
        for tool_name, tool_def in mcp_tools.items():
            params = tool_def.get("parameters", {})
            formatted.append({
                "name": tool_def["name"],
                "description": tool_def["description"],
                "input_schema": {
                    "type": "object",
                    "properties": {
                        prop_name: {
                            "type": prop_def.get("type", "string"),
                            "description": prop_def.get("description", ""),
                        }
                        for prop_name, prop_def in params.items()
                    },
                    "required": [
                        p for p, d in params.items()
                        if d.get("required", False) or p in ["action", "value", "destination"]
                    ],
                },
            })
        return formatted

    @traceable(name="MiniMax.chat") if traceable else lambda fn: fn
    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        """Call MiniMax API for intent recognition and tool selection."""
        start_time = time.time()

        # Build request body
        request_body: dict[str, Any] = {
            "model": "MiniMax-M2.7-highspeed",
            "max_tokens": 1024,
            "messages": messages,
        }

        if system_prompt:
            request_body["system"] = system_prompt

        if tools:
            request_body["tools"] = tools

        logger.info(
            "MiniMax API call: model=%s, tools=%d, messages=%d",
            request_body["model"],
            len(tools),
            len(messages),
        )

        client = await self._get_client()

        try:
            response = await client.post("/v1/messages", json=request_body)
            response.raise_for_status()
            result = response.json()

            elapsed_ms = (time.time() - start_time) * 1000
            usage = result.get("usage", {})
            logger.info(
                "MiniMax API response: tokens=%d+%d=%d, elapsed=%.1fms",
                usage.get("input_tokens", 0),
                usage.get("output_tokens", 0),
                usage.get("total_tokens", 0),
                elapsed_ms,
            )

            return result

        except httpx.HTTPStatusError as e:
            elapsed_ms = (time.time() - start_time) * 1000
            logger.error("MiniMax API error: %s - %s (elapsed=%.1fms)",
                        e.response.status_code, e.response.text[:200], elapsed_ms)
            raise
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            logger.error("MiniMax API call failed: %s (elapsed=%.1fms)", e, elapsed_ms)
            raise

    def parse_tool_call(self, response: dict[str, Any]) -> tuple[str | None, str | None, dict | None]:
        """Parse LLM response for tool call."""
        try:
            if response.get("type") == "error":
                return None, None, None

            content = response.get("content", [])
            if not content:
                return None, None, None

            for block in content:
                if block.get("type") == "tool_use":
                    tool_name = block.get("name")
                    input_data = block.get("input", {})

                    if tool_name == "climate_control":
                        return tool_name, "control", input_data
                    elif tool_name == "navigation":
                        return tool_name, "navigate", input_data
                    elif tool_name == "music_player":
                        return tool_name, input_data.get("action", "play"), input_data
                    elif tool_name == "news":
                        return tool_name, "get_news", {}
                    elif tool_name == "vehicle_status":
                        return tool_name, "get_status", {}
                    elif tool_name == "door_control":
                        return tool_name, input_data.get("action", "lock"), input_data
                    else:
                        return tool_name, input_data.get("action") or "get_status", input_data

            return None, None, None

        except Exception as e:
            logger.error("Failed to parse tool call: %s", e)
            return None, None, None


# Global client instance
_client: MiniMaxClient | None = None


def get_minimax_client() -> MiniMaxClient:
    """Get or create global MiniMax client."""
    global _client
    if _client is None:
        _client = MiniMaxClient()
        if not _client.api_key:
            logger.warning("No API token found, LLM calls will fail")
    return _client


# System prompt for intent recognition
INTENT_SYSTEM_PROMPT = """你是一个智能车载助手。你的任务是根据用户消息识别意图并选择合适的工具。

重要：请仔细分析用户消息中的所有需求，可以一次性设置多个参数！

可用工具及参数:

1. climate_control: 控制空调
   参数: power(boolean), temperature(16-30), fan_speed(low/medium/high/auto)
   示例: 用户说"开空调24度风力大" => power=true, temperature=24, fan_speed=high

2. navigation: 导航
   参数: destination(目的地字符串)
   示例: 用户说"回家" => destination="家"

3. music_player: 音乐
   参数: action(play/pause/skip), value(音量0-100)

4. vehicle_status: 车辆状态查询
   无参数

5. door_control: 车门
   参数: action(lock/unlock)

6. emergency: 紧急救援
   无参数

7. news: 新闻
   无参数

请分析用户消息中的所有需求，一次性设置所有相关参数。不要遗漏任何用户明确提到的需求！

回复格式要求：
- 使用 tool_use 格式调用工具
- 如果无法确定，回复"无法识别意图，请说得更具体一些"
"""


INTENT_USER_PROMPT = """用户消息: {message}

请识别用户意图并选择合适的工具。"""


