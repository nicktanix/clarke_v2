"""LLM response contracts."""

from enum import StrEnum

from pydantic import BaseModel


class ModelRole(StrEnum):
    ANSWER = "answer"
    REWRITER = "rewriter"
    EVALUATOR = "evaluator"
    CLASSIFIER = "classifier"


class TokenUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0


class LLMResponse(BaseModel):
    content: str
    model: str
    usage: TokenUsage = TokenUsage()
    latency_ms: int = 0
    structured_output: dict | None = None
