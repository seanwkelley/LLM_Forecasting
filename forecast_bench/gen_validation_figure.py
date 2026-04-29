#!/usr/bin/env python3
"""Three-panel validation figure.

Panel A: Persuasiveness control — partial correlation survives controlling for persuasiveness
Panel B: Edge permutation — beta degrades when topology is shuffled
Panel C: Factor ranking null — models can't rank importance without DAG

Usage:
    python -m forecast_bench.gen_validation_figure
"""

import csv
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
OUT = BASE / "paper" / "figures" / "internal"  # validation figure replaced by tab:validation_summary in main paper
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
    "GPT-OSS-120B": "GPT-OSS",
    "Qwen3-32B": "Qwen3 32B",
}


def _label_axes(axes, fontsize=14):
    for i, ax in enumerate(axes):
        label = chr(ord("a") + i)
        ax.text(-0.02, 1.02, f"({label})", transform=ax.transAxes,
                fontsize=fontsize, fontweight="bold", va="bottom", ha="right")


# ═══════════════════════════════════════════════════════════════════════════
# PANEL A: Persuasiveness control
# ═══════════════════════════════════════════════════════════════════════════

def _logit(p):
    eps = 1e-4
    p = np.clip(p, eps, 1 - eps)
    return np.log(p / (1 - p))


def panel_a(ax):
    """Bar chart: raw vs partial correlation (controlling for persuasiveness)."""
    from scipy import stats

    # Load neutral persuasiveness ratings
    path = CAUSAL_DIR / "persuasiveness_ratings_neutral.csv"
    if not path.exists():
        ax.text(0.5, 0.5, "No persuasiveness data", ha="center", va="center",
                transform=ax.transAxes)
        return

    rows = list(csv.DictReader(open(path, encoding="utf-8")))

    importance = np.array([1 if r["importance"] == "high" else 0 for r in rows])
    persuasiveness = np.array([int(r["persuasiveness"]) for r in rows])
    shift = np.array([float(r["absolute_shift"]) for r in rows])

    # Use log-odds shift if initial/updated probabilities are available
    # Fall back to raw shift otherwise
    # TODO: update persuasiveness CSV to include probabilities for log-odds

    # Raw correlation
    rho_raw, p_raw = stats.spearmanr(importance, shift)

    # Partial: residualize both on persuasiveness
    def residualize(x, control):
        slope, intercept = np.polyfit(control, x, 1)
        return x - (slope * control + intercept)

    imp_resid = residualize(importance.astype(float), persuasiveness.astype(float))
    shift_resid = residualize(shift, persuasiveness.astype(float))
    rho_partial, p_partial = stats.spearmanr(imp_resid, shift_resid)

    # Bar chart
    x = [0, 1]
    heights = [rho_raw, rho_partial]
    colors = ["#0072B2", "#D55E00"]
    labels = ["Raw", "Controlling\npersuasiveness"]

    bars = ax.bar(x, heights, color=colors, width=0.5, edgecolor="none", alpha=0.85)

    # Add p-value annotations
    for i, (h, p) in enumerate(zip(heights, [p_raw, p_partial])):
        sig = "***" if p < .001 else "**" if p < .01 else "*" if p < .05 else "n.s."
        ax.text(i, h + 0.01, f"$\\rho$={h:.2f}{sig}", ha="center", fontsize=9)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylabel("Spearman $\\rho$\n(importance $\\rightarrow$ shift)")
    ax.set_ylim(0, max(heights) * 1.3)
    ax.set_title("Persuasiveness Control", fontsize=12, fontweight="bold")


# ═══════════════════════════════════════════════════════════════════════════
# PANEL B: Edge permutation — beta comparison
# ═══════════════════════════════════════════════════════════════════════════

