#!/usr/bin/env python3
"""CLARKE vs Raw LLM — Head-to-head evaluation.

Compares:
  A) Raw LLM: All documents stuffed into prompt (truncated at context limit)
  B) CLARKE: Selective retrieval via /query endpoint

Measures: token efficiency, latency, hallucination rate, correctness.

Usage:
    python scripts/run_eval_comparison.py --size small     # 10 questions
    python scripts/run_eval_comparison.py --size medium    # 50 questions
    python scripts/run_eval_comparison.py --size full      # all questions
    python scripts/run_eval_comparison.py --corpus evals/corpus --base-url http://localhost:8000
"""

import argparse
import asyncio
import json
import time
from dataclasses import dataclass
from pathlib import Path

import httpx
import litellm

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DEFAULT_MODEL = "gpt-4o-mini"
MAX_CONTEXT_TOKENS = 120000  # model context window for raw stuffing
TENANT_ID = "t_eval"
PROJECT_ID = "p_eval"

SIZES = {"small": 10, "medium": 50, "full": 999}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class QueryResult:
    question_id: str
    query: str
    gold_answer: str
    source_docs: list[str]
    category: str
    # Raw LLM results
    raw_answer: str = ""
    raw_input_tokens: int = 0
    raw_output_tokens: int = 0
    raw_latency_ms: int = 0
    raw_hallucination_count: int = 0
    raw_correctness: float = 0.0
    # CLARKE results
    clarke_answer: str = ""
    clarke_input_tokens: int = 0
    clarke_output_tokens: int = 0
    clarke_latency_ms: int = 0
    clarke_hallucination_count: int = 0
    clarke_correctness: float = 0.0
    clarke_retrieved_count: int = 0


@dataclass
class EvalSummary:
    total_questions: int = 0
    # Raw LLM
    raw_total_input_tokens: int = 0
    raw_total_output_tokens: int = 0
    raw_mean_latency_ms: float = 0.0
    raw_p95_latency_ms: float = 0.0
    raw_hallucination_rate: float = 0.0
    raw_mean_correctness: float = 0.0
    # CLARKE
    clarke_total_input_tokens: int = 0
    clarke_total_output_tokens: int = 0
    clarke_mean_latency_ms: float = 0.0
    clarke_p95_latency_ms: float = 0.0
    clarke_hallucination_rate: float = 0.0
    clarke_mean_correctness: float = 0.0
    clarke_mean_retrieved: float = 0.0
    # Deltas
    token_savings_pct: float = 0.0
    latency_delta_ms: float = 0.0
    hallucination_reduction_pct: float = 0.0
    correctness_delta: float = 0.0


# ---------------------------------------------------------------------------
# Corpus loading
# ---------------------------------------------------------------------------


def load_corpus(corpus_dir: str) -> tuple[dict[str, str], list[dict]]:
    """Load documents and questions. Returns (doc_contents, questions)."""
    corpus_path = Path(corpus_dir)

    # Load documents
    docs: dict[str, str] = {}
    docs_dir = corpus_path / "documents"
    for f in sorted(docs_dir.glob("*.md")):
        docs[f.name] = f.read_text()

    # Load questions
    with open(corpus_path / "questions.json") as f:
        questions = json.load(f)["questions"]

    return docs, questions


def build_raw_prompt(docs: dict[str, str], max_tokens: int = MAX_CONTEXT_TOKENS) -> str:
    """Concatenate all documents into a single prompt, truncating at limit."""
    parts = []
    token_count = 0
    for name, content in docs.items():
        doc_tokens = len(content) // 4  # rough estimate
        if token_count + doc_tokens > max_tokens:
            parts.append(
                f"\n[TRUNCATED: {len(docs) - len(parts)} documents omitted due to context limit]\n"
            )
            break
        parts.append(f"--- Document: {name} ---\n{content}\n")
        token_count += doc_tokens
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Correctness scoring — LLM judge against source documents
# ---------------------------------------------------------------------------


