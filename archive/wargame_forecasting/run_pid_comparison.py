"""
PID Comparison: Pre-v3.10 vs v3.10 Domain Differentiation

Runs PID analysis on both the original (pre-v3.10) and new (v3.10) datasets,
then produces a side-by-side comparison of emergence metrics.

Usage:
    python forecasting/run_pid_comparison.py [--n-permutations 200]

Requires both datasets to exist:
    - outputs/multiscenario/       (original, pre-v3.10)
    - outputs/multiscenario_v310/  (new, v3.10 domain differentiation)
"""

import os
import sys
import json
import argparse
import numpy as np
import pandas as pd
import warnings
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
warnings.filterwarnings("ignore", message="Sample space has more than")

from pid_data_extraction import (
    extract_agent_escalation_matrix,
    pivot_to_pid_matrix,
    print_escalation_distribution,
    print_collapse_distribution,
)
from pid_analysis import (
    compute_pairwise_pid,
    emergence_capacity,
    permutation_test,
    summarize_pid,
    pairwise_results_to_df,
)


def analyze_action_diversity(raw_df, label):
    """Print action diversity statistics for a dataset."""
    print(f"\n{'='*50}")
    print(f"Action Diversity: {label}")
    print(f"{'='*50}")

    primary = raw_df[raw_df["priority"] == "primary"]
    for faction in ["Novaris", "Tethys"]:
        print(f"\n  {faction}:")
        faction_df = primary[primary["faction_name"] == faction]
        for role in sorted(faction_df["agent_role"].unique()):
            role_df = faction_df[faction_df["agent_role"] == role]
            n_unique = role_df["proposed_action"].nunique()
            top_action = role_df["proposed_action"].value_counts().index[0]
            top_pct = role_df["proposed_action"].value_counts().values[0] / len(role_df) * 100
            print(f"    {role:12s}: {n_unique} unique actions, "
                  f"top={top_action} ({top_pct:.0f}%)")

    # Escalation value diversity per agent
    print(f"\n  Escalation levels per agent:")
    for faction in ["Novaris", "Tethys"]:
        faction_df = primary[primary["faction_name"] == faction]
        for role in sorted(faction_df["agent_role"].unique()):
            role_df = faction_df[faction_df["agent_role"] == role]
            vals = sorted(role_df["proposed_escalation"].dropna().unique())
            print(f"    {faction:8s} {role:12s}: {len(vals)} levels: {vals}")


def run_analysis(data_dir, label, n_permutations=200, seed=42):
    """Run PID analysis on a single dataset."""
    print(f"\n{'#'*70}")
    print(f"# ANALYZING: {label}")
    print(f"# Data: {data_dir}")
    print(f"{'#'*70}")

    raw_df = extract_agent_escalation_matrix(data_dir)
    n_scenarios = raw_df["scenario_id"].nunique()
    print(f"\nExtracted {len(raw_df)} rows from {n_scenarios} scenarios")

    if n_scenarios < 10:
        print(f"WARNING: Only {n_scenarios} scenarios — insufficient for PID analysis")
        return None

    print_escalation_distribution(raw_df)
    analyze_action_diversity(raw_df, label)

    results = {}
    for faction in ["Novaris", "Tethys"]:
        matrix, meta = pivot_to_pid_matrix(raw_df, faction)
        agent_cols = meta["agent_cols"]
        print(f"\n--- {faction} ({meta['n_scenarios']} scenarios, "
              f"agents={agent_cols}) ---")

        for col in agent_cols:
            vals = sorted(matrix[col].dropna().unique())
            print(f"  {col}: {len(vals)} escalation levels: {vals}")

        # Pairwise PID
        pairwise = compute_pairwise_pid(matrix, agent_cols, "Y")
        ec = emergence_capacity(pairwise)
        summarize_pid(pairwise, f"{label} - {faction}")

        # Permutation test (row_shuffle only for comparison)
        perm = None
        ec_p = np.nan
        if n_permutations > 0:
            print(f"\n  Running permutation test ({n_permutations} permutations)...")
            perm = permutation_test(
                matrix, agent_cols, "Y",
                n_permutations=n_permutations,
                surrogate_type="row_shuffle",
                seed=seed,
            )
            ec_p = perm["emergence_capacity_p"]
            print(f"  EC = {ec:.4f}, p = {ec_p:.3f}")

        pw_df = pairwise_results_to_df(pairwise).dropna(subset=["synergy"])
        results[faction] = {
            "pairwise": pairwise,
            "pairwise_df": pw_df,
            "emergence_capacity": ec,
            "ec_p_value": ec_p,
            "mean_synergy": pw_df["synergy"].mean() if len(pw_df) > 0 else np.nan,
            "mean_redundancy": pw_df["redundancy"].mean() if len(pw_df) > 0 else np.nan,
            "mean_mi": pw_df["mutual_info"].mean() if len(pw_df) > 0 else np.nan,
            "n_scenarios": meta["n_scenarios"],
            "n_agents": len(agent_cols),
            "agent_cols": agent_cols,
            "permutation": perm,
        }

    return results


