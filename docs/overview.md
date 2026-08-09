# RAG System — Implementation Strategy

## 1. Overview

The goal is to build a Retrieval-Augmented Generation (RAG) system that allows users to:

1. Upload documents.
2. Extract and process their content.
3. Split documents into manageable chunks.
4. Generate embeddings for each chunk.
5. Store embeddings in a vector database.
6. Ask questions about uploaded documents.
7. Retrieve the most relevant chunks.
8. Build a prompt using the retrieved context.
9. Send the prompt to an LLM.
10. Return a human-readable, grounded answer.
11. Provide citations showing where the answer came from.

The overall architecture is:

```text
                    DOCUMENT INGESTION
                           │
                           ▼
                 Upload PDF / DOCX / MD / TXT
                           │
                           ▼
                     Validate File
                           │
                           ▼
                    SHA-256 Hash
                           │
                  Duplicate Detection
                           │
                           ▼
                    Text Extraction
                           │
                           ▼
                    Text Normalization
                           │
                           ▼
                       Chunking
                           │
                    500 tokens
                    100 overlap
                           │
                           ▼
                  Generate Embeddings
                           │
                           ▼
                    Vector Database
                           │
                           │
───────────────────────────┼────────────────────────────
                           │
                           │
                         QUERY
                           │
                           ▼
                    User Question
                           │
                           ▼
                  Generate Query Embedding
                           │
                           ▼
                   Semantic Search
                           │
                           ▼
                  Top-K Relevant Chunks
                           │
                           ▼
                    Prompt Building
                           │
                           ▼
                         LLM
                           │
                           ▼
                  Human-readable Answer
                           │
                           ▼
                       Citations
```

---

# 2. Ingestion Pipeline

The ingestion pipeline runs when a user uploads a document.

```text
File
 ↓
Validation
 ↓
Duplicate Detection
 ↓
Text Extraction
 ↓
Text Normalization
 ↓
Tokenization
 ↓
Chunking
 ↓
Embedding
 ↓
Vector Storage
```

---

## 2.1 Upload PDF, DOCX, Markdown, or TXT

The API accepts:

```text
.pdf
.docx
.md
.txt
```

Example:

```http
POST /api/v1/documents/upload
Content-Type: multipart/form-data
```

The API should validate:

* File extension
* MIME type
* File size
* Empty files
* Corrupted files
* Unsupported formats

Do not trust the file extension alone. Validate the actual file type where possible.

---

# 3. Duplicate Detection

Before processing the document, calculate a **SHA-256 hash** of the complete uploaded file.

Example:

```text
document.pdf
       │
       ▼
SHA-256
       │
       ▼
a8f42c...9d21
```

Store the hash in the `documents` table.

Example:

```text
documents

id
filename
file_hash
file_size
mime_type
created_at
```

Before processing a new upload:

```text
Calculate SHA-256
       │
       ▼
Search existing file_hash
       │
       ├── Exists → return existing document
       │
       └── Doesn't exist → continue processing
```

### Important

SHA-256 is being used for **file identity / duplicate detection**.

It is not an embedding and is not used for semantic search.

---

# 4. Text Extraction

After validation and duplicate detection, extract text from the document.

## PDF

Use:

```text
PyMuPDF
```

## DOCX

Use:

```text
python-docx
```

## Markdown

Read the file directly.

## TXT

Read the file directly.

The extraction layer should return structured information rather than just one giant string.

For example:

```python
ExtractedDocument(
    text="...",
    pages=[
        ExtractedPage(
            page_number=1,
            text="..."
        )
    ]
)
```

This is important because page information will later be used for citations.

---

# 5. Text Normalization

Before chunking, normalize the extracted text.

Examples:

```text
Multiple spaces
        ↓
Single spaces
```

Normalize:

* Line endings
* Excessive whitespace
* Empty lines
* Encoding issues

But do **not** aggressively remove formatting that carries meaning.

For example:

```text
Section: Vacation Policy
```

should remain distinguishable from:

