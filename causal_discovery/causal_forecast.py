"""
Causal Forecasting Test — Can causal knowledge improve time-series prediction?

The agent receives a previously-discovered causal graph + warmup time-series
from a new scenario (same ground truth structure, different seed) and forecasts
the next N periods for the key DV (clearing_price / escalation_index).

Three conditions per run:
- discovered: model's own graph from a prior causal discovery run
- ground_truth: actual GT adjacency matrix (performance ceiling)
- no_graph: no causal structure, just history (ablation)

Scoring: MAE, directional accuracy, Spearman rho.
Naive baselines: last-value and linear trend (programmatic, no LLM).

Usage:
    # Dry run
    python -m causal_discovery.causal_forecast --domain market --dry-run

    # With discovered graph + baselines
    python -m causal_discovery.causal_forecast --domain market \\
        --graph-source outputs/causal_discovery/single_agent/market_single/pilot_results.json \\
        --include-baselines

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

def _generate_actual_trajectory(domain_setup: dict, n_periods: int) -> list[float]:
    """Run simulation forward from post-warmup snapshot, return key DV series."""
    domain = domain_setup["domain"]

    if domain == "market":
        return _generate_market_trajectory(domain_setup, n_periods)
    else:
        return _generate_conflict_trajectory(domain_setup, n_periods)


def _generate_market_trajectory(domain_setup: dict, n_periods: int) -> list[float]:
    """Run market sim forward, extract clearing_price series."""
    from causal_discovery.intervention import _run_market_rollout

    state = copy.deepcopy(domain_setup["state_snapshot"])
    agents = copy.deepcopy(domain_setup["agents_snapshot"])
    base_params = copy.deepcopy(domain_setup["base_params"])

    trajectory = _run_market_rollout(
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

    return [period["clearing_price"] for period in trajectory]


def _generate_conflict_trajectory(domain_setup: dict, n_periods: int) -> list[float]:
    """Run conflict sim forward, extract escalation_index series."""
    from causal_discovery.intervention import _run_conflict_rollout

    state = copy.deepcopy(domain_setup["state_snapshot"])
    agents_config = copy.deepcopy(domain_setup["agents_snapshot"])

    trajectory = _run_conflict_rollout(
        state=state,
        agents_config=agents_config,
        shocks=domain_setup["shocks"],
        start_period=domain_setup["start_period"],
        n_periods=n_periods,
        overrides=None,
        rule_based=True,
        llm_pool=None,
    )

    return [period["escalation_index"] for period in trajectory]


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


def _compute_naive_baselines(
    warmup_values: list[float], actual: list[float], n_forecast: int,
) -> dict:
    """Last-value and trend baselines scored against actual."""
    if not warmup_values or not actual:
        return {"last_value": {}, "trend": {}}

    last_val = warmup_values[-1]
    n = min(n_forecast, len(actual))

    # Last-value baseline: repeat final warmup value
    last_value_pred = [last_val] * n
    last_value_scores = score_forecast(last_value_pred, actual[:n])

    # Trend baseline: linear extrapolation from last 3 warmup points
    n_trend = min(3, len(warmup_values))
    recent = warmup_values[-n_trend:]
    if n_trend >= 2:
        # Fit linear trend
        x = np.arange(n_trend)
        slope = np.polyfit(x, recent, 1)[0]
        trend_pred = [last_val + slope * (i + 1) for i in range(n)]
    else:
        trend_pred = last_value_pred  # fallback to flat

    trend_scores = score_forecast(trend_pred, actual[:n])

    return {
        "last_value": {
            "predictions": [round(v, 4) for v in last_value_pred],
            **last_value_scores,
        },
        "trend": {
            "predictions": [round(v, 4) for v in trend_pred],
            "slope": round(float(slope), 6) if n_trend >= 2 else 0.0,
            **trend_scores,
        },
    }


# =============================================================================
# Single condition x single scenario
# =============================================================================

def _run_forecast_condition(
    domain_setup: dict,
    graph_edges: list[tuple[str, str]] | None,
    condition_name: str,
    actual: list[float],
    n_forecast: int,
    api_key: str,
    model: str,
    dry_run: bool,
    verbose: bool,
) -> dict:
    """Run one forecast condition on one scenario.

    Returns dict with predicted values, scores, and raw response.
    """
    domain = domain_setup["domain"]
    variables = domain_setup["variables"]
    history_data = domain_setup["history_data"]
    key_dv = "clearing_price" if domain == "market" else "escalation_index"

    # Build system prompt
    system_prompt = build_forecast_system_prompt(domain, variables, graph_edges)

    # Build history summary
    if domain == "market":
        history_summary = format_market_history(history_data)
    else:
        history_summary = format_conflict_history(history_data)

    # Build forecast prompt
    user_prompt = build_forecast_prompt(domain, history_summary, n_forecast, key_dv)

    # Call LLM or mock
    if dry_run:
        response_text = mock_forecast_response(domain, n_forecast, history_data)
    else:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        response_text = call_llm(messages, api_key, model, max_tokens=4000)

    # Parse response
    parsed = parse_json_response(response_text)
    forecasts = parsed.get("forecasts", [])

    # Extract predicted values
    predicted = []
    for f in forecasts:
        val = f.get(key_dv)
        if val is not None:
            try:
                predicted.append(float(val))
            except (ValueError, TypeError):
                pass

    # Score
    scores = score_forecast(predicted, actual)

    if verbose:
        print(f"      [{condition_name}] MAE={scores['mae']:.4f}, "
              f"DirAcc={scores.get('directional_accuracy', 'N/A')}, "
              f"Spearman={scores.get('spearman_rho', 'N/A')}")

    return {
        "condition": condition_name,
        "predicted": [round(v, 4) for v in predicted],
        "actual": [round(v, 4) for v in actual[:len(predicted)]],
        "scores": scores,
        "graph_edges": len(graph_edges) if graph_edges is not None else 0,
        "overall_reasoning": parsed.get("overall_reasoning", ""),
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
    include_baselines: bool = True,
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
        If empty and include_baselines=True, runs only GT + no_graph.
    include_baselines : bool
        If True, run all applicable conditions (discovered + GT + no_graph).
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
        print("=" * 60)

    # Determine which conditions to run
    conditions = {}

    # Load discovered graph if provided
    if graph_source and graph_source not in ("ground_truth", "none"):
        if os.path.exists(graph_source):
            discovered_edges = _load_discovered_graph(graph_source)
            conditions["discovered"] = discovered_edges
            if verbose:
                print(f"  Discovered graph: {len(discovered_edges)} edges from {graph_source}")
        else:
            print(f"  [WARNING] Graph source not found: {graph_source}")

    # Ground truth condition
    if graph_source == "ground_truth" or include_baselines:
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
    if graph_source == "none" or include_baselines:
        conditions["no_graph"] = None

    if not conditions:
        raise ValueError("No conditions to run. Provide --graph-source or --include-baselines.")

    # Run across scenarios
    all_results = {cond: [] for cond in conditions}
    all_baselines = []

    for scenario_idx in range(n_scenarios):
        seed = forecast_seed_start + scenario_idx
        if verbose:
            print(f"\n--- Scenario {scenario_idx + 1}/{n_scenarios} (seed={seed}) ---")

        # Setup domain with this seed
        domain_setup = setup_domain(domain, n_warmup=n_warmup, seed=seed)

        # Generate actual trajectory
        actual = _generate_actual_trajectory(domain_setup, n_forecast)
        if verbose:
            key_dv = "clearing_price" if domain == "market" else "escalation_index"
            print(f"  Actual {key_dv}: [{actual[0]:.2f}, ..., {actual[-1]:.2f}]")

        # Get warmup values for naive baselines
        if domain == "market":
            warmup_values = domain_setup["history_data"].get("price_history", [])
        else:
            warmup_values = domain_setup["history_data"].get("escalation_history", [])

        # Naive baselines (programmatic)
        baselines = _compute_naive_baselines(warmup_values, actual, n_forecast)
        baselines["seed"] = seed
        all_baselines.append(baselines)

        if verbose:
            print(f"  Naive baselines:")
            print(f"    Last-value MAE={baselines['last_value'].get('mae', 'N/A')}")
            print(f"    Trend MAE={baselines['trend'].get('mae', 'N/A')}")

        # Run each condition
        scenario_results = {}
        for cond_name, graph_edges in conditions.items():
            result = _run_forecast_condition(
                domain_setup=domain_setup,
                graph_edges=graph_edges,
                condition_name=cond_name,
                actual=actual,
                n_forecast=n_forecast,
                api_key=api_key,
                model=model,
                dry_run=dry_run,
                verbose=verbose,
            )
            result["seed"] = seed
            all_results[cond_name].append(result)
            scenario_results[cond_name] = result

        # Save per-scenario results
        if output_dir:
            scenario_dir = Path(output_dir) / "per_scenario"
            scenario_dir.mkdir(parents=True, exist_ok=True)
            with open(scenario_dir / f"scenario_{seed}.json", "w") as f:
                json.dump({
                    "seed": seed,
                    "actual": [round(v, 4) for v in actual],
                    "warmup_values": [round(v, 4) for v in warmup_values],
                    "conditions": scenario_results,
                    "naive_baselines": baselines,
                }, f, indent=2, default=str)

    # Aggregate results
    summary = _aggregate_results(all_results, all_baselines, conditions)

    if verbose:
        print(f"\n{'=' * 60}")
        print("AGGREGATE RESULTS")
        print(f"{'=' * 60}")
        for cond_name in conditions:
            s = summary["conditions"][cond_name]
            print(f"  {cond_name:15s}: MAE={s['mean_mae']:.4f}, "
                  f"DirAcc={s.get('mean_dir_acc', 'N/A')}, "
                  f"Spearman={s.get('mean_spearman', 'N/A')}")
        print(f"  {'last_value':15s}: MAE={summary['naive_baselines']['last_value']['mean_mae']:.4f}")
        print(f"  {'trend':15s}: MAE={summary['naive_baselines']['trend']['mean_mae']:.4f}")

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
    all_baselines: list[dict],
    conditions: dict,
) -> dict:
    """Aggregate per-scenario results into condition-level means."""
    summary = {"conditions": {}, "naive_baselines": {}}

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

    # Aggregate naive baselines
    for baseline_type in ("last_value", "trend"):
        baseline_maes = [
            b[baseline_type].get("mae")
            for b in all_baselines
            if b[baseline_type].get("mae") is not None
            and not np.isnan(b[baseline_type]["mae"])
        ]
        summary["naive_baselines"][baseline_type] = {
            "mean_mae": round(float(np.mean(baseline_maes)), 6) if baseline_maes else None,
            "std_mae": round(float(np.std(baseline_maes)), 6) if baseline_maes else None,
        }

    return summary


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
    parser.add_argument("--include-baselines", action="store_true", default=True,
                        help="Run all 3 conditions (discovered + GT + no_graph)")
    parser.add_argument("--no-baselines", action="store_true",
                        help="Only run the specified graph-source condition")
    parser.add_argument("--dry-run", action="store_true",
                        help="Use mock LLM responses")
    parser.add_argument("--output-dir", default="",
                        help="Directory to save results (auto-generated if empty)")
    parser.add_argument("--quiet", action="store_true")

    args = parser.parse_args()

    include_baselines = not args.no_baselines

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
        include_baselines=include_baselines,
        dry_run=args.dry_run,
        output_dir=output_dir,
        verbose=not args.quiet,
    )


if __name__ == "__main__":
    main()
