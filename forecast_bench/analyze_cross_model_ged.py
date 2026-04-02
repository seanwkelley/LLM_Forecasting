"""
Cross-model DAG convergence test (semantic matching).

For each question, computes pairwise semantic node/edge Jaccard and aligned
spectral distance across all C(N,2) model pairs. Permutation test shuffles
question assignments to build a null, testing whether models produce more
similar DAGs for the same question than expected by chance.

Uses embedding-based Hungarian matching to align nodes across models
(different models use different node IDs for the same concept).

Usage:
    python -m forecast_bench.analyze_cross_model_ged
"""

from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from forecast_bench.semantic_graph_match import (
    _ensure_embeddings,
    _semantic_scores_for_pair,
    NODE_EMB_CACHE,
    NODE_EMB_KEYS_CACHE,
    EDGE_EMB_CACHE,
    EDGE_EMB_KEYS_CACHE,
    _get_api_key,
)

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
CAUSAL = BASE / "outputs" / "sensitivity" / "causal"
OUT = BASE / "paper" / "figures" / "supplementary"

MODEL_DIRS = {
    "Llama-3.1-8B": CAUSAL / "llama_neutral",
    "Llama-3.3-70B": CAUSAL / "llama_70b_neutral",
    "DeepSeek-V3": CAUSAL / "deepseek_neutral",
    "Qwen3-235B": CAUSAL / "qwen_neutral",
    "Gemini-Flash-Lite": CAUSAL / "gemini_fl_neutral",
    "GPT-OSS-120B": CAUSAL / "gpt_oss_neutral",
    "Qwen3-32B": CAUSAL / "qwen_32b_neutral",
}


def load_all_model_dags() -> dict[str, dict[str, dict]]:
    """Load DAGs for all models. Tries _shared_stages_causal first, falls back to question_results."""
    all_dags = {}
    for name, d in MODEL_DIRS.items():
        dags = {}
        # Try shared stages first (has DAG structure without probe results)
        shared_dir = d / "_shared_stages_causal"
        if shared_dir.exists() and any(shared_dir.glob("*.json")):
            for f in sorted(shared_dir.glob("*.json")):
                data = json.loads(f.read_text(encoding="utf-8"))
                qid = data.get("question_id", f.stem)
                dags[qid] = data
        else:
            # Fall back to question_results (has full data including DAG)
            qr_dir = d / "question_results"
            if not qr_dir.exists():
                print(f"  [SKIP] {name}: no data at {d}")
                continue
            for f in sorted(qr_dir.glob("*.json")):
                data = json.loads(f.read_text(encoding="utf-8"))
                qid = data.get("question_id", f.stem)
                dags[qid] = data
        all_dags[name] = dags
        print(f"  {name}: {len(dags)} DAGs")
    return all_dags


def embed_all_models(all_dags: dict[str, dict[str, dict]],
                     shared_qids: list[str]):
    """Ensure all node and edge embeddings are cached for all models."""
    api_key = _get_api_key()
    if not api_key:
        raise ValueError("No OPENROUTER_API_KEY found")

    node_texts = {}
    edge_texts = {}
    for model_name, dags in all_dags.items():
        for qid in shared_qids:
            qdata = dags[qid]
            for n in qdata.get("nodes", []):
                key = f"node|{qid}|{model_name}|{n['id']}"
                desc = n.get("description", n["id"])
                node_texts[key] = f"{n['id']}: {desc}"
            for e in qdata.get("edges", []):
                key = f"edge|{qid}|{model_name}|{e['from']}|{e['to']}"
                mechanism = e.get("mechanism", f"{e['from']} -> {e['to']}")
                edge_texts[key] = f"{e['from']} -> {e['to']}: {mechanism}"

    print(f"  Total node texts: {len(node_texts)}")
    print(f"  Total edge texts: {len(edge_texts)}")

    node_idx, node_mat = _ensure_embeddings(
        node_texts, NODE_EMB_CACHE, NODE_EMB_KEYS_CACHE, api_key)
    edge_idx, edge_mat = _ensure_embeddings(
        edge_texts, EDGE_EMB_CACHE, EDGE_EMB_KEYS_CACHE, api_key)

    return node_idx, node_mat, edge_idx, edge_mat


