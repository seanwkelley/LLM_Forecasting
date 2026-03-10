"""
Comprehensive Belief Sensitivity Analysis — Full paper analysis suite.

Analyses:
 1. Graph Quality Assessment
 2. Shift Directionality
 3. Test-Retest Reliability (requires two runs of same questions)
 4. Alternative Importance Metrics Comparison
 5. Graph Structure Controls (partial correlations)
 6. Question-Level Random Effects (variance decomposition)
 7. Dose-Response (continuous importance vs shift)
 8. Formal Null Test (irrelevant probes as null)
 9. Edge Probe Analysis
10. Dependency Structure (upstream vs downstream shifts)
11. Probe Faithfulness Sampling (for human review)
12. Domain Stratification (prediction market vs economic vs events)
13. Within-Question Consistency (per-question Kendall's tau)
14. Mechanism Text Quality (NLP features of edge mechanisms vs shift)
14b. Ground Truth Calibration (Brier scores vs ForecastBench freeze values)
15. Probe Text Assertiveness Control (SSR confound check)
15b. Multiple Comparisons Correction (Benjamini-Hochberg FDR)
16. Reasoning Coherence (does stated reasoning match actual shift?)
17. Cross-Model Comparison (requires multiple model runs)
18. Cross-Model Graph Structure Comparison (requires multiple model runs)

Usage:
    # Full analysis on one run
    python -m forecast_bench.analysis_full outputs/sensitivity/causal/70b_one_turn

    # Cross-model comparison
    python -m forecast_bench.analysis_full outputs/sensitivity/causal/70b_one_turn outputs/sensitivity/causal/llama_one_turn

    # Test-retest (two runs of same model on same questions)
    python -m forecast_bench.analysis_full outputs/sensitivity/causal/70b_one_turn --retest outputs/sensitivity/causal/70b_one_turn_run2
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from forecast_bench.analysis_causal import (
    load_causal_results,
    compute_anchoring_metrics,
    compute_consistency_metrics,
    compare_conditions,
    importance_sensitivity_correlation,
    structural_sensitivity_ratio,
    sensitivity_by_probe_category,
    sensitivity_by_probe_type,
    critical_path_premium,
    spurious_acceptance_rate,
    asymmetry_index,
    _spearman_correlation,
    _t_to_p,
    _safe_mean,
)


# =============================================================================
# DATA LOADING
# =============================================================================

def load_question_jsons(output_dir: Path) -> dict[str, dict]:
    """Load all per-question JSON result files."""
    q_dir = output_dir / "question_results"
    if not q_dir.exists():
        return {}

    results = {}
    for p in sorted(q_dir.glob("q_*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            qid = data.get("question_id", p.stem.replace("q_", ""))
            results[qid] = data
        except (json.JSONDecodeError, KeyError):
            continue
    return results


def _median(vals: list[float]) -> float:
    """Compute median of a sorted or unsorted list."""
    s = sorted(vals)
    n = len(s)
    if n == 0:
        return 0.0
    return s[n // 2] if n % 2 == 1 else (s[n // 2 - 1] + s[n // 2]) / 2


def _bootstrap_ci(
    vals: list[float],
    stat_fn=None,
    n_boot: int = 2000,
    ci: float = 0.95,
    seed: int = 42,
) -> dict:
    """Bootstrap confidence interval for a statistic."""
    if stat_fn is None:
        stat_fn = lambda v: sum(v) / len(v) if v else 0.0

    if len(vals) < 3:
        observed = stat_fn(vals) if vals else None
        return {"observed": observed, "ci_lower": None, "ci_upper": None, "n": len(vals)}

    rng = random.Random(seed)
    observed = stat_fn(vals)
    boot_stats = []
    n = len(vals)

    for _ in range(n_boot):
        sample = [vals[rng.randint(0, n - 1)] for _ in range(n)]
        boot_stats.append(stat_fn(sample))

    boot_stats.sort()
    alpha = (1 - ci) / 2
    lo_idx = int(alpha * n_boot)
    hi_idx = int((1 - alpha) * n_boot) - 1

    return {
        "observed": round(observed, 4),
        "ci_lower": round(boot_stats[lo_idx], 4),
        "ci_upper": round(boot_stats[hi_idx], 4),
        "n": n,
    }


def _paired_t_test(vals_a: list[float], vals_b: list[float]) -> dict:
    """Paired t-test between two equal-length lists."""
    n = len(vals_a)
    if n < 3 or n != len(vals_b):
        return {"t": None, "p": None, "n": n, "mean_diff": None}

    diffs = [a - b for a, b in zip(vals_a, vals_b)]
    mean_d = sum(diffs) / n
    var_d = sum((d - mean_d) ** 2 for d in diffs) / (n - 1)
    se_d = math.sqrt(var_d / n) if var_d > 0 else 1e-10

    t = mean_d / se_d
    p = _t_to_p(t, n - 1)

    return {
        "t": round(t, 4),
        "p": round(p, 4),
        "n": n,
        "mean_diff": round(mean_d, 4),
    }


def _linear_regression(x: list[float], y: list[float]) -> dict:
    """Simple OLS regression: y = a + b*x."""
    n = len(x)
    if n < 3:
        return {"slope": None, "intercept": None, "r_squared": None, "n": n}

    mean_x = sum(x) / n
    mean_y = sum(y) / n

    ss_xy = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
    ss_xx = sum((xi - mean_x) ** 2 for xi in x)
    ss_yy = sum((yi - mean_y) ** 2 for yi in y)

    if ss_xx == 0:
        return {"slope": None, "intercept": mean_y, "r_squared": None, "n": n}

    slope = ss_xy / ss_xx
    intercept = mean_y - slope * mean_x
    r_squared = (ss_xy ** 2) / (ss_xx * ss_yy) if ss_yy > 0 else 0.0

    # t-test for slope significance
    residuals = [yi - (intercept + slope * xi) for xi, yi in zip(x, y)]
    mse = sum(r ** 2 for r in residuals) / (n - 2) if n > 2 else 0
    se_slope = math.sqrt(mse / ss_xx) if ss_xx > 0 and mse > 0 else 1e-10
    t_slope = slope / se_slope
    p_slope = _t_to_p(t_slope, n - 2) if n > 2 else 1.0

    return {
        "slope": round(slope, 6),
        "intercept": round(intercept, 6),
        "r_squared": round(r_squared, 4),
        "t_slope": round(t_slope, 4),
        "p_slope": round(p_slope, 4),
        "n": n,
    }


# =============================================================================
# 1. GRAPH QUALITY ASSESSMENT
# =============================================================================

def analyze_graph_quality(question_data: dict[str, dict]) -> dict:
    """Assess quality and consistency of LLM-generated causal graphs.

    Reports distributions of graph properties and flags degenerate cases.
    """
    stats = {
        "n_questions": len(question_data),
        "node_counts": [],
        "edge_counts": [],
        "densities": [],
        "is_dag": [],
        "n_degenerate": 0,
        "degenerate_questions": [],
    }

    for qid, qdata in question_data.items():
        nodes = qdata.get("nodes", [])
        edges = qdata.get("edges", [])
        net = qdata.get("network_analysis", {})

        n_nodes = len(nodes)
        n_edges = len(edges)
        density = net.get("density", 0.0)
        is_dag = net.get("is_dag", True)

        stats["node_counts"].append(n_nodes)
        stats["edge_counts"].append(n_edges)
        stats["densities"].append(density)
        stats["is_dag"].append(is_dag)

        # Flag degenerate cases
        factor_nodes = [n for n in nodes if n.get("role") != "outcome"]
        if len(factor_nodes) < 2 or n_edges < 2:
            stats["n_degenerate"] += 1
            stats["degenerate_questions"].append(qid)

    if not stats["node_counts"]:
        return stats

    stats["node_count_summary"] = {
        "mean": round(sum(stats["node_counts"]) / len(stats["node_counts"]), 2),
        "median": _median(stats["node_counts"]),
        "min": min(stats["node_counts"]),
        "max": max(stats["node_counts"]),
    }
    stats["edge_count_summary"] = {
        "mean": round(sum(stats["edge_counts"]) / len(stats["edge_counts"]), 2),
        "median": _median(stats["edge_counts"]),
        "min": min(stats["edge_counts"]),
        "max": max(stats["edge_counts"]),
    }
    stats["density_summary"] = {
        "mean": round(sum(stats["densities"]) / len(stats["densities"]), 4),
        "median": round(_median(stats["densities"]), 4),
        "min": round(min(stats["densities"]), 4),
        "max": round(max(stats["densities"]), 4),
    }
    stats["pct_dag"] = round(
        sum(1 for d in stats["is_dag"] if d) / len(stats["is_dag"]) * 100, 1
    )
    stats["pct_degenerate"] = round(
        stats["n_degenerate"] / len(question_data) * 100, 1
    )

    # Clean up raw lists for JSON serialization
    del stats["node_counts"]
    del stats["edge_counts"]
    del stats["densities"]
    del stats["is_dag"]

    return stats


# =============================================================================
# 2. SHIFT DIRECTIONALITY
# =============================================================================

def analyze_shift_directionality(rows: list[dict]) -> dict:
    """Analyze whether probability shifts go in the expected direction.

    Negation probes should decrease confidence (shift toward 0.5).
    Strengthening probes should increase confidence (shift away from 0.5).
    Irrelevant probes should not shift systematically.
    """
    results = {}

    # Group by probe type
    type_groups = defaultdict(list)
    for r in rows:
        if not r["success"] or r.get("updated_probability") is None:
            continue
        pt = r.get("probe_type", "")
        initial = r.get("initial_probability")
        updated = r.get("updated_probability")
        if initial is None or updated is None:
            continue

        signed_shift = updated - initial
        # "Toward uncertainty" = toward 0.5
        initial_confidence = abs(initial - 0.5)
        updated_confidence = abs(updated - 0.5)
        confidence_change = updated_confidence - initial_confidence

        type_groups[pt].append({
            "signed_shift": signed_shift,
            "confidence_change": confidence_change,
            "initial": initial,
            "updated": updated,
        })

    # Expected directions
    negation_types = {
        "node_negate_high", "node_negate_medium", "node_negate_low",
        "edge_negate_critical", "edge_negate_peripheral",
    }
    strengthen_types = {"node_strengthen"}
    control_types = {"irrelevant"}

    # Negation probes: should decrease confidence (move toward 0.5)
    neg_data = []
    for pt in negation_types:
        neg_data.extend(type_groups.get(pt, []))

    if neg_data:
        n_decreased_confidence = sum(1 for d in neg_data if d["confidence_change"] < 0)
        results["negation"] = {
            "n": len(neg_data),
            "pct_decreased_confidence": round(n_decreased_confidence / len(neg_data) * 100, 1),
            "mean_confidence_change": round(
                sum(d["confidence_change"] for d in neg_data) / len(neg_data), 4
            ),
            "mean_signed_shift": round(
                sum(d["signed_shift"] for d in neg_data) / len(neg_data), 4
            ),
        }

    # Strengthening probes: should increase confidence (move away from 0.5)
    str_data = []
    for pt in strengthen_types:
        str_data.extend(type_groups.get(pt, []))

    if str_data:
        n_increased_confidence = sum(1 for d in str_data if d["confidence_change"] > 0)
        results["strengthening"] = {
            "n": len(str_data),
            "pct_increased_confidence": round(n_increased_confidence / len(str_data) * 100, 1),
            "mean_confidence_change": round(
                sum(d["confidence_change"] for d in str_data) / len(str_data), 4
            ),
            "mean_signed_shift": round(
                sum(d["signed_shift"] for d in str_data) / len(str_data), 4
            ),
        }

    # Irrelevant probes: should not shift systematically (mean signed shift ≈ 0)
    ctrl_data = []
    for pt in control_types:
        ctrl_data.extend(type_groups.get(pt, []))

    if ctrl_data:
        signed_shifts = [d["signed_shift"] for d in ctrl_data]
        mean_signed = sum(signed_shifts) / len(signed_shifts)
        # One-sample t-test against 0
        if len(signed_shifts) >= 3:
            var_s = sum((s - mean_signed) ** 2 for s in signed_shifts) / (len(signed_shifts) - 1)
            se_s = math.sqrt(var_s / len(signed_shifts)) if var_s > 0 else 1e-10
            t_stat = mean_signed / se_s
            p_val = _t_to_p(t_stat, len(signed_shifts) - 1)
        else:
            t_stat, p_val = None, None

        results["irrelevant_control"] = {
            "n": len(ctrl_data),
            "mean_signed_shift": round(mean_signed, 4),
            "t_vs_zero": round(t_stat, 4) if t_stat is not None else None,
            "p_vs_zero": round(p_val, 4) if p_val is not None else None,
            "interpretation": "unbiased" if (p_val and p_val > 0.05) else "systematic bias detected",
        }

    # Edge reversal: should shift in opposite direction from edge negation
    reversal_data = type_groups.get("edge_reverse", [])
    if reversal_data:
        results["edge_reversal"] = {
            "n": len(reversal_data),
            "mean_signed_shift": round(
                sum(d["signed_shift"] for d in reversal_data) / len(reversal_data), 4
            ),
            "mean_abs_shift": round(
                sum(abs(d["signed_shift"]) for d in reversal_data) / len(reversal_data), 4
            ),
        }

    return results


# =============================================================================
# 3. TEST-RETEST RELIABILITY
# =============================================================================

def analyze_test_retest(
    run1_questions: dict[str, dict],
    run2_questions: dict[str, dict],
) -> dict:
    """Compare two runs of the same questions for test-retest reliability.

    Computes ICC on initial probabilities and per-question mean shifts.
    Computes graph similarity (Jaccard on edges).
    """
    shared_ids = sorted(set(run1_questions) & set(run2_questions))
    if len(shared_ids) < 3:
        return {"error": f"Too few shared questions ({len(shared_ids)})", "n_shared": len(shared_ids)}

    # Initial probability ICC
    probs_1 = [run1_questions[qid]["initial_probability"] for qid in shared_ids]
    probs_2 = [run2_questions[qid]["initial_probability"] for qid in shared_ids]

    # Graph similarity (Jaccard on edges)
    jaccards = []
    for qid in shared_ids:
        edges_1 = {(e["from"], e["to"]) for e in run1_questions[qid].get("edges", [])}
        edges_2 = {(e["from"], e["to"]) for e in run2_questions[qid].get("edges", [])}
        if edges_1 or edges_2:
            jaccard = len(edges_1 & edges_2) / len(edges_1 | edges_2)
            jaccards.append(jaccard)

    # Node overlap (Jaccard on node IDs)
    node_jaccards = []
    for qid in shared_ids:
        nodes_1 = {n["id"] for n in run1_questions[qid].get("nodes", [])}
        nodes_2 = {n["id"] for n in run2_questions[qid].get("nodes", [])}
        if nodes_1 or nodes_2:
            node_jaccards.append(len(nodes_1 & nodes_2) / len(nodes_1 | nodes_2))

    # Per-question mean shift comparison
    def _question_mean_shifts(questions):
        result = {}
        for qid, qdata in questions.items():
            probe_results = qdata.get("probe_results", [])
            shifts = [
                r["absolute_shift"] for r in probe_results
                if r.get("success") and r.get("absolute_shift") is not None
            ]
            if shifts:
                result[qid] = sum(shifts) / len(shifts)
        return result

    shifts_1 = _question_mean_shifts(run1_questions)
    shifts_2 = _question_mean_shifts(run2_questions)
    shift_shared = sorted(set(shifts_1) & set(shifts_2))

    shift_vals_1 = [shifts_1[qid] for qid in shift_shared]
    shift_vals_2 = [shifts_2[qid] for qid in shift_shared]

    # ICC(2,1) approximation via Pearson on paired measurements
    prob_corr = _spearman_correlation(probs_1, probs_2)
    shift_corr = _spearman_correlation(shift_vals_1, shift_vals_2) if len(shift_shared) >= 3 else None

    return {
        "n_shared_questions": len(shared_ids),
        "initial_probability": {
            "correlation": round(prob_corr, 4) if prob_corr is not None else None,
            "mean_abs_diff": round(
                sum(abs(a - b) for a, b in zip(probs_1, probs_2)) / len(shared_ids), 4
            ),
        },
        "graph_similarity": {
            "mean_edge_jaccard": round(sum(jaccards) / len(jaccards), 4) if jaccards else None,
            "mean_node_jaccard": round(sum(node_jaccards) / len(node_jaccards), 4) if node_jaccards else None,
            "n_graphs": len(jaccards),
        },
        "mean_shift_reliability": {
            "correlation": round(shift_corr, 4) if shift_corr is not None else None,
            "n_questions": len(shift_shared),
        },
    }


# =============================================================================
# 4. ALTERNATIVE IMPORTANCE METRICS COMPARISON
# =============================================================================

def compare_importance_metrics(rows: list[dict], question_data: dict[str, dict]) -> dict:
    """Compare betweenness vs PageRank vs path_relevance vs degree as importance metrics.

    For each metric, compute:
    - Spearman correlation with |shift|
    - SSR (high vs low by that metric)
    """
    # Build lookup: (question_id, node_id) -> node metrics
    node_lookup: dict[tuple[str, str], dict] = {}
    for qid, qdata in question_data.items():
        net = qdata.get("network_analysis", {})
        for nm in net.get("node_metrics", []):
            node_lookup[(qid, nm["node_id"])] = nm

    # Collect node-level probes with all metrics
    records = []
    for r in rows:
        if not r["success"] or r.get("absolute_shift") is None:
            continue
        if r.get("probe_category") != "node":
            continue

        qid = r.get("question_id", "")
        target_id = r.get("target_id", "")
        nm = node_lookup.get((qid, target_id))
        if nm is None:
            continue

        records.append({
            "shift": r["absolute_shift"],
            "betweenness": nm.get("betweenness", 0),
            "pagerank": nm.get("pagerank", 0),
            "path_relevance": nm.get("path_relevance", 0),
            "out_degree": nm.get("out_degree", 0),
            "in_degree": nm.get("in_degree", 0),
        })

    if len(records) < 5:
        return {"error": "Too few node probe records", "n": len(records)}

    metrics = ["betweenness", "pagerank", "path_relevance", "out_degree"]
    results = {"n_records": len(records)}

    for metric in metrics:
        metric_vals = [r[metric] for r in records]
        shift_vals = [r["shift"] for r in records]

        # Spearman correlation
        rho = _spearman_correlation(metric_vals, shift_vals)

        # SSR: top third vs bottom third
        sorted_records = sorted(records, key=lambda r: r[metric], reverse=True)
        n_third = max(1, len(sorted_records) // 3)
        high_shifts = [r["shift"] for r in sorted_records[:n_third]]
        low_shifts = [r["shift"] for r in sorted_records[-n_third:]]

        mean_high = sum(high_shifts) / len(high_shifts) if high_shifts else 0
        mean_low = sum(low_shifts) / len(low_shifts) if low_shifts else 0
        ssr = mean_high / mean_low if mean_low > 0.001 else None

        results[metric] = {
            "spearman_rho": round(rho, 4) if rho is not None else None,
            "ssr": round(ssr, 4) if ssr is not None else None,
            "mean_shift_high": round(mean_high, 4),
            "mean_shift_low": round(mean_low, 4),
        }

    return results


# =============================================================================
# 5. GRAPH STRUCTURE CONTROLS
# =============================================================================

def analyze_graph_structure_controls(rows: list[dict]) -> dict:
    """Test whether graph structure confounds importance-sensitivity correlation.

    Stratifies by graph density and tests partial correlations.
    """
    # Group probes by question to get per-question graph stats
    question_groups = defaultdict(list)
    for r in rows:
        if r["success"] and r.get("absolute_shift") is not None:
            question_groups[r["question_id"]].append(r)

    # Per-question: mean shift, graph density, n_nodes
    q_stats = []
    for qid, q_rows in question_groups.items():
        density = q_rows[0].get("graph_density") if q_rows else None
        n_nodes = q_rows[0].get("n_nodes") if q_rows else None
        n_edges = q_rows[0].get("n_edges") if q_rows else None

        shifts = [r["absolute_shift"] for r in q_rows if r["absolute_shift"] is not None]
        if not shifts or density is None:
            continue

        q_stats.append({
            "qid": qid,
            "mean_shift": sum(shifts) / len(shifts),
            "density": density,
            "n_nodes": n_nodes,
            "n_edges": n_edges,
            "n_probes": len(shifts),
        })

    if len(q_stats) < 5:
        return {"error": "Too few questions for structure analysis", "n": len(q_stats)}

    # Correlation: graph density vs mean shift
    densities = [q["density"] for q in q_stats]
    mean_shifts = [q["mean_shift"] for q in q_stats]
    n_nodes_list = [q["n_nodes"] for q in q_stats if q["n_nodes"] is not None]
    n_nodes_shifts = [q["mean_shift"] for q in q_stats if q["n_nodes"] is not None]

    density_shift_rho = _spearman_correlation(densities, mean_shifts)
    nodes_shift_rho = _spearman_correlation(n_nodes_list, n_nodes_shifts) if len(n_nodes_list) >= 3 else None

    # Stratify by density: sparse (below median) vs dense (above median)
    median_density = _median(densities)
    sparse_shifts = [q["mean_shift"] for q in q_stats if q["density"] <= median_density]
    dense_shifts = [q["mean_shift"] for q in q_stats if q["density"] > median_density]

    # Per-question importance-sensitivity rho, stratified
    sparse_rhos = []
    dense_rhos = []
    for q in q_stats:
        q_rows = question_groups[q["qid"]]
        importances = [r["target_importance"] for r in q_rows
                       if r.get("target_importance") is not None and r["target_importance"] > 0]
        shifts = [r["absolute_shift"] for r in q_rows
                  if r.get("target_importance") is not None and r["target_importance"] > 0]
        if len(importances) >= 3:
            rho = _spearman_correlation(importances, shifts)
            if rho is not None:
                if q["density"] <= median_density:
                    sparse_rhos.append(rho)
                else:
                    dense_rhos.append(rho)

    return {
        "n_questions": len(q_stats),
        "density_shift_correlation": round(density_shift_rho, 4) if density_shift_rho is not None else None,
        "n_nodes_shift_correlation": round(nodes_shift_rho, 4) if nodes_shift_rho is not None else None,
        "stratified_by_density": {
            "median_density": round(median_density, 4),
            "sparse": {
                "n": len(sparse_shifts),
                "mean_shift": round(sum(sparse_shifts) / len(sparse_shifts), 4) if sparse_shifts else None,
                "mean_importance_rho": round(sum(sparse_rhos) / len(sparse_rhos), 4) if sparse_rhos else None,
                "n_rho": len(sparse_rhos),
            },
            "dense": {
                "n": len(dense_shifts),
                "mean_shift": round(sum(dense_shifts) / len(dense_shifts), 4) if dense_shifts else None,
                "mean_importance_rho": round(sum(dense_rhos) / len(dense_rhos), 4) if dense_rhos else None,
                "n_rho": len(dense_rhos),
            },
        },
    }


# =============================================================================
# 6. QUESTION-LEVEL RANDOM EFFECTS
# =============================================================================

def analyze_question_level_effects(rows: list[dict]) -> dict:
    """Variance decomposition: how much sensitivity variation is question-level vs residual.

    Reports per-question distributions of SSR, SAR, and importance-sensitivity rho.
    """
    # Group by question
    question_groups = defaultdict(list)
    for r in rows:
        if r["success"] and r.get("absolute_shift") is not None:
            question_groups[r["question_id"]].append(r)

    per_q_metrics = []
    per_q_shifts = []

    for qid, q_rows in question_groups.items():
        shifts = [r["absolute_shift"] for r in q_rows]
        per_q_shifts.append(sum(shifts) / len(shifts))

        # Per-question SSR
        ssr = structural_sensitivity_ratio(q_rows)
        # Per-question SAR
        sar = spurious_acceptance_rate(q_rows)
        # Per-question importance-sensitivity rho
        isc = importance_sensitivity_correlation(q_rows)

        per_q_metrics.append({
            "question_id": qid,
            "n_probes": len(q_rows),
            "mean_shift": round(sum(shifts) / len(shifts), 4),
            "ssr": ssr.get("ssr"),
            "sar": sar.get("acceptance_rate"),
            "importance_rho": isc.get("spearman_rho"),
            "initial_probability": q_rows[0].get("initial_probability"),
        })

    if len(per_q_metrics) < 3:
        return {"error": "Too few questions", "n": len(per_q_metrics)}

    # Variance decomposition on mean shifts
    grand_mean = sum(per_q_shifts) / len(per_q_shifts)
    between_var = sum((s - grand_mean) ** 2 for s in per_q_shifts) / (len(per_q_shifts) - 1)

    within_vars = []
    for qid, q_rows in question_groups.items():
        shifts = [r["absolute_shift"] for r in q_rows]
        q_mean = sum(shifts) / len(shifts)
        if len(shifts) > 1:
            within_vars.append(
                sum((s - q_mean) ** 2 for s in shifts) / (len(shifts) - 1)
            )
    within_var = sum(within_vars) / len(within_vars) if within_vars else 0

    total_var = between_var + within_var
    icc = between_var / total_var if total_var > 0 else 0

    # SSR distribution
    ssr_vals = [m["ssr"] for m in per_q_metrics if m["ssr"] is not None]
    sar_vals = [m["sar"] for m in per_q_metrics if m["sar"] is not None]
    rho_vals = [m["importance_rho"] for m in per_q_metrics if m["importance_rho"] is not None]

    # Initial confidence vs sensitivity
    conf_vals = [abs(m["initial_probability"] - 0.5) for m in per_q_metrics
                 if m["initial_probability"] is not None]
    shift_vals = [m["mean_shift"] for m in per_q_metrics
                  if m["initial_probability"] is not None]

    confidence_sensitivity_rho = _spearman_correlation(conf_vals, shift_vals) if len(conf_vals) >= 3 else None

    return {
        "n_questions": len(per_q_metrics),
        "variance_decomposition": {
            "between_question_var": round(between_var, 6),
            "within_question_var": round(within_var, 6),
            "icc": round(icc, 4),
            "interpretation": (
                "high question-level clustering" if icc > 0.3
                else "moderate question-level clustering" if icc > 0.1
                else "low question-level clustering"
            ),
        },
        "per_question_ssr": {
            "n": len(ssr_vals),
            "mean": round(sum(ssr_vals) / len(ssr_vals), 4) if ssr_vals else None,
            "median": round(_median(ssr_vals), 4) if ssr_vals else None,
            "pct_above_1": round(sum(1 for v in ssr_vals if v > 1) / len(ssr_vals) * 100, 1) if ssr_vals else None,
        },
        "per_question_sar": {
            "n": len(sar_vals),
            "mean": round(sum(sar_vals) / len(sar_vals), 4) if sar_vals else None,
            "median": round(_median(sar_vals), 4) if sar_vals else None,
        },
        "per_question_importance_rho": {
            "n": len(rho_vals),
            "mean": round(sum(rho_vals) / len(rho_vals), 4) if rho_vals else None,
            "median": round(_median(rho_vals), 4) if rho_vals else None,
            "pct_positive": round(
                sum(1 for v in rho_vals if v > 0) / len(rho_vals) * 100, 1
            ) if rho_vals else None,
        },
        "confidence_sensitivity": {
            "rho": round(confidence_sensitivity_rho, 4) if confidence_sensitivity_rho is not None else None,
            "interpretation": (
                "more confident forecasts are more/less sensitive"
                if confidence_sensitivity_rho is not None and abs(confidence_sensitivity_rho) > 0.3
                else "no strong relationship"
            ),
        },
        "per_question_detail": per_q_metrics,
    }


# =============================================================================
# 7. DOSE-RESPONSE (CONTINUOUS IMPORTANCE VS SHIFT)
# =============================================================================

def analyze_dose_response(rows: list[dict]) -> dict:
    """Continuous analysis: betweenness centrality vs |shift|.

    Fits linear regression and tests for non-linearity.
    """
    # Node probes only (edges use a different importance metric)
    node_data = [
        (r["target_importance"], r["absolute_shift"])
        for r in rows
        if r["success"]
        and r.get("absolute_shift") is not None
        and r.get("target_importance") is not None
        and r["target_importance"] > 0
        and r.get("probe_category") == "node"
    ]

    if len(node_data) < 5:
        return {"error": "Too few node probes for dose-response", "n": len(node_data)}

    importance_vals = [d[0] for d in node_data]
    shift_vals = [d[1] for d in node_data]

    # Linear regression
    regression = _linear_regression(importance_vals, shift_vals)

    # Spearman (monotonic but possibly non-linear)
    rho = _spearman_correlation(importance_vals, shift_vals)

    # Quartile analysis (check for non-linearity)
    sorted_data = sorted(node_data, key=lambda d: d[0])
    n = len(sorted_data)
    q_size = max(1, n // 4)
    quartiles = []
    for i in range(4):
        start = i * q_size
        end = start + q_size if i < 3 else n
        q_data = sorted_data[start:end]
        q_importance = [d[0] for d in q_data]
        q_shifts = [d[1] for d in q_data]
        quartiles.append({
            "quartile": i + 1,
            "n": len(q_data),
            "mean_importance": round(sum(q_importance) / len(q_importance), 4),
            "mean_shift": round(sum(q_shifts) / len(q_shifts), 4),
        })

    # Bootstrap CI on slope
    slope_ci = _bootstrap_ci(
        list(range(len(node_data))),
        stat_fn=lambda indices: _linear_regression(
            [importance_vals[i] for i in indices],
            [shift_vals[i] for i in indices],
        ).get("slope", 0) or 0,
    )

    return {
        "n_observations": len(node_data),
        "linear_regression": regression,
        "spearman_rho": round(rho, 4) if rho is not None else None,
        "slope_bootstrap_ci": slope_ci,
        "quartile_analysis": quartiles,
    }


# =============================================================================
# 8. FORMAL NULL TEST
# =============================================================================

def analyze_null_test(rows: list[dict]) -> dict:
    """Test whether real probes cause significantly larger shifts than irrelevant probes.

    Per-question paired comparison: mean(real probes) vs mean(irrelevant probes).
    """
    # Group by question
    question_groups = defaultdict(lambda: {"real": [], "irrelevant": []})
    for r in rows:
        if not r["success"] or r.get("absolute_shift") is None:
            continue
        qid = r["question_id"]
        if r.get("probe_type") == "irrelevant":
            question_groups[qid]["irrelevant"].append(r["absolute_shift"])
        else:
            question_groups[qid]["real"].append(r["absolute_shift"])

    # Per-question: mean real shift vs mean irrelevant shift
    real_means = []
    irrel_means = []
    question_significant = 0
    question_details = []

    for qid, groups in question_groups.items():
        if not groups["real"] or not groups["irrelevant"]:
            continue

        real_mean = sum(groups["real"]) / len(groups["real"])
        irrel_mean = sum(groups["irrelevant"]) / len(groups["irrelevant"])
        real_means.append(real_mean)
        irrel_means.append(irrel_mean)

        # Is real > irrelevant for this question?
        if real_mean > irrel_mean:
            question_significant += 1

        question_details.append({
            "question_id": qid,
            "mean_real_shift": round(real_mean, 4),
            "mean_irrelevant_shift": round(irrel_mean, 4),
            "difference": round(real_mean - irrel_mean, 4),
            "real_exceeds_control": real_mean > irrel_mean,
        })

    if len(real_means) < 3:
        return {"error": "Too few paired questions", "n": len(real_means)}

    # Paired t-test across questions
    paired = _paired_t_test(real_means, irrel_means)

    # Effect size (Cohen's d)
    diffs = [r - i for r, i in zip(real_means, irrel_means)]
    mean_diff = sum(diffs) / len(diffs)
    sd_diff = math.sqrt(sum((d - mean_diff) ** 2 for d in diffs) / (len(diffs) - 1)) if len(diffs) > 1 else 1e-10
    cohens_d = mean_diff / sd_diff

    # Bootstrap CI on difference
    diff_ci = _bootstrap_ci(diffs)

    return {
        "n_questions": len(real_means),
        "mean_real_shift": round(sum(real_means) / len(real_means), 4),
        "mean_irrelevant_shift": round(sum(irrel_means) / len(irrel_means), 4),
        "paired_t_test": paired,
        "cohens_d": round(cohens_d, 4),
        "difference_bootstrap_ci": diff_ci,
        "pct_questions_real_exceeds_control": round(
            question_significant / len(real_means) * 100, 1
        ),
        "per_question": question_details,
    }


# =============================================================================
# 9. EDGE PROBE ANALYSIS
# =============================================================================

def analyze_edge_probes(rows: list[dict]) -> dict:
    """Detailed analysis of edge-targeting probes.

    Tests edge betweenness vs |shift| and critical vs peripheral comparison.
    """
    edge_rows = [
        r for r in rows
        if r["success"]
        and r.get("absolute_shift") is not None
        and r.get("probe_category") == "edge"
    ]

    if len(edge_rows) < 3:
        return {"error": "Too few edge probes", "n": len(edge_rows)}

    # Edge betweenness vs |shift| correlation
    eb_vals = [r["target_importance"] for r in edge_rows if r.get("target_importance") is not None]
    shift_vals = [r["absolute_shift"] for r in edge_rows if r.get("target_importance") is not None]
    eb_shift_rho = _spearman_correlation(eb_vals, shift_vals) if len(eb_vals) >= 3 else None

    # Critical vs peripheral (formal test)
    critical_shifts = [r["absolute_shift"] for r in edge_rows if r.get("target_on_critical_path") is True]
    peripheral_shifts = [r["absolute_shift"] for r in edge_rows if r.get("target_on_critical_path") is False]

    if critical_shifts and peripheral_shifts and len(critical_shifts) >= 2 and len(peripheral_shifts) >= 2:
        # Welch's t-test (unpaired, unequal variance)
        n1, n2 = len(critical_shifts), len(peripheral_shifts)
        m1 = sum(critical_shifts) / n1
        m2 = sum(peripheral_shifts) / n2
        v1 = sum((s - m1) ** 2 for s in critical_shifts) / (n1 - 1) if n1 > 1 else 0
        v2 = sum((s - m2) ** 2 for s in peripheral_shifts) / (n2 - 1) if n2 > 1 else 0
        se = math.sqrt(v1 / n1 + v2 / n2) if (v1 / n1 + v2 / n2) > 0 else 1e-10
        t_stat = (m1 - m2) / se
        # Welch-Satterthwaite df
        num = (v1 / n1 + v2 / n2) ** 2
        den = (v1 / n1) ** 2 / (n1 - 1) + (v2 / n2) ** 2 / (n2 - 1) if (n1 > 1 and n2 > 1) else 1
        df = num / den if den > 0 else 1
        p_val = _t_to_p(t_stat, max(1, int(df)))

        critical_vs_peripheral = {
            "mean_critical": round(m1, 4),
            "mean_peripheral": round(m2, 4),
            "difference": round(m1 - m2, 4),
            "t": round(t_stat, 4),
            "p": round(p_val, 4),
            "n_critical": n1,
            "n_peripheral": n2,
        }
    else:
        critical_vs_peripheral = {
            "mean_critical": _safe_mean(critical_shifts),
            "mean_peripheral": _safe_mean(peripheral_shifts),
            "n_critical": len(critical_shifts),
            "n_peripheral": len(peripheral_shifts),
        }

    # By edge probe type
    edge_types = defaultdict(list)
    for r in edge_rows:
        edge_types[r.get("probe_type", "")].append(r["absolute_shift"])

    by_type = {}
    for pt, shifts in sorted(edge_types.items()):
        by_type[pt] = {
            "n": len(shifts),
            "mean_shift": round(sum(shifts) / len(shifts), 4),
            "median_shift": round(_median(shifts), 4),
        }

    return {
        "n_edge_probes": len(edge_rows),
        "edge_betweenness_shift_rho": round(eb_shift_rho, 4) if eb_shift_rho is not None else None,
        "critical_vs_peripheral": critical_vs_peripheral,
        "by_edge_probe_type": by_type,
    }


# =============================================================================
# 10. DEPENDENCY STRUCTURE
# =============================================================================

def analyze_dependency_structure(rows: list[dict], question_data: dict[str, dict]) -> dict:
    """Test whether upstream node negation causes larger shifts than downstream.

    For node pairs where A is upstream of B (A -> ... -> B -> outcome),
    negation of A should cause a larger shift than negation of B.
    """
    import networkx as nx

    pairs_tested = 0
    upstream_larger = 0
    upstream_shifts = []
    downstream_shifts = []

    for qid, qdata in question_data.items():
        nodes = qdata.get("nodes", [])
        edges = qdata.get("edges", [])
        if not nodes or not edges:
            continue

        # Build graph
        G = nx.DiGraph()
        for n in nodes:
            G.add_node(n["id"], role=n.get("role", "factor"))
        for e in edges:
            G.add_edge(e["from"], e["to"])

        outcome_node = next((n["id"] for n in nodes if n.get("role") == "outcome"), None)
        if outcome_node is None:
            continue

        # Get negation probe shifts for this question
        q_rows = [r for r in rows if r.get("question_id") == qid and r["success"]]
        negate_shifts = {}
        for r in q_rows:
            pt = r.get("probe_type", "")
            if "negate" in pt and r.get("probe_category") == "node":
                tid = r.get("target_id", "")
                if tid and r.get("absolute_shift") is not None:
                    if tid not in negate_shifts:
                        negate_shifts[tid] = []
                    negate_shifts[tid].append(r["absolute_shift"])

        # Average shifts per node
        node_mean_shift = {
            nid: sum(s) / len(s) for nid, s in negate_shifts.items()
        }

        # Find upstream/downstream pairs
        factor_nodes = [n["id"] for n in nodes if n.get("role") != "outcome"]
        for a in factor_nodes:
            for b in factor_nodes:
                if a == b:
                    continue
                if a not in node_mean_shift or b not in node_mean_shift:
                    continue
                # Check if A is upstream of B (A -> ... -> B)
                try:
                    if nx.has_path(G, a, b) and nx.has_path(G, b, outcome_node):
                        pairs_tested += 1
                        if node_mean_shift[a] > node_mean_shift[b]:
                            upstream_larger += 1
                        upstream_shifts.append(node_mean_shift[a])
                        downstream_shifts.append(node_mean_shift[b])
                except nx.NetworkXError:
                    continue

    if pairs_tested == 0:
        return {"error": "No upstream/downstream pairs found", "n_pairs": 0}

    # Paired test
    paired = _paired_t_test(upstream_shifts, downstream_shifts) if len(upstream_shifts) >= 3 else {}

    return {
        "n_pairs": pairs_tested,
        "pct_upstream_larger": round(upstream_larger / pairs_tested * 100, 1),
        "mean_upstream_shift": round(sum(upstream_shifts) / len(upstream_shifts), 4),
        "mean_downstream_shift": round(sum(downstream_shifts) / len(downstream_shifts), 4),
        "paired_t_test": paired,
    }


# =============================================================================
# 11. WITHIN-QUESTION CONSISTENCY (Kendall's tau)
# =============================================================================

def _kendall_tau(x: list[float], y: list[float]) -> float | None:
    """Compute Kendall's tau-b rank correlation between two lists."""
    n = len(x)
    if n < 3:
        return None

    concordant = 0
    discordant = 0
    ties_x = 0
    ties_y = 0

    for i in range(n):
        for j in range(i + 1, n):
            dx = x[i] - x[j]
            dy = y[i] - y[j]

            if dx == 0 and dy == 0:
                ties_x += 1
                ties_y += 1
            elif dx == 0:
                ties_x += 1
            elif dy == 0:
                ties_y += 1
            elif (dx > 0 and dy > 0) or (dx < 0 and dy < 0):
                concordant += 1
            else:
                discordant += 1

    n_pairs = n * (n - 1) / 2
    denom = math.sqrt((n_pairs - ties_x) * (n_pairs - ties_y))
    if denom == 0:
        return None

    return (concordant - discordant) / denom


