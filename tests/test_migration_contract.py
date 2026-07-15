from pathlib import Path

from backend.db.models import Base


ROOT = Path(__file__).resolve().parents[1]


def test_application_startup_does_not_run_schema_ddl():
    source = (ROOT / "backend" / "main.py").read_text(encoding="utf-8")
    assert "ensure_runtime_schema" not in source


def test_alembic_configuration_and_baseline_exist():
    assert (ROOT / "alembic.ini").exists()
    assert (ROOT / "backend" / "db" / "alembic" / "env.py").exists()
    revisions = list((ROOT / "backend" / "db" / "alembic" / "versions").glob("*.py"))
    assert revisions
    source = revisions[0].read_text(encoding="utf-8")
    assert "def upgrade()" in source
    assert "Destructive baseline downgrade is not supported" in source


def test_orm_metadata_contains_runtime_tables():
    required = {"users", "documents", "document_chunks", "audit_logs", "long_term_memories"}
    assert required <= set(Base.metadata.tables)
