"""
Embedding provider port.

Business logic depends on this ABC so cloud providers (OpenAI, Gemini, etc.)
can replace the local model without changing services.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """Port for text embedding backends."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Canonical model identifier stored with documents."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Embedding vector dimensionality."""

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """
        Embed *texts* and return one L2-normalized vector per input.

        Implementations should support batching internally.
        """

    @abstractmethod
    def is_ready(self) -> bool:
        """Return True when the backend is loaded and ready to embed."""

    @abstractmethod
    def load(self) -> None:
        """Load model weights / establish client connections (idempotent)."""
