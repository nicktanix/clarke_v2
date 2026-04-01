"""Episodic memory tests."""

from unittest.mock import AsyncMock, patch

import pytest

from clarke.memory.episodic import build_episodic_summary, store_episodic_memory


def test_build_episodic_summary_basic():
    summary = build_episodic_summary("What is CLARKE?", "CLARKE is a context engine.")
    assert "User asked: What is CLARKE?" in summary
    assert "CLARKE is a context engine." in summary


def test_build_episodic_summary_with_keywords():
    summary = build_episodic_summary(
        "How does auth work?",
        "Auth uses JWT tokens.",
        query_features={"keywords": ["auth", "work"]},
    )
    assert "Topics: auth, work" in summary


def test_build_episodic_summary_truncates_answer():
    long_answer = "x" * 1000
    summary = build_episodic_summary("question", long_answer)
    assert len(summary) < 600  # answer truncated to 500


@pytest.mark.asyncio
async def test_store_episodic_memory_success():
    with (
        patch(
            "clarke.memory.episodic.embed_single",
            new_callable=AsyncMock,
            return_value=[0.1] * 1536,
        ),
        patch("clarke.retrieval.qdrant.client.get_qdrant_store") as mock_qdrant,
    ):
        mock_store = AsyncMock()
        mock_store.upsert_chunks = AsyncMock()
        mock_qdrant.return_value = mock_store

        await store_episodic_memory(
            tenant_id="t1",
            project_id="p1",
            user_id="u1",
            session_id="s1",
            request_id="r_test",
            message="We decided to use PostgreSQL for the canonical storage layer going forward.",
            answer="Good choice. PostgreSQL provides ACID transactions, JSONB support, and row-level security.",
        )

        mock_store.upsert_chunks.assert_called_once()
        call_args = mock_store.upsert_chunks.call_args
        payload = (
            call_args.kwargs.get("payloads") or call_args[1].get("payloads") or call_args[0][2]
        )
        assert payload[0]["source_type"] == "memory"
        assert payload[0]["node_type"] == "episodic"


@pytest.mark.asyncio
async def test_store_episodic_memory_qdrant_unavailable():
    import clarke.retrieval.qdrant.client as qdrant_module

    original = qdrant_module._store

    with patch(
        "clarke.memory.episodic.embed_single",
        new_callable=AsyncMock,
        return_value=[0.1] * 1536,
    ):
        qdrant_module._store = None  # simulate not initialized
        try:
            # Should not raise
            await store_episodic_memory(
                tenant_id="t1",
                project_id="p1",
                user_id="u1",
                session_id=None,
                request_id="r_test",
                message="test",
                answer="test answer",
            )
        finally:
            qdrant_module._store = original