```text
Employees receive 20 vacation days.
```

Headers can become valuable metadata later.

---

# 6. Tokenization

Chunking should be based on **tokens**, not characters.

A token is a piece of text processed by the tokenizer.

A token can represent:

* A whole word
* Part of a word
* Punctuation
* Special characters
* Other subword pieces

Therefore:

```text
500 tokens
```

does NOT mean:

```text
500 characters
```

and does NOT necessarily mean:

```text
500 words
```

The exact number depends on the tokenizer.

---

# 7. Use the Embedding Model's Tokenizer

Because this project uses:

```text
BAAI/bge-small-en-v1.5
```

use the tokenizer associated with that model for token counting.

Conceptually:

```text
BAAI/bge-small-en-v1.5
        │
        ├── Tokenizer
        │
        └── Embedding Model
```

The tokenizer should be loaded once during application startup.

Do NOT do this:

```python
for chunk in chunks:
    tokenizer = load_tokenizer()
```

Instead:

```text
Application Startup
        │
        ▼
Load Tokenizer Once
        │
        ▼
Reuse tokenizer
```

The same principle applies to the embedding model.

Load:

```text
Tokenizer
Embedding Model
```

once and reuse them.

---

# 8. Chunking

The purpose of chunking is to divide a large document into smaller pieces that can be effectively retrieved and provided to the LLM.

A document might contain:

```text
50,000 tokens
```

while the model's useful context capacity is much smaller.

Therefore:

```text
50,000-token document
          │
          ▼
       Chunking
          │
          ├── Chunk 1
          ├── Chunk 2
          ├── Chunk 3
          ├── ...
          └── Chunk N
```

Initial configuration:

```text
Chunk size: 500 tokens
Overlap: 100 tokens
```

---

# 9. Chunk Overlap

Chunks should overlap.

Example:

```text
Chunk 1
Token 1 → 500

Chunk 2
Token 401 → 900

Chunk 3
Token 801 → 1300
```

Therefore:

```text
Chunk 1
        └──────────────┐
                       │ 100-token overlap
                       ▼
                 Chunk 2
```

The overlap helps prevent important information from being lost at chunk boundaries.

For example, a sentence or explanation may cross the boundary between two chunks.

Without overlap:

```text
Chunk 1:
Employees can carry forward unused vacation days if

Chunk 2:
they receive manager approval.
```

The relationship may become harder to retrieve.

With overlap, the relevant context can appear in both chunks.

---

# 10. Preserve Document Structure

Do not blindly split every 500 tokens.

Prefer this hierarchy:

```text
Document
   │
   ├── Section
   │      │
   │      ├── Paragraph
   │      ├── Paragraph
   │      └── Paragraph
   │
   └── Section
```

The chunker should preferably:

1. Preserve sections.
2. Preserve paragraphs.
3. Preserve sentences.
4. Use token limits as the final constraint.

This is generally better than splitting at arbitrary token positions.

---

# 11. Chunk Metadata

Every chunk should contain useful metadata.

Example:

```json
{
    "chunk_id": "...",
    "document_id": "...",
    "filename": "Simple-Policy.md",
    "page_number": 1,
    "chunk_index": 0,
    "token_count": 487
}
```

Additional metadata can include:

```text
section
heading
author
document_type
department
created_at
tags
```

This metadata is extremely useful for:

* Citations
* Filtering
* Debugging
* Search
* Access control
* Evaluation

---

# 12. Generate Embeddings

Each chunk is converted into an embedding.

Using:

```text
BAAI/bge-small-en-v1.5
```

the output dimension is:

```text
384
```

Conceptually:

```text
Chunk Text
    │
    ▼
BGE Tokenizer
    │
    ▼
BGE Embedding Model
    │
    ▼
384-dimensional vector
```

Example:

```text
[
    0.023,
    -0.182,
    0.441,
    ...
]
```

The embedding represents the semantic meaning of the chunk.

---

# 13. Store Chunks and Embeddings

Store the chunk and its embedding in PostgreSQL with `pgvector`.

