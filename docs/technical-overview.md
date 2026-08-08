# RAG API: Beginner Technical Overview

This document explains the main ideas behind the RAG API project in a way that is friendly for junior Python developers.

## 1. System Overview

The system has two main phases:

- **Ingestion**: Bring files into the system and prepare them for search.
- **Query**: Let users ask questions and return grounded answers.

Simple flowchart:

```
[Ingestion]            [Query]
  Upload                Ask question
     |                     |
     v                     v
  Extract text         Embed question
     |                     |
     v                     v
  Chunk documents     Find similar chunks
     |                     |
     v                     v
  Create vectors      Build prompt context
     |                     |
     v                     v
  Store vectors       Generate answer
```

## 2. User Flow

The user experience starts very simply:

- The user sees an empty chat or upload screen.
- They upload a file.
- The file is sent to the backend.
- The backend extracts text from the file.
- No AI answer is generated yet during upload.

This means the first step is about getting the content ready, not answering questions.

## 3. Ingestion Pipeline

Ingestion is the process that prepares documents so the system can search them later.

### Chunking: Why split documents

A document may be long, and language models have a limit on how much text they can use at once. That limit is called a context window.

So the system splits the document into smaller pieces called **chunks**. Each chunk is a manageable block of text.

Why this matters:

- A long document becomes easier to search.
- The system can compare smaller pieces to the question.
- It avoids pushing too much text into the model at once.

### Embedding: Convert chunks to vectors

Each chunk is turned into a number list called a **vector**. This happens with a pre-trained embedding model.

Key points:

- The model is already trained by someone else.
- We do not train it ourselves.
- It converts text into a math-friendly format.

This means a chunk like “Project goals and design” becomes a vector such as `[0.12, -0.05, 0.73, ...]`.

### Storage: Save vectors + text in a vector database

After chunking and embedding, the system stores:

- the chunk text,
- the vector for that chunk,
- metadata like file name or page number.

These are saved in a **vector database**. The database is built to search by vector similarity quickly.

## 4. Query Pipeline

When a user asks a question, the system follows these steps:

### User question → embed the same way

The question is converted into a vector using the same embedding model.

This makes the question and document chunks comparable in the same mathematical space.

### Semantic search: Find top-K similar chunks

The system searches the vector database for the chunks most similar to the question.

A simple way to think about similarity is this:

- Each vector is a point in space.
- The model measures how close two points are.
- The closer they are, the more likely the chunk is relevant.

This is often called **cosine similarity**. In plain language, it means:

- Compare the direction of the question vector and the chunk vector.
- If they point in a similar direction, the text is likely related.
- This helps pick the top K best chunks.

### Context assembly: Pack chunks into a prompt template

The top chunks are collected and placed into a prompt template.

That prompt is a structured instruction that tells the LLM:

- what the question is,
- which chunks are relevant,
- how to answer carefully using the text.

This step keeps the answer grounded in real document content.

### LLM generation

The system can generate answers in two main ways:

- **Local**: Load downloaded model weights and run the model on your own machine.
- **API**: Send the prompt to an external service, like OpenAI, and get the result back.

#### Local generation

If the project is configured for local use, the LLM is loaded from saved weights. The model runs locally and produces text directly.

#### API generation

If the project uses an external provider, it sends the assembled prompt over the network to an API endpoint. The API returns the generated answer.

### Citations: Append source metadata to response

The answer includes citations from the selected chunks.

This means the system tells the user where the answer came from, such as:

- file name,
- page number,
- chunk index.

Citations help users trust the response and find the original source text.

## 5. Key Clarification: Embedding model ≠ Generative LLM

These two models have different roles:

- An **embedding model** is used for search. It converts text into vectors. It is not directly writing answers.
- A **generative LLM** is used to write responses. It takes the selected text and question and produces human-readable output.

Think of it like this:

- Embeddings are the index in a library. They help find the right pages.
- The LLM is the writer that uses those pages to answer the question.

That separation is important because the system is not training a new model. It is using a ready-made embedding model for similarity and a ready-made LLM for answer generation.

## Final Notes

This project is a classic example of Retrieval-Augmented Generation (RAG). It combines file ingestion, semantic search, and LLM answering to make responses more accurate and grounded.

The main idea is:

- Prepare documents first,
- search for the best pieces of text,
- then use an LLM to generate a helpful answer.

That approach helps the system stay useful even when the user asks questions about long or complex documents.