def compute_observed(all_dags: dict[str, dict[str, dict]],
                     shared_qids: list[str],
                     model_names: list[str],
                     node_idx, node_mat, edge_idx, edge_mat) -> dict:
    """Compute observed pairwise semantic metrics for all model pairs x questions."""
    pairs = list(itertools.combinations(model_names, 2))

    per_q_nj = []    # semantic node Jaccard
    per_q_mej = []   # mapped edge Jaccard
    per_q_dej = []   # direct edge Jaccard
    per_q_sd = []    # aligned spectral distance

    for qi, qid in enumerate(shared_qids):
        njs, mejs, dejs, sds = [], [], [], []
        for m1, m2 in pairs:
            d1 = all_dags[m1][qid]
            d2 = all_dags[m2][qid]
            nj, mej, dej, sd = _semantic_scores_for_pair(
                d1.get("nodes", []), d1.get("edges", []),
                d2.get("nodes", []), d2.get("edges", []),
                node_idx, node_mat, edge_idx, edge_mat,
                m1, m2, qid, qid)
            njs.append(nj)
            mejs.append(mej)
            dejs.append(dej)
            sds.append(sd)
        per_q_nj.append(np.mean(njs))
        per_q_mej.append(np.mean(mejs))
        per_q_dej.append(np.mean(dejs))
        per_q_sd.append(np.mean(sds))
        if (qi + 1) % 20 == 0:
            print(f"  Observed: {qi+1}/{len(shared_qids)} questions")

    return {
        "per_q_nj": np.array(per_q_nj),
        "per_q_mej": np.array(per_q_mej),
        "per_q_dej": np.array(per_q_dej),
        "per_q_sd": np.array(per_q_sd),
        "mean_nj": float(np.mean(per_q_nj)),
        "mean_mej": float(np.mean(per_q_mej)),
        "mean_dej": float(np.mean(per_q_dej)),
        "mean_sd": float(np.mean(per_q_sd)),
        "n_pairs": len(pairs),
    }


def run_permutation_test(all_dags: dict[str, dict[str, dict]],
                         shared_qids: list[str],
                         model_names: list[str],
                         node_idx, node_mat, edge_idx, edge_mat,
                         n_perm: int = 2000,
                         seed: int = 42) -> dict:
    """Permutation test: shuffle question assignments independently per model.

    Uses fewer permutations than raw GED (default 2000) since semantic
    matching is slower. Each permutation: for each model, randomly reassign
    which question's DAG goes in each slot, then recompute pairwise metrics.
    """
    rng = np.random.default_rng(seed)
    pairs = list(itertools.combinations(range(len(model_names)), 2))
    n_q = len(shared_qids)
    n_models = len(model_names)

    # Pre-extract nodes/edges indexed by (model_idx, question_idx)
    nodes_arr = []
    edges_arr = []
    for m in model_names:
        m_nodes = [all_dags[m][qid].get("nodes", []) for qid in shared_qids]
        m_edges = [all_dags[m][qid].get("edges", []) for qid in shared_qids]
        nodes_arr.append(m_nodes)
        edges_arr.append(m_edges)

    perm_nj = np.zeros(n_perm)
    perm_mej = np.zeros(n_perm)
    perm_dej = np.zeros(n_perm)
    perm_sd = np.zeros(n_perm)

    for p in range(n_perm):
        perm_indices = [rng.permutation(n_q) for _ in range(n_models)]

        njs, mejs, dejs, sds = [], [], [], []
        for q_slot in range(n_q):
            for mi, mj in pairs:
                qi = perm_indices[mi][q_slot]
                qj = perm_indices[mj][q_slot]
                nj, mej, dej, sd = _semantic_scores_for_pair(
                    nodes_arr[mi][qi], edges_arr[mi][qi],
                    nodes_arr[mj][qj], edges_arr[mj][qj],
                    node_idx, node_mat, edge_idx, edge_mat,
                    model_names[mi], model_names[mj],
                    shared_qids[qi], shared_qids[qj])
                njs.append(nj)
                mejs.append(mej)
                dejs.append(dej)
                sds.append(sd)
        perm_nj[p] = np.mean(njs)
        perm_mej[p] = np.mean(mejs)
        perm_dej[p] = np.mean(dejs)
        perm_sd[p] = np.mean(sds)

        if (p + 1) % 100 == 0:
            print(f"  Permutation {p+1}/{n_perm}")

    return {
        "perm_nj": perm_nj,
        "perm_mej": perm_mej,
        "perm_dej": perm_dej,
        "perm_sd": perm_sd,
    }


