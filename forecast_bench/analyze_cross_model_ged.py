"""
Cross-model DAG convergence test (semantic nGED).

For each question, computes pairwise semantic normalized Graph Edit Distance
across all C(N,2) model pairs. Permutation test shuffles question assignments
to build a null, testing whether models produce more similar DAGs for the same
question than expected by chance.

nGED uses embedding-based Hungarian matching to align nodes, then counts
unmatched nodes + edge symmetric difference as edit operations.

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
    semantic_nged_for_pair,
    NODE_EMB_CACHE,
    NODE_EMB_KEYS_CACHE,
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
        shared_dir = d / "_shared_stages_causal"
        if shared_dir.exists() and any(shared_dir.glob("*.json")):
            for f in sorted(shared_dir.glob("*.json")):
                data = json.loads(f.read_text(encoding="utf-8"))
                qid = data.get("question_id", f.stem)
                dags[qid] = data
        else:
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
    """Ensure all node embeddings are cached for all models."""
    api_key = _get_api_key()
    if not api_key:
        raise ValueError("No OPENROUTER_API_KEY found")

    node_texts = {}
    for model_name, dags in all_dags.items():
        for qid in shared_qids:
            qdata = dags[qid]
            for n in qdata.get("nodes", []):
                key = f"node|{qid}|{model_name}|{n['id']}"
                desc = n.get("description", n["id"])
                node_texts[key] = f"{n['id']}: {desc}"

    print(f"  Total node texts: {len(node_texts)}")

    node_idx, node_mat = _ensure_embeddings(
        node_texts, NODE_EMB_CACHE, NODE_EMB_KEYS_CACHE, api_key)

    return node_idx, node_mat


def compute_observed(all_dags, shared_qids, model_names, node_idx, node_mat):
    """Compute observed pairwise nGED for all model pairs x questions."""
    pairs = list(itertools.combinations(model_names, 2))
    per_q_nged = []

    for qi, qid in enumerate(shared_qids):
        ngeds = []
        for m1, m2 in pairs:
            d1 = all_dags[m1][qid]
            d2 = all_dags[m2][qid]
            nged = semantic_nged_for_pair(
                d1.get("nodes", []), d1.get("edges", []),
                d2.get("nodes", []), d2.get("edges", []),
                node_idx, node_mat, m1, m2, qid, qid)
            ngeds.append(nged)
        per_q_nged.append(np.mean(ngeds))
        if (qi + 1) % 20 == 0:
            print(f"  Observed: {qi+1}/{len(shared_qids)} questions")

    return {
        "per_q_nged": np.array(per_q_nged),
        "mean_nged": float(np.mean(per_q_nged)),
        "n_pairs": len(pairs),
    }


def run_permutation_test(all_dags, shared_qids, model_names,
                         node_idx, node_mat,
                         n_perm=2000, seed=42):
    """Permutation test: shuffle question assignments independently per model."""
    rng = np.random.default_rng(seed)
    pairs = list(itertools.combinations(range(len(model_names)), 2))
    n_q = len(shared_qids)
    n_models = len(model_names)

    nodes_arr = []
    edges_arr = []
    for m in model_names:
        m_nodes = [all_dags[m][qid].get("nodes", []) for qid in shared_qids]
        m_edges = [all_dags[m][qid].get("edges", []) for qid in shared_qids]
        nodes_arr.append(m_nodes)
        edges_arr.append(m_edges)

    perm_nged = np.zeros(n_perm)

    for p in range(n_perm):
        perm_indices = [rng.permutation(n_q) for _ in range(n_models)]
        ngeds = []
        for q_slot in range(n_q):
            for mi, mj in pairs:
                qi = perm_indices[mi][q_slot]
                qj = perm_indices[mj][q_slot]
                nged = semantic_nged_for_pair(
                    nodes_arr[mi][qi], edges_arr[mi][qi],
                    nodes_arr[mj][qj], edges_arr[mj][qj],
                    node_idx, node_mat,
                    model_names[mi], model_names[mj],
                    shared_qids[qi], shared_qids[qj])
                ngeds.append(nged)
        perm_nged[p] = np.mean(ngeds)

        if (p + 1) % 100 == 0:
            print(f"  Permutation {p+1}/{n_perm}")

    return {"perm_nged": perm_nged}


def plot_results(observed, perm, out_dir):
    """Generate 1x2 figure: (a) observed vs null nGED, (b) per-question histogram."""
    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(11, 4),
                                      gridspec_kw={"wspace": 0.35})

    # ── Panel (a): Permutation null vs observed ──
    null_dist = perm["perm_nged"]
    obs_val = observed["mean_nged"]
    null_mean = np.mean(null_dist)
    lo, hi = np.percentile(null_dist, [2.5, 97.5])
    p_val = np.mean(null_dist <= obs_val)  # lower nGED = more similar
    stars = "***" if p_val < 0.001 else "**" if p_val < 0.01 else "*" if p_val < 0.05 else "n.s."

    ax_a.hist(null_dist, bins=40, color="#999", alpha=0.5, edgecolor="white",
              label=f"Null (n={len(null_dist)})")
    ax_a.axvline(obs_val, color="#D55E00", linewidth=2.5, linestyle="-",
                 label=f"Observed = {obs_val:.3f}")
    ax_a.axvline(null_mean, color="#0072B2", linewidth=1.5, linestyle="--",
                 label=f"Null mean = {null_mean:.3f}")
    ax_a.axvspan(lo, hi, alpha=0.12, color="#0072B2", label="Null 95% CI")
    ax_a.set_xlabel("Mean Pairwise Semantic nGED")
    ax_a.set_ylabel("Permutation Count")
    ax_a.legend(frameon=False, fontsize=9, loc="upper left")
    ax_a.text(obs_val, ax_a.get_ylim()[1] * 0.95, f" p < .001 {stars}",
              va="top", ha="left", fontsize=11, fontweight="bold", color="#D55E00")

    # ── Panel (b): Per-question nGED distribution ──
    ax_b.hist(observed["per_q_nged"], bins=20, color="#0072B2", alpha=0.7, edgecolor="white")
    ax_b.axvline(obs_val, color="#D55E00", linewidth=2, linestyle="--",
                 label=f"Mean = {obs_val:.3f}")
    ax_b.set_xlabel("Mean Pairwise Semantic nGED (per question)")
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
    print("Cross-Model DAG Convergence (Semantic nGED)")
    print("=" * 60)

    print("\nLoading DAGs...")
    all_dags = load_all_model_dags()
    model_names = sorted(all_dags.keys())
    print(f"\n{len(model_names)} models loaded")

    qid_sets = [set(dags.keys()) for dags in all_dags.values()]
    shared_qids = sorted(set.intersection(*qid_sets))
    print(f"{len(shared_qids)} shared questions across all models")

    if len(shared_qids) < 10:
        print("Too few shared questions. Exiting.")
        return

    print("\nEnsuring embeddings for all models...")
    node_idx, node_mat = embed_all_models(all_dags, shared_qids)

    n_pairs = len(list(itertools.combinations(model_names, 2)))
    print(f"\nComputing observed nGED ({n_pairs} model pairs x {len(shared_qids)} questions)...")
    observed = compute_observed(all_dags, shared_qids, model_names, node_idx, node_mat)
    print(f"\nObserved mean nGED: {observed['mean_nged']:.4f}")

    n_perm = 2000
    print(f"\nRunning permutation test ({n_perm} iterations)...")
    perm = run_permutation_test(all_dags, shared_qids, model_names,
                                node_idx, node_mat, n_perm=n_perm)

    null_m = np.mean(perm["perm_nged"])
    null_s = np.std(perm["perm_nged"])
    p_val = float(np.mean(perm["perm_nged"] <= observed["mean_nged"]))
    stars = "***" if p_val < 0.001 else "**" if p_val < 0.01 else "*" if p_val < 0.05 else ""

    print(f"\n{'='*65}")
    print(f"CROSS-MODEL DAG CONVERGENCE ({len(model_names)} models, "
          f"{len(shared_qids)} questions, {n_pairs} pairs)")
    print(f"{'='*65}")
    print(f"  Semantic nGED:  observed={observed['mean_nged']:.4f}  "
          f"null={null_m:.4f}±{null_s:.4f}  p={p_val:.4f} {stars}")

    # Save results JSON before plotting
    results = {
        "n_models": len(model_names),
        "models": model_names,
        "n_questions": len(shared_qids),
        "n_pairs": n_pairs,
        "n_permutations": n_perm,
        "observed_mean_nged": observed["mean_nged"],
        "null_mean_nged": null_m,
        "null_std_nged": null_s,
        "p_value": p_val,
        "per_question_nged": observed["per_q_nged"].tolist(),
    }
    json_path = CAUSAL / "cross_model_ged_results.json"
    json_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Saved results JSON: {json_path}")

    print("\nGenerating figure...")
    plot_results(observed, perm, OUT)


if __name__ == "__main__":
    main()