def analyze_within_question_consistency(
    rows: list[dict],
    question_data: dict[str, dict],
) -> dict:
    """Test within-question rank consistency of importance vs shift.

    For each question, computes Kendall's tau between the importance rank
    ordering of probes and the rank ordering of their absolute shifts.
    This is a stronger test than the aggregate Spearman rho because it
    asks: within each question's own causal graph, does the model respect
    its own importance hierarchy?

    Only uses node probes (node_negate_high/medium/low, node_strengthen)
    where importance varies meaningfully.
    """
    node_probe_types = {
        "node_negate_high", "node_negate_medium", "node_negate_low",
        "node_strengthen",
    }

    # Group by question
    q_probes: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        if (r["success"]
            and r.get("absolute_shift") is not None
            and r.get("target_importance") is not None
            and r.get("probe_type") in node_probe_types):
            q_probes[r["question_id"]].append(r)

    taus = []
    per_question = []

    for qid, probes in q_probes.items():
        if len(probes) < 4:
            continue

        importance_vals = [p["target_importance"] for p in probes]
        shift_vals = [p["absolute_shift"] for p in probes]

        tau = _kendall_tau(importance_vals, shift_vals)
        if tau is not None:
            taus.append(tau)
            per_question.append({
                "question_id": qid,
                "tau": round(tau, 4),
                "n_probes": len(probes),
            })

    if not taus:
        return {"error": "Not enough within-question data", "n_questions": 0}

    mean_tau = sum(taus) / len(taus)
    pct_positive = round(sum(1 for t in taus if t > 0) / len(taus) * 100, 1)
    pct_strong = round(sum(1 for t in taus if t > 0.3) / len(taus) * 100, 1)

    # One-sample t-test: is mean tau significantly > 0?
    n = len(taus)
    var_tau = sum((t - mean_tau) ** 2 for t in taus) / (n - 1) if n > 1 else 0
    se_tau = math.sqrt(var_tau / n) if var_tau > 0 else 1e-10
    t_stat = mean_tau / se_tau
    p_value = _t_to_p(t_stat, n - 1)
    # One-tailed (we predict tau > 0)
    p_one_tailed = p_value / 2 if t_stat > 0 else 1 - p_value / 2

    # Bootstrap CI for mean tau
    tau_ci = _bootstrap_ci(taus)

    return {
        "n_questions": len(taus),
        "mean_tau": round(mean_tau, 4),
        "median_tau": round(_median(taus), 4),
        "pct_positive": pct_positive,
        "pct_strong_positive": pct_strong,
        "t_test_vs_zero": {
            "t": round(t_stat, 4),
            "p_two_tailed": round(p_value, 4),
            "p_one_tailed": round(p_one_tailed, 4),
        },
        "bootstrap_ci": tau_ci,
        "per_question": sorted(per_question, key=lambda x: x["tau"], reverse=True),
    }


