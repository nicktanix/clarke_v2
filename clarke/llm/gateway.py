"""LLM gateway wrapping LiteLLM with retry and fallback."""

import asyncio

import litellm

from clarke.llm.contracts import LLMResponse, TokenUsage
from clarke.settings import LLMSettings
from clarke.telemetry.logging import get_logger
from clarke.utils.time import ms_since, utc_now

logger = get_logger(__name__)

# Fallback model chain — if primary fails, try these in order
_FALLBACK_MODELS = ["gpt-4o-mini", "gpt-3.5-turbo"]


class LLMGateway:
    def __init__(
        self,
        settings: LLMSettings,
        max_retries: int = 3,
        retry_delay_s: float = 1.0,
    ) -> None:
        self.settings = settings
        self.max_retries = max_retries
        self.retry_delay_s = retry_delay_s
        if settings.litellm_master_key:
            litellm.api_key = settings.litellm_master_key
        litellm.drop_params = True

    async def call(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float | None = None,
    ) -> LLMResponse:
        model = model or self.settings.default_answer_model
        temperature = temperature if temperature is not None else self.settings.answer_temperature

        # Build model chain: primary model + fallbacks (excluding duplicates)
        models_to_try = [model]
        for fb in _FALLBACK_MODELS:
            if fb != model and fb not in models_to_try:
                models_to_try.append(fb)

        last_error: Exception | None = None

        for attempt_model in models_to_try:
            for attempt in range(self.max_retries):
                start = utc_now()
                try:
                    response = await litellm.acompletion(
                        model=attempt_model,
                        messages=messages,
                        temperature=temperature,
                        timeout=self.settings.request_timeout_ms / 1000,
                    )

                    latency = ms_since(start)
                    content = response.choices[0].message.content or ""
                    usage = response.usage

                    if attempt > 0 or attempt_model != model:
                        logger.info(
                            "llm_call_recovered",
                            model=attempt_model,
                            attempt=attempt + 1,
                            original_model=model,
                        )

                    return LLMResponse(
                        content=content,
                        model=attempt_model,
                        usage=TokenUsage(
                            input_tokens=getattr(usage, "prompt_tokens", 0),
                            output_tokens=getattr(usage, "completion_tokens", 0),
                        ),
                        latency_ms=latency,
                    )

                except Exception as e:
                    last_error = e
                    logger.warning(
                        "llm_call_retry",
                        model=attempt_model,
                        attempt=attempt + 1,
                        max_retries=self.max_retries,
                        error=str(e)[:200],
                    )
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay_s * (attempt + 1))

            logger.warning("llm_model_exhausted", model=attempt_model)

        # All models and retries exhausted
        logger.exception("llm_call_failed_all_models", models=models_to_try)
        if last_error:
            raise last_error
        raise RuntimeError("All LLM models and retries exhausted")
