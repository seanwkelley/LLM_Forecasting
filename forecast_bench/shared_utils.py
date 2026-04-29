"""Shared constants and utilities for figure/table generation scripts.

Extracted from `generate_figures.py` so individual `gen_*.py` / `analyze_*.py`
scripts don't need to import from the monolithic legacy module.
"""
from __future__ import annotations

from pathlib import Path

from forecast_bench.analysis_causal import load_causal_results
from forecast_bench.analysis_full import load_question_jsons

BASE = Path(__file__).parent.parent
CAUSAL_DIR = BASE / "outputs" / "sensitivity" / "causal"

MODEL_DIRS = {
    "Llama-3.1-8B":      CAUSAL_DIR / "llama_neutral",
    "Llama-3.3-70B":     CAUSAL_DIR / "llama_70b_neutral",
    "DeepSeek-V3":       CAUSAL_DIR / "deepseek_neutral",
    "Qwen3-235B":        CAUSAL_DIR / "qwen_neutral",
    "Gemini-Flash-Lite": CAUSAL_DIR / "gemini_fl_neutral",
    "GPT-OSS-120B":      CAUSAL_DIR / "gpt_oss_neutral",
    "Qwen3-32B":         CAUSAL_DIR / "qwen_32b_neutral",
}

# Colorblind-safe palette (Wong 2011 / IBM Design)
COLORS = {
    "Llama-3.1-8B":      "#E69F00",   # orange
    "Llama-3.3-70B":     "#0072B2",   # blue
    "DeepSeek-V3":       "#D55E00",   # vermillion
    "Qwen3-235B":        "#009E73",   # green
    "Gemini-Flash-Lite": "#CC79A7",   # reddish purple
    "GPT-OSS-120B":      "#882255",   # wine
    "Qwen3-32B":         "#56B4E9",   # sky blue
}

IMPORTANCE_TIER = {
    "node_negate_high":          "High",
    "node_strengthen":           "High",
    "edge_negate_critical":      "High",
    "edge_strengthen_critical":  "High",
    "node_negate_medium":        "Medium",
    "node_strengthen_medium":    "Medium",
    "node_negate_low":           "Low",
    "node_strengthen_low":       "Low",
    "edge_negate_peripheral":    "Low",
    "edge_strengthen_peripheral":"Low",
    "edge_reverse":              "Low",
    "edge_spurious":             "Control",
    "missing_node":              "Control",
    "irrelevant":                "Control",
}

# Normalize non-standard probe-type names from older/inconsistent runs
EMBED_PROBE_NORMALIZE = {
    "irlevant":         "irrelevant",
    "edge_missing":     "edge_spurious",
    "edge_omitted":     "edge_spurious",
    "edge_added":       "edge_spurious",
    "edge_addition":    "edge_spurious",
    "edge_add":         "edge_spurious",
    "edge_add_causal":  "edge_spurious",
    "edge_add_direct":  "edge_spurious",
    "edge_feedback":    "edge_spurious",
    "edge_fabricate":   "edge_spurious",
}

# Back-compat aliases for callers that used the leading-underscore names
_IMPORTANCE_TIER = IMPORTANCE_TIER
_EMBED_PROBE_NORMALIZE = EMBED_PROBE_NORMALIZE


def load_all_runs(verbose: bool = True) -> dict:
    """Load probe rows + per-question data for all 7 models."""
    runs = {}
    for name, d in MODEL_DIRS.items():
        csv_path = d / "sensitivity_results.csv"
        if not csv_path.exists():
            if verbose:
                print(f"  [SKIP] {name}: no CSV")
            continue
        rows = load_causal_results(csv_path)
        q_data = load_question_jsons(d)
        runs[name] = (rows, q_data)
        if verbose:
            print(f"  Loaded {name}: {len(rows)} probes, {len(q_data)} questions")
    return runs


# Back-compat alias
_load_all_runs = load_all_runs
