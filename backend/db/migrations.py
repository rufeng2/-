"""Small idempotent migrations for deployments without Alembic history."""
from sqlalchemy import text

from backend.db.session import engine


async def ensure_runtime_schema() -> None:
    statements = [
        "CREATE EXTENSION IF NOT EXISTS pg_trgm",
        """
        CREATE TABLE IF NOT EXISTS audit_logs (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            username VARCHAR(64) DEFAULT '',
            role VARCHAR(20) DEFAULT '',
            action VARCHAR(20) NOT NULL,
            resource_type VARCHAR(80) DEFAULT '',
            resource_id VARCHAR(100) DEFAULT '',
            path VARCHAR(500) DEFAULT '',
            status_code INT DEFAULT 0,
            ip_address VARCHAR(64) DEFAULT '',
            request_id VARCHAR(64) DEFAULT '',
            details JSONB DEFAULT '{}',
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_audit_created_at ON audit_logs(created_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_audit_request_id ON audit_logs(request_id)",
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS retention_until TIMESTAMPTZ",
        "ALTER TABLE evaluation_runs ADD COLUMN IF NOT EXISTS is_baseline BOOLEAN DEFAULT FALSE",
        "ALTER TABLE evaluation_runs ADD COLUMN IF NOT EXISTS baseline_name VARCHAR(120) DEFAULT ''",
        """
        CREATE TABLE IF NOT EXISTS knowledge_bases (
            id UUID PRIMARY KEY,
            name VARCHAR(120) NOT NULL UNIQUE,
            description TEXT DEFAULT '',
            owner_id UUID REFERENCES users(id) ON DELETE SET NULL,
            department_id UUID REFERENCES departments(id) ON DELETE SET NULL,
            visibility VARCHAR(20) DEFAULT 'internal',
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
        """,
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS knowledge_base_id UUID REFERENCES knowledge_bases(id) ON DELETE SET NULL",
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS chunk_template VARCHAR(30) DEFAULT 'general'",
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS quality_report JSONB DEFAULT '{}'",
        "ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS multimodal_embedding vector(1024)",
        "ALTER TABLE IF EXISTS evaluation_items ADD COLUMN IF NOT EXISTS expected_document_titles JSONB DEFAULT '[]'",
        "ALTER TABLE IF EXISTS evaluation_items ADD COLUMN IF NOT EXISTS expected_chunk_ids JSONB DEFAULT '[]'",
        "ALTER TABLE IF EXISTS evaluation_items ADD COLUMN IF NOT EXISTS expected_pages JSONB DEFAULT '[]'",
        "ALTER TABLE IF EXISTS evaluation_runs ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'completed'",
        "ALTER TABLE IF EXISTS evaluation_runs ADD COLUMN IF NOT EXISTS progress INT DEFAULT 100",
        "ALTER TABLE IF EXISTS evaluation_runs ADD COLUMN IF NOT EXISTS error_message TEXT DEFAULT ''",
        "ALTER TABLE IF EXISTS evaluation_runs ADD COLUMN IF NOT EXISTS options JSONB DEFAULT '{}'",
        """
        CREATE TABLE IF NOT EXISTS evaluation_items (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            question TEXT NOT NULL,
            expected_answer TEXT DEFAULT '',
            expected_keywords JSONB DEFAULT '[]',
            category VARCHAR(60) DEFAULT '通用',
            knowledge_base_id UUID REFERENCES knowledge_bases(id) ON DELETE SET NULL,
            enabled BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS evaluation_runs (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            created_by UUID REFERENCES users(id) ON DELETE SET NULL,
            sample_count INT DEFAULT 0,
            metrics JSONB DEFAULT '{}',
            details JSONB DEFAULT '[]',
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
        """,
        "ALTER TABLE evaluation_items ADD COLUMN IF NOT EXISTS expected_document_titles JSONB DEFAULT '[]'",
        "ALTER TABLE evaluation_items ADD COLUMN IF NOT EXISTS expected_chunk_ids JSONB DEFAULT '[]'",
        "ALTER TABLE evaluation_items ADD COLUMN IF NOT EXISTS expected_pages JSONB DEFAULT '[]'",
        "ALTER TABLE evaluation_runs ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'completed'",
        "ALTER TABLE evaluation_runs ADD COLUMN IF NOT EXISTS progress INT DEFAULT 100",
        "ALTER TABLE evaluation_runs ADD COLUMN IF NOT EXISTS error_message TEXT DEFAULT ''",
        "ALTER TABLE evaluation_runs ADD COLUMN IF NOT EXISTS options JSONB DEFAULT '{}'",
        """
        CREATE TABLE IF NOT EXISTS long_term_memories (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            kind VARCHAR(30) DEFAULT 'task_summary',
            content TEXT NOT NULL,
            metadata JSONB DEFAULT '{}',
            embedding vector(1024),
            importance SMALLINT DEFAULT 50,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_long_memory_user ON long_term_memories(user_id, created_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_long_memory_embedding_hnsw ON long_term_memories USING hnsw (embedding vector_cosine_ops) WITH (m=12, ef_construction=48)",
        "CREATE INDEX IF NOT EXISTS idx_docs_knowledge_base ON documents(knowledge_base_id)",
        "CREATE INDEX IF NOT EXISTS idx_chunks_content_trgm ON document_chunks USING gin (content gin_trgm_ops)",
        "CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw ON document_chunks USING hnsw (embedding vector_cosine_ops) WITH (m=16, ef_construction=64)",
        "CREATE INDEX IF NOT EXISTS idx_chunks_multimodal_hnsw ON document_chunks USING hnsw (multimodal_embedding vector_cosine_ops) WITH (m=16, ef_construction=64)",
        """
        INSERT INTO knowledge_bases (id, name, description, visibility)
        VALUES ('00000000-0000-0000-0000-000000000100', '默认知识库', '系统自动迁移的现有文档', 'internal')
        ON CONFLICT (name) DO NOTHING
        """,
        """
        UPDATE documents
        SET knowledge_base_id = (
            SELECT id FROM knowledge_bases WHERE name = '默认知识库' LIMIT 1
        )
        WHERE knowledge_base_id IS NULL
        """,
    ]
    async with engine.begin() as connection:
        for statement in statements:
            await connection.execute(text(statement))

