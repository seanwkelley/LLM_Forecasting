"""
Temporal PID Analysis — Main Script

Analyzes multi-period simulation data for temporal emergence:
Do agents adapt to each other's actions over time?

Computes time-delayed PID: (agent_i_action_t, agent_j_action_t) → delta_state_{t→t+1}

Usage:
    python forecasting/run_temporal_pid_analysis.py [--data-dir outputs/multiperiod_pilot]
"""

import os
import sys
import json
import time
import argparse
import warnings
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from temporal_pid_analysis import (
    extract_temporal_data,
    build_temporal_pid_matrix,
    compute_temporal_pairwise_pid,
    compute_temporal_emergence_capacity,
    temporal_permutation_test,
    compute_action_adaptation,
    summarize_temporal_pid,
)
from pid_analysis import summarize_pid, pairwise_results_to_df
from pid_data_extraction import collapse_escalation_to_3_levels


def parse_args():
    parser = argparse.ArgumentParser(description="Temporal PID Analysis")
    parser.add_argument("--data-dir", type=str,
                        default="outputs/multiperiod_pilot")
    parser.add_argument("--output-dir", type=str,
                        default="experiment_results/temporal_pid_analysis")
    parser.add_argument("--n-permutations", type=int, default=500)
    parser.add_argument("--collapse-levels", type=int, default=3,
                        choices=[3, 5])
    parser.add_argument("--target", type=str, default="delta_crisis",
                        choices=["delta_crisis", "delta_collapse", "collapse_next"])
    parser.add_argument("--skip-permutation", action="store_true")
    return parser.parse_args()