def plot_results(observed: dict, perm: dict, out_dir: Path):
    """Generate 1x2 figure: (a) permutation test summary, (b) per-question histogram."""
    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(11, 4),
                                      gridspec_kw={"wspace": 0.40})

    # ── Panel (a): Observed vs null for each metric ──
    metrics = [
        ("Sem. Node Jaccard", observed["mean_nj"], perm["perm_nj"], "upper"),
        ("Mapped Edge Jaccard", observed["mean_mej"], perm["perm_mej"], "upper"),
        ("Direct Edge Jaccard", observed["mean_dej"], perm["perm_dej"], "upper"),
        ("Aligned Spectral Dist.", observed["mean_sd"], perm["perm_sd"], "lower"),
    ]
    colors = ["#0072B2", "#E69F00", "#D55E00", "#009E73"]

    for i, (label, obs_val, null_dist, tail) in enumerate(metrics):
        null_mean = np.mean(null_dist)
        null_std = np.std(null_dist)

        if tail == "lower":
            p = np.mean(null_dist <= obs_val)
        else:
            p = np.mean(null_dist >= obs_val)
        stars = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "n.s."

        lo, hi = np.percentile(null_dist, [2.5, 97.5])
        ax_a.barh(i, null_mean, color=colors[i], alpha=0.25, height=0.5)
        ax_a.errorbar(null_mean, i, xerr=[[null_mean - lo], [hi - null_mean]],
                      color=colors[i], capsize=4, capthick=1.2, linewidth=1.2, fmt="none")
        ax_a.scatter(obs_val, i, marker="D", s=80, color=colors[i],
                     edgecolors="black", linewidths=0.5, zorder=5)

        # Stars annotation
        x_annot = max(obs_val, hi) + (ax_a.get_xlim()[1] - ax_a.get_xlim()[0]) * 0.01
        ax_a.text(x_annot, i, stars,
                  va="center", ha="left", fontsize=11, fontweight="bold", color=colors[i])

    ax_a.set_yticks(range(len(metrics)))
    ax_a.set_yticklabels([m[0] for m in metrics], fontsize=10)
    ax_a.set_xlabel("Metric Value")

    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker="D", color="gray", linestyle="none",
               markersize=7, label="Observed (same question)"),
        plt.Rectangle((0, 0), 1, 1, fc="gray", alpha=0.25, label="Null 95% CI"),
    ]
    ax_a.legend(handles=legend_elements, frameon=False, fontsize=9, loc="lower right")

    # Fix annotation positions after axes are set
    xleft, xright = ax_a.get_xlim()
    x_range = xright - xleft
    for i, (label, obs_val, null_dist, tail) in enumerate(metrics):
        lo, hi = np.percentile(null_dist, [2.5, 97.5])
        if tail == "lower":
            p = np.mean(null_dist <= obs_val)
        else:
            p = np.mean(null_dist >= obs_val)
        stars = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "n.s."
        # Remove old text and re-annotate with correct x position
        ax_a.texts.clear()
    for i, (label, obs_val, null_dist, tail) in enumerate(metrics):
        lo, hi = np.percentile(null_dist, [2.5, 97.5])
        if tail == "lower":
            p = np.mean(null_dist <= obs_val)
        else:
            p = np.mean(null_dist >= obs_val)
        stars = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "n.s."
        ax_a.text(max(obs_val, hi) + x_range * 0.02, i, stars,
                  va="center", ha="left", fontsize=11, fontweight="bold", color=colors[i])

    # ── Panel (b): Per-question semantic node Jaccard distribution ──
    ax_b.hist(observed["per_q_nj"], bins=20, color="#0072B2", alpha=0.7, edgecolor="white")
    ax_b.axvline(observed["mean_nj"], color="#D55E00", linewidth=2, linestyle="--",
                 label=f"Mean = {observed['mean_nj']:.3f}")
    null_mean_nj = np.mean(perm["perm_nj"])
    ax_b.axvline(null_mean_nj, color="#999", linewidth=1.5, linestyle=":",
                 label=f"Null mean = {null_mean_nj:.3f}")
    ax_b.set_xlabel("Mean Pairwise Sem. Node Jaccard (per question)")
    ax_b.set_ylabel("Number of Questions")
    ax_b.legend(frameon=False, fontsize=9)

    for ax, label in zip([ax_a, ax_b], ["(a)", "(b)"]):
        ax.text(-0.02, 1.05, label, transform=ax.transAxes,
                fontsize=14, fontweight="bold", va="bottom", ha="right")

    out_dir.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(out_dir / f"cross_model_ged.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved cross_model_ged.pdf/png to {out_dir}")


