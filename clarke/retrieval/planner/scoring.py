"""Score retrieval plans using proto-class membership."""

import numpy as np

from clarke.learning.clustering import build_episode_vector
from clarke.telemetry.logging import get_logger

logger = get_logger(__name__)


def score_by_proto_class(
    query_features: dict,
    retrieval_plan: list[dict],
    proto_classes: list[dict],
) -> list[dict]:
    """Boost retrieval request weights based on matching proto-class.

    Computes cosine similarity between the current query's feature vector
    and each proto-class centroid. If a match is found (similarity > 0.7),
    applies the class's retrieval signature to boost matching requests.
    """
    if not proto_classes:
        return retrieval_plan

    # Build feature vector for current query
    episode_proxy = {
        "query_features": query_features,
        "retrieval_plan": retrieval_plan,
        "retrieved_items": [],
        "usefulness_score": 0.5,
    }
    query_vector = np.array(build_episode_vector(episode_proxy))

    # Find best matching proto-class
    best_match = None
    best_sim = 0.0

    for pc in proto_classes:
        centroid = pc.get("centroid")
        if not centroid:
            continue
        centroid_arr = np.array(centroid)

        dot = np.dot(query_vector, centroid_arr)
        norm = np.linalg.norm(query_vector) * np.linalg.norm(centroid_arr)
        sim = float(dot / norm) if norm > 0 else 0.0

        if sim > best_sim:
            best_sim = sim
            best_match = pc

    if best_match is None or best_sim < 0.7:
        return retrieval_plan

    # Apply retrieval signature boost
    signature = best_match.get("retrieval_signature") or {}
    source_dist = signature.get("source_distribution", {})

    boosted = []
    for req in retrieval_plan:
        source = req.get("source", "docs")
        if source in source_dist:
            boost = min(source_dist[source] / 10.0, 0.2)
            req = {**req, "weight": min(req.get("weight", 0.5) + boost, 1.0)}
        boosted.append(req)

    logger.debug(
        "proto_class_scoring_applied",
        class_id=best_match.get("id"),
        similarity=round(best_sim, 3),
    )

    return boosted
