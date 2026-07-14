"""测试 app 能否成功加载"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__))))
os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@localhost:5432/test"
os.environ["SECRET_KEY"] = "test"
os.environ["DEEPSEEK_API_KEY"] = "test"
os.environ["DASHSCOPE_API_KEY"] = "test"
os.environ["ADMIN_PASSWORD"] = "test"

try:
    from backend.main import app
    print(f"OK: {len(app.routes)} routes loaded")
except Exception as e:
    print(f"FAIL: {type(e).__name__}: {e}")
    sys.exit(1)
