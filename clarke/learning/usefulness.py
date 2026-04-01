"""Usefulness scoring from multiple signals."""


def compute_usefulness_score(
    feedback_accepted: bool | None = None,
    feedback_score: float | None = None,
    ucr: float = 0.0,
    groundedness_score: float | None = None,
) -> float:
    """Combine signals into a single usefulness score in [0, 1].

    Weights:
    - feedback (if present): 0.4
    - useful_context_ratio: 0.3
    - groundedness (if present): 0.3

    If a signal is absent, redistribute its weight equally.
    """
    signals: list[tuple[float, float]] = []  # (value, weight)

    # Feedback signal
    if feedback_score is not None:
        signals.append((max(0.0, min(1.0, feedback_score)), 0.4))
    elif feedback_accepted is not None:
        signals.append((1.0 if feedback_accepted else 0.0, 0.4))

    # UCR signal
    signals.append((max(0.0, min(1.0, ucr)), 0.3))

    # Groundedness signal
    if groundedness_score is not None:
        signals.append((max(0.0, min(1.0, groundedness_score)), 0.3))

    if not signals:
        return 0.0

    total_weight = sum(w for _, w in signals)
    if total_weight == 0:
        return 0.0

    weighted_sum = sum(v * w for v, w in signals)
    return round(weighted_sum / total_weight, 4)
