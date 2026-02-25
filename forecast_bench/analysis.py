"""
Belief Sensitivity Analysis — Compute metrics from experiment results.

Reads sensitivity_results.csv and produces experiment_summary.json with:
1. Anchoring metrics (mean/median shift, % no-change, % small-shift)
2. Sensitivity by reason importance (high vs medium vs low)
3. Sensitivity by probe type (negation vs counterfactual vs weakening)
4. Conversational drift (Spearman correlation of probe order vs cumulative shift)
5. Condition comparison (paired t-test + Cohen's d)

Usage:
    python forecast_bench/analysis.py outputs/sensitivity/forecasting/one_turn
    python forecast_bench/analysis.py outputs/sensitivity/forecasting/one_turn outputs/sensitivity/forecasting/multi_turn
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path


def load_results(csv_path: Path) -> list[dict]:
    """Load sensitivity_results.csv into a list of dicts."""
    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Parse numeric fields
            for field in ("initial_probability", "updated_probability", "absolute_shift", "probe_index"):
                if row.get(field):
                    try:
                        row[field] = float(row[field])
                    except ValueError:
                        row[field] = None
                else:
                    row[field] = None
            row["success"] = str(row.get("success", "")).lower() == "true"
            rows.append(row)
    return rows


def compute_anchoring_metrics(rows: list[dict]) -> dict:
    """Compute anchoring metrics from successful probe results.

    Returns
    -------
    Dict with mean_absolute_shift, median_absolute_shift, pct_no_change, pct_small_shift.
    """
    shifts = [r["absolute_shift"] for r in rows if r["success"] and r["absolute_shift"] is not None]

    if not shifts:
        return {"n": 0, "mean_absolute_shift": None, "median_absolute_shift": None,
                "pct_no_change": None, "pct_small_shift": None}

    shifts_sorted = sorted(shifts)
    n = len(shifts)
    mean_shift = sum(shifts) / n
    median_shift = shifts_sorted[n // 2] if n % 2 == 1 else (shifts_sorted[n // 2 - 1] + shifts_sorted[n // 2]) / 2

    no_change = sum(1 for s in shifts if s < 0.01)
    small_shift = sum(1 for s in shifts if s < 0.05)

    return {
        "n": n,
        "mean_absolute_shift": round(mean_shift, 4),
        "median_absolute_shift": round(median_shift, 4),
        "pct_no_change": round(no_change / n * 100, 1),
        "pct_small_shift": round(small_shift / n * 100, 1),
    }


def sensitivity_by_importance(rows: list[dict]) -> dict:
    """Mean absolute shift grouped by reason importance level.

    Returns
    -------
    Dict mapping importance -> {n, mean_shift, median_shift}.
    """
    groups = defaultdict(list)
    for r in rows:
        if r["success"] and r["absolute_shift"] is not None:
            imp = r.get("target_reason_importance", "unknown")
            groups[imp].append(r["absolute_shift"])

    result = {}
    for imp, shifts in sorted(groups.items()):
        shifts_sorted = sorted(shifts)
        n = len(shifts)
        median = shifts_sorted[n // 2] if n % 2 == 1 else (shifts_sorted[n // 2 - 1] + shifts_sorted[n // 2]) / 2
        result[imp] = {
            "n": n,
            "mean_shift": round(sum(shifts) / n, 4),
            "median_shift": round(median, 4),
        }
    return result


def sensitivity_by_probe_type(rows: list[dict]) -> dict:
    """Mean absolute shift grouped by probe type.

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


def compute_consistency_metrics(rows: list[dict]) -> dict:
    """Conversational drift: Spearman correlation of probe order vs cumulative shift.

    Computed per question, then averaged.

    Returns
    -------
    Dict with mean_spearman_rho, n_questions.
    """
    # Group by question
    questions = defaultdict(list)
    for r in rows:
        if r["success"] and r["absolute_shift"] is not None and r.get("probe_index") is not None:
            questions[r["question_id"]].append(r)

    rhos = []
    for qid, q_rows in questions.items():
        q_rows.sort(key=lambda x: x["probe_index"])
        if len(q_rows) < 3:
            continue

        # Cumulative shift
        cumulative = []
        total = 0.0
        for r in q_rows:
            total += r["absolute_shift"]
            cumulative.append(total)

        orders = list(range(len(q_rows)))
        rho = _spearman_correlation(orders, cumulative)
        if rho is not None:
            rhos.append(rho)

    if not rhos:
        return {"mean_spearman_rho": None, "n_questions": 0}

    return {
        "mean_spearman_rho": round(sum(rhos) / len(rhos), 4),
        "n_questions": len(rhos),
    }


