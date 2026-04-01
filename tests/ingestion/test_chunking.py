"""Chunking tests."""

from clarke.ingestion.chunking import chunk_sections
from clarke.ingestion.documents import ParsedSection


def _fake_count(text: str, model: str = "") -> int:
    """Simple word-based token counter for testing."""
    return len(text.split())


def test_single_section_fits_in_one_chunk():
    sections = [ParsedSection(content="Short content here.", index=0)]
    chunks = chunk_sections(sections, document_id="d1", max_tokens=100, count_fn=_fake_count)
    assert len(chunks) == 1
    assert chunks[0].content == "Short content here."
    assert chunks[0].metadata["document_id"] == "d1"


def test_long_section_splits():
    # Create a section with many sentences
    sentences = [f"Sentence number {i} with some words." for i in range(20)]
    content = " ".join(sentences)
    sections = [ParsedSection(content=content, index=0)]
    chunks = chunk_sections(sections, document_id="d1", max_tokens=20, count_fn=_fake_count)
    assert len(chunks) > 1


def test_chunk_preserves_metadata():
    sections = [ParsedSection(content="Some content.", heading="My Section", level=2, index=3)]
    chunks = chunk_sections(sections, document_id="d1", max_tokens=100, count_fn=_fake_count)
    assert chunks[0].metadata["heading"] == "My Section"
    assert chunks[0].metadata["section_index"] == 3


def test_multiple_sections():
    sections = [
        ParsedSection(content="First section.", index=0),
        ParsedSection(content="Second section.", index=1),
    ]
    chunks = chunk_sections(sections, document_id="d1", max_tokens=100, count_fn=_fake_count)
    assert len(chunks) == 2
    assert chunks[0].chunk_index == 0
    assert chunks[1].chunk_index == 1


def test_empty_sections():
    chunks = chunk_sections([], document_id="d1")
    assert chunks == []
