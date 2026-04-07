"""
Causal Forecasting Test — Can causal knowledge improve time-series prediction?

Uses rolling-window forecasting: predict 1 period at a time, reveal the actual,
update history, predict the next. Each step is 1 LLM call. N=10 gives 10
individually-scored predictions per condition per scenario.

Three conditions per run:
- discovered: model's own graph from a prior causal discovery run (fixed graph)
- ground_truth: actual GT adjacency matrix (performance ceiling, fixed graph)
- no_graph: no causal structure, just history (ablation)

Optional 4th condition (--adaptive):
- adaptive: rolling forecast with per-step causal graph revision. After each
  prediction, the model sees its cumulative errors and can revise its causal
  graph before the next step. N forecast calls + (N-1) revision calls per scenario.

Scoring: MAE, directional accuracy, Spearman rho.

Usage:
    # Dry run
    python -m causal_discovery.causal_forecast --domain market --dry-run

    # With discovered graph + baselines
    python -m causal_discovery.causal_forecast --domain market \\
        --graph-source outputs/causal_discovery/single_agent/market_single/pilot_results.json \\
        --include-baselines

    # With adaptive condition (per-step graph revision)
    python -m causal_discovery.causal_forecast --domain market --adaptive \\
        --graph-source outputs/causal_discovery/single_agent/market_single/pilot_results.json

    # Ground truth only
    python -m causal_discovery.causal_forecast --domain market --graph-source ground_truth

    # Custom scenarios/horizon
    python -m causal_discovery.causal_forecast --domain conflict --n-forecast 15 --n-scenarios 3
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
from scipy import stats

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from causal_discovery.ground_truth import (
    MARKET_VARIABLES, CONFLICT_VARIABLES,
    get_market_ground_truth, get_conflict_ground_truth,
)
from causal_discovery.multi_agent.agent import (
    setup_domain, call_llm, parse_json_response,
)
from causal_discovery.prompts_tests import (
    build_forecast_system_prompt,
    build_forecast_prompt,
    mock_forecast_response,
    build_graph_revision_prompt,
    mock_graph_revision_response,
)
from causal_discovery.prompts import (
    format_market_history, format_conflict_history,
)


# =============================================================================
# Graph loading
# =============================================================================

def _load_discovered_graph(path: str) -> list[tuple[str, str]]:
    """Load edges from pilot_results.json -> declaration.final_graph."""
    with open(path) as f:
        data = json.load(f)

    final_graph = data.get("declaration", {}).get("final_graph", [])
    edges = []
    for e in final_graph:
        src = e.get("from", "")
        dst = e.get("to", "")
        if src and dst:
            edges.append((src, dst))
    return edges


def _gt_to_edge_list(gt_matrix: np.ndarray, variables: list[str]) -> list[tuple[str, str]]:
    """Convert ground truth adjacency matrix to edge list."""
    edges = []
    n = gt_matrix.shape[0]
    for i in range(n):
        for j in range(n):
            if gt_matrix[i, j] == 1:
                edges.append((variables[i], variables[j]))
    return edges


def _format_graph_for_prompt(edges: list[tuple[str, str]]) -> str:
    """Edge list -> readable text for prompt inclusion."""
    if not edges:
        return "(empty graph)"
    return "\n".join(f"  {src} -> {dst}" for src, dst in edges)


# =============================================================================
# Actual trajectory generation
# =============================================================================

def _generate_actual_trajectory(domain_setup: dict, n_periods: int) -> list[dict]:
    """Run simulation forward from post-warmup snapshot, return full per-period dicts."""
    domain = domain_setup["domain"]

    if domain == "market":
        return _generate_market_trajectory(domain_setup, n_periods)
    else:
        return _generate_conflict_trajectory(domain_setup, n_periods)


def _generate_market_trajectory(domain_setup: dict, n_periods: int) -> list[dict]:
    """Run market sim forward, return full trajectory dicts."""
    from causal_discovery.intervention import _run_market_rollout

    state = copy.deepcopy(domain_setup["state_snapshot"])
    agents = copy.deepcopy(domain_setup["agents_snapshot"])
    base_params = copy.deepcopy(domain_setup["base_params"])

    return _run_market_rollout(
        state=state,
        agents=agents,
        base_params=base_params,
        shocks=domain_setup["shocks"],
        start_period=domain_setup["start_period"],
        n_periods=n_periods,
        overrides=None,
        rule_based=True,
        llm_pool=None,
        scenario_config=domain_setup["config"],
    )


def _generate_conflict_trajectory(domain_setup: dict, n_periods: int) -> list[dict]:
    """Run conflict sim forward, return full trajectory dicts."""
    from causal_discovery.intervention import _run_conflict_rollout

    state = copy.deepcopy(domain_setup["state_snapshot"])
    agents_config = copy.deepcopy(domain_setup["agents_snapshot"])

    return _run_conflict_rollout(
        state=state,
        agents_config=agents_config,
        shocks=domain_setup["shocks"],
        start_period=domain_setup["start_period"],
        n_periods=n_periods,
        overrides=None,
        rule_based=True,
        llm_pool=None,
    )


# =============================================================================
# History update helper
# =============================================================================

def _append_actual_to_history(domain: str, history_data: dict, period_dict: dict) -> None:
    """Append one actual period's values to the growing history_data (in-place).

    Market: price_history, volume_history, fundamental_history
    Conflict: escalation_history, actions_log
    """
    if domain == "market":
        history_data["price_history"].append(period_dict["clearing_price"])
        history_data["volume_history"].append(period_dict["volume"])
        history_data["fundamental_history"].append(period_dict["fundamental_price"])
    else:
        history_data["escalation_history"].append(period_dict["escalation_index"])
        # Build an actions_log entry from the trajectory dict
        actions_entry = {
            "novaris_action": f"delta={period_dict.get('novaris_action_delta', 0):.2f}",
            "tethys_action": f"delta={period_dict.get('tethys_action_delta', 0):.2f}",
        }
        history_data["actions_log"].append(actions_entry)


# =============================================================================
# Scoring
# =============================================================================

def score_forecast(predicted: list[float], actual: list[float]) -> dict:
    """Compute MAE, directional accuracy, and Spearman rho."""
    n = min(len(predicted), len(actual))
    if n == 0:
        return {"mae": float("nan"), "directional_accuracy": float("nan"),
                "spearman_rho": float("nan"), "n": 0}

    pred = np.array(predicted[:n])
    act = np.array(actual[:n])

    # MAE
    mae = float(np.mean(np.abs(pred - act)))

    # Directional accuracy (fraction of periods where direction of change matches)
    if n >= 2:
        pred_dir = np.sign(np.diff(pred))
        act_dir = np.sign(np.diff(act))
        dir_acc = float(np.mean(pred_dir == act_dir))
    else:
        dir_acc = float("nan")

    # Spearman rank correlation
    if n >= 3 and np.std(pred) > 0 and np.std(act) > 0:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            rho, _ = stats.spearmanr(pred, act)
        spearman = float(rho) if not np.isnan(rho) else 0.0
    elif n >= 3:
        spearman = 0.0  # constant input — no rank variation
    else:
        spearman = float("nan")

    return {
        "mae": round(mae, 6),
        "directional_accuracy": round(dir_acc, 4) if not np.isnan(dir_acc) else None,
        "spearman_rho": round(spearman, 4) if not np.isnan(spearman) else None,
        "n": n,
    }


# =============================================================================
# Single condition x single scenario
# =============================================================================

def _run_forecast_condition(
    domain_setup: dict,
    graph_edges: list[tuple[str, str]] | None,
    condition_name: str,
    trajectory: list[dict],
    n_forecast: int,
    api_key: str,
    model: str,
    dry_run: bool,
    verbose: bool,
) -> dict:
    """Run one forecast condition on one scenario using rolling window.

    Predicts 1 period at a time, reveals actual, updates history, repeats.
    Each step is 1 LLM call. N steps total.

    Returns dict with predicted values, scores, and per-step details.
    """
    domain = domain_setup["domain"]
    variables = domain_setup["variables"]
    key_dv = "clearing_price" if domain == "market" else "escalation_index"

    # Deep-copy history so we can grow it without affecting other conditions
    history_data = copy.deepcopy(domain_setup["history_data"])

    # Build system prompt once (graph is fixed for non-adaptive conditions)
    system_prompt = build_forecast_system_prompt(domain, variables, graph_edges)

    predicted = []
    actual_values = []
    n_steps = min(n_forecast, len(trajectory))

    for step in range(n_steps):
        # Format current history (grows each step)
        if domain == "market":
            history_summary = format_market_history(history_data)
        else:
            history_summary = format_conflict_history(history_data)

        # Build 1-step forecast prompt
        user_prompt = build_forecast_prompt(domain, history_summary, key_dv)

        # Call LLM or mock
        if dry_run:
            response_text = mock_forecast_response(domain, history_data)
        else:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            response_text = call_llm(messages, api_key, model, max_tokens=2000)

        # Parse single-value response
        parsed = parse_json_response(response_text)
        val = parsed.get(key_dv)
        if val is not None:
            try:
                predicted.append(float(val))
            except (ValueError, TypeError):
                predicted.append(float("nan"))
        else:
            predicted.append(float("nan"))

        # Record actual
        actual_val = trajectory[step][key_dv]
        actual_values.append(actual_val)

        # Append actual to history for next step
        _append_actual_to_history(domain, history_data, trajectory[step])

    # Score
    scores = score_forecast(predicted, actual_values)

    if verbose:
        print(f"      [{condition_name}] MAE={scores['mae']:.4f}, "
              f"DirAcc={scores.get('directional_accuracy', 'N/A')}, "
              f"Spearman={scores.get('spearman_rho', 'N/A')} "
              f"({n_steps} rolling steps)")

    return {
        "condition": condition_name,
        "predicted": [round(v, 4) for v in predicted],
        "actual": [round(v, 4) for v in actual_values],
        "scores": scores,
        "graph_edges": len(graph_edges) if graph_edges is not None else 0,
        "n_steps": n_steps,
    }


# =============================================================================
# Adaptive condition: revise graph from errors, re-forecast
# =============================================================================

def _run_adaptive_condition(
    domain_setup: dict,
    discovered_edges: list[tuple[str, str]],
    trajectory: list[dict],
    n_forecast: int,
    api_key: str,
    model: str,
    dry_run: bool,
    verbose: bool,
) -> dict:
    """Adaptive condition: rolling forecast with per-step graph revision.

    Each step:
    1. Forecast next period using current graph (1 LLM call)
    2. Reveal actual, record prediction error
    3. Revise graph based on cumulative errors (1 LLM call) — except after last step

    Total: N forecast calls + (N-1) revision calls.

    Returns dict with predictions, scores, per-step graph snapshots, and
    final revision quality vs ground truth.
    """
    domain = domain_setup["domain"]
    variables = domain_setup["variables"]
    key_dv = "clearing_price" if domain == "market" else "escalation_index"

    # Deep-copy history so we can grow it
    history_data = copy.deepcopy(domain_setup["history_data"])

    # Start with discovered graph — will be revised each step
    current_edges = list(discovered_edges)

    predicted = []
    actual_values = []
    graph_snapshots = []  # track graph at each step
    n_steps = min(n_forecast, len(trajectory))

    for step in range(n_steps):
        # Build system prompt with current graph
        system_prompt = build_forecast_system_prompt(domain, variables, current_edges)

        # Format current history
        if domain == "market":
            history_summary = format_market_history(history_data)
        else:
            history_summary = format_conflict_history(history_data)

        # 1-step forecast
        user_prompt = build_forecast_prompt(domain, history_summary, key_dv)

        if dry_run:
            response_text = mock_forecast_response(domain, history_data)
        else:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            response_text = call_llm(messages, api_key, model, max_tokens=2000)

        parsed = parse_json_response(response_text)
        val = parsed.get(key_dv)
        if val is not None:
            try:
                predicted.append(float(val))
            except (ValueError, TypeError):
                predicted.append(float("nan"))
        else:
            predicted.append(float("nan"))

        # Record actual
        actual_val = trajectory[step][key_dv]
        actual_values.append(actual_val)

        # Append actual to history for next step
        _append_actual_to_history(domain, history_data, trajectory[step])

        # Record graph snapshot
        graph_snapshots.append({
            "step": step,
            "n_edges": len(current_edges),
            "edges": list(current_edges),
        })

        # --- Per-step graph revision (skip after last step) ---
        if step < n_steps - 1:
            # Build cumulative error data for revision prompt
            interim_scores = score_forecast(predicted, actual_values)

            revision_prompt = build_graph_revision_prompt(
                domain=domain,
                key_dv=key_dv,
                graph_edges=current_edges,
                predicted=predicted,
                actual=actual_values,
                forecast_scores=interim_scores,
                variables=variables,
            )

            if dry_run:
                revision_text = mock_graph_revision_response(
                    domain, current_edges, variables,
                )
            else:
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": revision_prompt},
                ]
                revision_text = call_llm(messages, api_key, model, max_tokens=4000)

            revision_parsed = parse_json_response(revision_text)
            revised_graph_raw = revision_parsed.get("revised_graph", [])
            revised_edges = []
            for e in revised_graph_raw:
                src = e.get("from", "")
                dst = e.get("to", "")
                if src and dst:
                    revised_edges.append((src, dst))

            if revised_edges:
                current_edges = revised_edges

            if verbose and step < 3:
                # Show first few revisions to avoid wall of text
                print(f"      [adaptive] step {step}: "
                      f"pred={predicted[-1]:.2f} actual={actual_val:.2f} "
                      f"-> {len(current_edges)} edges")

    # Final scoring
    scores = score_forecast(predicted, actual_values)

    # --- Revision quality: original vs final graph against GT ---
    from causal_discovery.ground_truth import (
        edges_to_matrix, precision_recall,
        get_market_ground_truth, get_conflict_ground_truth,
        MARKET_VARIABLES, CONFLICT_VARIABLES,
    )
    if domain == "market":
        gt_matrix = get_market_ground_truth()
        gt_variables = MARKET_VARIABLES
    else:
        gt_matrix = get_conflict_ground_truth()
        gt_variables = CONFLICT_VARIABLES

    original_matrix = edges_to_matrix(discovered_edges, gt_variables)
    final_matrix = edges_to_matrix(current_edges, gt_variables)
    original_quality = precision_recall(original_matrix, gt_matrix)
    final_quality = precision_recall(final_matrix, gt_matrix)

    # Compute edge changes from original to final
    original_set = {(s, d) for s, d in discovered_edges}
    final_set = {(s, d) for s, d in current_edges}
    edges_added = sorted(final_set - original_set)
    edges_removed = sorted(original_set - final_set)

    if verbose:
        print(f"      [adaptive] MAE={scores['mae']:.4f}, "
              f"DirAcc={scores.get('directional_accuracy', 'N/A')}, "
              f"Spearman={scores.get('spearman_rho', 'N/A')} "
              f"({n_steps} rolling steps, {n_steps - 1} revisions)")
        print(f"      [adaptive] Graph: {len(discovered_edges)} -> {len(current_edges)} edges "
              f"(+{len(edges_added)}, -{len(edges_removed)})")
        print(f"      [adaptive] Quality: SHD {original_quality['shd']} -> {final_quality['shd']}, "
              f"P {original_quality['precision']:.2f}->{final_quality['precision']:.2f}, "
              f"R {original_quality['recall']:.2f}->{final_quality['recall']:.2f}")

    return {
        "condition": "adaptive",
        "predicted": [round(v, 4) for v in predicted],
        "actual": [round(v, 4) for v in actual_values],
        "scores": scores,
        "n_steps": n_steps,
        "n_revisions": n_steps - 1,
        "graph_revision": {
            "original_edges": len(discovered_edges),
            "final_edges": len(current_edges),
            "edges_added": edges_added,
            "edges_removed": edges_removed,
        },
        "graph_snapshots": graph_snapshots,
        "revision_quality": {
            "original": {
                "precision": original_quality["precision"],
                "recall": original_quality["recall"],
                "f1": original_quality["f1"],
                "shd": original_quality["shd"],
            },
            "final": {
                "precision": final_quality["precision"],
                "recall": final_quality["recall"],
                "f1": final_quality["f1"],
                "shd": final_quality["shd"],
            },
        },
    }


# =============================================================================
# Main pipeline
# =============================================================================

def run_causal_forecast(
    domain: str = "market",
    n_forecast: int = 10,
    n_scenarios: int = 5,
    forecast_seed_start: int = 100,
    n_warmup: int = 10,
    api_key: str = "",
    model: str = "meta-llama/llama-3.3-70b-instruct",
    graph_source: str = "",
    all_conditions: bool = True,
    adaptive: bool = False,
    dry_run: bool = False,
    output_dir: str = "",
    verbose: bool = True,
) -> dict:
    """Run causal forecasting test across scenarios and conditions.

    Parameters
    ----------
    domain : str
        "market" or "conflict".
    n_forecast : int
        Number of periods to forecast.
    n_scenarios : int
        Number of different-seed scenarios to test.
    forecast_seed_start : int
        Starting seed for forecast scenarios (increments by 1).
    n_warmup : int
        Warmup periods before forecasting.
    api_key : str
        OpenRouter API key.
    model : str
        Model identifier.
    graph_source : str
        Path to pilot_results.json, "ground_truth", or "none".
        If empty and all_conditions=True, runs only GT + no_graph.
    all_conditions : bool
        If True, run all 3 conditions (discovered + GT + no_graph).
    adaptive : bool
        If True, run adaptive condition (revise graph from errors, re-forecast).
        Only active when graph_source is a file path (discovered graph).
    dry_run : bool
        Use mock LLM responses.
    output_dir : str
        Directory to save results.
    verbose : bool
        Print progress.

    Returns
    -------
    dict with per-condition and per-scenario results.
    """
    if verbose:
        print("=" * 60)
        print(f"CAUSAL FORECASTING TEST — {domain.upper()}")
        print(f"Forecast horizon: {n_forecast} periods | Scenarios: {n_scenarios}")
        print(f"Model: {'DRY RUN' if dry_run else model}")
        if adaptive:
            print("Adaptive condition: ENABLED")
        print("=" * 60)

    # Determine which conditions to run
    conditions = {}
    discovered_edges = None
    run_adaptive = False

    # Load discovered graph if provided
    if graph_source and graph_source not in ("ground_truth", "none"):
        if os.path.exists(graph_source):
            discovered_edges = _load_discovered_graph(graph_source)
            conditions["discovered"] = discovered_edges
            if verbose:
                print(f"  Discovered graph: {len(discovered_edges)} edges from {graph_source}")
            if adaptive:
                run_adaptive = True
        else:
            print(f"  [WARNING] Graph source not found: {graph_source}")

    # Adaptive requires discovered graph
    if adaptive and not run_adaptive:
        if verbose:
            print("  [WARNING] --adaptive requires --graph-source file path; skipping adaptive.")

    # Ground truth condition
    if graph_source == "ground_truth" or all_conditions:
        if domain == "market":
            gt_matrix = get_market_ground_truth()
            gt_edges = _gt_to_edge_list(gt_matrix, MARKET_VARIABLES)
        else:
            gt_matrix = get_conflict_ground_truth()
            gt_edges = _gt_to_edge_list(gt_matrix, CONFLICT_VARIABLES)
        conditions["ground_truth"] = gt_edges
        if verbose:
            print(f"  Ground truth graph: {len(gt_edges)} edges")

    # No-graph ablation
    if graph_source == "none" or all_conditions:
        conditions["no_graph"] = None

    if not conditions:
        raise ValueError("No conditions to run. Provide --graph-source or --include-baselines.")

    # Run across scenarios
    all_results = {cond: [] for cond in conditions}
    if run_adaptive:
        all_results["adaptive"] = []
    all_adaptive = []

    for scenario_idx in range(n_scenarios):
        seed = forecast_seed_start + scenario_idx
        if verbose:
            print(f"\n--- Scenario {scenario_idx + 1}/{n_scenarios} (seed={seed}) ---")

        # Setup domain with this seed
        domain_setup = setup_domain(domain, n_warmup=n_warmup, seed=seed)

        # Generate actual trajectory (full dicts)
        trajectory = _generate_actual_trajectory(domain_setup, n_forecast)
        key_dv = "clearing_price" if domain == "market" else "escalation_index"
        actual_values = [p[key_dv] for p in trajectory]

        if verbose:
            print(f"  Actual {key_dv}: [{actual_values[0]:.2f}, ..., {actual_values[-1]:.2f}]")

        # Run each condition (rolling window)
        scenario_results = {}
        for cond_name, graph_edges in conditions.items():
            result = _run_forecast_condition(
                domain_setup=domain_setup,
                graph_edges=graph_edges,
                condition_name=cond_name,
                trajectory=trajectory,
                n_forecast=n_forecast,
                api_key=api_key,
                model=model,
                dry_run=dry_run,
                verbose=verbose,
            )
            result["seed"] = seed
            all_results[cond_name].append(result)
            scenario_results[cond_name] = result

        # Adaptive condition (per-step graph revision)
        if run_adaptive:
            adaptive_result = _run_adaptive_condition(
                domain_setup=domain_setup,
                discovered_edges=discovered_edges,
                trajectory=trajectory,
                n_forecast=n_forecast,
                api_key=api_key,
                model=model,
                dry_run=dry_run,
                verbose=verbose,
            )
            adaptive_result["seed"] = seed
            all_adaptive.append(adaptive_result)
            scenario_results["adaptive"] = adaptive_result

            all_results["adaptive"].append({
                "seed": seed,
                "condition": "adaptive",
                "predicted": adaptive_result["predicted"],
                "scores": adaptive_result["scores"],
            })

        # Save per-scenario results
        if output_dir:
            scenario_dir = Path(output_dir) / "per_scenario"
            scenario_dir.mkdir(parents=True, exist_ok=True)
            with open(scenario_dir / f"scenario_{seed}.json", "w") as f:
                json.dump({
                    "seed": seed,
                    "actual": [round(v, 4) for v in actual_values],
                    "conditions": scenario_results,
                }, f, indent=2, default=str)

    # Aggregate results
    all_cond_keys = dict(conditions)
    if run_adaptive:
        all_cond_keys["adaptive"] = None
    summary = _aggregate_results(all_results, all_cond_keys)

    # Aggregate adaptive graph revision stats
    if run_adaptive and all_adaptive:
        summary["adaptive_graph_revision"] = _aggregate_adaptive_revisions(all_adaptive)

    if verbose:
        print(f"\n{'=' * 60}")
        print("AGGREGATE RESULTS")
        print(f"{'=' * 60}")
        for cond_name in all_cond_keys:
            s = summary["conditions"].get(cond_name, {})
            if s and s.get("mean_mae") is not None:
                print(f"  {cond_name:15s}: MAE={s['mean_mae']:.4f}, "
                      f"DirAcc={s.get('mean_dir_acc', 'N/A')}, "
                      f"Spearman={s.get('mean_spearman', 'N/A')}")

        if run_adaptive and "adaptive_graph_revision" in summary:
            rev = summary["adaptive_graph_revision"]
            print(f"\n  Adaptive graph revision (per-step):")
            print(f"    SHD: {rev['mean_original_shd']:.1f} -> {rev['mean_final_shd']:.1f}")
            print(f"    Edges added: {rev['mean_edges_added']:.1f}, removed: {rev['mean_edges_removed']:.1f}")

    # Save aggregate results
    if output_dir:
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        final = {
            "domain": domain,
            "model": model if not dry_run else "dry_run",
            "n_forecast": n_forecast,
            "n_scenarios": n_scenarios,
            "forecast_seed_start": forecast_seed_start,
            "n_warmup": n_warmup,
            **summary,
        }
        with open(out_path / "results.json", "w") as f:
            json.dump(final, f, indent=2, default=str)

        if verbose:
            print(f"\n  Results saved to: {out_path}")

    return summary


def _aggregate_results(
    all_results: dict[str, list[dict]],
    conditions: dict,
) -> dict:
    """Aggregate per-scenario results into condition-level means."""
    summary = {"conditions": {}}

    for cond_name in conditions:
        results = all_results[cond_name]
        if not results:
            summary["conditions"][cond_name] = {}
            continue

        maes = [r["scores"]["mae"] for r in results if not np.isnan(r["scores"]["mae"])]
        dir_accs = [r["scores"]["directional_accuracy"] for r in results
                    if r["scores"]["directional_accuracy"] is not None]
        spearmans = [r["scores"]["spearman_rho"] for r in results
                     if r["scores"]["spearman_rho"] is not None]

        summary["conditions"][cond_name] = {
            "mean_mae": round(float(np.mean(maes)), 6) if maes else None,
            "std_mae": round(float(np.std(maes)), 6) if maes else None,
            "mean_dir_acc": round(float(np.mean(dir_accs)), 4) if dir_accs else None,
            "mean_spearman": round(float(np.mean(spearmans)), 4) if spearmans else None,
            "per_scenario": [
                {"seed": r["seed"], **r["scores"]} for r in results
            ],
        }

    return summary


def _aggregate_adaptive_revisions(all_adaptive: list[dict]) -> dict:
    """Aggregate adaptive graph revision statistics across scenarios."""
    original_shds = []
    final_shds = []
    edges_added = []
    edges_removed = []

    for ar in all_adaptive:
        rq = ar.get("revision_quality", {})
        orig = rq.get("original", {})
        final = rq.get("final", {})

        if "shd" in orig:
            original_shds.append(orig["shd"])
        if "shd" in final:
            final_shds.append(final["shd"])

        gr = ar.get("graph_revision", {})
        edges_added.append(len(gr.get("edges_added", [])))
        edges_removed.append(len(gr.get("edges_removed", [])))

    return {
        "mean_original_shd": round(float(np.mean(original_shds)), 2) if original_shds else None,
        "mean_final_shd": round(float(np.mean(final_shds)), 2) if final_shds else None,
        "mean_edges_added": round(float(np.mean(edges_added)), 2) if edges_added else None,
        "mean_edges_removed": round(float(np.mean(edges_removed)), 2) if edges_removed else None,
        "per_scenario": [
            {
                "seed": ar.get("seed"),
                "n_revisions": ar.get("n_revisions", 0),
                "original_shd": ar.get("revision_quality", {}).get("original", {}).get("shd"),
                "final_shd": ar.get("revision_quality", {}).get("final", {}).get("shd"),
                "edges_added": len(ar.get("graph_revision", {}).get("edges_added", [])),
                "edges_removed": len(ar.get("graph_revision", {}).get("edges_removed", [])),
            }
            for ar in all_adaptive
        ],
    }


# =============================================================================
# CLI
# =============================================================================

def _load_api_key() -> str:
    """Load API key from env, .Renviron, or config module."""
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        renviron = Path(__file__).parent.parent / ".Renviron"
        if renviron.exists():
            for line in renviron.read_text().splitlines():
                if line.startswith("OPENROUTER_API_KEY="):
                    api_key = line.split("=", 1)[1].strip()
                    break
    if not api_key:
        try:
            from archive.wargame_forecasting.config import OPENROUTER_API_KEY
            api_key = OPENROUTER_API_KEY
        except ImportError:
            pass
    return api_key


def main():
    parser = argparse.ArgumentParser(
        description="Causal Forecasting Test — does causal knowledge improve prediction?"
    )
    parser.add_argument("--domain", choices=["market", "conflict"], default="market")
    parser.add_argument("--n-forecast", type=int, default=10,
                        help="Number of periods to forecast")
    parser.add_argument("--n-scenarios", type=int, default=5,
                        help="Number of different-seed scenarios")
    parser.add_argument("--forecast-seed-start", type=int, default=100,
                        help="Starting seed for forecast scenarios")
    parser.add_argument("--n-warmup", type=int, default=10,
                        help="Warmup periods before forecasting")
    parser.add_argument("--model", default="meta-llama/llama-3.3-70b-instruct")
    parser.add_argument("--graph-source", default="",
                        help="Path to pilot_results.json, 'ground_truth', or 'none'")
    parser.add_argument("--all-conditions", action="store_true", default=True,
                        help="Run all 3 conditions (discovered + GT + no_graph)")
    parser.add_argument("--only-source", action="store_true",
                        help="Only run the specified graph-source condition")
    parser.add_argument("--adaptive", action="store_true",
                        help="Run adaptive condition (revise graph from errors, re-forecast)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Use mock LLM responses")
    parser.add_argument("--output-dir", default="",
                        help="Directory to save results (auto-generated if empty)")
    parser.add_argument("--quiet", action="store_true")

    args = parser.parse_args()

    all_conditions = not args.only_source

    # Auto-generate output dir
    output_dir = args.output_dir
    if not output_dir:
        model_slug = args.model.split("/")[-1].replace("-instruct", "")
        output_dir = f"outputs/causal_discovery/causal_forecast/{args.domain}_{model_slug}"

    # Load API key
    api_key = ""
    if not args.dry_run:
        api_key = _load_api_key()
        if not api_key:
            print("[ERROR] No API key found. Set OPENROUTER_API_KEY or use --dry-run.")
            sys.exit(1)

    run_causal_forecast(
        domain=args.domain,
        n_forecast=args.n_forecast,
        n_scenarios=args.n_scenarios,
        forecast_seed_start=args.forecast_seed_start,
        n_warmup=args.n_warmup,
        api_key=api_key,
        model=args.model,
        graph_source=args.graph_source,
        all_conditions=all_conditions,
        adaptive=args.adaptive,
        dry_run=args.dry_run,
        output_dir=output_dir,
        verbose=not args.quiet,
    )


if __name__ == "__main__":
    main()
