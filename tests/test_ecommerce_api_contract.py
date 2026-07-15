from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

import backend.middleware.production as production
from backend.main import app


client = TestClient(app)


@pytest.fixture(autouse=True)
def allow_requests(monkeypatch):
    class DummySession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def add(self, _item):
            return None

        async def commit(self):
            return None

    monkeypatch.setattr(production, "_allow_request", AsyncMock(return_value=(True, 120, False)))
    monkeypatch.setattr(production, "AsyncSessionLocal", lambda: DummySession())


def test_ecommerce_dashboard_endpoint_returns_kpis():
    response = client.get("/api/ecommerce/dashboard")

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 200
    assert "gmv" in payload["data"]["kpis"]
    assert payload["data"]["anomalies"]


def test_ecommerce_agent_endpoint_returns_trace_and_recommendations():
    response = client.post("/api/ecommerce/agent/analyze", json={"question": "昨天 GMV 为什么下降？"})

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["intent"] == "business_diagnosis"
    assert data["tool_trace"]
    assert data["recommendations"]


def test_recommendation_approval_flow():
    created = client.post("/api/ecommerce/agent/analyze", json={"question": "哪些广告计划 ROI 太低？"}).json()["data"]
    recommendation_id = created["recommendations"][0]["id"]

    approved = client.post(f"/api/ecommerce/recommendations/{recommendation_id}/approve").json()["data"]

    assert approved["status"] == "approved"


def test_campaign_plan_uses_selected_goal():
    response = client.get("/api/ecommerce/campaigns/plan", params={"goal": "新品冷启动"})

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["goal"] == "新品冷启动"
    assert data["theme"] == "新品冷启动策略"
    assert data["tool_trace"][0]["input"]["goal"] == "新品冷启动"
