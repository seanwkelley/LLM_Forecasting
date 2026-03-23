#!/usr/bin/env python3
"""Generate propagation decay figure (single panel: effect vs graph distance)."""

import json
import glob
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
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
})

BASE = Path(__file__).parent.parent
PROP_DIR = BASE / "outputs" / "sensitivity" / "causal" / "70b_one_turn" / "propagation_results"
OUT_DIR = BASE / "paper" / "figures" / "supplementary"


def _probe_direction(probe_type: str) -> str:
    if "negate" in probe_type:
        return "negate"
    if "strengthen" in probe_type:
        return "strengthen"
    return probe_type


def load_propagation_data() -> list[dict]:
    """Load all (direction, distance, abs_impact) triples."""
    rows = []
    for f in sorted(glob.glob(str(PROP_DIR / "q_*.json"))):
        data = json.load(open(f))
        for pr in data.get("propagation_results", []):
            if not pr.get("success"):
                continue
            direction = _probe_direction(pr["probe_type"])
            for node_id, eff in pr.get("downstream_effects", {}).items():
                dist = eff.get("undirected_distance", -1)
                ai = eff.get("abs_impact", 0)
                if dist >= 1:
                    rows.append({"direction": direction, "distance": dist, "abs_impact": ai})
    return rows


def compute_decay_curve(rows, max_dist=5, n_boot=10_000):
    """Compute mean + bootstrap CI per distance."""
    rng = np.random.default_rng(42)
    by_dist = {}
    for r in rows:
        d = r["distance"]
        if d <= max_dist:
            by_dist.setdefault(d, []).append(r["abs_impact"])

    dists = sorted(by_dist.keys())
    means, ci_los, ci_his, ns = [], [], [], []
    for d in dists:
        vals = np.array(by_dist[d])
        m = np.mean(vals)
        boots = np.array([np.mean(rng.choice(vals, size=len(vals)))
                          for _ in range(n_boot)])
        lo, hi = np.percentile(boots, [2.5, 97.5])
        means.append(m)
        ci_los.append(lo)
        ci_his.append(hi)
        ns.append(len(vals))

    all_d = [r["distance"] for r in rows if r["distance"] <= max_dist]
    all_ai = [r["abs_impact"] for r in rows if r["distance"] <= max_dist]
    rho, p = stats.spearmanr(all_d, all_ai)

    return dists, means, ci_los, ci_his, ns, rho, p


def main():
    rows = load_propagation_data()
    print(f"Total pairs: {len(rows)}")

    negate_rows = [r for r in rows if r["direction"] == "negate"]
    strengthen_rows = [r for r in rows if r["direction"] == "strengthen"]

    # ── Figure: single panel, overlaid ──────────────────────────────────
    fig, ax = plt.subplots(1, 1, figsize=(5, 3.8))

    configs = [
        (negate_rows, "Negate", "#D55E00"),
        (strengthen_rows, "Strengthen", "#009E73"),
    ]

    for data, label, color in configs:
        dists, means, ci_los, ci_his, ns, rho, p = compute_decay_curve(data)

        ax.plot(dists, means, "o-", color=color, markersize=6,
                linewidth=1.5, zorder=3, label=label)
        ax.fill_between(dists, ci_los, ci_his, color=color, alpha=0.15)

        print(f"\n{label}: rho={rho:.3f}, p={p:.1e}, n={len(data)}")
        for d, m, n in zip(dists, means, ns):
            print(f"  d={d}: mean={m:.3f} (n={n})")

    ax.set_xlabel("Graph distance from probed node")
    ax.set_ylabel("Mean |impact| on downstream node")
    ax.set_xticks(dists)
    ax.set_ylim(bottom=0)
    ax.legend(frameon=False)

    # ── Save ─────────────────────────────────────────────────────────────
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"propagation_decay.{ext}",
                    bbox_inches="tight", dpi=300)
    print(f"\nSaved to {OUT_DIR / 'propagation_decay.*'}")
    plt.close(fig)


if __name__ == "__main__":
    main()
