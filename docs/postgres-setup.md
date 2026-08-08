# PostgreSQL Setup for rag-api

This document explains the PostgreSQL setup needed for this project, including tables, extensions, scripts, and configuration requirements.

## 1. Required PostgreSQL extensions

The project requires the following PostgreSQL extension:

- `vector`

This is the pgvector extension used to store embedding vectors and run similarity search.

### Install or enable the extension

If you use a managed Postgres service like Supabase, enable the `vector` extension in the SQL editor or database settings.

If you use a local Postgres instance, run:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

## 2. Database configuration

Use a database URL in the `.env` file that matches your Docker Compose setup.

### Docker Compose configuration

Your current Docker Compose service is:

```yaml
services:
  postgres:
    image: postgres:17
    container_name: my-postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: mydb
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### Matching `.env` value

For local use from the host machine, set:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/mydb
```

If the app runs inside the same Docker Compose network, the host should be `postgres` instead of `localhost`.

## 3. Required tables

The project schema is created by Alembic migrations. There are four main application tables plus the Alembic version table.

### Full table list

| Table | Purpose |
| --- | --- |
| `documents` | Stores uploaded file metadata, dedupe hash, page/chunk counts, and embedding model information. |
| `document_chunks` | Stores text chunks, embeddings, metadata, and chunk ordering for retrieval. |
| `conversations` | Stores chat conversation metadata. |
| `messages` | Stores individual chat messages, retrieved chunk references, and citations. |
| `alembic_version` | Tracks the current Alembic migration head. |

### Table responsibilities

- `documents`
  - Stores uploaded file metadata, dedupe hash, page/chunk counts, and embedding model details.
  - Key columns: `id`, `filename`, `file_size`, `mime_type`, `sha256_hash`, `total_pages`, `total_chunks`, `embedding_model`, `metadata`, `created_at`.

- `document_chunks`
  - Stores document chunk text, vector embeddings, metadata, and chunk position data.
  - Key columns: `id`, `document_id`, `page_number`, `chunk_index`, `content`, `token_count`, `embedding`, `metadata`, `created_at`.
  - Foreign key: `document_id` references `documents.id`.
  - Indexes:
    - `ix_document_chunks_document_id`
    - `ix_document_chunks_chunk_index`
    - `ix_document_chunks_document_id_chunk_index`
    - `ix_document_chunks_embedding_cosine` using HNSW and `vector_cosine_ops`

- `conversations`
  - Stores chat conversation metadata.
  - Key columns: `id`, `title`, `created_at`, `updated_at`.

- `messages`
  - Stores chat history messages and references retrieved chunks/citations.
  - Key columns: `id`, `conversation_id`, `role`, `content`, `retrieved_chunk_ids`, `citations`, `created_at`.
  - Foreign key: `conversation_id` references `conversations.id`.
  - Indexes:
    - `ix_messages_conversation_id`
    - `ix_messages_conversation_id_created_at`

## 4. Migrations and scripts

The project supports two migration workflows:

### 4.1 Alembic migrations

Alembic migrations are stored in `app/db/migrations/versions/`.

- `0001_enable_pgvector.py` — enables the `vector` extension and creates the initial `document_chunks` table.
- `0002_documents_and_chunks.py` — adds the `documents` table and recreates `document_chunks` for the current schema.
- `0003_conversations_messages.py` — adds the `conversations` and `messages` tables.

Run migrations from the project root with:

```bash
poetry run python scripts/migrate.py
```

### 4.2 Supabase / manual SQL setup

If you prefer manual setup, the `scripts/README.md` mentions `scripts/supabase_schema.sql`.

That SQL file creates the same final schema and stamps Alembic to the current head.

### 4.3 Scripts folder contents

The `scripts/` folder contains the following useful helpers:

- `migrate.py`
  - Runs the Alembic upgrade to the current migration head.
  - Supports `current`, `history`, and `downgrade` operations via command-line arguments.
  - Reads `DATABASE_URL` from `.env`.

- `migrate.ps1`
  - PowerShell wrapper for `scripts/migrate.py`.
  - Useful on Windows to run migration commands from PowerShell.

- `README.md`
  - Explains the migration workflow and the two setup options: Supabase SQL or Alembic migration.

- `supabase_schema.sql`
  - Contains the full final schema SQL for manual execution.
  - Can be applied directly in Supabase SQL editor or any PostgreSQL query runner.

- `test_db_connect.py`
  - Verifies the `DATABASE_URL` connection string.
  - Attempts a simple SQL query against Postgres using `asyncpg`.
  - Helpful to confirm the database is reachable before running the application.

## 5. What to configure in PostgreSQL

### Database user and password

Your Docker Compose uses:

- `POSTGRES_USER=postgres`
- `POSTGRES_PASSWORD=postgres`
- `POSTGRES_DB=mydb`

Make sure these match the connection string in `.env`.

### Network access

- For host access from Windows, use `localhost:5432`.
- For container-to-container access inside Docker Compose, use `postgres:5432`.

### Extensions and indexes

- Install or enable `vector`.
- The project creates a cosine similarity index for `document_chunks.embedding` using HNSW.
- No additional Postgres extensions are required for the app beyond `vector`.

## 6. Validation steps

1. Start the database container:

```powershell
docker compose up -d
```

2. Confirm the service is running and port 5432 is available.

3. Confirm `.env` uses the local database URL.

4. Run the migration script:

```powershell
poetry run python scripts/migrate.py
```

5. Optionally run the connection test script:

```powershell
python .\scripts\test_db_connect.py
```

## 7. Notes

- The app uses async SQLAlchemy with `asyncpg`, so the connection URL must be `postgresql+asyncpg://...`.
- Your current migrations expect a 384-dimensional `vector` column on `document_chunks`.
- The `vector` extension must support the `vector_cosine_ops` operator for the HNSW index.
