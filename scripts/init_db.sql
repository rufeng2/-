-- ====================================================
-- 多模态企业知识库 RAG 系统 - 数据库初始化
-- PostgreSQL 16 + pgvector
-- ====================================================

-- 启用 pgvector 扩展
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ====================================================
-- 1. 用户表
-- ====================================================
CREATE TABLE IF NOT EXISTS users (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username    VARCHAR(64)  NOT NULL UNIQUE,
    password    VARCHAR(255) NOT NULL,           -- bcrypt hash
    display_name VARCHAR(100) DEFAULT '',
    email       VARCHAR(255) DEFAULT '',
    role        VARCHAR(20)  NOT NULL DEFAULT 'user',  -- admin | user
    is_active   BOOLEAN      DEFAULT TRUE,
    department  VARCHAR(100) DEFAULT '',
    created_at  TIMESTAMPTZ  DEFAULT NOW(),
    updated_at  TIMESTAMPTZ  DEFAULT NOW()
);

-- ====================================================
-- 2. 部门表
-- ====================================================
CREATE TABLE IF NOT EXISTS departments (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        VARCHAR(100) NOT NULL UNIQUE,
    parent_id   UUID REFERENCES departments(id) ON DELETE CASCADE,
    description TEXT DEFAULT '',
    created_at  TIMESTAMPTZ  DEFAULT NOW()
);