# =============================================================================
# 12. MECHANISM TEXT QUALITY
# =============================================================================

def _count_hedging_words(text: str) -> int:
    """Count hedging/uncertainty words in mechanism text."""
    hedges = {
        "may", "might", "could", "possibly", "potentially", "perhaps",
        "likely", "unlikely", "tends", "tend", "sometimes", "often",
        "generally", "typically", "can", "somewhat", "partially",
        "indirectly", "approximately", "roughly",
    }
    words = text.lower().split()
    return sum(1 for w in words if w.strip(".,;:") in hedges)


def _count_causal_words(text: str) -> int:
    """Count causal/mechanistic language in mechanism text."""
    causal = {
        "causes", "leads", "increases", "decreases", "reduces", "drives",
        "triggers", "affects", "influences", "determines", "shapes",
        "contributes", "enables", "prevents", "inhibits", "promotes",
        "accelerates", "amplifies", "dampens", "undermines", "strengthens",
        "weakens", "facilitates", "constrains", "forces", "creates",
        "produces", "generates", "results",
    }
    words = text.lower().split()
    return sum(1 for w in words if w.strip(".,;:") in causal)


def analyze_mechanism_text_quality(
    rows: list[dict],
    question_data: dict[str, dict],
) -> dict:
    """Analyze whether mechanism text quality predicts probe sensitivity.

    For each edge in each question's causal graph, extracts NLP features
    of the mechanism description and correlates with the absolute shift
    produced when that edge is probed.

    Features:
    - length (character count)
    - word_count
    - specificity (causal word density)
    - hedging (hedge word density)
    - has_direction (contains increase/decrease language)

    Hypothesis: edges with more specific, longer, less hedged mechanism
    descriptions should produce larger shifts when probed, because the
    model has encoded a stronger causal commitment.
    """
    # Build edge mechanism lookup from question data
    edge_mechanisms: dict[str, dict[tuple[str, str], str]] = {}
    for qid, qdata in question_data.items():
        edge_mechanisms[qid] = {}
        for e in qdata.get("edges", []):
            key = (e.get("from", ""), e.get("to", ""))
            edge_mechanisms[qid][key] = e.get("mechanism", "")

    # Collect edge probe results with mechanism text features
    records = []
    for r in rows:
        if not r["success"] or r.get("absolute_shift") is None:
            continue
        if r.get("probe_category") != "edge":
            continue

        qid = r.get("question_id", "")
        target_id = r.get("target_id", "")

        # target_id for edges is typically "from->to"
        if "->" not in target_id:
            continue

        parts = target_id.split("->")
        if len(parts) != 2:
            continue

        from_node, to_node = parts[0].strip(), parts[1].strip()
        q_edges = edge_mechanisms.get(qid, {})
        mechanism = q_edges.get((from_node, to_node), "")

        if not mechanism:
            continue

        word_count = len(mechanism.split())
        n_hedge = _count_hedging_words(mechanism)
        n_causal = _count_causal_words(mechanism)

        records.append({
            "question_id": qid,
            "edge": target_id,
            "mechanism": mechanism,
            "absolute_shift": r["absolute_shift"],
            "probe_type": r.get("probe_type", ""),
            "length": len(mechanism),
            "word_count": word_count,
            "hedge_count": n_hedge,
            "causal_count": n_causal,
            "hedge_density": n_hedge / word_count if word_count > 0 else 0,
            "causal_density": n_causal / word_count if word_count > 0 else 0,
            "specificity_score": (n_causal - n_hedge) / word_count if word_count > 0 else 0,
        })

    if len(records) < 10:
        return {"error": f"Too few edge probes with mechanism text ({len(records)})", "n_records": len(records)}

    # Compute correlations between each feature and absolute shift
    shifts = [r["absolute_shift"] for r in records]
    features = {
        "length": [r["length"] for r in records],
        "word_count": [r["word_count"] for r in records],
        "hedge_density": [r["hedge_density"] for r in records],
        "causal_density": [r["causal_density"] for r in records],
        "specificity_score": [r["specificity_score"] for r in records],
    }

    correlations = {}
    for feat_name, feat_vals in features.items():
        rho = _spearman_correlation(feat_vals, shifts)
        reg = _linear_regression(feat_vals, shifts)
        correlations[feat_name] = {
            "spearman_rho": round(rho, 4) if rho is not None else None,
            "regression": reg,
            "mean": round(sum(feat_vals) / len(feat_vals), 4),
            "median": round(_median(feat_vals), 4),
        }

    # Stratify by mechanism quality: high-specificity vs low-specificity edges
    specs = [r["specificity_score"] for r in records]
    median_spec = _median(specs)

    high_spec = [r["absolute_shift"] for r in records if r["specificity_score"] > median_spec]
    low_spec = [r["absolute_shift"] for r in records if r["specificity_score"] <= median_spec]

    stratified = {
        "median_specificity": round(median_spec, 4),
        "high_specificity": {
            "n": len(high_spec),
            "mean_shift": round(sum(high_spec) / len(high_spec), 4) if high_spec else None,
        },
        "low_specificity": {
            "n": len(low_spec),
            "mean_shift": round(sum(low_spec) / len(low_spec), 4) if low_spec else None,
        },
    }

    if high_spec and low_spec and len(high_spec) >= 3 and len(low_spec) >= 3:
        # Unpaired t-test
        mean_h = sum(high_spec) / len(high_spec)
        mean_l = sum(low_spec) / len(low_spec)
        var_h = sum((x - mean_h) ** 2 for x in high_spec) / (len(high_spec) - 1)
        var_l = sum((x - mean_l) ** 2 for x in low_spec) / (len(low_spec) - 1)
        se = math.sqrt(var_h / len(high_spec) + var_l / len(low_spec))
        t = (mean_h - mean_l) / se if se > 0 else 0
        df = len(high_spec) + len(low_spec) - 2
        p = _t_to_p(t, df)
        stratified["t_test"] = {
            "t": round(t, 4),
            "p": round(p, 4),
            "mean_diff": round(mean_h - mean_l, 4),
        }

    # Summary stats for mechanism texts
    all_lengths = [r["length"] for r in records]
    all_words = [r["word_count"] for r in records]

    return {
        "n_records": len(records),
        "mechanism_stats": {
            "mean_length_chars": round(sum(all_lengths) / len(all_lengths), 1),
            "mean_word_count": round(sum(all_words) / len(all_words), 1),
            "median_length_chars": round(_median(all_lengths), 1),
            "median_word_count": round(_median(all_words), 1),
        },
        "feature_correlations": correlations,
        "specificity_stratification": stratified,
    }


