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
PROP_DIRS = {
    "GPT-OSS": BASE / "outputs" / "sensitivity" / "causal" / "gpt_oss_propagation" / "propagation_results",
}
PROP_DIR = PROP_DIRS["GPT-OSS"]  # default for single-model functions
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
    return "low"


def load_propagation_data(prop_dir=None) -> list[dict]:
    """Load all (direction, importance, distance, abs_impact) triples."""
    if prop_dir is None:
        prop_dir = PROP_DIR
    rows = []
    for f in sorted(glob.glob(str(prop_dir / "q_*.json"))):
        data = json.load(open(f))
        for pr in data.get("propagation_results", []):
            if not pr.get("success"):
                continue
            direction = _probe_direction(pr["probe_type"])
            importance = _importance_tier(pr["probe_type"])
            for node_id, eff in pr.get("downstream_effects", {}).items():
                dist = eff.get("undirected_distance", -1)
                ai = eff.get("abs_impact", 0)
                if dist >= 1:
                    rows.append({"direction": direction, "importance": importance,
                                 "distance": dist, "abs_impact": ai})
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
    # ── Single panel: negate + strengthen overlaid (GPT-OSS) ──
    prop_dir = PROP_DIRS["GPT-OSS"]
    rows = load_propagation_data(prop_dir)
    print(f"GPT-OSS: {len(rows)} total pairs")

    fig, ax = plt.subplots(figsize=(5, 4))

    negate_rows = [r for r in rows if r["direction"] == "negate"]
    strengthen_rows = [r for r in rows if r["direction"] == "strengthen"]

    configs = [
        (negate_rows, "Negate", "#D55E00"),
        (strengthen_rows, "Strengthen", "#009E73"),
    ]

    for data, label, color in configs:
        dists, means, ci_los, ci_his, ns, rho, p = compute_decay_curve(data)

        ax.plot(dists, means, "o-", color=color, markersize=6,
                linewidth=1.5, zorder=3, label=label)
        ax.fill_between(dists, ci_los, ci_his, color=color, alpha=0.15)

        print(f"\n  {label}: rho={rho:.3f}, p={p:.1e}, n={len(data)}")
        for d, m, n in zip(dists, means, ns):
            print(f"    d={d}: mean={m:.3f} (n={n})")

    ax.set_xlabel("Graph distance from probed node")
    ax.set_ylabel("Mean |impact| on downstream node")
    ax.set_xticks(range(1, 6))
    ax.set_ylim(bottom=0)
    ax.legend(frameon=False, fontsize=10)

    # ── Save ─────────────────────────────────────────────────────────────
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"propagation_decay.{ext}",
                    bbox_inches="tight", dpi=300)
    print(f"\nSaved to {OUT_DIR / 'propagation_decay.*'}")
    plt.close(fig)




