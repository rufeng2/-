# Runtime secrets

Create one-line files here and reference them with *_FILE environment variables.
Never commit real values. Supported names: SECRET_KEY_FILE, ADMIN_PASSWORD_FILE,
DATABASE_URL_FILE, MINIO_SECRET_KEY_FILE, DEEPSEEK_API_KEY_FILE,
DASHSCOPE_API_KEY_FILE, and OIDC_CLIENT_SECRET_FILE.

For production, use Docker/Kubernetes secrets or a vault and mount them read-only.