-- =============================================================================
-- RAG API — Supabase schema (Phases 1–3 final state)
-- =============================================================================
-- Paste this into the Supabase SQL Editor and run it once.
--
-- This creates the FINAL schema directly (skips the temporary Phase-1 1536-d
-- chunks table that Alembic migration 0001 then drops in 0002).
--
-- After running, Alembic is stamped at head so `poetry run python scripts/migrate.py`
-- will see the DB as already migrated.
--
-- Safe to re-run: uses IF NOT EXISTS / DROP IF EXISTS where practical.
-- WARNING: DROP TABLE will remove existing RAG data if those tables already exist.
-- =============================================================================

-- Required for VECTOR / HNSW (available on Supabase)
CREATE EXTENSION IF NOT EXISTS vector;

-- ---------------------------------------------------------------------------
-- Clean recreate of app tables (comment out DROPs if you must preserve data)
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS messages CASCADE;
DROP TABLE IF EXISTS conversations CASCADE;
DROP TABLE IF EXISTS document_chunks CASCADE;
DROP TABLE IF EXISTS documents CASCADE;

-- ---------------------------------------------------------------------------
-- documents
-- ---------------------------------------------------------------------------
CREATE TABLE documents (
    id UUID PRIMARY KEY,
    filename VARCHAR(512) NOT NULL,
    file_size BIGINT NOT NULL,
    mime_type VARCHAR(255) NOT NULL,
    sha256_hash VARCHAR(64) NOT NULL,
    total_pages INTEGER NOT NULL DEFAULT 0,
    total_chunks INTEGER NOT NULL DEFAULT 0,
    embedding_model VARCHAR(255) NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_documents_sha256_hash UNIQUE (sha256_hash)
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_documents_sha256_hash
    ON documents (sha256_hash);

-- ---------------------------------------------------------------------------
-- document_chunks (BGE-small 384-d embeddings)
-- ---------------------------------------------------------------------------
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY,
    document_id UUID NOT NULL,
    page_number INTEGER NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    token_count INTEGER NOT NULL DEFAULT 0,
    embedding VECTOR(384) NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_document_chunks_document_id
        FOREIGN KEY (document_id)
        REFERENCES documents (id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_document_chunks_document_id
    ON document_chunks (document_id);

CREATE INDEX IF NOT EXISTS ix_document_chunks_chunk_index
    ON document_chunks (chunk_index);

CREATE INDEX IF NOT EXISTS ix_document_chunks_document_id_chunk_index
    ON document_chunks (document_id, chunk_index);

-- Cosine similarity index for retrieval
CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_cosine
    ON document_chunks
    USING hnsw (embedding vector_cosine_ops);

-- ---------------------------------------------------------------------------
-- conversations / messages (chat history)
-- ---------------------------------------------------------------------------
CREATE TABLE conversations (
    id UUID PRIMARY KEY,
    title VARCHAR(512) NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE messages (
    id UUID PRIMARY KEY,
    conversation_id UUID NOT NULL,
    role VARCHAR(32) NOT NULL,
    content TEXT NOT NULL,
    retrieved_chunk_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    citations JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_messages_conversation_id
        FOREIGN KEY (conversation_id)
        REFERENCES conversations (id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_messages_conversation_id
    ON messages (conversation_id);

CREATE INDEX IF NOT EXISTS ix_messages_conversation_id_created_at
    ON messages (conversation_id, created_at);

-- ---------------------------------------------------------------------------
-- Alembic version stamp (matches app/db/migrations head)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

DELETE FROM alembic_version;
INSERT INTO alembic_version (version_num)
VALUES ('0003_conversations_messages');