"""Rewrite template inventory — predefined query transformations."""

from clarke.telemetry.logging import get_logger

logger = get_logger(__name__)

BUILTIN_TEMPLATES = [
    {
        "source": "docs",
        "strategy": "direct",
        "template": "{query} — extract key facts and definitions",
        "description": "factual_extract",
    },
    {
        "source": "decisions",
        "strategy": "direct",
        "template": "prior decisions and tradeoffs related to: {query}",
        "description": "decision_context",
    },
    {
        "source": "docs",
        "strategy": "direct",
        "template": "implementation details, code patterns, and technical specifics for: {query}",
        "description": "implementation_detail",
    },
    {
        "source": "docs",
        "strategy": "direct",
        "template": "constraints, rules, policies, and requirements related to: {query}",
        "description": "constraint_check",
    },
]


def apply_template(template: str, query: str) -> str:
    """Apply a rewrite template to a query."""
    return template.replace("{query}", query)


def select_templates(
    source: str,
    strategy: str,
    features: dict | None = None,
    max_templates: int = 2,
) -> list[dict]:
    """Select applicable templates for a given source/strategy.

    Returns at most max_templates matching templates.
    """
    matching = [t for t in BUILTIN_TEMPLATES if t["source"] == source and t["strategy"] == strategy]

    # Prioritize by feature match
    if features:
        is_design = features.get("is_design_oriented", 0) > 0.5
        doc_dep = features.get("doc_dependency", 0) > 0.5

        # Sort: implementation_detail first for design queries, factual for doc queries
        def priority(t: dict) -> int:
            if is_design and t["description"] == "implementation_detail":
                return 0
            if doc_dep and t["description"] == "factual_extract":
                return 0
            return 1

        matching.sort(key=priority)

    return matching[:max_templates]
