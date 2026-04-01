"""Semantic deduplication of retrieved items."""

import re

import numpy as np

from clarke.api.schemas.retrieval import RetrievedItem


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    va = np.array(a)
    vb = np.array(b)
    dot = np.dot(va, vb)
    norm = np.linalg.norm(va) * np.linalg.norm(vb)
    if norm == 0:
        return 0.0
    return float(dot / norm)


def deduplicate_items(
    items: list[RetrievedItem],
    embeddings: dict[str, list[float]],
    similarity_threshold: float = 0.92,
) -> list[RetrievedItem]:
    """Remove near-duplicate items based on cosine similarity.

    When two items are above threshold, keep the higher-scored one.
    """
    if len(items) <= 1:
        return items

    kept: list[RetrievedItem] = []
    removed_ids: set[str] = set()

    for i, item in enumerate(items):
        if item.item_id in removed_ids:
            continue

        emb_a = embeddings.get(item.item_id)
        if emb_a is None:
            kept.append(item)
            continue

        for j in range(i + 1, len(items)):
            other = items[j]
            if other.item_id in removed_ids:
                continue
            emb_b = embeddings.get(other.item_id)
            if emb_b is None:
                continue

            sim = _cosine_similarity(emb_a, emb_b)
            if sim >= similarity_threshold:
                # Keep the higher-scored item
                if item.score >= other.score:
                    removed_ids.add(other.item_id)
                else:
                    removed_ids.add(item.item_id)
                    break

        if item.item_id not in removed_ids:
            kept.append(item)

    return kept


def _text_tokens(text: str) -> set[str]:
    """Extract lowercased word tokens for overlap comparison."""
    return set(re.findall(r"\b\w{3,}\b", text.lower()))


def deduplicate_by_text_overlap(
    items: list[RetrievedItem],
    similarity_threshold: float = 0.7,
) -> list[RetrievedItem]:
    """Remove near-duplicate items based on text token overlap (no embeddings needed).

    When two items have high jaccard overlap, keep the higher-scored one.
    """
    if len(items) <= 1:
        return items

    token_cache: dict[str, set[str]] = {}
    for item in items:
        token_cache[item.item_id] = _text_tokens(item.summary)

    kept: list[RetrievedItem] = []
    removed_ids: set[str] = set()

    for i, item in enumerate(items):
        if item.item_id in removed_ids:
            continue

        tokens_a = token_cache.get(item.item_id, set())
        if not tokens_a:
            kept.append(item)
            continue

        for j in range(i + 1, len(items)):
            other = items[j]
            if other.item_id in removed_ids:
                continue
            tokens_b = token_cache.get(other.item_id, set())
            if not tokens_b:
                continue

            intersection = tokens_a & tokens_b
            union = tokens_a | tokens_b
            jaccard = len(intersection) / len(union) if union else 0.0

            if jaccard >= similarity_threshold:
                if item.score >= other.score:
                    removed_ids.add(other.item_id)
                else:
                    removed_ids.add(item.item_id)
                    break

        if item.item_id not in removed_ids:
            kept.append(item)

    return kept
