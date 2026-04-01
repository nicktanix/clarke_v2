"""Redaction tests."""

from clarke.ingestion.redaction import redact


def test_redact_email():
    result = redact("Contact us at user@example.com for info.")
    assert "[REDACTED_EMAIL]" in result.content
    assert "email" in result.redacted_fields
    assert "user@example.com" not in result.content


def test_redact_phone():
    result = redact("Call us at 555-123-4567.")
    assert "[REDACTED_PHONE]" in result.content
    assert "phone" in result.redacted_fields


def test_redact_ssn():
    result = redact("SSN: 123-45-6789")
    assert "[REDACTED_SSN]" in result.content
    assert "ssn" in result.redacted_fields
    assert "123-45-6789" not in result.content


def test_redact_multiple_patterns():
    result = redact("Email: a@b.com, SSN: 111-22-3333, Phone: 555-000-1234")
    assert "email" in result.redacted_fields
    assert "ssn" in result.redacted_fields
    assert "phone" in result.redacted_fields


def test_redact_no_pii():
    text = "This is clean text with no sensitive data."
    result = redact(text)
    assert result.content == text
    assert result.redacted_fields == []
