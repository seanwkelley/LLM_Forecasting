#!/usr/bin/env python3
"""Combined probe effects figure: (a) shift by probe type, (b) on/off shortest path, (c) path relevance."""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from collections import defaultdict
from pathlib import Path
from scipy import stats as sp_stats
import networkx as nx

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 15,
    "axes.labelsize": 16,
    "axes.titlesize": 17,
    "legend.fontsize": 13,
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

COLORS = {
    "Llama-3.1-8B": "#E69F00",
    "Llama-3.3-70B": "#0072B2",
    "DeepSeek-V3": "#D55E00",
    "Qwen3-235B": "#009E73",
    "Gemini-Flash-Lite": "#CC79A7",
}

# Distinct from model colors (orange, blue, vermillion, green, pink)
CAT_COLORS = {"node": "#332288", "edge": "#AA3377", "control": "#BBBBBB"}

DISPLAY_CATEGORIES = {
    "node_negate_high": "node", "node_negate_medium": "node", "node_negate_low": "node",
    "node_strengthen": "node", "node_strengthen_medium": "node", "node_strengthen_low": "node",
    "missing_node": "node",
    "edge_negate_critical": "edge", "edge_negate_peripheral": "edge",
    "edge_strengthen_critical": "edge", "edge_strengthen_peripheral": "edge",
    "edge_reverse": "edge", "edge_spurious": "edge", "edge_fabricate": "edge",
    "irrelevant": "control",
}

PROBE_TYPE_NORMALIZE = {
    "irlevant": "irrelevant", "edge_missing": "edge_spurious", "edge_omitted": "edge_spurious",
    "edge_added": "edge_spurious", "edge_addition": "edge_spurious", "edge_add": "edge_spurious",
    "edge_add_causal": "edge_spurious", "edge_add_direct": "edge_spurious",
    "edge_feedback": "edge_spurious", "edge_fabricate": "edge_spurious",
}

