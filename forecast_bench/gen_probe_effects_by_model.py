#!/usr/bin/env python3
"""Probe effects by model: 3 panels with all models overlaid."""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from collections import defaultdict
from pathlib import Path
from scipy import stats as sp_stats
from scipy.stats import pearsonr
import networkx as nx

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

COLORS = {
    "Llama-3.1-8B": "#E69F00",
    "Llama-3.3-70B": "#0072B2",
    "DeepSeek-V3": "#D55E00",
    "Qwen3-235B": "#009E73",
    "Gemini-Flash-Lite": "#CC79A7",
}

PROBE_TYPE_NORMALIZE = {
    "irlevant": "irrelevant", "edge_missing": "edge_spurious", "edge_omitted": "edge_spurious",
    "edge_added": "edge_spurious", "edge_addition": "edge_spurious", "edge_add": "edge_spurious",
    "edge_add_causal": "edge_spurious", "edge_add_direct": "edge_spurious",
    "edge_feedback": "edge_spurious", "edge_fabricate": "edge_spurious",
}

PRETTY_LABELS = {
    "node_negate_high": "Negate High Node",
    "node_negate_medium": "Negate Med Node",
    "node_negate_low": "Negate Low Node",
    "node_strengthen": "Str. High Node",
    "node_strengthen_medium": "Str. Med Node",
    "node_strengthen_low": "Str. Low Node",
    "edge_negate_critical": "Negate SP Edge",
    "edge_negate_peripheral": "Negate Periph. Edge",
    "edge_strengthen_critical": "Str. SP Edge",
    "edge_strengthen_peripheral": "Str. Periph. Edge",
    "edge_reverse": "Reverse Edge",
    "edge_spurious": "Spurious Edge",
    "missing_node": "Missing Node",
    "irrelevant": "Irrelevant (Control)",
}


def _short_name(name):
    return {"Llama-3.1-8B": "Llama\n8B", "Llama-3.3-70B": "Llama\n70B",
            "DeepSeek-V3": "DeepSeek\nV3", "Qwen3-235B": "Qwen3\n235B",
            "Gemini-Flash-Lite": "Gemini\nFlash-Lite"}.get(name, name)