def fig_directed():
    """Separate figure: downstream (directed) vs upstream impact."""
    rows_down = []  # directed distance >= 1
    rows_up = []    # directed unreachable but undirected reachable

    for f in sorted(glob.glob(str(PROP_DIR / "q_*.json"))):
        data = json.load(open(f))
        for pr in data.get("propagation_results", []):
            if not pr.get("success"):
                continue
            for node_id, eff in pr.get("downstream_effects", {}).items():
                dd = eff.get("directed_distance", -1)
                ud = eff.get("undirected_distance", -1)
                ai = eff.get("abs_impact", 0)
                if ud < 1:
                    continue
                if dd >= 1:
                    rows_down.append({"distance": dd, "abs_impact": ai})
                else:
                    rows_up.append({"distance": ud, "abs_impact": ai})

    print(f"\nDirected figure:")
    print(f"  Downstream: n={len(rows_down)}, mean={np.mean([r['abs_impact'] for r in rows_down]):.3f}")
    print(f"  Upstream:   n={len(rows_up)}, mean={np.mean([r['abs_impact'] for r in rows_up]):.3f}")

    fig, ax = plt.subplots(1, 1, figsize=(5, 3.8))

    # Downstream decay by directed distance
    dists_d, means_d, ci_los_d, ci_his_d, ns_d, rho_d, p_d = compute_decay_curve(
        rows_down, max_dist=3)  # cap at 3, sparse beyond
    ax.plot(dists_d, means_d, "o-", color="#0072B2", markersize=6,
            linewidth=1.5, zorder=3, label="Downstream")
    ax.fill_between(dists_d, ci_los_d, ci_his_d, color="#0072B2", alpha=0.15)

    print(f"  Downstream decay: rho={rho_d:.3f}")
    for d, m, n in zip(dists_d, means_d, ns_d):
        print(f"    d={d}: mean={m:.3f} (n={n})")

    # Upstream: show as horizontal band (no meaningful distance gradient expected)
    up_vals = np.array([r["abs_impact"] for r in rows_up])
    up_mean = np.mean(up_vals)
    rng = np.random.default_rng(42)
    boots = np.array([np.mean(rng.choice(up_vals, size=len(up_vals)))
                      for _ in range(10_000)])
    up_lo, up_hi = np.percentile(boots, [2.5, 97.5])

    ax.axhline(up_mean, color="#E69F00", linewidth=1.5, linestyle="--",
               label=f"Upstream (mean = {up_mean:.2f})", zorder=2)
    ax.axhspan(up_lo, up_hi, color="#E69F00", alpha=0.1)

    ax.set_xlabel("Directed distance from probed node")
    ax.set_ylabel("Mean |impact|")
    ax.set_xticks(dists_d)
    ax.set_ylim(bottom=0)
    ax.legend(frameon=False)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"propagation_directed.{ext}",
                    bbox_inches="tight", dpi=300)
    print(f"\nSaved to {OUT_DIR / 'propagation_directed.*'}")
    plt.close(fig)


def fig_downstream_by_direction():
    """Downstream-only decay split by negate vs strengthen."""
    rows = []
    for f in sorted(glob.glob(str(PROP_DIR / "q_*.json"))):
        data = json.load(open(f))
        for pr in data.get("propagation_results", []):
            if not pr.get("success"):
                continue
            direction = _probe_direction(pr["probe_type"])
            for node_id, eff in pr.get("downstream_effects", {}).items():
                dd = eff.get("directed_distance", -1)
                ai = eff.get("abs_impact", 0)
                if dd >= 1:
                    rows.append({"direction": direction, "distance": dd, "abs_impact": ai})

    fig, ax = plt.subplots(1, 1, figsize=(5, 3.8))

    configs = [
        ([r for r in rows if r["direction"] == "negate"], "Negate", "#D55E00"),
        ([r for r in rows if r["direction"] == "strengthen"], "Strengthen", "#009E73"),
    ]

    print("\nDownstream-only by direction:")
    for data, label, color in configs:
        dists, means, ci_los, ci_his, ns, rho, p = compute_decay_curve(data, max_dist=3)

        ax.plot(dists, means, "o-", color=color, markersize=6,
                linewidth=1.5, zorder=3, label=label)
        ax.fill_between(dists, ci_los, ci_his, color=color, alpha=0.15)

        print(f"  {label}: rho={rho:.3f}, p={p:.1e}, n={len(data)}")
        for d, m, n in zip(dists, means, ns):
            print(f"    d={d}: mean={m:.3f} (n={n})")

    ax.set_xlabel("Directed distance from probed node")
    ax.set_ylabel("Mean |impact| on downstream node")
    ax.set_xticks([1, 2, 3])
    ax.set_ylim(bottom=0)
    ax.legend(frameon=False)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"propagation_downstream.{ext}",
                    bbox_inches="tight", dpi=300)
    print(f"\nSaved to {OUT_DIR / 'propagation_downstream.*'}")
    plt.close(fig)


if __name__ == "__main__":
    main()
    fig_directed()
    fig_downstream_by_direction()
