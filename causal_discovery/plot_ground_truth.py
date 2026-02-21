"""
Ground Truth Causal Graph Visualizations.

Generates publication-quality network plots for the market and conflict
engine causal graphs using networkx + matplotlib.

Usage:
    python causal_discovery/plot_ground_truth.py
"""

from __future__ import annotations

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


# =============================================================================
# Node categories for coloring
# =============================================================================

MARKET_CATEGORIES = {
    "exogenous":  ["shock"],
    "parameters": ["production_cost", "demand_per_period", "demand_value", "storage_cost"],
    "state":      ["cash", "inventory", "price_history"],
    "mechanism":  ["agent_orders", "clearing_price", "volume"],
    "diagnostic": ["fundamental_price"],
}

CONFLICT_CATEGORIES = {
    "exogenous":  ["shock"],
    "agent":      ["hawk_score", "agent_recommendation", "faction_action"],
    "outcome":    ["escalation_index"],
    "faction":    ["resources", "gdp", "military_strength", "political_stability"],
    "global":     ["military_balance", "territory_controlled", "sanctions_level",
                   "international_support"],
}

CATEGORY_COLORS = {
    "exogenous":  "#e74c3c",   # red
    "parameters": "#3498db",   # blue
    "state":      "#2ecc71",   # green
    "mechanism":  "#f39c12",   # orange
    "diagnostic": "#95a5a6",   # gray
    "agent":      "#9b59b6",   # purple
    "outcome":    "#e74c3c",   # red
    "faction":    "#3498db",   # blue
    "global":     "#1abc9c",   # teal
}


def _build_digraph(adj_matrix: np.ndarray, variables: list[str]) -> nx.DiGraph:
    """Convert adjacency matrix to networkx DiGraph."""
    G = nx.DiGraph()
    G.add_nodes_from(variables)
    n = len(variables)
    for i in range(n):
        for j in range(n):
            if adj_matrix[i, j] == 1:
                G.add_edge(variables[i], variables[j])
    return G


def _get_node_colors(
    variables: list[str],
    categories: dict[str, list[str]],
) -> list[str]:
    """Map each variable to its category color."""
    var_to_cat = {}
    for cat, vars_list in categories.items():
        for v in vars_list:
            var_to_cat[v] = cat
    return [CATEGORY_COLORS.get(var_to_cat.get(v, ""), "#cccccc") for v in variables]


def _short_label(name: str) -> str:
    """Shorten variable names for display."""
    replacements = {
        "production_cost": "prod_cost",
        "demand_per_period": "demand_qty",
        "demand_value": "demand_val",
        "storage_cost": "stor_cost",
        "price_history": "price_hist",
        "agent_orders": "orders",
        "clearing_price": "clear_price",
        "fundamental_price": "fund_price",
        "escalation_index": "escalation",
        "hawk_score": "hawk_score",
        "agent_recommendation": "agent_rec",
        "faction_action": "faction_act",
        "military_strength": "mil_strength",
        "political_stability": "pol_stability",
        "military_balance": "mil_balance",
        "territory_controlled": "territory",
        "sanctions_level": "sanctions",
        "international_support": "intl_support",
    }
    return replacements.get(name, name)


# =============================================================================
# Market layout — manually tuned for readability
# =============================================================================

MARKET_POS = {
    # Exogenous (top)
    "shock":              (0.0, 1.0),
    # Parameters (upper layer)
    "production_cost":    (-0.7, 0.65),
    "demand_per_period":  (-0.2, 0.7),
    "demand_value":       (0.3, 0.7),
    "storage_cost":       (0.75, 0.65),
    # State (middle layer)
    "cash":               (-0.6, 0.25),
    "inventory":          (0.05, 0.3),
    "price_history":      (0.65, 0.25),
    # Mechanism (lower layer)
    "agent_orders":       (0.0, -0.05),
    "clearing_price":     (0.05, -0.45),
    "volume":             (0.65, -0.45),
    # Diagnostic (bottom left — non-causal)
    "fundamental_price":  (-0.65, -0.45),
}


# =============================================================================
# Conflict layout — manually tuned for readability
# =============================================================================

CONFLICT_POS = {
    # Exogenous (top center)
    "shock":                (0.0, 1.0),
    # Agent decision chain (left side)
    "hawk_score":           (-0.8, 0.6),
    "agent_recommendation": (-0.45, 0.3),
    "faction_action":       (0.0, 0.0),
    # Outcome (center below)
    "escalation_index":     (0.0, -0.45),
    # Faction state (left)
    "resources":            (-0.8, 0.0),
    "gdp":                  (-0.8, -0.45),
    # Global state (right)
    "military_strength":    (0.8, 0.3),
    "military_balance":     (0.8, 0.0),
    "territory_controlled": (0.8, -0.7),
    "political_stability":  (0.55, -0.7),
    "sanctions_level":      (0.0, -0.85),
    "international_support": (-0.45, -0.7),
}