# =============================================================================
# 13. PROBE TEXT ASSERTIVENESS CONTROL
# =============================================================================

# Strong/forceful language in probe texts
_ASSERTIVE_PHRASES = [
    "completely", "entirely", "fundamentally", "actually",
    "in fact", "evidence shows", "research shows", "data shows",
    "clearly", "obviously", "undeniably", "proven",
    "failed", "broken", "wrong", "false", "flawed",
    "no evidence", "no support", "no basis", "no relationship",
    "contradicts", "disproves", "refutes", "invalidates",
    "impossible", "implausible", "unlikely",
    "overwhelmingly", "conclusively", "definitively",
]

# Tentative/weak language in probe texts
_TENTATIVE_PHRASES = [
    "might", "may", "could", "perhaps", "possibly",
    "somewhat", "slightly", "marginally",
    "suggests", "implies", "indicates",
    "some argue", "some believe", "some evidence",
    "not necessarily", "not always", "not entirely",
    "questionable", "debatable", "uncertain",
]


def _score_assertiveness(text: str) -> float:
    """Score assertiveness of probe text. Higher = more forceful."""
    text_lower = text.lower()
    assertive = sum(1 for p in _ASSERTIVE_PHRASES if p in text_lower)
    tentative = sum(1 for p in _TENTATIVE_PHRASES if p in text_lower)
    word_count = len(text.split())
    if word_count == 0:
        return 0.0
    return (assertive - tentative) / word_count


def analyze_probe_assertiveness_control(
    rows: list[dict],
    question_data: dict[str, dict],
) -> dict:
    """Control analysis: does importance predict shift after accounting for
    probe text assertiveness?

    The Stage 2 probe generation prompts use different framing for high vs low
    importance targets. If the generated probe texts are systematically more
    forceful for high-importance targets, then SSR could reflect probe quality
    rather than structural sensitivity.

    Tests:
    1. Does assertiveness differ by importance level? (confound check)
    2. Does assertiveness independently predict shift?
    3. Does importance still predict shift after partialling out assertiveness?
       (partial correlation via residualization)
    """
    # Build probe text lookup from question JSONs
    probe_text_map: dict[str, dict[str, str]] = {}
    for qid, qdata in question_data.items():
        probe_text_map[qid] = {}
        for i, probe in enumerate(qdata.get("probes", [])):
            if probe.get("probe_text"):
                probe_text_map[qid][str(i)] = probe["probe_text"]

    # Only use node probes where importance varies (exclude structural/irrelevant)
    node_types = {"node_negate_high", "node_negate_medium", "node_negate_low", "node_strengthen"}

    records = []
    for r in rows:
        if not r["success"] or r.get("absolute_shift") is None:
            continue
        if r.get("probe_type") not in node_types:
            continue
        if r.get("target_importance") is None:
            continue

        qid = r.get("question_id", "")
        probe_idx = r.get("probe_index")

        # Get full probe text from question JSON
        probe_text = ""
        if qid in probe_text_map and probe_idx is not None:
            probe_text = probe_text_map[qid].get(str(int(probe_idx)), "")
        if not probe_text:
            probe_text = r.get("probe_text", "")
        if not probe_text:
            continue

        assertiveness = _score_assertiveness(probe_text)

        records.append({
            "importance": r["target_importance"],
            "absolute_shift": r["absolute_shift"],
            "assertiveness": assertiveness,
            "probe_type": r["probe_type"],
            "probe_text_length": len(probe_text.split()),
        })

    if len(records) < 20:
        return {"error": f"Too few node probes ({len(records)})", "n_records": len(records)}

    importances = [r["importance"] for r in records]
    shifts = [r["absolute_shift"] for r in records]
    assertiveness_vals = [r["assertiveness"] for r in records]

    # --- 1. Does assertiveness differ by probe type? ---
    by_type = defaultdict(list)
    for r in records:
        by_type[r["probe_type"]].append(r["assertiveness"])

    assertiveness_by_type = {}
    for pt, vals in sorted(by_type.items()):
        assertiveness_by_type[pt] = {
            "n": len(vals),
            "mean_assertiveness": round(sum(vals) / len(vals), 4),
        }

    # Correlation: importance vs assertiveness
    imp_assert_rho = _spearman_correlation(importances, assertiveness_vals)

    # --- 2. Does assertiveness independently predict shift? ---
    assert_shift_rho = _spearman_correlation(assertiveness_vals, shifts)
    assert_shift_reg = _linear_regression(assertiveness_vals, shifts)

    # --- 3. Partial correlation: importance -> shift, controlling assertiveness ---
    # Residualize both importance and shift on assertiveness via OLS
    imp_reg = _linear_regression(assertiveness_vals, importances)
    shift_reg = _linear_regression(assertiveness_vals, shifts)

    if imp_reg.get("slope") is not None and shift_reg.get("slope") is not None:
        imp_residuals = [
            imp - (imp_reg["intercept"] + imp_reg["slope"] * a)
            for imp, a in zip(importances, assertiveness_vals)
        ]
        shift_residuals = [
            s - (shift_reg["intercept"] + shift_reg["slope"] * a)
            for s, a in zip(shifts, assertiveness_vals)
        ]
        partial_rho = _spearman_correlation(imp_residuals, shift_residuals)
    else:
        partial_rho = None

    # Raw importance-shift correlation for comparison
    raw_rho = _spearman_correlation(importances, shifts)

    return {
        "n_records": len(records),
        "confound_check": {
            "importance_assertiveness_rho": round(imp_assert_rho, 4) if imp_assert_rho is not None else None,
            "assertiveness_by_probe_type": assertiveness_by_type,
            "interpretation": (
                "strong confound" if imp_assert_rho is not None and abs(imp_assert_rho) > 0.3
                else "moderate confound" if imp_assert_rho is not None and abs(imp_assert_rho) > 0.15
                else "weak/no confound"
            ),
        },
        "assertiveness_predicts_shift": {
            "spearman_rho": round(assert_shift_rho, 4) if assert_shift_rho is not None else None,
            "regression": assert_shift_reg,
        },
        "partial_correlation": {
            "raw_importance_shift_rho": round(raw_rho, 4) if raw_rho is not None else None,
            "partial_importance_shift_rho": round(partial_rho, 4) if partial_rho is not None else None,
            "attenuation_pct": (
                round((1 - abs(partial_rho) / abs(raw_rho)) * 100, 1)
                if partial_rho is not None and raw_rho is not None and abs(raw_rho) > 0.01
                else None
            ),
            "interpretation": (
                "importance effect robust after controlling assertiveness"
                if partial_rho is not None and abs(partial_rho) > 0.2
                else "importance effect substantially attenuated"
                if partial_rho is not None and abs(partial_rho) < 0.1
                else "partial attenuation"
            ),
        },
    }


# =============================================================================
# 14. GROUND TRUTH CALIBRATION
# =============================================================================

# Path to bundled ForecastBench questions (has freeze_datetime_value)
_FORECASTBENCH_PATH = Path(__file__).parent / "forecastbench_questions.json"
# Path to resolved ground truth (prediction market + data source resolutions)
_GROUND_TRUTH_PATH = Path(__file__).parent.parent / "outputs" / "sensitivity" / "causal" / "ground_truth_resolutions.json"


def _load_freeze_values() -> dict[str, float]:
    """Load ground truth outcome probabilities for calibration.

    Prefers the resolved ground truth file (ground_truth_resolutions.json)
    which includes both prediction market probabilities and resolved data
    source outcomes. Falls back to prediction-market-only freeze values
    from the ForecastBench questions file.
    """
    # Try resolved ground truth first (includes data source resolutions)
    if _GROUND_TRUTH_PATH.exists():
        gt_data = json.loads(_GROUND_TRUTH_PATH.read_text(encoding="utf-8"))
        result = {}
        for qid, entry in gt_data.items():
            val = entry.get("outcome_probability")
            if val is not None and 0.0 <= float(val) <= 1.0:
                result[qid] = float(val)
        if result:
            return result

    # Fallback: prediction market freeze values only
    if not _FORECASTBENCH_PATH.exists():
        return {}

    data = json.loads(_FORECASTBENCH_PATH.read_text(encoding="utf-8"))
    qs = data.get("questions", [])
    prob_sources = {"metaculus", "manifold", "polymarket", "infer"}

    result = {}
    for q in qs:
        fv = q.get("freeze_datetime_value")
        source = q.get("source", "")
        if fv is None or source not in prob_sources:
            continue
        try:
            val = float(fv)
            if 0.0 <= val <= 1.0:
                result[q["id"]] = val
        except (ValueError, TypeError):
            continue
    return result


def analyze_ground_truth_calibration(
    rows: list[dict],
    question_data: dict[str, dict],
    model_runs: dict[str, tuple[list[dict], dict[str, dict]]] | None = None,
) -> dict:
    """Test whether structurally-faithful models are also better forecasters.

    Uses ForecastBench freeze_datetime_value as ground truth proxy.
    Computes Brier scores and tests whether sensitivity metrics (SSR,
    importance-rho) correlate with forecasting accuracy.

    Tests:
    1. Per-model Brier score (mean squared error vs ground truth)
    2. Calibration curve (binned predicted vs actual)
    3. Question-level: does initial probability accuracy correlate with
       sensitivity metrics (SSR, importance-rho)?
    4. Cross-model: are models with better SSR also better calibrated?
    """
    freeze_vals = _load_freeze_values()
    if not freeze_vals:
        return {"error": "ForecastBench freeze values not available"}

    # Compute per-model calibration
    all_model_results = {}
    runs_to_check = model_runs if model_runs else {"primary": (rows, question_data)}

    for model_name, (m_rows, m_q_data) in runs_to_check.items():
        brier_scores = []
        pred_actual_pairs = []

        for qid, qdata in m_q_data.items():
            if qid not in freeze_vals:
                continue

            pred = qdata.get("initial_probability")
            actual = freeze_vals[qid]
            if pred is None:
                continue

            brier = (pred - actual) ** 2
            brier_scores.append(brier)
            pred_actual_pairs.append({"qid": qid, "predicted": pred, "actual": actual, "brier": brier})

        if not brier_scores:
            all_model_results[model_name] = {"error": "No matched questions", "n": 0}
            continue

        mean_brier = sum(brier_scores) / len(brier_scores)
        preds = [p["predicted"] for p in pred_actual_pairs]
        actuals = [p["actual"] for p in pred_actual_pairs]

        # Calibration curve (5 bins)
        bins = [(0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.0)]
        cal_bins = []
        for lo, hi in bins:
            bin_pairs = [p for p in pred_actual_pairs if lo <= p["predicted"] < hi]
            if not bin_pairs:
                cal_bins.append({"bin": f"{lo}-{hi}", "n": 0, "mean_pred": None, "mean_actual": None})
                continue
            cal_bins.append({
                "bin": f"{lo}-{hi}",
                "n": len(bin_pairs),
                "mean_pred": round(sum(p["predicted"] for p in bin_pairs) / len(bin_pairs), 4),
                "mean_actual": round(sum(p["actual"] for p in bin_pairs) / len(bin_pairs), 4),
            })

        # Correlation between predicted and actual
        pred_actual_rho = _spearman_correlation(preds, actuals)

        all_model_results[model_name] = {
            "n_questions": len(brier_scores),
            "mean_brier": round(mean_brier, 4),
            "median_brier": round(_median(brier_scores), 4),
            "pred_actual_rho": round(pred_actual_rho, 4) if pred_actual_rho is not None else None,
            "calibration_bins": cal_bins,
        }

    # Per-question: does accuracy correlate with sensitivity?
    # For each question, compute Brier score and per-Q SSR/importance-rho
    primary_q_data = question_data
    q_accuracy_sensitivity = []
    for qid, qdata in primary_q_data.items():
        if qid not in freeze_vals:
            continue
        pred = qdata.get("initial_probability")
        if pred is None:
            continue

        brier = (pred - freeze_vals[qid]) ** 2
        abs_error = abs(pred - freeze_vals[qid])

        # Get this question's probes
        q_rows = [r for r in rows if r.get("question_id") == qid and r["success"]
                   and r.get("absolute_shift") is not None and r.get("target_importance") is not None]
        if len(q_rows) < 4:
            continue

        q_shifts = [r["absolute_shift"] for r in q_rows]
        mean_shift = sum(q_shifts) / len(q_shifts)

        importances = [r["target_importance"] for r in q_rows if r.get("target_importance", 0) > 0]
        shifts_for_rho = [r["absolute_shift"] for r in q_rows if r.get("target_importance", 0) > 0]
        q_rho = _spearman_correlation(importances, shifts_for_rho) if len(importances) >= 4 else None

        q_accuracy_sensitivity.append({
            "qid": qid,
            "brier": brier,
            "abs_error": abs_error,
            "mean_shift": mean_shift,
            "importance_rho": q_rho,
        })

    accuracy_sensitivity_corr = {}
    if len(q_accuracy_sensitivity) >= 10:
        briers = [q["brier"] for q in q_accuracy_sensitivity]
        mean_shifts = [q["mean_shift"] for q in q_accuracy_sensitivity]
        rhos = [q["importance_rho"] for q in q_accuracy_sensitivity if q["importance_rho"] is not None]
        briers_for_rho = [q["brier"] for q in q_accuracy_sensitivity if q["importance_rho"] is not None]

        # Does forecasting accuracy correlate with sensitivity?
        brier_shift_rho = _spearman_correlation(briers, mean_shifts)
        # Does accuracy correlate with structural faithfulness?
        brier_imprho_rho = _spearman_correlation(briers_for_rho, rhos) if len(rhos) >= 5 else None

        accuracy_sensitivity_corr = {
            "n_questions": len(q_accuracy_sensitivity),
            "brier_vs_mean_shift_rho": round(brier_shift_rho, 4) if brier_shift_rho is not None else None,
            "brier_vs_importance_rho_rho": round(brier_imprho_rho, 4) if brier_imprho_rho is not None else None,
        }

    return {
        "per_model": all_model_results,
        "accuracy_sensitivity": accuracy_sensitivity_corr,
    }


