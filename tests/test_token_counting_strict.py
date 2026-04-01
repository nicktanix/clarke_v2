"""Token counting strict mode tests."""

from clarke.llm.token_counting import count_tokens


def test_strict_mode_known_model_works():
    # gpt-4o-mini is a known model with tiktoken support
    count = count_tokens("Hello, world!", "gpt-4o-mini", strict=True)
    assert count > 0


def test_strict_mode_unknown_model_falls_back():
    # Unknown models still use char estimate even in strict mode
    count = count_tokens("Hello world", "unknown-model", strict=True)
    assert count == len("Hello world") // 4


def test_non_strict_mode_always_works():
    count = count_tokens("Hello world", "unknown-model", strict=False)
    assert count == len("Hello world") // 4
