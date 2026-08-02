# RAG API

Production-oriented FastAPI service for Retrieval-Augmented Generation.

**Phase 3** adds the **retrieval + grounded answering pipeline**: pgvector semantic search, PromptBuilder, OpenAI streaming answers with citations, SSE, and conversation history.

## Stack

| Layer | Technology |
| --- | --- |
| Runtime | Python 3.13 (compatible with 3.10+) |
| Package manager | Poetry |
| API | FastAPI + uvicorn (SSE streaming) |
| Config | Pydantic Settings v2 + python-dotenv |
| DB | SQLAlchemy 2.0 async + asyncpg |
| Migrations | Alembic |
| Vectors | pgvector cosine similarity (Top-K=5) |
| Embeddings | `sentence-transformers` (`BAAI/bge-small-en-v1.5`) |
| LLM | OpenAI Chat Completions (stream) |
| Extraction | PyMuPDF, python-docx |
| Chunking | tiktoken (500 tokens / 100 overlap) |
| Logging | structlog |
| Tests | pytest + pytest-asyncio + httpx |

## Project layout

```
rag-api/
├── app/
│   ├── api/v1/          # upload, search (SSE), chat
│   ├── core/            # config, logging, DI, middleware, errors
│   ├── db/              # engine, models, Alembic migrations
│   ├── rag/
│   │   ├── extraction/
│   │   ├── chunking/
│   │   ├── embedding/
│   │   ├── retrieval/   # Retriever port + PgVectorRetriever
│   │   ├── prompts/     # PromptBuilder
│   │   └── llm/         # LLMProvider + OpenAI
│   ├── repositories/
│   ├── schemas/
│   ├── services/        # Upload / Search / Chat
│   └── utils/
├── tests/
├── main.py
└── pyproject.toml
```

## Prerequisites

- Python 3.10+ (3.13 recommended)
- [Poetry](https://python-poetry.org/docs/#installation) 2.x
- PostgreSQL with the `vector` extension (e.g. Supabase)
- OpenAI API key
- **Windows:** [Microsoft Visual C++ 2015–2022 Redistributable (x64)](https://aka.ms/vs/17/release/vc_redist.x64.exe) — required by PyMuPDF

## Setup

```bash
cd rag-api
poetry install
cp .env.example .env
# Set DATABASE_URL and OPENAI_API_KEY
poetry run alembic upgrade head
```

## Run

```bash
poetry run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- Docs: http://localhost:8000/docs
- Health: `GET /health`
- Upload: `POST /api/v1/upload`
- Search (SSE): `POST /api/v1/search`
- Chat (SSE): `POST /api/v1/chat`
- History: `GET /api/v1/chat/{conversation_id}`

### Search example (SSE)

```bash
curl -N -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"question":"What is the refund policy?","document_id":null}'
```

SSE events:

| Event | Purpose |
| --- | --- |
| `citation` | filename, page_number, chunk_index, similarity_score, ids |
| `token` | streamed answer fragment |
| `done` | full answer + citations + timings |
| `error` | failure payload |

### Chat example

```bash
# Start a conversation
curl -N -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"Summarize the handbook introduction."}'

# Continue (include conversation_id from the `conversation` / `done` event)
curl -N -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"What about chapter 2?","conversation_id":"<uuid>"}'

curl http://localhost:8000/api/v1/chat/<uuid>
```

Optional filters on search/chat: `document_id`, `filename` (ILIKE), `tags`, `page_number`.

## Tests

```bash
poetry run pytest
```

LLM / retrieval HTTP tests mock services; PromptBuilder and pipeline tests are pure unit tests.

## Architecture notes

- **Retriever port**: `PgVectorRetriever` today; hybrid search / reranking can plug in without changing Search/Chat services.
- **LLM port**: `OpenAILLMProvider` behind `LLMProvider` for Azure/local swaps later.
- **Grounding**: PromptBuilder forces context-only answers; empty retrieval returns the exact not-found sentence without calling the LLM.
- **Citations**: emitted as SSE `citation` events (and again on `done`) for clickable UI rendering.
- **History**: recent messages (configurable `CONVERSATION_HISTORY_LIMIT`) are injected into chat prompts.
- **Disconnect**: SSE generators stop when `request.is_disconnected()` is true.

## Config knobs

| Env | Default | Meaning |
| --- | --- | --- |
| `RETRIEVAL_TOP_K` | 5 | Chunks retrieved per query |
| `OPENAI_MODEL` | `gpt-4o-mini` | Chat model |
| `LLM_TEMPERATURE` | 0 | Prefer deterministic grounded answers |
| `CONVERSATION_HISTORY_LIMIT` | 10 | Recent messages kept in prompts |
