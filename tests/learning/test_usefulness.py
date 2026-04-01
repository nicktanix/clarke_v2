"""Usefulness scoring tests."""

from clarke.learning.usefulness import compute_usefulness_score


def test_with_all_signals():
    score = compute_usefulness_score(
        feedback_accepted=True,
        feedback_score=0.8,
        ucr=0.7,
        groundedness_score=0.9,
    )
    assert 0.0 <= score <= 1.0
    assert score > 0.5


def test_without_feedback():
    score = compute_usefulness_score(ucr=0.7, groundedness_score=0.9)
    assert 0.0 <= score <= 1.0


def test_without_groundedness():
    score = compute_usefulness_score(feedback_accepted=True, ucr=0.7)
    assert 0.0 <= score <= 1.0


def test_feedback_rejected():
    score = compute_usefulness_score(feedback_accepted=False, ucr=0.7)
    assert score < compute_usefulness_score(feedback_accepted=True, ucr=0.7)


def test_no_signals():
    assert compute_usefulness_score(ucr=0.0) == 0.0
