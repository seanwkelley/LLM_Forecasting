#!/usr/bin/env python3
"""Generate compound interaction figure: probe direction pairing analysis."""

import json
import glob
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# ── Style ────────────────────────────────────────────────────────────────

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


def _probe_direction(probe_type: str) -> str:
    if "negate" in probe_type:
        return "negate"
    if "strengthen" in probe_type:
        return "strengthen"
    return probe_type


def _importance_tier(probe_type: str) -> str:
    if "_high" in probe_type or probe_type == "node_strengthen":
        return "high"
    if "_low" in probe_type:
        return "low"
    return "medium"


def load_compound_data() -> list[dict]:
    rows = []
    for f in sorted(glob.glob(str(COMPOUND_DIR / "q_*.json"))):
        data = json.load(open(f))
        initial_p = data.get("initial_probability", 0.5)
        for r in data.get("compound_results", []):
            if not r.get("success"):
                continue
            da = _probe_direction(r["probe_a_type"])
            db = _probe_direction(r["probe_b_type"])
            ia = _importance_tier(r["probe_a_type"])
            ib = _importance_tier(r["probe_b_type"])

            # For str+neg pairs, track which direction is high-importance
            dir_pair = tuple(sorted([da, db]))
            if dir_pair == ("negate", "strengthen"):
                if da == "strengthen":
                    str_imp, neg_imp = ia, ib
                else:
                    str_imp, neg_imp = ib, ia
                sub_label = f"str({str_imp})\n+neg({neg_imp})"
            else:
                sub_label = None

            rows.append({
                "dir_pair_label": f"{sorted([da,db])[0]} + {sorted([da,db])[1]}",
                "sub_label": sub_label,
                "signed_shift": r["updated_probability"] - initial_p,
            })
    return rows


def main():
    rows = load_compound_data()
    print(f"Loaded {len(rows)} compound pairs")

    # ── Groups ───────────────────────────────────────────────────────────
    # 4 boxplots: str+str, neg+neg, str(high)+neg(low), str(low)+neg(high)
    labels = [
        "str + str",
        "neg + neg",
        "str(high)\n+neg(low)",
        "str(low)\n+neg(high)",
    ]
    colors_list = [
        "#009E73",   # green
        "#D55E00",   # vermillion
        "#0072B2",   # blue
        "#56B4E9",   # sky blue
    ]

    groups = {
        "str + str": [r["signed_shift"] for r in rows
                      if r["dir_pair_label"] == "strengthen + strengthen"],
        "neg + neg": [r["signed_shift"] for r in rows
                      if r["dir_pair_label"] == "negate + negate"],
        "str(high)\n+neg(low)": [r["signed_shift"] for r in rows
                                  if r["sub_label"] == "str(high)\n+neg(low)"],
        "str(low)\n+neg(high)": [r["signed_shift"] for r in rows
                                  if r["sub_label"] == "str(low)\n+neg(high)"],
    }

    for label in labels:
        v = groups[label]
        if v:
            print(f"  {label.replace(chr(10), ' '):24s}: n={len(v):4d}, "
                  f"mean={np.mean(v):+.3f}, median={np.median(v):+.3f}")
        else:
            print(f"  {label.replace(chr(10), ' '):24s}: n=0")

    # ── Figure ───────────────────────────────────────────────────────────
    fig, ax = plt.subplots(1, 1, figsize=(5.5, 4))
    rng = np.random.default_rng(42)

    plot_data = [groups[label] for label in labels]
    positions = [0, 1, 2.5, 3.5]  # gap between concordant and mixed

    bp = ax.boxplot(plot_data, positions=positions, widths=0.55,
                    patch_artist=True, showfliers=False,
                    medianprops=dict(color="black", linewidth=1.5))

    for patch, color in zip(bp["boxes"], colors_list):
        patch.set_facecolor(color)
        patch.set_alpha(0.5)

    # Overlay individual points
    for pos, vals, color in zip(positions, plot_data, colors_list):
        if vals:
            jitter = rng.uniform(-0.15, 0.15, size=len(vals))
            ax.scatter(pos + jitter, vals, color=color, alpha=0.35,
                       s=14, zorder=3, edgecolors="none")

    ax.set_xticks(positions)
    ax.set_xticklabels(labels, fontsize=9)
    ax.axhline(0, color="black", linewidth=0.8, linestyle="--", alpha=0.5)
    ax.set_ylabel("Probability shift")
    ax.set_title("Compound probe shift by direction pairing")

    # Bracket label for the two mixed groups
    ax.annotate("", xy=(2.5, ax.get_ylim()[0] - 0.02),
                xytext=(3.5, ax.get_ylim()[0] - 0.02),
                arrowprops=dict(arrowstyle="-", color="gray", lw=0.8))

    # ── Save ─────────────────────────────────────────────────────────────
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"compound_interaction.{ext}",
                    bbox_inches="tight", dpi=300)
    print(f"Saved to {OUT_DIR / 'compound_interaction.*'}")
    plt.close(fig)


if __name__ == "__main__":
    main()
