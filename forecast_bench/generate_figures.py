"""
Generate all paper figures for the Belief Sensitivity analysis.

Outputs saved to paper/figures/.

Usage:
    python -m forecast_bench.generate_figures
"""

from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

from forecast_bench.analysis_causal import (
    load_causal_results,
    _spearman_correlation,
    _safe_mean,
)
from forecast_bench.analysis_full import (
    load_question_jsons,
    _load_freeze_values,
    _median,
    _bootstrap_ci,
    _classify_stated_impact,
    _count_phrase_hits,
    _STRONG_IMPACT_PHRASES,
    _WEAK_IMPACT_PHRASES,
    _CAUSAL_PATH_PHRASES,
    _kendall_tau,
)

# ── Paths ───────────────────────────────────────────────────────────────────
BASE = Path(__file__).parent.parent
FIGURES_DIR = BASE / "paper" / "figures"
SUPPLEMENT_DIR = BASE / "paper" / "figures" / "supplementary"
CAUSAL_DIR = BASE / "outputs" / "sensitivity" / "causal"

MODEL_DIRS = {
    "Llama-3.1-8B": CAUSAL_DIR / "llama_one_turn",
    "Llama-3.3-70B": CAUSAL_DIR / "70b_one_turn",
    "DeepSeek-V3-0324": CAUSAL_DIR / "deepseek_one_turn",
    "Qwen3-235B": CAUSAL_DIR / "qwen_one_turn",
}

# Colorblind-safe palette (Wong 2011 / IBM Design)
# Blue, Orange, Vermillion — distinct under all forms of color vision deficiency
COLORS = {
    "Llama-3.1-8B": "#E69F00",        # orange
    "Llama-3.3-70B": "#0072B2",       # blue
    "DeepSeek-V3-0324": "#D55E00",    # vermillion
    "Qwen3-235B": "#009E73",          # green
}

# Category palette for probe types (colorblind-safe)
CAT_COLORS = {
    "node": "#0072B2",       # blue
    "edge": "#D55E00",       # vermillion
    "structural": "#009E73", # bluish green
    "control": "#999999",    # gray
}

# Common style
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
    "mathtext.default": "regular",  # use same font for math text
    "axes.spines.top": False,
    "axes.spines.right": False,
    "boxplot.medianprops.color": "black",
    "boxplot.medianprops.linewidth": 1.5,
})


def _label_axes(axes, fontsize=14):
    """Add (a), (b), (c), ... labels to a list of axes.

    Labels are placed above the top-left corner of each subplot,
    aligned with the y-axis label so they don't overlap titles.
    """
    if not hasattr(axes, "__iter__"):
        axes = [axes]
    for i, ax in enumerate(axes):
        label = chr(ord("a") + i)
        ax.text(-0.02, 1.02, f"({label})", transform=ax.transAxes,
                fontsize=fontsize, fontweight="bold", va="bottom", ha="right")


def _load_all_runs():
    """Load rows and question data for all models."""
    runs = {}
    for name, d in MODEL_DIRS.items():
        csv_path = d / "sensitivity_results.csv"
        if not csv_path.exists():
            print(f"  [SKIP] {name}: no CSV")
            continue
        rows = load_causal_results(csv_path)
        q_data = load_question_jsons(d)
        runs[name] = (rows, q_data)
        print(f"  Loaded {name}: {len(rows)} probes, {len(q_data)} questions")
    return runs


# ═════════════════════════════════════════════════════════════════════════════
# FIGURE 1: Dose-Response (Importance vs Shift)
# ═════════════════════════════════════════════════════════════════════════════

def fig_dose_response(runs: dict):
    """Scatter plot of target importance (betweenness centrality) vs |shift|."""
    fig, axes = plt.subplots(1, len(runs), figsize=(5 * len(runs), 4.5), sharey=True)
    if len(runs) == 1:
        axes = [axes]

    for ax, (name, (rows, _)) in zip(axes, runs.items()):
        importances = []
        shifts = []
        for r in rows:
            if not r.get("success"):
                continue
            imp = r.get("target_importance")
            shift = r.get("absolute_shift")
            if imp is not None and shift is not None and imp > 0:
                importances.append(imp)
                shifts.append(shift)

        ax.scatter(importances, shifts, alpha=0.25, s=15, color=COLORS[name],
                   edgecolor="none")

        # OLS regression line
        if importances:
            x = np.array(importances)
            y = np.array(shifts)
            m, b = np.polyfit(x, y, 1)
            x_line = np.linspace(x.min(), x.max(), 100)
            ax.plot(x_line, m * x_line + b, color="black", linewidth=2, zorder=5)

        rho = _spearman_correlation(importances, shifts)
        ax.set_xlabel("Betweenness Centrality")
        ax.set_title(name)
        if rho is not None:
            # Approximate p-value from rho via t-distribution
            n_pts = len(importances)
            t_stat = rho * (n_pts - 2) ** 0.5 / max((1 - rho**2) ** 0.5, 1e-12)
            from forecast_bench.analysis_causal import _t_to_p
            p_val = _t_to_p(abs(t_stat), n_pts - 2)
            p_str = "p < 0.001" if p_val < 0.001 else f"p = {p_val:.3f}"
            ax.annotate(f"ρ = {rho:.3f}\n{p_str}",
                        xy=(0.95, 0.95), xycoords="axes fraction",
                        ha="right", va="top", fontsize=10)

    axes[0].set_ylabel("|Probability Shift|")
    _label_axes(axes)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "dose_response.png")
    plt.savefig(FIGURES_DIR / "dose_response.pdf")
    plt.close()
    print("  Saved dose_response.png/pdf")


# ═════════════════════════════════════════════════════════════════════════════
# FIGURE 2: SSR Comparison (bar chart)
# ═════════════════════════════════════════════════════════════════════════════

