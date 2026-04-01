"""LLM-as-judge for hallucination detection.

Compares answer claims against source documents to identify unsupported claims.
"""

import asyncio
import json

import litellm


async def judge_hallucination(
    answer: str,
    source_text: str,
    model: str = "gpt-4o-mini",
) -> dict:
    """Judge whether an answer contains hallucinated claims.

    Returns: {"hallucination_count": int, "unsupported_claims": list[str], "score": float}
    """
    if not answer or not answer.strip():
        return {"hallucination_count": 0, "unsupported_claims": [], "score": 1.0}

    prompt = f"""You are a strict hallucination evaluator. Your job is to identify claims in an answer that are FABRICATED — meaning they assert specific facts that CANNOT be found anywhere in the source documents.

## Source Documents (ground truth)
{source_text[:16000]}

## Answer to Evaluate
{answer}

## Rules
- A claim is ONLY a hallucination if it asserts a specific fact that CONTRADICTS or is COMPLETELY ABSENT from the source documents.
- If a claim paraphrases, summarizes, or reasonably infers from the source content, it is NOT a hallucination.
- If a number, name, or configuration value appears in the source documents, citing it is NOT a hallucination even if the wording differs.
- General knowledge statements (e.g., "queues buffer messages") are NOT hallucinations — they are common domain knowledge.
- Saying "I don't have information" or "the context doesn't contain details" is NEVER a hallucination.
- Be conservative: when in doubt, a claim is NOT hallucinated.

## Task
1. Identify each specific factual claim in the answer.
2. Check if each claim is supported by OR reasonably inferable from the source documents.
3. Only flag claims that are clearly fabricated with no basis in the sources.

Respond in JSON:
{{"total_claims": <int>, "supported_claims": <int>, "unsupported_claims": ["claim1", "claim2"]}}"""

    try:
        response = await litellm.acompletion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            timeout=30,
        )
        content = response.choices[0].message.content or "{}"
        parsed = json.loads(content)

        total = max(parsed.get("total_claims", 1), 1)
        unsupported = parsed.get("unsupported_claims", [])
        score = (total - len(unsupported)) / total

        return {
            "hallucination_count": len(unsupported),
            "unsupported_claims": unsupported,
            "score": round(score, 4),
        }
    except Exception:
        return {"hallucination_count": 0, "unsupported_claims": [], "score": 1.0}


def judge_hallucination_sync(answer: str, source_text: str, model: str = "gpt-4o-mini") -> dict:
    """Synchronous wrapper."""
    return asyncio.run(judge_hallucination(answer, source_text, model))
