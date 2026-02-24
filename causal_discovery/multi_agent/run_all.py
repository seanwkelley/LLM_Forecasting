"""
Sweep all multi-agent causal discovery conditions across both domains.

Usage:
    python -m causal_discovery.multi_agent.run_all --dry-run
    python -m causal_discovery.multi_agent.run_all --budget 5
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from causal_discovery.multi_agent.runner import run_condition, _load_api_key


# Conditions: (communication, extra kwargs)
CONDITIONS = [
    ("single", {}),
    ("independent", {}),
    ("debate", {}),
    ("specialization", {}),
]

DOMAINS = ["market", "conflict"]


def run_all(
    budget: int = 30,
    n_warmup: int = 10,
    seed: int = 42,
    api_key: str = "",
    model: str = "meta-llama/llama-3.3-70b-instruct",
    dry_run: bool = False,
    base_output_dir: str = "outputs/causal_discovery/multi_agent",
    verbose: bool = True,
    domains: list[str] | None = None,
    communications: list[str] | None = None,
) -> dict:
    """Run all conditions and produce comparison.json.

    Parameters
    ----------
    domains : list[str] | None
        If provided, only run these domains.
    communications : list[str] | None
        If provided, only run these communication structures.
    """
    if domains is None:
        domains = DOMAINS
    if communications is None:
        communications = [c for c, _ in CONDITIONS]

    conditions_to_run = [
        (comm, kwargs) for comm, kwargs in CONDITIONS
        if comm in communications
    ]

    base_path = Path(base_output_dir)
    comparison = {}
    total_start = time.time()

    for domain in domains:
        comparison[domain] = {}

        for communication, extra_kwargs in conditions_to_run:
            key = f"{domain}_{communication}"
            output_dir = str(base_path / key)

            if verbose:
                print(f"\n{'#' * 60}")
                print(f"# Running: {key}")
                print(f"{'#' * 60}")

            start = time.time()
            try:
                result = run_condition(
                    domain=domain,
                    communication=communication,
                    budget=budget,
                    n_warmup=n_warmup,
                    seed=seed,
                    api_key=api_key,
                    model=model,
                    dry_run=dry_run,
                    output_dir=output_dir,
                    verbose=verbose,
                    **extra_kwargs,
                )
                elapsed = time.time() - start

                # Extract comparable scores
                if communication == "single":
                    # run_pilot returns scores dict directly
                    entry = {
                        "communication": communication,
                        "f1": result.get("f1", 0),
                        "precision": result.get("precision", 0),
                        "recall": result.get("recall", 0),
                        "hamming_distance": result.get("hamming_distance", 0),
                        "elapsed_seconds": round(elapsed, 1),
                    }
                else:
                    # Multi-agent returns nested dict
                    scores = result.get("scores", {})
                    # Pick the primary aggregation method
                    if communication == "independent":
                        primary_key = "majority_vote"
                    elif communication == "debate":
                        primary_key = "union"
                    elif communication == "specialization":
                        primary_key = "llm_aggregator"
                    else:
                        primary_key = list(scores.keys())[0] if scores else "unknown"

                    primary = scores.get(primary_key, {})
                    entry = {
                        "communication": communication,
                        "primary_method": primary_key,
                        "f1": primary.get("f1", 0),
                        "precision": primary.get("precision", 0),
                        "recall": primary.get("recall", 0),
                        "hamming_distance": primary.get("hamming_distance", 0),
                        "all_methods": {
                            k: {
                                "f1": v.get("f1", 0),
                                "precision": v.get("precision", 0),
                                "recall": v.get("recall", 0),
                            }
                            for k, v in scores.items()
                        },
                        "elapsed_seconds": round(elapsed, 1),
                    }

                comparison[domain][communication] = entry

            except Exception as e:
                elapsed = time.time() - start
                if verbose:
                    print(f"  [ERROR] {e}")
                comparison[domain][communication] = {
                    "communication": communication,
                    "error": str(e),
                    "elapsed_seconds": round(elapsed, 1),
                }

    total_elapsed = time.time() - total_start

    # Save comparison
    comparison["_meta"] = {
        "budget": budget,
        "seed": seed,
        "model": model if not dry_run else "dry_run",
        "total_elapsed_seconds": round(total_elapsed, 1),
    }

    base_path.mkdir(parents=True, exist_ok=True)
    comparison_path = base_path / "comparison.json"
    with open(comparison_path, "w") as f:
        json.dump(comparison, f, indent=2, default=str)

    if verbose:
        print(f"\n{'=' * 60}")
        print("COMPARISON SUMMARY")
        print(f"{'=' * 60}")
        for domain in domains:
            print(f"\n{domain.upper()}:")
            for comm in communications:
                entry = comparison.get(domain, {}).get(comm, {})
                if "error" in entry:
                    print(f"  {comm:20s}: ERROR — {entry['error'][:50]}")
                else:
                    print(f"  {comm:20s}: F1={entry.get('f1', 0):.3f} "
                          f"P={entry.get('precision', 0):.3f} "
                          f"R={entry.get('recall', 0):.3f}")
        print(f"\nComparison saved to: {comparison_path}")
        print(f"Total time: {total_elapsed:.0f}s")

    return comparison


def main():
    parser = argparse.ArgumentParser(
        description="Multi-Agent Causal Discovery — Sweep All Conditions"
    )
    parser.add_argument("--budget", type=int, default=30)
    parser.add_argument("--warmup", type=int, default=10)
    parser.add_argument("--model", type=str,
                        default="meta-llama/llama-3.3-70b-instruct")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output-dir", type=str,
                        default="outputs/causal_discovery/multi_agent")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--domain", type=str, choices=["market", "conflict"],
                        default=None, help="Run only this domain")
    parser.add_argument("--communication", type=str,
                        choices=["single", "independent", "debate", "specialization"],
                        default=None, help="Run only this communication structure")
    args = parser.parse_args()

    api_key = ""
    if not args.dry_run:
        api_key = _load_api_key()
        if not api_key:
            print("[ERROR] OPENROUTER_API_KEY not set. Use --dry-run for testing.")
            sys.exit(1)

    domains = [args.domain] if args.domain else None
    communications = [args.communication] if args.communication else None

    run_all(
        budget=args.budget,
        n_warmup=args.warmup,
        seed=args.seed,
        api_key=api_key,
        model=args.model,
        dry_run=args.dry_run,
        base_output_dir=args.output_dir,
        verbose=not args.quiet,
        domains=domains,
        communications=communications,
    )


if __name__ == "__main__":
    main()