def main():
    warnings.filterwarnings("ignore", message="Sample space has more than")
    args = parse_args()

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(project_root, args.data_dir) if not os.path.isabs(args.data_dir) else args.data_dir
    output_dir = os.path.join(project_root, args.output_dir) if not os.path.isabs(args.output_dir) else args.output_dir
    os.makedirs(output_dir, exist_ok=True)

    print("=" * 70)
    print("TEMPORAL PID ANALYSIS")
    print("Time-Delayed Partial Information Decomposition")
    print("=" * 70)
    print(f"\nData directory:     {data_dir}")
    print(f"Output directory:   {output_dir}")
    print(f"Target variable:    {args.target}")
    print(f"Escalation levels:  {args.collapse_levels}")
    print(f"N permutations:     {args.n_permutations}")

    t0 = time.time()

    # ==================================================================
    # PHASE 1: Data Extraction
    # ==================================================================
    print("\n" + "=" * 70)
    print("PHASE 1: Temporal Data Extraction")
    print("=" * 70)

    actions_df, gt_df = extract_temporal_data(data_dir)

    n_scenarios = actions_df["scenario_id"].nunique()
    n_periods = actions_df["period"].nunique()
    print(f"\nExtracted {len(actions_df)} rows from {n_scenarios} scenarios × {n_periods} periods")
    print(f"Factions: {sorted(actions_df['faction_name'].unique())}")
    print(f"Roles: {sorted(actions_df['agent_role'].unique())}")

    if gt_df is not None:
        print(f"Ground truth: {len(gt_df)} rows")
        print(f"  Collapse prob range: [{gt_df['collapse_probability'].min():.3f}, "
              f"{gt_df['collapse_probability'].max():.3f}]")
        if "crisis_level" in gt_df.columns:
            print(f"  Crisis level range: [{gt_df['crisis_level'].min():.1f}, "
                  f"{gt_df['crisis_level'].max():.1f}]")

    # Save raw extraction
    actions_df.to_csv(os.path.join(output_dir, "temporal_actions.csv"), index=False)

    # ==================================================================
    # PHASE 2: Action Adaptation Analysis
    # ==================================================================
    print("\n" + "=" * 70)
    print("PHASE 2: Action Adaptation Analysis")
    print("=" * 70)
    print("(Do agents change their actions across periods?)")

    for faction in ["Novaris", "Tethys"]:
        print(f"\n--- {faction} ---")
        adapt_df = compute_action_adaptation(actions_df, faction)

        if adapt_df.empty:
            print("  No data")
            continue

        # Summarize per agent role
        role_summary = adapt_df.groupby("agent_role").agg({
            "change_rate": "mean",
            "escalation_range": "mean",
            "n_unique_actions": "mean",
            "n_periods": "mean",
        }).round(3)

        for role, row in role_summary.iterrows():
            print(f"  {role:12s}: change_rate={row['change_rate']:.2f}, "
                  f"esc_range={row['escalation_range']:.1f}, "
                  f"unique_actions={row['n_unique_actions']:.1f}")

        adapt_df.to_csv(
            os.path.join(output_dir, f"{faction.lower()}_adaptation.csv"),
            index=False
        )

    # ==================================================================
    # PHASE 3: Temporal PID Computation
    # ==================================================================
    print("\n" + "=" * 70)
    print("PHASE 3: Temporal PID Computation")
    print("=" * 70)

    all_results = {}

    for faction in ["Novaris", "Tethys"]:
        print(f"\n--- {faction} ---")

        try:
            matrix, meta = build_temporal_pid_matrix(
                actions_df, gt_df, faction,
                use_final=False,
                target=args.target,
            )
        except ValueError as e:
            print(f"  Skipping: {e}")
            continue

        agent_cols = meta["agent_cols"]
        print(f"Temporal matrix: {meta['n_transitions']} transitions from "
              f"{meta['n_scenarios']} scenarios")
        print(f"Agent roles: {agent_cols}")
        print(f"Target: {meta['target_type']}")
        print(f"Y distribution: {dict(matrix['Y'].value_counts().sort_index())}")

        # Collapse escalation levels if requested
        if args.collapse_levels == 3:
            print("Collapsing escalation to 3 levels...")
            matrix = collapse_escalation_to_3_levels(matrix, agent_cols)

        # Save temporal PID matrix
        matrix.to_csv(
            os.path.join(output_dir, f"{faction.lower()}_temporal_matrix.csv"),
            index=False
        )

        # Pairwise PID
        n_pairs = len(agent_cols) * (len(agent_cols) - 1) // 2
        print(f"\nComputing temporal pairwise PID ({len(agent_cols)} agents, "
              f"{n_pairs} pairs)...")
        pairwise = compute_temporal_pairwise_pid(matrix, agent_cols, "Y")
        ec = compute_temporal_emergence_capacity(pairwise)
        summarize_temporal_pid(pairwise, faction)

        all_results[faction] = {
            "matrix": matrix,
            "metadata": meta,
            "pairwise_results": pairwise,
            "emergence_capacity": ec,
            "agent_cols": agent_cols,
        }

        # Save pairwise results
        pw_df = pairwise_results_to_df(pairwise)
        pw_df.to_csv(
            os.path.join(output_dir, f"{faction.lower()}_temporal_pairwise.csv"),
            index=False
        )

    # ==================================================================
    # PHASE 4: Permutation Tests
    # ==================================================================
    if not args.skip_permutation and all_results:
        print("\n" + "=" * 70)
        print("PHASE 4: Temporal Permutation Tests")
        print("=" * 70)

        for faction, data in all_results.items():
            print(f"\n--- {faction} ({args.n_permutations} permutations) ---")

            perm_results = temporal_permutation_test(
                data["matrix"], data["agent_cols"], "Y",
                n_permutations=args.n_permutations,
            )

            print(f"\n  Temporal Emergence Capacity: "
                  f"{perm_results['emergence_capacity_observed']:.4f} bits")
            print(f"  EC p-value: {perm_results['emergence_capacity_p']:.3f}")

            for pair, p in perm_results["p_values"].items():
                obs = perm_results["observed_synergy"][pair]
                sig = " *" if p < 0.05 else ""
                print(f"  {pair[0]:12s} × {pair[1]:12s}: "
                      f"synergy={obs:.4f}, p={p:.3f}{sig}")

            data["permutation_results"] = perm_results
            data["ec_p_value"] = perm_results["emergence_capacity_p"]
    else:
        print("\n[Skipping permutation tests]")
        for faction in all_results:
            all_results[faction]["ec_p_value"] = np.nan

    # ==================================================================
    # PHASE 5: Summary
    # ==================================================================
    print("\n" + "=" * 70)
    print("TEMPORAL PID SUMMARY")
    print("=" * 70)

    summary = {}
    for faction, data in all_results.items():
        pw = data["pairwise_results"]
        pw_df = pairwise_results_to_df(pw).dropna(subset=["synergy"])

        if pw_df.empty:
            print(f"\n{faction}: No valid PID results")
            continue

        mean_mi = pw_df["mutual_info"].mean()
        mean_syn = pw_df["synergy"].mean()
        mean_red = pw_df["redundancy"].mean()
        ec = data["emergence_capacity"]
        ec_p = data.get("ec_p_value", np.nan)

        total_info = mean_syn + mean_red + pw_df["unique_i"].mean() + pw_df["unique_j"].mean()
        syn_pct = 100 * mean_syn / total_info if total_info > 0 else 0
        red_pct = 100 * mean_red / total_info if total_info > 0 else 0

        print(f"\n{faction} (Temporal):")
        print(f"  Transitions analyzed:     {data['metadata']['n_transitions']}")
        print(f"  Target variable:          {data['metadata']['target_type']}")
        print(f"  Mean Mutual Information:  {mean_mi:.4f} bits")
        print(f"  Mean Synergy:             {mean_syn:.4f} bits ({syn_pct:.1f}%)")
        print(f"  Mean Redundancy:          {mean_red:.4f} bits ({red_pct:.1f}%)")
        print(f"  Emergence Capacity:       {ec:.4f} bits")
        if not np.isnan(ec_p):
            sig = "SIGNIFICANT" if ec_p < 0.05 else "NOT significant"
            print(f"  EC p-value:               {ec_p:.3f} ({sig})")

        # Interpretation
        if mean_mi < 0.01:
            interp = "VERY LOW MI — agents don't adapt over time"
        elif mean_syn < 0.005:
            interp = "NEGLIGIBLE temporal synergy — actions evolve independently"
        elif syn_pct > 40:
            interp = "HIGH temporal synergy — genuine dynamic coordination"
        elif syn_pct > red_pct and mean_syn > 0.01:
            interp = "MODERATE temporal synergy — some dynamic coordination"
        else:
            interp = "MIXED temporal signal"
        print(f"  Interpretation:           {interp}")

        summary[faction] = {
            "mean_mutual_info": round(mean_mi, 6),
            "mean_synergy": round(mean_syn, 6),
            "mean_redundancy": round(mean_red, 6),
            "emergence_capacity": round(ec, 6),
            "ec_p_value": round(ec_p, 4) if not np.isnan(ec_p) else None,
            "synergy_pct": round(syn_pct, 1),
            "interpretation": interp,
            "n_transitions": data["metadata"]["n_transitions"],
            "n_scenarios": data["metadata"]["n_scenarios"],
            "target": data["metadata"]["target_type"],
        }

    # Save summary
    summary_path = os.path.join(output_dir, "temporal_pid_summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSaved summary: {summary_path}")

    elapsed = time.time() - t0
    print(f"\nTotal time: {elapsed:.1f}s")
    print(f"Results in: {output_dir}")
    print("=" * 70)


if __name__ == "__main__":
    main()
