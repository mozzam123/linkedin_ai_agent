import os
from functools import lru_cache

from langchain_groq import ChatGroq

from app.core.config import settings

# ── Defaults ───────────────────────────────────────────────────────────────────
# The Groq models available on this account are reasoning models (gpt-oss
# family). Without a token cap and an explicit reasoning effort they can spend
# 15-20s "thinking" before emitting a visible token, and with no timeout a
# stalled connection blocks the whole workflow indefinitely.
DEFAULT_TIMEOUT = 30      # seconds before a single request is abandoned
DEFAULT_RETRIES = 2       # retries on transient failures / rate limits
DEFAULT_MAX_TOKENS = 1200


def _api_key() -> str:
    """Read the key at call time so a key typed in the UI is picked up."""
    return os.getenv("GROQ_API_KEY") or settings.GROQ_API_KEY


def _model_name() -> str:
    return os.getenv("GROQ_MODEL") or settings.GROQ_MODEL or "qwen/qwen3.8-27b"


@lru_cache(maxsize=64)
def _build_llm(api_key, model, temperature, max_tokens, reasoning_effort):
    kwargs = {
        "model": model,
        "api_key": api_key,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "timeout": DEFAULT_TIMEOUT,
        "max_retries": DEFAULT_RETRIES,
    }
    # reasoning_effort is only accepted by the gpt-oss models
    if reasoning_effort and model.startswith("openai/gpt-oss"):
        kwargs["reasoning_effort"] = reasoning_effort
    return ChatGroq(**kwargs)


def get_llm(
    temperature: float = 0.7,
    *,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    reasoning_effort: str | None = None,
    model: str | None = None,
):
    """
    Returns a cached ChatGroq client.

    temperature       – 0.95 topic generation, 0.7 drafting/rewriting,
                        0.2 critique, 0.0 extraction
    max_tokens        – hard cap per response; keep it tight for utility calls
    reasoning_effort  – "low" for scoring/formatting/extraction (much faster),
                        None (provider default) for writing
    model             – override the configured model
    """
    return _build_llm(
        _api_key(),
        model or _model_name(),
        float(temperature),
        int(max_tokens),
        reasoning_effort,
    )
