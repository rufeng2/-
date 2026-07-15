from pathlib import Path

from backend.ecommerce.agent import EcommerceAgent
from backend.ecommerce.data_loader import EcommerceDataLoader
from backend.ecommerce.recommendations import RecommendationStore


def test_agent_returns_tool_trace_for_gmv_question():
    dataset = EcommerceDataLoader(Path("data/ecommerce")).load()
    agent = EcommerceAgent(dataset)

    result = agent.analyze("昨天 GMV 为什么下降？")

    assert result.intent == "business_diagnosis"
    assert [step.tool_name for step in result.tool_trace] == ["get_kpi_snapshot", "detect_anomalies", "rank_products"]
    assert result.evidence
    assert any(action.risk_level == "high" for action in result.recommendations)
    assert result.confidence >= 0.7


def test_agent_routes_campaign_question():
    dataset = EcommerceDataLoader(Path("data/ecommerce")).load()
    agent = EcommerceAgent(dataset)

    result = agent.analyze("哪些商品适合参加大促？")

    assert result.intent == "campaign_planning"
    assert any(step.tool_name == "generate_campaign_plan" for step in result.tool_trace)
    assert "活动" in result.summary


def test_recommendation_store_status_transition():
    dataset = EcommerceDataLoader(Path("data/ecommerce")).load()
    analysis = EcommerceAgent(dataset).analyze("哪些广告计划 ROI 太低？")
    store = RecommendationStore()
    store.seed_from_analysis(analysis)
    pending = store.list(status="pending")

    assert len(pending) >= 2
    approved = store.approve(pending[0].id, operator="admin")
    assert approved.status == "approved"
    rejected = store.reject(pending[-1].id, operator="admin")
    assert rejected.status == "rejected"