PRETTY_LABELS = {
    "node_negate_high": "Negate High-Imp. Node",
    "node_negate_medium": "Negate Medium Node",
    "node_negate_low": "Negate Low Node",
    "node_strengthen": "Strengthen High-Imp. Node",
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


def _short_model_name(name):
    return {"Llama-3.1-8B": "Llama\n8B", "Llama-3.3-70B": "Llama\n70B",
            "DeepSeek-V3": "DeepSeek\nV3", "Qwen3-235B": "Qwen3\n235B",
            "Gemini-Flash-Lite": "Gemini\nFlash-Lite"}.get(name, name)


def main():
    from forecast_bench.generate_figures import _load_all_runs
    runs = _load_all_runs()

    fig = plt.figure(figsize=(20, 6))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.1, 0.7, 1.2], wspace=0.4)
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1])
    ax3 = fig.add_subplot(gs[2])

    # ── (a) Shift by probe type (dot plot) ───────────────────────────────
    type_shifts = defaultdict(list)
    for name, (rows, _) in runs.items():
        for r in rows:
            if not r.get("success") or r.get("absolute_shift") is None:
                continue
            pt = PROBE_TYPE_NORMALIZE.get(r.get("probe_type", "unknown"),
                                           r.get("probe_type", "unknown"))
            type_shifts[pt].append(r["absolute_shift"])

    ordered = sorted(type_shifts.items(),
                     key=lambda kv: sum(kv[1]) / len(kv[1]) if kv[1] else 0)
    labels = [k for k, _ in ordered]
    data = [v for _, v in ordered]

    means, ci_los, ci_his = [], [], []
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

    face_colors = [CAT_COLORS.get(DISPLAY_CATEGORIES.get(l, "control"), "#999") for l in labels]
    pretty = [PRETTY_LABELS.get(l, l.replace("_", " ").title()) for l in labels]

    y = list(range(len(labels)))
    for i, (m, lo, hi, color) in enumerate(zip(means, ci_los, ci_his, face_colors)):
        ax1.plot([m - lo, m + hi], [i, i], color=color, linewidth=3, solid_capstyle="round")
        ax1.plot(m, i, "o", color=color, markersize=4, zorder=5)
    ax1.set_yticks(y)
    ax1.set_yticklabels(pretty, fontsize=12)
    ax1.set_xlabel("Mean |Probability Shift|")
    ax1.axvline(x=0, color="#333333", linewidth=1.0, linestyle="--", zorder=0)
    ax1.legend(handles=[
        Patch(facecolor=CAT_COLORS["node"], alpha=0.7, label="Node"),
        Patch(facecolor=CAT_COLORS["edge"], alpha=0.7, label="Edge"),
        Patch(facecolor=CAT_COLORS["control"], alpha=0.7, label="Control"),
    ], loc="lower right", frameon=False, fontsize=12)

    # ── Collect path data ───────────────────────────────────────────────
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
            G = nx.DiGraph()
            for n in nodes:
                G.add_node(n["id"])
            for e in edges:
                if e.get("from") in G and e.get("to") in G:
                    G.add_edge(e["from"], e["to"])
            if outcome not in G:
                continue
            factor_ids = {n["id"] for n in nodes if n.get("role") != "outcome"}
            sources = [n for n in factor_ids if G.in_degree(n) == 0 and nx.has_path(G, n, outcome)]
            if not sources:
                sources = [n for n in factor_ids if nx.has_path(G, n, outcome)]
            node_is_bottleneck = {}
            for nid in factor_ids:
                if nid not in G:
                    continue
                G_r = G.copy()
                G_r.remove_node(nid)
                is_bn = False
                for src in sources:
                    if src == nid:
                        continue
                    if src in G_r and outcome in G_r:
                        if not nx.has_path(G_r, src, outcome):
                            is_bn = True
                            break
                node_is_bottleneck[nid] = is_bn
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
                pr_val = node_metrics.get(tid, {}).get("path_relevance", 0)
                all_path_rel.append(pr_val)
                all_shifts.append(shift)

    # ── (b) On-path vs off-path (pooled) ────────────────────────────────
    all_on = [s for name in model_names for s in bottleneck_shifts[name]]
    all_off = [s for name in model_names for s in redundant_shifts[name]]

    on_mean = np.mean(all_on)
    off_mean = np.mean(all_off)

    # Bootstrap CIs
    rng = np.random.default_rng(42)
    n_boot = 10_000
    def _boot_ci(vals):
        v = np.array(vals)
        m = np.mean(v)
        boots = np.array([np.mean(rng.choice(v, size=len(v))) for _ in range(n_boot)])
        lo, hi = np.percentile(boots, [2.5, 97.5])
        return m, m - lo, hi - m

    on_m, on_lo, on_hi = _boot_ci(all_on)
    off_m, off_lo, off_hi = _boot_ci(all_off)

    bars = ax2.bar([0, 1], [on_m, off_m],
                   yerr=[[on_lo, off_lo], [on_hi, off_hi]],
                   color=["#332288", "#BBBBBB"], edgecolor="none", capsize=5,
                   error_kw={"linewidth": 1.5}, width=0.6)
    ax2.set_xticks([0, 1])
    ax2.set_xticklabels(["On Shortest\nPath", "Off Shortest\nPath"], fontsize=14)
    ax2.set_ylabel("Mean |Probability Shift|")

    # Significance
    _, p_val = sp_stats.mannwhitneyu(all_on, all_off, alternative="two-sided")
    stars = "***" if p_val < 0.001 else "**" if p_val < 0.01 else "*" if p_val < 0.05 else "n.s."
    y_top = max(on_m + on_hi, off_m + off_hi) + 0.003
    ax2.plot([0, 0, 1, 1], [y_top, y_top + 0.002, y_top + 0.002, y_top],
             color="black", linewidth=1.0)
    ax2.text(0.5, y_top + 0.003, stars, ha="center", va="bottom",
             fontsize=14, fontweight="bold")
    ax2.set_ylim(bottom=0)

    # ── (c) Path relevance scatter with linear fit ───────────────────────
    ax3.scatter(all_path_rel, all_shifts, alpha=0.15, s=15, color="#332288", edgecolors="none")
    if len(all_path_rel) > 2:
        from scipy.stats import pearsonr
        pr_arr = np.array(all_path_rel)
        sh_arr = np.array(all_shifts)
        slope, intercept = np.polyfit(pr_arr, sh_arr, 1)
        r, p = pearsonr(pr_arr, sh_arr)
        x_line = np.linspace(0, 1, 100)
        ax3.plot(x_line, slope * x_line + intercept, color="#882255", linewidth=2, zorder=5)
        stars = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
        ax3.text(0.95, 0.95, f"r = {r:.2f}", transform=ax3.transAxes, ha="right", va="top", fontsize=14)
        ax3.text(0.958, 0.97, stars, transform=ax3.transAxes, ha="left", va="top", fontsize=12, fontweight="bold")
    ax3.set_xlabel("Path Relevance", fontsize=16)
    ax3.set_ylabel("Mean |Probability Shift|", fontsize=16)
    ax3.tick_params(axis="both", labelsize=13)
    ax3.set_xlim(-0.05, 1.05)

    # Panel labels
    for ax, label in zip([ax1, ax2, ax3], ["(a)", "(b)", "(c)"]):
        ax.text(-0.02, 1.02, label, transform=ax.transAxes,
                fontsize=14, fontweight="bold", va="bottom", ha="right")

    OUT.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT / f"probe_effects.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("Saved probe_effects.png/pdf")


if __name__ == "__main__":
    main()
