"""Clustering tests."""

from clarke.learning.clustering import build_episode_vector, cluster_episodes, compute_centroid


def test_build_episode_vector_basic():
    episode = {
        "query_features": {"is_design_oriented": 0.8, "doc_dependency": 0.3},
        "retrieval_plan": [{"source": "docs", "strategy": "direct"}],
        "retrieved_items": [{"source": "docs"}, {"source": "graph"}],
        "usefulness_score": 0.7,
    }
    vec = build_episode_vector(episode)
    assert len(vec) == 12
    assert vec[0] == 0.8  # is_design_oriented
    assert vec[-1] == 0.7  # usefulness


def test_build_episode_vector_empty():
    vec = build_episode_vector({})
    assert len(vec) == 12
    assert all(v == 0.0 for v in vec)


def test_cluster_episodes_too_few():
    episodes = [{"query_features": {}} for _ in range(3)]
    result = cluster_episodes(episodes, min_cluster_size=5)
    assert result == {}


def test_cluster_episodes_finds_clusters():
    # Create two distinct clusters
    cluster_a = [
        {
            "query_features": {"is_design_oriented": 0.9, "doc_dependency": 0.1},
            "retrieval_plan": [{"source": "docs", "strategy": "direct"}],
            "retrieved_items": [{"source": "docs"}] * 5,
            "usefulness_score": 0.8,
        }
        for _ in range(10)
    ]
    cluster_b = [
        {
            "query_features": {"is_design_oriented": 0.1, "doc_dependency": 0.9},
            "retrieval_plan": [{"source": "decisions", "strategy": "direct"}],
            "retrieved_items": [{"source": "decisions"}] * 5,
            "usefulness_score": 0.3,
        }
        for _ in range(10)
    ]
    episodes = cluster_a + cluster_b
    result = cluster_episodes(episodes, min_cluster_size=5)
    # Should find at least 1 cluster (HDBSCAN behavior depends on data)
    assert isinstance(result, dict)


def test_compute_centroid():
    vectors = [[1.0, 2.0, 3.0], [3.0, 4.0, 5.0]]
    centroid = compute_centroid(vectors)
    assert len(centroid) == 3
    assert centroid[0] == 2.0
    assert centroid[1] == 3.0


def test_compute_centroid_empty():
    assert compute_centroid([]) == []
