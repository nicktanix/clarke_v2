"""Extract query features using keyword heuristics."""

import re

from clarke.graph.state import BrokerState

_DESIGN_KEYWORDS = {
    "design",
    "architecture",
    "pattern",
    "structure",
    "approach",
    "tradeoff",
    "trade-off",
    "decision",
    "alternative",
    "comparison",
    "component",
}
_DOC_KEYWORDS = {
    "document",
    "file",
    "section",
    "page",
    "spec",
    "specification",
    "readme",
    "docs",
    "documentation",
    "reference",
}
_HISTORY_KEYWORDS = {
    "previously",
    "before",
    "last time",
    "earlier",
    "recent",
    "yesterday",
    "last week",
    "history",
    "prior",
}
_STOPWORDS = {
    "the",
    "a",
    "an",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "have",
    "has",
    "had",
    "do",
    "does",
    "did",
    "will",
    "would",
    "could",
    "should",
    "may",
    "might",
    "shall",
    "can",
    "need",
    "dare",
    "ought",
    "used",
    "to",
    "of",
    "in",
    "for",
    "on",
    "with",
    "at",
    "by",
    "from",
    "as",
    "into",
    "through",
    "during",
    "until",
    "against",
    "among",
    "throughout",
    "despite",
    "towards",
    "upon",
    "about",
    "it",
    "its",
    "this",
    "that",
    "these",
    "those",
    "i",
    "me",
    "my",
    "we",
    "our",
    "you",
    "your",
    "he",
    "she",
    "they",
    "them",
    "what",
    "which",
    "who",
    "when",
    "where",
    "why",
    "how",
    "not",
    "no",
    "nor",
    "and",
    "but",
    "or",
    "so",
    "if",
    "then",
    "else",
    "than",
    "too",
    "very",
    "just",
}


def _keyword_score(message: str, keywords: set[str]) -> float:
    """Score how many keywords appear in the message."""
    words = set(message.lower().split())
    matches = words & keywords
    if not matches:
        # Check multi-word keywords
        lower = message.lower()
        matches = {kw for kw in keywords if " " in kw and kw in lower}
    return min(len(matches) / 3.0, 1.0)


def _extract_keywords(message: str) -> list[str]:
    """Extract significant terms from the message."""
    words = re.findall(r"\b\w+\b", message.lower())
    return [w for w in words if w not in _STOPWORDS and len(w) > 2]


def _detect_question_type(message: str) -> str:
    """Classify the question type."""
    lower = message.lower()
    if any(w in lower for w in ["how do", "how to", "steps to", "process for", "procedure"]):
        return "procedural"
    if any(
        w in lower
        for w in ["compare", "tradeoff", "trade-off", "versus", "vs", "difference between"]
    ):
        return "comparison"
    if any(w in lower for w in ["why", "reason", "rationale", "motivation"]):
        return "conceptual"
    if any(w in lower for w in ["what is", "what are", "define", "explain"]):
        return "factual"
    return "general"


def _extract_entities(message: str) -> list[str]:
    """Extract candidate entities (capitalized multi-word sequences)."""
    entity_pattern = re.compile(r"\b([A-Z]\w+(?:\s+[A-Z]\w+)+)\b")
    matches = entity_pattern.findall(message)
    seen: set[str] = set()
    entities: list[str] = []
    for m in matches:
        if m.lower() not in seen:
            seen.add(m.lower())
            entities.append(m)
    return entities


def extract_features(state: BrokerState) -> dict:
    """Extract query features using keyword heuristics, entity detection, and question classification."""
    message = state.get("message", "")

    features = {
        "is_design_oriented": _keyword_score(message, _DESIGN_KEYWORDS),
        "doc_dependency": _keyword_score(message, _DOC_KEYWORDS),
        "recent_history_dependency": _keyword_score(message, _HISTORY_KEYWORDS),
        "keywords": _extract_keywords(message),
        "question_type": _detect_question_type(message),
        "entities": _extract_entities(message),
    }

    return {"query_features": features}
