# Role

Continue from the existing project.

Do not rewrite previously completed modules.

Only implement the retrieval pipeline.

---

# Objective

Users can ask questions about uploaded documents.

The system retrieves relevant chunks using vector similarity and generates answers using an LLM.

---

# Search API

POST /api/v1/search

Input

{
  "question": "...",
  "document_id": "optional"
}

---

# Embedding Query

Convert the question into an embedding.

Reuse the existing embedding service.

---

# Semantic Search

Use pgvector cosine similarity.

Return Top 5 chunks.

Support optional metadata filtering

document id

filename

tags

page number

---

# Retrieval

Return

content

similarity score

metadata

page

filename

---

# Prompt Construction

Implement a reusable PromptBuilder.

Prompt template

System

You are a helpful assistant.

Answer ONLY using the provided context.

If the answer cannot be found,

respond exactly

"I couldn't find that information in the uploaded documents."

User

Context

{retrieved_chunks}

Question

{question}

---

# LLM

Use OpenAI Responses API or Chat Completions API.

Return only grounded answers.

Never hallucinate.

---

# Streaming

Implement Server-Sent Events (SSE).

The endpoint should stream generated tokens.

Support graceful client disconnect.

---

# Citations

Every answer must include citations.

Each citation should include

filename

page number

chunk index

similarity score

The frontend should be able to render clickable citations.

---

# Conversation History

Create conversation tables.

Conversation

Message

Store

user message

assistant message

retrieved chunk ids

timestamp

Implement

POST /chat

GET /chat/{conversation_id}

Automatically include recent conversation history in subsequent prompts while respecting a configurable context limit.

---

# Logging

Log

query embedding latency

vector search latency

LLM latency

total response time

retrieved chunk count

---

# Testing

Create tests for

semantic retrieval

prompt builder

search endpoint

streaming endpoint

conversation APIs

---

# Performance

Design retrieval so that

future hybrid search

reranking

multiple embedding models

can be added without major refactoring.

---

# Deliverables

Generate one module at a time.

Explain important architectural decisions.

Do not rewrite previously completed code unless necessary.

Keep the implementation production-ready and extensible.