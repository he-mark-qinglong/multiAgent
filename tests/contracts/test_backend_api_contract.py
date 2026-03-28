"""Backend API 契约测试 - FastAPI /api/chat SSE 端点。"""
import sys
sys.path.insert(0, '.')

import asyncio
import pytest
from httpx import ASGITransport, AsyncClient
from starlette.testclient import TestClient
from sse_starlette.sse import AppStatus
from backend.main import app


@pytest.fixture(autouse=True)
def reset_sse_app_status():
    """重置 sse_starlette AppStatus，避免 event loop 冲突。"""
    AppStatus.should_exit_event = asyncio.Event()


@pytest.fixture
def sync_client():
    """同步 TestClient（用于非 SSE 端点）。"""
    return TestClient(app)


class TestBackendAPI:
    """FastAPI 后端 API 契约测试。"""

    # ── 健康检查 ──────────────────────────────────────────────

    def test_health_returns_ok(self, sync_client):
        """GET /api/health 返回 status=ok。"""
        resp = sync_client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data

    # ── 工具路由 ──────────────────────────────────────────────

    def test_list_tools_returns_array(self, sync_client):
        """GET /api/tools 返回工具列表。"""
        resp = sync_client.get("/api/tools")
        assert resp.status_code == 200
        data = resp.json()
        assert "tools" in data
        assert isinstance(data["tools"], list)

    def test_call_tool_climate(self, sync_client):
        """POST /api/tools/climate_control 返回成功。"""
        resp = sync_client.post("/api/tools/climate_control?action=get_status")
        assert resp.status_code == 200
        data = resp.json()
        assert "success" in data

    def test_call_tool_navigation(self, sync_client):
        """POST /api/tools/navigation 返回成功。"""
        resp = sync_client.post("/api/tools/navigation?action=get_traffic")
        assert resp.status_code == 200
        data = resp.json()
        assert "success" in data

    def test_call_tool_music(self, sync_client):
        """POST /api/tools/music_player 返回成功。"""
        resp = sync_client.post("/api/tools/music_player?action=play")
        assert resp.status_code == 200
        data = resp.json()
        assert "success" in data

    def test_call_tool_vehicle_status(self, sync_client):
        """POST /api/tools/vehicle_status 返回成功。"""
        resp = sync_client.post("/api/tools/vehicle_status?action=get_status")
        assert resp.status_code == 200
        data = resp.json()
        assert "success" in data

    # ── SSE 聊天端点 ─────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_chat_sse_returns_200(self):
        """POST /api/chat 返回 200。"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            async with client.stream("POST", "/api/chat", json={"message": "你好"}) as resp:
                assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_chat_sse_contains_event_lines(self):
        """SSE 响应包含 event: 字段。"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            async with client.stream("POST", "/api/chat", json={"message": "你好"}) as resp:
                lines = []
                async for line in resp.aiter_lines():
                    lines.append(line)
                    if line.startswith("event:"):
                        break
                assert any(l.startswith("event:") for l in lines)

    @pytest.mark.asyncio
    async def test_chat_sse_think_event(self):
        """空调请求触发 think 事件。"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            async with client.stream("POST", "/api/chat", json={"message": "把空调开到24度"}) as resp:
                events = await _collect_events_async(resp)
                event_types = [e["type"] for e in events]
                assert "think" in event_types

    @pytest.mark.asyncio
    async def test_chat_sse_result_event(self):
        """所有请求都产生 result 事件。"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            async with client.stream("POST", "/api/chat", json={"message": "你好"}) as resp:
                events = await _collect_events_async(resp)
                event_types = [e["type"] for e in events]
                assert "result" in event_types

    @pytest.mark.asyncio
    async def test_chat_sse_done_event(self):
        """SSE 响应以 done 事件结束。"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            async with client.stream("POST", "/api/chat", json={"message": "你好"}) as resp:
                events = await _collect_events_async(resp)
                event_types = [e["type"] for e in events]
                assert "done" in event_types

    @pytest.mark.asyncio
    async def test_chat_sse_observation_for_tool(self):
        """工具请求产生 observation 事件。"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            async with client.stream("POST", "/api/chat", json={"message": "把空调开到24度"}) as resp:
                events = await _collect_events_async(resp)
                event_types = [e["type"] for e in events]
                assert "observation" in event_types

    @pytest.mark.asyncio
    async def test_chat_with_session_id(self):
        """session_id 参数被接受。"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            async with client.stream("POST", "/api/chat", json={"message": "你好", "session_id": "test-123"}) as resp:
                assert resp.status_code == 200

    def test_chat_empty_message_rejected(self, sync_client):
        """空消息返回 422。"""
        resp = sync_client.post("/api/chat", json={"message": ""})
        assert resp.status_code == 422

    def test_chat_missing_message_rejected(self, sync_client):
        """缺少 message 字段返回 422。"""
        resp = sync_client.post("/api/chat", json={})
        assert resp.status_code == 422


# ── 辅助函数 ─────────────────────────────────────────────────────

async def _collect_events_async(response):
    """从 SSE 响应中异步解析出事件列表。"""
    events = []
    current_event_type = None
    import json

    async for line in response.aiter_lines():
        if line.startswith("event:"):
            current_event_type = line[len("event:"):].strip()
        elif line.startswith("data:"):
            current_data = line[len("data:"):].strip()
            try:
                parsed = json.loads(current_data)
                events.append({"type": current_event_type, "data": parsed})
            except Exception:
                events.append({"type": current_event_type, "data": current_data})
            current_event_type = None

    return events
