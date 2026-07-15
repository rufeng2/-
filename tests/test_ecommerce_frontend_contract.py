from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_frontend_uses_ecommerce_product_identity():
    app = read("frontend/src/App.vue")
    login = read("frontend/src/views/Login.vue")
    router = read("frontend/src/router/index.ts")

    assert "智能电商运营 Agent 平台" in app
    assert "运营驾驶舱" in app
    assert "运营 Agent" in app
    assert "运营知识库" in app
    assert "智能电商运营 Agent 平台" in login
    assert 'path: "/dashboard"' in router
    assert 'path: "/agent"' in router
    assert 'path: "/recommendations"' in router
    assert "企业知识库问答" not in app + login + router


def test_frontend_api_exports_ecommerce_client():
    client = read("frontend/src/api/client.ts")
    assert "export const ecommerceAPI" in client
    assert 'client.get("/ecommerce/dashboard")' in client
    assert 'client.post("/ecommerce/agent/analyze"' in client


def test_ecommerce_pages_render_agent_and_analysis_terms():
    pages = [
        "frontend/src/views/Ecommerce/Dashboard.vue",
        "frontend/src/views/Ecommerce/AgentWorkspace.vue",
        "frontend/src/views/Ecommerce/Products.vue",
        "frontend/src/views/Ecommerce/Campaigns.vue",
        "frontend/src/views/Ecommerce/Recommendations.vue",
    ]
    content = "\n".join(read(path) for path in pages)

    assert "GMV" in content
    assert "工具调用轨迹" in content
    assert "数据证据" in content
    assert "商品分层" in content
    assert "建议审批" in content
