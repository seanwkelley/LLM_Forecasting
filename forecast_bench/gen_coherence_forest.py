#!/usr/bin/env python3
"""Coherence forest plot: per-model LME slopes for all four coherence measures.

Four panels, each a horizontal forest plot showing per-model slopes with 95% CIs.
  (a) Stated-impact rating → |logit shift|
  (b) Uncertainty (numeric) → |logit shift|
  (c) Initial logit → signed logit shift (Bayesian coherence)
  (d) Structural vs Control embedding similarity

Reads per-model slopes from the interaction models in lme_results.json.

Usage:
    python -m forecast_bench.gen_coherence_forest
"""

import json
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).parent.parent))

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

MODEL_COLORS = {
    "Llama-3.1-8B": "#E69F00",
    "Llama-3.3-70B": "#0072B2",
    "DeepSeek-V3": "#D55E00",
    "Qwen3-235B": "#009E73",
    "Gemini-Flash-Lite": "#CC79A7",
    "GPT-OSS-120B": "#882255",
    "Qwen3-32B": "#56B4E9",
}

SHORT_NAMES = {
    "Llama-3.1-8B": "Llama 8B",
    "Llama-3.3-70B": "Llama 70B",
    "DeepSeek-V3": "DeepSeek V3",
    "Qwen3-235B": "Qwen3 235B",
    "Gemini-Flash-Lite": "Gemini FL",
    "GPT-OSS-120B": "GPT-OSS 120B",
    "Qwen3-32B": "Qwen3 32B",
}


def _stars(p):
    if p < 0.001:
        return "***"
    elif p < 0.01:
        return "**"
    elif p < 0.05:
        return "*"
    return ""


def _forest_panel(ax, slopes, title, xlabel, sort_descending=True):
    """Draw a single forest plot panel.

    slopes: dict model_name → {slope, slope_se, slope_ci_lower, slope_ci_upper, p_vs_zero}
    """
    if not slopes:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        return

    model_order = sorted(
        slopes.keys(),
        key=lambda m: slopes[m]["slope"],
        reverse=sort_descending,
    )

    n = len(model_order)
    y_pos = np.arange(n)

    for i, model_name in enumerate(model_order):
        s = slopes[model_name]
        color = MODEL_COLORS.get(model_name, "#333333")
        p = s.get("p_vs_zero", 1.0)
        stars = _stars(p)

        ax.errorbar(
            s["slope"], i,
            xerr=[[s["slope"] - s["slope_ci_lower"]],
                   [s["slope_ci_upper"] - s["slope"]]],
            fmt="o", color=color, markersize=8, capsize=4, capthick=1.2,
            linewidth=1.5, markeredgecolor="white", markeredgewidth=0.5, zorder=3,
        )

        # Significance stars to the right of the CI
        if stars:
            ax.text(s["slope_ci_upper"] + (ax.get_xlim()[1] - ax.get_xlim()[0]) * 0.01,
                    i, stars, va="center", ha="left", fontsize=10, fontweight="bold",
                    color=color)

    ax.axvline(x=0, color="#333333", linewidth=0.8, linestyle="--", zorder=0)

    ax.set_yticks(y_pos)
    ax.set_yticklabels([SHORT_NAMES.get(m, m) for m in model_order], fontsize=10)
    ax.set_xlabel(xlabel)
    ax.set_title(title, fontsize=12, fontweight="bold")

    # Add significance stars after setting xlim
    ax.figure.canvas.draw()


def main():
    lme_path = CAUSAL_DIR / "lme_results.json"
    if not lme_path.exists():
        print(f"[ERROR] No LME results at {lme_path}")
        print("Run: python -m forecast_bench.lme_analysis")
        sys.exit(1)

    lme = json.loads(lme_path.read_text(encoding="utf-8"))

    # Extract per-model slopes from interaction models
    panels = [
        {
            "key": "coherence_reasoning_interaction",
            "title": "Stated-Impact Rating",
            "xlabel": r"$\beta$ (|logit shift| per rating point)",
            "sort_desc": True,
        },
        {
            "key": "coherence_uncertainty_interaction",
            "title": "Uncertainty",
            "xlabel": r"$\beta$ (|logit shift| per uncertainty level)",
            "sort_desc": False,  # More negative = stronger effect
        },
        {
            "key": "coherence_bayesian_interaction",
            "title": "Bayesian Coherence",
            "xlabel": r"$\beta$ (logit shift per initial logit)",
            "sort_desc": False,  # Negative = regression to mean
        },
        {
            "key": "coherence_embedding_interaction",
            "title": "Embedding Separation",
            "xlabel": r"$\beta$ (cosine sim: structural $-$ control)",
            "sort_desc": True,
        },
    ]

    fig, axes = plt.subplots(2, 2, figsize=(14, 10),
                              gridspec_kw={"hspace": 0.45, "wspace": 0.50})
    axes_flat = axes.flatten()

    for ax, panel_info, label in zip(axes_flat, panels, ["(a)", "(b)", "(c)", "(d)"]):
        result = lme.get(panel_info["key"])
        slopes = result.get("per_model_slopes", {}) if result else {}

        _forest_panel(ax, slopes, panel_info["title"], panel_info["xlabel"],
                      sort_descending=panel_info["sort_desc"])

        ax.text(-0.02, 1.05, label, transform=ax.transAxes,
                fontsize=14, fontweight="bold", va="bottom", ha="right")

    # Second pass: add significance stars now that xlim is set
    for ax, panel_info in zip(axes_flat, panels):
        result = lme.get(panel_info["key"])
        slopes = result.get("per_model_slopes", {}) if result else {}
        if not slopes:
            continue

        model_order = sorted(
            slopes.keys(),
            key=lambda m: slopes[m]["slope"],
            reverse=panel_info["sort_desc"],
        )

        xleft, xright = ax.get_xlim()
        x_range = xright - xleft
        for i, model_name in enumerate(model_order):
            s = slopes[model_name]
            p = s.get("p_vs_zero", 1.0)
            stars = _stars(p)
            if stars:
                ax.text(s["slope_ci_upper"] + x_range * 0.02,
                        i, stars, va="center", ha="left", fontsize=10, fontweight="bold",
                        color=MODEL_COLORS.get(model_name, "#333333"))

    OUT.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT / f"coherence_forest.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("Saved coherence_forest.png/pdf")


if __name__ == "__main__":
    main()