async def score_correctness_llm(
    query: str, answer: str, source_text: str, model: str = DEFAULT_MODEL
) -> float:
    """Score correctness using LLM judge against actual source documents."""
    if not answer or not answer.strip():
        return 0.0
    if not source_text:
        # No source docs — correct if answer says "no information available"
        no_info_phrases = [
            "don't have",
            "no information",
            "not available",
            "no context",
            "cannot find",
        ]
        return 1.0 if any(p in answer.lower() for p in no_info_phrases) else 0.3

    prompt = f"""You are scoring the correctness of an answer against source documents.

## Question
{query}

## Source Documents (ground truth)
{source_text[:12000]}

## Answer to Score
{answer}

## Scoring Rules
- Score 1.0: Answer correctly addresses the question using facts from the source documents.
- Score 0.75: Answer is mostly correct but missing some details or slightly imprecise.
- Score 0.5: Answer is partially correct — some right, some wrong or missing key points.
- Score 0.25: Answer is mostly wrong or addresses the question poorly.
- Score 0.0: Answer is completely wrong or unrelated.
- An answer that correctly says "I don't have this information" when the sources genuinely don't cover the topic scores 0.75.

Respond with ONLY a JSON object: {{"score": <float>, "reason": "<brief explanation>"}}"""

    try:
        response = await litellm.acompletion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            timeout=30,
        )
        content = response.choices[0].message.content or "{}"
        parsed = json.loads(content)
        return round(float(parsed.get("score", 0.5)), 4)
    except Exception:
        return 0.5  # default on failure


# ---------------------------------------------------------------------------
# Execution paths
# ---------------------------------------------------------------------------


async def run_raw_llm(query: str, raw_prompt: str, model: str = DEFAULT_MODEL) -> dict:
    """Path A: Raw LLM with all documents stuffed in prompt."""
    start = time.time()
    try:
        response = await litellm.acompletion(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": f"Answer based on the following documents:\n\n{raw_prompt}",
                },
                {"role": "user", "content": query},
            ],
            temperature=0.0,
            timeout=120,
        )
        latency_ms = int((time.time() - start) * 1000)
        usage = response.usage
        return {
            "answer": response.choices[0].message.content or "",
            "input_tokens": getattr(usage, "prompt_tokens", 0),
            "output_tokens": getattr(usage, "completion_tokens", 0),
            "latency_ms": latency_ms,
        }
    except Exception as e:
        return {
            "answer": f"Error: {e}",
            "input_tokens": 0,
            "output_tokens": 0,
            "latency_ms": int((time.time() - start) * 1000),
        }


def run_clarke(query: str, base_url: str) -> dict:
    """Path B: CLARKE selective retrieval."""
    start = time.time()
    try:
        with httpx.Client(base_url=base_url, timeout=120.0) as client:
            response = client.post(
                "/query",
                json={
                    "tenant_id": TENANT_ID,
                    "project_id": PROJECT_ID,
                    "user_id": "eval_user",
                    "session_id": "eval_session",
                    "message": query,
                },
            )
            latency_ms = int((time.time() - start) * 1000)

            if response.status_code != 200:
                return {
                    "answer": f"HTTP {response.status_code}",
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "latency_ms": latency_ms,
                    "retrieved_count": 0,
                }

            data = response.json()
            request_id = data.get("request_id", "")

            # Fetch episode for token data
            ep_resp = client.get(f"/admin/episodes/{request_id}")
            episode = ep_resp.json() if ep_resp.status_code == 200 else {}
            retrieved = episode.get("retrieved_items") or []
            injected = episode.get("injected_items") or []

            # Estimate tokens from injected items
            injected_text = " ".join(
                item.get("summary", "") if isinstance(item, dict) else "" for item in injected
            )
            est_input_tokens = len(injected_text) // 4 + 500  # +500 for system prompt

            return {
                "answer": data.get("answer", ""),
                "input_tokens": est_input_tokens,
                "output_tokens": len(data.get("answer", "")) // 4,
                "latency_ms": latency_ms,
                "retrieved_count": len(retrieved),
            }
    except Exception as e:
        return {
            "answer": f"Error: {e}",
            "input_tokens": 0,
            "output_tokens": 0,
            "latency_ms": int((time.time() - start) * 1000),
            "retrieved_count": 0,
        }


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------


def ingest_corpus(docs: dict[str, str], base_url: str) -> None:
    """Ingest all documents into CLARKE via /ingest endpoint."""
    print(f"\nIngesting {len(docs)} documents into CLARKE...")
    with httpx.Client(base_url=base_url, timeout=120.0) as client:
        for i, (name, content) in enumerate(docs.items()):
            resp = client.post(
                "/ingest",
                json={
                    "tenant_id": TENANT_ID,
                    "project_id": PROJECT_ID,
                    "filename": name,
                    "content_type": "text/markdown",
                    "content": content,
                },
            )
            status = "OK" if resp.status_code == 200 else f"FAIL({resp.status_code})"
            if (i + 1) % 25 == 0 or i == 0:
                print(f"  [{i + 1}/{len(docs)}] {name}: {status}")
    print("  Ingestion complete.")


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------