# =============================================================================
# 15. MULTIPLE COMPARISONS CORRECTION
# =============================================================================

def collect_and_correct_pvalues(report: dict) -> dict:
    """Collect all p-values from the analysis report and apply FDR correction.

    Uses Benjamini-Hochberg procedure to control false discovery rate at q=0.05.

    Returns
    -------
    Dict with original p-values, corrected p-values, and which tests survive.
    """
    # Collect p-values with labels
    pvals = []

    # Core metrics don't have explicit p-values, but several analyses do:

    # Dose-response
    dr = report.get("dose_response", {})
    if dr.get("linear_regression", {}).get("p_slope") is not None:
        pvals.append(("dose_response_slope", dr["linear_regression"]["p_slope"]))

    # Null test
    nt = report.get("null_test", {})
    if nt.get("paired_t_test", {}).get("p") is not None:
        pvals.append(("null_test_real_vs_irrelevant", nt["paired_t_test"]["p"]))

    # Edge probes
    ep = report.get("edge_probes", {})
    cv = ep.get("critical_vs_peripheral", {})
    if cv.get("p") is not None:
        pvals.append(("edge_critical_vs_peripheral", cv["p"]))

    # Dependency structure
    ds = report.get("dependency_structure", {})
    if ds.get("paired_t_test", {}).get("p") is not None:
        pvals.append(("upstream_vs_downstream", ds["paired_t_test"]["p"]))

    # Within-question consistency
    wq = report.get("within_question_consistency", {})
    if wq.get("t_test_vs_zero", {}).get("p_two_tailed") is not None:
        pvals.append(("within_q_tau_vs_zero", wq["t_test_vs_zero"]["p_two_tailed"]))

    # Mechanism text features
    mt = report.get("mechanism_text_quality", {})
    for feat, data in mt.get("feature_correlations", {}).items():
        reg = data.get("regression", {})
        if reg.get("p_slope") is not None:
            pvals.append((f"mechanism_{feat}", reg["p_slope"]))

    # Assertiveness control
    ac = report.get("assertiveness_control", {})
    aps = ac.get("assertiveness_predicts_shift", {})
    if aps.get("regression", {}).get("p_slope") is not None:
        pvals.append(("assertiveness_shift_regression", aps["regression"]["p_slope"]))

    # Reasoning coherence
    rc = report.get("reasoning_coherence", {})
    sic = rc.get("stated_impact_coherence", {})
    if sic.get("t_test_strong_vs_weak", {}).get("p") is not None:
        pvals.append(("reasoning_strong_vs_weak", sic["t_test_strong_vs_weak"]["p"]))

    # Directionality
    dr = report.get("directionality", {})
    ic = dr.get("irrelevant_control", {})
    if ic.get("p_vs_zero") is not None:
        pvals.append(("irrelevant_bias_vs_zero", ic["p_vs_zero"]))

    # Specificity stratification
    mt_strat = mt.get("specificity_stratification", {})
    if mt_strat.get("t_test", {}).get("p") is not None:
        pvals.append(("mechanism_specificity_strat", mt_strat["t_test"]["p"]))

    if not pvals:
        return {"error": "No p-values collected", "n_tests": 0}

    # Sort by p-value for BH procedure
    pvals.sort(key=lambda x: x[1])
    m = len(pvals)

    # Benjamini-Hochberg correction
    corrected = []
    prev_corrected = 1.0
    for i in range(m - 1, -1, -1):
        label, p = pvals[i]
        rank = i + 1
        bh_critical = (rank / m) * 0.05
        corrected_p = min(prev_corrected, p * m / rank)
        corrected_p = min(corrected_p, 1.0)
        prev_corrected = corrected_p
        corrected.append({
            "test": label,
            "p_original": round(p, 6),
            "p_corrected": round(corrected_p, 6),
            "rank": rank,
            "bh_critical": round(bh_critical, 6),
            "significant_original": p < 0.05,
            "significant_corrected": corrected_p < 0.05,
        })

    # Reverse back to sorted-by-p order
    corrected.reverse()

    n_sig_original = sum(1 for c in corrected if c["significant_original"])
    n_sig_corrected = sum(1 for c in corrected if c["significant_corrected"])

    return {
        "n_tests": m,
        "fdr_level": 0.05,
        "n_significant_original": n_sig_original,
        "n_significant_corrected": n_sig_corrected,
        "tests": corrected,
    }


# =============================================================================
# 16. REASONING COHERENCE
# =============================================================================

# Language patterns indicating the model believes the probe is impactful
_STRONG_IMPACT_PHRASES = [
    "breaks", "broken", "undermines", "eliminates", "removes",
    "fundamentally", "substantially", "significantly", "dramatically",
    "critical", "crucial", "primary", "main", "key", "major",
    "collapses", "invalidates", "reverses", "disrupts",
]

# Language patterns indicating the model believes the probe is weak/peripheral
_WEAK_IMPACT_PHRASES = [
    "peripheral", "minor", "marginal", "negligible", "minimal",
    "does not affect", "does not impact", "does not change",
    "no bearing", "no direct", "no significant", "no substantial",
    "remains unchanged", "remains intact", "still holds",
    "unrelated", "irrelevant", "tangential",
    "however", "but", "nonetheless", "still",
]

# Language referencing causal structure
_CAUSAL_PATH_PHRASES = [
    "causal path", "causal link", "causal chain", "causal mechanism",
    "path to", "path from", "path leading",
    "upstream", "downstream",
    "direct link", "indirect",
    "mediating", "mediator",
]


def _count_phrase_hits(text: str, phrases: list[str]) -> int:
    """Count how many phrases from a list appear in text (case-insensitive)."""
    text_lower = text.lower()
    return sum(1 for p in phrases if p in text_lower)


def _classify_stated_impact(reasoning: str) -> str:
    """Classify the reasoning text into stated impact level.

    Returns 'strong', 'weak', or 'mixed' based on language patterns.
    """
    strong = _count_phrase_hits(reasoning, _STRONG_IMPACT_PHRASES)
    weak = _count_phrase_hits(reasoning, _WEAK_IMPACT_PHRASES)

    if strong >= 2 and weak <= 1:
        return "strong"
    elif weak >= 2 and strong <= 1:
        return "weak"
    else:
        return "mixed"


def analyze_reasoning_coherence(
    rows: list[dict],
    question_data: dict[str, dict],
) -> dict:
    """Analyze whether the model's stated reasoning aligns with its actual shift.

    Tests:
    1. Stated-impact coherence: when the model uses strong-impact language
       ("breaks the main path", "fundamentally undermines"), does it actually
       shift more than when it uses weak-impact language ("peripheral",
       "does not affect")?
    2. Causal path referencing: does the model reference more causal paths
       in its reasoning when it shifts more?
    3. Reasoning length vs shift: do larger shifts come with longer explanations?
    4. Incoherence detection: cases where stated impact and actual shift diverge
       (e.g., says "critical path broken" but shifts by 0.01, or says
       "no effect" but shifts by 0.15).
    """
    # Build reasoning lookup from question JSONs (full text, not truncated CSV)
    reasoning_map: dict[str, dict[str, str]] = {}  # qid -> {probe_idx -> reasoning}
    for qid, qdata in question_data.items():
        probe_results = qdata.get("probe_results", [])
        reasoning_map[qid] = {}
        for i, pr in enumerate(probe_results):
            if pr.get("reasoning"):
                reasoning_map[qid][str(i)] = pr["reasoning"]

    records = []
    for r in rows:
        if not r["success"] or r.get("absolute_shift") is None:
            continue

        qid = r.get("question_id", "")
        probe_idx = r.get("probe_index")

        # Prefer full reasoning from question JSON over truncated CSV
        reasoning = ""
        if qid in reasoning_map and probe_idx is not None:
            reasoning = reasoning_map[qid].get(str(int(probe_idx)), "")
        if not reasoning:
            reasoning = r.get("reasoning", "")

        if not reasoning or len(reasoning.split()) < 5:
            continue

        word_count = len(reasoning.split())
        stated_impact = _classify_stated_impact(reasoning)
        strong_hits = _count_phrase_hits(reasoning, _STRONG_IMPACT_PHRASES)
        weak_hits = _count_phrase_hits(reasoning, _WEAK_IMPACT_PHRASES)
        path_refs = _count_phrase_hits(reasoning, _CAUSAL_PATH_PHRASES)
        n_hedge = _count_hedging_words(reasoning)
        n_causal = _count_causal_words(reasoning)

        records.append({
            "question_id": qid,
            "probe_type": r.get("probe_type", ""),
            "probe_category": r.get("probe_category", ""),
            "absolute_shift": r["absolute_shift"],
            "reasoning": reasoning,
            "word_count": word_count,
            "stated_impact": stated_impact,
            "strong_hits": strong_hits,
            "weak_hits": weak_hits,
            "path_refs": path_refs,
            "hedge_count": n_hedge,
            "causal_count": n_causal,
            "impact_score": strong_hits - weak_hits,  # net directional score
        })

    if len(records) < 20:
        return {"error": f"Too few reasoning responses ({len(records)})", "n_records": len(records)}

    # --- 1. Stated-impact coherence ---
    by_impact = defaultdict(list)
    for r in records:
        by_impact[r["stated_impact"]].append(r["absolute_shift"])

    impact_coherence = {}
    for level in ["strong", "mixed", "weak"]:
        shifts = by_impact.get(level, [])
        if shifts:
            impact_coherence[level] = {
                "n": len(shifts),
                "mean_shift": round(sum(shifts) / len(shifts), 4),
                "median_shift": round(_median(shifts), 4),
            }

    # T-test: strong vs weak
    strong_shifts = by_impact.get("strong", [])
    weak_shifts = by_impact.get("weak", [])
    if len(strong_shifts) >= 5 and len(weak_shifts) >= 5:
        mean_s = sum(strong_shifts) / len(strong_shifts)
        mean_w = sum(weak_shifts) / len(weak_shifts)
        var_s = sum((x - mean_s) ** 2 for x in strong_shifts) / (len(strong_shifts) - 1)
        var_w = sum((x - mean_w) ** 2 for x in weak_shifts) / (len(weak_shifts) - 1)
        se = math.sqrt(var_s / len(strong_shifts) + var_w / len(weak_shifts))
        t = (mean_s - mean_w) / se if se > 0 else 0
        df = len(strong_shifts) + len(weak_shifts) - 2
        p = _t_to_p(t, df)
        impact_t_test = {"t": round(t, 4), "p": round(p, 4), "mean_diff": round(mean_s - mean_w, 4)}
    else:
        impact_t_test = {"error": "Too few strong or weak classifications"}

    # --- 2. Impact score correlation ---
    impact_scores = [r["impact_score"] for r in records]
    shifts = [r["absolute_shift"] for r in records]
    impact_rho = _spearman_correlation(impact_scores, shifts)

    # --- 3. Path referencing correlation ---
    path_counts = [r["path_refs"] for r in records]
    path_rho = _spearman_correlation(path_counts, shifts)

    # --- 4. Reasoning length correlation ---
    word_counts = [r["word_count"] for r in records]
    length_rho = _spearman_correlation(word_counts, shifts)
    length_reg = _linear_regression(word_counts, shifts)

    # --- 5. Incoherence detection ---
    n_incoherent_over = 0   # says weak but shifts a lot
    n_incoherent_under = 0  # says strong but barely shifts
    incoherent_examples = []

    for r in records:
        if r["stated_impact"] == "weak" and r["absolute_shift"] >= 0.10:
            n_incoherent_over += 1
            if len(incoherent_examples) < 5:
                incoherent_examples.append({
                    "type": "over_shift",
                    "question_id": r["question_id"],
                    "probe_type": r["probe_type"],
                    "shift": r["absolute_shift"],
                    "stated_impact": r["stated_impact"],
                    "reasoning_excerpt": r["reasoning"][:200],
                })
        elif r["stated_impact"] == "strong" and r["absolute_shift"] < 0.03:
            n_incoherent_under += 1
            if len(incoherent_examples) < 5:
                incoherent_examples.append({
                    "type": "under_shift",
                    "question_id": r["question_id"],
                    "probe_type": r["probe_type"],
                    "shift": r["absolute_shift"],
                    "stated_impact": r["stated_impact"],
                    "reasoning_excerpt": r["reasoning"][:200],
                })

    total_classifiable = len(strong_shifts) + len(weak_shifts)
    n_incoherent = n_incoherent_over + n_incoherent_under
    incoherence_rate = round(n_incoherent / total_classifiable, 4) if total_classifiable > 0 else None

    # --- 6. By probe category ---
    cat_stats = defaultdict(lambda: {"word_counts": [], "path_refs": [], "impact_scores": []})
    for r in records:
        cat = r["probe_category"]
        cat_stats[cat]["word_counts"].append(r["word_count"])
        cat_stats[cat]["path_refs"].append(r["path_refs"])
        cat_stats[cat]["impact_scores"].append(r["impact_score"])

    by_category = {}
    for cat, stats in cat_stats.items():
        wc = stats["word_counts"]
        pr = stats["path_refs"]
        by_category[cat] = {
            "n": len(wc),
            "mean_word_count": round(sum(wc) / len(wc), 1),
            "mean_path_refs": round(sum(pr) / len(pr), 2),
        }

    return {
        "n_records": len(records),
        "reasoning_stats": {
            "mean_word_count": round(sum(word_counts) / len(word_counts), 1),
            "median_word_count": round(_median(word_counts), 1),
        },
        "stated_impact_coherence": {
            "by_level": impact_coherence,
            "t_test_strong_vs_weak": impact_t_test,
        },
        "correlations": {
            "impact_score_vs_shift": {
                "spearman_rho": round(impact_rho, 4) if impact_rho is not None else None,
            },
            "path_refs_vs_shift": {
                "spearman_rho": round(path_rho, 4) if path_rho is not None else None,
            },
            "reasoning_length_vs_shift": {
                "spearman_rho": round(length_rho, 4) if length_rho is not None else None,
                "regression": length_reg,
            },
        },
        "incoherence": {
            "n_over_shift": n_incoherent_over,
            "n_under_shift": n_incoherent_under,
            "incoherence_rate": incoherence_rate,
            "total_classifiable": total_classifiable,
            "examples": incoherent_examples,
        },
        "by_category": by_category,
    }


# =============================================================================
# 17. PROBE FAITHFULNESS SAMPLING
# =============================================================================

