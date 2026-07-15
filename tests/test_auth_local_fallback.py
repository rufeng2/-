import asyncio

import pytest

from backend.api import auth
from backend.schemas.user import LoginRequest, RegisterRequest


class OfflineDb:
    async def execute(self, *_args, **_kwargs):
        raise OSError("database offline")


def test_register_uses_local_demo_auth_store_when_database_is_unavailable(monkeypatch, tmp_path):
    monkeypatch.setattr(auth.settings, "APP_ENV", "development")
    monkeypatch.setattr(auth, "LOCAL_AUTH_STORE_PATH", tmp_path / "users.json", raising=False)

    response = asyncio.run(
        auth.register(RegisterRequest(username="local_user", password="Password123"), OfflineDb())
    )

    assert response.code == 200
    assert response.username == "local_user"
    assert response.token


def test_login_uses_local_demo_auth_store_after_fallback_registration(monkeypatch, tmp_path):
    monkeypatch.setattr(auth.settings, "APP_ENV", "development")
    monkeypatch.setattr(auth, "LOCAL_AUTH_STORE_PATH", tmp_path / "users.json", raising=False)

    asyncio.run(auth.register(RegisterRequest(username="local_user", password="Password123"), OfflineDb()))
    response = asyncio.run(auth.login(LoginRequest(username="local_user", password="Password123"), OfflineDb()))

    assert response.code == 200
    assert response.username == "local_user"
    assert response.role == "user"
    assert response.token


def test_local_demo_auth_store_is_disabled_in_production(monkeypatch, tmp_path):
    monkeypatch.setattr(auth.settings, "APP_ENV", "production")
    monkeypatch.setattr(auth, "LOCAL_AUTH_STORE_PATH", tmp_path / "users.json", raising=False)

    with pytest.raises(OSError):
        asyncio.run(auth.register(RegisterRequest(username="local_user", password="Password123"), OfflineDb()))
