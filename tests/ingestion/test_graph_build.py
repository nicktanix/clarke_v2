"""Graph build tests."""

from clarke.ingestion.graph_build import extract_entities


def test_extract_entities_capitalized_sequences():
    text = "The WebSocket Session Manager handles connections."
    entities = extract_entities(text)
    # Should find multi-word capitalized sequences
    found = any("WebSocket" in e and "Session" in e for e in entities)
    assert found, f"Expected WebSocket Session in {entities}"


def test_extract_entities_multi_word():
    text = "Use the Context Request Protocol for structured requests."
    entities = extract_entities(text)
    found = any("Context" in e and "Request" in e for e in entities)
    assert found, f"Expected Context Request in {entities}"


def test_extract_entities_deduplication():
    text = "The WebSocket Session is great. The WebSocket Session is mentioned again."
    entities = extract_entities(text)
    # Same phrase "The WebSocket Session" should only appear once
    ws_count = sum(1 for e in entities if "websocket session" in e.lower())
    assert ws_count == 1


def test_extract_entities_empty():
    assert extract_entities("") == []
    assert extract_entities("all lowercase text with no entities") == []
