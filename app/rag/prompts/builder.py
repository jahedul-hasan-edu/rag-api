"""
Grounded RAG prompt construction.

Reusable across search and chat; never embeds model-specific APIs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from app.rag.retrieval.base import RetrievedChunk

NOT_FOUND_MESSAGE = (
    "I couldn't find that information in the uploaded documents."
)

SYSTEM_PROMPT = (
    "You are a helpful assistant.\n\n"
    "Answer ONLY using the provided context.\n\n"
    "If the answer cannot be found,\n"
    "respond exactly\n\n"
    f'"{NOT_FOUND_MESSAGE}"'
)


@dataclass(frozen=True, slots=True)
class ChatTurn:
    """A prior conversation turn for multi-turn prompts."""

    role: str
    content: str


class PromptBuilder:
    """Build OpenAI-style chat messages from retrieved context + history."""

    def __init__(self, *, system_prompt: str = SYSTEM_PROMPT) -> None:
        self._system_prompt = system_prompt

    def build(
        self,
        *,
        question: str,
        chunks: Sequence[RetrievedChunk],
        history: Sequence[ChatTurn] | None = None,
    ) -> list[dict[str, str]]:
        """
        Return messages: system + optional history + user (context + question).
        """
        messages: list[dict[str, str]] = [
            {"role": "system", "content": self._system_prompt},
        ]

        if history:
            for turn in history:
                if turn.role in {"user", "assistant", "system"} and turn.content:
                    messages.append({"role": turn.role, "content": turn.content})

        context_block = self._format_context(chunks)
        user_content = (
            f"Context\n\n{context_block}\n\nQuestion\n\n{question.strip()}"
        )
        messages.append({"role": "user", "content": user_content})
        return messages

    @staticmethod
    def _format_context(chunks: Sequence[RetrievedChunk]) -> str:
        if not chunks:
            return "(No relevant context was retrieved.)"

        parts: list[str] = []
        for i, chunk in enumerate(chunks, start=1):
            page = chunk.page_number if chunk.page_number is not None else "?"
            header = (
                f"[{i}] source={chunk.filename} "
                f"page={page} chunk={chunk.chunk_index} "
                f"score={chunk.similarity_score:.4f}"
            )
            parts.append(f"{header}\n{chunk.content}")
        return "\n\n".join(parts)