def compare_conditions(
    one_turn_rows: list[dict],
    multi_turn_rows: list[dict],
) -> dict:
    """Compare mean absolute shifts between conditions using paired t-test + Cohen's d.

    Pairs are matched by question_id.

    Returns
    -------
    Dict with t_statistic, p_value, cohens_d, n_pairs,
    mean_shift_one_turn, mean_shift_multi_turn.
    """
    # Compute mean shift per question for each condition
    def _question_means(rows):
        groups = defaultdict(list)
        for r in rows:
            if r["success"] and r["absolute_shift"] is not None:
                groups[r["question_id"]].append(r["absolute_shift"])
        return {qid: sum(s) / len(s) for qid, s in groups.items()}

    ind_means = _question_means(one_turn_rows)
    conv_means = _question_means(multi_turn_rows)

    # Paired: only questions present in both
    shared_ids = sorted(set(ind_means) & set(conv_means))
    if len(shared_ids) < 3:
        return {"error": f"Too few paired questions ({len(shared_ids)})", "n_pairs": len(shared_ids)}

    ind_vals = [ind_means[qid] for qid in shared_ids]
    conv_vals = [conv_means[qid] for qid in shared_ids]

    # Paired t-test
    diffs = [c - i for c, i in zip(conv_vals, ind_vals)]
    n = len(diffs)
    mean_diff = sum(diffs) / n
    var_diff = sum((d - mean_diff) ** 2 for d in diffs) / (n - 1)
    se_diff = math.sqrt(var_diff / n) if var_diff > 0 else 1e-10

    t_stat = mean_diff / se_diff

    # Two-tailed p-value approximation (using normal for n >= 30, else conservative)
    p_value = _t_to_p(t_stat, n - 1)

    # Cohen's d (paired)
    sd_diff = math.sqrt(var_diff) if var_diff > 0 else 1e-10
    cohens_d = mean_diff / sd_diff

    return {
        "n_pairs": n,
        "mean_shift_one_turn": round(sum(ind_vals) / len(ind_vals), 4),
        "mean_shift_multi_turn": round(sum(conv_vals) / len(conv_vals), 4),
        "mean_difference": round(mean_diff, 4),
        "t_statistic": round(t_stat, 4),
        "p_value": round(p_value, 4),
        "cohens_d": round(cohens_d, 4),
    }


# =============================================================================
# STATISTICAL HELPERS
# =============================================================================

def _spearman_correlation(x: list, y: list) -> float | None:
    """Compute Spearman rank correlation between two lists."""
    n = len(x)
    if n < 3:
        return None

    def _rank(vals):
        indexed = sorted(enumerate(vals), key=lambda t: t[1])
        ranks = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j < n - 1 and indexed[j + 1][1] == indexed[j][1]:
                j += 1
            avg_rank = (i + j) / 2.0 + 1  # 1-based
            for k in range(i, j + 1):
                ranks[indexed[k][0]] = avg_rank
            i = j + 1
        return ranks

    rx = _rank(x)
    ry = _rank(y)

    # Pearson on ranks
    mean_rx = sum(rx) / n
    mean_ry = sum(ry) / n

    cov = sum((a - mean_rx) * (b - mean_ry) for a, b in zip(rx, ry))
    std_x = math.sqrt(sum((a - mean_rx) ** 2 for a in rx))
    std_y = math.sqrt(sum((b - mean_ry) ** 2 for b in ry))

    if std_x == 0 or std_y == 0:
        return None

    return cov / (std_x * std_y)


def _t_to_p(t: float, df: int) -> float:
    """Approximate two-tailed p-value from t-statistic.

    Uses the normal approximation for df >= 30; for smaller df, uses a
    rough beta-function-based approximation.
    """
    t_abs = abs(t)

    if df >= 30:
        # Normal approximation
        z = t_abs
        # Rational approximation to the normal CDF tail
        p_one_tail = 0.5 * math.erfc(z / math.sqrt(2))
        return min(1.0, 2 * p_one_tail)

    # Small-sample approximation using the regularized incomplete beta function
    x = df / (df + t_abs ** 2)
    # Approximate I_x(df/2, 0.5) using a series expansion
    a = df / 2.0
    b = 0.5
    p = _regularized_incomplete_beta(x, a, b)
    return min(1.0, p)


