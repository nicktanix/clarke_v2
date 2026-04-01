"""Exploration tests."""

from unittest.mock import patch

from clarke.retrieval.planner.exploration import select_exploration_strategy, should_explore


def test_should_explore_always_with_epsilon_1():
    assert should_explore(1.0) is True


def test_should_explore_never_with_epsilon_0():
    assert should_explore(0.0) is False


def test_should_explore_probabilistic():
    with patch("clarke.retrieval.planner.exploration.random") as mock_random:
        mock_random.random.return_value = 0.04
        assert should_explore(0.05) is True

        mock_random.random.return_value = 0.06
        assert should_explore(0.05) is False


def test_select_exploration_strategy_picks_low_weight():
    strategies = [
        {"source": "docs", "strategy": "direct"},
        {"source": "memory", "strategy": "direct"},
        {"source": "decisions", "strategy": "direct"},
    ]
    weights = {
        "docs:direct": 0.9,
        "memory:direct": 0.2,
        "decisions:direct": 0.3,
    }
    excluded = {"docs:direct"}

    result = select_exploration_strategy(strategies, weights, excluded)
    assert result is not None
    assert result["source"] in ("memory", "decisions")
    assert result.get("is_exploration") is True


def test_select_exploration_strategy_excludes_existing():
    strategies = [
        {"source": "docs", "strategy": "direct"},
    ]
    excluded = {"docs:direct"}

    result = select_exploration_strategy(strategies, {}, excluded)
    assert result is None


def test_select_exploration_strategy_empty():
    result = select_exploration_strategy([], {}, set())
    assert result is None
