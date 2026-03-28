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

async def simulate_reasoning(message: str, session_id: str) -> AsyncGenerator[dict, None]:  # noqa: ARG001
    """模拟 ReAct 推理过程，通过 SSE 流式输出。

    Yields:
        SSE 格式的 dict: {"event": <type>, "data": <json>}
    """
    msg_lower = message.lower()

    # --- 推理步骤: Think ---
    yield {"event": "think", "data": json.dumps({"content": "正在分析用户请求..."}, ensure_ascii=False)}
    await asyncio.sleep(0.3)

    # --- 意图识别 ---
    if any(k in msg_lower for k in ["温度", "空调", "冷", "热"]):
        tool_name, action = "climate_control", "get_status"
        yield {"event": "think", "data": json.dumps({"content": f"识别为空调控制请求，执行 {action}..."}, ensure_ascii=False)}
    elif any(k in msg_lower for k in ["导航", "去", "路线", "怎么走"]):
        tool_name, action = "navigation", "get_traffic"
        dest = message.replace("导航", "").replace("去", "").strip()
        yield {"event": "think", "data": json.dumps({"content": f"识别为导航请求，目的地: {dest or '未指定'}"}, ensure_ascii=False)}
    elif any(k in msg_lower for k in ["音乐", "播放", "暂停", "切歌"]):
        tool_name, action = "music_player", "play"
        yield {"event": "think", "data": json.dumps({"content": "识别为音乐控制请求..."}, ensure_ascii=False)}
    elif any(k in msg_lower for k in ["状态", "电量", "续航", "车况"]):
        tool_name, action = "vehicle_status", "get_status"
        yield {"event": "think", "data": json.dumps({"content": "识别为车辆状态查询..."}, ensure_ascii=False)}
    elif any(k in msg_lower for k in ["新闻", "天气", "资讯"]):
        tool_name, action = "news", "get_news"
        yield {"event": "think", "data": json.dumps({"content": "识别为新闻请求（注意：需等待5秒）..."}, ensure_ascii=False)}
    else:
        tool_name, action = None, None
        yield {"event": "think", "data": json.dumps({"content": "未识别到具体工具，将直接回复..."}, ensure_ascii=False)}

    await asyncio.sleep(0.4)

    # --- 执行工具 ---
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

    # --- 最终回复 ---
    response_text = _build_response(message, tool_name)
    yield {"event": "result", "data": json.dumps({"content": response_text}, ensure_ascii=False)}
    yield {"event": "done", "data": json.dumps({"timestamp": time.time()}, ensure_ascii=False)}


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
        async for event in simulate_reasoning(request.message, sid):
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