def plot_market_ground_truth(ax: plt.Axes | None = None, show_legend: bool = True):
    """Plot the market engine ground truth causal graph."""
    M = get_market_ground_truth()
    G = _build_digraph(M, MARKET_VARIABLES)
    colors = _get_node_colors(MARKET_VARIABLES, MARKET_CATEGORIES)
    labels = {v: _short_label(v) for v in MARKET_VARIABLES}

    if ax is None:
        fig, ax = plt.subplots(1, 1, figsize=(14, 10))
    else:
        fig = ax.get_figure()

    # Draw edges
    nx.draw_networkx_edges(
        G, MARKET_POS, ax=ax,
        edge_color="#555555",
        arrows=True,
        arrowsize=18,
        arrowstyle="-|>",
        connectionstyle="arc3,rad=0.1",
        width=1.5,
        alpha=0.7,
        min_source_margin=20,
        min_target_margin=20,
    )

    # Draw nodes
    nx.draw_networkx_nodes(
        G, MARKET_POS, ax=ax,
        node_color=colors,
        node_size=2200,
        alpha=0.9,
        edgecolors="#333333",
        linewidths=1.5,
    )

    # Draw labels
    nx.draw_networkx_labels(
        G, MARKET_POS, labels, ax=ax,
        font_size=8,
        font_weight="bold",
        font_family="sans-serif",
    )

    if show_legend:
        legend_patches = [
            mpatches.Patch(color=CATEGORY_COLORS["exogenous"], label="Exogenous"),
            mpatches.Patch(color=CATEGORY_COLORS["parameters"], label="Parameters"),
            mpatches.Patch(color=CATEGORY_COLORS["state"], label="State"),
            mpatches.Patch(color=CATEGORY_COLORS["mechanism"], label="Mechanism"),
            mpatches.Patch(color=CATEGORY_COLORS["diagnostic"], label="Diagnostic (non-causal)"),
        ]
        ax.legend(handles=legend_patches, loc="lower left", fontsize=9,
                  framealpha=0.9, edgecolor="#cccccc")

    n_edges = int(np.sum(M))
    ax.set_title(f"Market Engine - Ground Truth Causal Graph\n"
                 f"{len(MARKET_VARIABLES)} variables, {n_edges} edges",
                 fontsize=14, fontweight="bold", pad=15)
    ax.axis("off")

    return fig, ax


def plot_conflict_ground_truth(ax: plt.Axes | None = None, show_legend: bool = True):
    """Plot the conflict engine ground truth causal graph."""
    M = get_conflict_ground_truth()
    G = _build_digraph(M, CONFLICT_VARIABLES)
    colors = _get_node_colors(CONFLICT_VARIABLES, CONFLICT_CATEGORIES)
    labels = {v: _short_label(v) for v in CONFLICT_VARIABLES}

    if ax is None:
        fig, ax = plt.subplots(1, 1, figsize=(14, 10))
    else:
        fig = ax.get_figure()

    # Draw edges
    nx.draw_networkx_edges(
        G, CONFLICT_POS, ax=ax,
        edge_color="#555555",
        arrows=True,
        arrowsize=18,
        arrowstyle="-|>",
        connectionstyle="arc3,rad=0.1",
        width=1.5,
        alpha=0.7,
        min_source_margin=20,
        min_target_margin=20,
    )

    # Draw nodes
    nx.draw_networkx_nodes(
        G, CONFLICT_POS, ax=ax,
        node_color=colors,
        node_size=2200,
        alpha=0.9,
        edgecolors="#333333",
        linewidths=1.5,
    )

    # Draw labels
    nx.draw_networkx_labels(
        G, CONFLICT_POS, labels, ax=ax,
        font_size=8,
        font_weight="bold",
        font_family="sans-serif",
    )

    if show_legend:
        legend_patches = [
            mpatches.Patch(color=CATEGORY_COLORS["exogenous"], label="Exogenous"),
            mpatches.Patch(color=CATEGORY_COLORS["agent"], label="Agent Decisions"),
            mpatches.Patch(color=CATEGORY_COLORS["outcome"], label="Outcome (EI)"),
            mpatches.Patch(color=CATEGORY_COLORS["faction"], label="Faction State"),
            mpatches.Patch(color=CATEGORY_COLORS["global"], label="Global State"),
        ]
        ax.legend(handles=legend_patches, loc="lower left", fontsize=9,
                  framealpha=0.9, edgecolor="#cccccc")

    n_edges = int(np.sum(M))
    ax.set_title(f"Conflict Engine - Ground Truth Causal Graph\n"
                 f"{len(CONFLICT_VARIABLES)} variables, {n_edges} edges",
                 fontsize=14, fontweight="bold", pad=15)
    ax.axis("off")

    return fig, ax


def main():
    """Generate and save both ground truth plots."""
    out_dir = Path("outputs/causal_discovery_pilot")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Market graph
    fig_m, _ = plot_market_ground_truth()
    fig_m.tight_layout()
    fig_m.savefig(out_dir / "ground_truth_market.png", dpi=200, bbox_inches="tight",
                  facecolor="white", edgecolor="none")
    print(f"Saved: {out_dir / 'ground_truth_market.png'}")

    # Conflict graph
    fig_c, _ = plot_conflict_ground_truth()
    fig_c.tight_layout()
    fig_c.savefig(out_dir / "ground_truth_conflict.png", dpi=200, bbox_inches="tight",
                  facecolor="white", edgecolor="none")
    print(f"Saved: {out_dir / 'ground_truth_conflict.png'}")

    # Combined side-by-side
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(26, 11))
    plot_market_ground_truth(ax=ax1)
    plot_conflict_ground_truth(ax=ax2)
    fig.suptitle("Ground Truth Causal Graphs", fontsize=16, fontweight="bold", y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(out_dir / "ground_truth_combined.png", dpi=200, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    print(f"Saved: {out_dir / 'ground_truth_combined.png'}")

    plt.close("all")


if __name__ == "__main__":
    main()
