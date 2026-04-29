"""Generate the combined exemplar networks figure for the paper.

Two side-by-side DAGs: (a) geopolitical, (b) pharmaceutical.
Simplified styling: all edges black, no critical-path distinction in legend.
Labels inside nodes, large nodes, well-spaced layout.
"""
import json, sys, textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import networkx as nx

from forecast_bench.network_analysis import analyze_network, _build_digraph

plt.rcParams.update({"font.family": "Arial", "font.size": 12, "figure.dpi": 300})

BASE = Path(__file__).parent.parent
OUT = BASE / "paper" / "figures" / "main"

# Question IDs (GPT-OSS neutral, 116 high-complexity questions)
CAUSAL_DIR = BASE / "outputs" / "sensitivity" / "causal" / "gpt_oss_neutral" / "_shared_stages_causal"
QUESTIONS = {
    "economics": "q_Qgg9Rc8PIy.json",
    "geopolitical": "q_x0N5kcbmFRaaxlj49kzO.json",
}


def _node_label(node_id, nodes_data):
    """Get a readable multi-line label for a node."""
    for n in nodes_data:
        if n["id"] == node_id:
            if n["role"] == "outcome":
                return "Outcome"
            else:
                label = _fix_title_case(node_id.replace("_", " ").title())
                # Wrap long labels into 2 lines to fit inside node
                # Wrap into lines to fit inside nodes
                label = "\n".join(textwrap.wrap(label, width=15))
                return label
    return _fix_title_case(node_id.replace("_", " ").title())


def _fix_title_case(s: str) -> str:
    """Fix .title() mangling of acronyms like US, UN, EU, GDP, NATO, etc."""
    fixes = {"Us": "US", "Un": "UN", "Eu": "EU", "Gdp": "GDP", "Nato": "NATO",
             "Uk": "UK", "Imf": "IMF", "Who": "WHO", "Ai": "AI"}
    for wrong, right in fixes.items():
        # Replace as whole word only
        s = s.replace(f" {wrong} ", f" {right} ")
        if s.startswith(wrong + " "):
            s = right + s[len(wrong):]
        if s.endswith(" " + wrong):
            s = s[:-len(wrong)] + right
    return s


def draw_network(ax, nodes, edges, analysis, initial_prob=None, label="(a)",
                 question_text=""):
    """Draw a single DAG panel with simplified styling."""
    G = _build_digraph(nodes, edges)

    # Importance lookup
    importance_map = {nm.node_id: nm.betweenness for nm in analysis.node_metrics}

    # Layout — strict hierarchical, no spring refinement
    outcome = [n for n in G.nodes if G.nodes[n].get("role") == "outcome"]
    if outcome:
        R = G.reverse()
        try:
            dists = nx.shortest_path_length(R, source=outcome[0])
        except Exception:
            dists = {}
        layers = {}
        for n in G.nodes:
            d = dists.get(n, max(dists.values()) if dists else 1)
            layers.setdefault(d, []).append(n)

        pos = {}
        layer_width = 4.0   # horizontal spacing between nodes in same layer
        layer_height = 3.5  # vertical spacing between layers
        for layer_y, nodes_in_layer in sorted(layers.items()):
            n_in_layer = len(nodes_in_layer)
            # Sort nodes for deterministic layout
            sorted_nodes = sorted(nodes_in_layer)
            for i, n in enumerate(sorted_nodes):
                x = (i - (n_in_layer - 1) / 2) * layer_width
                pos[n] = (x, layer_y * layer_height)
    else:
        pos = nx.kamada_kawai_layout(G)
        pos = {n: (x * 4.0, y * 4.0) for n, (x, y) in pos.items()}

    # --- Nodes (large, so text fits inside) ---
    factor_nodes = [n for n in G.nodes if G.nodes[n].get("role") != "outcome"]
    outcome_nodes = [n for n in G.nodes if G.nodes[n].get("role") == "outcome"]

    NODE_SIZE = 5000
    OUTCOME_SIZE = 5500

    if factor_nodes:
        nx.draw_networkx_nodes(
            G, pos, nodelist=factor_nodes, ax=ax,
            node_color="#A8D0E6", node_size=NODE_SIZE,
            edgecolors="#333333", linewidths=1.5,
        )

    if outcome_nodes:
        nx.draw_networkx_nodes(
            G, pos, nodelist=outcome_nodes, ax=ax,
            node_color="#E69F00", node_size=OUTCOME_SIZE,
            edgecolors="#333333", linewidths=2.0,
            node_shape="s",
        )

    # --- Edges: uniform black, margins to clear nodes ---
    all_edges = list(G.edges())
    if all_edges:
        nx.draw_networkx_edges(
            G, pos, edgelist=all_edges, ax=ax,
            edge_color="#333333", width=1.8, alpha=0.8,
            arrows=True, arrowsize=20, arrowstyle="-|>",
            connectionstyle="arc3,rad=0.12",
            min_source_margin=48, min_target_margin=48,
        )

    # --- Labels inside nodes (no background box) ---
    labels = {n: _node_label(n, nodes) for n in G.nodes}

    nx.draw_networkx_labels(
        G, pos, labels=labels, ax=ax,
        font_size=11, font_weight="bold", font_color="black",
    )

    # --- Question text as title (larger, black) ---
    if question_text:
        # Fix missing year and normalize date formats
        qt = question_text.replace("by December 31?", "by December 31, 2025?")
        qt = qt.replace("2025-12-28", "December 28, 2025")
        wrapped = "\n".join(textwrap.wrap(qt, width=42))
        ax.set_title(wrapped, fontsize=15, fontweight="bold", pad=30,
                     color="black")

    # --- Stats subtitle ---
    subtitle_parts = [f"{analysis.n_nodes} nodes, {analysis.n_edges} edges"]
    if initial_prob is not None:
        subtitle_parts.append(f"P(Yes) = {initial_prob:.0%}")
    subtitle_parts.append(f"density = {analysis.density:.2f}")
    ax.text(
        0.5, 1.01, "  |  ".join(subtitle_parts),
        transform=ax.transAxes, ha="center", fontsize=13, color="black",
    )

    # --- Panel label ---
    ax.text(-0.05, 1.14, label, transform=ax.transAxes,
            fontsize=20, fontweight="bold")

    ax.set_axis_off()
    ax.margins(0.20)


def main():
    panels = {}
    for name, fname in QUESTIONS.items():
        with open(CAUSAL_DIR / fname) as f:
            data = json.load(f)
        nodes = data["nodes"]
        edges = data["edges"]
        prob = data.get("probability", data.get("initial_probability"))
        question_text = data.get("question_text", "")
        analysis = analyze_network(nodes, edges)
        panels[name] = (nodes, edges, analysis, prob, question_text)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 10))
    fig.patch.set_facecolor("white")

    n1, e1, a1, p1, q1 = panels["economics"]
    n2, e2, a2, p2, q2 = panels["geopolitical"]
    draw_network(ax1, n1, e1, a1, p1, label="(a)", question_text=q1)
    draw_network(ax2, n2, e2, a2, p2, label="(b)", question_text=q2)

    plt.tight_layout()

    for ext in ["png", "pdf"]:
        fig.savefig(str(OUT / f"exemplar_networks_combined.{ext}"),
                    dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("Saved exemplar_networks_combined")


if __name__ == "__main__":
    main()
