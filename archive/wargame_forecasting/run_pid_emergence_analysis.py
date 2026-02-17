"""
PID Emergence Analysis — Main Orchestration Script

Runs the full Partial Information Decomposition pipeline to measure
emergent coordination in the Tethys-Novaris multi-agent LLM simulation.

Phases:
1. Data extraction and escalation encoding
2. Pairwise PID computation per faction
3. Permutation significance testing
4. Conditional analysis (crisis level, territory, sanctions)
5. Leader value-add analysis
6. Visualization

Usage:
    python forecasting/run_pid_emergence_analysis.py

Output:
    experiment_results/pid_analysis/
"""

import os
import sys
import json
import time
import argparse
import numpy as np
import pandas as pd
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pid_data_extraction import (
    extract_agent_escalation_matrix,
    pivot_to_pid_matrix,
    extract_leader_decisions,
    collapse_escalation_to_3_levels,
    print_escalation_distribution,
    print_collapse_distribution,
)
from pid_analysis import (
    compute_pairwise_pid,
    compute_full_group_pid,
    emergence_capacity,
    permutation_test,
    conditional_pid,
    leader_value_add_pid,
    summarize_pid,
    pairwise_results_to_df,
)
from pid_visualization import (
    plot_synergy_heatmap,
    plot_null_distribution,
    plot_pid_decomposition,
    plot_conditional_comparison,
    plot_proposed_vs_final,
    plot_leader_value_add,
    plot_summary_table,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="PID Emergence Analysis for Tethys-Novaris Simulation"
    )
    parser.add_argument(
        "--data-dir", type=str,
        default="outputs/multiscenario",
        help="Path to multiscenario data directory",
    )
    parser.add_argument(
        "--output-dir", type=str,
        default="experiment_results/pid_analysis",
        help="Output directory for results and plots",
    )
    parser.add_argument(
        "--n-permutations", type=int, default=1000,
        help="Number of permutations for significance tests",
    )
    parser.add_argument(
        "--aggregation", type=str, default="primary",
        choices=["primary", "max", "mean"],
        help="How to aggregate multi-action proposals",
    )
    parser.add_argument(
        "--collapse-levels", type=int, default=5,
        choices=[3, 5],
        help="Number of escalation levels (5=full, 3=collapsed)",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for permutation tests",
    )
    parser.add_argument(
        "--skip-permutation", action="store_true",
        help="Skip permutation tests (faster for debugging)",
    )
    parser.add_argument(
        "--collapse-bins", type=str, default=None,
        help="Comma-separated collapse probability bin boundaries (e.g., '0,0.45,0.65,1.0')",
    )
    parser.add_argument(
        "--binning", type=str, default="tercile",
        choices=["tercile", "quartile", "fixed"],
        help="Binning strategy for target variable: 'tercile' (equal-frequency 3 bins, default), "
             "'quartile' (equal-frequency 4 bins), 'fixed' (use --collapse-bins boundaries)",
    )
    parser.add_argument(
        "--target", type=str, default="collapse_probability",
        choices=["collapse_probability", "final_crisis_level",
                 "final_military_balance", "final_territory",
                 "final_sanctions", "final_support"],
        help="Target variable for PID (default: collapse_probability)",
    )
    return parser.parse_args()


