"""Token counting tests."""

from clarke.llm.token_counting import count_tokens


def test_count_tokens_empty_string():
    assert count_tokens("") == 0


def test_count_tokens_known_model():
    # gpt-4o-mini uses cl100k_base tokenizer
    count = count_tokens("Hello, world!", "gpt-4o-mini")
    assert count > 0
    assert count < 10  # "Hello, world!" is about 4 tokens


def test_count_tokens_unknown_model_falls_back():
    count = count_tokens("Hello world", "unknown-model-xyz")
    assert count == len("Hello world") // 4


def test_count_tokens_no_model_falls_back():
    count = count_tokens("Hello world")
    assert count == len("Hello world") // 4
