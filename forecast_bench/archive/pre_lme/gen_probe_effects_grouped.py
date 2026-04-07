#!/usr/bin/env python3
"""Probe effects by model: grouped CI bar versions."""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from collections import defaultdict
from pathlib import Path

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


def _short_name(name):
    return {"Llama-3.1-8B": "Llama 8B", "Llama-3.3-70B": "Llama 70B",
            "DeepSeek-V3": "DeepSeek V3", "Qwen3-235B": "Qwen3 235B",
            "Gemini-Flash-Lite": "Gemini FL"}.get(name, name)


def _get_shifts_by_model_and_type(runs):
    """Returns {model: {probe_type: [shifts]}}."""
    result = {}
    for name, (rows, _) in runs.items():
        type_shifts = defaultdict(list)
        for r in rows:
            if not r.get("success") or r.get("absolute_shift") is None:
                continue
            pt = PROBE_TYPE_NORMALIZE.get(r.get("probe_type", ""), r.get("probe_type", ""))
            type_shifts[pt].append(r["absolute_shift"])
        result[name] = type_shifts
    return result


def fig_all_types(runs):
    """All 14 probe types × 5 models — grouped horizontal bars."""
    data = _get_shifts_by_model_and_type(runs)
    model_names = list(runs.keys())
    n_models = len(model_names)

    # Get pooled ordering
    pooled = defaultdict(list)
    for name, ts in data.items():
        for pt, vals in ts.items():
            pooled[pt].extend(vals)
    ordered = [k for k, _ in sorted(pooled.items(),
               key=lambda kv: np.mean(kv[1]) if kv[1] else 0)]

    n_types = len(ordered)
    fig, ax = plt.subplots(figsize=(10, 8))

    bar_h = 0.15
    offsets = np.linspace(-(n_models - 1) / 2 * bar_h, (n_models - 1) / 2 * bar_h, n_models)

    for mi, name in enumerate(model_names):
        means, cis = [], []
        for pt in ordered:
            vals = data[name].get(pt, [])
            if vals:
                m = np.mean(vals)
                se = np.std(vals) / np.sqrt(len(vals)) if len(vals) > 1 else 0
                means.append(m)
                cis.append(1.96 * se)
            else:
                means.append(0)
                cis.append(0)

        y = np.arange(n_types) + offsets[mi]
        ax.barh(y, means, bar_h, xerr=cis, color=COLORS[name], alpha=0.8,
                label=_short_name(name), capsize=2, error_kw={"linewidth": 0.8})

    PRETTY = {
        "node_negate_high": "Negate High Node", "node_negate_medium": "Negate Med Node",
        "node_negate_low": "Negate Low Node", "node_strengthen": "Str. High Node",
        "node_strengthen_medium": "Str. Med Node", "node_strengthen_low": "Str. Low Node",
        "edge_negate_critical": "Negate SP Edge", "edge_negate_peripheral": "Negate Periph. Edge",
        "edge_strengthen_critical": "Str. SP Edge", "edge_strengthen_peripheral": "Str. Periph. Edge",
        "edge_reverse": "Reverse Edge", "edge_spurious": "Spurious Edge",
        "missing_node": "Missing Node", "irrelevant": "Irrelevant (Control)",
    }

    ax.set_yticks(range(n_types))
    ax.set_yticklabels([PRETTY.get(pt, pt) for pt in ordered], fontsize=9)
    ax.set_xlabel("Mean |Probability Shift|")
    ax.axvline(x=0, color="#333", linewidth=0.8, linestyle="--", zorder=0)
    ax.legend(frameon=False, fontsize=8, loc="lower right")

    for ext in ("pdf", "png"):
        fig.savefig(OUT / f"probe_effects_grouped_all.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("Saved probe_effects_grouped_all")


def fig_key_types(runs):
    """Key probe types only (5 types × 5 models) — grouped vertical bars."""
    data = _get_shifts_by_model_and_type(runs)
    model_names = list(runs.keys())
    n_models = len(model_names)

    # Probe type colors — avoid model colors (orange, blue, vermillion, green, pink)
    # and category colors (blue, vermillion, gray)
    TYPE_COLORS = {
        "node_strengthen": "#332288",     # indigo
        "node_negate_high": "#882255",    # wine
        "node_strengthen_low": "#88CCEE", # cyan
        "node_negate_low": "#DDCC77",     # sand
        "irrelevant": "#BBBBBB",          # light gray
    }

    KEY_TYPES = [
        ("node_strengthen", "Strengthen\nHigh Node"),
        ("node_negate_high", "Negate\nHigh Node"),
        ("node_strengthen_low", "Strengthen\nLow Node"),
        ("node_negate_low", "Negate\nLow Node"),
        ("irrelevant", "Irrelevant\n(Control)"),
    ]

    n_types = len(KEY_TYPES)
    fig, ax = plt.subplots(figsize=(10, 5))

    bar_w = 0.15
    offsets = np.linspace(-(n_models - 1) / 2 * bar_w, (n_models - 1) / 2 * bar_w, n_models)

    for mi, name in enumerate(model_names):
        means, cis = [], []
        for pt, _ in KEY_TYPES:
            vals = data[name].get(pt, [])
            if vals:
                m = np.mean(vals)
                se = np.std(vals) / np.sqrt(len(vals)) if len(vals) > 1 else 0
                means.append(m)
                cis.append(1.96 * se)
            else:
                means.append(0)
                cis.append(0)

        x = np.arange(n_types) + offsets[mi]
        ax.bar(x, means, bar_w, yerr=cis, color=COLORS[name], alpha=0.8,
               label=_short_name(name), capsize=2, error_kw={"linewidth": 0.8})

    ax.set_xticks(range(n_types))
    ax.set_xticklabels([label for _, label in KEY_TYPES], fontsize=10)
    ax.set_ylabel("Mean |Probability Shift|")
    ax.legend(frameon=False, fontsize=9, ncol=n_models, loc="upper center",
              bbox_to_anchor=(0.5, 1.12))
    ax.set_ylim(bottom=0)

    for ext in ("pdf", "png"):
        fig.savefig(OUT / f"probe_effects_grouped_key.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("Saved probe_effects_grouped_key")


def main():
    from forecast_bench.generate_figures import _load_all_runs
    runs = _load_all_runs()
    fig_all_types(runs)
    fig_key_types(runs)


if __name__ == "__main__":
    main()
