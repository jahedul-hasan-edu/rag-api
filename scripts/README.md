# Migration scripts

## Two ways to set up the database

### Option A — Supabase SQL Editor (manual)

Open **Supabase → SQL Editor**, paste and run:

[`scripts/supabase_schema.sql`](./supabase_schema.sql)

That creates the final schema (pgvector, `documents`, `document_chunks`, `conversations`, `messages`) and stamps Alembic at `0003_conversations_messages`.

Use this when you do not want to run Alembic from your machine.

### Option B — Alembic via script (remote connection)

`scripts/migrate.py` **does** execute SQL on whatever database `DATABASE_URL` points to — including Supabase — as long as `.env` has a valid connection string:

```env
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@db.YOUR_PROJECT.supabase.co:5432/postgres
```

```bash
poetry run python scripts/migrate.py
```

If you already ran Option A, Option B should report you are already at head (no changes).

---

## What the schema includes

| Object | Purpose |
| --- | --- |
| extension `vector` | pgvector |
| `documents` | uploaded files + SHA-256 dedupe |
| `document_chunks` | text + `VECTOR(384)` embeddings + HNSW cosine index |
| `conversations` / `messages` | chat history + citations |
| `alembic_version` | tracks migration head (`0003_conversations_messages`) |

## Alembic helper commands

```bash
poetry run python scripts/migrate.py              # upgrade to head
poetry run python scripts/migrate.py current
poetry run python scripts/migrate.py history
poetry run python scripts/migrate.py downgrade -1
```

Windows PowerShell:

```powershell
.\scripts\migrate.ps1
.\scripts\migrate.ps1 current
```