def _bootstrap_metric(rows, metric_fn, n_boot=2000, seed=42):
    """Bootstrap a metric that takes a list of rows and returns a scalar.

    Returns (point_estimate, ci_lower, ci_upper).
    """
    import random as _rng
    _rng.seed(seed)
    point = metric_fn(rows)
    boot_vals = []
    n = len(rows)
    for _ in range(n_boot):
        sample = _rng.choices(rows, k=n)
        boot_vals.append(metric_fn(sample))
    boot_vals.sort()
    lo = boot_vals[int(0.025 * n_boot)]
    hi = boot_vals[int(0.975 * n_boot)]
    return point, lo, hi


def fig_ssr_comparison(runs: dict):
    """Bar chart comparing SSR, SAR, and importance-rho across models with 95% CIs."""
    from forecast_bench.analysis_causal import (
        structural_sensitivity_ratio,
        spurious_acceptance_rate,
        importance_sensitivity_correlation,
    )

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))
    model_names = list(runs.keys())
    x = range(len(model_names))
    bar_colors = [COLORS[n] for n in model_names]

    # Helper lambdas for bootstrapping
    def _ssr_val(rows):
        r = structural_sensitivity_ratio(rows)
        return r.get("ssr", 0)

    def _sar_val(rows):
        r = spurious_acceptance_rate(rows)
        return r.get("acceptance_rate", 0)

    def _rho_val(rows):
        r = importance_sensitivity_correlation(rows)
        return r.get("spearman_rho", 0)

    # SSR with CI
    ssrs, ssr_los, ssr_his = [], [], []
    for name, (rows, _) in runs.items():
        pt, lo, hi = _bootstrap_metric(rows, _ssr_val)
        ssrs.append(pt)
        ssr_los.append(pt - lo)
        ssr_his.append(hi - pt)
    axes[0].bar(x, ssrs, yerr=[ssr_los, ssr_his], color=bar_colors,
                edgecolor="black", linewidth=0.5, capsize=5, error_kw={"linewidth": 1.5})
    axes[0].axhline(y=1, color="gray", linestyle="--", alpha=0.5, label="SSR = 1 (no sensitivity)")
    axes[0].set_ylabel("Structural Sensitivity Ratio\n(SSR)")
    axes[0].set_xticks(list(x))
    axes[0].set_xticklabels([n.replace("-", "\n", 1) for n in model_names], fontsize=9)
    axes[0].legend(fontsize=8, frameon=False)

    # SAR with CI
    sars, sar_los, sar_his = [], [], []
    for name, (rows, _) in runs.items():
        pt, lo, hi = _bootstrap_metric(rows, _sar_val)
        sars.append(pt)
        sar_los.append(pt - lo)
        sar_his.append(hi - pt)
    axes[1].bar(x, sars, yerr=[sar_los, sar_his], color=bar_colors,
                edgecolor="black", linewidth=0.5, capsize=5, error_kw={"linewidth": 1.5})
    axes[1].set_ylabel("Spurious Acceptance Rate\n(SAR)")
    axes[1].set_xticks(list(x))
    axes[1].set_xticklabels([n.replace("-", "\n", 1) for n in model_names], fontsize=9)
    axes[1].set_ylim(0, 1)

    # Importance rho with CI and p-values
    rhos, rho_los, rho_his = [], [], []
    rho_ps = []
    for name, (rows, _) in runs.items():
        pt, lo, hi = _bootstrap_metric(rows, _rho_val)
        rhos.append(pt)
        rho_los.append(pt - lo)
        rho_his.append(hi - pt)
        # Compute p-value from rho and n
        r = importance_sensitivity_correlation(rows)
        n = r.get("n", 0)
        rho = r.get("spearman_rho", 0) or 0
        if n > 2:
            t_stat = rho * ((n - 2) / (1 - rho**2 + 1e-12))**0.5
            from forecast_bench.analysis_causal import _t_to_p
            p = _t_to_p(abs(t_stat), n - 2)
        else:
            p = 1.0
        rho_ps.append(p)
    axes[2].bar(x, rhos, yerr=[rho_los, rho_his], color=bar_colors,
                edgecolor="black", linewidth=0.5, capsize=5, error_kw={"linewidth": 1.5})
    # Add significance stars above bars
    for i, (rho_v, hi, p) in enumerate(zip(rhos, rho_his, rho_ps)):
        if p < 0.001:
            stars = "***"
        elif p < 0.01:
            stars = "**"
        elif p < 0.05:
            stars = "*"
        else:
            stars = "n.s."
        axes[2].annotate(stars, xy=(i, rho_v + hi), xytext=(0, 4),
                         textcoords="offset points", ha="center", fontsize=13, fontweight="bold")
    axes[2].set_ylabel("Importance–Shift Correlation\n(Spearman ρ)")
    axes[2].set_xticks(list(x))
    axes[2].set_xticklabels([n.replace("-", "\n", 1) for n in model_names], fontsize=9)

    _label_axes(axes)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "ssr_comparison.png")
    plt.savefig(FIGURES_DIR / "ssr_comparison.pdf")
    plt.close()
    print("  Saved ssr_comparison.png/pdf")


# ═════════════════════════════════════════════════════════════════════════════
# FIGURE 3: Shift Distributions by Probe Type
# ═════════════════════════════════════════════════════════════════════════════