def panel_b(ax):
    """Paired bar: original vs permuted beta for betweenness and outcome mediation."""
    lme_path = CAUSAL_DIR / "lme_results.json"
    if not lme_path.exists():
        ax.text(0.5, 0.5, "No LME results", ha="center", va="center",
                transform=ax.transAxes)
        return

    d = json.load(open(lme_path, encoding="utf-8"))

    # Get original (log-odds preferred) and permuted betas
    # TODO: rerun edge permutation with log-odds model; for now fall back to raw
    orig = d.get("model_a_logit_shared") or d.get("model_a_shared")
    perm = d.get("permutation_placebo")

    if orig is None or perm is None:
        ax.text(0.5, 0.5, "Missing original or permuted results", ha="center",
                va="center", transform=ax.transAxes)
        return

    # Extract beta and CI
    orig_fe = orig["fixed_effects"]
    perm_fe = perm["fixed_effects"]

    # Find the importance predictor
    orig_key = next((k for k in orig_fe if "importance" in k), None)
    perm_key = next((k for k in perm_fe if "importance" in k), None)

    if orig_key is None or perm_key is None:
        ax.text(0.5, 0.5, "Missing importance predictor", ha="center",
                va="center", transform=ax.transAxes)
        return

    orig_beta = orig_fe[orig_key]["coef"]
    orig_ci_lo = orig_fe[orig_key].get("ci_lower", orig_beta - 1.96 * orig_fe[orig_key]["se"])
    orig_ci_hi = orig_fe[orig_key].get("ci_upper", orig_beta + 1.96 * orig_fe[orig_key]["se"])
    orig_p = orig_fe[orig_key]["p"]

    perm_beta = perm_fe[perm_key]["coef"]
    perm_ci_lo = perm_fe[perm_key].get("ci_lower", perm_beta - 1.96 * perm_fe[perm_key]["se"])
    perm_ci_hi = perm_fe[perm_key].get("ci_upper", perm_beta + 1.96 * perm_fe[perm_key]["se"])
    perm_p = perm_fe[perm_key]["p"]

    x = [0, 1]
    heights = [orig_beta, perm_beta]
    errors_lo = [orig_beta - orig_ci_lo, perm_beta - perm_ci_lo]
    errors_hi = [orig_ci_hi - orig_beta, perm_ci_hi - perm_beta]
    colors = ["#0072B2", "#999999"]

    bars = ax.bar(x, heights, color=colors, width=0.5, edgecolor="none", alpha=0.85)
    ax.errorbar(x, heights, yerr=[errors_lo, errors_hi], fmt="none",
                color="black", capsize=5, capthick=1.2, linewidth=1.2)

    # Annotations
    for i, (h, p) in enumerate(zip(heights, [orig_p, perm_p])):
        sig = "***" if p < .001 else "**" if p < .01 else "*" if p < .05 else "n.s."
        y_pos = h + errors_hi[i] + 0.001
        ax.text(i, y_pos, f"$\\beta$={h:.3f}{sig}", ha="center", fontsize=9)

    ax.set_xticks(x)
    ax.set_xticklabels(["Original\nTopology", "Permuted\nEdges"], fontsize=10)
    ax.set_ylabel("$\\beta_1$ (betweenness)")
    ax.axhline(y=0, color="#333333", linewidth=0.8, linestyle="--", zorder=0)
    ax.set_title("Edge Permutation", fontsize=12, fontweight="bold")


# ═══════════════════════════════════════════════════════════════════════════
# PANEL C: Factor ranking null
# ═══════════════════════════════════════════════════════════════════════════

