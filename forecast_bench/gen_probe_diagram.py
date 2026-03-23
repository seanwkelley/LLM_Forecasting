"""Generate the propagation decay + compound probe procedure diagram."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 11,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.1,
    "mathtext.default": "regular",
})


def draw_node(ax, xy, label, color="#E8E8E8", edgecolor="black", textcolor="black",
              fontsize=8, radius=0.12, linewidth=1.5, zorder=3):
    circle = plt.Circle(xy, radius, facecolor=color, edgecolor=edgecolor,
                        linewidth=linewidth, zorder=zorder)
    ax.add_patch(circle)
    ax.text(xy[0], xy[1], label, ha="center", va="center", fontsize=fontsize,
            color=textcolor, zorder=zorder + 1, fontweight="bold")


def draw_arrow(ax, start, end, color="#666666", linewidth=1.2, radius=0.12):
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    dist = np.sqrt(dx ** 2 + dy ** 2)
    ux, uy = dx / dist, dy / dist
    sx = start[0] + ux * radius
    sy = start[1] + uy * radius
    ex = end[0] - ux * (radius + 0.03)
    ey = end[1] - uy * (radius + 0.03)
    ax.annotate("", xy=(ex, ey), xytext=(sx, sy),
                arrowprops=dict(arrowstyle="->", color=color, linewidth=linewidth))


def setup_ax(ax):
    ax.set_xlim(-0.3, 1.3)
    ax.set_ylim(-0.65, 1.7)
    ax.set_aspect("equal")
    ax.axis("off")


NODES = {
    "A": (0.2, 1.2), "B": (0.8, 1.2),
    "C": (0.0, 0.6), "D": (0.5, 0.6), "E": (1.0, 0.6),
    "O": (0.5, 0.0),
}
EDGES = [("A", "C"), ("A", "D"), ("B", "D"), ("B", "E"), ("C", "O"), ("D", "O"), ("E", "O")]


def draw_base_graph(ax):
    for s, e in EDGES:
        draw_arrow(ax, NODES[s], NODES[e])


def main():
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5), gridspec_kw={"wspace": 0.3})

    # --- Panel 1: Single probe ---
    ax = axes[0]
    setup_ax(ax)
    draw_base_graph(ax)
    for name, xy in NODES.items():
        if name == "A":
            draw_node(ax, xy, name, color="#D55E00", edgecolor="#D55E00", textcolor="white")
        elif name == "O":
            draw_node(ax, xy, "Outcome", color="#CCE5FF", edgecolor="#0072B2", fontsize=7)
        else:
            draw_node(ax, xy, name)
    ax.annotate("Probe A\n(negate)", xy=(0.2, 1.38), fontsize=8, ha="center", va="bottom",
                color="#D55E00", fontweight="bold")
    ax.text(0.5, -0.45, "p = 0.60  \u2192  0.45\n|shift(A)| = 0.15",
            fontsize=8, ha="center", va="top",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#FFF3E0", edgecolor="#D55E00"))
    ax.text(0.5, 1.65, "Single probe", fontsize=11, ha="center", fontweight="bold")

    # --- Panel 2: Propagation decay ---
    ax = axes[1]
    setup_ax(ax)
    draw_base_graph(ax)

    dist_colors = {"C": "#FFB74D", "D": "#FFB74D", "B": "#FFF176", "E": "#E0E0E0"}
    for name, xy in NODES.items():
        if name == "A":
            draw_node(ax, xy, name, color="#D55E00", edgecolor="#D55E00", textcolor="white")
        elif name == "O":
            draw_node(ax, xy, "Outcome", color="#CCE5FF", edgecolor="#0072B2", fontsize=7)
        else:
            draw_node(ax, xy, name, color=dist_colors.get(name, "#E8E8E8"))

    ax.annotate("Probe A\n(negate)", xy=(0.2, 1.38), fontsize=8, ha="center", va="bottom",
                color="#D55E00", fontweight="bold")
    # Distance labels
    ax.text(-0.18, 0.6, "d=1", fontsize=7, color="#E65100", fontweight="bold")
    ax.text(0.5, 0.42, "d=1", fontsize=7, color="#E65100", fontweight="bold", ha="center")
    ax.text(0.98, 1.2, "d=2", fontsize=7, color="#F57F17", fontweight="bold")
    ax.text(1.18, 0.6, "d=3", fontsize=7, color="#999", fontweight="bold")
    # Impact ratings
    ax.text(-0.25, 0.78, "+0.3", fontsize=7, color="#D55E00", fontstyle="italic")
    ax.text(0.5, 0.78, "+0.4", fontsize=7, color="#D55E00", fontstyle="italic", ha="center")
    ax.text(0.98, 1.38, "+0.1", fontsize=7, color="#F57F17", fontstyle="italic")
    ax.text(1.18, 0.78, "0.0", fontsize=7, color="#999", fontstyle="italic")

    ax.text(0.5, -0.35, "Rate impact on\neach other node", fontsize=8, ha="center",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#FFF3E0", edgecolor="#D55E00"))
    ax.text(0.5, 1.65, "Propagation decay", fontsize=11, ha="center", fontweight="bold")

    for fmt in ("pdf", "png"):
        fig.savefig(f"paper/figures/compound_probe_diagram.{fmt}",
                    bbox_inches="tight", dpi=300)
    print("Done")
    plt.close()


if __name__ == "__main__":
    main()
