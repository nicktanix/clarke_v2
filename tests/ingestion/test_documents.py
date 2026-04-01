"""Document parsing tests."""

from clarke.ingestion.documents import (
    parse_document,
    parse_html,
    parse_markdown,
    parse_plain_text,
)


def test_parse_markdown_with_headers():
    md = """# Title

Introduction paragraph.

## Section One

Content of section one.

## Section Two

Content of section two.
"""
    sections = parse_markdown(md)
    assert len(sections) == 3
    assert sections[0].heading == "Title"
    assert sections[0].level == 1
    assert sections[1].heading == "Section One"
    assert sections[2].heading == "Section Two"


def test_parse_markdown_no_headers():
    md = "Just a plain paragraph without any headers."
    sections = parse_markdown(md)
    assert len(sections) == 1
    assert sections[0].heading is None


def test_parse_markdown_empty():
    assert parse_markdown("") == []
    assert parse_markdown("   ") == []


def test_parse_plain_text():
    text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
    sections = parse_plain_text(text)
    assert len(sections) == 3
    assert sections[0].content == "First paragraph."
    assert sections[2].content == "Third paragraph."


def test_parse_plain_text_empty():
    assert parse_plain_text("") == []


def test_parse_html():
    html = "<html><body><p>Hello</p><p>World</p></body></html>"
    sections = parse_html(html)
    assert len(sections) >= 1
    assert "Hello" in sections[0].content


def test_parse_document_dispatches_correctly():
    md = "# Header\n\nContent"
    sections = parse_document(md, "text/markdown")
    assert any(s.heading == "Header" for s in sections)

    text = "Plain content"
    sections = parse_document(text, "text/plain")
    assert len(sections) == 1

    sections = parse_document(text, "unknown/type")
    assert len(sections) == 1  # falls back to plain text
