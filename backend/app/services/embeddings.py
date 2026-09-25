"""Local text embeddings (no API key required). The model loads lazily, once per process."""

import threading
from typing import TYPE_CHECKING

from app.core.config import get_settings

if TYPE_CHECKING:
    from fastembed import TextEmbedding

_model: "TextEmbedding | None" = None
_lock = threading.Lock()


def _get_model() -> "TextEmbedding":
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                from fastembed import TextEmbedding

                settings = get_settings()
                _model = TextEmbedding(
                    settings.embedding_model, cache_dir=settings.embedding_cache_dir
                )
    return _model


def embed_passages(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    return [vector.tolist() for vector in _get_model().passage_embed(texts)]


def embed_query(text: str) -> list[float]:
    vector: list[float] = next(iter(_get_model().query_embed(text))).tolist()
    return vector
