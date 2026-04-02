#!/usr/bin/env python3
"""Two-panel figure for structural grounding results.

Panel A (Taxonomy): Horizontal bar chart of mean |log-odds shift| by intervention
    category, split by Node/Edge level.
Panel B (Forest): Per-model LME slopes for betweenness centrality,
    tested against zero, from the log-odds interaction model.

Reads LME results from outputs/sensitivity/causal/lme_results.json.

Usage:
    python -m forecast_bench.gen_lme_figure
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).parent.parent))

# ── Style (matching figure_style_guide.md) ─────────────────────────────────
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 11,
    "axes.labelsize": 12,
    "axes.titlesize": 13,
    "legend.fontsize": 10,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.1,
    "mathtext.default": "regular",
    "axes.spines.top": False,
    "axes.spines.right": False,
})

BASE = Path(__file__).parent.parent
OUT = BASE / "paper" / "figures"
CAUSAL_DIR = BASE / "outputs" / "sensitivity" / "causal"

# ── Colors ─────────────────────────────────────────────────────────────────
MODEL_COLORS = {
    "Llama-3.1-8B": "#E69F00",
    "Llama-3.3-70B": "#0072B2",
    "DeepSeek-V3": "#D55E00",
    "Qwen3-235B": "#009E73",
    "Gemini-Flash-Lite": "#CC79A7",
    "GPT-OSS-120B": "#882255",
    "Qwen3-32B": "#56B4E9",
}

MODEL_DIRS = {
    "Llama-3.1-8B": CAUSAL_DIR / "llama_neutral",
    "Llama-3.3-70B": CAUSAL_DIR / "llama_70b_neutral",
    "DeepSeek-V3": CAUSAL_DIR / "deepseek_neutral",
    "Qwen3-235B": CAUSAL_DIR / "qwen_neutral",
    "Gemini-Flash-Lite": CAUSAL_DIR / "gemini_fl_neutral",
    "GPT-OSS-120B": CAUSAL_DIR / "gpt_oss_neutral",
    "Qwen3-32B": CAUSAL_DIR / "qwen_32b_neutral",
}

PROBE_TYPE_NORMALIZE = {
    "irlevant": "irrelevant", "edge_missing": "edge_spurious", "edge_omitted": "edge_spurious",
    "edge_added": "edge_spurious", "edge_addition": "edge_spurious", "edge_add": "edge_spurious",
    "edge_add_causal": "edge_spurious", "edge_add_direct": "edge_spurious",
    "edge_feedback": "edge_spurious", "edge_fabricate": "edge_spurious",
}


def _short_model_name(name):
    return {
        "Llama-3.1-8B": "Llama 8B",
        "Llama-3.3-70B": "Llama 70B",
        "DeepSeek-V3": "DeepSeek V3",
        "Qwen3-235B": "Qwen3 235B",
        "Gemini-Flash-Lite": "Gemini FL",
        "GPT-OSS-120B": "GPT-OSS",
        "Qwen3-32B": "Qwen3 32B",
    }.get(name, name)


def _label_axes(axes, fontsize=14):
    for i, ax in enumerate(axes):
        label = chr(ord("a") + i)
        ax.text(-0.02, 1.02, f"({label})", transform=ax.transAxes,
                fontsize=fontsize, fontweight="bold", va="bottom", ha="right")


def _load_all_rows():
    """Load all probe rows from all models."""
    from forecast_bench.analysis_causal import load_causal_results
    all_rows = []
    for name, d in MODEL_DIRS.items():
        csv_path = d / "sensitivity_results.csv"
        if not csv_path.exists():
            continue
        rows = load_causal_results(csv_path)
        for r in rows:
            r["model"] = name
        all_rows.extend(rows)
    return all_rows


def _bootstrap_mean_ci(vals, n_boot=10_000, seed=42):
    """Bootstrap mean with 95% CI."""
    rng = np.random.default_rng(seed)
    arr = np.array(vals)
    m = np.mean(arr)
    boots = np.array([np.mean(rng.choice(arr, size=len(arr))) for _ in range(n_boot)])
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return m, lo, hi


def _logit(p):
    eps = 1e-4
    p = np.clip(p, eps, 1 - eps)
    return np.log(p / (1 - p))


# ═══════════════════════════════════════════════════════════════════════════
# PANEL A: Intervention Taxonomy Bar Chart (log-odds shift)
# ═══════════════════════════════════════════════════════════════════════════

def panel_a(ax, rows):
    """Horizontal bar chart of mean |log-odds shift| by category, split by node/edge."""
    LEVEL_MAP = {
        "node_strengthen": ("Strengthen", "Node"),
        "node_strengthen_medium": ("Strengthen", "Node"),
        "node_strengthen_low": ("Strengthen", "Node"),
        "edge_strengthen_critical": ("Strengthen", "Edge"),
        "edge_strengthen_peripheral": ("Strengthen", "Edge"),
        "node_negate_high": ("Negate", "Node"),
        "node_negate_medium": ("Negate", "Node"),
        "node_negate_low": ("Negate", "Node"),
        "edge_negate_critical": ("Negate", "Edge"),
        "edge_negate_peripheral": ("Negate", "Edge"),
        "edge_spurious": ("Structural Challenge", "Edge"),
        "missing_node": ("Structural Challenge", "Node"),
        "edge_reverse": ("Structural Challenge", "Edge"),
        "irrelevant": ("Control", "Control"),
    }

    group_shifts = defaultdict(list)
    for r in rows:
        if not r.get("success") or r.get("absolute_shift") is None:
            continue
        p0 = r.get("initial_probability")
        p1 = r.get("updated_probability")
        if p0 is None or p1 is None:
            continue
        abs_logit = abs(_logit(p1) - _logit(p0))

        pt = PROBE_TYPE_NORMALIZE.get(r.get("probe_type", ""), r.get("probe_type", ""))
        mapping = LEVEL_MAP.get(pt)
        if mapping:
            cat, level = mapping
            group_shifts[(cat, level)].append(abs_logit)

    # Display order: group by category, node before edge
    category_order = ["Control", "Negate", "Structural Challenge", "Strengthen"]
    ordered = []
    for cat in category_order:
        for level in ["Edge", "Node", "Control"]:
            key = (cat, level)
            if key in group_shifts:
                ordered.append(key)

    labels = []
    for cat, level in ordered:
        if level == "Control":
            labels.append("Control")
        else:
            labels.append(f"{cat} ({level})")

    data = [group_shifts[k] for k in ordered]

    LEVEL_COLORS = {
        ("Strengthen", "Node"): "#006d5b",
        ("Strengthen", "Edge"): "#66c2a5",
        ("Negate", "Node"): "#b33000",
        ("Negate", "Edge"): "#f4a582",
        ("Structural Challenge", "Node"): "#8c4a6e",
        ("Structural Challenge", "Edge"): "#e0b0d0",
        ("Control", "Control"): "#999999",
    }

    y = np.arange(len(labels))
    for i, (key, vals) in enumerate(zip(ordered, data)):
        m, lo, hi = _bootstrap_mean_ci(vals)
        color = LEVEL_COLORS.get(key, "#999")
        ax.barh(i, m, color=color, edgecolor="none", height=0.6, alpha=0.85)
        ax.errorbar(m, i, xerr=[[m - lo], [hi - m]], color="black",
                    capsize=3, capthick=1.0, linewidth=1.0, fmt="none")

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel("Mean |Log-Odds Shift|")
    ax.axvline(x=0, color="#333333", linewidth=0.8, linestyle="--", zorder=0)
    ax.set_xlim(left=0)


# ═══════════════════════════════════════════════════════════════════════════
# PANEL B: Forest plot — per-model betweenness slopes
# ═══════════════════════════════════════════════════════════════════════════

def panel_b(ax, lme_results):
    """Forest plot: each model as a row, betweenness centrality slope + 95% CI."""
    model_a = lme_results.get("model_a_logit")

    if model_a is None:
        ax.text(0.5, 0.5, "No log-odds LME results", ha="center", va="center",
                transform=ax.transAxes)
        return

    slopes = model_a.get("per_model_slopes", {})

    # Sort by slope (descending)
    model_order = sorted(slopes.keys(), key=lambda m: slopes[m]["slope"], reverse=True)

    n_models = len(model_order)
    y_positions = np.arange(n_models)

    for i, model_name in enumerate(model_order):
        s = slopes[model_name]
        color = MODEL_COLORS.get(model_name, "#333333")

        ax.errorbar(
            s["slope"], i,
            xerr=[[s["slope"] - s["slope_ci_lower"]], [s["slope_ci_upper"] - s["slope"]]],
            fmt="o", color=color, markersize=8, capsize=4, capthick=1.2, linewidth=1.5,
            markeredgecolor="white", markeredgewidth=0.5, zorder=3,
        )

    # Zero line
    ax.axvline(x=0, color="#333333", linewidth=0.8, linestyle="--", zorder=0)

    # Y axis
    ax.set_yticks(y_positions)
    ax.set_yticklabels([_short_model_name(m) for m in model_order], fontsize=10)
    ax.set_xlabel("$\\beta_1$ (|log-odds shift| per SD betweenness)")

    # Add significance stars
    xleft, xright = ax.get_xlim()
    x_range = xright - xleft
    for i, model_name in enumerate(model_order):
        s = slopes[model_name]
        p = s.get("p_vs_zero", 1.0)
        stars = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
        if stars:
            ax.text(s["slope_ci_upper"] + x_range * 0.02, i,
                    stars, va="center", ha="left", fontsize=10, fontweight="bold",
                    color=MODEL_COLORS.get(model_name, "#333333"))

    ax.set_xlim(left=min(ax.get_xlim()[0], -0.02))


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    # Load LME results
    lme_path = CAUSAL_DIR / "lme_results.json"
    if not lme_path.exists():
        print(f"[ERROR] LME results not found at {lme_path}")
        print("  Run: python -m forecast_bench.lme_analysis")
        sys.exit(1)

    with open(lme_path, "r", encoding="utf-8") as f:
        lme_results = json.load(f)

    # Load all probe rows
    rows = _load_all_rows()
    print(f"Loaded {len(rows)} probe rows across {len(MODEL_DIRS)} models")

    # Create figure: 2 panels
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5),
                                    gridspec_kw={"width_ratios": [0.9, 1.1], "wspace": 0.35})

    panel_a(ax1, rows)
    panel_b(ax2, lme_results)

    _label_axes([ax1, ax2])

    OUT.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT / f"probe_effects.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("Saved probe_effects.pdf/png")


if __name__ == "__main__":
    main()