def fig_shift_by_probe_type(runs: dict):
    """Box plots of |shift| by probe type, pooled across all models."""
    type_shifts = defaultdict(list)
    for name, (rows, _) in runs.items():
        for r in rows:
            if not r.get("success") or r.get("absolute_shift") is None:
                continue
            pt = r.get("probe_type", "unknown")
            type_shifts[pt].append(r["absolute_shift"])

    # Order by median shift
    ordered = sorted(type_shifts.items(), key=lambda kv: _median(kv[1]), reverse=True)
    labels = [k for k, _ in ordered]
    data = [v for _, v in ordered]

    # Color by category
    cat_colors = CAT_COLORS
    from forecast_bench.prompts_causal import PROBE_CATEGORIES
    face_colors = [cat_colors.get(PROBE_CATEGORIES.get(l, "structural"), "#999") for l in labels]

    fig, ax = plt.subplots(figsize=(10, 5))
    bp = ax.boxplot(data, tick_labels=[l.replace("_", "\n") for l in labels],
                    patch_artist=True, widths=0.6, showfliers=False)
    for patch, color in zip(bp["boxes"], face_colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)

    # Add significance stars (one-sample t-test: mean > 0)
    from forecast_bench.analysis_causal import _t_to_p
    for i, (label, vals) in enumerate(ordered):
        if len(vals) < 2:
            continue
        mean_v = sum(vals) / len(vals)
        var_v = sum((v - mean_v) ** 2 for v in vals) / (len(vals) - 1)
        se_v = var_v ** 0.5 / len(vals) ** 0.5
        t_stat = mean_v / se_v if se_v > 0 else 0
        p = _t_to_p(abs(t_stat), len(vals) - 1)
        if p < 0.001:
            stars = "***"
        elif p < 0.01:
            stars = "**"
        elif p < 0.05:
            stars = "*"
        else:
            stars = "n.s."
        # Place above the whisker
        whisker_top = bp["caps"][2 * i + 1].get_ydata()[0]
        ax.annotate(stars, xy=(i + 1, whisker_top), xytext=(0, 4),
                    textcoords="offset points", ha="center", fontsize=11, fontweight="bold")

    ax.set_ylabel("|Probability Shift|")

    # Legend for categories
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=CAT_COLORS["node"], alpha=0.6, label="Node probes"),
        Patch(facecolor=CAT_COLORS["edge"], alpha=0.6, label="Edge probes"),
        Patch(facecolor=CAT_COLORS["structural"], alpha=0.6, label="Structural probes"),
        Patch(facecolor=CAT_COLORS["control"], alpha=0.6, label="Control probes"),
    ]
    ax.legend(handles=legend_elements, loc="upper right", frameon=False)

    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "shift_by_probe_type.png")
    plt.savefig(FIGURES_DIR / "shift_by_probe_type.pdf")
    plt.close()
    print("  Saved shift_by_probe_type.png/pdf")


# ═════════════════════════════════════════════════════════════════════════════
# FIGURE 4: Calibration Curves
# ═════════════════════════════════════════════════════════════════════════════

def fig_calibration(runs: dict):
    """Calibration curve: predicted probability vs ground truth."""
    freeze_vals = _load_freeze_values()
    if not freeze_vals:
        print("  [SKIP] No ground truth data")
        return

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.plot([0, 1], [0, 1], "k--", alpha=0.3, linewidth=1, label="Perfect calibration")

    for name, (rows, q_data) in runs.items():
        pairs = []
        for qid, qd in q_data.items():
            if qid in freeze_vals:
                pred = qd.get("initial_probability")
                if pred is not None:
                    pairs.append((pred, freeze_vals[qid]))

        if len(pairs) < 5:
            continue

        # Bin into quintiles
        pairs.sort(key=lambda p: p[0])
        n_bins = 5
        bin_size = len(pairs) // n_bins
        bin_preds = []
        bin_actuals = []
        bin_ns = []
        for i in range(n_bins):
            start = i * bin_size
            end = start + bin_size if i < n_bins - 1 else len(pairs)
            chunk = pairs[start:end]
            bin_preds.append(sum(p for p, _ in chunk) / len(chunk))
            bin_actuals.append(sum(a for _, a in chunk) / len(chunk))
            bin_ns.append(len(chunk))

        ax.plot(bin_preds, bin_actuals, "o-", color=COLORS[name], markersize=8,
                linewidth=2, label=f"{name} (n={len(pairs)})")

        # Add error region
        for bp, ba, bn in zip(bin_preds, bin_actuals, bin_ns):
            se = (ba * (1 - ba) / max(bn, 1)) ** 0.5
            ax.fill_between([bp - 0.01, bp + 0.01],
                           [ba - 1.96 * se] * 2, [ba + 1.96 * se] * 2,
                           alpha=0.1, color=COLORS[name])

    ax.set_xlabel("Predicted Probability")
    ax.set_ylabel("Ground Truth Probability")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_aspect("equal")
    ax.legend(loc="upper left", fontsize=9, frameon=False)
    ax.grid(True, alpha=0.2)

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "calibration_curve.png")
    plt.savefig(FIGURES_DIR / "calibration_curve.pdf")
    plt.close()
    print("  Saved calibration_curve.png/pdf")


# ═════════════════════════════════════════════════════════════════════════════
# FIGURE 5: Within-Question Consistency (Kendall's tau distribution)
# ═════════════════════════════════════════════════════════════════════════════

def fig_within_question_consistency(runs: dict):
    """Histogram of per-question Kendall's tau values for all models."""
    model_names = list(runs.keys())
    fig, axes = plt.subplots(1, len(model_names), figsize=(5 * len(model_names), 4.5),
                             sharey=True, sharex=True)
    if len(model_names) == 1:
        axes = [axes]

    bins = [i * 0.1 for i in range(-10, 11)]

    for ax, name in zip(axes, model_names):
        rows = runs[name][0]

        q_probes = defaultdict(list)
        for r in rows:
            if not r.get("success") or r.get("absolute_shift") is None:
                continue
            if r.get("target_importance") is None or r["target_importance"] == 0:
                continue
            cat = r.get("probe_category", "")
            if cat != "node":
                continue
            qid = r.get("question_id", "")
            q_probes[qid].append(r)

        taus = []
        for qid, probes in q_probes.items():
            if len(probes) < 3:
                continue
            importances = [p["target_importance"] for p in probes]
            shifts = [p["absolute_shift"] for p in probes]
            tau = _kendall_tau(importances, shifts)
            if tau is not None:
                taus.append(tau)

        if not taus:
            ax.text(0.5, 0.5, "Insufficient data", transform=ax.transAxes, ha="center")
            continue

        ax.hist(taus, bins=bins, color=COLORS[name], alpha=0.7, edgecolor="black",
                linewidth=0.5)

        # One-sample t-test: is mean τ different from zero?
        n_tau = len(taus)
        mean_tau = sum(taus) / n_tau
        var_tau = sum((t - mean_tau) ** 2 for t in taus) / (n_tau - 1)
        se_tau = var_tau ** 0.5 / n_tau ** 0.5
        t_stat = mean_tau / se_tau if se_tau > 0 else 0
        from forecast_bench.analysis_causal import _t_to_p
        p_val = _t_to_p(abs(t_stat), n_tau - 1)
        p_str = "p < 0.001" if p_val < 0.001 else f"p = {p_val:.3f}"

        ax.set_xlabel("Kendall's τ")
        ax.set_title(f"{name}")
        ax.annotate(f"Mean τ = {mean_tau:.3f}\n{p_str}\nn = {n_tau}",
                    xy=(0.03, 0.95), xycoords="axes fraction",
                    ha="left", va="top", fontsize=9)

    axes[0].set_ylabel("Number of Questions")
    _label_axes(axes)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "within_question_tau.png")
    plt.savefig(FIGURES_DIR / "within_question_tau.pdf")
    plt.close()
    print("  Saved within_question_tau.png/pdf")


