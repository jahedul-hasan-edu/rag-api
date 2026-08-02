"""LLM provider port for grounded answer generation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Sequence


class LLMProvider(ABC):
    """Port for chat/completion backends (OpenAI, Azure, local, etc.)."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Canonical model identifier."""

    @abstractmethod
    def stream_chat(
        self,
        messages: Sequence[dict[str, str]],
    ) -> AsyncIterator[str]:
        """
        Stream assistant token deltas for *messages*.

        Implementations must yield text fragments only (no role metadata).
        """

    @abstractmethod
    async def complete_chat(
        self,
        messages: Sequence[dict[str, str]],
    ) -> str:
        """Return a full assistant completion for *messages*."""
