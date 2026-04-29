"""Configuration for the agent-forecast pipeline.

Environment variables expected:
    OPENROUTER_API_KEY  - LLM access (paper uses OpenRouter for all 7 models)
    TAVILY_API_KEY      - web search (primary)
    SERPER_API_KEY      - web search (fallback, optional)
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path

BASE = Path(__file__).parent.parent.parent
OUT_DIR = BASE / "outputs" / "agent_forecast"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Models ─────────────────────────────────────────────────────────────────
# Mirrors the paper's 7-model set, but agentic search is gated to the
# stronger ones by default (weaker models struggle with tool-use formatting).
MODELS = {
    "Llama-3.3-70B":     "meta-llama/llama-3.3-70b-instruct",
    "DeepSeek-V3":       "deepseek/deepseek-chat-v3-0324",
    "Qwen3-235B":        "qwen/qwen3-235b-a22b-07-25",
    "GPT-OSS-120B":      "openai/gpt-oss-120b",
    "Gemini-Flash-Lite": "google/gemini-2.5-flash-lite",
}
# Opt-in secondary set (tool-use fragile but useful for completeness)
MODELS_SMALL = {
    "Llama-3.1-8B": "meta-llama/llama-3.1-8b-instruct",
    "Qwen3-32B":    "qwen/qwen3-32b",
}

# ── Conditions ─────────────────────────────────────────────────────────────
# peripheral_targeted mirrors topology_targeted but targets the bottom-k
# factors rather than the top-k, isolating the centrality effect from the
# decomposition-of-search effect.
CONDITIONS = ["no_search", "untargeted", "topology_targeted", "peripheral_targeted"]

# ── Agent budgets (held equal across conditions to isolate topology effect) ─
MAX_SEARCH_QUERIES = 8      # per question, per condition (except no_search)
MAX_RESULTS_PER_QUERY = 5   # top-k returned by search API
SEARCH_SNIPPET_CHARS = 400  # truncate each result snippet

# ── Topology-targeted search ────────────────────────────────────────────────
# How many top-betweenness factors to focus the search on
TOP_K_FACTORS = 3
# Allocate queries across selected factors (e.g., 3 factors * 2-3 queries each)
QUERIES_PER_FACTOR = 3

# ── Question selection ──────────────────────────────────────────────────────
# Only quantitative / data-anchored sources (answers not Google-able as prose)
ELIGIBLE_SOURCES = {"fred", "yfinance", "dbnomics", "acled", "wikipedia"}

# Resolution window: pull questions that resolve within this future window
RESOLUTION_WINDOW_DAYS_MIN = 14   # at least 2 weeks out
RESOLUTION_WINDOW_DAYS_MAX = 56   # at most 8 weeks out (configurable)

TODAY = datetime.utcnow().date()

# ── API keys (fail loudly if missing when needed) ───────────────────────────
def get_openrouter_key() -> str:
    k = os.environ.get("OPENROUTER_API_KEY")
    if not k:
        raise RuntimeError("OPENROUTER_API_KEY not set")
    return k

def get_tavily_key() -> str | None:
    return os.environ.get("TAVILY_API_KEY")

def get_serper_key() -> str | None:
    return os.environ.get("SERPER_API_KEY")
