-- ============================================================
-- init.sql — PostgreSQL schema for pageindex_db
-- Generated from SQLAlchemy models (backend + file-service)
-- ============================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- USERS
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id              VARCHAR(36)   PRIMARY KEY,
    firebase_uid    VARCHAR(128)  NOT NULL UNIQUE,
    email           VARCHAR(255),
    display_name    VARCHAR(255),
    photo_url       VARCHAR(1024),
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    last_seen_at    TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_users_firebase_uid ON users(firebase_uid);

-- ============================================================
-- MEMORIES  (synced from mem0)
-- ============================================================
CREATE TABLE IF NOT EXISTS memories (
    id          VARCHAR(36)   PRIMARY KEY,
    user_id     VARCHAR(36)   NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    memory      TEXT          NOT NULL,
    score       FLOAT,
    categories  VARCHAR(512),
    created_at  TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_memories_user_created ON memories(user_id, created_at DESC);

-- ============================================================
-- CHAT SESSIONS & MESSAGES
-- ============================================================
CREATE TABLE IF NOT EXISTS chat_sessions (
    id          VARCHAR(36)   PRIMARY KEY,
    user_id     VARCHAR(36)   NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title       VARCHAR(255),
    created_at  TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions(user_id);

CREATE TABLE IF NOT EXISTS chat_messages (
    id          VARCHAR(36)   PRIMARY KEY,
    session_id  VARCHAR(36)   NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    "order"     INTEGER       NOT NULL DEFAULT 0,
    query       TEXT          NOT NULL,
    response    TEXT,
    created_at  TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON chat_messages(session_id);

-- ============================================================
-- DOCUMENTS  (owned by file-service)
-- ============================================================
CREATE TABLE IF NOT EXISTS documents (
    doc_id      VARCHAR(64)   PRIMARY KEY,
    file_name   VARCHAR(512)  NOT NULL,
    minio_key   VARCHAR(512)  NOT NULL,
    bucket      VARCHAR(128)  NOT NULL DEFAULT 'documents',
    user_id     VARCHAR(256),
    status      VARCHAR(32)   NOT NULL DEFAULT 'processing',
    engine      VARCHAR(32)   NOT NULL DEFAULT 'hybrid',
    page_count  INTEGER       NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

-- ============================================================
-- DOCUMENT TREES  (one per document)
-- ============================================================
CREATE TABLE IF NOT EXISTS document_trees (
    doc_id      VARCHAR(64)   PRIMARY KEY REFERENCES documents(doc_id) ON DELETE CASCADE,
    tree_json   JSONB         NOT NULL
);

-- ============================================================
-- DOCUMENT NODES
-- ============================================================
CREATE TABLE IF NOT EXISTS document_nodes (
    node_id     VARCHAR(128)  NOT NULL,
    doc_id      VARCHAR(64)   NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
    parent_id   VARCHAR(128),
    title       TEXT          NOT NULL DEFAULT '',
    summary     TEXT          NOT NULL DEFAULT '',
    content     TEXT          NOT NULL DEFAULT '',
    start_index INTEGER       NOT NULL DEFAULT 0,
    end_index   INTEGER       NOT NULL DEFAULT 0,
    pages       INTEGER[],
    bboxes      JSONB,
    PRIMARY KEY (node_id, doc_id)
);
CREATE INDEX IF NOT EXISTS idx_document_nodes_doc_id ON document_nodes(doc_id);