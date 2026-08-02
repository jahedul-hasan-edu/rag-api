# RAG API

Production-oriented FastAPI service for Retrieval-Augmented Generation.

**Phase 2** ships the complete **document ingestion pipeline**: upload validation, text extraction, chunking, local BGE embeddings, and pgvector persistence. Search / LLM answering arrive in a later phase.

## Stack

| Layer | Technology |
| --- | --- |
| Runtime | Python 3.13 (compatible with 3.10+) |
| Package manager | Poetry |
| API | FastAPI + uvicorn |
| Config | Pydantic Settings v2 + python-dotenv |
| DB | SQLAlchemy 2.0 async + asyncpg |
| Migrations | Alembic |
| Vectors | pgvector (Supabase PostgreSQL), 384-d |
| Embeddings | `sentence-transformers` (`BAAI/bge-small-en-v1.5`) |
| Extraction | PyMuPDF, python-docx |
| Chunking | tiktoken (500 tokens / 100 overlap) |
| Logging | structlog |
| Tests | pytest + pytest-asyncio + httpx |

## Project layout

```
rag-api/
├── app/
│   ├── api/v1/          # health + upload (+ search stub)
│   ├── core/            # config, logging, DI, middleware, errors
│   ├── db/              # engine, models, Alembic migrations
│   ├── rag/
│   │   ├── extraction/  # PDF / DOCX / MD / TXT extractors
│   │   ├── chunking/    # token-aware ChunkingService
│   │   ├── embedding/   # EmbeddingProvider + local BGE
│   │   ├── retrieval/   # later
│   │   └── prompts/     # later
│   ├── repositories/    # Document + DocumentChunk ports/adapters
│   ├── schemas/         # Pydantic v2 response models
│   ├── services/        # UploadService orchestration
│   └── utils/
├── tests/
├── main.py
├── alembic.ini
├── pyproject.toml
├── poetry.lock
└── .env.example
```

## Prerequisites

- Python 3.10+ (3.13 recommended)
- [Poetry](https://python-poetry.org/docs/#installation) 2.x
- PostgreSQL with the `vector` extension (e.g. Supabase)
- **Windows:** [Microsoft Visual C++ 2015–2022 Redistributable (x64)](https://aka.ms/vs/17/release/vc_redist.x64.exe) — required by PyMuPDF (`MSVCP140.dll`)

```bash
poetry --version
```

## Setup

```bash
cd rag-api
poetry install
cp .env.example .env
# Set DATABASE_URL and OPENAI_API_KEY in .env
```

First startup downloads `BAAI/bge-small-en-v1.5` (cached by Hugging Face). For tests / CI that mock embeddings, set:

```env
LOAD_EMBEDDING_MODEL_ON_STARTUP=false
```

### Migrations

```bash
poetry run alembic upgrade head
```

Creates `documents`, reshapes `document_chunks` (FK + `token_count` + 384-d vectors), and adds a cosine HNSW index.

## Run

```bash
poetry run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- Swagger UI: http://localhost:8000/docs
- Health: http://localhost:8000/health
- Upload: `POST /api/v1/upload`

### Upload example

```bash
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@./handbook.pdf"
```

Response:

```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "handbook.pdf",
  "total_pages": 12,
  "total_chunks": 48,
  "embedding_model": "BAAI/bge-small-en-v1.5",
  "processing_time": 1.8421,
  "status": "completed"
}
```

Identical content (SHA-256 match) returns the existing document with `"status": "duplicate"`.

### Supported types

| Extension | MIME |
| --- | --- |
| `.pdf` | `application/pdf` |
| `.docx` | Word OpenXML |
| `.md` | `text/markdown` |
| `.txt` | `text/plain` |

Default max size: **10 MiB** (`MAX_UPLOAD_SIZE_BYTES`).

## Tests

```bash
poetry run pytest
```

Embedding tests mock `sentence-transformers`; upload HTTP tests mock `UploadService`.

## Architecture notes

- **Clean architecture**: routers → `UploadService` → repository interfaces → SQLAlchemy adapters.
- **Provider-independent embeddings**: services depend on `EmbeddingProvider`; swap local BGE for OpenAI/Gemini later without changing business logic.
- **Background-ready orchestration**: all pipeline steps live in `UploadService.process()` (no FastAPI imports), so Celery/RQ/Dramatiq can call the same method later.
- **Transactions**: request-scoped `AsyncSession` commits on success and rolls back on any failure — no partial documents/chunks.
- **Structured logging**: upload started → validation → duplicate detection → extraction → chunking → embedding → DB insert → processing time.

## Next phases (not in this PR)

1. Vector similarity search
2. Prompt construction + LLM answers
3. Streaming + citations
4. Conversation history
