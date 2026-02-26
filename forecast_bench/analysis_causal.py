"""
Causal Network Analysis — Compute network-specific metrics from causal experiment results.

Six network-specific metrics on top of the base analysis:
1. Importance-sensitivity correlation (Spearman)
2. Structural sensitivity ratio (SSR)
3. Sensitivity by probe category (node/edge/structural)
4. Critical path premium
5. Spurious acceptance rate
6. Asymmetry index

Usage:
    python forecast_bench/analysis_causal.py outputs/sensitivity/causal/llama_one_turn
    python forecast_bench/analysis_causal.py outputs/sensitivity/causal/llama_one_turn outputs/sensitivity/causal/70b_multi_turn
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from forecast_bench.analysis import (
    compute_anchoring_metrics,
    compute_consistency_metrics,
    compare_conditions,
    _spearman_correlation,
)


# =============================================================================
# DATA LOADING
# =============================================================================

def load_causal_results(csv_path: Path) -> list[dict]:
    """Load causal sensitivity_results.csv into a list of dicts."""
    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Parse numeric fields
            for field in ("initial_probability", "updated_probability", "absolute_shift",
                          "probe_index", "target_importance", "target_centrality_rank",
                          "n_nodes", "n_edges", "graph_density"):
                if row.get(field):
                    try:
                        row[field] = float(row[field])
                    except ValueError:
                        row[field] = None
                else:
                    row[field] = None
            # Parse boolean fields
            row["success"] = str(row.get("success", "")).lower() == "true"
            row["target_on_critical_path"] = str(row.get("target_on_critical_path", "")).lower() == "true"
            row["probe_generated"] = str(row.get("probe_generated", "")).lower() == "true"
            rows.append(row)
    return rows


def is_causal_csv(csv_path: Path) -> bool:
    """Check if a CSV file has causal-mode fields."""
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
    return "probe_category" in fields and "target_importance" in fields


# =============================================================================
# NETWORK-SPECIFIC METRICS
# =============================================================================

def importance_sensitivity_correlation(rows: list[dict]) -> dict:
    """Spearman correlation between target_importance and |shift|.

    Core hypothesis test: does computed centrality predict actual sensitivity?

    Returns
    -------
    Dict with spearman_rho, n, p_significant (rho > 0 at rough significance level).
    """
    pairs = [
        (r["target_importance"], r["absolute_shift"])
        for r in rows
        if r["success"]
        and r["absolute_shift"] is not None
        and r["target_importance"] is not None
        and r["target_importance"] > 0  # exclude structural probes with 0 importance
    ]

    if len(pairs) < 5:
        return {"spearman_rho": None, "n": len(pairs)}

    importance_vals = [p[0] for p in pairs]
    shift_vals = [p[1] for p in pairs]

    rho = _spearman_correlation(importance_vals, shift_vals)

    return {
        "spearman_rho": round(rho, 4) if rho is not None else None,
        "n": len(pairs),
    }


def structural_sensitivity_ratio(rows: list[dict]) -> dict:
    """Mean shift of high-importance probes / mean shift of low-importance probes.

    SSR > 1 = appropriately calibrated to importance.
    SSR ~ 1 = undifferentiated (treats all probes equally).

    High-importance: node_negate_high, node_strengthen, edge_negate_critical
    Low-importance: node_negate_low, edge_negate_peripheral, irrelevant
    """
    high_types = {"node_negate_high", "node_strengthen", "edge_negate_critical"}
    low_types = {"node_negate_low", "edge_negate_peripheral", "irrelevant"}

    high_shifts = [
        r["absolute_shift"] for r in rows
        if r["success"] and r["absolute_shift"] is not None
        and r.get("probe_type") in high_types
    ]
    low_shifts = [
        r["absolute_shift"] for r in rows
        if r["success"] and r["absolute_shift"] is not None
        and r.get("probe_type") in low_types
    ]

    if not high_shifts or not low_shifts:
        return {
            "ssr": None,
            "mean_shift_high": _safe_mean(high_shifts),
            "mean_shift_low": _safe_mean(low_shifts),
            "n_high": len(high_shifts),
            "n_low": len(low_shifts),
        }

    mean_high = sum(high_shifts) / len(high_shifts)
    mean_low = sum(low_shifts) / len(low_shifts)
    ssr = mean_high / mean_low if mean_low > 0.001 else None

    return {
        "ssr": round(ssr, 4) if ssr is not None else None,
        "mean_shift_high": round(mean_high, 4),
        "mean_shift_low": round(mean_low, 4),
        "n_high": len(high_shifts),
        "n_low": len(low_shifts),
    }


def sensitivity_by_probe_category(rows: list[dict]) -> dict:
    """Mean shift grouped by probe category (node / edge / structural).

    Returns
    -------
    Dict mapping category -> {n, mean_shift, median_shift}.
    """
    groups = defaultdict(list)
    for r in rows:
        if r["success"] and r["absolute_shift"] is not None:
            cat = r.get("probe_category", "unknown")
            groups[cat].append(r["absolute_shift"])

    result = {}
    for cat, shifts in sorted(groups.items()):
        shifts_sorted = sorted(shifts)
        n = len(shifts)
        median = shifts_sorted[n // 2] if n % 2 == 1 else (shifts_sorted[n // 2 - 1] + shifts_sorted[n // 2]) / 2
        result[cat] = {
            "n": n,
            "mean_shift": round(sum(shifts) / n, 4),
            "median_shift": round(median, 4),
        }
    return result


def sensitivity_by_probe_type(rows: list[dict]) -> dict:
    """Mean shift grouped by specific probe type.

    Returns
    -------
    Dict mapping probe_type -> {n, mean_shift, median_shift}.
    """
    groups = defaultdict(list)
    for r in rows:
        if r["success"] and r["absolute_shift"] is not None:
            pt = r.get("probe_type", "unknown")
            groups[pt].append(r["absolute_shift"])

    result = {}
    for pt, shifts in sorted(groups.items()):
        shifts_sorted = sorted(shifts)
        n = len(shifts)
        median = shifts_sorted[n // 2] if n % 2 == 1 else (shifts_sorted[n // 2 - 1] + shifts_sorted[n // 2]) / 2
        result[pt] = {
            "n": n,
            "mean_shift": round(sum(shifts) / n, 4),
            "median_shift": round(median, 4),
        }
    return result


def critical_path_premium(rows: list[dict]) -> dict:
    """Mean shift for on-path targets minus mean shift for off-path targets.

    Positive = path position matters (on-path probes cause larger shifts).

    Returns
    -------
    Dict with premium, mean_shift_on_path, mean_shift_off_path, n_on, n_off.
    """
    on_path = [
        r["absolute_shift"] for r in rows
        if r["success"] and r["absolute_shift"] is not None
        and r.get("target_on_critical_path") is True
    ]
    off_path = [
        r["absolute_shift"] for r in rows
        if r["success"] and r["absolute_shift"] is not None
        and r.get("target_on_critical_path") is False
    ]

    if not on_path or not off_path:
        return {
            "premium": None,
            "mean_shift_on_path": _safe_mean(on_path),
            "mean_shift_off_path": _safe_mean(off_path),
            "n_on": len(on_path),
            "n_off": len(off_path),
        }

    mean_on = sum(on_path) / len(on_path)
    mean_off = sum(off_path) / len(off_path)

    return {
        "premium": round(mean_on - mean_off, 4),
        "mean_shift_on_path": round(mean_on, 4),
        "mean_shift_off_path": round(mean_off, 4),
        "n_on": len(on_path),
        "n_off": len(off_path),
    }


def spurious_acceptance_rate(rows: list[dict]) -> dict:
    """Fraction of edge_spurious + missing_node probes where |shift| >= 0.05.

    High rate = model is vulnerable to accepting spurious causal structure.

    Returns
    -------
    Dict with acceptance_rate, n_accepted, n_total.
    """
    spurious_types = {"edge_spurious", "missing_node"}
    spurious_rows = [
        r for r in rows
        if r["success"] and r["absolute_shift"] is not None
        and r.get("probe_type") in spurious_types
    ]

    if not spurious_rows:
        return {"acceptance_rate": None, "n_accepted": 0, "n_total": 0}

    accepted = sum(1 for r in spurious_rows if r["absolute_shift"] >= 0.05)

    return {
        "acceptance_rate": round(accepted / len(spurious_rows), 4),
        "n_accepted": accepted,
        "n_total": len(spurious_rows),
    }


def asymmetry_index(rows: list[dict]) -> dict:
    """Mean shift for negation / mean shift for strengthening on same-importance targets.

    > 1 = negativity bias (negations cause larger shifts).
    < 1 = confirmation bias (strengthening causes larger shifts).

    Compares node_negate_high vs node_strengthen (both target high-importance nodes).

    Returns
    -------
    Dict with index, mean_shift_negate, mean_shift_strengthen, n_negate, n_strengthen.
    """
    negate_shifts = [
        r["absolute_shift"] for r in rows
        if r["success"] and r["absolute_shift"] is not None
        and r.get("probe_type") == "node_negate_high"
    ]
    strengthen_shifts = [
        r["absolute_shift"] for r in rows
        if r["success"] and r["absolute_shift"] is not None
        and r.get("probe_type") == "node_strengthen"
    ]

    if not negate_shifts or not strengthen_shifts:
        return {
            "index": None,
            "mean_shift_negate": _safe_mean(negate_shifts),
            "mean_shift_strengthen": _safe_mean(strengthen_shifts),
            "n_negate": len(negate_shifts),
            "n_strengthen": len(strengthen_shifts),
        }

    mean_neg = sum(negate_shifts) / len(negate_shifts)
    mean_str = sum(strengthen_shifts) / len(strengthen_shifts)
    idx = mean_neg / mean_str if mean_str > 0.001 else None

    return {
        "index": round(idx, 4) if idx is not None else None,
        "mean_shift_negate": round(mean_neg, 4),
        "mean_shift_strengthen": round(mean_str, 4),
        "n_negate": len(negate_shifts),
        "n_strengthen": len(strengthen_shifts),
    }


# =============================================================================
# HELPERS
# =============================================================================

def _safe_mean(vals: list) -> float | None:
    """Mean of a list, or None if empty."""
    if not vals:
        return None
    return round(sum(vals) / len(vals), 4)


# =============================================================================
# MAIN ANALYSIS RUNNER
# =============================================================================

def run_causal_analysis(*dirs: str):
    """Run full causal analysis on one or two output directories."""
    all_rows = {}

    for d in dirs:
        d_path = Path(d)
        csv_path = d_path / "sensitivity_results.csv"
        if not csv_path.exists():
            print(f"[ERROR] {csv_path} not found")
            continue

        if not is_causal_csv(csv_path):
            print(f"[WARNING] {csv_path} does not appear to be causal mode output. "
                  f"Use analysis.py for reasons-mode results.")
            continue

        rows = load_causal_results(csv_path)
        if not rows:
            print(f"[WARNING] No data in {csv_path}")
            continue

        condition = rows[0].get("condition", d_path.name)
        all_rows[condition] = rows

        print(f"\n{'='*60}")
        print(f"CAUSAL ANALYSIS: {condition.upper()} ({len(rows)} probe results)")
        print(f"{'='*60}")

        # --- Base metrics ---
        anchoring = compute_anchoring_metrics(rows)
        print(f"\n--- Anchoring ---")
        print(f"  N probes: {anchoring['n']}")
        print(f"  Mean absolute shift: {anchoring['mean_absolute_shift']}")
        print(f"  Median absolute shift: {anchoring['median_absolute_shift']}")
        print(f"  % no change (<1%): {anchoring['pct_no_change']}%")
        print(f"  % small shift (<5%): {anchoring['pct_small_shift']}%")

        # --- By probe type ---
        by_type = sensitivity_by_probe_type(rows)
        print(f"\n--- Sensitivity by Probe Type ---")
        for pt, stats in by_type.items():
            print(f"  {pt:25s}: mean={stats['mean_shift']:.4f}, "
                  f"median={stats['median_shift']:.4f}, n={stats['n']}")

        # --- By probe category ---
        by_cat = sensitivity_by_probe_category(rows)
        print(f"\n--- Sensitivity by Probe Category ---")
        for cat, stats in by_cat.items():
            print(f"  {cat:12s}: mean={stats['mean_shift']:.4f}, "
                  f"median={stats['median_shift']:.4f}, n={stats['n']}")

        # --- Network-specific metrics ---
        print(f"\n--- Network-Specific Metrics ---")

        # 1. Importance-sensitivity correlation
        isc = importance_sensitivity_correlation(rows)
        print(f"\n  Importance-Sensitivity Correlation:")
        print(f"    Spearman rho: {isc['spearman_rho']}")
        print(f"    N pairs: {isc['n']}")

        # 2. Structural sensitivity ratio
        ssr = structural_sensitivity_ratio(rows)
        print(f"\n  Structural Sensitivity Ratio (SSR):")
        print(f"    SSR: {ssr['ssr']} (>1 = calibrated to importance)")
        print(f"    Mean shift (high-importance): {ssr['mean_shift_high']} (n={ssr['n_high']})")
        print(f"    Mean shift (low-importance): {ssr['mean_shift_low']} (n={ssr['n_low']})")

        # 3. Critical path premium
        cpp = critical_path_premium(rows)
        print(f"\n  Critical Path Premium:")
        print(f"    Premium: {cpp['premium']} (>0 = path position matters)")
        print(f"    Mean shift (on-path): {cpp['mean_shift_on_path']} (n={cpp['n_on']})")
        print(f"    Mean shift (off-path): {cpp['mean_shift_off_path']} (n={cpp['n_off']})")

        # 4. Spurious acceptance rate
        fnar = spurious_acceptance_rate(rows)
        print(f"\n  Spurious Acceptance Rate:")
        print(f"    Rate: {fnar['acceptance_rate']} ({fnar['n_accepted']}/{fnar['n_total']} spurious probes accepted)")

        # 5. Asymmetry index
        ai = asymmetry_index(rows)
        print(f"\n  Asymmetry Index (negation vs strengthening):")
        print(f"    Index: {ai['index']} (>1 = negativity bias, <1 = confirmation bias)")
        print(f"    Mean shift (negate): {ai['mean_shift_negate']} (n={ai['n_negate']})")
        print(f"    Mean shift (strengthen): {ai['mean_shift_strengthen']} (n={ai['n_strengthen']})")

        # Drift
        drift = compute_consistency_metrics(rows)
        print(f"\n  Conversational Drift:")
        print(f"    Mean Spearman rho: {drift['mean_spearman_rho']}")
        print(f"    N questions: {drift['n_questions']}")

        # Save summary
        summary = {
            "condition": condition,
            "mode": "causal",
            "n_probes": len(rows),
            "n_successful": sum(1 for r in rows if r["success"]),
            "anchoring": anchoring,
            "sensitivity_by_probe_type": by_type,
            "sensitivity_by_probe_category": by_cat,
            "importance_sensitivity_correlation": isc,
            "structural_sensitivity_ratio": ssr,
            "critical_path_premium": cpp,
            "spurious_acceptance_rate": fnar,
            "asymmetry_index": ai,
            "conversational_drift": drift,
        }
        summary_path = d_path / "experiment_summary.json"
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"\nSaved: {summary_path}")

    # Cross-condition comparison
    conditions = list(all_rows.keys())
    if len(conditions) >= 2 and "one-turn" in all_rows and "multi-turn" in all_rows:
        print(f"\n{'='*60}")
        print("CONDITION COMPARISON: One-Turn vs Multi-Turn (Causal)")
        print(f"{'='*60}")

        comparison = compare_conditions(all_rows["one-turn"], all_rows["multi-turn"])

        print(f"  N paired questions: {comparison.get('n_pairs', 0)}")
        print(f"  Mean shift (one-turn): {comparison.get('mean_shift_one_turn')}")
        print(f"  Mean shift (multi-turn): {comparison.get('mean_shift_multi_turn')}")
        print(f"  Mean difference: {comparison.get('mean_difference')}")
        print(f"  t-statistic: {comparison.get('t_statistic')}")
        print(f"  p-value: {comparison.get('p_value')}")
        print(f"  Cohen's d: {comparison.get('cohens_d')}")

        comp_path = Path(dirs[0]) / "condition_comparison.json"
        comp_path.write_text(json.dumps(comparison, indent=2), encoding="utf-8")
        print(f"\nSaved: {comp_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze causal network belief sensitivity results",
    )
    parser.add_argument(
        "dirs", nargs="+",
        help="One or two output directories to analyze (causal mode)",
    )
    args = parser.parse_args()
    run_causal_analysis(*args.dirs)


if __name__ == "__main__":
    main()
