"""Generate the methodology pipeline diagram for the paper.

Clean left-to-right flow. No cross-stage arrows.
Boxes well-spaced within each stage, large text.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

plt.rcParams.update({"font.family": "Arial", "font.size": 14, "figure.dpi": 300})

BASE = Path(__file__).parent.parent
OUT = BASE / "paper" / "figures" / "archive"

# ── Colors ──
C_INPUT = "#DCEEFB"
C_LLM = "#FFE0B2"
C_COMPUTE = "#D5ECD4"
C_OUTPUT = "#E8D5F5"
C_BORDER = "#444444"
C_ARROW = "#333333"
C_STAGE_BG = ["#F4F8FD", "#FDF8F2", "#F2FDF4"]


def _box(ax, x, y, w, h, title, subtitle, color, title_size=16, sub_size=13, bold=False):
    box = FancyBboxPatch(
        (x - w / 2, y - h / 2), w, h,
        boxstyle="round,pad=0.18",
        facecolor=color, edgecolor=C_BORDER, linewidth=2.0, zorder=3,
    )
    ax.add_patch(box)
    weight = "bold" if bold else "normal"
    if subtitle:
        n_sub_lines = subtitle.count("\n") + 1
        gap = min(0.35, h / 4) if n_sub_lines >= 3 else min(0.3, h / 3.5)
        ax.text(x, y + gap, title, ha="center", va="center",
                fontsize=title_size, fontweight=weight, zorder=4)
        ax.text(x, y - gap - 0.05, subtitle, ha="center", va="center",
                fontsize=sub_size, color="#333333", zorder=4)
    else:
        ax.text(x, y, title, ha="center", va="center",
                fontsize=title_size, fontweight=weight, zorder=4)


def _arrow(ax, x1, y1, x2, y2, rad=0.0):
    arrow = FancyArrowPatch(
        (x1, y1), (x2, y2),
        arrowstyle="-|>", mutation_scale=24, linewidth=2.5,
        color=C_ARROW, connectionstyle=f"arc3,rad={rad}", zorder=2,
        shrinkA=10, shrinkB=10,
    )
    ax.add_patch(arrow)


def _stage_bg(ax, x, y, w, h, color, edge_color):
    bg = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.3", facecolor=color,
        edgecolor=edge_color, linewidth=2.5, linestyle="--", zorder=0,
    )
    ax.add_patch(bg)


def main():
    fig, ax = plt.subplots(figsize=(24, 11))
    ax.set_xlim(-1.0, 24.5)
    ax.set_ylim(-2.0, 11.5)
    ax.set_axis_off()
    fig.patch.set_facecolor("white")

    # ── Stage backgrounds ──
    _stage_bg(ax, 0.0, 0.3, 6.4, 9.2, C_STAGE_BG[0], "#B0C4DE")
    ax.text(3.2, 10.0, "Stage 1: Causal Forecast", ha="center", va="bottom",
            fontsize=20, fontweight="bold", color="#333333", zorder=5)

    _stage_bg(ax, 7.4, 0.3, 7.6, 9.2, C_STAGE_BG[1], "#DEB887")
    ax.text(11.2, 10.0, "Stage 2: Probe Generation", ha="center", va="bottom",
            fontsize=20, fontweight="bold", color="#333333", zorder=5)

    _stage_bg(ax, 16.0, 0.3, 7.2, 9.2, C_STAGE_BG[2], "#90C090")
    ax.text(19.3, 10.0, "Stage 3: Probed Forecast", ha="center", va="bottom",
            fontsize=20, fontweight="bold", color="#333333", zorder=5)

    # ═══════════════════════════════════════════════════════════════════
    # STAGE 1
    # ═══════════════════════════════════════════════════════════════════
    _box(ax, 3.2, 8.5, 4.5, 1.0,
         "Binary Forecasting Question", None, C_INPUT, title_size=16)

    _box(ax, 3.2, 6.0, 3.4, 1.0,
         "LLM", None, C_LLM, title_size=18, bold=True)

    _box(ax, 1.8, 3.0, 2.8, 1.8,
         "Causal Network\n(DAG)", "4-8 factor nodes + outcome\n+ directed causal edges",
         C_OUTPUT, title_size=15, sub_size=12)

    _box(ax, 5.0, 3.0, 2.2, 1.4,
         "Initial P(Yes)", None, C_OUTPUT, title_size=16, bold=True)

    _arrow(ax, 3.2, 8.0, 3.2, 6.5)
    _arrow(ax, 2.2, 5.5, 1.9, 3.9)
    _arrow(ax, 4.2, 5.5, 4.8, 3.7)

    # ═══════════════════════════════════════════════════════════════════
    # STAGE 2  (vertical: Analysis → Targets → Probe Types → LLM)
    # ═══════════════════════════════════════════════════════════════════
    _box(ax, 11.2, 8.5, 3.6, 1.2,
         "Network Analysis", "Betweenness centrality,\nshortest-path detection",
         C_COMPUTE, title_size=16, sub_size=13)

    _box(ax, 11.2, 6.5, 3.6, 1.2,
         "Probe Targets", "Ranked by structural\nimportance",
         C_COMPUTE, title_size=16, sub_size=13)

    _box(ax, 11.2, 3.8, 5.4, 1.6,
         "14 Probe Types",
         "Node: negate, strengthen (high/med/low)\n"
         "Edge: negate, strengthen (crit./periph.), reverse, spurious\n"
         "Structural: missing node  |  Control: irrelevant",
         C_OUTPUT, title_size=14, sub_size=11)

    _box(ax, 11.2, 1.5, 2.6, 1.0,
         "LLM", "Generates probe text", C_LLM, title_size=18, sub_size=13, bold=True)

    # Network Analysis → Probe Targets
    _arrow(ax, 11.2, 7.9, 11.2, 7.1)

    # Probe Targets → 14 Probe Types
    _arrow(ax, 11.2, 5.9, 11.2, 4.6)

    # 14 Probe Types → LLM
    _arrow(ax, 11.2, 3.0, 11.2, 2.0)

    # ═══════════════════════════════════════════════════════════════════
    # STAGE 3
    # ═══════════════════════════════════════════════════════════════════
    _box(ax, 18.3, 8.5, 2.8, 1.0,
         "DAG + P(Yes)", "from Stage 1", C_INPUT, title_size=15, sub_size=13)

    _box(ax, 19.8, 6.2, 3.4, 1.2,
         "LLM", "DAG + P(Yes) + probe", C_LLM, title_size=18, sub_size=14, bold=True)

    _box(ax, 18.1, 3.2, 2.8, 1.5,
         "Updated P(Yes)", "Shift = P1 - P0", C_OUTPUT, title_size=16, sub_size=14, bold=True)

    _box(ax, 21.7, 3.2, 2.8, 1.5,
         "Stated Reasoning", "Which causal\npaths affected", C_OUTPUT, title_size=15, sub_size=13)

    # Repeat callout
    ax.text(22.0, 8.5, "~16 probes\nper question",
            ha="center", va="center", fontsize=15, fontweight="bold",
            color="#555555", zorder=5,
            bbox=dict(boxstyle="round,pad=0.35", facecolor="white",
                      edgecolor="#AAAAAA", linewidth=1.2))

    # Context box → LLM (within Stage 3)
    _arrow(ax, 19.0, 8.0, 19.4, 6.8)

    # LLM → Updated P
    _arrow(ax, 18.8, 5.6, 18.3, 3.95)

    # LLM → Reasoning
    _arrow(ax, 20.8, 5.6, 21.5, 3.95)

    # ── Legend (centered under Stage 2) ──
    legend_items = [
        (C_INPUT, "Input"),
        (C_LLM, "LLM Call"),
        (C_COMPUTE, "Computation"),
        (C_OUTPUT, "Output"),
    ]
    total_w = len(legend_items) * 2.2
    start_x = 11.2 - total_w / 2 + 1.0
    for i, (color, label) in enumerate(legend_items):
        lx = start_x + i * 2.2
        ly = -1.2
        patch = FancyBboxPatch(
            (lx - 0.3, ly - 0.22), 0.6, 0.44,
            boxstyle="round,pad=0.06", facecolor=color,
            edgecolor=C_BORDER, linewidth=1.3, zorder=3,
        )
        ax.add_patch(patch)
        ax.text(lx + 0.5, ly, label, ha="left", va="center",
                fontsize=14, zorder=4)

    plt.tight_layout()
    for ext in ["png", "pdf"]:
        fig.savefig(str(OUT / f"pipeline_diagram.{ext}"),
                    dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("Saved pipeline_diagram.png/pdf")


if __name__ == "__main__":
    main()
