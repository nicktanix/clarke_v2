"""Token counting with tiktoken for OpenAI models, char fallback for unknown models.

Spec §23: tokenizer failure should fail closed on prompt assembly.
For known models that fail tokenizer init, raise rather than silently under-counting.
For genuinely unknown models, char estimate is the only option.
"""

import tiktoken

from clarke.telemetry.logging import get_logger

logger = get_logger(__name__)

_encoder_cache: dict[str, tiktoken.Encoding] = {}

# Models known to have tiktoken support — failure for these is unexpected
_KNOWN_MODELS = {
    "gpt-4",
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo",
    "gpt-3.5-turbo",
    "gpt-3.5-turbo-16k",
    "text-embedding-3-small",
    "text-embedding-3-large",
    "text-embedding-ada-002",
}


def _get_encoder(model: str) -> tiktoken.Encoding | None:
    """Get tiktoken encoder for model. Returns None if model not supported."""
    if not model:
        return None
    if model in _encoder_cache:
        return _encoder_cache[model]
    try:
        enc = tiktoken.encoding_for_model(model)
        _encoder_cache[model] = enc
        return enc
    except KeyError:
        return None


def count_tokens(text: str, model: str = "", strict: bool = False) -> int:
    """Count tokens using tiktoken for OpenAI models, char estimate for others.

    When strict=True and a known model's tokenizer fails, raises ValueError
    rather than silently falling back to char estimate (spec §23 fail-closed).
    """
    if not text:
        return 0
    encoder = _get_encoder(model)
    if encoder:
        return len(encoder.encode(text))

    # No encoder found — check if this is a known model (unexpected failure)
    if strict and model in _KNOWN_MODELS:
        raise ValueError(
            f"Tokenizer unavailable for known model '{model}'. "
            "Refusing to fall back to char estimate in strict mode."
        )

    # Genuinely unknown model — char estimate is the only option
    return len(text) // 4