def sample_probes_for_review(rows: list[dict], n_sample: int = 30, seed: int = 42) -> dict:
    """Sample probes for human faithfulness review.

    Stratified sample: 10 node probes, 10 edge probes, 10 structural probes.
    """
    rng = random.Random(seed)

    by_category = defaultdict(list)
    for r in rows:
        if r["success"] and r.get("probe_text"):
            cat = r.get("probe_category", "unknown")
            by_category[cat].append(r)

    samples = []
    per_category = n_sample // 3

    for cat in ["node", "edge", "structural"]:
        pool = by_category.get(cat, [])
        n_pick = min(per_category, len(pool))
        if n_pick > 0:
            picked = rng.sample(pool, n_pick)
            for r in picked:
                samples.append({
                    "category": cat,
                    "probe_type": r.get("probe_type", ""),
                    "question_id": r.get("question_id", ""),
                    "question_text": r.get("question_text", "")[:200],
                    "target_id": r.get("target_id", ""),
                    "target_description": r.get("target_description", ""),
                    "probe_text": r.get("probe_text", ""),
                    "absolute_shift": r.get("absolute_shift"),
                    # For human annotation:
                    "faithful": None,  # To be filled: does probe challenge the target?
                    "relevant": None,  # To be filled: is probe relevant to the question?
                    "smuggles_info": None,  # To be filled: does probe introduce unrelated info?
                })

    return {
        "n_sampled": len(samples),
        "category_counts": {cat: len(by_category.get(cat, [])) for cat in ["node", "edge", "structural"]},
        "samples": samples,
    }


# =============================================================================
# 18. CROSS-MODEL COMPARISON
# =============================================================================

SOURCE_DOMAIN_MAP = {
    "metaculus": "prediction_market",
    "manifold": "prediction_market",
    "polymarket": "prediction_market",
    "infer": "prediction_market",
    "fred": "economic",
    "dbnomics": "economic",
    "yfinance": "economic",
    "acled": "events",
    "wikipedia": "events",
}


def analyze_domain_stratification(
    rows: list[dict],
    question_data: dict[str, dict],
) -> dict:
    """Stratify all core metrics by question domain (source category).

    Groups: prediction_market, economic, events.
    """
    # Map question_id -> domain
    qid_domain: dict[str, str] = {}
    for qid, qd in question_data.items():
        source = qd.get("source", "unknown")
        qid_domain[qid] = SOURCE_DOMAIN_MAP.get(source, "other")

    # Also tag by raw source for fine-grained view
    qid_source: dict[str, str] = {}
    for qid, qd in question_data.items():
        qid_source[qid] = qd.get("source", "unknown")

    # Group rows by domain
    domain_rows: dict[str, list[dict]] = defaultdict(list)
    source_rows: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        qid = r["question_id"]
        domain = qid_domain.get(qid, "other")
        source = qid_source.get(qid, "unknown")
        domain_rows[domain].append(r)
        source_rows[source].append(r)

    # Compute metrics per domain
    per_domain = {}
    for domain, d_rows in sorted(domain_rows.items()):
        successful = [r for r in d_rows if r.get("success")]
        n_questions = len({r["question_id"] for r in d_rows})
        per_domain[domain] = {
            "n_questions": n_questions,
            "n_probes": len(successful),
            "anchoring": compute_anchoring_metrics(d_rows),
            "ssr": structural_sensitivity_ratio(d_rows),
            "sar": spurious_acceptance_rate(d_rows),
            "asymmetry": asymmetry_index(d_rows),
            "importance_rho": importance_sensitivity_correlation(d_rows),
            "critical_path": critical_path_premium(d_rows),
        }

    # Per-source counts (fine-grained)
    source_counts = {}
    for source, s_rows in sorted(source_rows.items()):
        source_counts[source] = {
            "n_questions": len({r["question_id"] for r in s_rows}),
            "n_probes": len([r for r in s_rows if r.get("success")]),
            "mean_shift": _safe_mean(
                [r["absolute_shift"] for r in s_rows
                 if r.get("success") and r.get("absolute_shift") is not None]
            ),
        }

    # Cross-domain comparison: is SSR consistent across domains?
    domain_ssrs = {d: m["ssr"].get("ssr") for d, m in per_domain.items()
                   if m["ssr"].get("ssr") is not None}

    return {
        "n_domains": len(per_domain),
        "per_domain": per_domain,
        "per_source": source_counts,
        "domain_ssr_values": domain_ssrs,
    }


def compare_graph_structures(
    model_runs: dict[str, tuple[list[dict], dict[str, dict]]],
) -> dict:
    """Compare causal graph structures across models for the same questions.

    For each shared question, compute:
    - Node set Jaccard similarity
    - Edge set Jaccard similarity
    - Initial probability correlation
    - Whether more similar graphs yield more similar sensitivity profiles
    """
    model_names = sorted(model_runs.keys())
    if len(model_names) < 2:
        return {"error": "Need at least 2 models", "n_models": len(model_names)}

    pairwise = {}
    for i, m1 in enumerate(model_names):
        for m2 in model_names[i + 1:]:
            _, qdata_1 = model_runs[m1]
            _, qdata_2 = model_runs[m2]

            shared = sorted(set(qdata_1.keys()) & set(qdata_2.keys()))
            if len(shared) < 3:
                pairwise[f"{m1}_vs_{m2}"] = {
                    "error": f"Too few shared questions ({len(shared)})",
                }
                continue

            node_jaccards = []
            edge_jaccards = []
            prob_1 = []
            prob_2 = []
            graph_sim_vs_shift_sim = []

            for qid in shared:
                q1 = qdata_1[qid]
                q2 = qdata_2[qid]

                # Node Jaccard (by id)
                nodes_1 = {n["id"] for n in q1.get("nodes", [])}
                nodes_2 = {n["id"] for n in q2.get("nodes", [])}
                if nodes_1 or nodes_2:
                    nj = len(nodes_1 & nodes_2) / len(nodes_1 | nodes_2) if (nodes_1 | nodes_2) else 0
                    node_jaccards.append(nj)

                # Edge Jaccard (by from->to pair)
                edges_1 = {(e["from"], e["to"]) for e in q1.get("edges", [])}
                edges_2 = {(e["from"], e["to"]) for e in q2.get("edges", [])}
                if edges_1 or edges_2:
                    ej = len(edges_1 & edges_2) / len(edges_1 | edges_2) if (edges_1 | edges_2) else 0
                    edge_jaccards.append(ej)

                # Initial probability
                p1 = q1.get("initial_probability")
                p2 = q2.get("initial_probability")
                if p1 is not None and p2 is not None:
                    prob_1.append(p1)
                    prob_2.append(p2)

                # Graph similarity vs shift similarity
                summary_1 = q1.get("summary", {})
                summary_2 = q2.get("summary", {})
                ms1 = summary_1.get("mean_absolute_shift")
                ms2 = summary_2.get("mean_absolute_shift")
                if ms1 is not None and ms2 is not None and (edges_1 or edges_2):
                    graph_sim_vs_shift_sim.append({
                        "edge_jaccard": ej,
                        "shift_diff": abs(ms1 - ms2),
                    })

            # Probability correlation
            prob_corr = _spearman_correlation(prob_1, prob_2) if len(prob_1) >= 3 else None

            # Correlation: graph similarity vs shift similarity
            graph_shift_rho = None
            if len(graph_sim_vs_shift_sim) >= 5:
                gs = [x["edge_jaccard"] for x in graph_sim_vs_shift_sim]
                sd = [x["shift_diff"] for x in graph_sim_vs_shift_sim]
                graph_shift_rho = _spearman_correlation(gs, sd)

            pairwise[f"{m1}_vs_{m2}"] = {
                "n_shared_questions": len(shared),
                "mean_node_jaccard": round(_safe_mean(node_jaccards), 4),
                "mean_edge_jaccard": round(_safe_mean(edge_jaccards), 4),
                "median_node_jaccard": round(_median(node_jaccards), 4) if node_jaccards else None,
                "median_edge_jaccard": round(_median(edge_jaccards), 4) if edge_jaccards else None,
                "initial_prob_correlation": prob_corr,
                "mean_prob_abs_diff": round(
                    _safe_mean([abs(a - b) for a, b in zip(prob_1, prob_2)]), 4
                ) if prob_1 else None,
                "graph_similarity_vs_shift_difference_rho": graph_shift_rho,
                "interpretation": (
                    "High node/edge Jaccard → models produce similar causal structures. "
                    "Negative graph-shift rho → more similar graphs yield more similar sensitivity profiles."
                ),
            }

    return {
        "n_models": len(model_names),
        "model_names": model_names,
        "pairwise_structure_comparison": pairwise,
    }


def compare_models(
    model_runs: dict[str, tuple[list[dict], dict[str, dict]]],
) -> dict:
    """Compare metrics across models, paired by question.

    Parameters
    ----------
    model_runs : dict
        Maps model_name -> (rows, question_data).
    """
    model_names = sorted(model_runs.keys())
    if len(model_names) < 2:
        return {"error": "Need at least 2 models for comparison", "n_models": len(model_names)}

    # Compute per-model aggregate metrics
    per_model = {}
    for name in model_names:
        rows, q_data = model_runs[name]
        per_model[name] = {
            "n_probes": len([r for r in rows if r["success"]]),
            "n_questions": len(q_data),
            "anchoring": compute_anchoring_metrics(rows),
            "ssr": structural_sensitivity_ratio(rows),
            "sar": spurious_acceptance_rate(rows),
            "asymmetry": asymmetry_index(rows),
            "importance_rho": importance_sensitivity_correlation(rows),
            "critical_path": critical_path_premium(rows),
        }

    # Pairwise comparisons (paired by question)
    pairwise = {}
    for i, m1 in enumerate(model_names):
        for m2 in model_names[i + 1:]:
            rows_1, qdata_1 = model_runs[m1]
            rows_2, qdata_2 = model_runs[m2]

            # Find shared questions
            shared = sorted(set(qdata_1.keys()) & set(qdata_2.keys()))
            if len(shared) < 3:
                pairwise[f"{m1}_vs_{m2}"] = {
                    "error": f"Too few shared questions ({len(shared)})",
                    "n_shared": len(shared),
                }
                continue

            # Per-question mean shifts for each model
            def _q_shifts(rows):
                groups = defaultdict(list)
                for r in rows:
                    if r["success"] and r.get("absolute_shift") is not None:
                        groups[r["question_id"]].append(r["absolute_shift"])
                return {qid: sum(s) / len(s) for qid, s in groups.items()}

            shifts_1 = _q_shifts(rows_1)
            shifts_2 = _q_shifts(rows_2)

            paired_ids = [qid for qid in shared if qid in shifts_1 and qid in shifts_2]
            vals_1 = [shifts_1[qid] for qid in paired_ids]
            vals_2 = [shifts_2[qid] for qid in paired_ids]

            paired = _paired_t_test(vals_1, vals_2)

            # Per-question SSR comparison
            ssr_1_vals = []
            ssr_2_vals = []
            for qid in paired_ids:
                q_rows_1 = [r for r in rows_1 if r["question_id"] == qid and r["success"]]
                q_rows_2 = [r for r in rows_2 if r["question_id"] == qid and r["success"]]
                s1 = structural_sensitivity_ratio(q_rows_1).get("ssr")
                s2 = structural_sensitivity_ratio(q_rows_2).get("ssr")
                if s1 is not None and s2 is not None:
                    ssr_1_vals.append(s1)
                    ssr_2_vals.append(s2)

            ssr_paired = _paired_t_test(ssr_1_vals, ssr_2_vals) if len(ssr_1_vals) >= 3 else {}

            pairwise[f"{m1}_vs_{m2}"] = {
                "n_shared_questions": len(paired_ids),
                "mean_shift_comparison": paired,
                f"mean_shift_{m1}": round(sum(vals_1) / len(vals_1), 4) if vals_1 else None,
                f"mean_shift_{m2}": round(sum(vals_2) / len(vals_2), 4) if vals_2 else None,
                "ssr_comparison": ssr_paired,
                f"mean_ssr_{m1}": round(sum(ssr_1_vals) / len(ssr_1_vals), 4) if ssr_1_vals else None,
                f"mean_ssr_{m2}": round(sum(ssr_2_vals) / len(ssr_2_vals), 4) if ssr_2_vals else None,
            }

    return {
        "n_models": len(model_names),
        "per_model": per_model,
        "pairwise_comparisons": pairwise,
    }


# =============================================================================
# BOOTSTRAP CIS FOR CORE METRICS
# =============================================================================

def bootstrap_core_metrics(rows: list[dict], n_boot: int = 2000, seed: int = 42) -> dict:
    """Compute bootstrapped confidence intervals for SSR, SAR, asymmetry index."""
    rng = random.Random(seed)
    n = len(rows)
    successful = [r for r in rows if r["success"] and r.get("absolute_shift") is not None]
    ns = len(successful)

    if ns < 10:
        return {"error": "Too few successful probes for bootstrap", "n": ns}

    def _boot_ssr(sample):
        result = structural_sensitivity_ratio(sample)
        return result.get("ssr") or 0.0

    def _boot_sar(sample):
        result = spurious_acceptance_rate(sample)
        return result.get("acceptance_rate") or 0.0

    def _boot_asymmetry(sample):
        result = asymmetry_index(sample)
        return result.get("index") or 0.0

    def _boot_stat(stat_fn):
        observed = stat_fn(successful)
        boot_vals = []
        for _ in range(n_boot):
            sample = [successful[rng.randint(0, ns - 1)] for _ in range(ns)]
            boot_vals.append(stat_fn(sample))
        boot_vals.sort()
        lo = int(0.025 * n_boot)
        hi = int(0.975 * n_boot) - 1
        return {
            "observed": round(observed, 4),
            "ci_lower": round(boot_vals[lo], 4),
            "ci_upper": round(boot_vals[hi], 4),
        }

    return {
        "n_probes": ns,
        "n_bootstrap": n_boot,
        "ssr": _boot_stat(_boot_ssr),
        "sar": _boot_stat(_boot_sar),
        "asymmetry_index": _boot_stat(_boot_asymmetry),
    }


# =============================================================================
# MAIN RUNNER
# =============================================================================

