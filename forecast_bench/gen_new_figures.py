"""Three new figures: cross-model agreement, shortest-path vs peripheral, asymmetry."""
import json, sys, csv
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

from forecast_bench.analysis_causal import load_causal_results, _spearman_correlation, _safe_mean
from forecast_bench.analysis_full import load_question_jsons
from forecast_bench.analyze_superforecasting_dag import normalized_ged, spectral_distance
from forecast_bench.semantic_graph_match import ensure_all_embeddings, compute_semantic_similarity

plt.rcParams.update({
    "font.family": "Arial",
    "font.size": 10,
    "figure.dpi": 300,
    "axes.spines.top": False,
    "axes.spines.right": False,
})

BLUE, ORANGE, VERMILLION, GREEN = "#0072B2", "#E69F00", "#D55E00", "#009E73"

BASE = Path(__file__).parent.parent
CAUSAL = BASE / "outputs" / "sensitivity" / "causal"
OUT = BASE / "paper" / "figures" / "internal"

MODEL_DIRS = {
    "Llama-3.1-8B":  CAUSAL / "llama_neutral",
    "Llama-3.3-70B": CAUSAL / "llama_70b_neutral",
    "DeepSeek-V3":   CAUSAL / "deepseek_neutral",
    "Qwen3-235B":    CAUSAL / "qwen_neutral",
    "Gemini-Flash-Lite": CAUSAL / "gemini_fl_neutral",
    "GPT-OSS-120B":  CAUSAL / "gpt_oss_neutral",
    "Qwen3-32B":     CAUSAL / "qwen_32b_neutral",
}
REDDISH_PURPLE = "#CC79A7"
WINE = "#882255"
MODEL_COLORS = {"Llama-3.1-8B": BLUE, "Llama-3.3-70B": ORANGE, "DeepSeek-V3": VERMILLION, "Qwen3-235B": GREEN, "Gemini-Flash-Lite": REDDISH_PURPLE, "GPT-OSS-120B": WINE, "Qwen3-32B": "#56B4E9"}


def jaccard(set_a, set_b):
    if not set_a and not set_b:
        return 1.0
    inter = len(set_a & set_b)
    union = len(set_a | set_b)
    return inter / union if union > 0 else 0.0


