"""Embedding providers: turn text into vectors whose distance reflects meaning.

The rest of the app depends only on `EmbeddingProvider`, so the model can be swapped
(another local model, or a paid API) without touching the pipeline or search code.
"""

import hashlib
import logging
import threading
from functools import lru_cache
from typing import Protocol

import numpy as np

from app.core.config import EMBEDDING_DIM, get_settings
from app.services.text_normalization import normalize_for_search

logger = logging.getLogger(__name__)


class EmbeddingError(Exception):
    """The embedding model failed. Usually transient (e.g. model download interrupted)."""


class EmbeddingProvider(Protocol):
    model_name: str
    dim: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


def _unit(vector: np.ndarray) -> list[float]:
    norm = float(np.linalg.norm(vector))
    return (vector / norm).tolist() if norm else vector.tolist()


class LocalEmbeddingProvider:
    """A multilingual sentence-embedding model run on the CPU with ONNX (via fastembed).

    Free and private: documents never leave the machine. The model (~220 MB) is downloaded
    on first use and cached.
    """

    def __init__(self, model_name: str, batch_size: int) -> None:
        self.model_name = model_name
        self.dim = EMBEDDING_DIM
        self._batch_size = batch_size
        self._model = None
        self._lock = threading.Lock()  # the API thread and the worker may load it concurrently

    def _load(self):
        with self._lock:
            if self._model is None:
                from fastembed import TextEmbedding  # imported lazily: slow, and unused in tests

                self._model = TextEmbedding(self.model_name)
        return self._model

    def _warn_if_truncated(self, texts: list[str]) -> None:
        """The model ignores tokens past its limit. Say so loudly instead of failing silently."""
        try:
            tokenizer = self._load().model.tokenizer  # fastembed internals: best effort only
            limit = tokenizer.truncation["max_length"]
            cut = sum(1 for e in tokenizer.encode_batch(texts) if e.overflowing)
        except Exception:
            return
        if cut:
            logger.warning(
                "%d of %d texts exceed the model's %d-token limit and were truncated; "
                "lower CHUNK_SIZE",
                cut,
                len(texts),
                limit,
            )

    def _embed(self, texts: list[str]) -> list[list[float]]:
        self._warn_if_truncated(texts)
        try:
            vectors = list(self._load().embed(texts, batch_size=self._batch_size))
        except Exception as exc:
            raise EmbeddingError(str(exc)) from exc
        for vector in vectors:
            if len(vector) != self.dim:
                raise EmbeddingError(
                    f"Model returned {len(vector)} dimensions, expected {self.dim}"
                )
        return [_unit(np.asarray(v, dtype=np.float32)) for v in vectors]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts) if texts else []

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text])[0]


class FakeEmbeddingProvider:
    """Deterministic, instant stand-in for tests: no model download, same input -> same vector.

    Uses the "hashing trick": each normalised word adds weight to a few positions picked by its
    hash, so texts sharing words get similar vectors. Crude, but enough to test the pipeline.
    """

    model_name = "fake-hashing-v1"
    dim = EMBEDDING_DIM

    def _vector(self, text: str) -> list[float]:
        vector = np.zeros(self.dim, dtype=np.float32)
        for word in normalize_for_search(text).split():
            digest = hashlib.sha256(word.encode()).digest()
            for i in range(0, 8, 2):
                index = int.from_bytes(digest[i : i + 2], "big") % self.dim
                vector[index] += 1.0 if digest[i + 8] % 2 else -1.0
        if not vector.any():
            vector[0] = 1.0
        return _unit(vector)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    settings = get_settings()
    if settings.embedding_provider == "fake":
        return FakeEmbeddingProvider()
    return LocalEmbeddingProvider(settings.embedding_model, settings.embedding_batch_size)
