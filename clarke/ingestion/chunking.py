"""Chunk splitter — token-bounded chunks with overlap."""

import re
from collections.abc import Callable
from dataclasses import dataclass

from clarke.llm.token_counting import count_tokens


@dataclass
class ChunkResult:
    content: str
    chunk_index: int
    token_count: int
    metadata: dict


_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")


def _split_at_sentences(text: str) -> list[str]:
    """Split text at sentence boundaries."""
    parts = _SENTENCE_BOUNDARY.split(text)
    return [p for p in parts if p.strip()]


def chunk_sections(
    sections: list,
    document_id: str,
    max_tokens: int = 512,
    overlap_tokens: int = 64,
    count_fn: Callable[[str, str], int] = count_tokens,
    model: str = "",
) -> list[ChunkResult]:
    """Split parsed sections into token-bounded chunks with overlap."""
    chunks: list[ChunkResult] = []
    chunk_idx = 0

    for section in sections:
        content = section.content
        tokens = count_fn(content, model)

        if tokens <= max_tokens:
            chunks.append(
                ChunkResult(
                    content=content,
                    chunk_index=chunk_idx,
                    token_count=tokens,
                    metadata={
                        "document_id": document_id,
                        "section_index": section.index,
                        "heading": section.heading,
                    },
                )
            )
            chunk_idx += 1
            continue

        # Split at sentence boundaries
        sentences = _split_at_sentences(content)
        if not sentences:
            sentences = content.split()

        current_parts: list[str] = []
        current_tokens = 0

        for sentence in sentences:
            s_tokens = count_fn(sentence, model)

            if current_tokens + s_tokens > max_tokens and current_parts:
                chunk_text = " ".join(current_parts)
                chunks.append(
                    ChunkResult(
                        content=chunk_text,
                        chunk_index=chunk_idx,
                        token_count=count_fn(chunk_text, model),
                        metadata={
                            "document_id": document_id,
                            "section_index": section.index,
                            "heading": section.heading,
                        },
                    )
                )
                chunk_idx += 1

                # Overlap: keep trailing sentences that fit in overlap budget
                overlap_parts: list[str] = []
                overlap_tok = 0
                for part in reversed(current_parts):
                    pt = count_fn(part, model)
                    if overlap_tok + pt > overlap_tokens:
                        break
                    overlap_parts.insert(0, part)
                    overlap_tok += pt

                current_parts = overlap_parts
                current_tokens = overlap_tok

            current_parts.append(sentence)
            current_tokens += s_tokens

        if current_parts:
            chunk_text = " ".join(current_parts)
            chunks.append(
                ChunkResult(
                    content=chunk_text,
                    chunk_index=chunk_idx,
                    token_count=count_fn(chunk_text, model),
                    metadata={
                        "document_id": document_id,
                        "section_index": section.index,
                        "heading": section.heading,
                    },
                )
            )
            chunk_idx += 1

    return chunks
