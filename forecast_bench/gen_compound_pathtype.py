#!/usr/bin/env python3
"""Compound probe shift: same causal path vs independent, by direction."""

import json
import glob
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from scipy.stats import mannwhitneyu

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
    "boxplot.medianprops.color": "black",
    "boxplot.medianprops.linewidth": 1.5,
})

BASE = Path(__file__).parent.parent
COMPOUND_DIR = BASE / "outputs" / "sensitivity" / "causal" / "70b_one_turn" / "compound_results"
OUT_DIR = BASE / "paper" / "figures" / "supplementary"


def main():
    rows = []
    for f in sorted(glob.glob(str(COMPOUND_DIR / "q_*.json"))):
        data = json.load(open(f))
        initial_p = data.get("initial_probability", 0.5)
        for r in data.get("compound_results", []):
            if not r.get("success"):
                continue
            da = "negate" if "negate" in r["probe_a_type"] else "strengthen"
            db = "negate" if "negate" in r["probe_b_type"] else "strengthen"
            pair = tuple(sorted([da, db]))

            if pair == ("negate", "negate"):
                dp = "neg + neg"
            elif pair == ("strengthen", "strengthen"):
                dp = "str + str"
            else:
                continue  # skip mixed

            dab = r["directed_distance_ab"]
            dba = r["directed_distance_ba"]
            pt = "Same path" if (dab >= 1 or dba >= 1) else "Independent"

            rows.append({
                "dir": dp,
                "path": pt,
                "signed": r["updated_probability"] - initial_p,
            })

    # ── Figure ───────────────────────────────────────────────────────────
    fig, ax = plt.subplots(1, 1, figsize=(5.5, 4))
    rng = np.random.default_rng(42)

    from matplotlib.patches import Patch
    path_colors = {"Same path": "#0072B2", "Independent": "#E69F00"}
    dir_labels = ["str + str", "neg + neg"]

    positions = []
    plot_data = []
    plot_colors = []
    pos = 0
    group_centers = []

    for dp in dir_labels:
        gp = []
        for pt in ["Same path", "Independent"]:
            vals = [r["signed"] for r in rows if r["dir"] == dp and r["path"] == pt]
            plot_data.append(vals)
            plot_colors.append(path_colors[pt])
            positions.append(pos)
            gp.append(pos)
            pos += 1
        pos += 0.5
        group_centers.append(np.mean(gp))

        # Stats
        s = [r["signed"] for r in rows if r["dir"] == dp and r["path"] == "Same path"]
        i = [r["signed"] for r in rows if r["dir"] == dp and r["path"] == "Independent"]
        if s and i:
            u, p = mannwhitneyu(s, i, alternative="two-sided")
            stars = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "n.s."
            print(f"{dp:12s}  same: n={len(s):3d} mean={np.mean(s):+.3f}  |  "
                  f"indep: n={len(i):3d} mean={np.mean(i):+.3f}  |  p={p:.3f} ({stars})")

    bp = ax.boxplot(plot_data, positions=positions, widths=0.55,
                    patch_artist=True, showfliers=False,
                    medianprops=dict(color="black", linewidth=1.5))

    for patch, color in zip(bp["boxes"], plot_colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.5)

    for px, vals, color in zip(positions, plot_data, plot_colors):
        if vals:
            jitter = rng.uniform(-0.15, 0.15, size=len(vals))
            ax.scatter(px + jitter, vals, color=color, alpha=0.3,
                       s=12, zorder=3, edgecolors="none")

    ax.axhline(0, color="black", linewidth=0.8, linestyle="--", alpha=0.5)
    ax.set_xticks(group_centers)
    ax.set_xticklabels(dir_labels)
    ax.set_ylabel("Probability shift")

    # Significance brackets
    idx = 0
    for dp in dir_labels:
        s = [r["signed"] for r in rows if r["dir"] == dp and r["path"] == "Same path"]
        i = [r["signed"] for r in rows if r["dir"] == dp and r["path"] == "Independent"]
        if s and i:
            _, p = mannwhitneyu(s, i, alternative="two-sided")
            stars = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "n.s."
            p1, p2 = positions[idx], positions[idx + 1]
            all_vals = s + i
            y_top = np.percentile(all_vals, 97) + 0.02
            ax.plot([p1, p1, p2, p2], [y_top - 0.01, y_top, y_top, y_top - 0.01],
                    color="black", linewidth=0.8)
            ax.text((p1 + p2) / 2, y_top + 0.005, stars, ha="center", va="bottom",
                    fontsize=9, fontweight="bold")
        idx += 2

    # Legend
    legend_patches = [Patch(facecolor=path_colors[pt], alpha=0.5, label=pt)
                      for pt in ["Same path", "Independent"]]
    ax.legend(handles=legend_patches, frameon=False, loc="upper right")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"compound_pathtype.{ext}",
                    bbox_inches="tight", dpi=300)
    print(f"Saved to {OUT_DIR / 'compound_pathtype.*'}")
    plt.close(fig)


if __name__ == "__main__":
    main()
