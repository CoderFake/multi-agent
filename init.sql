-- Enable pgvector extension for mem0 memory storage
CREATE EXTENSION IF NOT EXISTS vector;

-- Users table (UUIDv7 PK + Firebase UID)
CREATE TABLE IF NOT EXISTS users (
    id              VARCHAR(36)  PRIMARY KEY,
    firebase_uid    VARCHAR(128) NOT NULL UNIQUE,
    email           VARCHAR(255),
    display_name    VARCHAR(255),
    photo_url       VARCHAR(1024),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    last_seen_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_users_firebase_uid ON users(firebase_uid);

-- Memories table (synced from mem0 — enables direct SQL queries)
CREATE TABLE IF NOT EXISTS memories (
    id          VARCHAR(36)  PRIMARY KEY,       -- mem0 memory ID
    user_id     VARCHAR(36)  NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    memory      TEXT         NOT NULL,
    score       FLOAT,
    categories  VARCHAR(512),
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_memories_user_created ON memories(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS documents (
    doc_id      TEXT PRIMARY KEY,
    file_name   TEXT        NOT NULL,
    minio_key   TEXT        NOT NULL,
    bucket      TEXT        NOT NULL DEFAULT 'documents',
    created_at  TIMESTAMP   NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS document_trees (
    doc_id      TEXT PRIMARY KEY REFERENCES documents(doc_id) ON DELETE CASCADE,
    tree_json   JSONB       NOT NULL
);

CREATE TABLE IF NOT EXISTS document_nodes (
    node_id     TEXT        NOT NULL,
    doc_id      TEXT        NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
    title       TEXT,
    summary     TEXT,
    content     TEXT,
    start_index INT,
    end_index   INT,
    pages       INT[],
    bboxes      JSONB,
    PRIMARY KEY (node_id, doc_id)
);

CREATE INDEX IF NOT EXISTS idx_document_nodes_doc_id ON document_nodes(doc_id);