def _regularized_incomplete_beta(x: float, a: float, b: float, n_terms: int = 200) -> float:
    """Approximate the regularized incomplete beta function I_x(a, b).

    Uses a simple series expansion. Sufficient for the t-test p-value approximation.
    """
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0

    # Use the continued fraction representation for better convergence
    # For small x, compute directly
    log_beta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    front = math.exp(a * math.log(x) + b * math.log(1 - x) - log_beta) / a

    # Series expansion
    total = 1.0
    term = 1.0
    for n in range(1, n_terms):
        term *= x * (n - b) / (n * (a + n)) if (a + n) != 0 else 0
        total += term
        if abs(term) < 1e-12:
            break

    return min(1.0, front * total)


# =============================================================================
# MAIN ANALYSIS RUNNER
# =============================================================================

def run_analysis(*dirs: str):
    """Run full analysis on one or two output directories.

    If two directories are given, also runs the condition comparison.
    """
    all_rows = {}

    for d in dirs:
        d_path = Path(d)
        csv_path = d_path / "sensitivity_results.csv"
        if not csv_path.exists():
            print(f"[ERROR] {csv_path} not found")
            continue

        rows = load_results(csv_path)
        if not rows:
            print(f"[WARNING] No data in {csv_path}")
            continue

        condition = rows[0].get("condition", d_path.name)
        all_rows[condition] = rows

        print(f"\n{'='*60}")
        print(f"ANALYSIS: {condition.upper()} ({len(rows)} probe results)")
        print(f"{'='*60}")

        # Anchoring
        anchoring = compute_anchoring_metrics(rows)
        print(f"\n--- Anchoring ---")
        print(f"  N probes: {anchoring['n']}")
        print(f"  Mean absolute shift: {anchoring['mean_absolute_shift']}")
        print(f"  Median absolute shift: {anchoring['median_absolute_shift']}")
        print(f"  % no change (<1%): {anchoring['pct_no_change']}%")
        print(f"  % small shift (<5%): {anchoring['pct_small_shift']}%")

        # By importance
        by_imp = sensitivity_by_importance(rows)
        print(f"\n--- Sensitivity by Importance ---")
        for imp, stats in by_imp.items():
            print(f"  {imp:8s}: mean={stats['mean_shift']:.4f}, "
                  f"median={stats['median_shift']:.4f}, n={stats['n']}")

        # By probe type
        by_type = sensitivity_by_probe_type(rows)
        print(f"\n--- Sensitivity by Probe Type ---")
        for pt, stats in by_type.items():
            print(f"  {pt:15s}: mean={stats['mean_shift']:.4f}, "
                  f"median={stats['median_shift']:.4f}, n={stats['n']}")

        # Drift
        drift = compute_consistency_metrics(rows)
        print(f"\n--- Conversational Drift ---")
        print(f"  Mean Spearman rho (probe order vs cumulative shift): {drift['mean_spearman_rho']}")
        print(f"  N questions: {drift['n_questions']}")

        # Save per-condition summary
        summary = {
            "condition": condition,
            "n_probes": len(rows),
            "n_successful": sum(1 for r in rows if r["success"]),
            "anchoring": anchoring,
            "sensitivity_by_importance": by_imp,
            "sensitivity_by_probe_type": by_type,
            "conversational_drift": drift,
        }
        summary_path = d_path / "experiment_summary.json"
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"\nSaved: {summary_path}")

    # Cross-condition comparison
    conditions = list(all_rows.keys())
    if len(conditions) >= 2 and "one-turn" in all_rows and "multi-turn" in all_rows:
        print(f"\n{'='*60}")
        print("CONDITION COMPARISON: One-Turn vs Multi-Turn")
        print(f"{'='*60}")

        comparison = compare_conditions(all_rows["one-turn"], all_rows["multi-turn"])

        print(f"  N paired questions: {comparison.get('n_pairs', 0)}")
        print(f"  Mean shift (one-turn): {comparison.get('mean_shift_one_turn')}")
        print(f"  Mean shift (multi-turn): {comparison.get('mean_shift_multi_turn')}")
        print(f"  Mean difference: {comparison.get('mean_difference')}")
        print(f"  t-statistic: {comparison.get('t_statistic')}")
        print(f"  p-value: {comparison.get('p_value')}")
        print(f"  Cohen's d: {comparison.get('cohens_d')}")

        # Save comparison
        comp_path = Path(dirs[0]) / "condition_comparison.json"
        comp_path.write_text(json.dumps(comparison, indent=2), encoding="utf-8")
        print(f"\nSaved: {comp_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze belief sensitivity experiment results",
    )
    parser.add_argument(
        "dirs", nargs="+",
        help="One or two output directories to analyze",
    )
    args = parser.parse_args()
    run_analysis(*args.dirs)


if __name__ == "__main__":
    main()
