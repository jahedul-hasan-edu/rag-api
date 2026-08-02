# Role

Continue from Phase 1.

Do NOT rewrite previously implemented modules unless absolutely necessary.

Your responsibility in this phase is to implement the complete document ingestion pipeline.

Do NOT implement search, prompt construction, LLM integration, streaming, citations, or conversation history.

Everything should follow the existing Clean Architecture.

------------------------------------------------------------
OBJECTIVE
------------------------------------------------------------

Users should be able to upload documents.

The system must

1. Validate files
2. Extract text
3. Normalize text
4. Chunk documents
5. Generate embeddings
6. Store vectors inside PostgreSQL (pgvector)

The implementation must be provider-independent so that another embedding provider (OpenAI, Gemini, Azure OpenAI, etc.) can later replace the local embedding model without changing business logic.

------------------------------------------------------------
SUPPORTED DOCUMENT TYPES
------------------------------------------------------------

PDF

DOCX

Markdown

TXT

------------------------------------------------------------
UPLOAD API
------------------------------------------------------------

POST /api/v1/upload

Content-Type

multipart/form-data

Validation

Supported extensions

Maximum file size

Empty file

Corrupted file

Return

document_id

filename

total_pages

total_chunks

embedding_model

processing_time

status

------------------------------------------------------------
DATABASE
------------------------------------------------------------

Create two logical entities.

Document

id

filename

file_size

mime_type

sha256_hash

total_pages

total_chunks

embedding_model

metadata JSONB

created_at

DocumentChunk

id

document_id

page_number

chunk_index

content

token_count

embedding VECTOR(384)

metadata JSONB

created_at

Create the proper foreign key relationship.

Create indexes for

document_id

chunk_index

pgvector cosine similarity

------------------------------------------------------------
DOCUMENT DUPLICATION
------------------------------------------------------------

Before processing,

calculate the SHA-256 hash of the uploaded file.

If the exact document already exists,

return the existing document information instead of processing again.

------------------------------------------------------------
TEXT EXTRACTION
------------------------------------------------------------

Create an abstract extractor interface.

DocumentExtractor

extract(file) -> ExtractedDocument

Implement

PdfExtractor

DocxExtractor

MarkdownExtractor

TextExtractor

Use

PyMuPDF

python-docx

built-in file reader

Each extractor should return

text

page information

metadata

Normalize text

Remove excessive whitespace

Normalize line endings

Preserve paragraph boundaries

Never generate embeddings inside extractors.

------------------------------------------------------------
CHUNKING
------------------------------------------------------------

Create a reusable ChunkingService.

Requirements

Chunk size

500 tokens

Overlap

100 tokens

Preserve paragraphs whenever possible.

Avoid splitting sentences unnecessarily.

Use

tiktoken

for token counting.

Each chunk should contain

content

page_number

chunk_index

token_count

Chunking should be completely independent from extraction and embedding.

------------------------------------------------------------
EMBEDDING ARCHITECTURE
------------------------------------------------------------

Do NOT call any cloud API.

Use

sentence-transformers

Create an abstraction.

EmbeddingProvider

embed(texts: list[str]) -> list[list[float]]

Implement

LocalBGEEmbeddingProvider

Use

BAAI/bge-small-en-v1.5

Generate normalized embeddings.

Support batch embedding generation.

Never instantiate the model per request.

Load the model once during application startup.

Reuse the singleton instance.

Log embedding latency.

------------------------------------------------------------
VECTOR STORAGE
------------------------------------------------------------

Persist

Document

DocumentChunk

Store

chunk text

embedding vector

page number

chunk index

token count

metadata

embedding model name

Use repository classes.

Business logic must remain inside services.

------------------------------------------------------------
TRANSACTIONS
------------------------------------------------------------

If any step fails

Extraction

Chunking

Embedding

Database insert

Rollback the entire transaction.

Never leave partial data.

------------------------------------------------------------
BACKGROUND PROCESSING
------------------------------------------------------------

Design the upload pipeline so that it can later be moved into

Celery

RQ

Dramatiq

FastAPI BackgroundTasks

without changing business logic.

Keep orchestration inside UploadService.

------------------------------------------------------------
LOGGING
------------------------------------------------------------

Log

upload started

validation completed

duplicate detection

text extraction completed

chunking completed

embedding completed

database insert completed

processing time

errors

------------------------------------------------------------
ERROR HANDLING
------------------------------------------------------------

Return proper HTTP status codes.

400

Unsupported file

413

File too large

409

Duplicate document (optional)

422

Validation failure

500

Unexpected processing error

------------------------------------------------------------
TESTING
------------------------------------------------------------

Create tests for

PDF extraction

DOCX extraction

Markdown extraction

TXT extraction

ChunkingService

EmbeddingProvider

UploadService

Upload endpoint

Mock embedding generation where appropriate.

------------------------------------------------------------
DOCUMENTATION
------------------------------------------------------------

Swagger documentation should include

supported file types

maximum upload size

response examples

error examples

------------------------------------------------------------
DELIVERABLES
------------------------------------------------------------

Generate code module-by-module.

Explain every architectural decision before generating code.

Do NOT continue to the next module until the current module is complete.

Keep everything production-ready.

Follow Clean Architecture, SOLID principles, dependency injection, async programming, and repository pattern.