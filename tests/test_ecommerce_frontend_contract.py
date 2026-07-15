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
