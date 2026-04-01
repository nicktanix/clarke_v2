"""Epsilon-greedy exploration for retrieval strategy selection."""

import random


def should_explore(epsilon: float) -> bool:
    """Return True with probability epsilon."""
    return random.random() < epsilon


def select_exploration_strategy(
    available_strategies: list[dict],
    current_weights: dict[str, float],
    excluded_keys: set[str],
) -> dict | None:
    """Pick one low-weight strategy not already in the plan.

    Selects from strategies whose weight is below the median.
    Returns a retrieval request dict or None if nothing eligible.

    available_strategies: list of {"source": str, "strategy": str} dicts
    current_weights: maps "source:strategy" -> weight
    excluded_keys: "source:strategy" keys already in the plan
    """
    if not available_strategies:
        return None

    candidates = []
    for strat in available_strategies:
        key = f"{strat['source']}:{strat['strategy']}"
        if key in excluded_keys:
            continue
        weight = current_weights.get(key, 0.5)
        candidates.append((strat, weight))

    if not candidates:
        return None

    # Sort by weight ascending — pick from the lowest-weight strategies
    candidates.sort(key=lambda x: x[1])

    # Pick from the bottom half (below median)
    mid = max(len(candidates) // 2, 1)
    selected_strat, selected_weight = random.choice(candidates[:mid])

    return {
        "source": selected_strat["source"],
        "strategy": selected_strat["strategy"],
        "query": "",  # will use the user message
        "weight": selected_weight,
        "constraints": {"max_items": 5, "timeout_ms": 800},
        "is_exploration": True,
    }
