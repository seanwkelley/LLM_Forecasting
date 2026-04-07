"""
Analyze: Does superforecasting framing change the causal DAG?

Compares baseline vs superforecasting-augmented DAGs for the same model+questions.
Primary metric: semantic nGED (normalized graph edit distance with embedding-based
node matching).

Usage:
    python -m forecast_bench.analyze_superforecasting_dag
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats as sp_stats
from forecast_bench.semantic_graph_match import (
    semantic_jaccard_pair,
    semantic_nged_for_pair,
    _ensure_embeddings,
    _get_api_key,
    NODE_EMB_CACHE,
    NODE_EMB_KEYS_CACHE,
)

plt.rcParams.update({"font.family": "Arial", "font.size": 10, "figure.dpi": 300})

BLUE, ORANGE, VERMILLION, GREEN = "#0072B2", "#E69F00", "#D55E00", "#009E73"

BASE = Path(__file__).parent.parent
CAUSAL = BASE / "outputs" / "sensitivity" / "causal"
OUT = BASE / "paper" / "figures"

BASELINE_DIR = CAUSAL / "gpt_oss_neutral" / "_shared_stages_causal"
SF_DIR = CAUSAL / "gpt_oss_superforecasting" / "_superforecasting_results"


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


def _embed_all_nodes(baseline: dict, sf: dict, shared_qids: list[str]):
    """Embed all nodes for both conditions, return (node_idx, node_mat)."""
    api_key = _get_api_key()
    node_texts: dict[str, str] = {}

    for qid in shared_qids:
        for n in baseline[qid].get("nodes", []):
            key = f"node|{qid}|baseline|{n['id']}"
            desc = n.get("description", n["id"])
            node_texts[key] = f"{n['id']}: {desc}"
        for n in sf[qid].get("nodes", []):
            key = f"node|{qid}|superforecasting|{n['id']}"
            desc = n.get("description", n["id"])
            node_texts[key] = f"{n['id']}: {desc}"

    print(f"Ensuring embeddings for {len(node_texts)} node texts...")
    node_idx, node_mat = _ensure_embeddings(
        node_texts, NODE_EMB_CACHE, NODE_EMB_KEYS_CACHE, api_key
    )
    return node_idx, node_mat


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

    # ── Embed all nodes ──
    node_idx, node_mat = _embed_all_nodes(baseline, sf, shared_qids)

    # ── Compute per-question comparisons ──
    comparisons = []
    for qid in shared_qids:
        bp = extract_graph_props(baseline[qid])
        sp = extract_graph_props(sf[qid])

        # Semantic nGED (primary metric)
        b_nodes = baseline[qid].get("nodes", [])
        b_edges = baseline[qid].get("edges", [])
        s_nodes = sf[qid].get("nodes", [])
        s_edges = sf[qid].get("edges", [])

        nged = semantic_nged_for_pair(
            b_nodes, b_edges, s_nodes, s_edges,
            node_idx, node_mat,
            model1="baseline", model2="superforecasting",
            qid1=qid, qid2=qid,
            threshold=0.7,
        )

        # Semantic Jaccard (backward compat)
        sem = semantic_jaccard_pair(
            [n for n in b_nodes if n.get("role") != "outcome"],
            [n for n in s_nodes if n.get("role") != "outcome"],
            edges1=b_edges, edges2=s_edges,
            condition1="baseline", condition2="superforecasting",
            qid=qid,
        )

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
            # Primary metric
            "semantic_nged": nged,
            # Backward compat
            "node_jaccard": jaccard(bp["factor_ids"], sp["factor_ids"]),
            "edge_jaccard": jaccard(bp["edge_tuples"], sp["edge_tuples"]),
            "semantic": sem,
        })

    # ── Print summary stats ──
    print(f"\n{'='*70}")
    print("SUMMARY: Baseline vs Superforecasting DAGs")
    print(f"{'='*70}")

    nged_vals = [c["semantic_nged"] for c in comparisons]
    node_j = [c["node_jaccard"] for c in comparisons]
    edge_j = [c["edge_jaccard"] for c in comparisons]
    prob_diffs = [c["prob_diff"] for c in comparisons if c["prob_diff"] is not None]

    sem_node_j = [c["semantic"]["node_jaccard"] for c in comparisons]
    sem_edge_j = [c["semantic"]["mapped_edge_jaccard"] for c in comparisons]

    print(f"\nSemantic nGED (primary):  mean={np.mean(nged_vals):.3f}, "
          f"median={np.median(nged_vals):.3f}, std={np.std(nged_vals):.3f}")
    print(f"Node Jaccard (exact):     mean={np.mean(node_j):.3f}, median={np.median(node_j):.3f}, "
          f"std={np.std(node_j):.3f}")
    print(f"Edge Jaccard (exact):     mean={np.mean(edge_j):.3f}, median={np.median(edge_j):.3f}, "
          f"std={np.std(edge_j):.3f}")
    print(f"Node Jaccard (semantic):  mean={np.mean(sem_node_j):.3f}, median={np.median(sem_node_j):.3f}, "
          f"std={np.std(sem_node_j):.3f}")
    print(f"Edge Jaccard (semantic):  mean={np.mean(sem_edge_j):.3f}, median={np.median(sem_edge_j):.3f}, "
          f"std={np.std(sem_edge_j):.3f}")
    print(f"Prob |diff|:              mean={np.mean(prob_diffs):.3f}, median={np.median(prob_diffs):.3f}")

    # Structure differences
    n_nodes_b = [c["n_nodes_baseline"] for c in comparisons]
    n_nodes_s = [c["n_nodes_sf"] for c in comparisons]
    n_edges_b = [c["n_edges_baseline"] for c in comparisons]
    n_edges_s = [c["n_edges_sf"] for c in comparisons]
    density_b = [c["density_baseline"] for c in comparisons]
    density_s = [c["density_sf"] for c in comparisons]

    print(f"\nNodes:   baseline={np.mean(n_nodes_b):.1f}\u00b1{np.std(n_nodes_b):.1f}, "
          f"SF={np.mean(n_nodes_s):.1f}\u00b1{np.std(n_nodes_s):.1f}")
    print(f"Edges:   baseline={np.mean(n_edges_b):.1f}\u00b1{np.std(n_edges_b):.1f}, "
          f"SF={np.mean(n_edges_s):.1f}\u00b1{np.std(n_edges_s):.1f}")
    print(f"Density: baseline={np.mean(density_b):.3f}\u00b1{np.std(density_b):.3f}, "
          f"SF={np.mean(density_s):.3f}\u00b1{np.std(density_s):.3f}")

    # Statistical tests
    if len(shared_qids) >= 10:
        t_nodes, p_nodes = sp_stats.wilcoxon(n_nodes_b, n_nodes_s)
        t_edges, p_edges = sp_stats.wilcoxon(n_edges_b, n_edges_s)
        t_density, p_density = sp_stats.wilcoxon(density_b, density_s)
    else:
        t_nodes, p_nodes = 0, 1
        t_edges, p_edges = 0, 1
        t_density, p_density = 0, 1

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
    N_PERM = 2000
    rng = np.random.default_rng(42)
    n_q = len(shared_qids)

    obs_nged = np.mean(nged_vals)

    print(f"\nRunning permutation test ({N_PERM} permutations)...")
    perm_nged = np.zeros(N_PERM)

    for p in range(N_PERM):
        perm_idx = rng.permutation(n_q)
        nged_perm = []
        for i in range(n_q):
            qid_b = shared_qids[i]
            qid_s = shared_qids[perm_idx[i]]

            b_nodes = baseline[qid_b].get("nodes", [])
            b_edges = baseline[qid_b].get("edges", [])
            s_nodes = sf[qid_s].get("nodes", [])
            s_edges = sf[qid_s].get("edges", [])

            val = semantic_nged_for_pair(
                b_nodes, b_edges, s_nodes, s_edges,
                node_idx, node_mat,
                model1="baseline", model2="superforecasting",
                qid1=qid_b, qid2=qid_s,
                threshold=0.7,
            )
            nged_perm.append(val)
        perm_nged[p] = np.mean(nged_perm)
        if (p + 1) % 200 == 0:
            print(f"  permutation {p + 1}/{N_PERM}")

    # p-value: observed nGED should be LOWER than null (more similar)
    p_nged = np.mean(perm_nged <= obs_nged)

    null_mean = np.mean(perm_nged)
    null_std = np.std(perm_nged)

    print(f"\nPermutation test ({N_PERM} permutations):")
    print(f"  Semantic nGED: obs={obs_nged:.3f}, null={null_mean:.3f}\u00b1{null_std:.3f}, p={p_nged:.4f}")

    # ── Generate figure: 1x2 -- (a) nGED null histogram, (b) probability scatter ──

    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(10, 3.5),
                                      gridspec_kw={"width_ratios": [1, 1]})
    fig.patch.set_facecolor("white")

    # Panel (a): histogram of null nGED distribution with observed line
    lo, hi = np.percentile(perm_nged, [2.5, 97.5])
    stars = "***" if p_nged < 0.001 else "**" if p_nged < 0.01 else "*" if p_nged < 0.05 else "n.s."

    ax_a.hist(perm_nged, bins=40, color="#999", alpha=0.5, edgecolor="white",
              label=f"Null (n={N_PERM})")
    ax_a.axvline(obs_nged, color=VERMILLION, linewidth=2.5, linestyle="-",
                 label=f"Observed = {obs_nged:.3f}")
    ax_a.axvline(null_mean, color=BLUE, linewidth=1.5, linestyle="--",
                 label=f"Null mean = {null_mean:.3f}")
    ax_a.axvspan(lo, hi, alpha=0.12, color=BLUE, label="Null 95% CI")
    ax_a.set_xlabel("Mean Semantic nGED")
    ax_a.set_ylabel("Frequency")
    ax_a.legend(fontsize=8, framealpha=0.9)
    ax_a.text(0.02, 0.95, f"p = {p_nged:.4f} {stars}",
              transform=ax_a.transAxes,
              va="top", ha="left", fontsize=11, fontweight="bold", color=VERMILLION)
    ax_a.text(-0.18, 1.05, "(a)", transform=ax_a.transAxes, fontsize=14, fontweight="bold")

    # Panel (b): Probability scatter with OLS
    pb = np.array(probs_b[:len(probs_s)])
    ps = np.array(probs_s[:len(probs_b)])
    ax_b.scatter(pb, ps, color=BLUE, alpha=0.8, s=50, edgecolors="none")
    if len(pb) >= 3:
        slope, intercept, r_val, p_val, _ = sp_stats.linregress(pb, ps)
        x_fit = np.linspace(0, 1, 100)
        ax_b.plot(x_fit, slope * x_fit + intercept, color=VERMILLION, linewidth=2)
        p_str = "p < 0.001" if p_val < 0.001 else f"p = {p_val:.3f}"
        ax_b.text(0.05, 0.92, f"r = {r_val:.2f}, {p_str}",
                  transform=ax_b.transAxes, fontsize=10)
    ax_b.set_xlabel("P(Yes) — Baseline")
    ax_b.set_ylabel("P(Yes) — Superforecasting")
    ax_b.set_xlim(0, 1); ax_b.set_ylim(0, 1)
    ax_b.set_aspect("equal")
    ax_b.text(-0.12, 1.05, "(b)", transform=ax_b.transAxes, fontsize=14, fontweight="bold")

    plt.tight_layout()
    supp_dir = OUT / "supplementary"
    supp_dir.mkdir(exist_ok=True)
    for ext in ["png", "pdf"]:
        fig.savefig(str(supp_dir / f"superforecasting_dag_comparison.{ext}"),
                    dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"\nFigure saved to {supp_dir / 'superforecasting_dag_comparison.png'}")


if __name__ == "__main__":
    main()