def main():
    # Load all data
    runs = {}
    for name, d in MODEL_DIRS.items():
        csv_path = d / "sensitivity_results.csv"
        if csv_path.exists():
            rows = load_causal_results(csv_path)
            q_data = load_question_jsons(d)
            runs[name] = (rows, q_data)
            print(f"Loaded {name}: {len(rows)} rows, {len(q_data)} questions")

    # ═══════════════════════════════════════════════════════════════════════
    # FIGURE 1: Cross-model graph agreement
    # ═══════════════════════════════════════════════════════════════════════

    model_names = sorted(runs.keys())
    pairs = []
    for i, m1 in enumerate(model_names):
        for m2 in model_names[i+1:]:
            _, qd1 = runs[m1]
            _, qd2 = runs[m2]
            shared = sorted(set(qd1.keys()) & set(qd2.keys()))

            node_jaccards, edge_jaccards, geds, spec_dists = [], [], [], []

            for qid in shared:
                nodes1 = {n["id"] for n in qd1[qid].get("nodes", [])}
                nodes2 = {n["id"] for n in qd2[qid].get("nodes", [])}
                edges1 = {(e["from"], e["to"]) for e in qd1[qid].get("edges", [])}
                edges2 = {(e["from"], e["to"]) for e in qd2[qid].get("edges", [])}

                node_jaccards.append(jaccard(nodes1, nodes2))
                edge_jaccards.append(jaccard(edges1, edges2))
                geds.append(normalized_ged(nodes1, edges1, nodes2, edges2))
                spec_dists.append(spectral_distance(edges1, nodes1, edges2, nodes2))

            # Permutation test: shuffle question pairings
            N_PERM = 5000
            rng = np.random.default_rng(42)
            nodes_list1 = [{n["id"] for n in qd1[qid].get("nodes", [])} for qid in shared]
            nodes_list2 = [{n["id"] for n in qd2[qid].get("nodes", [])} for qid in shared]
            edges_list1 = [{(e["from"], e["to"]) for e in qd1[qid].get("edges", [])} for qid in shared]
            edges_list2 = [{(e["from"], e["to"]) for e in qd2[qid].get("edges", [])} for qid in shared]
            n_sh = len(shared)

            perm_nj = np.zeros(N_PERM)
            perm_ej = np.zeros(N_PERM)
            perm_gd = np.zeros(N_PERM)
            perm_sd = np.zeros(N_PERM)
            for p in range(N_PERM):
                pidx = rng.permutation(n_sh)
                pnj, pej, pgd, psd = [], [], [], []
                for k in range(n_sh):
                    j = pidx[k]
                    pnj.append(jaccard(nodes_list1[k], nodes_list2[j]))
                    pej.append(jaccard(edges_list1[k], edges_list2[j]))
                    pgd.append(normalized_ged(nodes_list1[k], edges_list1[k],
                                              nodes_list2[j], edges_list2[j]))
                    psd.append(spectral_distance(edges_list1[k], nodes_list1[k],
                                                 edges_list2[j], nodes_list2[j]))
                perm_nj[p] = np.mean(pnj)
                perm_ej[p] = np.mean(pej)
                perm_gd[p] = np.mean(pgd)
                perm_sd[p] = np.mean(psd)

            obs = {
                "node_j": np.mean(node_jaccards), "edge_j": np.mean(edge_jaccards),
                "ged": np.mean(geds), "spectral": np.mean(spec_dists),
            }
            pvals = {
                "node_j": np.mean(perm_nj >= obs["node_j"]),
                "edge_j": np.mean(perm_ej >= obs["edge_j"]),
                "ged": np.mean(perm_gd <= obs["ged"]),
                "spectral": np.mean(perm_sd <= obs["spectral"]),
            }

            pairs.append({
                "pair": f"{m1}\nvs\n{m2}",
                "pair_short": f"{m1} vs {m2}",
                "n_shared": len(shared),
                "obs": obs, "pvals": pvals,
                "perm_nj": perm_nj, "perm_ej": perm_ej,
                "perm_gd": perm_gd, "perm_sd": perm_sd,
            })
            print(f"  {m1} vs {m2}: {len(shared)} shared, "
                  f"node J={obs['node_j']:.3f} (p={pvals['node_j']:.4f}), "
                  f"edge J={obs['edge_j']:.3f} (p={pvals['edge_j']:.4f}), "
                  f"GED={obs['ged']:.3f} (p={pvals['ged']:.4f}), "
                  f"spectral={obs['spectral']:.3f} (p={pvals['spectral']:.4f})")

    # ── Semantic matching ──
    print("\n  Computing semantic graph similarity...")
    try:
        node_idx, node_mat, edge_idx, edge_mat = ensure_all_embeddings(runs)
        has_semantic = True
    except (ValueError, Exception) as e:
        print(f"  Skipping semantic matching: {e}")
        has_semantic = False

    semantic_results = {}
    if has_semantic:
        for i, m1 in enumerate(model_names):
            for m2 in model_names[i+1:]:
                _, qd1 = runs[m1]
                _, qd2 = runs[m2]
                sem = compute_semantic_similarity(
                    qd1, qd2, m1, m2,
                    node_idx, node_mat, edge_idx, edge_mat,
                    threshold=0.7,
                )
                semantic_results[f"{m1} vs {m2}"] = sem
                print(f"  {m1} vs {m2}: semantic node J={sem['mean_node_jaccard']:.3f} (p={sem['pval_node_jaccard']:.4f}), "
                      f"mapped edge J={sem['mean_mapped_edge_jaccard']:.3f} (p={sem['pval_mapped_edge_jaccard']:.4f}), "
                      f"direct edge J={sem['mean_direct_edge_jaccard']:.3f} (p={sem['pval_direct_edge_jaccard']:.4f}), "
                      f"spectral={sem['mean_spectral_distance']:.3f} (p={sem['pval_spectral_distance']:.4f})")

    # ── LaTeX table instead of figure ──
    def _fmt_p(p):
        if p < 0.001:
            return "$<$0.001"
        return f"{p:.3f}"

    if has_semantic:
        tex_lines = [
            r"\begin{table}[ht]",
            r"\centering",
            r"\caption{Cross-model DAG agreement via semantic matching. Nodes and edges are aligned across models using embedding-based Hungarian matching (text-embedding-3-large, cosine $\geq 0.7$). Mapped-edge Jaccard re-identifies edges through aligned node pairs; direct-edge Jaccard matches edge descriptions independently. Spectral distance compares normalized Laplacian eigenvalues in the aligned node namespace. All $p$-values from permutation tests ($n=5{,}000$).}",
            r"\label{tab:cross_model_agreement}",
            r"\small",
            r"\begin{tabular}{lccccc}",
            r"\toprule",
            r"Model Pair & $n$ & Node ($p$) & Edge mapped ($p$) & Edge direct ($p$) & Spectral ($p$) \\",
            r"\midrule",
        ]

        for p in pairs:
            pair_label = p["pair_short"]
            n = p["n_shared"]
            sem = semantic_results.get(pair_label, {})
            snj = sem.get("mean_node_jaccard", 0)
            smej = sem.get("mean_mapped_edge_jaccard", 0)
            sdej = sem.get("mean_direct_edge_jaccard", 0)
            ssd = sem.get("mean_spectral_distance", 0)
            psnj = sem.get("pval_node_jaccard", 1)
            psmej = sem.get("pval_mapped_edge_jaccard", 1)
            psdej = sem.get("pval_direct_edge_jaccard", 1)
            pssd = sem.get("pval_spectral_distance", 1)
            tex_lines.append(
                f"{pair_label} & {n} & "
                f"{snj:.3f} ({_fmt_p(psnj)}) & {smej:.3f} ({_fmt_p(psmej)}) & "
                f"{sdej:.3f} ({_fmt_p(psdej)}) & {ssd:.3f} ({_fmt_p(pssd)}) \\\\"
            )
    else:
        tex_lines = [
            r"\begin{table}[ht]",
            r"\centering",
            r"\caption{Cross-model DAG agreement. Observed metric values with permutation-test $p$-values ($n=5{,}000$ permutations). Node and edge Jaccard test whether same-question DAGs share more labels/connections than chance; spectral distance tests topological similarity.}",
            r"\label{tab:cross_model_agreement}",
            r"\small",
            r"\begin{tabular}{lcccc}",
            r"\toprule",
            r"Model Pair & $n$ & Node Jaccard ($p$) & Edge Jaccard ($p$) & Spectral Dist.\ ($p$) \\",
            r"\midrule",
        ]

        for p in pairs:
            pair_label = p["pair_short"]
            n = p["n_shared"]
            nj = p["obs"]["node_j"]
            ej = p["obs"]["edge_j"]
            sd = p["obs"]["spectral"]
            pnj = p["pvals"]["node_j"]
            pej = p["pvals"]["edge_j"]
            psd = p["pvals"]["spectral"]
            tex_lines.append(
                f"{pair_label} & {n} & {nj:.3f} ({_fmt_p(pnj)}) & "
                f"{ej:.3f} ({_fmt_p(pej)}) & {sd:.3f} ({_fmt_p(psd)}) \\\\"
            )

    tex_lines += [
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ]

    tex_path = BASE / "paper" / "tables" / "cross_model_agreement.tex"
    tex_path.parent.mkdir(parents=True, exist_ok=True)
    tex_path.write_text("\n".join(tex_lines), encoding="utf-8")
    print(f"Saved {tex_path}")

    # Clean up old figure files
    for ext in ["png", "pdf"]:
        old = OUT / "supplementary" / f"cross_model_agreement.{ext}"
        if old.exists():
            old.unlink()
            print(f"  Removed old {old.name}")

    # ═══════════════════════════════════════════════════════════════════════
    # FIGURE 2: Shortest-path vs peripheral edges
    # ═══════════════════════════════════════════════════════════════════════

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    fig.patch.set_facecolor("white")

    # (a) Shortest-path vs peripheral mean shift per model
    x = np.arange(len(runs))
    w = 0.35
    on_means, off_means = [], []
    on_sems, off_sems = [], []

    for name, (rows, q_data) in runs.items():
        successful = [r for r in rows
                      if r.get("success") and r.get("absolute_shift") is not None]
        on = [r["absolute_shift"] for r in successful if r.get("target_on_critical_path")]
        off = [r["absolute_shift"] for r in successful if not r.get("target_on_critical_path")]
        on_means.append(np.mean(on) if on else 0)
        off_means.append(np.mean(off) if off else 0)
        on_sems.append(np.std(on)/np.sqrt(len(on)) if len(on) > 1 else 0)
        off_sems.append(np.std(off)/np.sqrt(len(off)) if len(off) > 1 else 0)
        print(f"  {name}: on_path n={len(on)} mean={np.mean(on):.3f}, "
              f"off_path n={len(off)} mean={np.mean(off):.3f}")

    ax1.bar(x - w/2, on_means, w, yerr=on_sems, color=VERMILLION, alpha=0.7,
            label="Shortest path", capsize=4)
    ax1.bar(x + w/2, off_means, w, yerr=off_sems, color="#AAAAAA", alpha=0.7,
            label="Peripheral", capsize=4)
    ax1.set_xticks(x)
    ax1.set_xticklabels(list(runs.keys()), fontsize=9)
    ax1.set_ylabel("Mean |Probability Shift|")
    ax1.legend(fontsize=9, frameon=False)
    ax1.text(-0.08, 1.05, "(a)", transform=ax1.transAxes, fontsize=14, fontweight="bold")

    # (b) By specific edge probe type
    edge_types = ["edge_negate_critical", "edge_negate_peripheral", "edge_reverse", "edge_spurious"]
    edge_labels = ["Negate\nShortest-Path", "Negate\nPeripheral", "Reverse\nEdge", "Spurious\nEdge"]

    x2 = np.arange(len(edge_types))
    n_models = len(runs)
    bar_w = 0.8 / n_models

    for i, (name, (rows, q_data)) in enumerate(runs.items()):
        successful = [r for r in rows
                      if r.get("success") and r.get("absolute_shift") is not None]
        means = []
        sems = []
        for et in edge_types:
            vals = [r["absolute_shift"] for r in successful if r.get("probe_type") == et]
            means.append(np.mean(vals) if vals else 0)
            sems.append(np.std(vals)/np.sqrt(len(vals)) if len(vals) > 1 else 0)

        offset = (i - (n_models - 1) / 2) * bar_w
        ax2.bar(x2 + offset, means, bar_w, yerr=sems,
                color=MODEL_COLORS[name], alpha=0.7, label=name, capsize=3)

    ax2.set_xticks(x2)
    ax2.set_xticklabels(edge_labels, fontsize=8)
    ax2.set_ylabel("Mean |Probability Shift|")
    ax2.legend(fontsize=8, frameon=False)
    ax2.text(-0.08, 1.05, "(b)", transform=ax2.transAxes, fontsize=14, fontweight="bold")

    plt.tight_layout()
    for ext in ["png", "pdf"]:
        fig.savefig(str(OUT / f"shortest_path_premium.{ext}"),
                    dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("Saved shortest_path_premium")

    # ═══════════════════════════════════════════════════════════════════════
    # FIGURE 3: Asymmetry — negate vs strengthen
    # ═══════════════════════════════════════════════════════════════════════
    from scipy import stats as sp_stats

    fig, ax = plt.subplots(figsize=(7, 5))
    fig.patch.set_facecolor("white")

    x = np.arange(len(runs))
    w = 0.35
    neg_means, str_means = [], []
    neg_sems, str_sems = [], []
    p_values = []

    for name, (rows, q_data) in runs.items():
        successful = [r for r in rows
                      if r.get("success") and r.get("absolute_shift") is not None]
        neg = [r["absolute_shift"] for r in successful
               if r.get("probe_type") == "node_negate_high"]
        stren = [r["absolute_shift"] for r in successful
                 if r.get("probe_type") == "node_strengthen"]
        neg_means.append(np.mean(neg) if neg else 0)
        str_means.append(np.mean(stren) if stren else 0)
        neg_sems.append(np.std(neg)/np.sqrt(len(neg)) if len(neg) > 1 else 0)
        str_sems.append(np.std(stren)/np.sqrt(len(stren)) if len(stren) > 1 else 0)
        # Two-sample Mann-Whitney U test
        if len(neg) > 1 and len(stren) > 1:
            _, p = sp_stats.mannwhitneyu(neg, stren, alternative="two-sided")
        else:
            p = 1.0
        p_values.append(p)
        print(f"  {name}: negate n={len(neg)} mean={np.mean(neg):.3f}, "
              f"strengthen n={len(stren)} mean={np.mean(stren):.3f}, p={p:.4f}")

    ax.bar(x - w/2, neg_means, w, yerr=neg_sems, color=VERMILLION, alpha=0.7,
           label="Negate (high-importance)", capsize=4)
    ax.bar(x + w/2, str_means, w, yerr=str_sems, color=GREEN, alpha=0.7,
           label="Strengthen (high-importance)", capsize=4)
    ax.set_xticks(x)
    ax.set_xticklabels(list(runs.keys()), fontsize=9)
    ax.set_ylabel("Mean |Probability Shift|")
    ax.legend(fontsize=9, frameon=False)

    # Significance brackets
    for i, p in enumerate(p_values):
        if p < 0.001:
            star = "***"
        elif p < 0.01:
            star = "**"
        elif p < 0.05:
            star = "*"
        else:
            star = "n.s."
        y_top = max(neg_means[i] + neg_sems[i], str_means[i] + str_sems[i]) + 0.008
        ax.plot([i - w/2, i - w/2, i + w/2, i + w/2],
                [y_top, y_top + 0.004, y_top + 0.004, y_top],
                color="black", linewidth=1.0)
        ax.text(i, y_top + 0.005, star, ha="center", va="bottom",
                fontsize=10, fontweight="bold")

    # Add padding so stars aren't clipped
    ylo, yhi = ax.get_ylim()
    ax.set_ylim(ylo, yhi + 0.02)

    plt.tight_layout()
    for ext in ["png", "pdf"]:
        fig.savefig(str(OUT / f"asymmetry_negate_vs_strengthen.{ext}"),
                    dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("Saved asymmetry_negate_vs_strengthen")

    print("\nDone - all three figures saved!")


if __name__ == "__main__":
    main()
