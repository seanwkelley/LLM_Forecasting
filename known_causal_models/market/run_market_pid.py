"""
Market PID Analysis — Run PID on market simulation results.

Takes output from run_market_sim.py (scenario JSON files) and runs
Partial Information Decomposition to measure emergent coordination
between LLM trading agents.

Usage:
    # Analyze baseline results
    python market/run_market_pid.py --results-dir outputs/simulations/market

    # Full analysis with permutation tests
    python market/run_market_pid.py \
        --results-dir outputs/simulations/market \
        --n-permutations 500 \
        --encoding direction_aggr
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from market.pid_extraction import (
    extract_multi_scenario,
    extract_order_matrix,
    load_scenario_result,
    print_extraction_summary,
)
from market.pid_analysis import (
    compute_all_pairwise,
    compute_all_triplets,
    compute_identity_differentiation,
    emergence_capacity,
    higher_order_capacity,
    permutation_test,
    print_differentiation_summary,
    print_triplet_summary,
)


def run_pid_on_market_data(
    results_dir: str | Path,
    encoding: str = "direction_aggr",
    agent_groups: dict | None = None,
    n_permutations: int = 0,
    seed: int = 42,
    verbose: bool = True,
) -> dict:
    """Run PID analysis on market simulation results.

    Parameters
    ----------
    results_dir : str or Path
        Directory with scenario_NNN.json files.
    encoding : str
        Action encoding: "direction", "direction_aggr", or "full".
    agent_groups : dict or None
        Optional grouping of agents for focused analysis.
        E.g., {"producers": ["producer_A", "producer_B"],
               "consumers": ["consumer_A", "consumer_B", "consumer_C"],
               "speculators": ["speculator_A", "speculator_B"]}
        If None, analyzes all agents together.
    n_permutations : int
        Number of permutations for significance testing. 0 = skip.
    seed : int
        Random seed.
    verbose : bool
        Print results.

    Returns
    -------
    dict with PID results.
    """
    results_dir = Path(results_dir)

    # Extract PID matrices (numpy arrays + column names)
    X, Y, col_names = extract_multi_scenario(results_dir, encoding=encoding)

    if verbose:
        print_extraction_summary(X, Y, col_names)

    agent_cols = list(col_names)

    # Filter out constant columns (zero variance — useless for PID)
    varying_mask = [X[:, i].std() > 0 for i in range(X.shape[1])]
    dropped = [c for c, v in zip(agent_cols, varying_mask) if not v]
    if dropped and verbose:
        print(f"\n  Dropped constant columns: {sorted(dropped)}")

    varying_indices = [i for i, v in enumerate(varying_mask) if v]
    X = X[:, varying_indices]
    agent_cols = [agent_cols[i] for i in varying_indices]

    if len(agent_cols) < 2:
        print("[FAIL] Fewer than 2 varying agent columns — cannot compute PID")
        return {"error": "insufficient_varying_agents"}

    # --- All-agent PID ---
    if verbose:
        print(f"\n{'='*60}")
        print(f"ALL-AGENT PID ({len(agent_cols)} agents, {len(X)} obs)")
        print(f"{'='*60}")

    pairwise = compute_all_pairwise(X, Y, agent_cols)
    ec = emergence_capacity(pairwise)

    if verbose:
        _print_pairwise(pairwise, ec)

    all_agent_result = {
        "pairwise": pairwise,
        "emergence_capacity": ec,
        "n_agents": len(agent_cols),
        "n_observations": len(X),
        "agent_cols": agent_cols,
    }

    # --- Permutation test ---
    perm_results = {}
    if n_permutations > 0:
        for method in ["row_shuffle", "column_shift"]:
            if verbose:
                print(f"\n--- Permutation test: {method} ({n_permutations} perms) ---")

            perm = permutation_test(
                X, Y, agent_cols,
                n_permutations=n_permutations,
                method=method,
                seed=seed,
                verbose=verbose,
            )

            if verbose:
                print(f"\n  EC = {perm['observed_ec']:.4f}, "
                      f"p = {perm['ec_pvalue']:.3f}")
                for pair, p in perm["pair_pvalues"].items():
                    obs_syn = [r for r in perm["observed_pairs"]
                               if (r["agent_i"], r["agent_j"]) == pair][0]["synergy"]
                    sig = "*" if p < 0.05 else ""
                    print(f"  {pair[0]:15s} x {pair[1]:15s}: "
                          f"syn={obs_syn:.4f}, p={p:.3f} {sig}")

            perm_results[method] = {
                "ec_observed": perm["observed_ec"],
                "ec_p": perm["ec_pvalue"],
                "pair_p_values": {
                    f"{k[0]}_x_{k[1]}": v for k, v in perm["pair_pvalues"].items()
                },
            }

        all_agent_result["permutation_tests"] = perm_results

    # Helper: get X subset for given agent names
    def _get_subset(names):
        indices = [agent_cols.index(n) for n in names]
        return X[:, indices]

    # --- Role-group PID ---
    group_results = {}
    if agent_groups:
        for group_name, group_agents in agent_groups.items():
            # Only include agents that exist and vary
            group_cols = [a for a in group_agents if a in agent_cols]
            if len(group_cols) < 2:
                if verbose:
                    print(f"\n  Skipping group '{group_name}': "
                          f"<2 varying agents ({group_cols})")
                continue

            if verbose:
                print(f"\n{'='*60}")
                print(f"GROUP: {group_name} ({group_cols})")
                print(f"{'='*60}")

            grp_X = _get_subset(group_cols)
            grp_pairwise = compute_all_pairwise(grp_X, Y, group_cols)
            grp_ec = emergence_capacity(grp_pairwise)

            if verbose:
                _print_pairwise(grp_pairwise, grp_ec)

            group_results[group_name] = {
                "agents": group_cols,
                "pairwise": grp_pairwise,
                "emergence_capacity": grp_ec,
            }

    # --- Cross-role PID (one agent from each role) ---
    cross_role_results = {}
    if agent_groups and len(agent_groups) >= 2:
        roles = list(agent_groups.keys())
        for i, role_a in enumerate(roles):
            for role_b in roles[i+1:]:
                agents_a = [a for a in agent_groups[role_a] if a in agent_cols]
                agents_b = [a for a in agent_groups[role_b] if a in agent_cols]
                if not agents_a or not agents_b:
                    continue

                cross_cols = agents_a + agents_b
                if verbose:
                    print(f"\n{'='*60}")
                    print(f"CROSS-ROLE: {role_a} vs {role_b}")
                    print(f"{'='*60}")

                cross_X = _get_subset(cross_cols)
                cross_pairwise = compute_all_pairwise(cross_X, Y, cross_cols)

                # Filter to only cross-role pairs
                cross_only = [
                    r for r in cross_pairwise
                    if (r["agent_i"] in agents_a and r["agent_j"] in agents_b) or
                       (r["agent_i"] in agents_b and r["agent_j"] in agents_a)
                ]
                cross_ec = emergence_capacity(cross_only) if cross_only else np.nan

                if verbose and cross_only:
                    _print_pairwise(cross_only, cross_ec)

                cross_role_results[f"{role_a}_vs_{role_b}"] = {
                    "pairwise": cross_only,
                    "emergence_capacity": cross_ec,
                }

    # --- Higher-order synergies (triplet G3) ---
    triplet_results = []
    hoc = np.nan
    if len(agent_cols) >= 3:
        if verbose:
            print(f"\n{'='*60}")
            print(f"HIGHER-ORDER SYNERGIES (Triplet G3)")
            print(f"{'='*60}")

        triplet_results = compute_all_triplets(X, Y, agent_cols)
        hoc = higher_order_capacity(triplet_results)

        if verbose:
            print_triplet_summary(triplet_results)

    all_agent_result["triplets"] = triplet_results
    all_agent_result["higher_order_capacity"] = hoc

    # --- Identity-linked differentiation ---
    if verbose:
        print(f"\n{'='*60}")
        print(f"IDENTITY-LINKED DIFFERENTIATION")
        print(f"{'='*60}")

    diff_results = compute_identity_differentiation(X, agent_cols)

    if verbose:
        print_differentiation_summary(diff_results)

    return {
        "all_agents": all_agent_result,
        "groups": group_results,
        "cross_role": cross_role_results,
        "differentiation": diff_results,
        "encoding": encoding,
        "results_dir": str(results_dir),
    }


def compare_llm_vs_baseline(
    llm_result: dict,
    baseline_result: dict,
    verbose: bool = True,
) -> dict:
    """Compare PID results between LLM and baseline runs.

    Parameters
    ----------
    llm_result : dict
        Output of run_pid_on_market_data() for LLM run.
    baseline_result : dict
        Output of run_pid_on_market_data() for baseline run.

    Returns
    -------
    dict with comparison statistics.
    """
    llm_all = llm_result["all_agents"]
    base_all = baseline_result["all_agents"]

    llm_ec = llm_all["emergence_capacity"]
    base_ec = base_all["emergence_capacity"]

    # Pairwise comparison
    llm_pairs = {(r["agent_i"], r["agent_j"]): r for r in llm_all["pairwise"]}
    base_pairs = {(r["agent_i"], r["agent_j"]): r for r in base_all["pairwise"]}

    common_pairs = set(llm_pairs.keys()) & set(base_pairs.keys())

    comparison = []
    for pair in sorted(common_pairs):
        lp = llm_pairs[pair]
        bp = base_pairs[pair]
        comparison.append({
            "pair": f"{pair[0]} x {pair[1]}",
            "llm_synergy": lp["synergy"],
            "baseline_synergy": bp["synergy"],
            "delta_synergy": lp["synergy"] - bp["synergy"],
            "llm_mi": lp["mutual_info"],
            "baseline_mi": bp["mutual_info"],
            "delta_mi": lp["mutual_info"] - bp["mutual_info"],
        })

    if verbose:
        print(f"\n{'='*70}")
        print("LLM vs BASELINE COMPARISON")
        print(f"{'='*70}")
        print(f"\n  Emergence Capacity:")
        print(f"    LLM:      {llm_ec:.4f} bits")
        print(f"    Baseline: {base_ec:.4f} bits")
        print(f"    Delta:    {llm_ec - base_ec:+.4f} bits")

        if comparison:
            print(f"\n  Pairwise Synergy Deltas:")
            for c in comparison:
                direction = "[+]" if c["delta_synergy"] > 0.001 else (
                    "[-]" if c["delta_synergy"] < -0.001 else "[=]"
                )
                print(f"    {direction} {c['pair']:30s}: "
                      f"LLM={c['llm_synergy']:.4f} vs "
                      f"Base={c['baseline_synergy']:.4f} "
                      f"(delta={c['delta_synergy']:+.4f})")

        # Summary statistics
        llm_syns = [c["llm_synergy"] for c in comparison
                    if not np.isnan(c["llm_synergy"])]
        base_syns = [c["baseline_synergy"] for c in comparison
                     if not np.isnan(c["baseline_synergy"])]

        if llm_syns and base_syns:
            print(f"\n  Mean synergy — LLM: {np.mean(llm_syns):.4f}, "
                  f"Baseline: {np.mean(base_syns):.4f}")

    return {
        "llm_ec": llm_ec,
        "baseline_ec": base_ec,
        "delta_ec": llm_ec - base_ec,
        "pairwise_comparison": comparison,
    }


def _print_pairwise(results: list[dict], ec: float):
    """Print pairwise PID summary."""
    for r in results:
        mi = r["mutual_info"]
        if mi > 0:
            syn_pct = r["synergy"] / mi * 100
            red_pct = r["redundancy"] / mi * 100
        else:
            syn_pct = red_pct = 0.0

        print(f"  {r['agent_i']:15s} x {r['agent_j']:15s} | "
              f"MI={mi:.4f} | "
              f"Syn={r['synergy']:.4f} ({syn_pct:4.1f}%) | "
              f"Red={r['redundancy']:.4f} ({red_pct:4.1f}%)")

    print(f"\n  Emergence Capacity (median synergy): {ec:.4f} bits")


def main():
    parser = argparse.ArgumentParser(
        description="Run PID analysis on market simulation results"
    )
    parser.add_argument(
        "--results-dir", type=str, required=True,
        help="Directory with scenario_NNN.json files"
    )
    parser.add_argument(
        "--baseline-dir", type=str, default=None,
        help="Optional baseline directory for comparison"
    )
    parser.add_argument(
        "--encoding", type=str, default="direction_aggr",
        choices=["direction", "direction_aggr", "full"],
        help="Action encoding method"
    )
    parser.add_argument(
        "--n-permutations", type=int, default=0,
        help="Permutation tests (0 = skip, 500+ recommended)"
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed"
    )
    parser.add_argument(
        "--output-dir", type=str, default=None,
        help="Output directory (default: <results-dir>/pid_analysis)"
    )
    args = parser.parse_args()

    # Default agent groups by role
    agent_groups = {
        "producers": ["producer_A", "producer_B"],
        "consumers": ["consumer_A", "consumer_B", "consumer_C"],
        "speculators": ["speculator_A", "speculator_B"],
    }

    print("=" * 70)
    print("MARKET PID ANALYSIS")
    print(f"Results:     {args.results_dir}")
    print(f"Encoding:    {args.encoding}")
    print(f"Permutations: {args.n_permutations}")
    if args.baseline_dir:
        print(f"Baseline:    {args.baseline_dir}")
    print("=" * 70)

    # Run main analysis
    llm_result = run_pid_on_market_data(
        results_dir=args.results_dir,
        encoding=args.encoding,
        agent_groups=agent_groups,
        n_permutations=args.n_permutations,
        seed=args.seed,
    )

    # Run baseline comparison if provided
    comparison = None
    if args.baseline_dir:
        print(f"\n\n{'='*70}")
        print("BASELINE ANALYSIS")
        print(f"{'='*70}")

        baseline_result = run_pid_on_market_data(
            results_dir=args.baseline_dir,
            encoding=args.encoding,
            agent_groups=agent_groups,
            n_permutations=0,  # No permutation test for baseline
            seed=args.seed,
        )

        comparison = compare_llm_vs_baseline(llm_result, baseline_result)

    # Save results
    output_dir = Path(args.output_dir) if args.output_dir else (
        Path(args.results_dir) / "pid_analysis"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    # Convert results to JSON-safe format
    def _clean(obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, dict):
            return {str(k): _clean(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_clean(v) for v in obj]
        return obj

    summary = {
        "results_dir": args.results_dir,
        "encoding": args.encoding,
        "n_permutations": args.n_permutations,
        "all_agents_ec": llm_result["all_agents"]["emergence_capacity"],
        "n_observations": llm_result["all_agents"]["n_observations"],
        "n_agents": llm_result["all_agents"]["n_agents"],
    }

    # Add permutation p-values if available
    perm = llm_result["all_agents"].get("permutation_tests", {})
    if "row_shuffle" in perm:
        summary["ec_p_row_shuffle"] = perm["row_shuffle"]["ec_p"]
    if "column_shift" in perm:
        summary["ec_p_column_shift"] = perm["column_shift"]["ec_p"]

    if comparison:
        summary["baseline_ec"] = comparison["baseline_ec"]
        summary["delta_ec"] = comparison["delta_ec"]

    # Higher-order synergies
    summary["higher_order_capacity"] = llm_result["all_agents"].get(
        "higher_order_capacity", None
    )

    # Identity differentiation
    diff = llm_result.get("differentiation", {})
    if diff:
        summary["mean_differentiation_jsd"] = diff.get("mean_jsd")
        summary["mean_consistency_jsd"] = diff.get("mean_consistency_jsd")
        summary["mean_action_entropy"] = diff.get("mean_action_entropy")

    with open(output_dir / "market_pid_summary.json", "w") as f:
        json.dump(_clean(summary), f, indent=2)

    # Save full pairwise results
    pairwise_data = llm_result["all_agents"]["pairwise"]
    if pairwise_data:
        pairwise_df = pd.DataFrame(pairwise_data)
        pairwise_df.to_csv(output_dir / "market_pairwise_pid.csv", index=False)

    if comparison and comparison.get("pairwise_comparison"):
        comp_df = pd.DataFrame(comparison["pairwise_comparison"])
        comp_df.to_csv(output_dir / "llm_vs_baseline.csv", index=False)

    print(f"\n\nResults saved to: {output_dir}")


if __name__ == "__main__":
    main()
