"""
Run all 26 experimental conditions (13 per domain).

Usage:
    python -m forecast_multi.run_all --api-key <key> [--model llama] [--resume]
    python -m forecast_multi.run_all --api-key <key> --domain market   # one domain only
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from forecast_multi.config import DESIGN_MATRIX
from forecast_multi.runner import run_experiment


def main():
    parser = argparse.ArgumentParser(description="Run all forecast_multi conditions")
    parser.add_argument("--api-key", default=None, help="OpenRouter API key (or set OPENROUTER_API_KEY)")
    parser.add_argument("--model", default="llama")
    parser.add_argument("--domain", default=None, choices=["market", "conflict"],
                        help="Run only one domain (default: both)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--start-period", type=int, default=5)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Print conditions without running")
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key and not args.dry_run:
        print("[ERROR] Set OPENROUTER_API_KEY or pass --api-key")
        sys.exit(1)

    domains = [args.domain] if args.domain else ["market", "conflict"]
    baseline_dirs = {
        "market": "outputs/market_baseline",
        "conflict": "outputs/conflict_baseline",
    }

    # Build ordered condition list
    comm_order = ["single", "independent", "debate", "specialization"]
    level_order = ["L0", "L1", "L2", "L3"]
    conditions = []
    for comm in comm_order:
        for level in level_order:
            if (comm, level) in DESIGN_MATRIX:
                conditions.append((comm, level))

    print("=" * 70)
    print("FULL EXPERIMENT RUN")
    print(f"  Domains:    {domains}")
    print(f"  Conditions: {len(conditions)} per domain")
    print(f"  Model:      {args.model}")
    print(f"  Resume:     {args.resume}")
    print(f"  Seed:       {args.seed}")
    print("=" * 70)

    for i, (comm, level) in enumerate(conditions):
        print(f"\n  [{i+1}/{len(conditions)}] {comm} × {level}")
    print()

    if args.dry_run:
        print("[DRY RUN] Would run the above conditions. Exiting.")
        return

    # Track results
    results_log = []
    t0_global = time.time()

    for domain in domains:
        baseline_dir = baseline_dirs[domain]
        print(f"\n{'#' * 70}")
        print(f"# DOMAIN: {domain.upper()}")
        print(f"{'#' * 70}")

        for i, (comm, level) in enumerate(conditions):
            condition_name = f"{domain}_{comm}_{level}"
            output_dir = f"outputs/forecast_multi/{condition_name}"

            # Skip if already complete (checkpoint has all scenarios)
            if args.resume:
                ckpt_path = Path(output_dir) / "checkpoint.json"
                if ckpt_path.exists():
                    with open(ckpt_path) as f:
                        ckpt = json.load(f)
                    n_done = len(ckpt.get("completed_scenarios", []))
                    if n_done >= 10:  # all scenarios done
                        print(f"\n[{i+1}/{len(conditions)}] {condition_name} — SKIP (complete, {n_done} scenarios)")
                        results_log.append({
                            "condition": condition_name,
                            "status": "skipped",
                            "reason": f"already complete ({n_done} scenarios)",
                        })
                        continue

            print(f"\n{'='*70}")
            print(f"[{i+1}/{len(conditions)}] {condition_name}")
            print(f"{'='*70}")

            t0 = time.time()
            try:
                result = run_experiment(
                    domain_name=domain,
                    communication=comm,
                    info_level=level,
                    model=args.model,
                    baseline_dir=baseline_dir,
                    output_dir=output_dir,
                    api_key=api_key,
                    start_period=args.start_period,
                    seed=args.seed,
                    resume=args.resume,
                )
                elapsed = time.time() - t0
                summary = result.get("summary", {})
                results_log.append({
                    "condition": condition_name,
                    "status": "complete",
                    "elapsed_seconds": round(elapsed, 1),
                    "n_forecasts": summary.get("n_final_forecasts", 0),
                    "brier": summary.get("brier_score"),
                    "accuracy": summary.get("accuracy"),
                    "llm_calls": summary.get("llm_stats", {}).get("total_calls", 0),
                })
                print(f"\n  [{condition_name}] DONE in {elapsed:.0f}s")
            except Exception as e:
                elapsed = time.time() - t0
                print(f"\n  [{condition_name}] FAILED after {elapsed:.0f}s: {e}")
                results_log.append({
                    "condition": condition_name,
                    "status": "failed",
                    "error": str(e),
                    "elapsed_seconds": round(elapsed, 1),
                })

    # Print final summary
    total_elapsed = time.time() - t0_global
    print(f"\n\n{'#' * 70}")
    print(f"# EXPERIMENT COMPLETE — {total_elapsed/3600:.1f} hours")
    print(f"{'#' * 70}\n")

    print(f"{'Condition':<35} {'Status':<10} {'Time':>8} {'Calls':>7} {'Brier':>8} {'Acc':>7}")
    print("-" * 80)
    for r in results_log:
        status = r["status"]
        elapsed = r.get("elapsed_seconds", 0)
        calls = r.get("llm_calls", "")
        brier = r.get("brier")
        acc = r.get("accuracy")
        brier_str = f"{brier:.4f}" if brier is not None else ""
        acc_str = f"{acc:.1f}%" if acc is not None else ""
        time_str = f"{elapsed:.0f}s" if elapsed else ""
        print(f"{r['condition']:<35} {status:<10} {time_str:>8} {str(calls):>7} {brier_str:>8} {acc_str:>7}")

    # Save run log
    log_path = Path("outputs/forecast_multi/run_log.json")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "w") as f:
        json.dump({
            "total_elapsed_hours": round(total_elapsed / 3600, 2),
            "conditions": results_log,
        }, f, indent=2)
    print(f"\nRun log saved to {log_path}")


if __name__ == "__main__":
    main()