Example:

```text
documents
────────────────────────
id
filename
file_hash
file_size
mime_type
total_pages
total_chunks
created_at


document_chunks
────────────────────────
id
document_id
chunk_index
page_number
content
token_count
embedding
metadata
created_at
```

Relationship:

```text
Document
   │
   ├── Chunk 1
   ├── Chunk 2
   ├── Chunk 3
   └── Chunk N
```

Each chunk belongs to exactly one document.

---

# 14. Vector Index

Create a vector index using pgvector.

For example:

```text
HNSW
```

HNSW is a good starting choice for semantic search because it provides a strong speed/recall tradeoff.

The exact index configuration should be benchmarked rather than blindly optimized.

---

# 15. Query Pipeline

Once ingestion is complete, the system can answer questions.

```text
User Question
      │
      ▼
Generate Query Embedding
      │
      ▼
Semantic Search
      │
      ▼
Retrieve Relevant Chunks
      │
      ▼
Build Prompt
      │
      ▼
LLM
      │
      ▼
Answer
```

---

# 16. Convert Question to Embedding

Suppose the user asks:

```text
How many vacation days do employees receive?
```

Use the **same embedding model**:

```text
BAAI/bge-small-en-v1.5
```

Convert the question:

```text
Question
   │
   ▼
BGE Tokenizer
   │
   ▼
BGE Embedding Model
   │
   ▼
384-dimensional query vector
```

The document chunks and query must be embedded into the same vector space.

This is why the same embedding model should normally be used for both:

```text
Document → Embedding
Question → Embedding
```

---

# 17. Semantic Search

Use the query vector to search pgvector.

Conceptually:

```text
Question Vector
       │
       ▼
pgvector
       │
       ▼
Compare against chunk vectors
       │
       ▼
Rank by similarity
```

Example:

```text
Chunk 1 → 0.92
Chunk 7 → 0.88
Chunk 3 → 0.84
Chunk 9 → 0.81
Chunk 2 → 0.79
```

---

# 18. Top-K Retrieval

Initially use:

```text
K = 5
```

Retrieve the top five relevant chunks.

However, do not blindly assume that five chunks are always useful.

Eventually introduce:

```text
Similarity threshold
```

For example:

```text
Score >= threshold
```

This prevents clearly irrelevant chunks from being passed to the LLM.

The final retrieval strategy should eventually become:

```text
Semantic similarity
        +
Metadata filtering
        +
Similarity threshold
        +
Optional reranking
```

---

# 19. Metadata Filtering

Before or during retrieval, support filters such as:

```text
document_id
filename
department
document_type
year
tags
```

For example:

```text
Question:
"What is the vacation policy?"

Filter:
department = "HR"
```

This prevents unrelated documents from being retrieved.

---

# 20. Retrieved Context

The result of retrieval is not the embedding vector.

The LLM needs the actual text.

For example:

```text
Retrieved Chunk 1:

Employees receive 20 paid vacation days each year.


Retrieved Chunk 2:

Unused vacation days may be carried forward up to 10 days.
```

This actual text becomes the **context**.

The vector is only used to find the relevant text.

---

# 21. Prompt Construction

Build the final prompt from:

```text
System Instructions
+
Retrieved Context
+
User Question
```

Conceptually:

```text
SYSTEM

You are a helpful assistant.

Answer only using the provided context.

If the answer cannot be found in the provided context,
say:

"I couldn't find that information in the uploaded documents."

Do not invent information.

CONTEXT

[Retrieved Chunk 1]
Employees receive 20 paid vacation days each year.

[Retrieved Chunk 2]
Unused vacation days may be carried forward up to 10 days.

QUESTION

How many vacation days do employees receive?
```

---

# 22. Why the LLM Is Needed

The embedding model is responsible for:

```text
Finding relevant information
```

The LLM is responsible for:

```text
Understanding the question
+
Understanding retrieved context
+
Generating a human-readable response
```

Therefore:

```text
BGE
    ↓
Retrieval

LLM
    ↓
Generation
```

