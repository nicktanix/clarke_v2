"""PII/sensitive data scrubbing."""

import re
from dataclasses import dataclass, field

EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
PHONE_PATTERN = re.compile(r"\b(?:\+?1[-.\s]?)?(?:\(?[0-9]{3}\)?[-.\s]?)?[0-9]{3}[-.\s]?[0-9]{4}\b")
SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")


@dataclass
class RedactionResult:
    content: str
    redacted_fields: list[str] = field(default_factory=list)


def redact(text: str) -> RedactionResult:
    """Apply all redaction patterns. Replace matches with [REDACTED_TYPE]."""
    redacted_fields: list[str] = []
    result = text

    if SSN_PATTERN.search(result):
        result = SSN_PATTERN.sub("[REDACTED_SSN]", result)
        redacted_fields.append("ssn")

    if EMAIL_PATTERN.search(result):
        result = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", result)
        redacted_fields.append("email")

    if PHONE_PATTERN.search(result):
        result = PHONE_PATTERN.sub("[REDACTED_PHONE]", result)
        redacted_fields.append("phone")

    return RedactionResult(content=result, redacted_fields=redacted_fields)