def main():
    print("=" * 60)
    print("Cross-Model DAG Convergence (Semantic Matching)")
    print("=" * 60)

    # Load DAGs
    print("\nLoading DAGs...")
    all_dags = load_all_model_dags()
    model_names = sorted(all_dags.keys())
    print(f"\n{len(model_names)} models loaded")

    # Find shared questions
    qid_sets = [set(dags.keys()) for dags in all_dags.values()]
    shared_qids = sorted(set.intersection(*qid_sets))
    print(f"{len(shared_qids)} shared questions across all models")

    if len(shared_qids) < 10:
        print("Too few shared questions. Exiting.")
        return

    # Embed all nodes and edges
    print("\nEnsuring embeddings for all models...")
    node_idx, node_mat, edge_idx, edge_mat = embed_all_models(all_dags, shared_qids)

    # Compute observed pairwise metrics
    n_pairs = len(list(itertools.combinations(model_names, 2)))
    print(f"\nComputing observed metrics ({n_pairs} model pairs x {len(shared_qids)} questions)...")
    observed = compute_observed(all_dags, shared_qids, model_names,
                                node_idx, node_mat, edge_idx, edge_mat)

    print(f"\nObserved (mean across all question x pair combinations):")
    print(f"  Sem. Node Jaccard:   {observed['mean_nj']:.4f}")
    print(f"  Mapped Edge Jaccard: {observed['mean_mej']:.4f}")
    print(f"  Direct Edge Jaccard: {observed['mean_dej']:.4f}")
    print(f"  Aligned Spectral:    {observed['mean_sd']:.4f}")

    # Permutation test
    n_perm = 2000
    print(f"\nRunning permutation test ({n_perm} iterations)...")
    perm = run_permutation_test(all_dags, shared_qids, model_names,
                                node_idx, node_mat, edge_idx, edge_mat,
                                n_perm=n_perm)

    # Results
    print(f"\n{'='*65}")
    print(f"CROSS-MODEL DAG CONVERGENCE ({len(model_names)} models, "
          f"{len(shared_qids)} questions, {n_pairs} pairs)")
    print(f"{'='*65}")
    print(f"{'Metric':<25} {'Observed':>10} {'Null Mean±SD':>18} {'p-value':>10}")
    print(f"{'-'*65}")

    results_summary = {}
    for label, obs_val, null_dist, tail in [
        ("Sem. Node Jaccard", observed["mean_nj"], perm["perm_nj"], "upper"),
        ("Mapped Edge Jaccard", observed["mean_mej"], perm["perm_mej"], "upper"),
        ("Direct Edge Jaccard", observed["mean_dej"], perm["perm_dej"], "upper"),
        ("Aligned Spectral", observed["mean_sd"], perm["perm_sd"], "lower"),
    ]:
        null_m = np.mean(null_dist)
        null_s = np.std(null_dist)
        if tail == "lower":
            p = np.mean(null_dist <= obs_val)
        else:
            p = np.mean(null_dist >= obs_val)
        stars = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
        print(f"  {label:<23} {obs_val:>10.4f} {null_m:>8.4f}±{null_s:<8.4f} {p:>8.4f} {stars}")
        results_summary[label] = {"observed": obs_val, "null_mean": null_m,
                                   "null_std": null_s, "p": p}

    # Generate figure
    print("\nGenerating figure...")
    plot_results(observed, perm, OUT)

    # Save results JSON
    results = {
        "n_models": len(model_names),
        "models": model_names,
        "n_questions": len(shared_qids),
        "n_pairs": n_pairs,
        "n_permutations": n_perm,
        "observed": {
            "mean_node_jaccard": observed["mean_nj"],
            "mean_mapped_edge_jaccard": observed["mean_mej"],
            "mean_direct_edge_jaccard": observed["mean_dej"],
            "mean_spectral_distance": observed["mean_sd"],
        },
        "summary": results_summary,
    }
    json_path = CAUSAL / "cross_model_ged_results.json"
    json_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Saved results JSON: {json_path}")


if __name__ == "__main__":
    main()
