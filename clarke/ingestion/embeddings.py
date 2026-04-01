"""Embedding generation via LiteLLM."""

import litellm

from clarke.telemetry.logging import get_logger

logger = get_logger(__name__)

_BATCH_SIZE = 100


async def embed_texts(
    texts: list[str],
    model: str = "text-embedding-3-small",
    dimensions: int = 1536,
) -> list[list[float]]:
    """Generate embeddings via LiteLLM's embedding endpoint.

    Batches texts to avoid rate limits.
    """
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), _BATCH_SIZE):
        batch = texts[i : i + _BATCH_SIZE]
        response = await litellm.aembedding(
            model=model,
            input=batch,
            dimensions=dimensions,
        )
        for item in response.data:
            all_embeddings.append(item["embedding"])

    return all_embeddings


async def embed_single(
    text: str,
    model: str = "text-embedding-3-small",
    dimensions: int = 1536,
) -> list[float]:
    """Convenience wrapper for a single text."""
    results = await embed_texts([text], model=model, dimensions=dimensions)
    return results[0]
