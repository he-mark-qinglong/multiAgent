"""FastAPI 后端 - 智能车载助手 API。

KISS: 单一文件，包含所有端点。不做过度封装。
SSE 事件格式: event=<type>, data=<json>
前端期望事件: think, action, observation, result, done
"""
import asyncio
import base64
import hashlib
import hmac
import json
import time
import uuid
from typing import AsyncGenerator

from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from backend.tools import registry
from backend.feishu_integration import (
    get_feishu_client,
    get_feishu_ws_client,
    start_feishu_ws_client,
    parse_message_content,
    _load_feishu_config,
)
from core.minimax_client import get_minimax_client, INTENT_SYSTEM_PROMPT, INTENT_USER_PROMPT
from pipelines.collaboration_pipeline import CollaborationPipeline
from tests.mock_tools import MCP_TOOLS

# ============================================================================
# Feishu WebSocket Client Management
# ============================================================================

_feishu_ws_thread = None
_processed_msg_ids: set[str] = set()


def feishu_message_handler(text: str, sender_id: str, chat_id: str, msg_id: str, event: dict) -> None:
    """Handle incoming Feishu message via WebSocket."""
    # Deduplicate duplicate messages from Feishu server retry
    if msg_id in _processed_msg_ids:
        print(f"[Feishu WS] Duplicate message ignored: {msg_id}")
        return
    _processed_msg_ids.add(msg_id)

    print(f"[Feishu WS] Message from {sender_id}: {text[:100]}")

    # Get or create pipeline
    pipeline = CollaborationPipeline(enable_tracing=False)

    try:
        result = pipeline.invoke(text)
        response_text = result.get("final_response", "处理中...")
    except Exception as e:
        response_text = f"抱歉，处理消息时出错: {str(e)}"

    # Send response back to Feishu
    import asyncio
    feishu_client = get_feishu_client()

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(feishu_client.send_text(
                receive_id=sender_id,
                text=response_text,
                msg_id=msg_id,
            ))
        else:
            loop.run_until_complete(feishu_client.send_text(
                receive_id=sender_id,
                text=response_text,
                msg_id=msg_id,
            ))
    except Exception as e:
        print(f"[Feishu WS] Failed to send response: {e}")


def start_feishu_ws() -> None:
    """Start Feishu WebSocket client in background thread."""
    global _feishu_ws_thread
    if _feishu_ws_thread is not None:
        print("[Feishu WS] Already running")
        return

    _feishu_ws_thread = start_feishu_ws_client(
        event_handler=feishu_message_handler,
        blocking=False,
    )
    print("[Feishu WS] Started in background thread")


# ============================================================================
# FastAPI App
# ============================================================================

app = FastAPI(title="智能车载助手 API", version="1.0.0")


@app.on_event("startup")
async def startup_event():
    """Start Feishu WebSocket client on app startup."""
    # Start Feishu WS client in background thread
    import threading
    global _feishu_ws_thread
    _feishu_ws_thread = start_feishu_ws_client(
        event_handler=feishu_message_handler,
        blocking=False,
    )
    print("[Feishu] WebSocket client started in background")

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
# Feishu Webhook 端点
# ============================================================================

# Global pipeline instance for Feishu
_feishu_pipeline: CollaborationPipeline | None = None


def get_feishu_pipeline() -> CollaborationPipeline:
    """Get or create pipeline for Feishu."""
    global _feishu_pipeline
    if _feishu_pipeline is None:
        _feishu_pipeline = CollaborationPipeline(enable_tracing=False)
    return _feishu_pipeline


@app.get("/feishu/webhook")
async def feishu_webhook_verify(request: Request):
    """Feishu webhook verification endpoint (GET).

    Feishu sends a GET request with challenge parameter for verification.
    """
    params = dict(request.query_params)

    # Feishu webhook verification challenge
    if "challenge" in params:
        challenge = params["challenge"]
        return {"challenge": challenge}

    # Otherwise return OK for health check
    return {"status": "ok"}


@app.post("/feishu/webhook")
async def feishu_webhook_event(request: Request):
    """Feishu webhook event receiver (POST).

    Receives events from Feishu and processes them through the agent pipeline.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    # Get Feishu config
    config = _load_feishu_config()
    encrypt_key = config.get("encryptKey", "")

    # Verify signature if encryption is enabled
    headers = dict(request.headers)
    timestamp = headers.get("X-Lark-Request-Timestamp", "")
    signature = headers.get("X-Lark-Signature", "")

    if encrypt_key and timestamp and signature:
        # Create signature verification string
        string_to_sign = f"{timestamp}{encrypt_key}"
        sign = hmac.new(
            encrypt_key.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        expected = base64.b64encode(sign).decode("utf-8")

        if expected != signature:
            raise HTTPException(status_code=401, detail="Invalid signature")

    # Handle different event types
    event_type = body.get("type")

    # Subscription confirmation (URL verification)
    if event_type == "url_verification":
        challenge = body.get("challenge", "")
        return {"challenge": challenge}

    # Event callback
    if event_type == "event_callback":
        event = body.get("event", {})

        # Handle message events
        if event.get("event_type") == "im.message.receive_v1":
            message = event.get("message", {})
            _chat_id = message.get("chat_id", "")
            msg_id = message.get("message_id", "")
            msg_type = message.get("message_type", "text")
            content_str = message.get("content", "{}")

            # Only process text messages in p2p (direct) chats
            chat_type = message.get("chat_type", "p2p")
            if chat_type != "p2p":
                return {"status": "ignored", "reason": "group messages not supported yet"}

            # Parse message content
            text = parse_message_content(content_str, msg_type)

            if not text:
                return {"status": "ignored", "reason": "empty message"}

            # Get sender info
            sender = event.get("sender", {})
            sender_id = sender.get("sender_id", {}).get("open_id", "")

            # Process message through pipeline
            pipeline = get_feishu_pipeline()

            try:
                result = pipeline.invoke(text)
                response_text = result.get("final_response", "处理中...")
            except Exception as e:
                response_text = f"抱歉，处理消息时出错: {str(e)}"

            # Send response back to Feishu
            feishu_client = get_feishu_client()
            try:
                await feishu_client.send_text(
                    receive_id=sender_id,
                    text=response_text,
                    msg_id=msg_id,
                )
            except Exception as e:
                # Log error but don't fail the webhook
                print(f"Failed to send Feishu response: {e}")

            return {"status": "ok"}

    # Unknown event type
    return {"status": "ignored"}


# ============================================================================
# Feishu WebSocket 控制端点
# ============================================================================

@app.get("/feishu/status")
async def feishu_status():
    """Check Feishu WebSocket connection status."""
    global _feishu_ws_thread
    return {
        "ws_running": _feishu_ws_thread is not None and _feishu_ws_thread.is_alive(),
        "config": {
            "app_id": _load_feishu_config().get("appId", ""),
            "domain": _load_feishu_config().get("domain", "feishu"),
        }
    }


@app.post("/feishu/start")
async def feishu_start():
    """Manually start Feishu WebSocket client."""
    global _feishu_ws_thread

    if _feishu_ws_thread is not None and _feishu_ws_thread.is_alive():
        return {"status": "already_running"}

    start_feishu_ws()
    return {"status": "starting"}


@app.post("/feishu/stop")
async def feishu_stop():
    """Stop Feishu WebSocket client."""
    global _feishu_ws_thread

    ws_client = get_feishu_ws_client()
    ws_client.stop()

    _feishu_ws_thread = None
    return {"status": "stopped"}


# ============================================================================
# 入口
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
