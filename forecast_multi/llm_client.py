"""
LLM Client — re-export from forecast_bench.llm_client.

All LLM interaction goes through the shared client to ensure consistent
retry logic, rate limiting, and stats tracking.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from forecast_bench.llm_client import CallStats, LLMClient, parse_json_response


# Model aliases for convenience
MODEL_ALIASES = {
    "llama": "meta-llama/llama-3.1-8b-instruct",
    "llama-70b": "meta-llama/llama-3.1-70b-instruct",
    "qwen": "qwen/qwen3-8b",
    "gemma": "google/gemma-2-9b-it",
}


def resolve_model(model: str) -> str:
    """Resolve a model alias to its full OpenRouter identifier."""
    return MODEL_ALIASES.get(model, model)


def parse_forecast_response(text: str) -> dict | None:
    """Parse an LLM forecast response into a dict with normalized probabilities.

    Handles thinking tags (Qwen), markdown code blocks, and malformed JSON.
    Returns dict with prob_up, prob_down, prob_flat, reasoning, and domain-specific
    point estimate keys, or None on failure.
    """
    # Strip thinking tags
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    data = parse_json_response(text)
    if data is None:
        return None

    # Extract and normalize probabilities
    try:
        prob_up = float(data.get("prob_up", 0.33))
        prob_down = float(data.get("prob_down", 0.33))
        prob_flat = float(data.get("prob_flat", 0.34))
    except (TypeError, ValueError):
        return None

    total = prob_up + prob_down + prob_flat
    if total <= 0:
        return None
    prob_up /= total
    prob_down /= total
    prob_flat /= total

    result = {
        "prob_up": round(prob_up, 4),
        "prob_down": round(prob_down, 4),
        "prob_flat": round(prob_flat, 4),
        "reasoning": str(data.get("reasoning", "")),
    }

    # Pass through domain-specific point estimates
    for key in ("predicted_price", "predicted_ei"):
        if key in data:
            try:
                result[key] = float(data[key])
            except (TypeError, ValueError):
                pass

    return result


__all__ = [
    "CallStats",
    "LLMClient",
    "parse_json_response",
    "parse_forecast_response",
    "resolve_model",
    "MODEL_ALIASES",
]
