"""
CLI runner for a single multi-agent causal discovery condition.

Usage:
    python -m causal_discovery.multi_agent.runner \
        --domain market --communication independent --budget 30 --dry-run

    python -m causal_discovery.multi_agent.runner \
        --domain conflict --communication debate --budget 30 --dry-run

    python -m causal_discovery.multi_agent.runner \
        --domain market --communication specialization --budget 30 --dry-run

    python -m causal_discovery.multi_agent.runner \
        --domain market --communication single --budget 30 --dry-run
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def _load_api_key() -> str:
    """Load API key from env, .Renviron, or config module."""
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        renviron = Path(__file__).parent.parent.parent / ".Renviron"
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


def run_condition(
    domain: str,
    communication: str,
    budget: int = 30,
    n_warmup: int = 10,
    seed: int = 42,
    api_key: str = "",
    model: str = "meta-llama/llama-3.3-70b-instruct",
    dry_run: bool = False,
    output_dir: str = "",
    verbose: bool = True,
    persona_set: str = "reasoning",
    sequential: bool = False,
) -> dict:
    """Run a single condition and return results."""
    if not output_dir:
        if communication == "single":
            output_dir = f"outputs/causal_discovery/single_agent/{domain}_{communication}"
        else:
            output_dir = f"outputs/causal_discovery/multi_agent/{domain}_{communication}"

    if communication == "single":
        from causal_discovery.run_pilot import run_pilot, run_conflict_pilot
        pilot_fn = run_conflict_pilot if domain == "conflict" else run_pilot
        return pilot_fn(
            budget=budget,
            n_warmup=n_warmup,
            api_key=api_key,
            model=model,
            dry_run=dry_run,
            output_dir=output_dir,
            seed=seed,
            verbose=verbose,
        )

    elif communication == "independent":
        from causal_discovery.multi_agent.independent import run_independent
        return run_independent(
            domain=domain,
            budget=budget,
            n_warmup=n_warmup,
            seed=seed,
            api_key=api_key,
            model=model,
            dry_run=dry_run,
            output_dir=output_dir,
            verbose=verbose,
            persona_set=persona_set,
            sequential=sequential,
        )

    elif communication == "debate":
        from causal_discovery.multi_agent.debate import run_debate
        return run_debate(
            domain=domain,
            budget=budget,
            n_warmup=n_warmup,
            seed=seed,
            api_key=api_key,
            model=model,
            dry_run=dry_run,
            output_dir=output_dir,
            verbose=verbose,
        )

    elif communication == "specialization":
        from causal_discovery.multi_agent.specialization import run_specialization
        return run_specialization(
            domain=domain,
            budget=budget,
            n_warmup=n_warmup,
            seed=seed,
            api_key=api_key,
            model=model,
            dry_run=dry_run,
            output_dir=output_dir,
            verbose=verbose,
        )

    else:
        raise ValueError(f"Unknown communication structure: {communication}")


def main():
    parser = argparse.ArgumentParser(
        description="Multi-Agent Causal Discovery — Single Condition Runner"
    )
    parser.add_argument("--domain", type=str, choices=["market", "conflict"],
                        default="market", help="Simulation domain")
    parser.add_argument("--communication", type=str,
                        choices=["single", "independent", "debate", "specialization"],
                        default="independent",
                        help="Communication structure")
    parser.add_argument("--budget", type=int, default=30,
                        help="Total intervention budget")
    parser.add_argument("--warmup", type=int, default=10,
                        help="Warm-up periods")
    parser.add_argument("--model", type=str,
                        default="meta-llama/llama-3.3-70b-instruct",
                        help="LLM model")
    parser.add_argument("--dry-run", action="store_true",
                        help="Use mock LLM responses")
    parser.add_argument("--output-dir", type=str, default="",
                        help="Output directory")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--persona-set", type=str, default="reasoning",
                        choices=["reasoning", "expertise"],
                        help="Persona set: 'reasoning' (5 causal) or 'expertise' (3 soft)")
    parser.add_argument("--sequential", action="store_true",
                        help="Sequential mode: each agent sees prior agents' results")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    api_key = ""
    if not args.dry_run:
        api_key = _load_api_key()
        if not api_key:
            print("[ERROR] OPENROUTER_API_KEY not set. Use --dry-run for testing.")
            sys.exit(1)

    run_condition(
        domain=args.domain,
        communication=args.communication,
        budget=args.budget,
        n_warmup=args.warmup,
        seed=args.seed,
        api_key=api_key,
        model=args.model,
        dry_run=args.dry_run,
        output_dir=args.output_dir,
        verbose=not args.quiet,
        persona_set=args.persona_set,
        sequential=args.sequential,
    )


if __name__ == "__main__":
    main()
