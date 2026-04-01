"""Rewrite template tests."""

from clarke.retrieval.planner.templates import apply_template, select_templates


def test_apply_template():
    result = apply_template("facts about: {query}", "websocket sessions")
    assert result == "facts about: websocket sessions"


def test_apply_template_no_placeholder():
    result = apply_template("static query", "ignored")
    assert result == "static query"


def test_select_templates_matching():
    templates = select_templates("docs", "direct")
    assert len(templates) >= 1
    assert all(t["source"] == "docs" for t in templates)


def test_select_templates_no_match():
    templates = select_templates("nonexistent", "none")
    assert templates == []


def test_select_templates_respects_max():
    templates = select_templates("docs", "direct", max_templates=1)
    assert len(templates) <= 1


def test_select_templates_design_priority():
    templates = select_templates(
        "docs", "direct", features={"is_design_oriented": 0.9}, max_templates=2
    )
    if len(templates) >= 2:
        # implementation_detail should come first for design queries
        assert templates[0]["description"] == "implementation_detail"