def plot_comparison(old_results, new_results, output_dir):
    """Generate comparison plots."""
    os.makedirs(output_dir, exist_ok=True)

    for faction in ["Novaris", "Tethys"]:
        if faction not in old_results or faction not in new_results:
            continue

        old = old_results[faction]
        new = new_results[faction]

        # --- 1. Emergence capacity comparison ---
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))

        # EC bar chart
        ax = axes[0]
        labels = ["Pre-v3.10", "v3.10"]
        ecs = [old["emergence_capacity"], new["emergence_capacity"]]
        colors = ["#3498db", "#e74c3c"]
        bars = ax.bar(labels, ecs, color=colors, edgecolor="white", width=0.5)
        for bar, ec, p in zip(bars, ecs,
                              [old["ec_p_value"], new["ec_p_value"]]):
            p_str = f"p={p:.3f}" if not np.isnan(p) else ""
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.001,
                    f"{ec:.4f}\n{p_str}", ha="center", va="bottom", fontsize=9)
        ax.set_ylabel("Emergence Capacity (bits)")
        ax.set_title("Emergence Capacity")
        ax.set_ylim(bottom=0)

        # Mean MI / Synergy / Redundancy comparison
        ax = axes[1]
        metrics = ["mean_mi", "mean_synergy", "mean_redundancy"]
        metric_labels = ["Mean MI", "Mean Synergy", "Mean Redundancy"]
        x = np.arange(len(metrics))
        width = 0.35
        old_vals = [old[m] for m in metrics]
        new_vals = [new[m] for m in metrics]
        ax.bar(x - width/2, old_vals, width, label="Pre-v3.10",
               color="#3498db", edgecolor="white")
        ax.bar(x + width/2, new_vals, width, label="v3.10",
               color="#e74c3c", edgecolor="white")
        ax.set_xticks(x)
        ax.set_xticklabels(metric_labels, fontsize=9)
        ax.set_ylabel("Information (bits)")
        ax.set_title("PID Metrics")
        ax.legend()

        # Synergy proportion comparison
        ax = axes[2]
        components = ["synergy", "redundancy", "unique_i", "unique_j"]
        comp_labels = ["Synergy", "Redundancy", "Unique i", "Unique j"]
        colors_comp = ["#e74c3c", "#3498db", "#2ecc71", "#f39c12"]

        for idx, (label, res) in enumerate([("Pre-v3.10", old), ("v3.10", new)]):
            pw = res["pairwise_df"]
            if pw.empty:
                continue
            means = [pw[c].mean() for c in components]
            total = sum(means)
            if total > 0:
                props = [m / total for m in means]
            else:
                props = [0] * len(components)
            bottom = 0
            for comp, prop, color in zip(comp_labels, props, colors_comp):
                ax.bar(idx, prop, bottom=bottom, color=color,
                       label=comp if idx == 0 else "", edgecolor="white",
                       width=0.5)
                bottom += prop
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["Pre-v3.10", "v3.10"])
        ax.set_ylabel("Proportion")
        ax.set_title("PID Decomposition")
        ax.set_ylim(0, 1)
        ax.legend(fontsize=8)

        fig.suptitle(f"{faction} — Pre-v3.10 vs v3.10 Comparison", fontsize=14)
        plt.tight_layout()
        fname = f"{faction.lower()}_comparison.png"
        plt.savefig(os.path.join(output_dir, fname), dpi=150)
        plt.close()
        print(f"  Saved: {fname}")

        # --- 2. Pairwise synergy heatmap side-by-side ---
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        for ax, res, title in [(ax1, old, "Pre-v3.10"), (ax2, new, "v3.10")]:
            pw = res["pairwise_df"]
            if pw.empty:
                continue
            agents = sorted(set(pw["agent_i"]) | set(pw["agent_j"]))
            n = len(agents)
            matrix = np.full((n, n), np.nan)
            agent_idx = {a: i for i, a in enumerate(agents)}
            for _, row in pw.iterrows():
                i = agent_idx[row["agent_i"]]
                j = agent_idx[row["agent_j"]]
                matrix[i, j] = row["synergy"]
                matrix[j, i] = row["synergy"]
            np.fill_diagonal(matrix, 0)

            vmax = max(0.01, np.nanmax([
                old["pairwise_df"]["synergy"].max() if not old["pairwise_df"].empty else 0,
                new["pairwise_df"]["synergy"].max() if not new["pairwise_df"].empty else 0,
            ]))
            mask = np.eye(n, dtype=bool)
            sns.heatmap(matrix, annot=True, fmt=".4f", cmap="YlOrRd",
                        xticklabels=agents, yticklabels=agents,
                        mask=mask, ax=ax, vmin=0, vmax=vmax,
                        cbar_kws={"label": "synergy (bits)"},
                        linewidths=0.5)
            ax.set_title(f"{title} (EC={res['emergence_capacity']:.4f})")

        fig.suptitle(f"{faction} — Pairwise Synergy Comparison", fontsize=14)
        plt.tight_layout()
        fname = f"{faction.lower()}_synergy_comparison.png"
        plt.savefig(os.path.join(output_dir, fname), dpi=150)
        plt.close()
        print(f"  Saved: {fname}")


