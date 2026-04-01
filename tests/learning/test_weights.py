"""Weight update and epsilon decay tests."""

from clarke.learning.weights import compute_weight_update, decay_epsilon


def test_update_weight_basic():
    new = compute_weight_update(old_weight=0.5, usefulness_score=1.0, learning_rate=0.1)
    assert new == 0.5 * 0.9 + 1.0 * 0.1
    assert new == 0.55


def test_update_weight_zero_usefulness():
    new = compute_weight_update(old_weight=0.5, usefulness_score=0.0, learning_rate=0.1)
    assert new == 0.45


def test_update_weight_boundary():
    new = compute_weight_update(old_weight=1.0, usefulness_score=1.0, learning_rate=0.05)
    assert new == 1.0


def test_decay_epsilon():
    new = decay_epsilon(0.10, decay_rate=0.99, min_epsilon=0.05)
    assert new == 0.099


def test_decay_epsilon_respects_floor():
    new = decay_epsilon(0.05, decay_rate=0.99, min_epsilon=0.05)
    assert new == 0.05


def test_decay_epsilon_above_floor():
    new = decay_epsilon(0.051, decay_rate=0.99, min_epsilon=0.05)
    assert new >= 0.05
