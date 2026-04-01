"""Significance classification tests."""

from clarke.memory.significance import classify_significance


def test_decision_high_significance():
    sig = classify_significance(
        "We decided to use PostgreSQL for the canonical store.",
        "Good choice. PostgreSQL provides ACID guarantees.",
    )
    assert sig.memory_type == "decision"
    assert sig.score >= 0.8
    assert sig.should_store is True


def test_preference_high_significance():
    sig = classify_significance(
        "I prefer responses that include code examples.",
        "Understood, I'll include code examples going forward.",
    )
    assert sig.memory_type == "preference"
    assert sig.score >= 0.7
    assert sig.should_store is True


def test_correction_high_significance():
    sig = classify_significance(
        "Actually, that's wrong. The timeout is 30 seconds, not 60.",
        "You're right, I apologize. The timeout is 30 seconds.",
    )
    assert sig.memory_type == "correction"
    assert sig.score >= 0.8
    assert sig.should_store is True


def test_factual_moderate_significance():
    sig = classify_significance(
        "What is the connection pool size?",
        "The maximum connection pool size is 50 connections.",
    )
    assert sig.memory_type == "factual"
    assert sig.score >= 0.5
    assert sig.should_store is True


def test_greeting_is_noise():
    sig = classify_significance("Hello!", "Hi there! How can I help?")
    assert sig.memory_type == "noise"
    assert sig.score < 0.2
    assert sig.should_store is False


def test_thanks_is_noise():
    sig = classify_significance("Thanks", "You're welcome!")
    assert sig.memory_type == "noise"
    assert sig.score < 0.2
    assert sig.should_store is False


def test_short_message_is_noise():
    sig = classify_significance("ok", "Understood.")
    assert sig.memory_type == "noise"
    assert sig.should_store is False


def test_no_info_answer_is_noise():
    sig = classify_significance(
        "What color is the sky on Mars?",
        "I don't have information about that topic.",
    )
    assert sig.memory_type == "noise"
    assert sig.should_store is False


def test_design_discussion_significant():
    sig = classify_significance(
        "What are the tradeoffs between Redis and Memcached for our caching layer?",
        "Redis offers persistence and data structures while Memcached is simpler.",
        query_features={"is_design_oriented": 0.8},
    )
    assert sig.score >= 0.6
    assert sig.should_store is True


def test_standard_question_moderate():
    sig = classify_significance(
        "How does the authentication system validate tokens?",
        "Tokens are validated using the JWT library with RS256 signatures.",
    )
    assert sig.should_store is True
    assert sig.score >= 0.3


# --- Coding context ---


def test_bug_fix_with_traceback():
    sig = classify_significance(
        "I'm getting this error:\nTraceback (most recent call last):\n  File 'app.py', line 42\nTypeError: 'NoneType' object is not subscriptable",
        "The issue was that the dictionary lookup returns None when the key doesn't exist. The fix is to use .get() with a default value. To prevent this in the future, always use .get() for optional dictionary keys.",
    )
    assert sig.memory_type == "bug_fix"
    assert sig.score >= 0.9
    assert sig.should_store is True


def test_bug_fix_with_http_error():
    sig = classify_significance(
        "The API is returning HTTP 500 on the /users endpoint",
        "The root cause was a missing null check in the user serializer. Fixed by adding validation before accessing the profile field.",
    )
    assert sig.memory_type == "bug_fix"
    assert sig.score >= 0.85
    assert sig.should_store is True


def test_bug_fix_error_only_no_fix():
    sig = classify_significance(
        "Getting ECONNREFUSED when connecting to the database",
        "Let me help investigate. Can you check if PostgreSQL is running?",
    )
    assert sig.memory_type == "bug_fix"
    assert sig.score >= 0.7
    assert sig.should_store is True


def test_bug_fix_with_prevention():
    sig = classify_significance(
        "ValueError: invalid UUID format",
        "The fix is to validate UUIDs before passing them to the database layer. To prevent this in the future, add input validation at the API boundary.",
    )
    assert sig.memory_type == "bug_fix"
    assert sig.score >= 0.9
    assert "prevention" in sig.reason.lower()


def test_code_pattern_style_guide():
    sig = classify_significance(
        "What's our coding standard for naming database models?",
        "Our style guide says to use PascalCase for model classes and snake_case for table names. Always use singular nouns for model names.",
    )
    assert sig.memory_type == "code_pattern"
    assert sig.score >= 0.8
    assert sig.should_store is True


def test_code_pattern_anti_pattern():
    sig = classify_significance(
        "Is it okay to use global variables for database connections?",
        "That's an anti-pattern. Use dependency injection instead. Global state makes testing difficult and creates race conditions.",
    )
    assert sig.memory_type == "code_pattern"
    assert sig.score >= 0.8
    assert sig.should_store is True


def test_code_pattern_linting():
    sig = classify_significance(
        "Should we enforce type hints in our pre-commit hooks?",
        "Yes, add mypy to pre-commit. Our lint rule requires type annotations on all public functions.",
    )
    assert sig.memory_type == "code_pattern"
    assert sig.should_store is True


def test_code_pattern_security():
    sig = classify_significance(
        "How do we handle user input in SQL queries?",
        "Never use string concatenation. Always use parameterized queries to prevent SQL injection. Use SQLAlchemy's bound parameters.",
    )
    assert sig.memory_type == "code_pattern"
    assert sig.should_store is True


def test_code_review_guidance():
    sig = classify_significance(
        "What should I look for in code reviews for the API layer?",
        "In code review, check for: input validation on all endpoints, proper error handling, consistent naming conventions, and test coverage for edge cases.",
    )
    assert sig.memory_type == "code_pattern"
    assert sig.should_store is True