def run_full_analysis(
    output_dirs: list[str],
    retest_dir: str | None = None,
):
    """Run all analyses on one or more output directories."""

    # Load all runs
    model_runs = {}
    for d in output_dirs:
        d_path = Path(d)
        csv_path = d_path / "sensitivity_results.csv"
        if not csv_path.exists():
            print(f"[ERROR] {csv_path} not found")
            continue

        rows = load_causal_results(csv_path)
        q_data = load_question_jsons(d_path)
        label = d_path.name
        model_runs[label] = (rows, q_data)
        print(f"Loaded {label}: {len(rows)} probes, {len(q_data)} questions")

    if not model_runs:
        print("[ERROR] No valid data loaded")
        return

    # Use first run as primary
    primary_label = list(model_runs.keys())[0]
    primary_rows, primary_q_data = model_runs[primary_label]

    report = {"primary_run": primary_label}

    print(f"\n{'='*70}")
    print(f"COMPREHENSIVE ANALYSIS: {primary_label}")
    print(f"{'='*70}")

    # --- Existing metrics (summary) ---
    print("\n--- Core Metrics ---")
    report["core_metrics"] = {
        "anchoring": compute_anchoring_metrics(primary_rows),
        "ssr": structural_sensitivity_ratio(primary_rows),
        "sar": spurious_acceptance_rate(primary_rows),
        "asymmetry": asymmetry_index(primary_rows),
        "importance_rho": importance_sensitivity_correlation(primary_rows),
        "critical_path": critical_path_premium(primary_rows),
        "by_probe_type": sensitivity_by_probe_type(primary_rows),
        "by_probe_category": sensitivity_by_probe_category(primary_rows),
    }
    _print_core_metrics(report["core_metrics"])

    # --- 1. Graph Quality ---
    print("\n--- 1. Graph Quality Assessment ---")
    report["graph_quality"] = analyze_graph_quality(primary_q_data)
    _print_graph_quality(report["graph_quality"])

    # --- 2. Shift Directionality ---
    print("\n--- 2. Shift Directionality ---")
    report["directionality"] = analyze_shift_directionality(primary_rows)
    _print_directionality(report["directionality"])

    # --- 3. Test-Retest ---
    if retest_dir:
        print("\n--- 3. Test-Retest Reliability ---")
        retest_path = Path(retest_dir)
        retest_q_data = load_question_jsons(retest_path)
        report["test_retest"] = analyze_test_retest(primary_q_data, retest_q_data)
        _print_test_retest(report["test_retest"])
    else:
        print("\n--- 3. Test-Retest Reliability --- [SKIPPED: no --retest dir]")
        report["test_retest"] = {"status": "requires_second_run"}

    # --- 4. Alternative Importance Metrics ---
    print("\n--- 4. Alternative Importance Metrics ---")
    report["alternative_metrics"] = compare_importance_metrics(primary_rows, primary_q_data)
    _print_alternative_metrics(report["alternative_metrics"])

    # --- 5. Graph Structure Controls ---
    print("\n--- 5. Graph Structure Controls ---")
    report["structure_controls"] = analyze_graph_structure_controls(primary_rows)
    _print_structure_controls(report["structure_controls"])

    # --- 6. Question-Level Effects ---
    print("\n--- 6. Question-Level Random Effects ---")
    report["question_effects"] = analyze_question_level_effects(primary_rows)
    _print_question_effects(report["question_effects"])

    # --- 7. Dose-Response ---
    print("\n--- 7. Dose-Response (Importance vs Shift) ---")
    report["dose_response"] = analyze_dose_response(primary_rows)
    _print_dose_response(report["dose_response"])

    # --- 8. Formal Null Test ---
    print("\n--- 8. Formal Null Test ---")
    report["null_test"] = analyze_null_test(primary_rows)
    _print_null_test(report["null_test"])

    # --- 9. Edge Probe Analysis ---
    print("\n--- 9. Edge Probe Analysis ---")
    report["edge_probes"] = analyze_edge_probes(primary_rows)
    _print_edge_probes(report["edge_probes"])

    # --- 10. Dependency Structure ---
    print("\n--- 10. Dependency Structure ---")
    report["dependency_structure"] = analyze_dependency_structure(primary_rows, primary_q_data)
    _print_dependency_structure(report["dependency_structure"])

    # --- 11. Probe Faithfulness Sampling ---
    print("\n--- 11. Probe Faithfulness Sampling ---")
    report["probe_sampling"] = sample_probes_for_review(primary_rows)
    print(f"  Sampled {report['probe_sampling']['n_sampled']} probes for human review")
    print(f"  Categories: {report['probe_sampling']['category_counts']}")

    # --- Bootstrap CIs ---
    print("\n--- Bootstrap Confidence Intervals ---")
    report["bootstrap_cis"] = bootstrap_core_metrics(primary_rows)
    _print_bootstrap(report["bootstrap_cis"])

    # --- 12. Domain Stratification ---
    print("\n--- 12. Domain Stratification ---")
    report["domain_stratification"] = analyze_domain_stratification(primary_rows, primary_q_data)
    _print_domain_stratification(report["domain_stratification"])

    # --- 13. Within-Question Consistency ---
    print("\n--- 13. Within-Question Consistency ---")
    report["within_question_consistency"] = analyze_within_question_consistency(primary_rows, primary_q_data)
    _print_within_question_consistency(report["within_question_consistency"])

    # --- 14. Mechanism Text Quality ---
    print("\n--- 14. Mechanism Text Quality ---")
    report["mechanism_text_quality"] = analyze_mechanism_text_quality(primary_rows, primary_q_data)
    _print_mechanism_text_quality(report["mechanism_text_quality"])

    # --- 15. Probe Text Assertiveness Control ---
    print("\n--- 15. Probe Text Assertiveness Control ---")
    report["assertiveness_control"] = analyze_probe_assertiveness_control(primary_rows, primary_q_data)
    _print_assertiveness_control(report["assertiveness_control"])

    # --- 14. Ground Truth Calibration ---
    print("\n--- 14. Ground Truth Calibration ---")
    report["ground_truth_calibration"] = analyze_ground_truth_calibration(
        primary_rows, primary_q_data, model_runs if len(model_runs) >= 2 else None,
    )
    _print_ground_truth_calibration(report["ground_truth_calibration"])

    # --- 16. Reasoning Coherence ---
    print("\n--- 16. Reasoning Coherence ---")
    report["reasoning_coherence"] = analyze_reasoning_coherence(primary_rows, primary_q_data)
    _print_reasoning_coherence(report["reasoning_coherence"])

    # --- 17. Cross-Model Comparison ---
    if len(model_runs) >= 2:
        print("\n--- 17. Cross-Model Comparison ---")
        report["cross_model"] = compare_models(model_runs)
        _print_cross_model(report["cross_model"])
    else:
        print("\n--- 17. Cross-Model Comparison --- [SKIPPED: need 2+ runs]")
        report["cross_model"] = {"status": "requires_multiple_models"}

    # --- 18. Cross-Model Graph Structure Comparison ---
    if len(model_runs) >= 2:
        print("\n--- 18. Cross-Model Graph Structure Comparison ---")
        report["graph_structure_comparison"] = compare_graph_structures(model_runs)
        _print_graph_structure_comparison(report["graph_structure_comparison"])
    else:
        print("\n--- 18. Cross-Model Graph Structure --- [SKIPPED: need 2+ runs]")
        report["graph_structure_comparison"] = {"status": "requires_multiple_models"}

    # --- Multiple Comparisons Correction ---
    print("\n--- Multiple Comparisons Correction (Benjamini-Hochberg) ---")
    report["multiple_comparisons"] = collect_and_correct_pvalues(report)
    _print_multiple_comparisons(report["multiple_comparisons"])

    # --- Probability Distribution Plot ---
    if len(model_runs) >= 2:
        print("\n--- Probability Distribution Plot ---")
        plot_path = Path(output_dirs[0]) / "probability_distributions.png"
        try:
            plot_probability_distributions(model_runs, plot_path)
        except Exception as e:
            print(f"  [WARNING] Plot failed: {e}")
    else:
        print("\n--- Probability Distribution Plot ---")
        plot_path = Path(output_dirs[0]) / "probability_distributions.png"
        try:
            plot_probability_distributions(model_runs, plot_path)
        except Exception as e:
            print(f"  [WARNING] Plot failed: {e}")

    # Save full report
    primary_path = Path(output_dirs[0])
    report_path = primary_path / "full_analysis_report.json"

    # Remove per-question detail and probe samples from JSON (too large)
    save_report = {k: v for k, v in report.items()}
    if "question_effects" in save_report and "per_question_detail" in save_report["question_effects"]:
        save_report["question_effects"] = {
            k: v for k, v in save_report["question_effects"].items()
            if k != "per_question_detail"
        }
    if "null_test" in save_report and "per_question" in save_report["null_test"]:
        save_report["null_test"] = {
            k: v for k, v in save_report["null_test"].items()
            if k != "per_question"
        }
    if "within_question_consistency" in save_report and "per_question" in save_report["within_question_consistency"]:
        save_report["within_question_consistency"] = {
            k: v for k, v in save_report["within_question_consistency"].items()
            if k != "per_question"
        }
    if "reasoning_coherence" in save_report:
        rc = save_report["reasoning_coherence"]
        if isinstance(rc, dict) and "incoherence" in rc:
            rc["incoherence"] = {
                k: v for k, v in rc["incoherence"].items()
                if k != "examples"
            }

    report_path.write_text(json.dumps(save_report, indent=2, default=str), encoding="utf-8")
    print(f"\nFull report saved: {report_path}")

    # Save probe samples separately
    samples_path = primary_path / "probe_faithfulness_samples.json"
    samples_path.write_text(
        json.dumps(report["probe_sampling"]["samples"], indent=2), encoding="utf-8"
    )
    print(f"Probe samples saved: {samples_path}")

    return report


# =============================================================================
# PRINTING HELPERS
# =============================================================================

def _print_core_metrics(m: dict):
    anch = m["anchoring"]
    print(f"  Anchoring: mean={anch['mean_absolute_shift']}, median={anch['median_absolute_shift']}, "
          f"n={anch['n']}, no_change={anch['pct_no_change']}%, small={anch['pct_small_shift']}%")
    ssr = m["ssr"]
    print(f"  SSR: {ssr['ssr']} (high={ssr['mean_shift_high']}, low={ssr['mean_shift_low']})")
    sar = m["sar"]
    print(f"  SAR: {sar['acceptance_rate']} ({sar['n_accepted']}/{sar['n_total']})")
    ai = m["asymmetry"]
    print(f"  Asymmetry: {ai['index']} (neg={ai['mean_shift_negate']}, str={ai['mean_shift_strengthen']})")
    isc = m["importance_rho"]
    print(f"  Importance-Sensitivity rho: {isc['spearman_rho']} (n={isc['n']})")
    cp = m["critical_path"]
    print(f"  Critical Path Premium: {cp['premium']} (on={cp['mean_shift_on_path']}, off={cp['mean_shift_off_path']})")


def _print_graph_quality(q: dict):
    if "error" in q:
        print(f"  {q['error']}")
        return
    ns = q["node_count_summary"]
    es = q["edge_count_summary"]
    ds = q["density_summary"]
    print(f"  Questions: {q['n_questions']}")
    print(f"  Nodes: mean={ns['mean']}, median={ns['median']}, range=[{ns['min']}, {ns['max']}]")
    print(f"  Edges: mean={es['mean']}, median={es['median']}, range=[{es['min']}, {es['max']}]")
    print(f"  Density: mean={ds['mean']}, range=[{ds['min']}, {ds['max']}]")
    print(f"  DAGs: {q['pct_dag']}%, Degenerate: {q['pct_degenerate']}% ({q['n_degenerate']})")


def _print_directionality(d: dict):
    if "negation" in d:
        n = d["negation"]
        print(f"  Negation: {n['pct_decreased_confidence']}% decreased confidence "
              f"(mean conf change={n['mean_confidence_change']}, n={n['n']})")
    if "strengthening" in d:
        s = d["strengthening"]
        print(f"  Strengthening: {s['pct_increased_confidence']}% increased confidence "
              f"(mean conf change={s['mean_confidence_change']}, n={s['n']})")
    if "irrelevant_control" in d:
        c = d["irrelevant_control"]
        print(f"  Irrelevant: mean signed shift={c['mean_signed_shift']}, "
              f"p(vs 0)={c['p_vs_zero']} [{c['interpretation']}]")
    if "edge_reversal" in d:
        r = d["edge_reversal"]
        print(f"  Edge reversal: mean signed={r['mean_signed_shift']}, mean |shift|={r['mean_abs_shift']}, n={r['n']}")


def _print_test_retest(tr: dict):
    if "error" in tr:
        print(f"  {tr['error']}")
        return
    ip = tr["initial_probability"]
    gs = tr["graph_similarity"]
    ms = tr["mean_shift_reliability"]
    print(f"  Shared questions: {tr['n_shared_questions']}")
    print(f"  Initial prob correlation: {ip['correlation']}, mean |diff|={ip['mean_abs_diff']}")
    print(f"  Graph edge Jaccard: {gs['mean_edge_jaccard']}, node Jaccard: {gs['mean_node_jaccard']}")
    print(f"  Mean shift correlation: {ms['correlation']} (n={ms['n_questions']})")


def _print_alternative_metrics(am: dict):
    if "error" in am:
        print(f"  {am['error']}")
        return
    print(f"  N records: {am['n_records']}")
    for metric in ["betweenness", "pagerank", "path_relevance", "out_degree"]:
        if metric in am:
            m = am[metric]
            print(f"  {metric:16s}: rho={m['spearman_rho']}, SSR={m['ssr']}")


def _print_structure_controls(sc: dict):
    if "error" in sc:
        print(f"  {sc['error']}")
        return
    print(f"  N questions: {sc['n_questions']}")
    print(f"  Density-shift rho: {sc['density_shift_correlation']}")
    print(f"  N_nodes-shift rho: {sc['n_nodes_shift_correlation']}")
    s = sc["stratified_by_density"]
    print(f"  Median density: {s['median_density']}")
    print(f"  Sparse ({s['sparse']['n']}q): mean_shift={s['sparse']['mean_shift']}, "
          f"importance_rho={s['sparse']['mean_importance_rho']}")
    print(f"  Dense  ({s['dense']['n']}q): mean_shift={s['dense']['mean_shift']}, "
          f"importance_rho={s['dense']['mean_importance_rho']}")


def _print_question_effects(qe: dict):
    if "error" in qe:
        print(f"  {qe['error']}")
        return
    vd = qe["variance_decomposition"]
    print(f"  Questions: {qe['n_questions']}")
    print(f"  ICC: {vd['icc']} ({vd['interpretation']})")
    print(f"  Between-Q var: {vd['between_question_var']}, Within-Q var: {vd['within_question_var']}")
    qs = qe["per_question_ssr"]
    print(f"  Per-Q SSR: mean={qs['mean']}, median={qs['median']}, {qs['pct_above_1']}% > 1")
    qr = qe["per_question_importance_rho"]
    print(f"  Per-Q rho: mean={qr['mean']}, {qr['pct_positive']}% positive")
    cs = qe["confidence_sensitivity"]
    print(f"  Confidence-sensitivity rho: {cs['rho']} ({cs['interpretation']})")


def _print_dose_response(dr: dict):
    if "error" in dr:
        print(f"  {dr['error']}")
        return
    reg = dr["linear_regression"]
    print(f"  N observations: {dr['n_observations']}")
    print(f"  Spearman rho: {dr['spearman_rho']}")
    print(f"  Linear: slope={reg['slope']}, R²={reg['r_squared']}, p={reg['p_slope']}")
    ci = dr["slope_bootstrap_ci"]
    print(f"  Slope 95% CI: [{ci['ci_lower']}, {ci['ci_upper']}]")
    print(f"  Quartile means: {' -> '.join(str(q['mean_shift']) for q in dr['quartile_analysis'])}")


def _print_null_test(nt: dict):
    if "error" in nt:
        print(f"  {nt['error']}")
        return
    print(f"  Questions: {nt['n_questions']}")
    print(f"  Mean real shift: {nt['mean_real_shift']}")
    print(f"  Mean irrelevant shift: {nt['mean_irrelevant_shift']}")
    pt = nt["paired_t_test"]
    print(f"  Paired t-test: t={pt['t']}, p={pt['p']}, diff={pt['mean_diff']}")
    print(f"  Cohen's d: {nt['cohens_d']}")
    ci = nt["difference_bootstrap_ci"]
    print(f"  Difference 95% CI: [{ci['ci_lower']}, {ci['ci_upper']}]")
    print(f"  Questions where real > control: {nt['pct_questions_real_exceeds_control']}%")


def _print_edge_probes(ep: dict):
    if "error" in ep:
        print(f"  {ep['error']}")
        return
    print(f"  N edge probes: {ep['n_edge_probes']}")
    print(f"  Edge betweenness-shift rho: {ep['edge_betweenness_shift_rho']}")
    cv = ep["critical_vs_peripheral"]
    print(f"  Critical: {cv.get('mean_critical')} (n={cv.get('n_critical')}), "
          f"Peripheral: {cv.get('mean_peripheral')} (n={cv.get('n_peripheral')})")
    if "t" in cv:
        print(f"  t={cv['t']}, p={cv['p']}")


def _print_dependency_structure(ds: dict):
    if "error" in ds:
        print(f"  {ds['error']}")
        return
    print(f"  Pairs tested: {ds['n_pairs']}")
    print(f"  Upstream > downstream: {ds['pct_upstream_larger']}%")
    print(f"  Mean upstream shift: {ds['mean_upstream_shift']}, downstream: {ds['mean_downstream_shift']}")
    if ds.get("paired_t_test"):
        pt = ds["paired_t_test"]
        print(f"  Paired t: t={pt.get('t')}, p={pt.get('p')}")


