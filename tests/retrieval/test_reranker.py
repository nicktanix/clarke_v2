"""Reranker tests."""

from unittest.mock import MagicMock, patch

from clarke.api.schemas.retrieval import Provenance, RetrievedItem
from clarke.retrieval.rerank.cross_encoder import CrossEncoderReranker


def _make_item(item_id: str, score: float = 0.5) -> RetrievedItem:
    return RetrievedItem(
        item_id=item_id,
        tenant_id="t1",
        project_id="p1",
        source="docs",
        node_type="chunk",
        score=score,
        summary=f"Content for {item_id}",
        provenance=Provenance(),
    )


def test_reranker_empty_input():
    reranker = CrossEncoderReranker()
    assert reranker.rerank("query", []) == []


def test_reranker_graceful_fallback_without_sentence_transformers():
    with patch("clarke.retrieval.rerank.cross_encoder._SENTENCE_TRANSFORMERS_AVAILABLE", False):
        reranker = CrossEncoderReranker()
        reranker._model = None
        items = [_make_item("a"), _make_item("b"), _make_item("c")]
        result = reranker.rerank("query", items, top_k=2)
        assert len(result) == 2


def test_reranker_with_mocked_model():
    reranker = CrossEncoderReranker()
    mock_model = MagicMock()
    mock_model.predict.return_value = [0.9, 0.1, 0.5]
    reranker._model = mock_model

    with patch("clarke.retrieval.rerank.cross_encoder._SENTENCE_TRANSFORMERS_AVAILABLE", True):
        items = [_make_item("a"), _make_item("b"), _make_item("c")]
        result = reranker.rerank("query", items, top_k=2)
        assert len(result) == 2
        # Highest raw score (0.9) should be first after sigmoid
        assert result[0].item_id == "a"
        assert result[0].score > result[1].score