-- ====================================================
-- 3. 知识库表
-- ====================================================
CREATE TABLE IF NOT EXISTS knowledge_bases (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            VARCHAR(120) NOT NULL UNIQUE,
    description     TEXT DEFAULT '',
    owner_id        UUID REFERENCES users(id) ON DELETE SET NULL,
    department_id   UUID REFERENCES departments(id) ON DELETE SET NULL,
    visibility      VARCHAR(20) DEFAULT 'internal',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
-- ====================================================
-- 3. 文档表
-- ====================================================
CREATE TABLE IF NOT EXISTS documents (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title           VARCHAR(500)  NOT NULL,
    file_type       VARCHAR(20)   DEFAULT '',    -- pdf|docx|xlsx|pptx|txt|image
    file_size       BIGINT        DEFAULT 0,
    storage_path    VARCHAR(1000) DEFAULT '',
    status          VARCHAR(20)   DEFAULT 'pending',  -- pending|parsing|indexed|failed
    uploader_id     UUID REFERENCES users(id) ON DELETE SET NULL,
    department_id   UUID REFERENCES departments(id) ON DELETE SET NULL,
    visibility      VARCHAR(20)   DEFAULT 'internal', -- public|internal|confidential
    knowledge_base_id UUID REFERENCES knowledge_bases(id) ON DELETE SET NULL,
    chunk_template  VARCHAR(30) DEFAULT 'general',
    page_count      INT           DEFAULT 0,
    parsed_text     TEXT          DEFAULT '',
    error_message   TEXT          DEFAULT '',
    quality_report  JSONB         DEFAULT '{}',
    created_at      TIMESTAMPTZ   DEFAULT NOW(),
    updated_at      TIMESTAMPTZ   DEFAULT NOW()
);

-- ====================================================
-- 4. 文档块表（Chunk + 向量）
-- ====================================================
CREATE TABLE IF NOT EXISTS document_chunks (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id     UUID REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index     INT           DEFAULT 0,
    content         TEXT          NOT NULL,
    content_type    VARCHAR(20)   DEFAULT 'text',  -- text|table|image
    metadata        JSONB         DEFAULT '{}',    -- {page, heading, etc.}
    embedding       vector(1024),                  -- 文本向量
    multimodal_embedding vector(1024),             -- 文本/表格/图片统一向量
    image_path      VARCHAR(500)  DEFAULT '',
    token_count     INT           DEFAULT 0,
    created_at      TIMESTAMPTZ   DEFAULT NOW()
);

-- 向量索引（IVFFlat 或 HNSW）
-- 数据量 > 1000 时再建索引效果更好
CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw ON document_chunks
  USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
CREATE INDEX IF NOT EXISTS idx_chunks_multimodal_hnsw ON document_chunks
  USING hnsw (multimodal_embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- ====================================================
-- 5. 文档块权限映射
-- ====================================================
CREATE TABLE IF NOT EXISTS chunk_permissions (
    chunk_id      UUID REFERENCES document_chunks(id) ON DELETE CASCADE,
    department_id UUID REFERENCES departments(id) ON DELETE CASCADE,
    PRIMARY KEY (chunk_id, department_id)
);

-- ====================================================
-- 6. 会话表
-- ====================================================
CREATE TABLE IF NOT EXISTS conversations (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
    title       VARCHAR(200) DEFAULT '新对话',
    created_at  TIMESTAMPTZ  DEFAULT NOW(),
    updated_at  TIMESTAMPTZ  DEFAULT NOW()
);

-- ====================================================
-- 7. 消息表
-- ====================================================
CREATE TABLE IF NOT EXISTS messages (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role            VARCHAR(10) NOT NULL,       -- user | assistant
    content         TEXT NOT NULL,
    references_json JSONB DEFAULT '[]',
    token_count     INT DEFAULT 0,
    latency_ms      INT DEFAULT 0,
    feedback        SMALLINT DEFAULT 0,         -- 1=有用, -1=没用
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ====================================================
-- 8. 反馈表
-- ====================================================
CREATE TABLE IF NOT EXISTS feedback (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    message_id  UUID REFERENCES messages(id) ON DELETE CASCADE,
    user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
    rating      SMALLINT NOT NULL,              -- 1 | -1
    comment     TEXT DEFAULT '',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ====================================================
-- 索引
-- ====================================================
CREATE INDEX IF NOT EXISTS idx_docs_uploader ON documents(uploader_id);
CREATE INDEX IF NOT EXISTS idx_docs_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_docs_knowledge_base ON documents(knowledge_base_id);
CREATE INDEX IF NOT EXISTS idx_chunks_doc ON document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_type ON document_chunks(content_type);
CREATE INDEX IF NOT EXISTS idx_chunks_content_trgm ON document_chunks USING gin (content gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_conv_user ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_msg_conv ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_msg_feedback ON messages(feedback);

-- ====================================================
-- 默认部门
-- ====================================================
INSERT INTO departments (id, name, description) VALUES
    ('00000000-0000-0000-0000-000000000001', '全员', '所有用户可见'),
    ('00000000-0000-0000-0000-000000000002', '技术部', '技术部门'),
    ('00000000-0000-0000-0000-000000000003', '人事部', '人力资源部门'),
    ('00000000-0000-0000-0000-000000000004', '财务部', '财务部门')
ON CONFLICT (name) DO NOTHING;

INSERT INTO knowledge_bases (id, name, description, visibility) VALUES
    ('00000000-0000-0000-0000-000000000100', '默认知识库', '系统默认知识库', 'internal')
ON CONFLICT (name) DO NOTHING;
-- ====================================================
-- RAG 自动评测
-- ====================================================
CREATE TABLE IF NOT EXISTS evaluation_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    question TEXT NOT NULL,
    expected_answer TEXT DEFAULT '',
    expected_keywords JSONB DEFAULT '[]',
    expected_document_titles JSONB DEFAULT '[]',
    expected_chunk_ids JSONB DEFAULT '[]',
    expected_pages JSONB DEFAULT '[]',
    category VARCHAR(60) DEFAULT '通用',
    knowledge_base_id UUID REFERENCES knowledge_bases(id) ON DELETE SET NULL,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS evaluation_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    sample_count INT DEFAULT 0,
    metrics JSONB DEFAULT '{}',
    details JSONB DEFAULT '[]',
    status VARCHAR(20) DEFAULT 'pending',
    progress INT DEFAULT 0,
    error_message TEXT DEFAULT '',
    options JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);