async def run_evaluation(
    corpus_dir: str,
    base_url: str,
    size: str,
    output_dir: str,
    model: str,
    skip_ingest: bool,
) -> None:
    docs, questions = load_corpus(corpus_dir)
    max_q = SIZES.get(size, len(questions))
    questions = questions[:max_q]

    print("\nCLARKE Evaluation — Raw LLM vs Brokered Retrieval")
    print(f"Corpus: {len(docs)} documents")
    print(f"Questions: {len(questions)}")
    print(f"Model: {model}")
    print("=" * 60)

    # Build raw prompt (all docs concatenated)
    raw_prompt = build_raw_prompt(docs)
    raw_prompt_tokens = len(raw_prompt) // 4
    print(f"Raw prompt size: ~{raw_prompt_tokens:,} tokens")

    # Ingest into CLARKE
    if not skip_ingest:
        ingest_corpus(docs, base_url)

    # Run evaluations
    results: list[QueryResult] = []

    for i, q in enumerate(questions):
        print(f"\n[{i + 1}/{len(questions)}] {q['query'][:60]}...")

        qr = QueryResult(
            question_id=q["id"],
            query=q["query"],
            gold_answer=q["gold_answer"],
            source_docs=q["source_docs"],
            category=q["category"],
        )

        # Path A: Raw LLM
        print("  Raw LLM... ", end="", flush=True)
        raw = await run_raw_llm(q["query"], raw_prompt, model)
        qr.raw_answer = raw["answer"]
        qr.raw_input_tokens = raw["input_tokens"]
        qr.raw_output_tokens = raw["output_tokens"]
        qr.raw_latency_ms = raw["latency_ms"]
        print(f"{raw['latency_ms']}ms, {raw['input_tokens']} in / {raw['output_tokens']} out")

        # Path B: CLARKE
        print("  CLARKE...  ", end="", flush=True)
        clarke = run_clarke(q["query"], base_url)
        qr.clarke_answer = clarke["answer"]
        qr.clarke_input_tokens = clarke["input_tokens"]
        qr.clarke_output_tokens = clarke["output_tokens"]
        qr.clarke_latency_ms = clarke["latency_ms"]
        qr.clarke_retrieved_count = clarke.get("retrieved_count", 0)
        print(
            f"{clarke['latency_ms']}ms, {clarke['input_tokens']} in / {clarke['output_tokens']} out, {clarke.get('retrieved_count', 0)} retrieved"
        )

        # Score correctness — LLM judge against source documents (fair for both)
        source_text = "\n\n".join(docs.get(d, "") for d in q["source_docs"])
        print("  Scoring correctness... ", end="", flush=True)
        qr.raw_correctness = await score_correctness_llm(
            q["query"], raw["answer"], source_text, model
        )
        qr.clarke_correctness = await score_correctness_llm(
            q["query"], clarke["answer"], source_text, model
        )
        print(f"raw={qr.raw_correctness:.2f}, clarke={qr.clarke_correctness:.2f}")
        if source_text:
            from scripts.eval_hallucination_judge import judge_hallucination

            print("  Judging hallucinations... ", end="", flush=True)
            raw_judge = await judge_hallucination(raw["answer"], source_text, model)
            clarke_judge = await judge_hallucination(clarke["answer"], source_text, model)
            qr.raw_hallucination_count = raw_judge["hallucination_count"]
            qr.clarke_hallucination_count = clarke_judge["hallucination_count"]
            print(
                f"raw={raw_judge['hallucination_count']}, clarke={clarke_judge['hallucination_count']}"
            )

        results.append(qr)

    # Compute summary
    summary = compute_summary(results)
    print_summary(summary)

    # Save results
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    results_data = [vars(r) for r in results]
    results_path = output / "comparison_results.json"
    with open(results_path, "w") as f:
        json.dump({"summary": vars(summary), "results": results_data}, f, indent=2, default=str)
    print(f"\nResults saved: {results_path}")

    # Generate HTML report
    from scripts.eval_report import generate_comparison_report

    report_path = output / "comparison_report.html"
    generate_comparison_report(summary, results, str(report_path))
    print(f"Report: {report_path}")


