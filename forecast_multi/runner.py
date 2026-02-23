"""
Runner — main CLI and experiment loop for the multi-agent forecasting framework.

Usage:
    python -m forecast_multi.runner \\
        --domain market \\
        --communication single \\
        --info-level L0 \\
        --model llama \\
        --baseline-dir outputs/market_baseline \\
        --output-dir outputs/forecast_multi/market_single_L0 \\
        --start-period 5 \\
        --seed 42
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from forecast_multi import info_builder
from forecast_multi.config import (
    get_debate_pair,
    get_ensemble_personas,
    get_subgraphs,
)
from forecast_multi.debate import DebateForecaster
from forecast_multi.domain import get_domain
from forecast_multi.evaluation import (
    brier_score,
    compute_baselines,
    compute_f1,
    log_score,
    pred_class_from_probs,
)
from forecast_multi.independent import IndependentEnsemble
from forecast_multi.llm_client import LLMClient, resolve_model
from forecast_multi.single import SingleForecaster
from forecast_multi.specialization import SpecializationForecaster


# ---------------------------------------------------------------------------
# Experiment runner
# ---------------------------------------------------------------------------

def run_experiment(
    domain_name: str,
    communication: str,
    info_level: str,
    model: str,
    baseline_dir: str,
    output_dir: str,
    api_key: str,
    start_period: int = 5,
    seed: int = 42,
    temperature: float = 0.7,
    n_forecasters: int = 5,
    mechanistic_aggregator: bool = False,
    history_window: int = 10,
    scenarios_subset: list[int] | None = None,
    resume: bool = False,
) -> dict:
    """Run a single experimental condition.

    Parameters
    ----------
    domain_name : "market" or "conflict"
    communication : "single", "independent", "debate", "specialization"
    info_level : "L0", "L1", "L2", "L3"
    model : model name or alias
    baseline_dir : path to baseline simulation output
    output_dir : path for results
    api_key : OpenRouter API key
    start_period : first period to forecast from
    seed : random seed
    temperature : LLM temperature
    n_forecasters : number of independent forecasters
    mechanistic_aggregator : use mechanistic aggregation for specialization
    history_window : periods of history to show
    scenarios_subset : optional list of scenario indices to run
    resume : resume from checkpoint if available
    """
    domain = get_domain(domain_name)
    model_id = resolve_model(model)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # Load scenarios
    scenarios = domain.load_scenarios(Path(baseline_dir))
    if not scenarios:
        print(f"[ERROR] No scenario files in {baseline_dir}")
        return {}

    if scenarios_subset is not None:
        scenarios = [scenarios[i] for i in scenarios_subset if i < len(scenarios)]

    # Initialize LLM client
    client = LLMClient(
        api_key=api_key,
        model=model_id,
        temperature=temperature,
        max_tokens=400,
    )

    # Initialize communication structure
    comm = _build_comm_structure(
        communication, domain_name, client, n_forecasters, mechanistic_aggregator,
    )

    # Checkpoint handling
    checkpoint_path = out_path / "checkpoint.json"
    completed_scenarios = set()
    if resume and checkpoint_path.exists():
        with open(checkpoint_path) as f:
            ckpt = json.load(f)
        completed_scenarios = set(ckpt.get("completed_scenarios", []))
        print(f"[RESUME] Skipping {len(completed_scenarios)} completed scenarios")

    # Print header
    condition = f"{domain_name}_{communication}_{info_level}"
    print("=" * 70)
    print(f"MULTI-AGENT FORECASTING EXPERIMENT")
    print(f"  Condition:     {condition}")
    print(f"  Domain:        {domain_name}")
    print(f"  Communication: {communication}")
    print(f"  Info level:    {info_level}")
    print(f"  Model:         {model_id}")
    print(f"  Scenarios:     {len(scenarios)}")
    print(f"  Start period:  {start_period}")
    print(f"  Output:        {out_path}")
    print("=" * 70)

    all_rows = []
    all_details = []
    t0 = time.time()

    csv_path = out_path / "forecast_results.csv"
    detail_path = out_path / "forecast_details.json"

    for s_idx, scenario in enumerate(scenarios):
        sid = scenario.get("summary", {}).get("scenario_id", f"scenario_{s_idx}")

        if sid in completed_scenarios:
            print(f"  [{s_idx+1}/{len(scenarios)}] {sid} — skipped (checkpoint)")
            continue

        n_periods = domain.get_n_periods(scenario)
        target_history = domain.get_target_history(scenario)
        print(f"\n[{s_idx+1}/{len(scenarios)}] {sid} ({n_periods} periods)")

        for t in range(start_period, n_periods - 1):
            # 1. Base prompt
            base_prompt = domain.build_base_prompt(scenario, t, window=history_window)

            # 2. Information section
            info_section = info_builder.build(
                domain, scenario, t, info_level, seed=seed,
            )

            # 3. Full prompt
            full_prompt = base_prompt + info_section

            # 4. Get system prompt
            if communication == "single":
                sys_prompt = domain.get_system_prompt(SingleForecaster.get_persona_prompt())
            else:
                sys_prompt = domain.get_system_prompt()

            # 5. Run forecast
            if communication == "specialization":
                expanded_vars = domain.get_expanded_variables(scenario, t)
                result = comm.forecast(
                    domain, sys_prompt, full_prompt,
                    expanded_vars=expanded_vars,
                )
            else:
                result = comm.forecast(domain, sys_prompt, full_prompt)

            # 6. Evaluate
            actual_val = domain.get_actual(scenario, t + 1)
            current_val = domain.get_actual(scenario, t)
            actual_dir = domain.classify_direction(current_val, actual_val)

            for forecast in result["forecasts"]:
                row = _build_row(
                    domain, forecast, sid, t, actual_dir,
                    current_val, actual_val,
                    communication, info_level,
                )
                all_rows.append(row)
                all_details.append({
                    **row,
                    "reasoning": forecast.get("reasoning", ""),
                })

            # Also add ensemble row (unless single)
            if communication != "single":
                ens = result["ensemble"]
                ens_row = _build_row(
                    domain, ens, sid, t, actual_dir,
                    current_val, actual_val,
                    communication, info_level,
                )
                all_rows.append(ens_row)
                all_details.append({
                    **ens_row,
                    "reasoning": ens.get("reasoning", ""),
                })

            # Progress
            if (t - start_period) % 5 == 0:
                # Filter to ensemble/final rows for running metrics
                final_rows = [
                    r for r in all_rows
                    if r["round"] == "final"
                ]
                if final_rows:
                    f1 = compute_f1(final_rows)["macro_f1"]
                    bs_mean = np.mean([r["brier_score"] for r in final_rows])
                    print(
                        f"  t={t+1:3d} | actual={actual_dir:4s} | "
                        f"running: F1={f1:.3f}, brier={bs_mean:.3f} "
                        f"({len(final_rows)} final forecasts)"
                    )

        # Save checkpoint after each scenario
        completed_scenarios.add(sid)
        _save_checkpoint(checkpoint_path, completed_scenarios, condition)

        # Incremental CSV save
        _save_csv(csv_path, all_rows)

    elapsed = time.time() - t0

    # Save full results
    with open(detail_path, "w") as f:
        json.dump(all_details, f, indent=2)

    # Compute and print summary
    summary = _print_summary(all_rows, client.stats, elapsed, out_path)

    # Save summary
    with open(out_path / "forecast_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    return {"rows": all_rows, "details": all_details, "summary": summary}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_comm_structure(
    communication: str,
    domain_name: str,
    client: LLMClient,
    n_forecasters: int,
    mechanistic_aggregator: bool,
):
    """Instantiate the appropriate communication structure."""
    if communication == "single":
        return SingleForecaster(client)
    elif communication == "independent":
        personas = get_ensemble_personas(domain_name)[:n_forecasters]
        return IndependentEnsemble(client, personas)
    elif communication == "debate":
        pair = get_debate_pair(domain_name)
        return DebateForecaster(client, pair[0], pair[1])
    elif communication == "specialization":
        subgraphs = get_subgraphs(domain_name)
        return SpecializationForecaster(client, subgraphs, mechanistic_aggregator)
    else:
        raise ValueError(f"Unknown communication structure: {communication}")


def _build_row(
    domain,
    forecast: dict,
    scenario_id: str,
    period: int,
    actual_dir: str,
    current_val: float,
    actual_val: float,
    communication: str,
    info_level: str,
) -> dict:
    """Build a result row from a forecast."""
    bs = brier_score(forecast, actual_dir)
    ls = log_score(forecast, actual_dir)
    pred_class = pred_class_from_probs(forecast)

    # Point estimate error
    point_est = domain.parse_point_estimate(forecast)
    if point_est is not None:
        err = domain.point_estimate_error(point_est, actual_val)
        value_error = err["value_error"]
        value_pct_error = err["value_pct_error"]
    else:
        value_error = None
        value_pct_error = None

    return {
        "scenario_id": scenario_id,
        "period": period + 1,
        "communication": communication,
        "info_level": info_level,
        "forecaster_id": forecast.get("forecaster_id", "unknown"),
        "round": forecast.get("round", "final"),
        "actual": actual_dir,
        "pred_class": pred_class,
        "correct": int(pred_class == actual_dir),
        "prob_up": forecast["prob_up"],
        "prob_down": forecast["prob_down"],
        "prob_flat": forecast["prob_flat"],
        "predicted_value": round(point_est, 4) if point_est is not None else "",
        "actual_value": round(actual_val, 4),
        "value_error": round(value_error, 4) if value_error is not None else "",
        "value_pct_error": round(value_pct_error, 4) if value_pct_error is not None else "",
        "brier_score": round(bs, 4),
        "log_score": round(ls, 4),
        "source": forecast.get("source", "unknown"),
    }


def _save_csv(path: Path, rows: list[dict]):
    """Save forecast results to CSV."""
    if not rows:
        return
    fieldnames = [
        "scenario_id", "period", "communication", "info_level",
        "forecaster_id", "round",
        "actual", "pred_class", "correct",
        "prob_up", "prob_down", "prob_flat",
        "predicted_value", "actual_value", "value_error", "value_pct_error",
        "brier_score", "log_score", "source",
    ]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows([{k: r.get(k, "") for k in fieldnames} for r in rows])


def _save_checkpoint(path: Path, completed: set, condition: str):
    """Save checkpoint with completed scenarios."""
    with open(path, "w") as f:
        json.dump({
            "completed_scenarios": sorted(completed),
            "condition": condition,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }, f, indent=2)


def _print_summary(
    rows: list[dict],
    stats,
    elapsed: float,
    out_path: Path,
) -> dict:
    """Print and return experiment summary."""
    if not rows:
        print("\n[WARN] No forecasts completed")
        return {}

    print(f"\n{'='*70}")
    print("EXPERIMENT SUMMARY")
    print(f"{'='*70}")

    # Filter to final/ensemble rows for aggregate metrics
    final_rows = [r for r in rows if r["round"] == "final"]
    n_total = len(rows)
    n_final = len(final_rows)
    n_fallback = sum(1 for r in rows if r["source"] == "fallback")

    print(f"  Total forecasts:  {n_total} ({n_final} final)")
    print(f"  LLM calls:        {stats.total_calls}")
    print(f"  Fallbacks:        {n_fallback}")
    print(f"  Total tokens:     {stats.total_tokens:,}")
    print(f"  Elapsed:          {elapsed:.1f}s")

    if final_rows:
        acc = np.mean([r["correct"] for r in final_rows]) * 100
        bs_mean = np.mean([r["brier_score"] for r in final_rows])
        ls_mean = np.mean([r["log_score"] for r in final_rows])

        print(f"\n  Final forecast metrics:")
        print(f"    Accuracy:     {acc:.1f}%")
        print(f"    Brier score:  {bs_mean:.4f}  (uniform: 0.667)")
        print(f"    Log score:    {ls_mean:.4f}  (uniform: 1.099)")

        f1 = compute_f1(final_rows)
        print(f"    Macro F1:     {f1['macro_f1']:.3f}")
        for cls in ("UP", "DOWN", "FLAT"):
            c = f1[cls]
            print(f"      {cls:5s}: P={c['precision']:.3f} R={c['recall']:.3f} F1={c['f1']:.3f}")

        # Value prediction metrics
        val_errors = [
            r["value_pct_error"] for r in final_rows
            if r["value_pct_error"] != "" and r["value_pct_error"] is not None
        ]
        if val_errors:
            mae_pct = np.mean(val_errors)
            med_pct = np.median(val_errors)
            print(f"\n    Value MAE (%): {mae_pct:.2f}%  (median: {med_pct:.2f}%)")

        # Baselines
        baselines = compute_baselines(final_rows)
        if baselines:
            print(f"\n  Baselines:")
            dist = baselines["class_distribution"]
            print(f"    Class dist: UP={dist['UP']:.3f} DOWN={dist['DOWN']:.3f} FLAT={dist['FLAT']:.3f}")
            print(f"    Uniform:    brier={baselines['uniform']['brier']:.4f}, log={baselines['uniform']['log']:.4f}")
            print(f"    Majority:   brier={baselines['majority']['brier']:.4f}, log={baselines['majority']['log']:.4f} ({baselines['majority']['class']})")
            print(f"    Frequency:  brier={baselines['frequency']['brier']:.4f}, log={baselines['frequency']['log']:.4f}")

    print(f"{'='*70}")

    summary = {
        "condition": f"{rows[0]['communication']}_{rows[0]['info_level']}" if rows else "",
        "n_total_forecasts": n_total,
        "n_final_forecasts": n_final,
        "n_fallbacks": n_fallback,
        "llm_stats": stats.to_dict(),
        "elapsed_seconds": round(elapsed, 1),
    }
    if final_rows:
        summary["accuracy"] = round(float(np.mean([r["correct"] for r in final_rows]) * 100), 2)
        summary["brier_score"] = round(float(np.mean([r["brier_score"] for r in final_rows])), 4)
        summary["log_score"] = round(float(np.mean([r["log_score"] for r in final_rows])), 4)
        summary["f1"] = compute_f1(final_rows)
        summary["baselines"] = compute_baselines(final_rows)

    return summary


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Multi-agent forecasting experiment runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--domain", required=True, choices=["market", "conflict"])
    parser.add_argument("--communication", required=True,
                        choices=["single", "independent", "debate", "specialization"])
    parser.add_argument("--info-level", required=True, choices=["L0", "L1", "L2", "L3"])
    parser.add_argument("--model", default="llama",
                        help="Model name or alias (default: llama)")
    parser.add_argument("--baseline-dir", required=True,
                        help="Path to baseline simulation output")
    parser.add_argument("--output-dir", default=None,
                        help="Output directory (default: auto-named)")
    parser.add_argument("--start-period", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--n-forecasters", type=int, default=5,
                        help="Number of independent forecasters")
    parser.add_argument("--mechanistic-aggregator", action="store_true",
                        help="Use mechanistic (averaging) aggregation for specialization")
    parser.add_argument("--history-window", type=int, default=10)
    parser.add_argument("--scenarios", type=int, nargs="+", default=None,
                        help="Scenario indices to run (default: all)")
    parser.add_argument("--resume", action="store_true",
                        help="Resume from checkpoint")

    args = parser.parse_args()

    # API key
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        print("[ERROR] Set OPENROUTER_API_KEY environment variable")
        sys.exit(1)

    # Auto-generate output directory name
    if args.output_dir is None:
        output_dir = (
            f"outputs/forecast_multi/"
            f"{args.domain}_{args.communication}_{args.info_level}"
        )
    else:
        output_dir = args.output_dir

    run_experiment(
        domain_name=args.domain,
        communication=args.communication,
        info_level=args.info_level,
        model=args.model,
        baseline_dir=args.baseline_dir,
        output_dir=output_dir,
        api_key=api_key,
        start_period=args.start_period,
        seed=args.seed,
        temperature=args.temperature,
        n_forecasters=args.n_forecasters,
        mechanistic_aggregator=args.mechanistic_aggregator,
        history_window=args.history_window,
        scenarios_subset=args.scenarios,
        resume=args.resume,
    )


if __name__ == "__main__":
    main()