def main():
    import warnings
    warnings.filterwarnings("ignore", message="Sample space has more than")
    args = parse_args()

    # Resolve paths relative to project root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(project_root, args.data_dir) if not os.path.isabs(args.data_dir) else args.data_dir
    output_dir = os.path.join(project_root, args.output_dir) if not os.path.isabs(args.output_dir) else args.output_dir
    os.makedirs(output_dir, exist_ok=True)

    # Parse collapse bins
    collapse_bins = None
    if args.collapse_bins:
        collapse_bins = [float(x) for x in args.collapse_bins.split(",")]
    elif args.binning in ("tercile", "quartile"):
        collapse_bins = args.binning  # pass string to pivot_to_pid_matrix
    elif args.binning == "fixed":
        collapse_bins = [0, 0.45, 0.65, 1.0]
    # For non-collapse targets with no explicit bins, collapse_bins=None triggers tercile binning

    # Load ground truth for alternative targets
    target_values = None
    if args.target != "collapse_probability":
        gt_path = os.path.join(data_dir, "ground_truth.csv")
        target_values = pd.read_csv(gt_path)
        if args.target not in target_values.columns:
            print(f"ERROR: Target '{args.target}' not found in ground_truth.csv")
            print(f"  Available columns: {list(target_values.columns)}")
            sys.exit(1)

    print("=" * 70)
    print("PID EMERGENCE ANALYSIS")
    print("Partial Information Decomposition of Multi-Agent Coordination")
    print("=" * 70)
    print(f"\nData directory:     {data_dir}")
    print(f"Output directory:   {output_dir}")
    print(f"Target variable:    {args.target}")
    print(f"Aggregation:        {args.aggregation}")
    print(f"Escalation levels:  {args.collapse_levels}")
    print(f"Collapse bins:      {collapse_bins if collapse_bins else 'tercile (auto)'}")
    print(f"N permutations:     {args.n_permutations}")
    print(f"Random seed:        {args.seed}")

    # ==================================================================
    # PHASE 1: Data Extraction
    # ==================================================================
    print("\n" + "=" * 70)
    print("PHASE 1: Data Extraction")
    print("=" * 70)

    t0 = time.time()
    raw_df = extract_agent_escalation_matrix(data_dir)
    print(f"\nExtracted {len(raw_df)} rows from {raw_df['scenario_id'].nunique()} scenarios")
    print(f"Factions: {sorted(raw_df['faction_name'].unique())}")
    print(f"Roles: {sorted(raw_df['agent_role'].unique())}")

    print_escalation_distribution(raw_df)
    print_collapse_distribution(raw_df, bins=collapse_bins)

    # Save raw extraction
    raw_path = os.path.join(output_dir, "raw_escalation_matrix.csv")
    raw_df.to_csv(raw_path, index=False)
    print(f"\nSaved raw data: {raw_path}")

    # ==================================================================
    # PHASE 2: PID Computation
    # ==================================================================
    print("\n" + "=" * 70)
    print("PHASE 2: PID Computation")
    print("=" * 70)

    all_faction_results = {}

    for faction in ["Novaris", "Tethys"]:
        print(f"\n--- {faction} ---")

        # Pivot to PID matrix (proposed actions)
        matrix, meta = pivot_to_pid_matrix(
            raw_df, faction,
            use_final=False,
            aggregation=args.aggregation,
            collapse_bins=collapse_bins,
            target=args.target,
            target_values=target_values,
        )
        agent_cols = meta["agent_cols"]
        print(f"PID matrix: {meta['n_scenarios']} scenarios × {len(agent_cols)} agents")
        print(f"Agent roles: {agent_cols}")
        print(f"Y distribution: {dict(matrix['Y'].value_counts().sort_index())}")

        # Optionally collapse escalation levels
        if args.collapse_levels == 3:
            print("Collapsing escalation to 3 levels...")
            matrix = collapse_escalation_to_3_levels(matrix, agent_cols)

        # Save PID matrix
        matrix_path = os.path.join(output_dir, f"{faction.lower()}_pid_matrix.csv")
        matrix.to_csv(matrix_path)
        print(f"Saved PID matrix: {matrix_path}")

        # Pairwise PID
        print(f"\nComputing pairwise PID ({len(agent_cols)} agents, "
              f"{len(agent_cols) * (len(agent_cols) - 1) // 2} pairs)...")
        pairwise = compute_pairwise_pid(matrix, agent_cols, "Y")
        ec = emergence_capacity(pairwise)
        summarize_pid(pairwise, faction)

        # Full-group PID (if feasible — BROJA is prohibitively slow for 4+ sources)
        full_group = None
        if len(agent_cols) <= 3:
            print(f"\nComputing full-group PID ({len(agent_cols)} sources)...")
            full_group = compute_full_group_pid(matrix, agent_cols, "Y")
            if "error" in full_group:
                print(f"  Full-group PID failed: {full_group['error']}")
            else:
                print(f"  Full-group PID atoms: {len(full_group['atoms'])}")
                for atom_name, val in sorted(full_group["atoms"].items(),
                                             key=lambda x: -x[1])[:10]:
                    print(f"    {atom_name}: {val:.4f} bits")
        else:
            print(f"\nSkipping full-group PID ({len(agent_cols)} sources — "
                  f"BROJA optimization too expensive for >3 sources)")

        # Also compute with final actions for comparison
        print(f"\nComputing PID on final (post-leader) actions...")
        matrix_final, meta_final = pivot_to_pid_matrix(
            raw_df, faction,
            use_final=True,
            aggregation=args.aggregation,
            collapse_bins=collapse_bins,
            target=args.target,
            target_values=target_values,
        )
        if args.collapse_levels == 3:
            matrix_final = collapse_escalation_to_3_levels(matrix_final, meta_final["agent_cols"])
        pairwise_final = compute_pairwise_pid(matrix_final, meta_final["agent_cols"], "Y")
        summarize_pid(pairwise_final, f"{faction} (final)")

        all_faction_results[faction] = {
            "matrix": matrix,
            "metadata": meta,
            "pairwise_results": pairwise,
            "pairwise_final": pairwise_final,
            "emergence_capacity": ec,
            "full_group": full_group,
            "agent_cols": agent_cols,
        }

    # Save pairwise results
    for faction, data in all_faction_results.items():
        pw_df = pairwise_results_to_df(data["pairwise_results"])
        pw_path = os.path.join(output_dir, f"{faction.lower()}_pairwise_pid.csv")
        pw_df.to_csv(pw_path, index=False)
        print(f"Saved: {pw_path}")

    # ==================================================================
    # PHASE 3: Permutation Tests
    # ==================================================================
    if not args.skip_permutation:
        print("\n" + "=" * 70)
        print("PHASE 3: Permutation Significance Tests")
        print("=" * 70)

        for faction, data in all_faction_results.items():
            matrix = data["matrix"]
            agent_cols = data["agent_cols"]

            for surr_type in ["row_shuffle", "column_shift"]:
                print(f"\n--- {faction} — {surr_type} ({args.n_permutations} permutations) ---")

                perm_results = permutation_test(
                    matrix, agent_cols, "Y",
                    n_permutations=args.n_permutations,
                    surrogate_type=surr_type,
                    seed=args.seed,
                )

                print(f"\n  Emergence Capacity: {perm_results['emergence_capacity_observed']:.4f} bits")
                print(f"  EC p-value: {perm_results['emergence_capacity_p']:.3f}")

                for pair, p in perm_results["p_values"].items():
                    obs = perm_results["observed_synergy"][pair]
                    sig = "*" if p < 0.05 else ""
                    sig2 = "*" if p < 0.01 else ""
                    print(f"  {pair[0]:12s} × {pair[1]:12s}: "
                          f"synergy={obs:.4f}, p={p:.3f} {sig}{sig2}")

                data[f"permutation_{surr_type}"] = perm_results

                # Store EC p-value for summary
                if surr_type == "row_shuffle":
                    data["ec_p_value"] = perm_results["emergence_capacity_p"]
    else:
        print("\n[Skipping permutation tests]")
        for faction in all_faction_results:
            all_faction_results[faction]["ec_p_value"] = np.nan

    # ==================================================================
    # PHASE 4: Conditional Analysis
    # ==================================================================
    print("\n" + "=" * 70)
    print("PHASE 4: Conditional Analysis")
    print("=" * 70)

    # Need to join scenario parameters back to PID matrix
    sc = pd.read_csv(os.path.join(data_dir, "scenarios.csv"))

    conditions = [
        ("crisis_level", 7, ("low_crisis", "high_crisis")),
        ("territory_controlled", 0.25, ("low_territory", "high_territory")),
        ("sanctions_level", 0.5, ("low_sanctions", "high_sanctions")),
    ]

    for faction, data in all_faction_results.items():
        print(f"\n--- {faction} ---")
        matrix = data["matrix"].copy()

        # Join scenario parameters
        matrix = matrix.reset_index()
        matrix = matrix.merge(sc, on="scenario_id", how="left")

        data["conditional_results"] = {}

        for cond_col, threshold, labels in conditions:
            if cond_col not in matrix.columns:
                print(f"  Skipping {cond_col}: not found in data")
                continue

            print(f"\n  Condition: {cond_col} (threshold={threshold})")
            cond_result = conditional_pid(
                matrix, data["agent_cols"], "Y",
                cond_col, threshold, labels
            )

            for label, res in cond_result.items():
                ec = res["emergence_capacity"]
                n = res["n_scenarios"]
                ec_str = f"{ec:.4f}" if not np.isnan(ec) else "N/A"
                warn = f" [{res.get('warning', '')}]" if "warning" in res else ""
                print(f"    {label}: EC={ec_str}, n={n}{warn}")

            data["conditional_results"][cond_col] = cond_result

    # ==================================================================
    # PHASE 5: Leader Value-Add Analysis
    # ==================================================================
    print("\n" + "=" * 70)
    print("PHASE 5: Leader Value-Add Analysis")
    print("=" * 70)

    for faction, data in all_faction_results.items():
        print(f"\n--- {faction} ---")
        leader_df = extract_leader_decisions(raw_df, faction)
        print(f"Leader decisions: {len(leader_df)} observations")
        print(f"Decision distribution: {dict(leader_df['leader_decision'].value_counts().sort_index())}")

        leader_results = leader_value_add_pid(leader_df, collapse_bins=collapse_bins)

        for r in leader_results:
            if not np.isnan(r.get("synergy", np.nan)):
                total = r["synergy"] + r["redundancy"] + r["unique_expert"] + r["unique_leader"]
                print(f"  {r['agent_role']:12s}: MI={r['mutual_info']:.4f}, "
                      f"Syn={r['synergy']:.4f}, Red={r['redundancy']:.4f}, "
                      f"U_exp={r['unique_expert']:.4f}, U_ldr={r['unique_leader']:.4f}")
            else:
                print(f"  {r['agent_role']:12s}: FAILED ({r.get('error', 'unknown')})")

        data["leader_results"] = leader_results

    # ==================================================================
    # PHASE 6: Visualization
    # ==================================================================
    print("\n" + "=" * 70)
    print("PHASE 6: Visualization")
    print("=" * 70)

    plots_dir = os.path.join(output_dir, "plots")

    for faction, data in all_faction_results.items():
        print(f"\n--- {faction} ---")

        # Synergy heatmap
        plot_synergy_heatmap(data["pairwise_results"], faction, plots_dir, "synergy")
        plot_synergy_heatmap(data["pairwise_results"], faction, plots_dir, "redundancy")
        plot_synergy_heatmap(data["pairwise_results"], faction, plots_dir, "mutual_info")

        # PID decomposition
        plot_pid_decomposition(data["pairwise_results"], faction, plots_dir)

        # Proposed vs Final
        plot_proposed_vs_final(
            data["pairwise_results"], data["pairwise_final"],
            faction, plots_dir
        )

        # Permutation null distributions
        for surr_type in ["row_shuffle", "column_shift"]:
            key = f"permutation_{surr_type}"
            if key in data:
                plot_null_distribution(data[key], faction, plots_dir)

        # Conditional comparisons
        for cond_col, cond_result in data.get("conditional_results", {}).items():
            plot_conditional_comparison(cond_result, cond_col, faction, plots_dir)

        # Leader value-add
        if "leader_results" in data:
            plot_leader_value_add(data["leader_results"], faction, plots_dir)

    # Summary table
    plot_summary_table(all_faction_results, plots_dir)

    # ==================================================================
    # PHASE 7: Summary & Interpretation
    # ==================================================================
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    summary = {}
    for faction, data in all_faction_results.items():
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

        print(f"\n{faction}:")
        print(f"  Mean Mutual Information:  {mean_mi:.4f} bits")
        print(f"  Mean Synergy:             {mean_syn:.4f} bits ({syn_pct:.1f}%)")
        print(f"  Mean Redundancy:          {mean_red:.4f} bits ({red_pct:.1f}%)")
        print(f"  Emergence Capacity:       {ec:.4f} bits")
        if not np.isnan(ec_p):
            sig = "SIGNIFICANT" if ec_p < 0.05 else "NOT significant"
            print(f"  EC p-value:               {ec_p:.3f} ({sig})")

        # Interpretation — consider both proportion and absolute magnitude
        if mean_mi < 0.01:
            interp = "VERY LOW MI — agents produce near-identical action patterns"
        elif mean_syn < 0.005:
            interp = "NEGLIGIBLE SYNERGY — unique information dominates, no emergent coordination"
        elif syn_pct > 40:
            interp = "HIGH SYNERGY — genuine emergent coordination detected"
        elif red_pct > 60:
            interp = "HIGH REDUNDANCY — cosmetic diversity, agents converge"
        elif syn_pct > red_pct and mean_syn > 0.01:
            interp = "MODERATE SYNERGY — some emergent coordination present"
        else:
            interp = "MIXED — no dominant pattern"
        print(f"  Interpretation:           {interp}")

        summary[faction] = {
            "mean_mutual_info": round(mean_mi, 6),
            "mean_synergy": round(mean_syn, 6),
            "mean_redundancy": round(mean_red, 6),
            "emergence_capacity": round(ec, 6),
            "ec_p_value": round(ec_p, 4) if not np.isnan(ec_p) else None,
            "synergy_pct": round(syn_pct, 1),
            "redundancy_pct": round(red_pct, 1),
            "interpretation": interp,
            "n_scenarios": data["metadata"]["n_scenarios"],
            "n_agent_pairs": len(pw_df),
        }

    # Save summary JSON
    summary_path = os.path.join(output_dir, "pid_summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSaved summary: {summary_path}")

    elapsed = time.time() - t0
    print(f"\nTotal time: {elapsed:.1f}s")
    print(f"Results in: {output_dir}")
    print("=" * 70)


if __name__ == "__main__":
    main()
