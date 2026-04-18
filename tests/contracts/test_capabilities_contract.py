"""Capabilities API 契约测试 - /api/capabilities 端点。"""
import sys
sys.path.insert(0, '.')

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.testclient import TestClient
from backend.main import app


@pytest.fixture
def sync_client():
    """同步 TestClient。"""
    return TestClient(app)


class TestCapabilitiesAPI:
    """Capabilities API 契约测试。"""

    def test_capabilities_returns_ok(self, sync_client):
        """GET /api/capabilities 返回 status=ok。"""
        resp = sync_client.get("/api/capabilities")
        assert resp.status_code == 200
        data = resp.json()

        # 检查基本结构
        assert "channels" in data
        assert "intents" in data
        assert "tools" in data
        assert "teams" in data
        assert "features" in data

    def test_capabilities_channels(self, sync_client):
        """返回支持的通道列表。"""
        resp = sync_client.get("/api/capabilities")
        data = resp.json()

        assert isinstance(data["channels"], list)
        assert len(data["channels"]) > 0
        assert "feishu" in data["channels"] or "http" in data["channels"]

    def test_capabilities_intents(self, sync_client):
        """返回支持的意图类型。"""
        resp = sync_client.get("/api/capabilities")
        data = resp.json()

        assert isinstance(data["intents"], list)
        assert len(data["intents"]) > 0
        # 检查基本意图
        expected_intents = ["climate_control", "navigation", "music", "vehicle_status"]
        for intent in expected_intents:
            assert intent in data["intents"], f"Missing intent: {intent}"

    def test_capabilities_tools(self, sync_client):
        """返回可用工具列表。"""
        resp = sync_client.get("/api/capabilities")
        data = resp.json()

        assert isinstance(data["tools"], list)
        assert len(data["tools"]) > 0

    def test_capabilities_teams(self, sync_client):
        """返回可用的Agent团队。"""
        resp = sync_client.get("/api/capabilities")
        data = resp.json()

        assert isinstance(data["teams"], list)

    def test_capabilities_features(self, sync_client):
        """返回功能特性列表。"""
        resp = sync_client.get("/api/capabilities")
        data = resp.json()

        features = data["features"]
        assert isinstance(features, dict)
        # 检查关键特性
        assert features.get("streaming") is True
        assert features.get("multi_agent") is True
        assert features.get("hierarchical_teams") is True
