#!/usr/bin/env python3
"""Three-panel figure for structural grounding results.

Panel A (Taxonomy): Horizontal bar chart of mean |shift| by intervention category.
Panel B (Mechanism): LME predicted effects — model-specific grounding slopes.
Panel C (Topology): Edge path relevance scatter with Model B fit line.

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
from matplotlib.patches import Patch

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
COLORS = {
    "Llama-3.1-8B": "#E69F00",
    "Llama-3.3-70B": "#0072B2",
    "DeepSeek-V3": "#D55E00",
    "Qwen3-235B": "#009E73",
    "Gemini-Flash-Lite": "#CC79A7",
    "GPT-OSS-120B": "#882255",
}

# Intervention category colors
CAT_COLORS = {
    "Strengthen": "#009E73",           # green
    "Negate": "#D55E00",               # vermillion
    "Structural Challenge": "#CC79A7", # reddish purple
    "Control": "#999999",              # gray
}

# Probe type → intervention category mapping
INTERVENTION_MAP = {
    "node_strengthen": "Strengthen",
    "node_strengthen_medium": "Strengthen",
    "node_strengthen_low": "Strengthen",
    "edge_strengthen_critical": "Strengthen",
    "edge_strengthen_peripheral": "Strengthen",
    "node_negate_high": "Negate",
    "node_negate_medium": "Negate",
    "node_negate_low": "Negate",
    "edge_negate_critical": "Negate",
    "edge_negate_peripheral": "Negate",
    "edge_spurious": "Structural Challenge",
    "missing_node": "Structural Challenge",
    "edge_reverse": "Structural Challenge",
    "irrelevant": "Control",
}

PROBE_TYPE_NORMALIZE = {
    "irlevant": "irrelevant", "edge_missing": "edge_spurious", "edge_omitted": "edge_spurious",
    "edge_added": "edge_spurious", "edge_addition": "edge_spurious", "edge_add": "edge_spurious",
    "edge_add_causal": "edge_spurious", "edge_add_direct": "edge_spurious",
    "edge_feedback": "edge_spurious", "edge_fabricate": "edge_spurious",
}

MODEL_DIRS = {
    "Llama-3.1-8B": CAUSAL_DIR / "llama_neutral",
    "Llama-3.3-70B": CAUSAL_DIR / "llama_70b_neutral",
    "DeepSeek-V3": CAUSAL_DIR / "deepseek_neutral",
    "Qwen3-235B": CAUSAL_DIR / "qwen_neutral",
    "Gemini-Flash-Lite": CAUSAL_DIR / "gemini_flash_lite_neutral",
    "GPT-OSS-120B": CAUSAL_DIR / "gpt_oss_neutral",
}

REFERENCE_MODEL = "Llama-3.3-70B"


def _short_model_name(name):
    return {"Llama-3.1-8B": "Llama 8B", "Llama-3.3-70B": "Llama 70B",
            "DeepSeek-V3": "DeepSeek V3", "Qwen3-235B": "Qwen3 235B",
            "Gemini-Flash-Lite": "Gemini FL"}.get(name, name)


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


# ═══════════════════════════════════════════════════════════════════════════
# PANEL A: Intervention Taxonomy Bar Chart
# ═══════════════════════════════════════════════════════════════════════════

def panel_a(ax, rows):
    """Horizontal bar chart of mean |shift| by intervention category, split by node/edge."""
    # Map probe types to (category, level)
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
        pt = PROBE_TYPE_NORMALIZE.get(r.get("probe_type", ""), r.get("probe_type", ""))
        mapping = LEVEL_MAP.get(pt)
        if mapping:
            cat, level = mapping
            group_shifts[(cat, level)].append(r["absolute_shift"])

    # Define display order: group by category, node before edge within each
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
        ax.text(m + (hi - m) + 0.002, i, f"n={len(vals)}", va="center",
                fontsize=7, color="#555555")

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel("Mean |Probability Shift|")
    ax.axvline(x=0, color="#333333", linewidth=0.8, linestyle="--", zorder=0)
    ax.set_xlim(left=0)


# ═══════════════════════════════════════════════════════════════════════════
# SHARED: Model-specific predicted effects panel
# ═══════════════════════════════════════════════════════════════════════════

def _plot_model_slopes(ax, lme_model, xlabel, x_lo=-2, x_hi=3):
    """Plot per-model regression lines with 95% CI bands from LME results."""
    if lme_model is None:
        ax.text(0.5, 0.5, "No results", ha="center", va="center",
                transform=ax.transAxes)
        return

    slopes = lme_model.get("per_model_slopes", {})
    if not slopes:
        ax.text(0.5, 0.5, "No per-model slopes", ha="center", va="center",
                transform=ax.transAxes)
        return

    x_range = np.linspace(x_lo, x_hi, 100)

    for model_name in COLORS:
        if model_name not in slopes:
            continue
        s = slopes[model_name]
        intercept = s["intercept"]
        slope = s["slope"]
        slope_se = s["slope_se"]

        y_pred = intercept + slope * x_range
        ax.plot(x_range, y_pred, color=COLORS[model_name], linewidth=2,
                label=_short_model_name(model_name), zorder=3)

        # CI band based on slope uncertainty
        y_lo = intercept + (slope - 1.96 * slope_se) * x_range
        y_hi = intercept + (slope + 1.96 * slope_se) * x_range
        ax.fill_between(x_range, y_lo, y_hi,
                        color=COLORS[model_name], alpha=0.12, zorder=1)

    ax.set_xlabel(xlabel)
    ax.set_ylabel("Predicted |$\\Delta$|")
    ax.legend(frameon=False, fontsize=8, loc="upper left")


# ═══════════════════════════════════════════════════════════════════════════
# PANEL B: Node Betweenness (Model A)
# ═══════════════════════════════════════════════════════════════════════════

def panel_b(ax, lme_results):
    """LME predicted effects: model-specific grounding slopes from Model A."""
    _plot_model_slopes(ax, lme_results.get("model_a"),
                       "Betweenness Centrality (z-scored)")


# ═══════════════════════════════════════════════════════════════════════════
# PANEL C: Path Relevance (Model B)
# ═══════════════════════════════════════════════════════════════════════════

def panel_c(ax, lme_results):
    """LME predicted effects: model-specific path relevance slopes from Model B."""
    _plot_model_slopes(ax, lme_results.get("model_b"),
                       "Path Relevance (z-scored)")


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

    # Create figure
    fig = plt.figure(figsize=(16, 4.5))
    gs = fig.add_gridspec(1, 3, width_ratios=[0.8, 1.0, 1.0], wspace=0.38)
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1])
    ax3 = fig.add_subplot(gs[2])

    panel_a(ax1, rows)
    panel_b(ax2, lme_results)
    panel_c(ax3, lme_results)

    # Shared y-axis scale for (b) and (c)
    y_lo = min(ax2.get_ylim()[0], ax3.get_ylim()[0])
    y_hi = max(ax2.get_ylim()[1], ax3.get_ylim()[1])
    margin = (y_hi - y_lo) * 0.15
    shared_lim = (max(y_lo - margin, 0), y_hi + margin)
    ax2.set_ylim(shared_lim)
    ax3.set_ylim(shared_lim)

    _label_axes([ax1, ax2, ax3])

    OUT.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT / f"probe_effects.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("Saved probe_effects.pdf/png")


if __name__ == "__main__":
    main()
