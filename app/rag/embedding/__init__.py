"""Embedding providers package."""

from app.rag.embedding.base import EmbeddingProvider
from app.rag.embedding.local_bge import (
    DEFAULT_DIMENSION,
    DEFAULT_MODEL_NAME,
    LocalBGEEmbeddingProvider,
)

__all__ = [
    "DEFAULT_DIMENSION",
    "DEFAULT_MODEL_NAME",
    "EmbeddingProvider",
    "LocalBGEEmbeddingProvider",
]
