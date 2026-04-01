"""Trust precedence and policy definitions."""

from enum import IntEnum


class TrustPrecedence(IntEnum):
    """Memory source trust ordering — lower value = higher trust."""

    CANONICAL_POLICY = 1
    STRUCTURED_DECISION = 2
    AUTHORITATIVE_DOC = 3
    EPISODIC_SUMMARY = 4
    SEMANTIC_NEIGHBOR = 5
