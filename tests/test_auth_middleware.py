import asyncio

from starlette.requests import Request
from starlette.responses import JSONResponse

import backend.middleware.production as production


def _request(method: str, path: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": method,
            "path": path,
            "headers": [],
            "client": ("127.0.0.1", 49152),
            "scheme": "http",
            "server": ("testserver", 80),
            "query_string": b"",
        }
    )


def _run_middleware(monkeypatch, method: str, path: str):
    calls = {}

    async def fake_allow_request(identity: str, fail_closed: bool = False):
        calls["identity"] = identity
        calls["fail_closed"] = fail_closed
        return (False, 0, True) if fail_closed else (True, 120, True)

    class DummySession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def add(self, _item):
            return None

        async def commit(self):
            return None

    async def call_next(_request):
        return JSONResponse({"ok": True})

    monkeypatch.setattr(production, "_allow_request", fake_allow_request)
    monkeypatch.setattr(production, "AsyncSessionLocal", lambda: DummySession())

    response = asyncio.run(production.production_middleware(_request(method, path), call_next))
    return response, calls


def test_register_fails_open_when_rate_limiter_is_unavailable_in_development(monkeypatch):
    monkeypatch.setattr(production.settings, "APP_ENV", "development")

    response, calls = _run_middleware(monkeypatch, "POST", "/api/register")

    assert response.status_code == 200
    assert calls["fail_closed"] is False


def test_login_fails_open_when_rate_limiter_is_unavailable_in_development(monkeypatch):
    monkeypatch.setattr(production.settings, "APP_ENV", "development")

    response, calls = _run_middleware(monkeypatch, "POST", "/api/login")

    assert response.status_code == 200
    assert calls["fail_closed"] is False


def test_ecommerce_agent_fails_open_when_rate_limiter_is_unavailable_in_development(monkeypatch):
    monkeypatch.setattr(production.settings, "APP_ENV", "development")

    response, calls = _run_middleware(monkeypatch, "POST", "/api/ecommerce/agent/analyze")

    assert response.status_code == 200
    assert calls["fail_closed"] is False


def test_register_fails_closed_when_rate_limiter_is_unavailable_in_production(monkeypatch):
    monkeypatch.setattr(production.settings, "APP_ENV", "production")

    response, calls = _run_middleware(monkeypatch, "POST", "/api/register")

    assert response.status_code == 503
    assert calls["fail_closed"] is True


def test_ecommerce_agent_fails_closed_when_rate_limiter_is_unavailable_in_production(monkeypatch):
    monkeypatch.setattr(production.settings, "APP_ENV", "production")

    response, calls = _run_middleware(monkeypatch, "POST", "/api/ecommerce/agent/analyze")

    assert response.status_code == 503
    assert calls["fail_closed"] is True