def compute_summary(results: list[QueryResult]) -> EvalSummary:
    """Compute aggregate statistics."""
    n = len(results)
    if n == 0:
        return EvalSummary()

    raw_latencies = sorted([r.raw_latency_ms for r in results])
    clarke_latencies = sorted([r.clarke_latency_ms for r in results])

    raw_total_in = sum(r.raw_input_tokens for r in results)
    raw_total_out = sum(r.raw_output_tokens for r in results)
    clarke_total_in = sum(r.clarke_input_tokens for r in results)
    clarke_total_out = sum(r.clarke_output_tokens for r in results)

    raw_halluc = sum(1 for r in results if r.raw_hallucination_count > 0)
    clarke_halluc = sum(1 for r in results if r.clarke_hallucination_count > 0)

    raw_total = raw_total_in + raw_total_out
    clarke_total = clarke_total_in + clarke_total_out

    return EvalSummary(
        total_questions=n,
        raw_total_input_tokens=raw_total_in,
        raw_total_output_tokens=raw_total_out,
        raw_mean_latency_ms=sum(raw_latencies) / n,
        raw_p95_latency_ms=raw_latencies[int(n * 0.95)] if n > 1 else raw_latencies[0],
        raw_hallucination_rate=raw_halluc / n,
        raw_mean_correctness=sum(r.raw_correctness for r in results) / n,
        clarke_total_input_tokens=clarke_total_in,
        clarke_total_output_tokens=clarke_total_out,
        clarke_mean_latency_ms=sum(clarke_latencies) / n,
        clarke_p95_latency_ms=clarke_latencies[int(n * 0.95)] if n > 1 else clarke_latencies[0],
        clarke_hallucination_rate=clarke_halluc / n,
        clarke_mean_correctness=sum(r.clarke_correctness for r in results) / n,
        clarke_mean_retrieved=sum(r.clarke_retrieved_count for r in results) / n,
        token_savings_pct=round((1 - clarke_total / max(raw_total, 1)) * 100, 1),
        latency_delta_ms=round(sum(clarke_latencies) / n - sum(raw_latencies) / n, 0),
        hallucination_reduction_pct=round((1 - clarke_halluc / max(raw_halluc, 1)) * 100, 1)
        if raw_halluc > 0
        else 0.0,
        correctness_delta=round(
            sum(r.clarke_correctness for r in results) / n
            - sum(r.raw_correctness for r in results) / n,
            4,
        ),
    )


def print_summary(s: EvalSummary) -> None:
    print("\n" + "=" * 60)
    print("EVALUATION RESULTS")
    print("=" * 60)
    print(f"Questions evaluated: {s.total_questions}")
    print()
    print(f"{'Metric':<30} {'Raw LLM':>15} {'CLARKE':>15} {'Delta':>15}")
    print("-" * 75)
    print(
        f"{'Total input tokens':<30} {s.raw_total_input_tokens:>15,} {s.clarke_total_input_tokens:>15,} {s.token_savings_pct:>14.1f}% saved"
    )
    print(
        f"{'Total output tokens':<30} {s.raw_total_output_tokens:>15,} {s.clarke_total_output_tokens:>15,}"
    )
    print(
        f"{'Mean latency (ms)':<30} {s.raw_mean_latency_ms:>15,.0f} {s.clarke_mean_latency_ms:>15,.0f} {s.latency_delta_ms:>+14.0f}ms"
    )
    print(
        f"{'p95 latency (ms)':<30} {s.raw_p95_latency_ms:>15,.0f} {s.clarke_p95_latency_ms:>15,.0f}"
    )
    print(
        f"{'Hallucination rate':<30} {s.raw_hallucination_rate:>14.1%} {s.clarke_hallucination_rate:>14.1%} {s.hallucination_reduction_pct:>14.1f}% reduced"
    )
    print(
        f"{'Mean correctness':<30} {s.raw_mean_correctness:>15.3f} {s.clarke_mean_correctness:>15.3f} {s.correctness_delta:>+14.3f}"
    )
    print(f"{'Mean retrieved items':<30} {'N/A':>15} {s.clarke_mean_retrieved:>15.1f}")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="CLARKE vs Raw LLM Evaluation")
    parser.add_argument("--size", choices=["small", "medium", "full"], default="small")
    parser.add_argument("--corpus", default="evals/corpus")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--output", default="evals/results")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--skip-ingest", action="store_true", help="Skip document ingestion (if already done)"
    )
    args = parser.parse_args()

    asyncio.run(
        run_evaluation(
            corpus_dir=args.corpus,
            base_url=args.base_url,
            size=args.size,
            output_dir=args.output,
            model=args.model,
            skip_ingest=args.skip_ingest,
        )
    )


if __name__ == "__main__":
    main()
