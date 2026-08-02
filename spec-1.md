# Role

You are a Senior Python Architect and AI Engineer.

We are building a production-ready RAG API using FastAPI.

Do NOT implement any RAG logic yet.

Your responsibility in this phase is ONLY to build the project foundation.

Everything should follow clean architecture, SOLID principles, dependency injection, async programming, and production-ready code.

---

# Objective

Build the project skeleton and infrastructure.

The application must be maintainable, testable, and scalable.

---

# Tech Stack

Python 3.13

Poetry (dependency management — do NOT use requirements.txt)

FastAPI

SQLAlchemy 2.0 Async

asyncpg

Alembic

Supabase PostgreSQL

pgvector

OpenAI SDK

Pydantic v2

uvicorn

python-dotenv

structlog

PyMuPDF

python-docx

tiktoken

---

# Dependency Management

Use Poetry exclusively.

- Declare runtime and dev dependencies in `pyproject.toml`
- Lock versions with `poetry.lock`
- Install with `poetry install`
- Run commands with `poetry run ...`

Do NOT create or maintain `requirements.txt`.

---

# Project Structure

Create a clean folder structure.

app/
    api/
        v1/
            upload.py
            search.py
            health.py

    core/
        config.py
        logging.py
        dependencies.py

    db/
        database.py
        session.py
        models.py
        migrations/

    rag/
        chunking/
        embedding/
        extraction/
        retrieval/
        prompts/

    services/

    repositories/

    schemas/

    utils/

tests/

main.py

pyproject.toml

poetry.lock

.env.example

README.md

---

# Configuration

Use BaseSettings.

Read every secret from .env.

Never hardcode credentials.

Support

DATABASE_URL

OPENAI_API_KEY

LOG_LEVEL

ENVIRONMENT

---

# Logging

Configure structured logging.

Every request should include

request id

execution time

path

status

---

# Database

Configure Async SQLAlchemy.

Use dependency injection.

Configure session lifecycle.

Health check endpoint should verify database connectivity.

---

# pgvector

Install pgvector.

Create migration enabling

CREATE EXTENSION IF NOT EXISTS vector;

Create a reusable Vector type.

---

# Models

Create an initial DocumentChunk model.

Fields

id

document_id

filename

page_number

chunk_index

content

embedding

metadata

created_at

No upload implementation yet.

---

# Repository Pattern

Create repository interfaces.

Create implementations.

Keep business logic outside repositories.

---

# API

Implement only

GET /health

Return

database connectivity

application version

environment

---

# Error Handling

Create global exception handlers.

Return standardized JSON errors.

---

# Validation

Use Pydantic v2.

Strict typing.

---

# Documentation

Swagger should be clean.

Every endpoint must have descriptions.

---

# Testing

Configure pytest.

Create one health endpoint test.

---

# Deliverables

Generate code one module at a time.

Explain each module briefly before generating the next.

Do NOT implement file upload.

Do NOT implement extraction.

Do NOT implement embeddings.

Do NOT implement RAG.