def main():
    parser = argparse.ArgumentParser(description="PID Comparison: Pre-v3.10 vs v3.10")
    parser.add_argument("--n-permutations", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    old_dir = os.path.join(project_root, "outputs", "multiscenario")
    new_dir = os.path.join(project_root, "outputs", "multiscenario_v310")
    output_dir = os.path.join(project_root, "experiment_results", "pid_comparison")

    print("=" * 70)
    print("PID EMERGENCE COMPARISON: Pre-v3.10 vs v3.10")
    print("=" * 70)

    # Check data availability
    for label, path in [("Pre-v3.10", old_dir), ("v3.10", new_dir)]:
        if not os.path.exists(path):
            print(f"\nERROR: {label} data not found at {path}")
            sys.exit(1)
        gt = os.path.join(path, "ground_truth.csv")
        if os.path.exists(gt):
            n = len(pd.read_csv(gt))
            print(f"  {label}: {n} scenarios in {path}")
        else:
            print(f"  {label}: ground_truth.csv not found in {path}")
            sys.exit(1)

    # Run analysis on both
    old_results = run_analysis(old_dir, "Pre-v3.10",
                               n_permutations=args.n_permutations, seed=args.seed)
    new_results = run_analysis(new_dir, "v3.10",
                               n_permutations=args.n_permutations, seed=args.seed)

    if old_results is None or new_results is None:
        print("\nCannot complete comparison — insufficient data")
        sys.exit(1)

    # Comparison summary
    print("\n" + "=" * 70)
    print("COMPARISON SUMMARY")
    print("=" * 70)

    summary = {}
    for faction in ["Novaris", "Tethys"]:
        if faction not in old_results or faction not in new_results:
            continue

        old = old_results[faction]
        new = new_results[faction]

        ec_change = new["emergence_capacity"] - old["emergence_capacity"]
        mi_change = new["mean_mi"] - old["mean_mi"]
        syn_change = new["mean_synergy"] - old["mean_synergy"]

        print(f"\n{faction}:")
        print(f"  {'Metric':<25s} {'Pre-v3.10':>12s} {'v3.10':>12s} {'Change':>12s}")
        print(f"  {'-'*61}")
        print(f"  {'Emergence Capacity':<25s} {old['emergence_capacity']:>12.4f} "
              f"{new['emergence_capacity']:>12.4f} {ec_change:>+12.4f}")
        print(f"  {'Mean MI':<25s} {old['mean_mi']:>12.4f} "
              f"{new['mean_mi']:>12.4f} {mi_change:>+12.4f}")
        print(f"  {'Mean Synergy':<25s} {old['mean_synergy']:>12.4f} "
              f"{new['mean_synergy']:>12.4f} {syn_change:>+12.4f}")
        print(f"  {'Mean Redundancy':<25s} {old['mean_redundancy']:>12.4f} "
              f"{new['mean_redundancy']:>12.4f} "
              f"{new['mean_redundancy'] - old['mean_redundancy']:>+12.4f}")
        print(f"  {'EC p-value':<25s} {old['ec_p_value']:>12.3f} "
              f"{new['ec_p_value']:>12.3f}")
        print(f"  {'N scenarios':<25s} {old['n_scenarios']:>12d} "
              f"{new['n_scenarios']:>12d}")

        summary[faction] = {
            "pre_v310": {
                "emergence_capacity": round(old["emergence_capacity"], 6),
                "ec_p_value": round(old["ec_p_value"], 4) if not np.isnan(old["ec_p_value"]) else None,
                "mean_mi": round(old["mean_mi"], 6),
                "mean_synergy": round(old["mean_synergy"], 6),
                "mean_redundancy": round(old["mean_redundancy"], 6),
                "n_scenarios": old["n_scenarios"],
            },
            "v310": {
                "emergence_capacity": round(new["emergence_capacity"], 6),
                "ec_p_value": round(new["ec_p_value"], 4) if not np.isnan(new["ec_p_value"]) else None,
                "mean_mi": round(new["mean_mi"], 6),
                "mean_synergy": round(new["mean_synergy"], 6),
                "mean_redundancy": round(new["mean_redundancy"], 6),
                "n_scenarios": new["n_scenarios"],
            },
            "change": {
                "emergence_capacity": round(ec_change, 6),
                "mean_mi": round(mi_change, 6),
                "mean_synergy": round(syn_change, 6),
            }
        }

    # Generate comparison plots
    print("\nGenerating comparison plots...")
    plot_comparison(old_results, new_results, os.path.join(output_dir, "plots"))

    # Save summary
    os.makedirs(output_dir, exist_ok=True)
    summary_path = os.path.join(output_dir, "comparison_summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSaved: {summary_path}")
    print(f"Results in: {output_dir}")


if __name__ == "__main__":
    main()
