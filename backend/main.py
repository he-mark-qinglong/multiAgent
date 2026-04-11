"""FastAPI 后端 - 智能车载助手 API。

KISS: 单一文件，包含所有端点。不做过度封装。
SSE 事件格式: event=<type>, data=<json>
前端期望事件: think, action, observation, result, done
"""
import asyncio
import json
import time
import uuid
from typing import AsyncGenerator

from fastapi import FastAPI
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from backend.tools import registry
from core.minimax_client import get_minimax_client, INTENT_SYSTEM_PROMPT, INTENT_USER_PROMPT
from tests.mock_tools import MCP_TOOLS

app = FastAPI(title="智能车载助手 API", version="1.0.0")

# ============================================================================
# 会话存储 (InMemory)
# ============================================================================

_sessions: dict[str, list[dict]] = {}


def get_or_create_session(session_id: str) -> list[dict]:
    if session_id not in _sessions:
        _sessions[session_id] = []
    return _sessions[session_id]


# ============================================================================
# 请求/响应模型
# ============================================================================

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str | None = Field(default=None)


# ============================================================================
# 模拟对话引擎 (ReAct 模式)
# ============================================================================

async def llm_reasoning(message: str, session_id: str) -> AsyncGenerator[dict, None]:  # noqa: ARG001
    """LLM驱动的 ReAct 推理过程，通过 SSE 流式输出。

    使用 MiniMax API 进行意图识别和工具选择。

    Yields:
        SSE 格式的 dict: {"event": <type>, "data": <json>}
    """
    # --- 推理步骤: Think ---
    yield {"event": "think", "data": json.dumps({"content": "正在分析用户请求..."}, ensure_ascii=False)}
    await asyncio.sleep(0.3)

    try:
        # --- 获取 LLM 客户端 ---
        client = get_minimax_client()
        tools = client.format_tools(MCP_TOOLS)

        # --- 调用 LLM ---
        yield {"event": "think", "data": json.dumps({"content": "正在调用 LLM 进行意图识别..."}, ensure_ascii=False)}

        messages = [
            {"role": "user", "content": INTENT_USER_PROMPT.format(message=message)}
        ]

        response = await client.chat(
            messages=messages,
            tools=tools,
            system_prompt=INTENT_SYSTEM_PROMPT,
        )

        # --- 解析 LLM 响应 ---
        tool_name, action, tool_input = client.parse_tool_call(response)

        if tool_name:
            yield {"event": "think", "data": json.dumps({
                "content": f"LLM 识别为: {tool_name}.{action}, 参数: {tool_input}"
            }, ensure_ascii=False)}

            # --- 执行工具 ---
            safe_action = action or "get_status"
            yield {"event": "action", "data": json.dumps({
                "content": f"调用工具: {tool_name}.{safe_action}",
                "params": tool_input,
            }, ensure_ascii=False)}
            await asyncio.sleep(0.2)

            # 从 tool_input 中提取参数（除了 action）
            kwargs = {k: v for k, v in (tool_input or {}).items() if k != "action"}
            result = registry.call_tool(tool_name, safe_action, **kwargs)

            # 详细的诊断信息
            observation_data = {
                "tool": tool_name,
                "action": safe_action,
                "params": kwargs,
                "success": result.success,
                "state": result.state,
                "description": result.description,
            }
            if result.error:
                observation_data["error"] = result.error

            yield {"event": "observation", "data": json.dumps(observation_data, ensure_ascii=False)}
            await asyncio.sleep(0.2)

            # --- 最终回复 ---
            yield {"event": "result", "data": json.dumps({"content": result.description}, ensure_ascii=False)}
        else:
            # LLM 没有选择工具
            yield {"event": "think", "data": json.dumps({"content": "LLM 未识别到具体工具，将直接回复..."}, ensure_ascii=False)}
            response_text = _build_response(message, None)
            yield {"event": "result", "data": json.dumps({"content": response_text}, ensure_ascii=False)}

    except Exception as e:
        # LLM 调用失败，降级到关键词匹配
        yield {"event": "think", "data": json.dumps({"content": f"LLM 调用失败: {e}，降级到关键词匹配..."}, ensure_ascii=False)}
        async for event in _fallback_keyword_reasoning(message):
            yield event

    yield {"event": "done", "data": json.dumps({"timestamp": time.time()}, ensure_ascii=False)}


