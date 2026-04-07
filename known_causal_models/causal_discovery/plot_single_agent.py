"""
Single-Agent Causal Discovery Results — Network Plots.

Generates one network plot per domain/model combination, showing the
proposed causal graph color-coded against ground truth (TP, FP, FN).

Usage:
    python causal_discovery/plot_single_agent.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import networkx as nx
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from causal_discovery.ground_truth import (
    MARKET_VARIABLES, CONFLICT_VARIABLES,
    get_market_ground_truth, get_conflict_ground_truth,
)
from causal_discovery.plot_ground_truth import (
    MARKET_CATEGORIES, CONFLICT_CATEGORIES,
    MARKET_POS, CONFLICT_POS,
    CATEGORY_COLORS,
    _get_node_colors, _short_label,
)


# Edge colors by classification
EDGE_COLORS = {
    "correct":        "#2ecc71",  # green — true positive
    "false_positive":  "#e74c3c",  # red — spurious edge
    "false_negative":  "#3498db",  # blue — missed edge (dashed)
}

# Model display names and directory suffixes
MODELS = [
    ("Llama 8B",  "_llama8b"),
    ("Llama 70B", "_llama70b"),
    ("Qwen 397B", "_qwen397b"),
]

DOMAINS = [
    {
        "name": "market",
        "variables": MARKET_VARIABLES,
        "categories": MARKET_CATEGORIES,
        "pos": MARKET_POS,
        "gt_fn": get_market_ground_truth,
    },
    {
        "name": "conflict",
        "variables": CONFLICT_VARIABLES,
        "categories": CONFLICT_CATEGORIES,
        "pos": CONFLICT_POS,
        "gt_fn": get_conflict_ground_truth,
    },
]


def _load_per_edge(path: str | Path) -> tuple[list[dict], dict]:
    """Load per-edge results from a pilot_results.json file."""
    with open(path) as f:
        data = json.load(f)
    return data["per_edge"], data["scores"]


def _compute_node_metrics(per_edge: list[dict], variables: list[str]) -> dict:
    """Compute per-node TP, FP, FN counts (as source or target)."""
    metrics = {v: {"tp": 0, "fp": 0, "fn": 0} for v in variables}
    for e in per_edge:
        src, dst, status = e["from"], e["to"], e["status"]
        if status == "correct":
            metrics[src]["tp"] += 1
            metrics[dst]["tp"] += 1
        elif status == "false_positive":
            metrics[src]["fp"] += 1
            metrics[dst]["fp"] += 1
        elif status == "false_negative":
            metrics[src]["fn"] += 1
            metrics[dst]["fn"] += 1
    return metrics


def plot_estimated_graph(
    per_edge: list[dict],
    variables: list[str],
    categories: dict[str, list[str]],
    pos: dict[str, tuple[float, float]],
    scores: dict,
    domain: str,
    model_name: str,
    ax: plt.Axes | None = None,
):
    """Plot estimated causal graph with edges colored by correctness."""
    if ax is None:
        fig, ax = plt.subplots(1, 1, figsize=(14, 10))
    else:
        fig = ax.get_figure()

    G = nx.DiGraph()
    G.add_nodes_from(variables)

    # Separate edges by status
    edges_by_status = {"correct": [], "false_positive": [], "false_negative": []}
    for e in per_edge:
        edges_by_status[e["status"]].append((e["from"], e["to"]))

    # Draw false negatives first (dashed, behind)
    if edges_by_status["false_negative"]:
        G_fn = nx.DiGraph()
        G_fn.add_nodes_from(variables)
        G_fn.add_edges_from(edges_by_status["false_negative"])
        nx.draw_networkx_edges(
            G_fn, pos, ax=ax,
            edge_color=EDGE_COLORS["false_negative"],
            arrows=True, arrowsize=15, arrowstyle="-|>",
            connectionstyle="arc3,rad=0.1",
            width=1.5, alpha=0.5, style="dashed",
            min_source_margin=20, min_target_margin=20,
        )

    # Draw correct edges (solid green)
    if edges_by_status["correct"]:
        G_tp = nx.DiGraph()
        G_tp.add_nodes_from(variables)
        G_tp.add_edges_from(edges_by_status["correct"])
        nx.draw_networkx_edges(
            G_tp, pos, ax=ax,
            edge_color=EDGE_COLORS["correct"],
            arrows=True, arrowsize=18, arrowstyle="-|>",
            connectionstyle="arc3,rad=0.1",
            width=2.0, alpha=0.8,
            min_source_margin=20, min_target_margin=20,
        )

    # Draw false positives (solid red)
    if edges_by_status["false_positive"]:
        G_fp = nx.DiGraph()
        G_fp.add_nodes_from(variables)
        G_fp.add_edges_from(edges_by_status["false_positive"])
        nx.draw_networkx_edges(
            G_fp, pos, ax=ax,
            edge_color=EDGE_COLORS["false_positive"],
            arrows=True, arrowsize=18, arrowstyle="-|>",
            connectionstyle="arc3,rad=0.1",
            width=2.0, alpha=0.8,
            min_source_margin=20, min_target_margin=20,
        )

    # Draw nodes
    colors = _get_node_colors(variables, categories)
    nx.draw_networkx_nodes(
        G, pos, ax=ax,
        node_color=colors,
        node_size=2200,
        alpha=0.9,
        edgecolors="#333333",
        linewidths=1.5,
    )

    # Labels
    labels = {v: _short_label(v) for v in variables}
    nx.draw_networkx_labels(
        G, pos, labels, ax=ax,
        font_size=8, font_weight="bold", font_family="sans-serif",
    )

    # Legend
    legend_patches = [
        mpatches.Patch(color=EDGE_COLORS["correct"],
                       label=f"True Positive ({len(edges_by_status['correct'])})"),
        mpatches.Patch(color=EDGE_COLORS["false_positive"],
                       label=f"False Positive ({len(edges_by_status['false_positive'])})"),
        mpatches.Patch(color=EDGE_COLORS["false_negative"],
                       label=f"False Negative ({len(edges_by_status['false_negative'])})"),
    ]
    ax.legend(handles=legend_patches, loc="lower left", fontsize=9,
              framealpha=0.9, edgecolor="#cccccc")

    shd = scores.get("shd", scores.get("hamming_distance", "?"))
    ax.set_title(
        f"{domain.title()} — {model_name}\n"
        f"P={scores['precision']:.2f}  R={scores['recall']:.2f}  "
        f"F1={scores['f1']:.2f}  SHD={shd}",
        fontsize=13, fontweight="bold", pad=15,
    )
    ax.axis("off")

    return fig, ax


def plot_node_breakdown(
    per_edge: list[dict],
    variables: list[str],
    scores: dict,
    domain: str,
    model_name: str,
    ax: plt.Axes | None = None,
):
    """Horizontal bar chart showing per-node TP, FP, FN edge counts."""
    if ax is None:
        fig, ax = plt.subplots(1, 1, figsize=(10, 8))
    else:
        fig = ax.get_figure()

    node_metrics = _compute_node_metrics(per_edge, variables)

    # Sort by total involvement (TP+FP+FN) descending
    sorted_vars = sorted(
        variables,
        key=lambda v: node_metrics[v]["tp"] + node_metrics[v]["fp"] + node_metrics[v]["fn"],
    )

    y_pos = np.arange(len(sorted_vars))
    tp_vals = [node_metrics[v]["tp"] for v in sorted_vars]
    fp_vals = [node_metrics[v]["fp"] for v in sorted_vars]
    fn_vals = [node_metrics[v]["fn"] for v in sorted_vars]

    bar_height = 0.6
    ax.barh(y_pos, tp_vals, bar_height, color=EDGE_COLORS["correct"],
            alpha=0.85, label="True Positive")
    ax.barh(y_pos, fp_vals, bar_height, left=tp_vals,
            color=EDGE_COLORS["false_positive"], alpha=0.85, label="False Positive")
    ax.barh(y_pos, fn_vals, bar_height,
            left=[tp + fp for tp, fp in zip(tp_vals, fp_vals)],
            color=EDGE_COLORS["false_negative"], alpha=0.85, label="False Negative")

    ax.set_yticks(y_pos)
    ax.set_yticklabels([_short_label(v) for v in sorted_vars], fontsize=9)
    ax.set_xlabel("Edge Count (as source or target)", fontsize=10)
    ax.set_title(
        f"{domain.title()} — {model_name} — Per-Node Edge Classification",
        fontsize=12, fontweight="bold",
    )
    ax.legend(loc="lower right", fontsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    return fig, ax


def main():
    base_dir = Path("outputs/causal_discovery/single_agent")
    plot_dir = base_dir / "plots"
    plot_dir.mkdir(parents=True, exist_ok=True)

    n_models = len(MODELS)
    n_domains = len(DOMAINS)

    # --- Combined grid: models (rows) x domains (cols) ---
    fig, axes = plt.subplots(
        n_models, n_domains, figsize=(14 * n_domains, 11 * n_models),
    )
    if n_models == 1:
        axes = [axes]

    found_any = False
    for row, (model_label, model_suffix) in enumerate(MODELS):
        for col, dom in enumerate(DOMAINS):
            ax = axes[row][col]
            domain_name = dom["name"]
            result_dir = base_dir / f"{domain_name}_single{model_suffix}"
            result_file = result_dir / "pilot_results.json"

            if not result_file.exists():
                ax.text(0.5, 0.5, f"No data\n{result_file.name}",
                        ha="center", va="center", fontsize=14, color="#999")
                ax.set_title(f"{domain_name.title()} — {model_label}",
                             fontsize=13, fontweight="bold")
                ax.axis("off")
                continue

            per_edge, scores = _load_per_edge(result_file)
            plot_estimated_graph(
                per_edge, dom["variables"], dom["categories"],
                dom["pos"], scores, domain_name, model_label, ax=ax,
            )
            found_any = True

    if not found_any:
        print("No result files found. Nothing to plot.")
        plt.close(fig)
        return

    fig.suptitle(
        "Single-Agent Causal Discovery — Estimated vs Ground Truth",
        fontsize=20, fontweight="bold", y=0.995,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.98])
    out_path = plot_dir / "single_agent_networks.png"
    fig.savefig(out_path, dpi=200, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    print(f"Saved: {out_path}")

    # --- Per-node breakdown grid ---
    fig2, axes2 = plt.subplots(
        n_models, n_domains, figsize=(10 * n_domains, 8 * n_models),
    )
    if n_models == 1:
        axes2 = [axes2]

    for row, (model_label, model_suffix) in enumerate(MODELS):
        for col, dom in enumerate(DOMAINS):
            ax = axes2[row][col]
            domain_name = dom["name"]
            result_file = base_dir / f"{domain_name}_single{model_suffix}" / "pilot_results.json"

            if not result_file.exists():
                ax.text(0.5, 0.5, "No data", ha="center", va="center",
                        fontsize=14, color="#999")
                ax.axis("off")
                continue

            per_edge, scores = _load_per_edge(result_file)
            plot_node_breakdown(
                per_edge, dom["variables"], scores,
                domain_name, model_label, ax=ax,
            )

    fig2.suptitle(
        "Single-Agent — Per-Node Edge Classification",
        fontsize=16, fontweight="bold", y=1.0,
    )
    fig2.tight_layout()
    out_path2 = plot_dir / "single_agent_node_breakdown.png"
    fig2.savefig(out_path2, dpi=200, bbox_inches="tight",
                 facecolor="white", edgecolor="none")
    print(f"Saved: {out_path2}")

    plt.close("all")


if __name__ == "__main__":
    main()