def panel_c(ax):
    """Forest plot of per-model Spearman rho (stated rank vs betweenness)."""
    fr_path = CAUSAL_DIR / "factor_ranking_analysis.json"
    if not fr_path.exists():
        ax.text(0.5, 0.5, "No factor ranking data", ha="center", va="center",
                transform=ax.transAxes)
        return

    d = json.load(open(fr_path, encoding="utf-8"))

    models = []
    rhos = []
    ps = []
    for model_name in ["Gemini-Flash-Lite", "Qwen3-235B", "DeepSeek-V3",
                        "Llama-3.3-70B", "Llama-3.1-8B"]:
        v = d.get(model_name)
        if v is None:
            continue
        models.append(model_name)
        rhos.append(v["pooled_rho_betweenness"])
        ps.append(v["pooled_p_betweenness"])

    y = np.arange(len(models))

    for i, (model, rho, p) in enumerate(zip(models, rhos, ps)):
        color = MODEL_COLORS.get(model, "#333")
        ax.plot(rho, i, "o", color=color, markersize=8, markeredgecolor="white",
                markeredgewidth=0.5, zorder=3)

    ax.axvline(x=0, color="#333333", linewidth=0.8, linestyle="--", zorder=0)
    ax.set_yticks(y)
    ax.set_yticklabels([SHORT_NAMES.get(m, m) for m in models], fontsize=10)
    ax.set_xlabel("Spearman $\\rho$ (stated rank vs. betweenness)")
    ax.set_title("Factor Ranking (No DAG)", fontsize=12, fontweight="bold")

    # Add "all n.s." annotation
    ax.text(0.95, 0.05, "all $p$ > .05", transform=ax.transAxes,
            ha="right", va="bottom", fontsize=10, fontstyle="italic", color="#666666")


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════════
# PANEL D: Network size — beta by graph size condition
# ═══════════════════════════════════════════════════════════════════════════

def panel_d(ax):
    """Bar chart: beta by network size condition."""
    lme_path = CAUSAL_DIR / "lme_results.json"
    if not lme_path.exists():
        ax.text(0.5, 0.5, "No LME results", ha="center", va="center",
                transform=ax.transAxes)
        return

    d = json.load(open(lme_path, encoding="utf-8"))

    # Network size conditions — use log-odds if available, fall back to raw
    # TODO: rerun network size with log-odds model
    conditions = [
        ("4-8\nnodes", d.get("net_medium")),
        ("6-10\nnodes", d.get("net_large")),
        ("12-16\nnodes", d.get("net_xl")),
    ]

    labels = []
    betas = []
    ci_los = []
    ci_his = []
    ps = []

    for label, result in conditions:
        if result is None:
            continue
        fe = result["fixed_effects"]
        key = next((k for k in fe if "importance" in k or "betweenness" in k), None)
        if key is None:
            continue
        beta = fe[key]["coef"]
        se = fe[key]["se"]
        p = fe[key]["p"]
        labels.append(label)
        betas.append(beta)
        ci_los.append(beta - 1.96 * se)
        ci_his.append(beta + 1.96 * se)
        ps.append(p)

    if not labels:
        ax.text(0.5, 0.5, "No network size data", ha="center", va="center",
                transform=ax.transAxes)
        return

    x = np.arange(len(labels))
    colors_ns = ["#0072B2", "#009E73", "#D55E00"]

    bars = ax.bar(x, betas, color=colors_ns[:len(labels)], width=0.5,
                  edgecolor="none", alpha=0.85)
    ax.errorbar(x, betas,
                yerr=[[b - lo for b, lo in zip(betas, ci_los)],
                      [hi - b for b, hi in zip(betas, ci_his)]],
                fmt="none", color="black", capsize=5, capthick=1.2, linewidth=1.2)

    for i, (b, p) in enumerate(zip(betas, ps)):
        sig = "***" if p < .001 else "**" if p < .01 else "*" if p < .05 else "n.s."
        y_pos = ci_his[i] + 0.001
        ax.text(i, y_pos, f"$\\beta$={b:.3f}{sig}", ha="center", fontsize=9)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylabel("$\\beta_1$ (betweenness)")
    ax.axhline(y=0, color="#333333", linewidth=0.8, linestyle="--", zorder=0)
    ax.set_title("Network Size", fontsize=12, fontweight="bold")


def main():
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(14, 4.5),
                                         gridspec_kw={"width_ratios": [1, 1, 1],
                                                      "wspace": 0.4})

    panel_a(ax1)
    panel_b(ax2)
    panel_d(ax3)

    _label_axes([ax1, ax2, ax3])

    OUT.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT / f"validation.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("Saved validation.pdf/png")


if __name__ == "__main__":
    main()