# ═════════════════════════════════════════════════════════════════════════════
# FIGURE 6: Reasoning Coherence
# ═════════════════════════════════════════════════════════════════════════════

def fig_reasoning_coherence(runs: dict):
    """Box plots of |shift| by LLM-as-a-judge impact rating (1-5)."""
    import json as _json

    # Load judge ratings
    judge_path = CAUSAL_DIR / "reasoning_judge_ratings.json"
    if not judge_path.exists():
        print("  [SKIP] reasoning_coherence: no judge ratings file")
        return
    judge_data = _json.loads(judge_path.read_text(encoding="utf-8"))

    # Map judge model keys to figure model names
    judge_model_map = {"llama-8b": "Llama-3.1-8B", "llama-70b": "Llama-3.3-70B",
                       "deepseek": "DeepSeek-V3-0324", "qwen": "Qwen3-235B"}

    # Collect shifts by rating, pooled across all models
    rating_shifts = {r: [] for r in range(1, 6)}
    for model_name, (rows, _) in runs.items():
        # Find the judge key prefix for this model
        judge_prefix = None
        for jk, mk in judge_model_map.items():
            if mk == model_name:
                judge_prefix = jk
                break
        if not judge_prefix:
            continue

        for r in rows:
            if not r.get("success") or r.get("absolute_shift") is None:
                continue
            qid = r.get("question_id", "")
            probe_idx = r.get("probe_index")
            if probe_idx is None:
                continue
            key = f"{judge_prefix}|{qid}|{int(probe_idx)}"
            judge_entry = judge_data.get(key, {})
            rating = judge_entry.get("rating")
            if rating and 1 <= rating <= 5:
                rating_shifts[rating].append(r["absolute_shift"])

    fig, ax = plt.subplots(figsize=(6, 4.5))

    ratings = [1, 2, 3, 4, 5]
    cat_data = [rating_shifts[r] for r in ratings]
    cat_labels = [f"{r}\n(n={len(rating_shifts[r])})" for r in ratings]
    # Gradient from blue (low impact) to vermillion (high impact)
    cat_colors_list = ["#0072B2", "#56B4E9", "#E69F00", "#D55E00", "#CC3311"]

    bp = ax.boxplot(cat_data, tick_labels=cat_labels, patch_artist=True,
                    widths=0.5, showfliers=False)
    for patch, color in zip(bp["boxes"], cat_colors_list):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)

    # Add means
    for i, vals in enumerate(cat_data):
        if vals:
            mean_v = sum(vals) / len(vals)
            ax.scatter([i + 1], [mean_v], marker="D", color="black", s=40, zorder=5)

    ax.set_ylabel("|Probability Shift|")
    ax.set_xlabel("Stated-Impact Rating")

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "reasoning_coherence.png")
    plt.savefig(FIGURES_DIR / "reasoning_coherence.pdf")
    plt.close()
    print("  Saved reasoning_coherence.png/pdf")


# ═════════════════════════════════════════════════════════════════════════════
# FIGURE 7: Probability Distributions (cross-model)
# ═════════════════════════════════════════════════════════════════════════════

def fig_probability_distributions(runs: dict):
    """Paired comparison of initial probabilities across models for shared questions."""
    model_names = list(runs.keys())

    # Collect per-question initial probabilities
    model_probs = {}
    for name, (rows, q_data) in runs.items():
        probs = {}
        for qid, qd in q_data.items():
            p = qd.get("initial_probability")
            if p is not None:
                probs[qid] = p
        model_probs[name] = probs

    # Find questions shared across ALL models
    shared_qids = set.intersection(*(set(p.keys()) for p in model_probs.values()))
    shared_qids = sorted(shared_qids)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))

    # (a) Connected dot plot: each question is a horizontal row, dots per model
    # Sort by mean probability across models
    q_means = []
    for qid in shared_qids:
        vals = [model_probs[m][qid] for m in model_names]
        q_means.append((qid, sum(vals) / len(vals)))
    q_means.sort(key=lambda x: x[1])
    sorted_qids = [qid for qid, _ in q_means]

    y_positions = range(len(sorted_qids))
    for name in model_names:
        x_vals = [model_probs[name][qid] for qid in sorted_qids]
        ax1.scatter(x_vals, y_positions, alpha=0.6, s=20, color=COLORS[name],
                    label=name, edgecolor="none", zorder=3)

    # Connect dots per question with thin gray lines
    for yi, qid in enumerate(sorted_qids):
        vals = [model_probs[m][qid] for m in model_names]
        ax1.plot([min(vals), max(vals)], [yi, yi], color="gray",
                 linewidth=0.5, alpha=0.4, zorder=1)

    ax1.set_xlabel("Initial Probability")
    ax1.set_ylabel("Questions (sorted by mean probability)")
    ax1.set_xlim(0, 1)
    ax1.set_yticks([])
    ax1.legend(fontsize=8, loc="lower right", frameon=False)
    ax1.grid(axis="x", alpha=0.2)

    # (b) Distribution of per-question spread (max - min across models)
    spreads = []
    for qid in shared_qids:
        vals = [model_probs[m][qid] for m in model_names]
        spreads.append(max(vals) - min(vals))

    bins = [i * 0.05 for i in range(13)]
    ax2.hist(spreads, bins=bins, color="#009E73", alpha=0.7, edgecolor="black",
             linewidth=0.5)
    ax2.set_xlabel("Cross-Model Spread (max − min)")
    ax2.set_ylabel("Number of Questions")

    _label_axes([ax1, ax2])
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "probability_distributions.png")
    plt.savefig(FIGURES_DIR / "probability_distributions.pdf")
    plt.close()
    print("  Saved probability_distributions.png/pdf")


