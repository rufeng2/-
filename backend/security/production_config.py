"""Fail-fast validation for settings that are unsafe in production."""

DEFAULT_SECRET_KEY = "your-256-bit-secret-change-in-production"
DEFAULT_ADMIN_PASSWORD = "admin123456"
DEFAULT_MINIO_SECRET = "minioadmin"
PASSWORD_ROTATION_PATHS = {"/api/users/password", "/api/verify", "/api/logout"}


def password_rotation_allows(path: str, must_change_password: bool) -> bool:
    return not must_change_password or path in PASSWORD_ROTATION_PATHS


def validate_production_settings(settings) -> list[str]:
    if str(settings.APP_ENV).lower() != "production":
        return []
    errors: list[str] = []
    if settings.DEBUG:
        errors.append("DEBUG must be false in production")
    if not settings.SECRET_KEY or settings.SECRET_KEY == DEFAULT_SECRET_KEY or len(settings.SECRET_KEY) < 32:
        errors.append("SECRET_KEY must be a non-default secret of at least 32 characters")
    if not settings.ADMIN_PASSWORD or settings.ADMIN_PASSWORD == DEFAULT_ADMIN_PASSWORD or len(settings.ADMIN_PASSWORD) < 16:
        errors.append("ADMIN_PASSWORD must be a non-default secret of at least 16 characters")
    if settings.ACCESS_TOKEN_EXPIRE_MINUTES > 120:
        errors.append("ACCESS_TOKEN_EXPIRE_MINUTES must not exceed 120 in production")
    if not settings.DEEPSEEK_API_KEY:
        errors.append("DEEPSEEK_API_KEY is required in production")
    if not settings.DASHSCOPE_API_KEY:
        errors.append("DASHSCOPE_API_KEY is required for embeddings in production")
    if settings.USE_MINIO:
        if not settings.MINIO_SECRET_KEY or settings.MINIO_SECRET_KEY == DEFAULT_MINIO_SECRET:
            errors.append("MINIO_SECRET_KEY must not use the default credential")
        if not settings.MINIO_SECURE:
            errors.append("MINIO_SECURE must be true in production")
    return errors


def assert_production_settings(settings) -> None:
    errors = validate_production_settings(settings)
    if errors:
        raise RuntimeError("Unsafe production configuration: " + "; ".join(errors))
