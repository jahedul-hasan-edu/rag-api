"""
Local BGE embedding provider (sentence-transformers).

Loaded once per process and reused. Never instantiate the model per request.
"""

from __future__ import annotations

import threading
import time
from typing import Sequence

from app.core.logging import get_logger
from app.rag.embedding.base import EmbeddingProvider

logger = get_logger(__name__)

DEFAULT_MODEL_NAME = "BAAI/bge-small-en-v1.5"
DEFAULT_DIMENSION = 384


class LocalBGEEmbeddingProvider(EmbeddingProvider):
    """
    Process-wide singleton wrapping BAAI/bge-small-en-v1.5.

    Thread-safe lazy/explicit load; generate normalized embeddings in batches.
    """

    _instance: LocalBGEEmbeddingProvider | None = None
    _instance_lock = threading.Lock()

    def __init__(
        self,
        *,
        model_name: str = DEFAULT_MODEL_NAME,
        dimension: int = DEFAULT_DIMENSION,
        batch_size: int = 32,
    ) -> None:
        self._model_name = model_name
        self._dimension = dimension
        self._batch_size = batch_size
        self._model = None
        self._load_lock = threading.Lock()

    @classmethod
    def get_instance(
        cls,
        *,
        model_name: str = DEFAULT_MODEL_NAME,
        dimension: int = DEFAULT_DIMENSION,
        batch_size: int = 32,
    ) -> LocalBGEEmbeddingProvider:
        """Return the process-wide singleton instance."""
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls(
                        model_name=model_name,
                        dimension=dimension,
                        batch_size=batch_size,
                    )
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Clear the singleton (intended for tests)."""
        with cls._instance_lock:
            cls._instance = None

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    def is_ready(self) -> bool:
        return self._model is not None

    def load(self) -> None:
        """Load the sentence-transformers model once (idempotent)."""
        if self._model is not None:
            return
        with self._load_lock:
            if self._model is not None:
                return
            started = time.perf_counter()
            # Import lazily so unit tests that mock the provider need no torch.
            from sentence_transformers import SentenceTransformer

            logger.info("embedding_model_load_started", model=self._model_name)
            self._model = SentenceTransformer(self._model_name)
            elapsed_ms = (time.perf_counter() - started) * 1000
            logger.info(
                "embedding_model_load_completed",
                model=self._model_name,
                latency_ms=round(elapsed_ms, 2),
            )

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed *texts* as L2-normalized float vectors."""
        if not texts:
            return []
        self.load()
        assert self._model is not None

        started = time.perf_counter()
        vectors = self._model.encode(
            texts,
            batch_size=self._batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        elapsed_ms = (time.perf_counter() - started) * 1000
        logger.info(
            "embedding_completed",
            model=self._model_name,
            batch_size=len(texts),
            latency_ms=round(elapsed_ms, 2),
        )
        return [self._to_float_list(row) for row in vectors]

    @staticmethod
    def _to_float_list(row: Sequence[float]) -> list[float]:
        return [float(value) for value in row]