# ═════════════════════════════════════════════════════════════════════════════
# FIGURE 8: Cross-Model Shift Comparison
# ═════════════════════════════════════════════════════════════════════════════

def fig_cross_model_shifts(runs: dict):
    """Box plots of mean |shift| per model, split by high/low importance."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    model_names = list(runs.keys())

    # Overall shift distributions
    all_shifts = {}
    for name, (rows, _) in runs.items():
        shifts = [r["absolute_shift"] for r in rows
                  if r.get("success") and r.get("absolute_shift") is not None]
        all_shifts[name] = shifts

    bp1 = ax1.boxplot([all_shifts[n] for n in model_names],
                      tick_labels=[n.replace("-", "\n", 1) for n in model_names],
                      patch_artist=True, widths=0.5, showfliers=False)
    for patch, name in zip(bp1["boxes"], model_names):
        patch.set_facecolor(COLORS[name])
        patch.set_alpha(0.5)
    for i, name in enumerate(model_names):
        mean_v = sum(all_shifts[name]) / len(all_shifts[name])
        ax1.scatter([i + 1], [mean_v], marker="D", color="black", s=30, zorder=5)
    ax1.set_ylabel("|Probability Shift|")

    # Shift by probe category (node / edge / structural) per model
    from forecast_bench.prompts_causal import PROBE_CATEGORIES
    cat_order = ["node", "edge", "structural", "control"]
    cat_labels = ["Node", "Edge", "Structural", "Control"]
    cat_colors_list = [CAT_COLORS[c] for c in cat_order]

    x = np.arange(len(model_names))
    n_cats = len(cat_order)
    width = 0.2

    for ci, cat in enumerate(cat_order):
        means = []
        ses = []
        for name, (rows, _) in runs.items():
            vals = [r["absolute_shift"] for r in rows
                    if r.get("success") and r.get("absolute_shift") is not None
                    and PROBE_CATEGORIES.get(r.get("probe_type", ""), "") == cat]
            if vals:
                m = sum(vals) / len(vals)
                se = (sum((v - m)**2 for v in vals) / len(vals))**0.5 / len(vals)**0.5
            else:
                m, se = 0, 0
            means.append(m)
            ses.append(se)
        ax2.bar(x + (ci - 1) * width, means, width, yerr=ses,
                label=cat_labels[ci], color=cat_colors_list[ci], alpha=0.7,
                edgecolor="black", linewidth=0.5, capsize=3)

    ax2.set_ylabel("Mean |Probability Shift|")
    ax2.set_xticks(x)
    ax2.set_xticklabels([n.replace("-", "\n", 1) for n in model_names], fontsize=9)
    ax2.legend(frameon=False)

    _label_axes([ax1, ax2])
    plt.tight_layout()
    plt.savefig(SUPPLEMENT_DIR / "cross_model_shifts.png")
    plt.savefig(SUPPLEMENT_DIR / "cross_model_shifts.pdf")
    plt.close()
    print("  Saved supplementary/cross_model_shifts.png/pdf")


# ═════════════════════════════════════════════════════════════════════════════
# FIGURE 9: Null Test (Real vs Irrelevant Probes)
# ═════════════════════════════════════════════════════════════════════════════

def fig_null_test(runs: dict):
    """Compare shift distributions: real probes vs irrelevant controls."""
    name = list(runs.keys())[0]
    rows = runs[name][0]

    real_shifts = [r["absolute_shift"] for r in rows
                   if r.get("success") and r.get("absolute_shift") is not None
                   and r.get("probe_type") != "irrelevant"]
    irrel_shifts = [r["absolute_shift"] for r in rows
                    if r.get("success") and r.get("absolute_shift") is not None
                    and r.get("probe_type") == "irrelevant"]

    fig, ax = plt.subplots(figsize=(7, 4.5))
    bins = [i * 0.02 for i in range(26)]

    ax.hist(real_shifts, bins=bins, alpha=0.5, color="#0072B2",
            edgecolor="#0072B2", linewidth=0.8, label=f"Real probes (n={len(real_shifts)})",
            density=True)
    ax.hist(irrel_shifts, bins=bins, alpha=0.5, color="#D55E00",
            edgecolor="#D55E00", linewidth=0.8, label=f"Irrelevant probes (n={len(irrel_shifts)})",
            density=True)

    # Add means
    real_mean = sum(real_shifts) / len(real_shifts)
    irrel_mean = sum(irrel_shifts) / len(irrel_shifts)
    ax.axvline(real_mean, color="#0072B2", linestyle="--", linewidth=2,
               label=f"Real mean = {real_mean:.3f}")
    ax.axvline(irrel_mean, color="#D55E00", linestyle="--", linewidth=2,
               label=f"Irrelevant mean = {irrel_mean:.3f}")

    # Welch's t-test for p-value
    from forecast_bench.analysis_causal import _t_to_p
    n1, n2 = len(real_shifts), len(irrel_shifts)
    m1, m2 = real_mean, irrel_mean
    var1 = sum((x - m1)**2 for x in real_shifts) / (n1 - 1)
    var2 = sum((x - m2)**2 for x in irrel_shifts) / (n2 - 1)
    se = (var1 / n1 + var2 / n2) ** 0.5
    t_stat = (m1 - m2) / se if se > 0 else 0
    df = min(n1, n2) - 1
    p_val = _t_to_p(abs(t_stat), df)
    p_str = f"p < 0.001" if p_val < 0.001 else f"p = {p_val:.3f}"
    ax.annotate(f"t = {t_stat:.1f}, {p_str}",
                xy=(0.55, 0.88), xycoords="axes fraction",
                fontsize=11, fontweight="bold")

    ax.set_xlabel("|Probability Shift|")
    ax.set_ylabel("Density")
    ax.legend(fontsize=9, frameon=False)

    plt.tight_layout()
    plt.savefig(SUPPLEMENT_DIR / "null_test.png")
    plt.savefig(SUPPLEMENT_DIR / "null_test.pdf")
    plt.close()
    print("  Saved supplementary/null_test.png/pdf")


# ═════════════════════════════════════════════════════════════════════════════
# FIGURE 10: Paired Initial Probabilities Across Models
# ═════════════════════════════════════════════════════════════════════════════

def fig_paired_initial_probabilities(runs: dict):
    """Scatter matrix showing how models rate the same questions differently."""
    model_names = list(runs.keys())
    if len(model_names) < 2:
        print("  [SKIP] Need at least 2 models for paired comparison")
        return

    # Collect initial probabilities by question ID for each model
    model_probs = {}
    for name, (rows, q_data) in runs.items():
        probs = {}
        for qid, qd in q_data.items():
            p = qd.get("initial_probability")
            if p is not None:
                probs[qid] = p
        model_probs[name] = probs

    # Find shared questions across all pairs
    n_pairs = len(model_names)
    # For 3 models: 3 pairwise comparisons
    pairs = []
    for i in range(n_pairs):
        for j in range(i + 1, n_pairs):
            pairs.append((model_names[i], model_names[j]))

    fig, axes = plt.subplots(1, len(pairs), figsize=(5.5 * len(pairs), 5), squeeze=False)
    axes = axes[0]

    for idx, (m1, m2) in enumerate(pairs):
        ax = axes[idx]
        shared = set(model_probs[m1].keys()) & set(model_probs[m2].keys())
        if not shared:
            ax.text(0.5, 0.5, "No shared questions", transform=ax.transAxes, ha="center")
            continue

        x = [model_probs[m1][qid] for qid in shared]
        y = [model_probs[m2][qid] for qid in shared]

        ax.scatter(x, y, alpha=0.5, s=30, color="#0072B2", edgecolor="none")
        ax.plot([0, 1], [0, 1], "k--", alpha=0.3, linewidth=1)

        # Compute correlation
        rho = _spearman_correlation(x, y)

        # Mean absolute difference
        diffs = [abs(a - b) for a, b in zip(x, y)]
        mad = sum(diffs) / len(diffs)

        ax.set_xlabel(m1)
        ax.set_ylabel(m2)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_aspect("equal")
        ax.grid(True, alpha=0.2)

        ax.annotate(f"ρ = {rho:.3f}\nMAD = {mad:.3f}\nn = {len(shared)}",
                    xy=(0.05, 0.88), xycoords="axes fraction", fontsize=10,
                    va="top",
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))

    _label_axes(axes)
    plt.tight_layout()
    plt.savefig(SUPPLEMENT_DIR / "paired_initial_probs.png")
    plt.savefig(SUPPLEMENT_DIR / "paired_initial_probs.pdf")
    plt.close()
    print("  Saved supplementary/paired_initial_probs.png/pdf")


def _wilson_ci(k, n, z=1.96):
    """Wilson score interval for proportion k/n."""
    if n == 0:
        return 0, 0, 0
    p_hat = k / n
    denom = 1 + z**2 / n
    centre = (p_hat + z**2 / (2 * n)) / denom
    margin = z * np.sqrt((p_hat * (1 - p_hat) + z**2 / (4 * n)) / n) / denom
    return centre, max(0, centre - margin), min(1, centre + margin)


# ═════════════════════════════════════════════════════════════════════════════
# FIGURE 8: Superforecasting Sub-Analysis
# ═════════════════════════════════════════════════════════════════════════════

def fig_superforecasting_analysis(runs: dict):
    """Four-panel analysis of superforecasting traits in LLM forecasters.

    (a) Reasoning uncertainty — hedging language frequency vs |shift|
    (b) Network richness vs Brier score
    (c) Source-stratified calibration (data-anchored vs speculative)
    (d) Probability granularity by model
    """
    import json as _json
    import re

    freeze_vals = _load_freeze_values()

    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    ax_a, ax_b, ax_c, ax_d = axes.flat

    # ── (a) Uncertainty rating (LLM judge) vs shift — pooled boxplot ──
    judge_rating_path = CAUSAL_DIR / "uncertainty_judge_ratings.json"
    judge_key_map = {"Llama-3.1-8B": "llama-8b", "Llama-3.3-70B": "llama-70b",
                     "DeepSeek-V3-0324": "deepseek", "Qwen3-235B": "qwen"}

    if judge_rating_path.exists():
        judge_ratings = _json.loads(judge_rating_path.read_text(encoding="utf-8"))

        by_rating = defaultdict(list)
        for display_name, (rows, q_data) in runs.items():
            judge_key = judge_key_map.get(display_name)
            if not judge_key:
                continue
            for qid, qd in q_data.items():
                init_p = qd.get("initial_probability")
                for i, pr in enumerate(qd.get("probe_results", [])):
                    if not pr.get("success"):
                        continue
                    up = pr.get("updated_probability")
                    if up is None or init_p is None:
                        continue
                    key = f"{judge_key}|{qid}|{i}"
                    if key not in judge_ratings:
                        continue
                    rating = judge_ratings[key].get("rating")
                    if rating is not None and rating in (2, 3, 4):
                        by_rating[rating].append(abs(up - init_p))

        rating_labels = {2: "Confident", 3: "Mixed", 4: "Hedging"}
        show_ratings = [2, 3, 4]
        box_data = [by_rating[r] for r in show_ratings]
        box_labels = [f"{rating_labels[r]}\n(n={len(by_rating[r])})" for r in show_ratings]

        bp_a = ax_a.boxplot(box_data, tick_labels=box_labels, patch_artist=True,
                            widths=0.5, showfliers=False)
        box_colors = ["#0072B2", "#E69F00", "#D55E00"]
        for patch, color in zip(bp_a["boxes"], box_colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.6)
        for i, vals in enumerate(box_data):
            if vals:
                ax_a.scatter([i + 1], [np.mean(vals)], marker="D",
                             color="black", s=40, zorder=5)
        ax_a.set_ylabel("|Probability Shift|")
        ax_a.set_xlabel("Uncertainty in Reasoning")
    else:
        ax_a.text(0.5, 0.5, "No uncertainty ratings", transform=ax_a.transAxes, ha="center")

    # ── (b) Anchoring bias — initial probability vs mean |shift| ──
    # Bin initial probabilities and show mean shift per bin
    for name, (rows, q_data) in runs.items():
        prob_shifts = defaultdict(list)
        for qid, qd in q_data.items():
            init_p = qd.get("initial_probability")
            if init_p is None:
                continue
            for pr in qd.get("probe_results", []):
                if pr.get("success") and pr.get("absolute_shift") is not None:
                    prob_shifts[qid].append(pr["absolute_shift"])

        if not prob_shifts:
            continue

        points = []
        for qid, shifts in prob_shifts.items():
            init_p = q_data[qid]["initial_probability"]
            mean_shift = sum(shifts) / len(shifts)
            points.append((init_p, mean_shift))

        points.sort(key=lambda p: p[0])
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        ax_b.scatter(xs, ys, alpha=0.5, s=30, color=COLORS[name],
                     label=name, edgecolor="none")

    # Add linear regression per model
    from scipy import stats as _sp_stats
    for name, (rows, q_data) in runs.items():
        prob_shifts = defaultdict(list)
        for qid, qd in q_data.items():
            init_p = qd.get("initial_probability")
            if init_p is None:
                continue
            for pr in qd.get("probe_results", []):
                if pr.get("success") and pr.get("absolute_shift") is not None:
                    prob_shifts[qid].append(pr["absolute_shift"])
        if not prob_shifts:
            continue
        xs = [q_data[qid]["initial_probability"] for qid in prob_shifts]
        ys = [sum(s) / len(s) for s in prob_shifts.values()]
        if len(xs) >= 5:
            slope, intercept, r_val, _, _ = _sp_stats.linregress(xs, ys)
            x_fit = np.linspace(min(xs), max(xs), 100)
            ax_b.plot(x_fit, slope * x_fit + intercept,
                      color=COLORS[name], linewidth=2, alpha=0.8)

    ax_b.set_xlabel("Initial Probability")
    ax_b.set_ylabel("Mean |Shift| per Question")
    ax_b.legend(fontsize=8, frameon=False)
    ax_b.set_xlim(0, 1)

    # ── (c) Source-stratified calibration ──
    DATA_SOURCES = {"fred", "dbnomics", "yfinance"}
    SPECULATIVE_SOURCES = {"manifold", "metaculus", "infer", "polymarket"}

    if freeze_vals:
        for src_type, src_set, color, marker in [
            ("Data-anchored", DATA_SOURCES, "#009E73", "o"),
            ("Speculative", SPECULATIVE_SOURCES, "#D55E00", "s"),
        ]:
            all_pairs = []
            for name, (rows, q_data) in runs.items():
                for qid, qd in q_data.items():
                    if qid not in freeze_vals:
                        continue
                    source = qd.get("source", "")
                    if source not in src_set:
                        continue
                    pred = qd.get("initial_probability")
                    if pred is not None:
                        all_pairs.append((pred, freeze_vals[qid]))

            if len(all_pairs) < 3:
                continue

            # Compute mean Brier
            brier = sum((p - a) ** 2 for p, a in all_pairs) / len(all_pairs)

            # Bin for calibration curve
            all_pairs.sort(key=lambda p: p[0])
            n_bins = min(4, len(all_pairs) // 2)
            if n_bins < 2:
                continue
            bin_size = len(all_pairs) // n_bins
            bin_preds, bin_actuals = [], []
            for i in range(n_bins):
                start = i * bin_size
                end = start + bin_size if i < n_bins - 1 else len(all_pairs)
                chunk = all_pairs[start:end]
                bin_preds.append(sum(p for p, _ in chunk) / len(chunk))
                bin_actuals.append(sum(a for _, a in chunk) / len(chunk))

            ax_c.plot(bin_preds, bin_actuals, f"{marker}-", color=color,
                      markersize=8, linewidth=2,
                      label=f"{src_type} (n={len(all_pairs)}, Brier={brier:.3f})")

        ax_c.plot([0, 1], [0, 1], "k--", alpha=0.3, linewidth=1)
        ax_c.set_xlabel("Predicted Probability")
        ax_c.set_ylabel("Ground Truth Probability")
        ax_c.set_xlim(0, 1)
        ax_c.set_ylim(0, 1)
        ax_c.set_aspect("equal")
        ax_c.legend(fontsize=8, loc="upper left", frameon=False)
    else:
        ax_c.text(0.5, 0.5, "No ground truth", transform=ax_c.transAxes, ha="center")

    # ── (d) Probability granularity with Wilson CIs ──
    model_names = list(runs.keys())
    granularities = []
    ci_lows, ci_highs = [], []
    for name, (rows, q_data) in runs.items():
        probs = []
        for qid, qd in q_data.items():
            p = qd.get("initial_probability")
            if p is not None:
                probs.append(p)
            for pr in qd.get("probe_results", []):
                up = pr.get("updated_probability")
                if up is not None and pr.get("success"):
                    probs.append(up)

        # Granularity: fraction NOT at 0.05 increments
        n_granular = sum(1 for p in probs if round(p * 20) / 20 != p)
        centre, lo, hi = _wilson_ci(n_granular, len(probs))
        granularities.append(centre)
        ci_lows.append(centre - lo)
        ci_highs.append(hi - centre)

    ax_d.bar(range(len(model_names)), granularities,
             yerr=[ci_lows, ci_highs], capsize=5,
             color=[COLORS[n] for n in model_names],
             edgecolor="black", linewidth=0.5)
    ax_d.set_xticks(range(len(model_names)))
    ax_d.set_xticklabels([n.replace("-", "\n", 1) for n in model_names], fontsize=9)
    ax_d.set_ylabel("Granularity Score\n(Fraction of Non-Round Probabilities)")
    ax_d.set_ylim(0, 1)

    _label_axes(axes.flat)
    plt.tight_layout()
    plt.savefig(SUPPLEMENT_DIR / "superforecasting_analysis.png")
    plt.savefig(SUPPLEMENT_DIR / "superforecasting_analysis.pdf")
    plt.close()
    print("  Saved supplementary/superforecasting_analysis.png/pdf")


def fig_hedge_vs_confidence(runs: dict):
    """Supplementary: hedging language rate vs distance from 0.5."""
    import re

    HEDGE_WORDS = re.compile(
        r"\b(might|could|possibly|perhaps|uncertain|unlikely|unclear|"
        r"depends|somewhat|partially|moderate|slight|marginal|debatable)\b",
        re.IGNORECASE,
    )

    fig, ax = plt.subplots(figsize=(5, 4.5))

    # Bin by distance from 0.5, per model
    bin_edges = [0, 0.1, 0.2, 0.3, 0.5]
    bin_labels = ["0–0.1", "0.1–0.2", "0.2–0.3", "0.3–0.5"]

    for name, (rows, q_data) in runs.items():
        bin_rates = [[] for _ in range(len(bin_labels))]
        for qid, qd in q_data.items():
            for pr in qd.get("probe_results", []):
                reasoning = pr.get("reasoning", "")
                up = pr.get("updated_probability")
                if not reasoning or up is None or not pr.get("success"):
                    continue
                words = len(reasoning.split())
                if words < 10:
                    continue
                n_hedge = len(HEDGE_WORDS.findall(reasoning))
                hedge_rate = n_hedge / words
                dist = abs(up - 0.5)
                for j in range(len(bin_labels)):
                    if bin_edges[j] <= dist < bin_edges[j + 1]:
                        bin_rates[j].append(hedge_rate)
                        break

        means = [sum(b) / len(b) * 100 if b else 0 for b in bin_rates]
        ax.plot(range(len(bin_labels)), means, "o-", color=COLORS[name],
                markersize=7, linewidth=2, label=name)

    ax.set_xticks(range(len(bin_labels)))
    ax.set_xticklabels(bin_labels)
    ax.set_xlabel("Distance from 0.5 (Confidence Level)")
    ax.set_ylabel("Hedging Word Rate (%)")
    ax.legend(fontsize=8, frameon=False)

    plt.tight_layout()
    plt.savefig(SUPPLEMENT_DIR / "hedge_vs_confidence.png")
    plt.savefig(SUPPLEMENT_DIR / "hedge_vs_confidence.pdf")
    plt.close()
    print("  Saved supplementary/hedge_vs_confidence.png/pdf")


def fig_granularity(runs: dict):
    """Supplementary: probability granularity score by model with Wilson CIs."""
    fig, ax = plt.subplots(figsize=(5, 4.5))
    model_names = list(runs.keys())
    granularities = []
    ci_lows, ci_highs = [], []
    for name, (rows, q_data) in runs.items():
        probs = []
        for qid, qd in q_data.items():
            p = qd.get("initial_probability")
            if p is not None:
                probs.append(p)
            for pr in qd.get("probe_results", []):
                up = pr.get("updated_probability")
                if up is not None and pr.get("success"):
                    probs.append(up)

        # Granularity: fraction NOT at 0.05 increments
        n_granular = sum(1 for p in probs if round(p * 20) / 20 != p)
        centre, lo, hi = _wilson_ci(n_granular, len(probs))
        granularities.append(centre)
        ci_lows.append(centre - lo)
        ci_highs.append(hi - centre)

    ax.bar(range(len(model_names)), granularities,
           yerr=[ci_lows, ci_highs], capsize=5,
           color=[COLORS[n] for n in model_names],
           edgecolor="black", linewidth=0.5)
    ax.set_xticks(range(len(model_names)))
    ax.set_xticklabels([n.replace("-", "\n", 1) for n in model_names], fontsize=9)
    ax.set_ylabel("Granularity Score\n(Fraction of Non-Round Probabilities)")
    ax.set_ylim(0, 1)

    plt.tight_layout()
    plt.savefig(SUPPLEMENT_DIR / "granularity.png")
    plt.savefig(SUPPLEMENT_DIR / "granularity.pdf")
    plt.close()
    print("  Saved supplementary/granularity.png/pdf")


# ═════════════════════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════════════════════

def main():
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    SUPPLEMENT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Generating figures in {FIGURES_DIR}\n")

    runs = _load_all_runs()
    if not runs:
        print("[ERROR] No data loaded")
        return

    # Main figures (1-7)
    print("\n--- Main figures ---")
    fig_dose_response(runs)
    fig_ssr_comparison(runs)
    fig_shift_by_probe_type(runs)
    fig_calibration(runs)
    fig_within_question_consistency(runs)
    fig_reasoning_coherence(runs)
    fig_probability_distributions(runs)

    # Supplementary figures
    print("\n--- Supplementary figures ---")
    fig_superforecasting_analysis(runs)
    fig_cross_model_shifts(runs)
    fig_null_test(runs)
    fig_paired_initial_probabilities(runs)
    fig_hedge_vs_confidence(runs)

    main_n = len(list(FIGURES_DIR.glob("*.png")))
    supp_n = len(list(SUPPLEMENT_DIR.glob("*.png")))
    print(f"\nDone! {main_n} main + {supp_n} supplementary figures")


if __name__ == "__main__":
    main()