async def _fallback_keyword_reasoning(message: str) -> AsyncGenerator[dict, None]:
    """降级方案：关键词匹配（当 LLM 不可用时）"""
    msg_lower = message.lower()

    if any(k in msg_lower for k in ["温度", "空调", "冷", "热"]):
        tool_name, action = "climate_control", "get_status"
    elif any(k in msg_lower for k in ["导航", "去", "路线", "怎么走"]):
        tool_name, action = "navigation", "get_traffic"
    elif any(k in msg_lower for k in ["音乐", "播放", "暂停", "切歌"]):
        tool_name, action = "music_player", "play"
    elif any(k in msg_lower for k in ["状态", "电量", "续航", "车况"]):
        tool_name, action = "vehicle_status", "get_status"
    elif any(k in msg_lower for k in ["新闻", "天气", "资讯"]):
        tool_name, action = "news", "get_news"
    else:
        tool_name, action = None, None

    if tool_name:
        safe_action = action or "get_status"
        yield {"event": "action", "data": json.dumps({"content": f"调用工具: {tool_name}.{safe_action}"}, ensure_ascii=False)}
        await asyncio.sleep(0.2)

        result = registry.call_tool(tool_name, safe_action)
        yield {"event": "observation", "data": json.dumps({
            "toolName": tool_name,
            "success": result.success,
            "description": result.description,
        }, ensure_ascii=False)}
        await asyncio.sleep(0.2)

        yield {"event": "result", "data": json.dumps({"content": result.description}, ensure_ascii=False)}
    else:
        yield {"event": "result", "data": json.dumps({"content": _build_response(message, None)}, ensure_ascii=False)}


def _build_response(message: str, tool_name: str | None) -> str:  # noqa: ARG001
    """根据意图构建最终回复。"""
    if "温度" in message or "空调" in message:
        return "好的，已为您查看空调状态。如需调节温度，请说「把温度调到26度」。"
    if "导航" in message or "去" in message:
        dest = message.replace("导航", "").replace("去", "").strip()
        return f"正在为您规划前往「{dest or '目的地'}」的路线，已显示在中控屏上。" if dest else "请问您想去哪里？"
    if "音乐" in message or "播放" in message:
        return "已为您播放音乐。您可以说「暂停」或「切歌」来控制播放。"
    if "状态" in message or "电量" in message:
        return "以上是您的车辆状态详情。请问还有什么需要帮助的？"
    if "新闻" in message or "天气" in message:
        return "以上是今日最新资讯。如需其他帮助，请随时告诉我。"
    if "你好" in message or "hi" in message or "hello" in message:
        return "您好！我是您的智能车载助手，可以帮您控制空调、导航、播放音乐、查询车辆状态等。有什么可以帮您的？"
    return "收到您的请求。如果需要具体操作，请告诉我，例如：「把空调开到24度」或「导航去公司」。"


# ============================================================================
# 工具路由 (简化为单一 router)
# ============================================================================

@app.get("/api/tools")
async def list_tools():
    """列出所有可用工具定义。"""
    return {"tools": registry.list_tools()}


@app.post("/api/tools/{tool_name}")
async def call_tool(tool_name: str, action: str = "get_status"):
    """直接调用指定工具（用于测试和调试）。"""
    result = registry.call_tool(tool_name, action)
    return {
        "success": result.success,
        "tool_name": result.tool_name,
        "description": result.description,
        "state": result.state,
        "error": result.error,
    }


# ============================================================================
# 聊天端点 (SSE 流式响应)
# ============================================================================

@app.get("/api/chat")
async def chat_get(message: str, session_id: str | None = None):
    """聊天端点 - SSE 流式响应 (GET)。

    通过 GET + query 参数触发 SSE 流。
    """
    sid = session_id or str(uuid.uuid4())

    async def event_generator() -> AsyncGenerator[dict, None]:
        async for event in llm_reasoning(message, sid):
            yield {
                "event": event.get("event", "message"),
                "data": event.get("data", json.dumps(event, ensure_ascii=False)),
            }

    return EventSourceResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/health")
async def health():
    """健康检查。"""
    return {"status": "ok", "version": "1.0.0", "timestamp": time.time()}


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """聊天端点 - SSE 流式响应。

    返回 SSE 事件流，包含推理步骤和工具执行结果。
    """
    sid = request.session_id or str(uuid.uuid4())

    async def event_generator() -> AsyncGenerator[dict, None]:
        # 逐事件流式输出
        async for event in llm_reasoning(request.message, sid):
            yield {
                "event": event.get("event", "message"),
                "data": event.get("data", json.dumps(event, ensure_ascii=False)),
            }

    return EventSourceResponse(event_generator(), media_type="text/event-stream")


# ============================================================================
# 入口
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