def _print_bootstrap(bs: dict):
    if "error" in bs:
        print(f"  {bs['error']}")
        return
    print(f"  N probes: {bs['n_probes']}, N bootstrap: {bs['n_bootstrap']}")
    for metric in ["ssr", "sar", "asymmetry_index"]:
        m = bs[metric]
        print(f"  {metric:16s}: {m['observed']} [{m['ci_lower']}, {m['ci_upper']}]")


def _print_domain_stratification(ds: dict):
    if "error" in ds:
        print(f"  {ds['error']}")
        return
    print(f"  Domains: {ds['n_domains']}")
    for domain, metrics in ds["per_domain"].items():
        ssr = metrics["ssr"].get("ssr", "N/A")
        sar = metrics["sar"].get("acceptance_rate", "N/A")
        rho = metrics["importance_rho"].get("spearman_rho", "N/A")
        mean_shift = metrics["anchoring"].get("mean_absolute_shift", "N/A")
        print(f"  {domain:20s}: n_q={metrics['n_questions']}, n_probes={metrics['n_probes']}, "
              f"mean_shift={mean_shift}, SSR={ssr}, SAR={sar}, rho={rho}")
    print("  Per-source breakdown:")
    for source, info in ds["per_source"].items():
        print(f"    {source:15s}: n_q={info['n_questions']}, "
              f"n_probes={info['n_probes']}, mean_shift={info['mean_shift']}")


def plot_probability_distributions(
    model_runs: dict[str, tuple[list[dict], dict[str, dict]]],
    output_path: Path,
):
    """Plot initial probability distributions across models.

    Creates a multi-panel figure:
    - Panel 1: Overlaid histograms of initial probabilities per model
    - Panel 2: Paired scatter of probabilities for shared questions (if 2+ models)
    - Panel 3: Violin/box plot comparison
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # Extract initial probabilities per model
    model_probs: dict[str, dict[str, float]] = {}
    for name, (rows, q_data) in model_runs.items():
        probs = {}
        for qid, qd in q_data.items():
            p = qd.get("initial_probability")
            if p is not None:
                probs[qid] = p
        model_probs[name] = probs

    n_models = len(model_probs)
    if n_models == 0:
        return

    has_pairs = n_models >= 2

    fig, axes = plt.subplots(1, 3 if has_pairs else 1, figsize=(18 if has_pairs else 7, 5))
    if not has_pairs:
        axes = [axes]

    colors = ["#4A90D9", "#E74C3C", "#2ECC71", "#F39C12", "#9B59B6"]

    # Panel 1: Overlaid histograms
    ax1 = axes[0]
    bins = [i * 0.05 for i in range(21)]  # 0.0 to 1.0 in steps of 0.05
    for i, (name, probs) in enumerate(model_probs.items()):
        vals = list(probs.values())
        ax1.hist(vals, bins=bins, alpha=0.4, label=f"{name} (n={len(vals)})",
                 color=colors[i % len(colors)], edgecolor=colors[i % len(colors)], linewidth=1.2)
    ax1.set_xlabel("Initial Probability", fontsize=12)
    ax1.set_ylabel("Count", fontsize=12)
    ax1.set_title("Distribution of Initial Probabilities", fontsize=13)
    ax1.legend(fontsize=10)
    ax1.set_xlim(0, 1)

    if has_pairs:
        model_names = list(model_probs.keys())

        # Panel 2: Paired scatter (first two models)
        ax2 = axes[1]
        m1, m2 = model_names[0], model_names[1]
        shared = set(model_probs[m1].keys()) & set(model_probs[m2].keys())
        if shared:
            x = [model_probs[m1][q] for q in shared]
            y = [model_probs[m2][q] for q in shared]
            ax2.scatter(x, y, alpha=0.6, s=40, color="#4A90D9", edgecolor="#333", linewidth=0.5)
            ax2.plot([0, 1], [0, 1], "k--", alpha=0.3, linewidth=1)
            ax2.set_xlabel(f"{m1}", fontsize=12)
            ax2.set_ylabel(f"{m2}", fontsize=12)
            ax2.set_title(f"Paired Probabilities (n={len(shared)})", fontsize=13)
            ax2.set_xlim(0, 1)
            ax2.set_ylim(0, 1)
            ax2.set_aspect("equal")

            # Add correlation annotation
            rho = _spearman_correlation(x, y)
            if rho is not None:
                ax2.annotate(f"ρ = {rho:.3f}", xy=(0.05, 0.92), xycoords="axes fraction",
                            fontsize=11, fontweight="bold")

        # Panel 3: Box plots
        ax3 = axes[2]
        box_data = []
        box_labels = []
        for name, probs in model_probs.items():
            vals = list(probs.values())
            box_data.append(vals)
            box_labels.append(name)

        bp = ax3.boxplot(box_data, tick_labels=box_labels, patch_artist=True, widths=0.6)
        for i, patch in enumerate(bp["boxes"]):
            patch.set_facecolor(colors[i % len(colors)])
            patch.set_alpha(0.5)
        ax3.set_ylabel("Initial Probability", fontsize=12)
        ax3.set_title("Model Comparison", fontsize=13)
        ax3.set_ylim(0, 1)

        # Add mean annotations
        for i, vals in enumerate(box_data):
            mean_v = sum(vals) / len(vals)
            ax3.annotate(f"μ={mean_v:.2f}", xy=(i + 1, mean_v), xytext=(i + 1.3, mean_v),
                        fontsize=9, arrowprops=dict(arrowstyle="-", color="gray"))

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(str(output_path), dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved probability distribution plot: {output_path}")


def _print_within_question_consistency(wq: dict):
    if "error" in wq:
        print(f"  {wq['error']}")
        return
    print(f"  Questions: {wq['n_questions']}")
    print(f"  Mean Kendall's tau: {wq['mean_tau']}")
    print(f"  Median Kendall's tau: {wq['median_tau']}")
    print(f"  % positive tau: {wq['pct_positive']}%")
    print(f"  % strong positive (>0.3): {wq['pct_strong_positive']}%")
    tt = wq["t_test_vs_zero"]
    print(f"  t-test (tau > 0): t={tt['t']}, p_one_tailed={tt['p_one_tailed']}")
    ci = wq["bootstrap_ci"]
    print(f"  Bootstrap 95% CI: [{ci['ci_lower']}, {ci['ci_upper']}]")

    # Show best and worst questions
    pq = wq.get("per_question", [])
    if pq:
        print(f"  Top 3: {', '.join(f'{q['tau']:.3f}' for q in pq[:3])}")
        print(f"  Bottom 3: {', '.join(f'{q['tau']:.3f}' for q in pq[-3:])}")


def _print_ground_truth_calibration(gt: dict):
    if "error" in gt:
        print(f"  {gt['error']}")
        return

    for model_name, metrics in gt.get("per_model", {}).items():
        if "error" in metrics:
            print(f"  {model_name}: {metrics['error']}")
            continue
        print(f"  {model_name}:")
        print(f"    N questions: {metrics['n_questions']}")
        print(f"    Mean Brier: {metrics['mean_brier']}, Median: {metrics['median_brier']}")
        print(f"    Pred-actual rho: {metrics['pred_actual_rho']}")
        print(f"    Calibration: ", end="")
        for b in metrics["calibration_bins"]:
            if b["n"] > 0:
                print(f"[{b['bin']}: pred={b['mean_pred']}, actual={b['mean_actual']}, n={b['n']}] ", end="")
        print()

    acs = gt.get("accuracy_sensitivity", {})
    if acs:
        print(f"\n  Accuracy-Sensitivity Correlations (n={acs.get('n_questions', 0)}):")
        print(f"    Brier vs mean shift: rho={acs.get('brier_vs_mean_shift_rho')}")
        print(f"    Brier vs importance-rho: rho={acs.get('brier_vs_importance_rho_rho')}")


def _print_multiple_comparisons(mc: dict):
    if "error" in mc:
        print(f"  {mc['error']}")
        return
    print(f"  Total tests: {mc['n_tests']}")
    print(f"  Significant at p<0.05 (uncorrected): {mc['n_significant_original']}")
    print(f"  Significant at q<0.05 (BH-corrected): {mc['n_significant_corrected']}")
    print()
    for t in mc["tests"]:
        sig = "***" if t["significant_corrected"] else "   "
        print(f"  {sig} {t['test']:35s}: p={t['p_original']:.6f} -> q={t['p_corrected']:.6f}")


def _print_assertiveness_control(ac: dict):
    if "error" in ac:
        print(f"  {ac['error']}")
        return
    print(f"  N node probes: {ac['n_records']}")

    cc = ac["confound_check"]
    print(f"\n  Confound Check (does importance correlate with probe assertiveness?):")
    print(f"    Importance-assertiveness rho: {cc['importance_assertiveness_rho']} [{cc['interpretation']}]")
    for pt, stats in cc["assertiveness_by_probe_type"].items():
        print(f"    {pt:22s}: mean_assertiveness={stats['mean_assertiveness']}, n={stats['n']}")

    aps = ac["assertiveness_predicts_shift"]
    print(f"\n  Does assertiveness independently predict shift?")
    print(f"    Assertiveness-shift rho: {aps['spearman_rho']}")
    reg = aps["regression"]
    print(f"    Regression: R²={reg.get('r_squared', 'N/A')}, p={reg.get('p_slope', 'N/A')}")

    pc = ac["partial_correlation"]
    print(f"\n  Partial correlation (importance -> shift, controlling assertiveness):")
    print(f"    Raw importance-shift rho: {pc['raw_importance_shift_rho']}")
    print(f"    Partial rho: {pc['partial_importance_shift_rho']}")
    print(f"    Attenuation: {pc['attenuation_pct']}%")
    print(f"    {pc['interpretation']}")


def _print_reasoning_coherence(rc: dict):
    if "error" in rc:
        print(f"  {rc['error']}")
        return
    print(f"  N reasoning responses: {rc['n_records']}")
    rs = rc["reasoning_stats"]
    print(f"  Reasoning text: mean={rs['mean_word_count']} words")

    print(f"\n  Stated-Impact Coherence:")
    sic = rc["stated_impact_coherence"]
    for level in ["strong", "mixed", "weak"]:
        if level in sic["by_level"]:
            d = sic["by_level"][level]
            print(f"    {level:8s}: mean_shift={d['mean_shift']}, median={d['median_shift']}, n={d['n']}")
    tt = sic.get("t_test_strong_vs_weak", {})
    if "t" in tt:
        print(f"    Strong vs Weak: t={tt['t']}, p={tt['p']}, diff={tt['mean_diff']}")

    print(f"\n  Correlations with |shift|:")
    corrs = rc["correlations"]
    isc = corrs["impact_score_vs_shift"]
    print(f"    Impact score (strong - weak hits): rho={isc['spearman_rho']}")
    prc = corrs["path_refs_vs_shift"]
    print(f"    Causal path references: rho={prc['spearman_rho']}")
    lrc = corrs["reasoning_length_vs_shift"]
    print(f"    Reasoning length: rho={lrc['spearman_rho']}, R²={lrc['regression'].get('r_squared', 'N/A')}")

    print(f"\n  Incoherence Detection:")
    inc = rc["incoherence"]
    print(f"    Over-shift (says weak, shifts >=0.10): {inc['n_over_shift']}")
    print(f"    Under-shift (says strong, shifts <0.03): {inc['n_under_shift']}")
    print(f"    Incoherence rate: {inc['incoherence_rate']} ({inc['n_over_shift'] + inc['n_under_shift']}/{inc['total_classifiable']})")

    if rc.get("by_category"):
        print(f"\n  By probe category:")
        for cat, stats in rc["by_category"].items():
            print(f"    {cat:12s}: n={stats['n']}, mean_words={stats['mean_word_count']}, "
                  f"mean_path_refs={stats['mean_path_refs']}")


def _print_mechanism_text_quality(mt: dict):
    if "error" in mt:
        print(f"  {mt['error']}")
        return
    print(f"  N edge probes with mechanism text: {mt['n_records']}")
    ms = mt["mechanism_stats"]
    print(f"  Mechanism text: mean={ms['mean_word_count']} words ({ms['mean_length_chars']} chars)")

    print(f"\n  Feature correlations with |shift|:")
    for feat, data in mt["feature_correlations"].items():
        rho = data["spearman_rho"]
        reg = data["regression"]
        r2 = reg.get("r_squared", "N/A")
        p = reg.get("p_slope", "N/A")
        print(f"    {feat:22s}: rho={rho}, R²={r2}, p={p}")

    strat = mt["specificity_stratification"]
    print(f"\n  Specificity stratification (median={strat['median_specificity']}):")
    print(f"    High specificity: mean_shift={strat['high_specificity']['mean_shift']} (n={strat['high_specificity']['n']})")
    print(f"    Low specificity:  mean_shift={strat['low_specificity']['mean_shift']} (n={strat['low_specificity']['n']})")
    if "t_test" in strat:
        tt = strat["t_test"]
        print(f"    t={tt['t']}, p={tt['p']}, diff={tt['mean_diff']}")


def _print_graph_structure_comparison(gs: dict):
    if "error" in gs:
        print(f"  {gs['error']}")
        return
    print(f"  Models: {', '.join(gs['model_names'])}")
    for pair, comp in gs["pairwise_structure_comparison"].items():
        if "error" in comp:
            print(f"  {pair}: {comp['error']}")
            continue
        print(f"  {pair} (n={comp['n_shared_questions']}):")
        print(f"    Node Jaccard: mean={comp['mean_node_jaccard']}, median={comp['median_node_jaccard']}")
        print(f"    Edge Jaccard: mean={comp['mean_edge_jaccard']}, median={comp['median_edge_jaccard']}")
        prob_rho = comp.get("initial_prob_correlation", {})
        if prob_rho is not None:
            if isinstance(prob_rho, dict):
                print(f"    Initial prob rho: {prob_rho.get('rho', 'N/A')}")
            else:
                print(f"    Initial prob rho: {prob_rho}")
        print(f"    Mean |prob diff|: {comp.get('mean_prob_abs_diff', 'N/A')}")
        gs_rho = comp.get("graph_similarity_vs_shift_difference_rho")
        if gs_rho is not None:
            if isinstance(gs_rho, dict):
                print(f"    Graph sim vs shift diff rho: {gs_rho.get('rho', 'N/A')}")
            else:
                print(f"    Graph sim vs shift diff rho: {gs_rho}")


def _print_cross_model(cm: dict):
    if "error" in cm:
        print(f"  {cm['error']}")
        return
    print(f"  Models: {cm['n_models']}")
    for name, metrics in cm["per_model"].items():
        ssr = metrics["ssr"].get("ssr", "N/A")
        sar = metrics["sar"].get("acceptance_rate", "N/A")
        rho = metrics["importance_rho"].get("spearman_rho", "N/A")
        print(f"  {name}: SSR={ssr}, SAR={sar}, rho={rho}, n={metrics['n_probes']}")
    for pair_name, comparison in cm["pairwise_comparisons"].items():
        if "error" in comparison:
            print(f"  {pair_name}: {comparison['error']}")
        else:
            pt = comparison.get("mean_shift_comparison", {})
            print(f"  {pair_name}: n={comparison['n_shared_questions']}, "
                  f"shift diff t={pt.get('t')}, p={pt.get('p')}")


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Comprehensive belief sensitivity analysis for paper",
    )
    parser.add_argument(
        "dirs", nargs="+",
        help="One or more output directories to analyze (first is primary)",
    )
    parser.add_argument(
        "--retest", default=None,
        help="Second run directory for test-retest reliability analysis",
    )
    args = parser.parse_args()
    run_full_analysis(args.dirs, retest_dir=args.retest)


if __name__ == "__main__":
    main()
