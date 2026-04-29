"""
Generate all paper figures for the Belief Sensitivity analysis.

Outputs saved to paper/figures/main, /supplement, or /internal depending on the figure.

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
FIGURES_DIR = BASE / "paper" / "figures" / "main"
SUPPLEMENT_DIR = BASE / "paper" / "figures" / "supplement"
INTERNAL_DIR = BASE / "paper" / "figures" / "internal"
CAUSAL_DIR = BASE / "outputs" / "sensitivity" / "causal"

MODEL_DIRS = {
    "Llama-3.1-8B": CAUSAL_DIR / "llama_neutral",
    "Llama-3.3-70B": CAUSAL_DIR / "llama_70b_neutral",
    "DeepSeek-V3": CAUSAL_DIR / "deepseek_neutral",
    "Qwen3-235B": CAUSAL_DIR / "qwen_neutral",
    "Gemini-Flash-Lite": CAUSAL_DIR / "gemini_fl_neutral",
    "GPT-OSS-120B": CAUSAL_DIR / "gpt_oss_neutral",
    "Qwen3-32B": CAUSAL_DIR / "qwen_32b_neutral",
}

# Colorblind-safe palette (Wong 2011 / IBM Design)
# Blue, Orange, Vermillion — distinct under all forms of color vision deficiency
COLORS = {
    "Llama-3.1-8B": "#E69F00",        # orange
    "Llama-3.3-70B": "#0072B2",       # blue
    "DeepSeek-V3": "#D55E00",    # vermillion
    "Qwen3-235B": "#009E73",          # green
    "Gemini-Flash-Lite": "#CC79A7",  # reddish purple
    "GPT-OSS-120B": "#882255",       # wine
    "Qwen3-32B": "#56B4E9",          # sky blue
}

# Category palette for probe types (colorblind-safe)
CAT_COLORS = {
    "node": "#0072B2",       # blue
    "edge": "#D55E00",       # vermillion
    "structural": "#009E73", # bluish green (unused — missing_node → node, spurious → edge)
    "control": "#999999",    # gray
}

# For figures: remap structural probes to their natural category
DISPLAY_CATEGORIES = {
    "node_negate_high": "node",
    "node_negate_medium": "node",
    "node_negate_low": "node",
    "node_strengthen": "node",
    "node_strengthen_medium": "node",
    "node_strengthen_low": "node",
    "missing_node": "node",
    "edge_negate_critical": "edge",
    "edge_negate_peripheral": "edge",
    "edge_strengthen_critical": "edge",
    "edge_strengthen_peripheral": "edge",
    "edge_reverse": "edge",
    "edge_spurious": "edge",
    "edge_fabricate": "edge",
    "irrelevant": "control",
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


def _short_model_name(name: str) -> str:
    """Consistent short display name for tick labels (with newline)."""
    _MAP = {
        "Llama-3.1-8B": "Llama\n8B",
        "Llama-3.3-70B": "Llama\n70B",
        "DeepSeek-V3": "DeepSeek\nV3",
        "Qwen3-235B": "Qwen3\n235B",
        "Gemini-Flash-Lite": "Gemini\nFlash-Lite",
    }
    return _MAP.get(name, name)


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
    """Bar chart comparing SSR, within-question Kendall tau, and SAR across models with 95% CIs."""
    from forecast_bench.analysis_causal import (
        structural_sensitivity_ratio,
        spurious_acceptance_rate,
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
        # Control sensitivity: fraction of irrelevant probes where |shift| > 0.05
        irrel = [r for r in rows if r.get("success") and r.get("absolute_shift") is not None
                 and r.get("probe_type") == "irrelevant"]
        if not irrel:
            return 0
        return sum(1 for r in irrel if r["absolute_shift"] > 0.05) / len(irrel)

    # Helper: compute mean within-question Kendall tau for a set of rows
    node_probe_types = {
        "node_negate_high", "node_negate_medium", "node_negate_low",
        "node_strengthen",
    }

    def _within_tau_val(rows):
        from collections import defaultdict as _dd
        q_probes = _dd(list)
        for r in rows:
            if (r.get("success")
                and r.get("absolute_shift") is not None
                and r.get("target_importance") is not None
                and r.get("probe_type") in node_probe_types):
                q_probes[r["question_id"]].append(r)
        taus = []
        for qid, probes in q_probes.items():
            if len(probes) < 4:
                continue
            imp = [p["target_importance"] for p in probes]
            sh = [p["absolute_shift"] for p in probes]
            tau = _kendall_tau(imp, sh)
            if tau is not None:
                taus.append(tau)
        return sum(taus) / len(taus) if taus else 0

    # (a) SSR with CI
    ssrs, ssr_los, ssr_his = [], [], []
    for name, (rows, _) in runs.items():
        pt, lo, hi = _bootstrap_metric(rows, _ssr_val)
        ssrs.append(pt)
        ssr_los.append(pt - lo)
        ssr_his.append(hi - pt)
    axes[0].bar(x, ssrs, yerr=[ssr_los, ssr_his], color=bar_colors,
                edgecolor="black", linewidth=0.5, capsize=5, error_kw={"linewidth": 1.5})
    axes[0].axhline(y=1, color="#444444", linestyle="--", linewidth=1.5)
    axes[0].set_ylabel("Structural Sensitivity Ratio\n(SSR)")
    axes[0].set_xticks(list(x))
    axes[0].set_xticklabels([n.replace("-", "\n", 1) for n in model_names], fontsize=9)

    # (b) Within-question Kendall tau with CI and p-values
    taus_pt, tau_los, tau_his = [], [], []
    tau_ps = []
    for name, (rows, q_data) in runs.items():
        pt, lo, hi = _bootstrap_metric(rows, _within_tau_val)
        taus_pt.append(pt)
        tau_los.append(pt - lo)
        tau_his.append(hi - pt)
        # Compute two-tailed p-value via one-sample t-test on per-question taus (H0: τ = 0)
        from collections import defaultdict as _dd
        q_probes = _dd(list)
        for r in rows:
            if (r.get("success")
                and r.get("absolute_shift") is not None
                and r.get("target_importance") is not None
                and r.get("probe_type") in node_probe_types):
                q_probes[r["question_id"]].append(r)
        per_q_taus = []
        for qid, probes in q_probes.items():
            if len(probes) < 4:
                continue
            imp = [p["target_importance"] for p in probes]
            sh = [p["absolute_shift"] for p in probes]
            tau = _kendall_tau(imp, sh)
            if tau is not None:
                per_q_taus.append(tau)
        if len(per_q_taus) > 1:
            mean_t = sum(per_q_taus) / len(per_q_taus)
            var_t = sum((t - mean_t) ** 2 for t in per_q_taus) / (len(per_q_taus) - 1)
            se_t = (var_t / len(per_q_taus)) ** 0.5 if var_t > 0 else 1e-10
            t_stat = mean_t / se_t
            from forecast_bench.analysis_causal import _t_to_p
            p = _t_to_p(abs(t_stat), len(per_q_taus) - 1)
        else:
            p = 1.0
        tau_ps.append(p)
    axes[1].bar(x, taus_pt, yerr=[tau_los, tau_his], color=bar_colors,
                edgecolor="black", linewidth=0.5, capsize=5, error_kw={"linewidth": 1.5})
    axes[1].axhline(y=0, color="#444444", linestyle="--", linewidth=1.5)
    # Add significance stars above bars
    for i, (tau_v, hi, p) in enumerate(zip(taus_pt, tau_his, tau_ps)):
        if p < 0.001:
            stars = "***"
        elif p < 0.01:
            stars = "**"
        elif p < 0.05:
            stars = "*"
        else:
            stars = "n.s."
        y_pos = tau_v + hi if tau_v >= 0 else tau_v - tau_los[i]
        axes[1].annotate(stars, xy=(i, y_pos), xytext=(0, 4),
                         textcoords="offset points", ha="center", fontsize=13, fontweight="bold")
    axes[1].set_ylabel("Within-Question Importance–Shift\n(Mean Kendall τ)")
    axes[1].set_xticks(list(x))
    axes[1].set_xticklabels([n.replace("-", "\n", 1) for n in model_names], fontsize=9)

    # (c) SAR with CI
    sars, sar_los, sar_his = [], [], []
    for name, (rows, _) in runs.items():
        pt, lo, hi = _bootstrap_metric(rows, _sar_val)
        sars.append(pt)
        sar_los.append(pt - lo)
        sar_his.append(hi - pt)
    axes[2].bar(x, sars, yerr=[sar_los, sar_his], color=bar_colors,
                edgecolor="black", linewidth=0.5, capsize=5, error_kw={"linewidth": 1.5})
    axes[2].set_ylabel("Control Sensitivity\n(Frac. irrelevant probes with |shift| > 0.05)")
    axes[2].set_xticks(list(x))
    axes[2].set_xticklabels([n.replace("-", "\n", 1) for n in model_names], fontsize=9)
    axes[2].set_ylim(0, 1)

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
    """Horizontal bar chart of mean |shift| by probe type with 95% CIs."""
    type_shifts = defaultdict(list)
    for name, (rows, _) in runs.items():
        for r in rows:
            if not r.get("success") or r.get("absolute_shift") is None:
                continue
            pt = r.get("probe_type", "unknown")
            # Normalize known typos/variants to canonical probe types
            PROBE_TYPE_NORMALIZE = {
                "irlevant": "irrelevant",
                "edge_missing": "edge_spurious",
                "edge_omitted": "edge_spurious",
                "edge_added": "edge_spurious",
                "edge_addition": "edge_spurious",
                "edge_add": "edge_spurious",
                "edge_add_causal": "edge_spurious",
                "edge_add_direct": "edge_spurious",
                "edge_feedback": "edge_spurious",
                "edge_fabricate": "edge_spurious",
            }
            pt = PROBE_TYPE_NORMALIZE.get(pt, pt)
            type_shifts[pt].append(r["absolute_shift"])

    # Readable labels
    PRETTY_LABELS = {
        "node_negate_high": "Negate High-Importance Node",
        "node_negate_medium": "Negate Medium-Importance Node",
        "node_negate_low": "Negate Low-Importance Node",
        "node_strengthen": "Strengthen High-Importance Node",
        "node_strengthen_medium": "Strengthen Medium Node",
        "node_strengthen_low": "Strengthen Low Node",
        "edge_negate_critical": "Negate Shortest-Path Edge",
        "edge_negate_peripheral": "Negate Peripheral Edge",
        "edge_strengthen_critical": "Strengthen Shortest-Path Edge",
        "edge_strengthen_peripheral": "Strengthen Peripheral Edge",
        "edge_reverse": "Reverse Edge",
        "edge_spurious": "Spurious Edge",

        "missing_node": "Missing Node",
        "irrelevant": "Irrelevant (Control)",
    }

    # Order by mean shift (ascending so highest is at top of horizontal plot)
    ordered = sorted(type_shifts.items(),
                     key=lambda kv: sum(kv[1]) / len(kv[1]) if kv[1] else 0)
    labels = [k for k, _ in ordered]
    data = [v for _, v in ordered]

    # Compute means and 95% CIs
    means = []
    ci_los = []
    ci_his = []
    for vals in data:
        n = len(vals)
        m = sum(vals) / n if n else 0
        means.append(m)
        if n > 1:
            se = (sum((v - m) ** 2 for v in vals) / (n - 1)) ** 0.5 / n ** 0.5
            ci_los.append(1.96 * se)
            ci_his.append(1.96 * se)
        else:
            ci_los.append(0)
            ci_his.append(0)

    # Color by category
    face_colors = [CAT_COLORS.get(DISPLAY_CATEGORIES.get(l, "control"), "#999") for l in labels]
    pretty = [PRETTY_LABELS.get(l, l.replace("_", " ").title()) for l in labels]

    fig, ax = plt.subplots(figsize=(9, 6))
    y = list(range(len(labels)))
    for i, (m, lo, hi, color) in enumerate(zip(means, ci_los, ci_his, face_colors)):
        ax.plot([m - lo, m + hi], [i, i], color=color, linewidth=3, solid_capstyle="round")
        ax.plot(m, i, "o", color=color, markersize=8, markeredgecolor="black",
                markeredgewidth=0.8, zorder=5)
    ax.set_yticks(y)
    ax.set_yticklabels(pretty, fontsize=10)
    ax.set_xlabel("Mean |Probability Shift|")
    ax.axvline(x=0, color="#333333", linewidth=1.0, linestyle="--", zorder=0)

    # Legend for categories
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=CAT_COLORS["node"], alpha=0.7, label="Node probes"),
        Patch(facecolor=CAT_COLORS["edge"], alpha=0.7, label="Edge probes"),
        Patch(facecolor=CAT_COLORS["control"], alpha=0.7, label="Control probes"),
    ]
    ax.legend(handles=legend_elements, loc="lower right", frameon=False, fontsize=9)

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "shift_by_probe_type.png")
    plt.savefig(FIGURES_DIR / "shift_by_probe_type.pdf")
    plt.close()
    print("  Saved shift_by_probe_type.png/pdf")


# ═════════════════════════════════════════════════════════════════════════════
# FIGURE 4: Calibration Curves
# ═════════════════════════════════════════════════════════════════════════════

def fig_calibration(runs: dict):
    """Combined figure: (a) cross-model initial probabilities,
    (b) inter-model agreement heatmap, (c) calibration curve."""
    from matplotlib.patches import Patch
    from scipy import stats as sp_stats

    freeze_vals = _load_freeze_values()
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

    shared_qids = set.intersection(*(set(p.keys()) for p in model_probs.values()))
    shared_qids = sorted(shared_qids)

    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 6),
                                         gridspec_kw={"width_ratios": [1, 1.1, 1],
                                                      "wspace": 0.35})

    # ── (a) Ridge plot of initial probability distributions ──
    from scipy.stats import gaussian_kde
    short_names = [_short_model_name(nm) for nm in model_names]
    x_grid = np.linspace(0, 1, 200)
    ridge_spacing = 0.6  # vertical offset between ridges

    for i, name in enumerate(model_names):
        probs = list(model_probs[name].values())
        if len(probs) < 5:
            continue
        kde = gaussian_kde(probs, bw_method=0.15)
        density = kde(x_grid)
        # Normalize so max height is consistent
        density = density / density.max() * 0.5
        baseline = i * ridge_spacing
        ax1.fill_between(x_grid, baseline, baseline + density,
                         color=COLORS[name], alpha=0.6, zorder=2)
        ax1.plot(x_grid, baseline + density,
                 color=COLORS[name], linewidth=1.5, zorder=3)

    ax1.set_yticks([i * ridge_spacing for i in range(len(model_names))])
    ax1.set_yticklabels(short_names, fontsize=9)
    ax1.set_xlabel("Initial Probability")
    ax1.set_xlim(0, 1)
    ax1.set_ylim(-0.1, len(model_names) * ridge_spacing)
    ax1.spines["left"].set_visible(False)
    ax1.tick_params(axis="y", length=0)

    # ── (b) Inter-model agreement heatmap ──
    n = len(model_names)
    rho_matrix = np.ones((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            shared = sorted(set(model_probs[model_names[i]]) & set(model_probs[model_names[j]]))
            if len(shared) < 5:
                rho_matrix[i, j] = rho_matrix[j, i] = np.nan
                continue
            p_i = [model_probs[model_names[i]][q] for q in shared]
            p_j = [model_probs[model_names[j]][q] for q in shared]
            rho, _ = sp_stats.spearmanr(p_i, p_j)
            rho_matrix[i, j] = rho_matrix[j, i] = rho

    im = ax2.imshow(rho_matrix, cmap="RdYlBu", vmin=0, vmax=1, aspect="equal")
    ax2.set_xticks(range(n))
    ax2.set_yticks(range(n))
    ax2.set_xticklabels([_short_model_name(nm) for nm in model_names], fontsize=8, rotation=45, ha="right")
    ax2.set_yticklabels([_short_model_name(nm) for nm in model_names], fontsize=8)

    for i in range(n):
        for j in range(n):
            val = rho_matrix[i, j]
            if not np.isnan(val):
                color = "white" if val < 0.5 else "black"
                ax2.text(j, i, f"{val:.2f}", ha="center", va="center",
                         fontsize=9, color=color, fontweight="bold" if i == j else "normal")

    cbar = fig.colorbar(im, ax=ax2, shrink=0.7, pad=0.08)
    cbar.set_label("Spearman ρ", fontsize=9)

    # ── (c) Calibration curve ──
    if freeze_vals:
        ax3.plot([0, 1], [0, 1], "k--", alpha=0.3, linewidth=1)

        for name, (rows, q_data) in runs.items():
            pairs = []
            for qid, qd in q_data.items():
                if qid in freeze_vals:
                    pred = qd.get("initial_probability")
                    if pred is not None:
                        pairs.append((pred, freeze_vals[qid]))

            if len(pairs) < 5:
                continue

            pairs.sort(key=lambda p: p[0])
            n_bins = 5
            bin_size = len(pairs) // n_bins
            bin_preds, bin_actuals, bin_ns = [], [], []
            for i in range(n_bins):
                start = i * bin_size
                end = start + bin_size if i < n_bins - 1 else len(pairs)
                chunk = pairs[start:end]
                bin_preds.append(sum(p for p, _ in chunk) / len(chunk))
                bin_actuals.append(sum(a for _, a in chunk) / len(chunk))
                bin_ns.append(len(chunk))

            ax3.plot(bin_preds, bin_actuals, "o-", color=COLORS[name], markersize=8,
                     linewidth=2)

            for bp, ba, bn in zip(bin_preds, bin_actuals, bin_ns):
                se = (ba * (1 - ba) / max(bn, 1)) ** 0.5
                ax3.fill_between([bp - 0.01, bp + 0.01],
                                [ba - 1.96 * se] * 2, [ba + 1.96 * se] * 2,
                                alpha=0.1, color=COLORS[name])

        ax3.set_xlabel("LLM Predicted Probability", fontsize=12)
        ax3.set_ylabel("Reference Probability", fontsize=12)
        ax3.set_xlim(0, 1)
        ax3.set_ylim(0, 1)
    else:
        ax3.text(0.5, 0.5, "No market reference data", ha="center", va="center",
                 transform=ax3.transAxes)

    # Align panel labels at the same vertical level using figure coords
    fig.canvas.draw()
    for ax, label in zip([ax1, ax2, ax3], ["(a)", "(b)", "(c)"]):
        # Get the top of the tallest axis in figure coords
        bbox = ax.get_position()
        fig.text(bbox.x0 - 0.01, 0.95, label,
                 fontsize=14, fontweight="bold", va="bottom", ha="right")

    # Shared legend at bottom
    legend_handles = [Patch(facecolor=COLORS[name], label=name) for name in model_names]
    fig.legend(handles=legend_handles, loc="lower center", ncol=len(model_names),
               fontsize=9, frameon=False, bbox_to_anchor=(0.5, -0.02))
    plt.savefig(FIGURES_DIR / "initial_probabilities.png", dpi=300, bbox_inches="tight")
    plt.savefig(FIGURES_DIR / "initial_probabilities.pdf", bbox_inches="tight")
    plt.close()
    print("  Saved initial_probabilities.png/pdf")


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
                       "deepseek": "DeepSeek-V3", "qwen": "Qwen3-235B",
                       "gemini": "Gemini-Flash-Lite"}

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
    # ax1.grid(axis="x", alpha=0.2)

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

    # Shift by probe category (node / edge / control) per model
    cat_order = ["node", "edge", "control"]
    cat_labels = ["Node", "Edge", "Control"]
    cat_colors_list = [CAT_COLORS[c] for c in cat_order]

    x = np.arange(len(model_names))
    n_cats = len(cat_order)
    width = 0.25

    for ci, cat in enumerate(cat_order):
        means = []
        ses = []
        for name, (rows, _) in runs.items():
            vals = [r["absolute_shift"] for r in rows
                    if r.get("success") and r.get("absolute_shift") is not None
                    and DISPLAY_CATEGORIES.get(r.get("probe_type", ""), "") == cat]
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
    ax2.legend(frameon=False, loc="upper left")

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
    """Two-panel forest plot: (a) shift separation, (b) reasoning embedding separation.

    Both panels compare structural vs control probes per model using a forest plot
    with per-model effects and a pooled estimate.
    """
    from collections import defaultdict
    from scipy.stats import wilcoxon
    import json as _json

    model_names = list(runs.keys())

    # ── Panel (a) data: shift difference (real - irrelevant) ──
    a_labels, a_effects, a_ci_los, a_ci_his = [], [], [], []
    all_diffs_a = []

    for name in model_names:
        rows = runs[name][0]
        question_groups = defaultdict(lambda: {"real": [], "irrelevant": []})
        for r in rows:
            if not r.get("success") or r.get("absolute_shift") is None:
                continue
            qid = r["question_id"]
            if r.get("probe_type") == "irrelevant":
                question_groups[qid]["irrelevant"].append(r["absolute_shift"])
            else:
                question_groups[qid]["real"].append(r["absolute_shift"])

        diffs = []
        for qid, groups in question_groups.items():
            if groups["real"] and groups["irrelevant"]:
                diffs.append(
                    sum(groups["real"]) / len(groups["real"])
                    - sum(groups["irrelevant"]) / len(groups["irrelevant"])
                )
        all_diffs_a.extend(diffs)

        mean_d = np.mean(diffs)
        se = np.std(diffs, ddof=1) / np.sqrt(len(diffs))
        a_labels.append(name)
        a_effects.append(mean_d)
        a_ci_los.append(mean_d - 1.96 * se)
        a_ci_his.append(mean_d + 1.96 * se)

    # Pooled
    pm = np.mean(all_diffs_a)
    pse = np.std(all_diffs_a, ddof=1) / np.sqrt(len(all_diffs_a))
    a_labels.append("Pooled")
    a_effects.append(pm)
    a_ci_los.append(pm - 1.96 * pse)
    a_ci_his.append(pm + 1.96 * pse)

    # ── Panel (b) data: embedding similarity difference (structural - control) ──
    b_labels, b_effects, b_ci_los, b_ci_his = [], [], [], []
    all_diffs_b = []

    embeddings_path = CAUSAL_DIR / "reasoning_embeddings.npz"
    keys_path = CAUSAL_DIR / "reasoning_embeddings_keys.json"
    has_embeddings = embeddings_path.exists() and keys_path.exists()

    embed_cache_path = CAUSAL_DIR / "embedding_separation_cache.json"

    if has_embeddings:
        # Check cache first
        if embed_cache_path.exists():
            cached = _json.loads(embed_cache_path.read_text(encoding="utf-8"))
            _cached_diffs = cached.get("per_model_diffs", {})
        else:
            _cached_diffs = {}

        keys = _json.loads(keys_path.read_text(encoding="utf-8"))
        data = np.load(str(embeddings_path))
        embeddings = data["embeddings"]

        CONTROL_TYPES = {"irrelevant", "edge_spurious", "missing_node"}

        # Index by (model, qid)
        model_q_index = defaultdict(list)
        for i, k in enumerate(keys):
            parts = k.split("|")
            if len(parts) < 4:
                continue
            pt = _EMBED_PROBE_NORMALIZE.get(parts[1], parts[1])
            if pt not in _IMPORTANCE_TIER:
                continue
            is_control = pt in CONTROL_TYPES
            model_q_index[(parts[3], parts[0])].append((is_control, i))

        def _cosine_sim(a, b):
            dot = np.dot(a, b)
            na, nb = np.linalg.norm(a), np.linalg.norm(b)
            return dot / (na * nb) if na > 0 and nb > 0 else 0.0

        model_key_map = {
            "Llama-3.1-8B": "llama-8b", "Llama-3.3-70B": "llama-70b",
            "DeepSeek-V3": "deepseek", "Qwen3-235B": "qwen",
            "Gemini-Flash-Lite": "gemini",
        }

        for name in model_names:
            mk = model_key_map.get(name)
            if not mk:
                continue

            # Use cache if available
            if mk in _cached_diffs:
                diffs = _cached_diffs[mk]
                all_diffs_b.extend(diffs)
                mean_d = np.mean(diffs) if diffs else 0
                se = np.std(diffs, ddof=1) / np.sqrt(len(diffs)) if len(diffs) > 1 else 0
                b_labels.append(name)
                b_effects.append(mean_d)
                b_ci_los.append(mean_d - 1.96 * se)
                b_ci_his.append(mean_d + 1.96 * se)
                continue

            model_questions = set(qid for (m, qid) in model_q_index if m == mk)
            diffs = []
            for qid in model_questions:
                entries = model_q_index[(mk, qid)]
                ctrl_idx = [idx for is_ctrl, idx in entries if is_ctrl]
                struct_idx = [idx for is_ctrl, idx in entries if not is_ctrl]
                if len(ctrl_idx) < 2 or len(struct_idx) < 2:
                    continue

                # Within-structural mean sim
                rng = np.random.RandomState(42)
                pairs_s = [(struct_idx[a], struct_idx[b])
                           for a in range(len(struct_idx)) for b in range(a+1, len(struct_idx))]
                if len(pairs_s) > 50:
                    sel = rng.choice(len(pairs_s), 50, replace=False)
                    pairs_s = [pairs_s[p] for p in sel]
                s_sims = [_cosine_sim(embeddings[a], embeddings[b]) for a, b in pairs_s]

                # Within-control mean sim
                pairs_c = [(ctrl_idx[a], ctrl_idx[b])
                           for a in range(len(ctrl_idx)) for b in range(a+1, len(ctrl_idx))]
                c_sims = [_cosine_sim(embeddings[a], embeddings[b]) for a, b in pairs_c]

                if s_sims and c_sims:
                    diffs.append(sum(s_sims)/len(s_sims) - sum(c_sims)/len(c_sims))

            _cached_diffs[mk] = diffs
            all_diffs_b.extend(diffs)
            mean_d = np.mean(diffs) if diffs else 0
            se = np.std(diffs, ddof=1) / np.sqrt(len(diffs)) if len(diffs) > 1 else 0
            b_labels.append(name)
            b_effects.append(mean_d)
            b_ci_los.append(mean_d - 1.96 * se)
            b_ci_his.append(mean_d + 1.96 * se)

        # Save cache (convert numpy floats to Python floats)
        serializable = {k: [float(v) for v in vals] for k, vals in _cached_diffs.items()}
        embed_cache_path.write_text(
            _json.dumps({"per_model_diffs": serializable}, indent=2),
            encoding="utf-8",
        )

        # Pooled
        pm = np.mean(all_diffs_b)
        pse = np.std(all_diffs_b, ddof=1) / np.sqrt(len(all_diffs_b))
        b_labels.append("Pooled")
        b_effects.append(pm)
        b_ci_los.append(pm - 1.96 * pse)
        b_ci_his.append(pm + 1.96 * pse)

    # ── Draw ──
    n_panels = 2 if has_embeddings else 1
    fig, axes = plt.subplots(1, n_panels, figsize=(7 * n_panels, 4.5))
    if n_panels == 1:
        axes = [axes]

    def _draw_forest(ax, labels, effects, ci_los, ci_his, xlabel):
        n = len(labels)
        y_pos = list(range(n))
        color_list = list(COLORS.values())
        for i in range(n - 1):
            c = color_list[i] if i < len(color_list) else "#333333"
            ax.plot(effects[i], y_pos[i], "o", color=c, markersize=10, zorder=5)
            ax.plot([ci_los[i], ci_his[i]], [y_pos[i], y_pos[i]],
                    color=c, linewidth=2.5, zorder=4)
        # Pooled
        pi = n - 1
        ax.plot(effects[pi], y_pos[pi], "D", color="black", markersize=11, zorder=5)
        ax.plot([ci_los[pi], ci_his[pi]], [y_pos[pi], y_pos[pi]],
                color="black", linewidth=3, zorder=4)
        ax.axhline(y=n - 1.5, color="#CCCCCC", linewidth=1, linestyle="-")
        ax.axvline(x=0, color="#999999", linewidth=1, linestyle="--", zorder=1)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels, fontsize=11, fontweight="bold")
        ax.invert_yaxis()
        ax.set_xlabel(xlabel, fontsize=10)
        ax.set_xlim(-0.01, None)

    _draw_forest(axes[0], a_labels, a_effects, a_ci_los, a_ci_his,
                 "Mean Difference in |Shift|\n(Structural − Control)")

    if has_embeddings:
        ax = axes[1]
        model_colors_map = {
            "llama-8b": "#E69F00", "llama-70b": "#0072B2",
            "deepseek": "#D55E00", "qwen": "#009E73", "gemini": "#CC79A7",
        }
        model_key_order = ["llama-8b", "llama-70b", "deepseek", "qwen", "gemini"]

        # Reconstruct per-model structural vs control means from cached diffs
        # diffs = structural_sim - control_sim per question, so we need the raw values
        # Instead, show the paired bar chart (structural vs control similarity)
        x_pos = np.arange(len(model_key_order))
        width = 0.35

        # Recompute structural and control means from the embedding data
        struct_means, ctrl_means = [], []
        struct_cis, ctrl_cis = [], []

        for mk in model_key_order:
            model_questions = set(qid for (m, qid) in model_q_index if m == mk)
            s_vals, c_vals = [], []
            for qid in model_questions:
                entries = model_q_index[(mk, qid)]
                ctrl_idx = [idx for is_ctrl, idx in entries if is_ctrl]
                struct_idx = [idx for is_ctrl, idx in entries if not is_ctrl]
                if len(ctrl_idx) < 2 or len(struct_idx) < 2:
                    continue

                rng = np.random.RandomState(42)
                pairs_s = [(struct_idx[a], struct_idx[b])
                           for a in range(len(struct_idx)) for b in range(a+1, len(struct_idx))]
                if len(pairs_s) > 50:
                    sel = rng.choice(len(pairs_s), 50, replace=False)
                    pairs_s = [pairs_s[p] for p in sel]

                def _cos(a, b):
                    d = np.dot(a, b)
                    na, nb = np.linalg.norm(a), np.linalg.norm(b)
                    return d / (na * nb) if na > 0 and nb > 0 else 0.0

                ss = [_cos(embeddings[a], embeddings[b]) for a, b in pairs_s]
                pairs_c = [(ctrl_idx[a], ctrl_idx[b])
                           for a in range(len(ctrl_idx)) for b in range(a+1, len(ctrl_idx))]
                cs = [_cos(embeddings[a], embeddings[b]) for a, b in pairs_c]

                if ss and cs:
                    s_vals.append(sum(ss) / len(ss))
                    c_vals.append(sum(cs) / len(cs))

            # Means
            s_m = sum(s_vals) / len(s_vals) if s_vals else 0
            c_m = sum(c_vals) / len(c_vals) if c_vals else 0
            struct_means.append(s_m)
            ctrl_means.append(c_m)

            # Bootstrap CIs
            for vals, ci_list in [(s_vals, struct_cis), (c_vals, ctrl_cis)]:
                m = sum(vals) / len(vals) if vals else 0
                boot_rng = np.random.RandomState(42)
                boot = []
                if len(vals) > 0:
                    for _ in range(2000):
                        sample = boot_rng.choice(vals, len(vals), replace=True)
                        boot.append(sum(sample) / len(sample))
                if boot:
                    boot.sort()
                    lo = boot[int(0.025 * len(boot))]
                    hi = boot[int(0.975 * len(boot))]
                    ci_list.append((m - lo, hi - m))
                else:
                    ci_list.append((0, 0))

        _MODEL_DISPLAY_SHORT = {
            "llama-8b": "Llama\n8B", "llama-70b": "Llama\n70B",
            "deepseek": "DeepSeek\nV3", "qwen": "Qwen3\n235B",
            "gemini": "Gemini\nFlash-Lite",
        }

        # Solid = structural, hatched = control
        ax.bar(x_pos, struct_means, width,
               yerr=[[c[0] for c in struct_cis], [c[1] for c in struct_cis]],
               color=[model_colors_map[m] for m in model_key_order],
               edgecolor="black", linewidth=0.5, capsize=3,
               error_kw={"linewidth": 1}, label="Structural Probes")
        ax.bar(x_pos + width, ctrl_means, width,
               yerr=[[c[0] for c in ctrl_cis], [c[1] for c in ctrl_cis]],
               color=[model_colors_map[m] for m in model_key_order],
               edgecolor="black", linewidth=0.5, capsize=3, hatch="//",
               error_kw={"linewidth": 1}, alpha=0.7, label="Control Probes")

        # Paired t-test brackets
        from forecast_bench.analysis_causal import _t_to_p as _ttp
        for i, mk in enumerate(model_key_order):
            diffs = _cached_diffs.get(mk, [])
            if len(diffs) > 1:
                mean_d = sum(diffs) / len(diffs)
                var_d = sum((d - mean_d) ** 2 for d in diffs) / (len(diffs) - 1)
                se_d = (var_d / len(diffs)) ** 0.5 if var_d > 0 else 1e-10
                p = _ttp(abs(mean_d / se_d), len(diffs) - 1)
            else:
                p = 1.0
            stars = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "n.s."
            y_top = max(struct_means[i], ctrl_means[i]) + 0.015
            h = 0.005
            x_l, x_r = x_pos[i], x_pos[i] + width
            ax.plot([x_l, x_l, x_r, x_r], [y_top, y_top + h, y_top + h, y_top],
                    color="black", linewidth=0.8, clip_on=False)
            ax.annotate(stars, xy=((x_l + x_r) / 2, y_top + h), xytext=(0, 1),
                        textcoords="offset points", ha="center", fontsize=9, fontweight="bold")

        ax.set_ylabel("Within-Question Cosine Similarity\n(Reasoning Text)")
        ax.set_xticks(x_pos + width / 2)
        ax.set_xticklabels([_MODEL_DISPLAY_SHORT[m] for m in model_key_order], fontsize=8)
        ax.set_ylim(0.55, 0.86)
        # Custom legend with neutral gray swatches
        from matplotlib.patches import Patch
        legend_handles = [
            Patch(facecolor="#888888", edgecolor="black", linewidth=0.5,
                  label="Structural Probes"),
            Patch(facecolor="#888888", edgecolor="black", linewidth=0.5,
                  alpha=0.7, hatch="//", label="Control Probes"),
        ]
        ax.legend(handles=legend_handles, fontsize=8, loc="upper left", frameon=False)

    _label_axes(axes)
    plt.tight_layout()
    plt.savefig(SUPPLEMENT_DIR / "null_test.png", dpi=300, bbox_inches="tight")
    plt.savefig(SUPPLEMENT_DIR / "null_test.pdf", bbox_inches="tight")
    plt.close()
    print("  Saved supplementary/null_test.png/pdf")


# ═════════════════════════════════════════════════════════════════════════════
# FIGURE 10: Paired Initial Probabilities Across Models
# ═════════════════════════════════════════════════════════════════════════════

def fig_paired_initial_probabilities(runs: dict):
    """Correlation heatmap of initial probabilities across models."""
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

    # Build correlation matrix
    n = len(model_names)
    corr_matrix = np.ones((n, n))
    n_shared_matrix = np.zeros((n, n), dtype=int)

    for i in range(n):
        for j in range(i + 1, n):
            m1, m2 = model_names[i], model_names[j]
            shared = sorted(set(model_probs[m1].keys()) & set(model_probs[m2].keys()))
            n_shared_matrix[i, j] = n_shared_matrix[j, i] = len(shared)
            if shared:
                x = [model_probs[m1][qid] for qid in shared]
                y = [model_probs[m2][qid] for qid in shared]
                rho = _spearman_correlation(x, y)
                corr_matrix[i, j] = corr_matrix[j, i] = rho

    fig, ax = plt.subplots(figsize=(5.5, 4.5))
    # Mask lower triangle and diagonal
    mask = np.tri(n, k=0, dtype=bool)
    masked = np.ma.array(corr_matrix, mask=mask)
    im = ax.imshow(masked, cmap="BuGn", vmin=0, vmax=1, aspect="equal")

    # White out masked cells (lower triangle + diagonal)
    for i in range(n):
        for j in range(i + 1):
            ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1,
                                       facecolor="white", edgecolor="white", linewidth=0))

    # Hide spines and ticks on masked side
    ax.spines[:].set_visible(False)

    # Annotate upper triangle only (no diagonal)
    for i in range(n):
        for j in range(i + 1, n):
            rho = corr_matrix[i, j]
            ns = n_shared_matrix[i, j]
            ax.text(j, i, f"ρ={rho:.2f}\n(n={ns})", ha="center", va="center",
                    fontsize=9, color="white" if rho > 0.65 else "black")

    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    short_names = [_short_model_name(nm).replace("\n", " ") for nm in model_names]
    ax.set_xticklabels(short_names, fontsize=9, rotation=30, ha="right")
    ax.set_yticklabels(short_names, fontsize=9)

    cbar = fig.colorbar(im, ax=ax, shrink=0.8, label="Spearman ρ")
    cbar.ax.tick_params(labelsize=9)

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
    """Two-panel analysis of superforecasting traits in LLM forecasters.

    (a) Reasoning uncertainty — LLM-judge rating vs |shift|
    (b) Probability granularity by model
    """
    import json as _json

    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(11, 5))

    # ── (a) Uncertainty rating (LLM judge) vs shift — pooled boxplot ──
    judge_rating_path = CAUSAL_DIR / "uncertainty_judge_ratings.json"
    judge_key_map = {"Llama-3.1-8B": "llama-8b", "Llama-3.3-70B": "llama-70b",
                     "DeepSeek-V3": "deepseek", "Qwen3-235B": "qwen",
                     "Gemini-Flash-Lite": "gemini"}

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

    # ── (b) Probability granularity with Wilson CIs ──
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

    ax_b.bar(range(len(model_names)), granularities,
             yerr=[ci_lows, ci_highs], capsize=5,
             color=[COLORS[n] for n in model_names],
             edgecolor="black", linewidth=0.5)
    ax_b.set_xticks(range(len(model_names)))
    ax_b.set_xticklabels([n.replace("-", "\n", 1) for n in model_names], fontsize=8)
    ax_b.set_ylabel("Granularity Score\n(Fraction of Non-Round Probabilities)")
    ax_b.set_ylim(0, 1)

    _label_axes([ax_a, ax_b])
    plt.tight_layout()
    plt.savefig(SUPPLEMENT_DIR / "superforecasting_analysis.png", dpi=300, bbox_inches="tight")
    plt.savefig(SUPPLEMENT_DIR / "superforecasting_analysis.pdf", bbox_inches="tight")
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
# FIGURE: Shift Directionality
# ═════════════════════════════════════════════════════════════════════════════

def fig_shift_directionality(runs: dict):
    """Bar chart: % of probes that shift in the expected direction, by model.

    (a) Negate probes → should decrease confidence (move toward 0.5)
    (b) Strengthen probes → should increase confidence (move away from 0.5)
    (c) Irrelevant probes → mean signed shift ≈ 0 (no systematic bias)
    """
    negation_types = {
        "node_negate_high", "node_negate_medium", "node_negate_low",
        "edge_negate_critical", "edge_negate_peripheral",
    }
    strengthen_types = {"node_strengthen", "node_strengthen_medium", "node_strengthen_low",
                        "edge_strengthen_critical", "edge_strengthen_peripheral"}

    model_names = list(runs.keys())
    neg_pcts = []
    str_pcts = []
    ctrl_means = []
    ctrl_cis = []

    for name in model_names:
        rows, _ = runs[name]
        neg_correct, neg_total = 0, 0
        str_correct, str_total = 0, 0
        ctrl_shifts = []

        for r in rows:
            if not r.get("success") or r.get("updated_probability") is None:
                continue
            pt = r.get("probe_type", "")
            if pt == "irlevant":
                pt = "irrelevant"
            initial = r.get("initial_probability")
            updated = r.get("updated_probability")
            if initial is None or updated is None:
                continue

            initial_conf = abs(initial - 0.5)
            updated_conf = abs(updated - 0.5)

            if pt in negation_types:
                neg_total += 1
                if updated_conf < initial_conf:
                    neg_correct += 1
            elif pt in strengthen_types:
                str_total += 1
                if updated_conf > initial_conf:
                    str_correct += 1
            elif pt == "irrelevant":
                ctrl_shifts.append(updated - initial)

        neg_pcts.append(neg_correct / neg_total * 100 if neg_total else 0)
        str_pcts.append(str_correct / str_total * 100 if str_total else 0)

        if ctrl_shifts:
            m = sum(ctrl_shifts) / len(ctrl_shifts)
            se = (sum((s - m) ** 2 for s in ctrl_shifts) / (len(ctrl_shifts) - 1)) ** 0.5 / len(ctrl_shifts) ** 0.5
            ctrl_means.append(m)
            ctrl_cis.append(1.96 * se)
        else:
            ctrl_means.append(0)
            ctrl_cis.append(0)

    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    _label_axes(axes)
    x = np.arange(len(model_names))
    short_names = [_short_model_name(n) for n in model_names]
    bar_colors = [COLORS[n] for n in model_names]

    # (a) Negation
    axes[0].bar(x, neg_pcts, color=bar_colors, edgecolor="none")
    axes[0].axhline(50, color="#999", linestyle="--", linewidth=1, zorder=0)
    axes[0].set_ylabel("% Correct Direction")
    axes[0].set_title("Negate Probes\n(should decrease confidence)")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(short_names, fontsize=9)
    axes[0].set_ylim(0, 100)

    # (b) Strengthen
    axes[1].bar(x, str_pcts, color=bar_colors, edgecolor="none")
    axes[1].axhline(50, color="#999", linestyle="--", linewidth=1, zorder=0)
    axes[1].set_title("Strengthen Probes\n(should increase confidence)")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(short_names, fontsize=9)
    axes[1].set_ylim(0, 100)

    # (c) Irrelevant mean signed shift
    axes[2].bar(x, ctrl_means, yerr=ctrl_cis, color=bar_colors, edgecolor="none",
                capsize=4, error_kw={"linewidth": 1.5})
    axes[2].axhline(0, color="#999", linestyle="--", linewidth=1, zorder=0)
    axes[2].set_ylabel("Mean Signed Shift")
    axes[2].set_title("Irrelevant Probes\n(should be ≈ 0)")
    axes[2].set_xticks(x)
    axes[2].set_xticklabels(short_names, fontsize=9)

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "shift_directionality.png")
    plt.savefig(FIGURES_DIR / "shift_directionality.pdf")
    plt.close()
    print("  Saved shift_directionality.png/pdf")


# ═════════════════════════════════════════════════════════════════════════════
# FIGURE: Causal Bottleneck Sensitivity
# ═════════════════════════════════════════════════════════════════════════════

def fig_bottleneck_sensitivity(runs: dict):
    """Test whether removing a bottleneck node (sole path to outcome) causes
    larger shifts than removing a node with redundant paths.

    For each question DAG, we classify probed factor nodes as:
    - Bottleneck: removing the node would disconnect at least one source from
      the outcome (i.e., it's a cut vertex on some source→outcome path).
    - Redundant: alternative paths exist even if the node is removed.

    (a) Mean |shift| for bottleneck vs redundant nodes per model.
    (b) Scatter of path_relevance vs |shift| pooled across models.
    """
    import networkx as nx

    model_names = list(runs.keys())
    bottleneck_shifts = {n: [] for n in model_names}
    redundant_shifts = {n: [] for n in model_names}
    all_path_rel = []
    all_shifts = []

    for name, (rows, q_data) in runs.items():
        for qid, qinfo in q_data.items():
            nodes = qinfo.get("nodes", [])
            edges = qinfo.get("edges", [])
            na = qinfo.get("network_analysis", {})
            outcome = na.get("outcome_node")
            if not outcome or len(nodes) < 3:
                continue

            # Build the graph
            G = nx.DiGraph()
            for n in nodes:
                G.add_node(n["id"])
            for e in edges:
                if e.get("from") in G and e.get("to") in G:
                    G.add_edge(e["from"], e["to"])

            if outcome not in G:
                continue

            # Find sources (factor nodes with in-degree 0 that can reach outcome)
            factor_ids = {n["id"] for n in nodes if n.get("role") != "outcome"}
            sources = [n for n in factor_ids if G.in_degree(n) == 0 and nx.has_path(G, n, outcome)]
            if not sources:
                # Fallback: any factor that can reach outcome
                sources = [n for n in factor_ids if nx.has_path(G, n, outcome)]

            # Classify each factor node as bottleneck or redundant
            node_is_bottleneck = {}
            for nid in factor_ids:
                if nid not in G:
                    continue
                # Remove node and check if any source loses its path to outcome
                G_reduced = G.copy()
                G_reduced.remove_node(nid)
                is_bottleneck = False
                for src in sources:
                    if src == nid:
                        continue
                    if src in G_reduced and outcome in G_reduced:
                        if not nx.has_path(G_reduced, src, outcome):
                            is_bottleneck = True
                            break
                node_is_bottleneck[nid] = is_bottleneck

            # Map probe results
            node_metrics = {m["node_id"]: m for m in na.get("node_metrics", [])}
            for pr in qinfo.get("probe_results", []):
                if not pr.get("success") or pr.get("absolute_shift") is None:
                    continue
                if pr.get("target_type") != "node":
                    continue
                tid = pr.get("target_id", "")
                if tid not in node_is_bottleneck:
                    continue

                shift = pr["absolute_shift"]
                if node_is_bottleneck[tid]:
                    bottleneck_shifts[name].append(shift)
                else:
                    redundant_shifts[name].append(shift)

                # For scatter
                pr_val = node_metrics.get(tid, {}).get("path_relevance", 0)
                all_path_rel.append(pr_val)
                all_shifts.append(shift)

    # Check we have data
    total_b = sum(len(v) for v in bottleneck_shifts.values())
    total_r = sum(len(v) for v in redundant_shifts.values())
    if total_b < 5 or total_r < 5:
        print(f"  [SKIP] bottleneck: not enough data (bottleneck={total_b}, redundant={total_r})")
        return

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    _label_axes([ax1, ax2])

    # (a) Grouped bar: bottleneck vs redundant per model
    x = np.arange(len(model_names))
    width = 0.35
    b_means, b_cis, r_means, r_cis = [], [], [], []
    for name in model_names:
        bv = bottleneck_shifts[name]
        rv = redundant_shifts[name]
        bm = sum(bv) / len(bv) if bv else 0
        rm = sum(rv) / len(rv) if rv else 0
        b_means.append(bm)
        r_means.append(rm)
        if len(bv) > 1:
            bse = (sum((v - bm)**2 for v in bv) / (len(bv)-1))**0.5 / len(bv)**0.5
            b_cis.append(1.96 * bse)
        else:
            b_cis.append(0)
        if len(rv) > 1:
            rse = (sum((v - rm)**2 for v in rv) / (len(rv)-1))**0.5 / len(rv)**0.5
            r_cis.append(1.96 * rse)
        else:
            r_cis.append(0)

    ax1.bar(x - width/2, b_means, width, yerr=b_cis, label="On shortest path",
            color="#D55E00", edgecolor="none", capsize=4, error_kw={"linewidth": 1.5})
    ax1.bar(x + width/2, r_means, width, yerr=r_cis, label="Off shortest path",
            color="#999999", edgecolor="none", capsize=4, error_kw={"linewidth": 1.5})
    ax1.set_xticks(x)
    ax1.set_xticklabels([_short_model_name(n) for n in model_names], fontsize=9)
    ax1.set_ylabel("Mean |Probability Shift|")
    ax1.legend(frameon=False, fontsize=9)

    # (b) Scatter: path_relevance vs |shift| with linear fit
    ax2.scatter(all_path_rel, all_shifts, alpha=0.15, s=15, color="#0072B2", edgecolors="none")
    # Linear regression line with p-value
    if len(all_path_rel) > 2:
        from scipy.stats import pearsonr
        pr_arr = np.array(all_path_rel)
        sh_arr = np.array(all_shifts)
        slope, intercept = np.polyfit(pr_arr, sh_arr, 1)
        r, p = pearsonr(pr_arr, sh_arr)
        x_line = np.linspace(0, 1, 100)
        ax2.plot(x_line, slope * x_line + intercept, color="#D55E00", linewidth=2, zorder=5)
        stars = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
        ax2.text(0.95, 0.95, f"r = {r:.2f}", transform=ax2.transAxes,
                 ha="right", va="top", fontsize=10)
        ax2.text(0.958, 0.97, stars, transform=ax2.transAxes,
                 ha="left", va="top", fontsize=8, fontweight="bold")
    ax2.set_xlabel("Path Relevance")
    ax2.set_ylabel("Mean |Probability Shift|")
    ax2.set_xlim(-0.05, 1.05)

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "bottleneck_sensitivity.png")
    plt.savefig(FIGURES_DIR / "bottleneck_sensitivity.pdf")
    plt.close()
    print("  Saved bottleneck_sensitivity.png/pdf")


# ═════════════════════════════════════════════════════════════════════════════
# FIGURE: Bayesian Coherence (log-odds shift independence from prior)
# ═════════════════════════════════════════════════════════════════════════════

def fig_bayesian_coherence(runs: dict):
    """Test whether LLM belief updates are Bayesian.

    A Bayesian agent's log-odds shift should depend only on evidence strength
    (probe type + structural importance), not on the initial probability.

    (a) Log-odds shift vs initial probability, pooled, with regression line
        controlling for probe type and betweenness centrality.
    (b) Partial correlation coefficient (initial_prob → log-odds shift,
        controlling for probe type + betweenness) per model. 0 = Bayesian.
    """
    from scipy import stats as sp_stats

    model_names = list(runs.keys())
    model_results = {}

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.5),
                                    gridspec_kw={"width_ratios": [1.3, 1]})
    _label_axes([ax1, ax2])

    all_p0 = []
    all_lo_shift = []

    for name, (rows, q_data) in runs.items():
        # Build betweenness lookup from question data
        betweenness_map = {}  # (qid, target_id) -> betweenness
        for qid, qinfo in q_data.items():
            na = qinfo.get("network_analysis", {})
            for nm in na.get("node_metrics", []):
                betweenness_map[(qid, nm["node_id"])] = nm.get("betweenness", 0)
            for em in na.get("edge_metrics", []):
                edge_id = f"{em['source']}->{em['target']}"
                betweenness_map[(qid, edge_id)] = em.get("edge_betweenness", 0)

        p0_vals = []
        lo_shifts = []
        betweenness_vals = []
        probe_types = []

        for r in rows:
            if not r.get("success") or r.get("updated_probability") is None:
                continue
            pt = r.get("probe_type", "")
            if pt == "irlevant":
                pt = "irrelevant"
            initial = r.get("initial_probability")
            updated = r.get("updated_probability")
            if initial is None or updated is None:
                continue
            # Clamp to avoid log(0)
            initial = max(0.01, min(0.99, initial))
            updated = max(0.01, min(0.99, updated))

            lo_initial = np.log(initial / (1 - initial))
            lo_updated = np.log(updated / (1 - updated))
            lo_shift = lo_updated - lo_initial

            qid = r.get("question_id", "")
            tid = r.get("target_id", "")
            btwn = betweenness_map.get((qid, tid), 0)

            p0_vals.append(initial)
            lo_shifts.append(lo_shift)
            betweenness_vals.append(btwn)
            probe_types.append(pt)

        if len(p0_vals) < 20:
            continue

        p0_arr = np.array(p0_vals)
        lo_arr = np.array(lo_shifts)
        btwn_arr = np.array(betweenness_vals)

        # Encode probe types as dummy variables
        unique_pts = sorted(set(probe_types))
        pt_dummies = np.zeros((len(probe_types), len(unique_pts)))
        for i, pt in enumerate(probe_types):
            pt_dummies[i, unique_pts.index(pt)] = 1

        # Build design matrix: [initial_prob, betweenness, probe_type_dummies]
        # Drop first probe type dummy to avoid multicollinearity
        X = np.column_stack([p0_arr, btwn_arr, pt_dummies[:, 1:]])
        X_with_intercept = np.column_stack([np.ones(len(X)), X])

        # OLS regression
        try:
            beta = np.linalg.lstsq(X_with_intercept, lo_arr, rcond=None)[0]
            # beta[1] is the coefficient on initial_probability
            coef_p0 = beta[1]

            # Compute standard error of beta[1]
            residuals = lo_arr - X_with_intercept @ beta
            n, k = X_with_intercept.shape
            mse = np.sum(residuals**2) / (n - k)
            cov = mse * np.linalg.inv(X_with_intercept.T @ X_with_intercept)
            se_p0 = np.sqrt(cov[1, 1])
            t_stat = coef_p0 / se_p0
            # Two-tailed p-value
            p_val = 2 * (1 - sp_stats.t.cdf(abs(t_stat), n - k))

            model_results[name] = {
                "coef": coef_p0,
                "se": se_p0,
                "p": p_val,
                "n": len(p0_arr),
            }
        except np.linalg.LinAlgError:
            continue

        all_p0.extend(p0_vals)
        all_lo_shift.extend(lo_shifts)

    # (a) Scatter: log-odds shift vs initial probability (pooled)
    ax1.scatter(all_p0, all_lo_shift, alpha=0.08, s=8, color="#0072B2", edgecolors="none")
    ax1.axhline(0, color="#999", linestyle="--", linewidth=1, zorder=0)

    # LOESS-style smoothed line via moving average on sorted data
    p0_all = np.array(all_p0)
    lo_all = np.array(all_lo_shift)
    sort_idx = np.argsort(p0_all)
    p0_sorted = p0_all[sort_idx]
    lo_sorted = lo_all[sort_idx]
    # Gaussian kernel smooth
    x_grid = np.linspace(0.05, 0.95, 100)
    y_smooth = np.zeros_like(x_grid)
    bw = 0.08  # bandwidth
    for i, xg in enumerate(x_grid):
        weights = np.exp(-0.5 * ((p0_sorted - xg) / bw) ** 2)
        if weights.sum() > 0:
            y_smooth[i] = np.average(lo_sorted, weights=weights)
    ax1.plot(x_grid, y_smooth, color="#D55E00", linewidth=2.5, zorder=5)

    ax1.set_xlabel("Initial Probability")
    ax1.set_ylabel("Log-Odds Shift")
    ax1.set_xlim(0, 1)
    # Trim y-axis to avoid extreme outliers
    lo_arr_all = np.array(all_lo_shift)
    q01, q99 = np.percentile(lo_arr_all, [1, 99])
    ax1.set_ylim(q01 * 1.2, q99 * 1.2)

    # (b) Coefficient on initial_probability per model
    if model_results:
        names = list(model_results.keys())
        coefs = [model_results[n]["coef"] for n in names]
        ses = [model_results[n]["se"] for n in names]
        bar_colors = [COLORS[n] for n in names]
        short_names = [_short_model_name(n) for n in names]

        x = np.arange(len(names))
        ax2.bar(x, coefs, yerr=[1.96 * s for s in ses], color=bar_colors,
                edgecolor="none", capsize=4, error_kw={"linewidth": 1.5})
        ax2.axhline(0, color="#444", linestyle="--", linewidth=1.5, zorder=0)
        ax2.set_xticks(x)
        ax2.set_xticklabels(short_names, fontsize=8)
        ax2.set_ylabel("β (Initial Prob → Log-Odds Shift)\nControlling for probe type + betweenness")
        # Add significance stars above/below bars with enough clearance
        max_extent = max(abs(c) + 1.96 * s for c, s in zip(coefs, ses))
        for i, n in enumerate(names):
            p = model_results[n]["p"]
            if p < 0.001:
                star = "***"
            elif p < 0.01:
                star = "**"
            elif p < 0.05:
                star = "*"
            else:
                star = "n.s."
            if coefs[i] >= 0:
                y_pos = coefs[i] + 1.96 * ses[i] + 0.03 * max_extent
                va = "bottom"
            else:
                y_pos = coefs[i] - 1.96 * ses[i] - 0.03 * max_extent
                va = "top"
            ax2.text(i, y_pos, star, ha="center", va=va, fontsize=9)

        # Expand y-axis so stars aren't clipped at edges
        ylo, yhi = ax2.get_ylim()
        pad = (yhi - ylo) * 0.15
        ax2.set_ylim(ylo - pad, yhi + pad)

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "bayesian_coherence.png")
    plt.savefig(FIGURES_DIR / "bayesian_coherence.pdf")
    plt.close()
    print("  Saved bayesian_coherence.png/pdf")


# ═════════════════════════════════════════════════════════════════════════════
# FIGURE: Test-Retest Reliability
# ═════════════════════════════════════════════════════════════════════════════

def fig_test_retest(runs: dict):
    """Test-retest reliability across all models: bar chart of Spearman ρ for probabilities and shifts."""
    from scipy import stats as sp_stats

    RETEST_DIRS = {
        "Llama-3.1-8B": (CAUSAL_DIR / "llama_neutral", CAUSAL_DIR / "llama_retest"),
        "Llama-3.3-70B": (CAUSAL_DIR / "llama_70b_neutral", CAUSAL_DIR / "llama_70b_retest"),
        "DeepSeek-V3": (CAUSAL_DIR / "deepseek_neutral", CAUSAL_DIR / "deepseek_retest"),
        "Qwen3-235B": (CAUSAL_DIR / "qwen_neutral", CAUSAL_DIR / "qwen_retest"),
        "Gemini-Flash-Lite": (CAUSAL_DIR / "gemini_fl_neutral", CAUSAL_DIR / "gemini_flash_lite_nitro_retest"),
        "GPT-OSS-120B": (CAUSAL_DIR / "gpt_oss_neutral", CAUSAL_DIR / "gpt_oss_retest"),
        "Qwen3-32B": (CAUSAL_DIR / "qwen_32b_neutral", CAUSAL_DIR / "qwen_32b_retest"),
    }

    def _mean_shift(qdata):
        probes = qdata.get("probe_results", [])
        s = [r["absolute_shift"] for r in probes
             if r.get("success") and r.get("absolute_shift") is not None]
        return sum(s) / len(s) if s else None

    def _load_shared_stages(d):
        """Load initial probabilities from _shared_stages_causal."""
        shared_dir = d / "_shared_stages_causal"
        if not shared_dir.exists():
            return {}
        results = {}
        for p in sorted(shared_dir.glob("q_*.json")):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                qid = data.get("question_id", p.stem.replace("q_", ""))
                results[qid] = data
            except (json.JSONDecodeError, KeyError):
                continue
        return results

    model_results = {}
    for model_name, (dir1, dir2) in RETEST_DIRS.items():
        if not dir1.exists() or not dir2.exists():
            print(f"  [SKIP] test-retest {model_name}: missing data")
            continue
        # Try question_results first, fall back to _shared_stages_causal
        run1 = load_question_jsons(dir1)
        if not run1:
            run1 = _load_shared_stages(dir1)
        run2 = load_question_jsons(dir2)
        if not run2:
            run2 = _load_shared_stages(dir2)
        shared = sorted(set(run1) & set(run2))
        if len(shared) < 10:
            print(f"  [SKIP] test-retest {model_name}: only {len(shared)} shared")
            continue

        probs_1, probs_2 = [], []
        for qid in shared:
            p1 = run1[qid].get("initial_probability")
            p2 = run2[qid].get("initial_probability")
            if p1 is not None and p2 is not None:
                probs_1.append(p1)
                probs_2.append(p2)

        rho_p, _ = sp_stats.spearmanr(probs_1, probs_2) if len(probs_1) >= 3 else (None, None)
        mad = float(np.mean([abs(a - b) for a, b in zip(probs_1, probs_2)])) if probs_1 else None
        model_results[model_name] = {
            "rho_prob": rho_p, "mad_prob": mad,
            "n_shared": len(shared),
        }
        print(f"  {model_name}: rho_prob={rho_p:.3f}, MAD={mad:.3f}, n={len(shared)}")

    if not model_results:
        print("  [SKIP] test-retest: no valid pairs")
        return

    # Bar chart: ρ for initial probabilities
    names = list(model_results.keys())
    x = np.arange(len(names))

    fig, ax = plt.subplots(figsize=(8, 4))
    rho_probs = [model_results[n]["rho_prob"] or 0 for n in names]
    colors_list = [COLORS.get(n, "#999") for n in names]

    bars = ax.bar(x, rho_probs, 0.6, color=colors_list, alpha=0.9, edgecolor="#333", linewidth=0.8)

    ax.set_ylabel("Spearman ρ (Run 1 vs Run 2)")
    ax.set_xticks(x)
    ax.set_xticklabels([n.replace("-", "\n", 1) for n in names], fontsize=9)
    ax.set_ylim(0, 1.05)
    ax.axhline(1.0, color="#999", linestyle="--", linewidth=0.8)

    for bar in bars:
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
                f"{bar.get_height():.3f}", ha="center", fontsize=8)

    plt.tight_layout()
    plt.savefig(SUPPLEMENT_DIR / "test_retest.png", dpi=300, bbox_inches="tight")
    plt.savefig(SUPPLEMENT_DIR / "test_retest.pdf", bbox_inches="tight")
    plt.close()
    print("  Saved supplementary/test_retest.png/pdf")


# ═════════════════════════════════════════════════════════════════════════════
# FIGURE: Inter-Model Agreement on Initial Probabilities
# ═════════════════════════════════════════════════════════════════════════════

def fig_inter_model_agreement(runs: dict):
    """Pairwise Spearman ρ heatmap for initial probability estimates across models."""
    from scipy import stats as sp_stats

    model_names = list(MODEL_DIRS.keys())
    # Load initial probabilities per model per question
    model_probs = {}
    for name in model_names:
        d = MODEL_DIRS[name]
        q_data = load_question_jsons(d)
        model_probs[name] = {qid: qd.get("initial_probability")
                             for qid, qd in q_data.items()
                             if qd.get("initial_probability") is not None}

    n = len(model_names)
    rho_matrix = np.ones((n, n))
    count_matrix = np.zeros((n, n), dtype=int)

    for i in range(n):
        for j in range(i + 1, n):
            shared = sorted(set(model_probs[model_names[i]]) & set(model_probs[model_names[j]]))
            if len(shared) < 5:
                rho_matrix[i, j] = rho_matrix[j, i] = np.nan
                continue
            p_i = [model_probs[model_names[i]][q] for q in shared]
            p_j = [model_probs[model_names[j]][q] for q in shared]
            rho, _ = sp_stats.spearmanr(p_i, p_j)
            rho_matrix[i, j] = rho_matrix[j, i] = rho
            count_matrix[i, j] = count_matrix[j, i] = len(shared)

    fig, ax = plt.subplots(figsize=(7, 6))
    im = ax.imshow(rho_matrix, cmap="RdYlBu", vmin=0, vmax=1, aspect="equal")

    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels([_short_model_name(n) for n in model_names], fontsize=9, rotation=45, ha="right")
    ax.set_yticklabels([_short_model_name(n) for n in model_names], fontsize=9)

    # Annotate cells
    for i in range(n):
        for j in range(n):
            val = rho_matrix[i, j]
            if not np.isnan(val):
                color = "white" if val < 0.5 else "black"
                ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                        fontsize=10, color=color, fontweight="bold" if i == j else "normal")

    cbar = fig.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label("Spearman ρ", fontsize=10)

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "inter_model_agreement.png", dpi=300, bbox_inches="tight")
    plt.savefig(FIGURES_DIR / "inter_model_agreement.pdf", bbox_inches="tight")
    plt.close()
    print("  Saved inter_model_agreement.png/pdf")


# ═════════════════════════════════════════════════════════════════════════════
# SUPPLEMENTARY: Network Size Comparison (Small / Medium / Large)
# ═════════════════════════════════════════════════════════════════════════════

def fig_network_size_comparison():
    """Compare grounding slopes across network sizes using LME regression lines.

    Single panel: one regression line per network size condition (Small/Medium/Large),
    showing how the betweenness → |shift| slope varies with graph complexity.
    Reads LME results from lme_results.json.
    """
    import json as _json

    lme_path = CAUSAL_DIR / "lme_results.json"
    if not lme_path.exists():
        print("  [SKIP] network_size: no LME results")
        return

    lme = _json.loads(lme_path.read_text(encoding="utf-8"))

    size_configs = [
        ("net_medium", "4–8 nodes",   "#56B4E9"),
        ("net_large",  "6–10 nodes",  "#0072B2"),
        ("net_xl",     "12–16 nodes", "#003f5c"),
    ]

    available = [(k, label, color) for k, label, color in size_configs
                 if lme.get(k) is not None]
    if not available:
        print("  [SKIP] network_size: no network size LME results")
        return

    fig, ax = plt.subplots(1, 1, figsize=(6, 4.5))
    x_range = np.linspace(-2, 3, 100)

    for key, label, color in available:
        result = lme[key]
        fe = result["fixed_effects"]

        intercept_key = [k for k in fe if "Intercept" in k]
        slope_key = [k for k in fe if k not in intercept_key and "model" not in k.lower()]

        if not intercept_key or not slope_key:
            continue

        b0 = fe[intercept_key[0]]["coef"]
        b1 = fe[slope_key[0]]["coef"]
        b1_se = fe[slope_key[0]]["se"]
        p_val = fe[slope_key[0]]["p"]

        stars = "***" if p_val < 0.001 else "**" if p_val < 0.01 else "*" if p_val < 0.05 else ""

        y_pred = b0 + b1 * x_range
        ax.plot(x_range, y_pred, color=color, linewidth=2.5, zorder=5,
                label=f"{label} ($\\beta_1$={b1:.3f}{stars})")

        y_lo = b0 + (b1 - 1.96 * b1_se) * x_range
        y_hi = b0 + (b1 + 1.96 * b1_se) * x_range
        ax.fill_between(x_range, y_lo, y_hi, color=color, alpha=0.15, zorder=2)

    ax.set_xlabel("Betweenness Centrality (z-scored)")
    ax.set_ylabel("Predicted |$\\Delta$|")
    ax.legend(frameon=False, fontsize=10, loc="upper left")

    plt.tight_layout()
    plt.savefig(SUPPLEMENT_DIR / "network_size.png", dpi=300, bbox_inches="tight")
    plt.savefig(SUPPLEMENT_DIR / "network_size.pdf", bbox_inches="tight")
    plt.close()
    print("  Saved supplementary/network_size.png/pdf")


# ═════════════════════════════════════════════════════════════════════════════
# SUPPLEMENTARY: Structural Ablation (Node/Edge Removal)
# ═════════════════════════════════════════════════════════════════════════════

def fig_structural_ablation():
    """Ablation: LME regression lines for node/edge removal.

    (a) Node removal: betweenness → |shift| with 95% CI.
    (b) Node removal: path relevance → |shift| with 95% CI.
    (c) Edge removal: edge betweenness → |shift| with 95% CI (expected null).

    Reads LME results from lme_results.json.
    """
    import json as _json

    lme_path = CAUSAL_DIR / "lme_results.json"
    if not lme_path.exists():
        print("  [SKIP] structural_ablation: no LME results")
        return

    lme = _json.loads(lme_path.read_text(encoding="utf-8"))

    lines_to_plot = [
        ("ablation_node_betw", "Node Betweenness", "#0072B2"),
        ("ablation_node_path_rel", "Node Path Relevance", "#009E73"),
        ("ablation_edge_betw", "Edge Betweenness", "#D55E00"),
    ]

    available = [(k, label, color) for k, label, color in lines_to_plot
                 if lme.get(k) is not None]
    if not available:
        print("  [SKIP] structural_ablation: no ablation LME results")
        return

    fig, ax = plt.subplots(1, 1, figsize=(6, 4.5))
    x_range = np.linspace(-2, 3, 100)

    for key, label, color in available:
        result = lme[key]
        fe = result["fixed_effects"]

        intercept_key = [k for k in fe if "Intercept" in k]
        slope_key = [k for k in fe if k not in intercept_key and "model" not in k.lower()]

        if not intercept_key or not slope_key:
            continue

        b0 = fe[intercept_key[0]]["coef"]
        b1 = fe[slope_key[0]]["coef"]
        b1_se = fe[slope_key[0]]["se"]
        p_val = fe[slope_key[0]]["p"]

        stars = "***" if p_val < 0.001 else "**" if p_val < 0.01 else "*" if p_val < 0.05 else ""

        # Regression line
        y_pred = b0 + b1 * x_range
        ax.plot(x_range, y_pred, color=color, linewidth=2.5, zorder=5,
                label=f"{label} ($\\beta_1$={b1:.3f}{stars})")

        # CI band
        y_lo = b0 + (b1 - 1.96 * b1_se) * x_range
        y_hi = b0 + (b1 + 1.96 * b1_se) * x_range
        ax.fill_between(x_range, y_lo, y_hi, color=color, alpha=0.15, zorder=2)

    ax.set_xlabel("Topological Importance (z-scored)")
    ax.set_ylabel("Predicted |$\\Delta$| (ablation)")
    ax.legend(frameon=False, fontsize=10, loc="upper left")

    plt.tight_layout()
    plt.savefig(SUPPLEMENT_DIR / "structural_ablation.png", dpi=300, bbox_inches="tight")
    plt.savefig(SUPPLEMENT_DIR / "structural_ablation.pdf", bbox_inches="tight")
    plt.close()
    print("  Saved supplementary/structural_ablation.png/pdf")


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

    # Main figures
    print("\n--- Main figures ---")
    # fig_dose_response — dropped
    # fig_ssr_comparison — dropped; SSR used only in Causal Forecast Lab, not paper
    fig_shift_by_probe_type(runs)
    fig_calibration(runs)
    fig_within_question_consistency(runs)
    fig_reasoning_coherence(runs)
    fig_shift_directionality(runs)
    fig_bottleneck_sensitivity(runs)
    fig_bayesian_coherence(runs)
    fig_inter_model_agreement(runs)
    # fig_probability_distributions — merged into fig_calibration as panel (a)

    # Supplementary figures
    print("\n--- Supplementary figures ---")
    fig_superforecasting_analysis(runs)
    # fig_cross_model_shifts removed — report consistency in text
    fig_null_test(runs)
    fig_test_retest(runs)
    # fig_paired_initial_probabilities removed — report ρ range in text

    # fig_reasoning_embeddings — merged into fig_null_test as panel (b)
    fig_network_size_comparison()
    fig_structural_ablation()

    main_n = len(list(FIGURES_DIR.glob("*.png")))
    supp_n = len(list(SUPPLEMENT_DIR.glob("*.png")))
    print(f"\nDone! {main_n} main + {supp_n} supplementary figures")


# ═════════════════════════════════════════════════════════════════════════════
# FIGURE: Reasoning Embedding Analysis
# ═════════════════════════════════════════════════════════════════════════════

# Importance tier for each probe type (used for UMAP coloring)
_IMPORTANCE_TIER = {
    "node_negate_high": "High",
    "node_strengthen": "High",
    "edge_negate_critical": "High",
    "edge_strengthen_critical": "High",
    "node_negate_medium": "Medium",
    "node_strengthen_medium": "Medium",
    "node_negate_low": "Low",
    "node_strengthen_low": "Low",
    "edge_negate_peripheral": "Low",
    "edge_strengthen_peripheral": "Low",
    "edge_reverse": "Low",
    "edge_spurious": "Control",
    "missing_node": "Control",
    "irrelevant": "Control",
}

# Normalize non-standard probe types (same as loader)
_EMBED_PROBE_NORMALIZE = {
    "irlevant": "irrelevant",
    "edge_missing": "edge_spurious",
    "edge_omitted": "edge_spurious",
    "edge_added": "edge_spurious",
    "edge_addition": "edge_spurious",
    "edge_add": "edge_spurious",
    "edge_add_causal": "edge_spurious",
    "edge_add_direct": "edge_spurious",
    "edge_feedback": "edge_spurious",
    "edge_fabricate": "edge_spurious",
}

_TIER_COLORS = {
    "High": "#D55E00",       # vermillion
    "Medium": "#E69F00",     # orange
    "Low": "#0072B2",        # blue
    "Control": "#999999",    # gray
}

_MODEL_DISPLAY = {
    "llama-8b": "Llama-3.1-8B",
    "llama-70b": "Llama-3.3-70B",
    "deepseek": "DeepSeek-V3",
    "qwen": "Qwen3-235B",
    "gemini": "Gemini-Flash-Lite",
}


def fig_reasoning_embeddings(runs: dict):
    """Two-panel reasoning embedding analysis.

    (a) Within-question cosine similarity: control vs structural probes by model.
        For each model × question, compute mean cosine similarity between
        control probe reasoning and structural probe reasoning. Lower similarity
        means the model produces semantically distinct reasoning for controls.
    (b) Cross-model reasoning convergence by probe type (bar chart).
    """
    import json as _json

    embeddings_path = CAUSAL_DIR / "reasoning_embeddings.npz"
    keys_path = CAUSAL_DIR / "reasoning_embeddings_keys.json"
    analysis_path = CAUSAL_DIR / "reasoning_similarity_analysis.json"

    if not embeddings_path.exists() or not keys_path.exists():
        print("  [SKIP] reasoning_embeddings: missing cached embeddings")
        return

    print("  Computing embedding separation...", end=" ", flush=True)

    keys = _json.loads(keys_path.read_text(encoding="utf-8"))
    data = np.load(str(embeddings_path))
    embeddings = data["embeddings"]

    # Parse metadata: qid|probe_type|probe_idx|model
    CONTROL_TYPES = {"irrelevant", "edge_spurious", "missing_node"}

    # Index embeddings by (model, qid) -> list of (is_control, embedding_idx)
    model_q_index = defaultdict(list)
    for i, k in enumerate(keys):
        parts = k.split("|")
        if len(parts) < 4:
            continue
        pt = _EMBED_PROBE_NORMALIZE.get(parts[1], parts[1])
        if pt not in _IMPORTANCE_TIER:
            continue
        model_key = parts[3]
        qid = parts[0]
        is_control = pt in CONTROL_TYPES
        model_q_index[(model_key, qid)].append((is_control, i))

    # For each model, compute within-question control vs structural similarity
    model_order = ["llama-8b", "llama-70b", "deepseek", "qwen", "gemini"]
    model_separations = {}  # model -> list of per-question mean(control-structural sim)
    model_within_control = {}  # model -> list of per-question mean(control-control sim)
    model_within_structural = {}  # model -> list of per-question mean(structural-structural sim)

    def _cosine_sim(a, b):
        dot = np.dot(a, b)
        na = np.linalg.norm(a)
        nb = np.linalg.norm(b)
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)

    for model_key in model_order:
        between_sims = []
        ctrl_sims = []
        struct_sims = []

        # Get all questions for this model
        model_questions = set(qid for (mk, qid) in model_q_index if mk == model_key)

        for qid in model_questions:
            entries = model_q_index[(model_key, qid)]
            ctrl_indices = [idx for is_ctrl, idx in entries if is_ctrl]
            struct_indices = [idx for is_ctrl, idx in entries if not is_ctrl]

            if len(ctrl_indices) < 2 or len(struct_indices) < 2:
                continue

            # Between-class: control vs structural
            q_between = []
            for ci in ctrl_indices:
                for si in struct_indices:
                    q_between.append(_cosine_sim(embeddings[ci], embeddings[si]))
            if q_between:
                between_sims.append(sum(q_between) / len(q_between))

            # Within-class: control-control
            q_ctrl = []
            for ii in range(len(ctrl_indices)):
                for jj in range(ii + 1, len(ctrl_indices)):
                    q_ctrl.append(_cosine_sim(embeddings[ctrl_indices[ii]], embeddings[ctrl_indices[jj]]))
            if q_ctrl:
                ctrl_sims.append(sum(q_ctrl) / len(q_ctrl))

            # Within-class: structural-structural
            # Sample to avoid O(n^2) explosion for large structural sets
            rng = np.random.RandomState(42)
            if len(struct_indices) > 10:
                pairs = [(struct_indices[a], struct_indices[b])
                         for a in range(len(struct_indices))
                         for b in range(a + 1, len(struct_indices))]
                if len(pairs) > 50:
                    pair_idx = rng.choice(len(pairs), 50, replace=False)
                    pairs = [pairs[p] for p in pair_idx]
            else:
                pairs = [(struct_indices[a], struct_indices[b])
                         for a in range(len(struct_indices))
                         for b in range(a + 1, len(struct_indices))]
            q_struct = [_cosine_sim(embeddings[a], embeddings[b]) for a, b in pairs]
            if q_struct:
                struct_sims.append(sum(q_struct) / len(q_struct))

        model_separations[model_key] = between_sims
        model_within_control[model_key] = ctrl_sims
        model_within_structural[model_key] = struct_sims

    print("done.")

    fig, ax = plt.subplots(figsize=(7, 4.5))

    model_colors_map = {
        "llama-8b": "#E69F00",
        "llama-70b": "#0072B2",
        "deepseek": "#D55E00",
        "qwen": "#009E73",
        "gemini": "#CC79A7",
    }

    x_pos = np.arange(len(model_order))
    width = 0.35

    for gi, (label, data_dict, hatch) in enumerate([
        ("Structural Probes", model_within_structural, None),
        ("Control Probes", model_within_control, "//"),
    ]):
        means = []
        cis = []
        for mk in model_order:
            vals = data_dict.get(mk, [])
            if vals:
                m = sum(vals) / len(vals)
                means.append(m)
                boot = []
                boot_rng = np.random.RandomState(42)
                for _ in range(2000):
                    sample = boot_rng.choice(vals, len(vals), replace=True)
                    boot.append(sum(sample) / len(sample))
                boot.sort()
                lo = boot[int(0.025 * len(boot))]
                hi = boot[int(0.975 * len(boot))]
                cis.append((m - lo, hi - m))
            else:
                means.append(0)
                cis.append((0, 0))

        err_lo = [c[0] for c in cis]
        err_hi = [c[1] for c in cis]
        ax.bar(x_pos + gi * width, means, width,
               yerr=[err_lo, err_hi],
               label=label, hatch=hatch,
               color=[model_colors_map[m] for m in model_order],
               edgecolor="black", linewidth=0.5, capsize=3,
               error_kw={"linewidth": 1}, alpha=0.7 if hatch else 1.0)

    # Paired t-test per model and add significance stars
    from forecast_bench.analysis_causal import _t_to_p
    for i, mk in enumerate(model_order):
        s_vals = model_within_structural.get(mk, [])
        c_vals = model_within_control.get(mk, [])
        # Pair by question (same index = same question)
        n_pairs = min(len(s_vals), len(c_vals))
        if n_pairs > 1:
            diffs = [s_vals[j] - c_vals[j] for j in range(n_pairs)]
            mean_d = sum(diffs) / len(diffs)
            var_d = sum((d - mean_d) ** 2 for d in diffs) / (len(diffs) - 1)
            se_d = (var_d / len(diffs)) ** 0.5 if var_d > 0 else 1e-10
            t_stat = mean_d / se_d
            p = _t_to_p(abs(t_stat), len(diffs) - 1)
        else:
            p = 1.0
        if p < 0.001:
            stars = "***"
        elif p < 0.01:
            stars = "**"
        elif p < 0.05:
            stars = "*"
        else:
            stars = "n.s."
        # Draw bracket between the two bars with stars above
        x_left = x_pos[i]  # structural bar center
        x_right = x_pos[i] + width  # control bar center
        s_mean = sum(s_vals) / len(s_vals) if s_vals else 0
        c_mean = sum(c_vals) / len(c_vals) if c_vals else 0
        y_top = max(s_mean, c_mean) + 0.015
        bracket_h = 0.005
        ax.plot([x_left, x_left, x_right, x_right],
                [y_top, y_top + bracket_h, y_top + bracket_h, y_top],
                color="black", linewidth=1.0, clip_on=False)
        ax.annotate(stars, xy=((x_left + x_right) / 2, y_top + bracket_h),
                     xytext=(0, 2), textcoords="offset points",
                     ha="center", fontsize=11, fontweight="bold")

    ax.set_ylabel("Within-Question Cosine Similarity")
    ax.set_xticks(x_pos + width / 2)
    ax.set_xticklabels([_MODEL_DISPLAY.get(m, m) for m in model_order], fontsize=9)
    ax.set_ylim(0.55, 0.86)
    ax.legend(fontsize=9, bbox_to_anchor=(1.02, 1), loc="upper left", borderaxespad=0)

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "reasoning_embeddings.png", dpi=300, bbox_inches="tight")
    plt.savefig(FIGURES_DIR / "reasoning_embeddings.pdf", bbox_inches="tight")
    plt.close()
    print("  Saved reasoning_embeddings.png/pdf")


if __name__ == "__main__":
    main()
