# RAG API

Production-oriented FastAPI foundation for a Retrieval-Augmented Generation service.

This phase ships **infrastructure only**: configuration, logging, async database access, pgvector-ready models, repository ports, health checks, and tests. Upload, extraction, embeddings, and retrieval are intentionally not implemented yet.

## Stack

| Layer | Technology |
| --- | --- |
| Runtime | Python 3.13 (compatible with 3.10+) |
| Package manager | Poetry |
| API | FastAPI + uvicorn |
| Config | Pydantic Settings v2 + python-dotenv |
| DB | SQLAlchemy 2.0 async + asyncpg |
| Migrations | Alembic |
| Vectors | pgvector (Supabase PostgreSQL) |
| Logging | structlog |
| Tests | pytest + pytest-asyncio + httpx |

## Project layout

```
rag-api/
├── app/
│   ├── api/v1/          # HTTP routers (health only for now)
│   ├── core/            # config, logging, DI, middleware, errors
│   ├── db/              # engine, models, Alembic migrations
│   ├── rag/             # placeholders for later phases
│   ├── repositories/    # ports + SQLAlchemy adapters
│   ├── schemas/         # Pydantic v2 response models
│   ├── services/        # use cases (later)
│   └── utils/
├── tests/
├── main.py
├── alembic.ini
├── pyproject.toml
├── poetry.lock
├── requirements.txt   # pip mirror of pyproject deps
└── .env.example
```

## Prerequisites

- Python 3.10+ (3.13 recommended)
- [Poetry](https://python-poetry.org/docs/#installation) 2.x

```bash
# Verify Poetry
poetry --version
```

## Setup

```bash
cd rag-api

# Create the virtualenv and install runtime + dev dependencies
poetry install

# Copy environment template and edit secrets
cp .env.example .env
# Set DATABASE_URL and OPENAI_API_KEY in .env
```

Poetry creates and manages a project virtualenv automatically. To activate it in your shell:

```bash
# Windows (PowerShell)
poetry env activate

# Or run any command inside the env without activating
poetry run <command>
```

### Useful Poetry commands

| Command | Purpose |
| --- | --- |
| `poetry install` | Install deps from `poetry.lock` |
| `poetry add <pkg>` | Add a runtime dependency |
| `poetry add --group dev <pkg>` | Add a dev/test dependency |
| `poetry update` | Update deps within version constraints |
| `poetry show --tree` | Inspect the dependency tree |
| `poetry run pytest` | Run tests in the Poetry env |
| `poetry run uvicorn main:app --reload` | Start the API |

### Database URL

Use the async driver prefix:

```text
postgresql+asyncpg://postgres:PASSWORD@db.PROJECT.supabase.co:5432/postgres
```

### Migrations

Enables `vector` and creates `document_chunks`:

```bash
poetry run alembic upgrade head
```

## Run

```bash
poetry run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- Swagger UI: http://localhost:8000/docs
- Health: http://localhost:8000/health

Example health response:

```json
{
  "status": "ok",
  "version": "0.1.0",
  "environment": "development",
  "database": "connected"
}
```

When the database is unreachable, `status` is `degraded` and `database` is `disconnected`.

## Tests

```bash
poetry run pytest
```

## Architecture notes

- **Clean architecture**: routers → services (later) → repository interfaces → SQLAlchemy adapters.
- **Dependency injection**: `app/core/dependencies.py` wires Settings, sessions, and repositories.
- **Async by default**: engine, sessions, and HTTP handlers are async.
- **Structured logging**: every request logs `request_id`, `path`, `status`, and `execution_time_ms`.
- **Errors**: global handlers return a consistent `{error, message, details}` JSON body.

## Next phases (not in this PR)

1. Document upload API
2. PDF / DOCX extraction
3. Chunking + OpenAI embeddings
4. Vector similarity search / RAG answers
