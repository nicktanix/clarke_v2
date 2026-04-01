"""HDBSCAN clustering of retrieval episodes into proto-classes."""

import numpy as np
from sklearn.cluster import HDBSCAN
from sklearn.preprocessing import normalize

from clarke.telemetry.logging import get_logger

logger = get_logger(__name__)

# Source types for feature vector construction
_SOURCE_TYPES = ["docs", "memory", "decisions", "graph", "policy"]
_STRATEGY_TYPES = ["direct", "leaf_first", "convergence_anchor"]


def build_episode_vector(episode: dict) -> list[float]:
    """Convert a retrieval episode to a feature vector for clustering.

    Vector components (12 dimensions):
    - query features: is_design_oriented, doc_dependency, recent_history_dependency (3)
    - source mixture: fraction from each source type (5)
    - strategy mixture: fraction using each strategy (3)
    - usefulness_score (1)
    """
    features = episode.get("query_features") or {}
    plan = episode.get("retrieval_plan") or []
    items = episode.get("retrieved_items") or []
    usefulness = episode.get("usefulness_score") or 0.0

    # Query features (3 floats)
    qf = [
        features.get("is_design_oriented", 0.0),
        features.get("doc_dependency", 0.0),
        features.get("recent_history_dependency", 0.0),
    ]

    # Source mixture (5 floats)
    source_counts: dict[str, int] = {s: 0 for s in _SOURCE_TYPES}
    for item in items:
        src = item.get("source", "docs") if isinstance(item, dict) else "docs"
        if src in source_counts:
            source_counts[src] += 1
    total_items = max(len(items), 1)
    source_mix = [source_counts[s] / total_items for s in _SOURCE_TYPES]

    # Strategy mixture (3 floats)
    strategy_counts: dict[str, int] = {s: 0 for s in _STRATEGY_TYPES}
    for req in plan:
        strat = req.get("strategy", "direct") if isinstance(req, dict) else "direct"
        if strat in strategy_counts:
            strategy_counts[strat] += 1
    total_strats = max(len(plan), 1)
    strategy_mix = [strategy_counts[s] / total_strats for s in _STRATEGY_TYPES]

    return qf + source_mix + strategy_mix + [usefulness]


def cluster_episodes(
    episodes: list[dict],
    min_cluster_size: int = 5,
) -> dict[int, list[int]]:
    """Run HDBSCAN on episode feature vectors.

    Returns mapping of cluster_label -> list of episode indices.
    Label -1 means noise (unclustered).
    """
    if len(episodes) < min_cluster_size:
        return {}

    vectors = [build_episode_vector(ep) for ep in episodes]
    X = np.array(vectors, dtype=np.float64)

    # Normalize for better clustering
    X = normalize(X)

    clusterer = HDBSCAN(min_cluster_size=min_cluster_size, metric="euclidean")
    labels = clusterer.fit_predict(X)

    clusters: dict[int, list[int]] = {}
    for idx, label in enumerate(labels):
        label = int(label)
        if label == -1:
            continue
        clusters.setdefault(label, []).append(idx)

    logger.info(
        "clustering_complete",
        total_episodes=len(episodes),
        clusters_found=len(clusters),
        noise_count=int(sum(1 for lbl in labels if lbl == -1)),
    )

    return clusters


def compute_centroid(vectors: list[list[float]]) -> list[float]:
    """Compute mean centroid of a set of feature vectors."""
    if not vectors:
        return []
    arr = np.array(vectors, dtype=np.float64)
    return arr.mean(axis=0).tolist()
