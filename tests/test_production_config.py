from types import SimpleNamespace

import pytest

from backend.security.production_config import password_rotation_allows, validate_production_settings


def production_settings(**overrides):
    values = {
        "APP_ENV": "production",
        "DEBUG": False,
        "SECRET_KEY": "a" * 48,
        "ADMIN_PASSWORD": "Strong-Initial-Password-2026!",
        "ACCESS_TOKEN_EXPIRE_MINUTES": 60,
        "DEEPSEEK_API_KEY": "provider-key",
        "DASHSCOPE_API_KEY": "embedding-key",
        "USE_MINIO": True,
        "MINIO_SECRET_KEY": "Strong-MinIO-Secret-2026!",
        "MINIO_SECURE": True,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_accepts_secure_production_settings():
    assert validate_production_settings(production_settings()) == []


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"DEBUG": True}, "DEBUG"),
        ({"SECRET_KEY": "your-256-bit-secret-change-in-production"}, "SECRET_KEY"),
        ({"ADMIN_PASSWORD": "admin123456"}, "ADMIN_PASSWORD"),
        ({"ACCESS_TOKEN_EXPIRE_MINUTES": 1440}, "ACCESS_TOKEN_EXPIRE_MINUTES"),
        ({"DEEPSEEK_API_KEY": ""}, "DEEPSEEK_API_KEY"),
        ({"DASHSCOPE_API_KEY": ""}, "DASHSCOPE_API_KEY"),
        ({"MINIO_SECRET_KEY": "minioadmin"}, "MINIO_SECRET_KEY"),
        ({"MINIO_SECURE": False}, "MINIO_SECURE"),
    ],
)
def test_rejects_unsafe_production_settings(override, message):
    errors = validate_production_settings(production_settings(**override))
    assert any(message in error for error in errors)


def test_development_settings_do_not_require_production_secrets():
    settings = production_settings(APP_ENV="development", DEBUG=True, SECRET_KEY="dev")
    assert validate_production_settings(settings) == []


def test_password_rotation_gate_only_allows_identity_routes():
    assert password_rotation_allows("/api/users/password", True)
    assert password_rotation_allows("/api/verify", True)
    assert not password_rotation_allows("/api/chat/send", True)
    assert password_rotation_allows("/api/chat/send", False)
