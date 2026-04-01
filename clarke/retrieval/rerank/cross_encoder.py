"""Cross-encoder reranker with graceful fallback."""

import math

from clarke.api.schemas.retrieval import RetrievedItem
from clarke.telemetry.logging import get_logger

logger = get_logger(__name__)

_SENTENCE_TRANSFORMERS_AVAILABLE = False
try:
    from sentence_transformers import CrossEncoder

    _SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    pass


class CrossEncoderReranker:
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2") -> None:
        self._model_name = model_name
        self._model = None

    def _load_model(self):  # type: ignore[no-untyped-def]
        """Lazy-load the model on first use."""
        if not _SENTENCE_TRANSFORMERS_AVAILABLE:
            return None
        if self._model is None:
            self._model = CrossEncoder(self._model_name)
        return self._model

    def rerank(
        self,
        query: str,
        items: list[RetrievedItem],
        top_k: int = 5,
    ) -> list[RetrievedItem]:
        """Rerank items by cross-encoder relevance score."""
        if not items:
            return []

        model = self._load_model()
        if model is None:
            logger.warning(
                "cross_encoder_unavailable", reason="sentence-transformers not installed"
            )
            return items[:top_k]

        pairs = [(query, item.summary) for item in items]
        raw_scores = model.predict(pairs)

        # Sigmoid normalize to [0, 1]
        scored_items = []
        for item, score in zip(items, raw_scores, strict=True):
            normalized = 1 / (1 + math.exp(-float(score)))
            scored_items.append(item.model_copy(update={"score": normalized}))

        scored_items.sort(key=lambda x: x.score, reverse=True)
        return scored_items[:top_k]
