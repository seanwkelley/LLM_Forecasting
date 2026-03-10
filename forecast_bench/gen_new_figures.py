"""Three new figures: cross-model agreement, critical vs peripheral, asymmetry."""
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

plt.rcParams.update({"font.family": "Arial", "font.size": 10, "figure.dpi": 300})

BLUE, ORANGE, VERMILLION, GREEN = "#0072B2", "#E69F00", "#D55E00", "#009E73"

BASE = Path(__file__).parent.parent
CAUSAL = BASE / "outputs" / "sensitivity" / "causal"
OUT = BASE / "paper" / "figures"

MODEL_DIRS = {
    "Llama-3.1-8B":  CAUSAL / "llama_one_turn",
    "Llama-3.3-70B": CAUSAL / "70b_one_turn",
    "DeepSeek-V3":   CAUSAL / "deepseek_one_turn",
    "Qwen3-235B":    CAUSAL / "qwen_one_turn",
}
MODEL_COLORS = {"Llama-3.1-8B": BLUE, "Llama-3.3-70B": ORANGE, "DeepSeek-V3": VERMILLION, "Qwen3-235B": GREEN}


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

    # 2×2 grid: one panel per metric, each with 3 horizontal boxplots + observed markers
    metric_keys = [
        ("node_j", "perm_nj", "Node Jaccard\n(higher = more similar)", BLUE),
        ("edge_j", "perm_ej", "Edge Jaccard\n(higher = more similar)", ORANGE),
        ("spectral", "perm_sd", "Spectral Distance\n(higher = more different)", GREEN),
    ]
    pair_labels = [p["pair_short"] for p in pairs]

    fig, axes = plt.subplots(1, 3, figsize=(16, max(5, len(pairs) * 1.2 + 1)))
    fig.patch.set_facecolor("white")
    panel_labels = ["(a)", "(b)", "(c)"]

    for idx, (obs_key, perm_key, metric_label, color) in enumerate(metric_keys):
        ax = axes.flat[idx]
        null_dists = [p[perm_key] for p in pairs]
        obs_vals = [p["obs"][obs_key] for p in pairs]
        p_vals = [p["pvals"][obs_key] for p in pairs]

        positions = list(range(len(pairs)))
        # Half-violin (upper half only)
        for j, dist in enumerate(null_dists):
            from scipy.stats import gaussian_kde
            kde = gaussian_kde(dist)
            x_range = np.linspace(dist.min(), dist.max(), 200)
            density = kde(x_range)
            density = density / density.max() * 0.4  # scale to fit
            ax.hlines(j, dist.min(), dist.max(), color="black",
                      linewidth=0.8, zorder=1)
            ax.fill_between(x_range, j - density, j, alpha=0.5, color=color,
                            edgecolor=color, linewidth=0.5)

        for j, obs_val in enumerate(obs_vals):
            ax.scatter([obs_val], [j], color=color, s=100, zorder=5,
                       edgecolors="black", linewidths=1.5, marker="D")

        ax.set_yticks(positions)
        ax.set_yticklabels(pair_labels, fontsize=8)
        ax.set_xlabel(metric_label, fontsize=9)
        ax.tick_params(axis="x", labelsize=8)
        ax.xaxis.set_major_locator(plt.MaxNLocator(5))
        ax.invert_yaxis()
        ax.text(-0.12, 1.05, panel_labels[idx], transform=ax.transAxes,
                fontsize=14, fontweight="bold")

    plt.tight_layout()
    for ext in ["png", "pdf"]:
        fig.savefig(str(OUT / "supplementary" / f"cross_model_agreement.{ext}"),
                    dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("Saved cross_model_agreement")

    # ═══════════════════════════════════════════════════════════════════════
    # FIGURE 2: Critical path vs peripheral edges
    # ═══════════════════════════════════════════════════════════════════════

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    fig.patch.set_facecolor("white")

    # (a) Critical vs peripheral mean shift per model
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
            label="Critical path", capsize=4)
    ax1.bar(x + w/2, off_means, w, yerr=off_sems, color="#AAAAAA", alpha=0.7,
            label="Peripheral", capsize=4)
    ax1.set_xticks(x)
    ax1.set_xticklabels(list(runs.keys()), fontsize=9)
    ax1.set_ylabel("Mean |Probability Shift|")
    ax1.legend(fontsize=9, frameon=False)
    ax1.text(-0.08, 1.05, "(a)", transform=ax1.transAxes, fontsize=14, fontweight="bold")

    # (b) By specific edge probe type
    edge_types = ["edge_negate_critical", "edge_negate_peripheral", "edge_reverse", "edge_spurious"]
    edge_labels = ["Negate\nCritical", "Negate\nPeripheral", "Reverse\nEdge", "Spurious\nEdge"]

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
        fig.savefig(str(OUT / f"critical_path_premium.{ext}"),
                    dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("Saved critical_path_premium")

    # ═══════════════════════════════════════════════════════════════════════
    # FIGURE 3: Asymmetry — negate vs strengthen
    # ═══════════════════════════════════════════════════════════════════════

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    fig.patch.set_facecolor("white")

    # (a) Paired bar: negate_high vs strengthen per model
    x = np.arange(len(runs))
    w = 0.35
    neg_means, str_means = [], []
    neg_sems, str_sems = [], []

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
        print(f"  {name}: negate n={len(neg)} mean={np.mean(neg):.3f}, "
              f"strengthen n={len(stren)} mean={np.mean(stren):.3f}")

    ax1.bar(x - w/2, neg_means, w, yerr=neg_sems, color=VERMILLION, alpha=0.7,
            label="Negate (high-importance)", capsize=4)
    ax1.bar(x + w/2, str_means, w, yerr=str_sems, color=GREEN, alpha=0.7,
            label="Strengthen (high-importance)", capsize=4)
    ax1.set_xticks(x)
    ax1.set_xticklabels(list(runs.keys()), fontsize=9)
    ax1.set_ylabel("Mean |Probability Shift|")
    ax1.legend(fontsize=8, frameon=False)
    ax1.text(-0.08, 1.05, "(a)", transform=ax1.transAxes, fontsize=14, fontweight="bold")

    # (b) Scatter: per-question negate vs strengthen
    for name, (rows, q_data) in runs.items():
        successful = [r for r in rows
                      if r.get("success") and r.get("absolute_shift") is not None]
        by_q = defaultdict(lambda: {"neg": [], "str": []})
        for r in successful:
            if r.get("probe_type") == "node_negate_high":
                by_q[r["question_id"]]["neg"].append(r["absolute_shift"])
            elif r.get("probe_type") == "node_strengthen":
                by_q[r["question_id"]]["str"].append(r["absolute_shift"])

        neg_q, str_q = [], []
        for qid, vals in by_q.items():
            if vals["neg"] and vals["str"]:
                neg_q.append(np.mean(vals["neg"]))
                str_q.append(np.mean(vals["str"]))

        ax2.scatter(str_q, neg_q, color=MODEL_COLORS[name], alpha=0.5, s=30, label=name)

    # Identity line
    lim = max(ax2.get_xlim()[1], ax2.get_ylim()[1])
    ax2.plot([0, lim], [0, lim], "k--", alpha=0.3, linewidth=1)
    ax2.set_xlabel("Mean |Shift| \u2014 Strengthen Probes")
    ax2.set_ylabel("Mean |Shift| \u2014 Negate Probes")
    ax2.legend(fontsize=8, frameon=False)
    ax2.set_aspect("equal")
    ax2.text(-0.08, 1.05, "(b)", transform=ax2.transAxes, fontsize=14, fontweight="bold")

    plt.tight_layout()
    for ext in ["png", "pdf"]:
        fig.savefig(str(OUT / f"asymmetry_negate_vs_strengthen.{ext}"),
                    dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("Saved asymmetry_negate_vs_strengthen")

    print("\nDone - all three figures saved!")


if __name__ == "__main__":
    main()