They have different responsibilities.

---

# 23. LLM Generation

The final prompt is sent to an LLM.

The LLM receives:

```text
System Instructions
+
Context
+
Question
```

and generates:

```text
Employees receive 20 paid vacation days each year.
```

The LLM does not need to receive the embedding vectors.

It receives the retrieved text.

---

# 24. Citations

The retrieved chunks already contain:

```text
chunk_id
document_id
filename
page_number
chunk_index
similarity_score
```

Therefore, the same retrieved chunks can be used to generate citations.

Example:

```text
Employees receive 20 paid vacation days each year.

Source:
Simple-Policy.md
Page 1
```

The citation should point back to the original chunk/document.

---

# 25. Streaming

For a better user experience, stream the LLM response.

Instead of:

```text
Wait 3 seconds
        ↓
Complete answer
```

stream:

```text
Employees
Employees receive
Employees receive 20
Employees receive 20 paid
...
```

Use Server-Sent Events (SSE) or another streaming mechanism.

A typical SSE sequence can be:

```text
event: citation
data: {...}

event: token
data: {"content":"Employees"}

event: token
data: {"content":" receive"}

event: token
data: {"content":" 20"}

event: done
data: {...}
```

---

# 26. Conversation History

Conversation history should be stored separately from document chunks.

Example:

```text
conversations
──────────────────
id
user_id
created_at


messages
──────────────────
id
conversation_id
role
content
created_at
```

For a follow-up:

```text
User:
What is the vacation policy?

Assistant:
Employees receive 20 vacation days.

User:
Can unused days be carried forward?
```

The previous conversation helps the LLM understand what "unused days" refers to.

However, conversation history should not replace document retrieval.

The system should still retrieve relevant document chunks for the new question.

---

# 27. Complete RAG Architecture

The final architecture should look like:

```text
                    ┌─────────────────────┐
                    │      DOCUMENT       │
                    │    PDF/DOCX/MD/TXT  │
                    └──────────┬──────────┘
                               │
                               ▼
                         File Validation
                               │
                               ▼
                           SHA-256
                               │
                         Duplicate Check
                               │
                               ▼
                       Text Extraction
                               │
                               ▼
                       Text Normalization
                               │
                               ▼
                     BGE Tokenizer
                     (loaded once)
                               │
                               ▼
                         Chunking
                    500 tokens / 100 overlap
                               │
                               ▼
                    BGE Embedding Model
                               │
                               ▼
                    384-dimensional vector
                               │
                               ▼
                    PostgreSQL + pgvector
                               │
                               │
═══════════════════════════════╪══════════════════════════════
                               │
                              QUERY
                               │
                               ▼
                         User Question
                               │
                               ▼
                    BGE Embedding Model
                               │
                               ▼
                       Query Vector
                               │
                               ▼
                      pgvector Search
                               │
                     ┌─────────┴─────────┐
                     │                   │
               Top-K Chunks       Metadata Filter
                     │                   │
                     └─────────┬─────────┘
                               │
                               ▼
                       Retrieved Context
                               │
                               ▼
                        Prompt Builder
                               │
                    ┌──────────┴──────────┐
                    │                     │
             System Instructions      Question
                    │                     │
                    └──────────┬──────────┘
                               │
                               ▼
                              LLM
                               │
                               ▼
                        Stream Response
                               │
                    ┌──────────┴──────────┐
                    │                     │
                 Answer               Citations
                    │                     │
                    └──────────┬──────────┘
                               ▼
                            User
```

---

# 28. What You Have Already Built

Your current RAG v1 should therefore contain:

### Ingestion

* [x] PDF upload
* [x] DOCX upload
* [x] Markdown upload
* [x] TXT upload
* [x] SHA-256 duplicate detection
* [x] Text extraction
* [x] Text normalization
* [x] Token-based chunking
* [x] Chunk overlap
* [x] BGE tokenizer
* [x] BGE embeddings
* [x] pgvector storage

### Query

