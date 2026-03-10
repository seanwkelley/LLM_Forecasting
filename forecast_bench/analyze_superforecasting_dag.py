"""
Analyze: Does superforecasting framing change the causal DAG?

Compares baseline vs superforecasting-augmented DAGs for the same model+questions.

Usage:
    python -m forecast_bench.analyze_superforecasting_dag
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats as sp_stats

plt.rcParams.update({"font.family": "Arial", "font.size": 10, "figure.dpi": 300})

BLUE, ORANGE, VERMILLION, GREEN = "#0072B2", "#E69F00", "#D55E00", "#009E73"

BASE = Path(__file__).parent.parent
CAUSAL = BASE / "outputs" / "sensitivity" / "causal"
OUT = BASE / "paper" / "figures"

BASELINE_DIR = CAUSAL / "70b_one_turn" / "_shared_stages_causal"
SF_DIR = CAUSAL / "llama_70b_superforecasting" / "_superforecasting_results"


def load_dags(directory: Path) -> dict[str, dict]:
    """Load all question JSONs from a directory, keyed by question_id."""
    results = {}
    for f in sorted(directory.glob("*.json")):
        with open(f) as fh:
            d = json.load(fh)
        qid = d.get("question_id", f.stem)
        results[qid] = d
    return results


def jaccard(set_a: set, set_b: set) -> float:
    if not set_a and not set_b:
        return 1.0
    inter = len(set_a & set_b)
    union = len(set_a | set_b)
    return inter / union if union > 0 else 0.0


def graph_edit_distance(nodes1: set, edges1: set, nodes2: set, edges2: set) -> int:
    """Approximate GED: count node + edge insertions/deletions."""
    node_ins = len(nodes2 - nodes1)
    node_del = len(nodes1 - nodes2)
    edge_ins = len(edges2 - edges1)
    edge_del = len(edges1 - edges2)
    return node_ins + node_del + edge_ins + edge_del


def normalized_ged(nodes1: set, edges1: set, nodes2: set, edges2: set) -> float:
    """GED normalized by total elements (0=identical, 1=completely different)."""
    ged = graph_edit_distance(nodes1, edges1, nodes2, edges2)
    total = len(nodes1 | nodes2) + len(edges1 | edges2)
    return ged / total if total > 0 else 0.0


def spectral_distance(edges1: set, nodes1: set, edges2: set, nodes2: set) -> float:
    """Compare normalized Laplacian spectra of two graphs.

    Returns L2 distance between sorted eigenvalue vectors (padded to same length).
    Lower = more similar topology.
    """
    def _laplacian_spectrum(node_set, edge_set):
        node_list = sorted(node_set)
        idx = {n: i for i, n in enumerate(node_list)}
        n = len(node_list)
        if n == 0:
            return np.array([])
        adj = np.zeros((n, n))
        for (u, v) in edge_set:
            if u in idx and v in idx:
                adj[idx[u], idx[v]] = 1
                adj[idx[v], idx[u]] = 1  # treat as undirected for spectrum
        deg = np.diag(adj.sum(axis=1))
        laplacian = deg - adj
        # Normalized Laplacian
        d_inv_sqrt = np.diag(np.where(deg.diagonal() > 0, 1.0 / np.sqrt(deg.diagonal()), 0))
        norm_lap = np.eye(n) - d_inv_sqrt @ adj @ d_inv_sqrt
        eigvals = np.sort(np.real(np.linalg.eigvals(norm_lap)))
        return eigvals

    spec1 = _laplacian_spectrum(nodes1, edges1)
    spec2 = _laplacian_spectrum(nodes2, edges2)

    # Pad shorter spectrum with zeros
    max_len = max(len(spec1), len(spec2))
    if max_len == 0:
        return 0.0
    s1 = np.zeros(max_len)
    s2 = np.zeros(max_len)
    s1[:len(spec1)] = spec1
    s2[:len(spec2)] = spec2

    return float(np.linalg.norm(s1 - s2))


def extract_graph_props(d: dict) -> dict:
    """Extract key properties from a question result."""
    nodes = d.get("nodes", [])
    edges = d.get("edges", [])
    na = d.get("network_analysis", {})
    factor_nodes = [n for n in nodes if n.get("role") != "outcome"]
    return {
        "prob": d.get("initial_probability"),
        "n_nodes": len(nodes),
        "n_edges": len(edges),
        "n_factors": len(factor_nodes),
        "density": na.get("density", 0),
        "node_ids": {n["id"] for n in nodes},
        "edge_tuples": {(e["from"], e["to"]) for e in edges},
        "factor_ids": {n["id"] for n in factor_nodes},
        "node_descriptions": {n["id"]: n.get("description", "") for n in nodes},
    }


def main():
    # Load both conditions
    baseline = load_dags(BASELINE_DIR)
    sf = load_dags(SF_DIR)

    shared_qids = sorted(set(baseline.keys()) & set(sf.keys()))
    print(f"Baseline: {len(baseline)} questions")
    print(f"Superforecasting: {len(sf)} questions")
    print(f"Shared: {len(shared_qids)} questions")

    if len(shared_qids) < 5:
        print("Not enough shared questions yet. Run more of the superforecasting condition.")
        return

    # ── Compute per-question comparisons ──
    comparisons = []
    for qid in shared_qids:
        bp = extract_graph_props(baseline[qid])
        sp = extract_graph_props(sf[qid])

        comparisons.append({
            "qid": qid,
            "q_text": baseline[qid].get("question_text", "")[:60],
            # Probability
            "prob_baseline": bp["prob"],
            "prob_sf": sp["prob"],
            "prob_diff": abs(sp["prob"] - bp["prob"]) if bp["prob"] and sp["prob"] else None,
            # Structure
            "n_nodes_baseline": bp["n_nodes"],
            "n_nodes_sf": sp["n_nodes"],
            "n_edges_baseline": bp["n_edges"],
            "n_edges_sf": sp["n_edges"],
            "density_baseline": bp["density"],
            "density_sf": sp["density"],
            # Overlap
            "node_jaccard": jaccard(bp["factor_ids"], sp["factor_ids"]),
            "edge_jaccard": jaccard(bp["edge_tuples"], sp["edge_tuples"]),
            # Graph edit distance (normalized)
            "norm_ged": normalized_ged(bp["node_ids"], bp["edge_tuples"],
                                       sp["node_ids"], sp["edge_tuples"]),
            # Spectral distance
            "spectral_dist": spectral_distance(bp["edge_tuples"], bp["node_ids"],
                                                sp["edge_tuples"], sp["node_ids"]),
        })

    # ── Print summary stats ──
    print(f"\n{'='*70}")
    print("SUMMARY: Baseline vs Superforecasting DAGs")
    print(f"{'='*70}")

    node_j = [c["node_jaccard"] for c in comparisons]
    edge_j = [c["edge_jaccard"] for c in comparisons]
    prob_diffs = [c["prob_diff"] for c in comparisons if c["prob_diff"] is not None]

    norm_geds = [c["norm_ged"] for c in comparisons]
    spectral_dists = [c["spectral_dist"] for c in comparisons]

    print(f"\nNode Jaccard:    mean={np.mean(node_j):.3f}, median={np.median(node_j):.3f}, "
          f"std={np.std(node_j):.3f}")
    print(f"Edge Jaccard:    mean={np.mean(edge_j):.3f}, median={np.median(edge_j):.3f}, "
          f"std={np.std(edge_j):.3f}")
    print(f"Norm GED:        mean={np.mean(norm_geds):.3f}, median={np.median(norm_geds):.3f}, "
          f"std={np.std(norm_geds):.3f}")
    print(f"Spectral dist:   mean={np.mean(spectral_dists):.3f}, median={np.median(spectral_dists):.3f}, "
          f"std={np.std(spectral_dists):.3f}")
    print(f"Prob |diff|:     mean={np.mean(prob_diffs):.3f}, median={np.median(prob_diffs):.3f}")

    # Structure differences
    n_nodes_b = [c["n_nodes_baseline"] for c in comparisons]
    n_nodes_s = [c["n_nodes_sf"] for c in comparisons]
    n_edges_b = [c["n_edges_baseline"] for c in comparisons]
    n_edges_s = [c["n_edges_sf"] for c in comparisons]
    density_b = [c["density_baseline"] for c in comparisons]
    density_s = [c["density_sf"] for c in comparisons]

    print(f"\nNodes:   baseline={np.mean(n_nodes_b):.1f}±{np.std(n_nodes_b):.1f}, "
          f"SF={np.mean(n_nodes_s):.1f}±{np.std(n_nodes_s):.1f}")
    print(f"Edges:   baseline={np.mean(n_edges_b):.1f}±{np.std(n_edges_b):.1f}, "
          f"SF={np.mean(n_edges_s):.1f}±{np.std(n_edges_s):.1f}")
    print(f"Density: baseline={np.mean(density_b):.3f}±{np.std(density_b):.3f}, "
          f"SF={np.mean(density_s):.3f}±{np.std(density_s):.3f}")

    # Statistical tests
    t_nodes, p_nodes = sp_stats.wilcoxon(n_nodes_b, n_nodes_s) if len(shared_qids) >= 10 else (0, 1)
    t_edges, p_edges = sp_stats.wilcoxon(n_edges_b, n_edges_s) if len(shared_qids) >= 10 else (0, 1)
    t_density, p_density = sp_stats.wilcoxon(density_b, density_s) if len(shared_qids) >= 10 else (0, 1)

    probs_b = [c["prob_baseline"] for c in comparisons if c["prob_baseline"] is not None]
    probs_s = [c["prob_sf"] for c in comparisons if c["prob_sf"] is not None]
    if len(probs_b) >= 10:
        t_prob, p_prob = sp_stats.wilcoxon(probs_b[:len(probs_s)], probs_s[:len(probs_b)])
    else:
        t_prob, p_prob = 0, 1

    print(f"\nWilcoxon tests (paired):")
    print(f"  Nodes:   p={p_nodes:.4f}")
    print(f"  Edges:   p={p_edges:.4f}")
    print(f"  Density: p={p_density:.4f}")
    print(f"  Prob:    p={p_prob:.4f}")

    # Probability correlation
    if probs_b and probs_s:
        rho, p_rho = sp_stats.spearmanr(probs_b[:len(probs_s)], probs_s[:len(probs_b)])
        print(f"\nProbability correlation (Spearman): rho={rho:.3f}, p={p_rho:.4f}")

    # ── Permutation test: are same-question DAGs more similar than random pairings? ──
    N_PERM = 10000
    rng = np.random.default_rng(42)

    # Extract graph properties for all shared questions (ordered)
    baseline_props = [extract_graph_props(baseline[qid]) for qid in shared_qids]
    sf_props = [extract_graph_props(sf[qid]) for qid in shared_qids]
    n_q = len(shared_qids)

    # Observed means
    obs_node_j = np.mean(node_j)
    obs_edge_j = np.mean(edge_j)
    obs_ged = np.mean(norm_geds)
    obs_spectral = np.mean(spectral_dists)

    # Permutation null: shuffle SF DAG assignments across questions
    perm_node_j = np.zeros(N_PERM)
    perm_edge_j = np.zeros(N_PERM)
    perm_ged = np.zeros(N_PERM)
    perm_spectral = np.zeros(N_PERM)

    for p in range(N_PERM):
        perm_idx = rng.permutation(n_q)
        nj, ej, gd, sd = [], [], [], []
        for i in range(n_q):
            bp = baseline_props[i]
            sp = sf_props[perm_idx[i]]
            nj.append(jaccard(bp["factor_ids"], sp["factor_ids"]))
            ej.append(jaccard(bp["edge_tuples"], sp["edge_tuples"]))
            gd.append(normalized_ged(bp["node_ids"], bp["edge_tuples"],
                                     sp["node_ids"], sp["edge_tuples"]))
            sd.append(spectral_distance(bp["edge_tuples"], bp["node_ids"],
                                        sp["edge_tuples"], sp["node_ids"]))
        perm_node_j[p] = np.mean(nj)
        perm_edge_j[p] = np.mean(ej)
        perm_ged[p] = np.mean(gd)
        perm_spectral[p] = np.mean(sd)

    # p-values: for similarity metrics, observed > null means more similar than chance
    p_node_j = np.mean(perm_node_j >= obs_node_j)
    p_edge_j = np.mean(perm_edge_j >= obs_edge_j)
    # For distance metrics, observed < null means more similar than chance
    p_ged = np.mean(perm_ged <= obs_ged)
    p_spectral = np.mean(perm_spectral <= obs_spectral)

    print(f"\nPermutation test ({N_PERM} permutations):")
    print(f"  Node Jaccard:  obs={obs_node_j:.3f}, null={np.mean(perm_node_j):.3f}±{np.std(perm_node_j):.3f}, p={p_node_j:.4f}")
    print(f"  Edge Jaccard:  obs={obs_edge_j:.3f}, null={np.mean(perm_edge_j):.3f}±{np.std(perm_edge_j):.3f}, p={p_edge_j:.4f}")
    print(f"  Norm GED:      obs={obs_ged:.3f}, null={np.mean(perm_ged):.3f}±{np.std(perm_ged):.3f}, p={p_ged:.4f}")
    print(f"  Spectral dist: obs={obs_spectral:.3f}, null={np.mean(perm_spectral):.3f}±{np.std(perm_spectral):.3f}, p={p_spectral:.4f}")

    # ── Generate figure: 1×3 — (a) Jaccard, (b) Distance, (c) Probability ──
    from scipy.stats import gaussian_kde

    fig, (ax_a, ax_b, ax_c) = plt.subplots(1, 3, figsize=(16, 4.5))
    fig.patch.set_facecolor("white")

    metric_keys_a = [
        ("Node\nJaccard", obs_node_j, perm_node_j, BLUE),
        ("Edge\nJaccard", obs_edge_j, perm_edge_j, ORANGE),
    ]
    metric_keys_b = [
        ("Spectral\nDist", obs_spectral, perm_spectral, GREEN),
    ]

    for ax, metrics, xlabel in [
        (ax_a, metric_keys_a, "Jaccard Similarity\n(higher = more similar)"),
        (ax_b, metric_keys_b, "Spectral Distance\n(higher = more different)"),
    ]:
        for j, (label, obs, null_dist, color) in enumerate(metrics):
            kde = gaussian_kde(null_dist)
            x_range = np.linspace(null_dist.min(), null_dist.max(), 200)
            density = kde(x_range)
            density = density / density.max() * 0.35
            # Black baseline
            ax.hlines(j, null_dist.min(), null_dist.max(), color="black",
                      linewidth=0.8, zorder=1)
            # Half-violin above baseline
            ax.fill_between(x_range, j - density, j, alpha=0.5, color=color,
                            edgecolor=color, linewidth=0.5)
            # Observed diamond
            ax.scatter([obs], [j], color=color, s=100, zorder=5,
                       edgecolors="black", linewidths=1.5, marker="D")
        ax.set_yticks(list(range(len(metrics))))
        ax.set_yticklabels([m[0] for m in metrics], fontsize=9)
        ax.set_xlabel(xlabel, fontsize=9)
        ax.invert_yaxis()

    ax_a.text(-0.15, 1.05, "(a)", transform=ax_a.transAxes, fontsize=14, fontweight="bold")
    ax_b.text(-0.12, 1.05, "(b)", transform=ax_b.transAxes, fontsize=14, fontweight="bold")

    # (c) Probability scatter with OLS
    pb = np.array(probs_b[:len(probs_s)])
    ps = np.array(probs_s[:len(probs_b)])
    ax_c.scatter(pb, ps, color=BLUE, alpha=0.8, s=50, edgecolors="none")
    if len(pb) >= 3:
        slope, intercept, r_val, p_val, _ = sp_stats.linregress(pb, ps)
        x_fit = np.linspace(0, 1, 100)
        ax_c.plot(x_fit, slope * x_fit + intercept, color=VERMILLION, linewidth=2)
        p_str = "p < 0.001" if p_val < 0.001 else f"p = {p_val:.3f}"
        ax_c.text(0.05, 0.92, f"r = {r_val:.2f}, {p_str}",
                  transform=ax_c.transAxes, fontsize=10)
    ax_c.set_xlabel("P(Yes) — Baseline")
    ax_c.set_ylabel("P(Yes) — Superforecasting")
    ax_c.set_xlim(0, 1); ax_c.set_ylim(0, 1)
    ax_c.set_aspect("equal")
    ax_c.text(-0.12, 1.05, "(c)", transform=ax_c.transAxes, fontsize=14, fontweight="bold")

    plt.tight_layout()
    for ext in ["png", "pdf"]:
        fig.savefig(str(OUT / f"superforecasting_dag_comparison.{ext}"),
                    dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"\nFigure saved to {OUT / 'superforecasting_dag_comparison.png'}")


if __name__ == "__main__":
    main()
