"""
Single-Agent Causal Discovery Results — Network Plots.

Visualizes the single-agent estimated causal graphs for both domains,
color-coding edges by correctness (TP, FP, FN) against ground truth.

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


def _load_per_edge(path: str | Path) -> list[dict]:
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

    title = domain.title()
    ax.set_title(
        f"{title} Engine — Single-Agent Estimated Graph\n"
        f"P={scores['precision']:.2f}  R={scores['recall']:.2f}  "
        f"F1={scores['f1']:.2f}  SHD={scores.get('shd', scores.get('hamming_distance', '?'))}",
        fontsize=13, fontweight="bold", pad=15,
    )
    ax.axis("off")

    return fig, ax


def plot_node_breakdown(
    per_edge: list[dict],
    variables: list[str],
    scores: dict,
    domain: str,
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
        f"{domain.title()} — Per-Node Edge Classification",
        fontsize=12, fontweight="bold",
    )
    ax.legend(loc="lower right", fontsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    return fig, ax


def main():
    out_dir = Path("outputs/causal_discovery/multi_agent")
    plot_dir = out_dir / "plots"
    plot_dir.mkdir(parents=True, exist_ok=True)

    # Load results
    market_edges, market_scores = _load_per_edge(
        out_dir / "market_single" / "pilot_results.json"
    )
    conflict_edges, conflict_scores = _load_per_edge(
        out_dir / "conflict_single" / "pilot_results.json"
    )

    # --- Combined network plot (side by side) ---
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(28, 11))

    plot_estimated_graph(
        market_edges, MARKET_VARIABLES, MARKET_CATEGORIES,
        MARKET_POS, market_scores, "market", ax=ax1,
    )
    plot_estimated_graph(
        conflict_edges, CONFLICT_VARIABLES, CONFLICT_CATEGORIES,
        CONFLICT_POS, conflict_scores, "conflict", ax=ax2,
    )

    fig.suptitle(
        "Single-Agent Causal Discovery — Estimated vs Ground Truth",
        fontsize=16, fontweight="bold", y=0.98,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(
        plot_dir / "single_agent_networks.png",
        dpi=200, bbox_inches="tight", facecolor="white", edgecolor="none",
    )
    print(f"Saved: {plot_dir / 'single_agent_networks.png'}")

    # --- Per-node breakdown (side by side) ---
    fig2, (ax3, ax4) = plt.subplots(1, 2, figsize=(20, 8))

    plot_node_breakdown(
        market_edges, MARKET_VARIABLES, market_scores, "market", ax=ax3,
    )
    plot_node_breakdown(
        conflict_edges, CONFLICT_VARIABLES, conflict_scores, "conflict", ax=ax4,
    )

    fig2.suptitle(
        "Single-Agent — Per-Node Edge Classification",
        fontsize=14, fontweight="bold", y=1.0,
    )
    fig2.tight_layout()
    fig2.savefig(
        plot_dir / "single_agent_node_breakdown.png",
        dpi=200, bbox_inches="tight", facecolor="white", edgecolor="none",
    )
    print(f"Saved: {plot_dir / 'single_agent_node_breakdown.png'}")

    plt.close("all")


if __name__ == "__main__":
    main()
