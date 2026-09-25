"""Second-stage re-ranking with a local cross-encoder (no API key required).

The first stage (hybrid search) compares the question and each passage separately. A
cross-encoder reads them together, which is far better at telling "the section that answers
this" from "a section that shares its words". Its score also tells whether anything in the
document answers the question at all (see qa.py).

Model: Xenova/ms-marco-MiniLM-L-6-v2 (~80 MB, downloaded once). Chosen on the dev split of
tests/real_document_cases.py: Recall@1 0.59 → 0.77 at ~0.4 s per question on a laptop CPU;
BAAI/bge-reranker-base was both slower (~3 s) and less accurate (0.64) there.
"""

import threading
from collections.abc import Sequence
from typing import TYPE_CHECKING

from app.core.config import get_settings

if TYPE_CHECKING:
    from fastembed.rerank.cross_encoder import TextCrossEncoder

_model: "TextCrossEncoder | None" = None
_lock = threading.Lock()


def enabled() -> bool:
    return get_settings().rerank_model.lower() != "none"


def _get_model() -> "TextCrossEncoder":
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                from fastembed.rerank.cross_encoder import TextCrossEncoder

                settings = get_settings()
                _model = TextCrossEncoder(
                    settings.rerank_model, cache_dir=settings.embedding_cache_dir
                )
    return _model


def scores(question: str, passages: Sequence[str]) -> list[float]:
    """Relevance of each passage to the question (higher is better; roughly -11 … +10)."""
    if not passages:
        return []
    return [float(s) for s in _get_model().rerank(question, list(passages))]
