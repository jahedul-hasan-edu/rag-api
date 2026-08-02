"""PromptBuilder unit tests."""

from __future__ import annotations

import uuid

from app.rag.prompts import NOT_FOUND_MESSAGE, SYSTEM_PROMPT, ChatTurn, PromptBuilder
from app.rag.retrieval import RetrievedChunk


def _chunk(content: str = "Alpha context", *, score: float = 0.9) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        content=content,
        similarity_score=score,
        page_number=2,
        chunk_index=0,
        filename="doc.pdf",
        metadata={},
    )


def test_prompt_builder_includes_system_context_and_question() -> None:
    builder = PromptBuilder()
    messages = builder.build(question="What is alpha?", chunks=[_chunk()])

    assert messages[0]["role"] == "system"
    assert NOT_FOUND_MESSAGE in messages[0]["content"]
    assert SYSTEM_PROMPT.splitlines()[0] in messages[0]["content"]
    assert messages[-1]["role"] == "user"
    assert "Alpha context" in messages[-1]["content"]
    assert "What is alpha?" in messages[-1]["content"]
    assert "doc.pdf" in messages[-1]["content"]


def test_prompt_builder_inserts_history_before_user() -> None:
    builder = PromptBuilder()
    messages = builder.build(
        question="Follow up?",
        chunks=[_chunk()],
        history=[
            ChatTurn(role="user", content="Earlier question"),
            ChatTurn(role="assistant", content="Earlier answer"),
        ],
    )
    roles = [m["role"] for m in messages]
    assert roles == ["system", "user", "assistant", "user"]
    assert messages[1]["content"] == "Earlier question"


def test_prompt_builder_handles_empty_chunks() -> None:
    builder = PromptBuilder()
    messages = builder.build(question="Missing?", chunks=[])
    assert "No relevant context" in messages[-1]["content"]
