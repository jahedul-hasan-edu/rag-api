"""EmbeddingProvider tests (no torch / sentence-transformers import required)."""

from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock

import numpy as np
import pytest

from app.rag.embedding.local_bge import LocalBGEEmbeddingProvider


@pytest.fixture(autouse=True)
def _reset_singleton() -> None:
    LocalBGEEmbeddingProvider.reset_instance()
    yield
    LocalBGEEmbeddingProvider.reset_instance()


def test_local_bge_embed_batches_and_normalizes() -> None:
    provider = LocalBGEEmbeddingProvider(
        model_name="fake-model",
        dimension=4,
        batch_size=2,
    )
    fake_model = MagicMock()
    fake_model.encode.return_value = np.array(
        [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]],
        dtype=np.float32,
    )
    # Pretend the model is already loaded — avoids importing torch.
    provider._model = fake_model

    vectors = provider.embed(["alpha", "beta"])

    assert provider.is_ready()
    assert provider.model_name == "fake-model"
    assert len(vectors) == 2
    assert len(vectors[0]) == 4
    fake_model.encode.assert_called_once()
    kwargs = fake_model.encode.call_args.kwargs
    assert kwargs["normalize_embeddings"] is True
    assert kwargs["batch_size"] == 2


def test_local_bge_load_uses_sentence_transformers() -> None:
    provider = LocalBGEEmbeddingProvider(model_name="fake-model", dimension=4)
    fake_model = MagicMock()
    fake_module = ModuleType("sentence_transformers")
    fake_module.SentenceTransformer = MagicMock(return_value=fake_model)  # type: ignore[attr-defined]

    sys.modules["sentence_transformers"] = fake_module
    try:
        provider.load()
        provider.load()  # idempotent
    finally:
        sys.modules.pop("sentence_transformers", None)

    assert provider.is_ready()
    fake_module.SentenceTransformer.assert_called_once_with("fake-model")


def test_local_bge_embed_empty_list() -> None:
    provider = LocalBGEEmbeddingProvider()
    assert provider.embed([]) == []


def test_singleton_reuses_instance() -> None:
    a = LocalBGEEmbeddingProvider.get_instance(model_name="m1")
    b = LocalBGEEmbeddingProvider.get_instance(model_name="ignored")
    assert a is b