* [x] Query embedding
* [x] Semantic search
* [x] Top-K retrieval
* [x] Prompt construction
* [x] LLM generation
* [x] Streaming
* [x] Citations
* [x] Conversation history

This is a solid **RAG v1**.

---

# 29. Future Improvements

Once the basic system is stable, do not immediately add random features.

Improve it systematically.

## Priority 1 — Retrieval Quality

Learn and implement:

```text
Hybrid Search
```

Combine:

```text
Vector Search
+
Keyword / Full-text Search
```

This helps with exact terms, IDs, names, policy numbers, etc.

---

## Priority 2 — Reranking

Current:

```text
Question
   ↓
Vector Search
   ↓
Top 5
```

Improved:

```text
Question
   ↓
Vector Search
   ↓
Top 20
   ↓
Reranker
   ↓
Top 5
   ↓
LLM
```

Learn cross-encoder reranking.

---

## Priority 3 — Better Chunking

Experiment with:

```text
Fixed-size chunking
Recursive chunking
Sentence-aware chunking
Semantic chunking
Header-aware chunking
Parent-child retrieval
```

Measure which strategy produces better retrieval.

---

## Priority 4 — Query Transformation

Learn:

```text
Query rewriting
Multi-query retrieval
HyDE
Query expansion
```

Example:

```text
User:
PTO?

        ↓

Expanded query:

What is the company's paid time off policy,
including annual allowance and carry-forward rules?
```

---

## Priority 5 — Evaluation

This is extremely important.

Create a dataset:

```text
Question
Expected Answer
Expected Source
```

Example:

| Question                         | Expected Answer    | Source |
| -------------------------------- | ------------------ | ------ |
| How many vacation days?          | 20 days            | Page 1 |
| Sick leave allowance?            | 10 days            | Page 2 |
| Can vacation be carried forward? | Yes, up to 10 days | Page 1 |

Measure:

```text
Retrieval accuracy
Context precision
Context recall
Answer correctness
Faithfulness
Latency
```

Do not change your RAG system without measuring whether the change actually improves it.

---

# 30. Performance Engineering

Measure each stage separately:

```text
File upload
Extraction
Chunking
Embedding
Database insertion
Query embedding
Vector search
Reranking
Prompt construction
LLM generation
Total latency
```

Track:

```text
Average
P50
P95
P99
Error rate
Throughput
```

This will teach you much more than simply measuring total API response time.

---

# 31. Production Improvements

After retrieval quality is good, learn:

```text
Background document processing
Caching
Rate limiting
Authentication
Authorization
Multi-tenancy
Document deletion
Document re-indexing
Document versioning
Observability
Metrics
Tracing
Retries
Circuit breakers
```

Especially important for a multi-user system:

```text
User A
   ↓
Only User A's documents

User B
   ↓
Only User B's documents
```

Never allow retrieval to cross tenant/user boundaries.

---

# 32. Advanced RAG Topics

After mastering the above:

```text
Parent-Child Retrieval
Contextual Retrieval
Context Compression
Hybrid Retrieval
Reranking
Multi-Query RAG
HyDE
Agentic RAG
Graph RAG
Self-RAG
Corrective RAG
Multimodal RAG
```

Do not learn all of these at once.

Build a strong conventional RAG first.

---

# 33. Recommended Learning Order

For your AI Engineering learning path:

```text
RAG v1
  │
  ▼
Understand Embeddings
  │
  ▼
Understand pgvector
  │
  ▼
Understand Chunking
  │
  ▼
Understand Retrieval
  │
  ▼
Hybrid Search
  │
  ▼
Reranking
  │
  ▼
RAG Evaluation
  │
  ▼
Query Transformation
  │
  ▼
Observability
  │
  ▼
Production RAG
  │
  ▼
Advanced RAG
  │
  ▼
Agents / Agentic RAG
```

The most important principle is:

> **Don't judge a RAG system only by whether the LLM produces a good-looking answer. Evaluate whether the right information was retrieved first.**

A beautiful answer based on the wrong context is still a bad RAG system.