def main():
    from forecast_bench.generate_figures import _load_all_runs
    runs = _load_all_runs()
    model_names = list(runs.keys())
    n_models = len(model_names)

    fig = plt.figure(figsize=(18, 7))
    gs = fig.add_gridspec(1, 3, width_ratios=[1, 1, 1], wspace=0.4)
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1])
    ax3 = fig.add_subplot(gs[2])

    # ── Compute pooled ordering ──────────────────────────────────────────
    pooled = defaultdict(list)
    for name, (rows, _) in runs.items():
        for r in rows:
            if not r.get("success") or r.get("absolute_shift") is None:
                continue
            pt = PROBE_TYPE_NORMALIZE.get(r.get("probe_type", ""), r.get("probe_type", ""))
            pooled[pt].append(r["absolute_shift"])
    ordered_types = [k for k, _ in sorted(pooled.items(),
                     key=lambda kv: np.mean(kv[1]) if kv[1] else 0)]

    # ── (a) Probe type dot plot — all models overlaid ────────────────────
    offsets = np.linspace(-0.3, 0.3, n_models)

    for mi, name in enumerate(model_names):
        rows_m = runs[name][0]
        type_shifts = defaultdict(list)
        for r in rows_m:
            if not r.get("success") or r.get("absolute_shift") is None:
                continue
            pt = PROBE_TYPE_NORMALIZE.get(r.get("probe_type", ""), r.get("probe_type", ""))
            type_shifts[pt].append(r["absolute_shift"])

        for yi, pt in enumerate(ordered_types):
            vals = type_shifts.get(pt, [])
            if not vals:
                continue
            m = np.mean(vals)
            ax1.plot(m, yi + offsets[mi], "o", color=COLORS[name], markersize=5,
                     markeredgecolor="white", markeredgewidth=0.3, zorder=3, alpha=0.85)

    ax1.set_yticks(range(len(ordered_types)))
    ax1.set_yticklabels([PRETTY_LABELS.get(pt, pt) for pt in ordered_types], fontsize=8)
    ax1.set_xlabel("Mean |Probability Shift|")
    ax1.axvline(x=0, color="#333", linewidth=0.8, linestyle="--", zorder=0)

    # ── (b) On/off shortest path — grouped bars per model ────────────────
    on_means, off_means, on_cis, off_cis = [], [], [], []
    for name, (rows_m, q_data) in runs.items():
        on_s, off_s = [], []
        for qid, qinfo in q_data.items():
            nodes = qinfo.get("nodes", [])
            edges = qinfo.get("edges", [])
            na = qinfo.get("network_analysis", {})
            outcome = na.get("outcome_node")
            if not outcome or len(nodes) < 3:
                continue
            G = nx.DiGraph()
            for nd in nodes:
                G.add_node(nd["id"])
            for e in edges:
                if e.get("from") in G and e.get("to") in G:
                    G.add_edge(e["from"], e["to"])
            if outcome not in G:
                continue
            factor_ids = {nd["id"] for nd in nodes if nd.get("role") != "outcome"}
            sources = [nd for nd in factor_ids if G.in_degree(nd) == 0 and nx.has_path(G, nd, outcome)]
            if not sources:
                sources = [nd for nd in factor_ids if nx.has_path(G, nd, outcome)]
            node_is_bn = {}
            for nid in factor_ids:
                if nid not in G:
                    continue
                G_r = G.copy()
                G_r.remove_node(nid)
                is_bn = any(src != nid and src in G_r and outcome in G_r
                            and not nx.has_path(G_r, src, outcome) for src in sources)
                node_is_bn[nid] = is_bn
            for pr in qinfo.get("probe_results", []):
                if not pr.get("success") or pr.get("absolute_shift") is None:
                    continue
                if pr.get("target_type") != "node":
                    continue
                tid = pr.get("target_id", "")
                if tid not in node_is_bn:
                    continue
                if node_is_bn[tid]:
                    on_s.append(pr["absolute_shift"])
                else:
                    off_s.append(pr["absolute_shift"])

        on_m = np.mean(on_s) if on_s else 0
        off_m = np.mean(off_s) if off_s else 0
        on_se = np.std(on_s) / np.sqrt(len(on_s)) if len(on_s) > 1 else 0
        off_se = np.std(off_s) / np.sqrt(len(off_s)) if len(off_s) > 1 else 0
        on_means.append(on_m)
        off_means.append(off_m)
        on_cis.append(1.96 * on_se)
        off_cis.append(1.96 * off_se)

    x = np.arange(n_models)
    w = 0.35
    ax2.bar(x - w / 2, on_means, w, yerr=on_cis, label="On shortest path",
            color="#D55E00", edgecolor="none", capsize=3, error_kw={"linewidth": 1.2})
    ax2.bar(x + w / 2, off_means, w, yerr=off_cis, label="Off shortest path",
            color="#999999", edgecolor="none", capsize=3, error_kw={"linewidth": 1.2})
    ax2.set_xticks(x)
    ax2.set_xticklabels([_short_name(n) for n in model_names], fontsize=9)
    ax2.set_ylabel("Mean |Probability Shift|")
    ax2.legend(frameon=False, fontsize=9)
    ax2.set_ylim(bottom=0)

    # ── (c) Path relevance — overlaid regression lines ───────────────────
    for name, (rows_m, q_data) in runs.items():
        pr_vals, sh_vals = [], []
        for qid, qinfo in q_data.items():
            na = qinfo.get("network_analysis", {})
            node_metrics = {m["node_id"]: m for m in na.get("node_metrics", [])}
            for pr in qinfo.get("probe_results", []):
                if not pr.get("success") or pr.get("absolute_shift") is None:
                    continue
                if pr.get("target_type") != "node":
                    continue
                tid = pr.get("target_id", "")
                prv = node_metrics.get(tid, {}).get("path_relevance", 0)
                pr_vals.append(prv)
                sh_vals.append(pr["absolute_shift"])

        if len(pr_vals) > 2:
            pr_arr, sh_arr = np.array(pr_vals), np.array(sh_vals)
            slope, intercept = np.polyfit(pr_arr, sh_arr, 1)
            x_line = np.linspace(0, 1, 100)
            ax3.plot(x_line, slope * x_line + intercept, color=COLORS[name],
                     linewidth=1.8, alpha=0.8, label=name.split("-")[0] if "-" in name else name)
            # Scatter with low alpha
            ax3.scatter(pr_vals, sh_vals, alpha=0.05, s=8, color=COLORS[name], edgecolors="none")

    ax3.set_xlabel("Path Relevance")
    ax3.set_ylabel("Mean |Probability Shift|")
    ax3.set_xlim(-0.05, 1.05)

    # Panel labels
    for ax, label in zip([ax1, ax2, ax3], ["(a)", "(b)", "(c)"]):
        ax.text(-0.02, 1.02, label, transform=ax.transAxes,
                fontsize=14, fontweight="bold", va="bottom", ha="right")

    # Shared legend for models (panel a)
    model_handles = [Patch(facecolor=COLORS[n], label=n) for n in model_names]
    ax1.legend(handles=model_handles, fontsize=7, frameon=False, loc="lower right")

    OUT.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT / f"probe_effects_by_model.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("Saved probe_effects_by_model.png/pdf")


if __name__ == "__main__":
    main()
