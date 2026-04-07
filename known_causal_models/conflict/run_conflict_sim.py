"""
Conflict Simulation Runner -- Runs LLM agents in the conflict engine.

Usage:
    # Quick test (1 scenario, 10 periods)
    python conflict/run_conflict_sim.py --n_scenarios 1 --n_periods 10

    # Full run (10 scenarios, 30 periods each)
    python conflict/run_conflict_sim.py --n_scenarios 10 --n_periods 30 --model llama
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from conflict.engine import (
    ConflictState, Action, ACTION_SPACE, initialize_state,
    aggregate_faction_action, run_period,
)
from conflict.agents_config import create_agents, compute_state_modifier
from conflict.shocks import (
    generate_shock_sequence, apply_shocks, get_active_shocks,
    generate_scenario_configs, describe_shocks,
)


def run_llm_simulation(
    scenario_config: dict,
    llm_config: dict,
    verbose: bool = True,
) -> dict:
    """Run a single conflict simulation with LLM agents.

    Parameters
    ----------
    scenario_config : dict
        From generate_scenario_configs().
    llm_config : dict
        Keys: api_key, model, temperature, etc.
    verbose : bool
        Print period-by-period output.

    Returns
    -------
    dict with summary statistics and full state history.
    """
    from conflict.llm_agent import LLMAgentConfig, LLMAgentPool

    agents, faction_agents = create_agents(scenario_config)
    shocks = scenario_config["shocks"]
    n_periods = scenario_config["n_periods"]

    state = initialize_state(scenario_config)

    # Set up LLM agent pool
    config = LLMAgentConfig(
        api_key=llm_config["api_key"],
        model=llm_config.get("model", "meta-llama/llama-3.1-8b-instruct"),
        temperature=llm_config.get("temperature", 0.7),
        max_tokens=llm_config.get("max_tokens", 300),
        rate_limit_delay=llm_config.get("rate_limit_delay", 0.5),
        use_persona=llm_config.get("use_persona", True),
    )
    pool = LLMAgentPool(config)
    pool.register_all(agents)

    if verbose:
        print(f"\n{'='*70}")
        print(f"Scenario: {scenario_config['scenario_id']} | LLM: {config.model}")
        print(f"Starting EI: {scenario_config['starting_escalation']:.2f} | Periods: {n_periods}")
        print(f"Agents: {[a['agent_id'] for a in agents]}")
        print(f"{'='*70}")

    # Track actions log
    all_actions_log = []

    for t in range(n_periods):
        # Apply shocks
        apply_shocks(state, shocks, t)

        # Describe active shocks
        active = get_active_shocks(shocks, t)
        shock_desc = describe_shocks(shocks, t) if active else ""

        if verbose:
            shock_str = f" [SHOCK: {', '.join(s.shock_type for s in active)}]" if active else ""
            print(f"\n  --- Period {t+1}/{n_periods}{shock_str} ---")

        # Collect LLM recommendations
        recommendations = pool.collect_recommendations(
            state=state,
            shock_description=shock_desc,
            verbose=verbose,
        )

        # Separate by faction
        novaris_recs = [r for r in recommendations if r["faction"] == "novaris"]
        tethys_recs = [r for r in recommendations if r["faction"] == "tethys"]

        # Aggregate within each faction
        novaris_action = aggregate_faction_action(novaris_recs, "novaris")
        tethys_action = aggregate_faction_action(tethys_recs, "tethys")

        # Log actions
        period_log = {
            "period": t,
            "recommendations": [
                {
                    "agent_id": r["agent_id"],
                    "faction": r["faction"],
                    "action": r["action"],
                    "reasoning": r["reasoning"],
                }
                for r in recommendations
            ],
            "novaris_action": novaris_action.action_name,
            "tethys_action": tethys_action.action_name,
        }

        # Run period
        result = run_period(state, novaris_action, tethys_action)

        period_log["escalation_index"] = result["escalation_index"]
        period_log["military_balance"] = result["military_balance"]
        period_log["territory_controlled"] = result["territory_controlled"]
        period_log["sanctions_level"] = result["sanctions_level"]
        all_actions_log.append(period_log)

        if verbose:
            print(f"  >> EI: {result['escalation_index']:.2f} | "
                  f"Nov: {novaris_action.action_name} | "
                  f"Teth: {tethys_action.action_name} | "
                  f"Mil: {result['military_balance']:+.2f}")

    # Summary
    ei_history = np.array(state.escalation_history)
    ei_changes = np.diff(ei_history) if len(ei_history) > 1 else np.array([0.0])

    summary = {
        "scenario_id": scenario_config["scenario_id"],
        "model": config.model,
        "n_periods": n_periods,
        "mean_ei": round(float(np.mean(ei_history)), 4),
        "std_ei": round(float(np.std(ei_history)), 4),
        "min_ei": round(float(np.min(ei_history)), 4),
        "max_ei": round(float(np.max(ei_history)), 4),
        "final_ei": round(float(ei_history[-1]), 4),
        "mean_change": round(float(np.mean(ei_changes)), 4),
        "std_change": round(float(np.std(ei_changes)), 4),
        "ei_range": round(float(np.max(ei_history) - np.min(ei_history)), 4),
        "llm_stats": pool.get_aggregate_stats(),
    }

    # Faction final states
    faction_finals = {}
    for fid, faction in state.factions.items():
        faction_finals[fid] = {
            "gdp": round(faction.gdp, 4),
            "military_strength": round(faction.military_strength, 4),
            "political_stability": round(faction.political_stability, 4),
            "resources": round(faction.resources, 2),
        }

    if verbose:
        print(f"\n  {'='*50}")
        print(f"  Summary: EI={summary['mean_ei']:.2f} +/- {summary['std_ei']:.2f} "
              f"(range {summary['ei_range']:.2f})")
        print(f"  Final EI: {summary['final_ei']:.2f} | "
              f"Change std: {summary['std_change']:.4f}")
        print(f"  LLM: {summary['llm_stats']}")
        print(f"\n  Faction Finals:")
        for fid, ff in faction_finals.items():
            print(f"    {fid:8s} | GDP={ff['gdp']:.2f} | "
                  f"Mil={ff['military_strength']:.2f} | "
                  f"Stab={ff['political_stability']:.2f} | "
                  f"Res={ff['resources']:.1f}")

    # Validation
    errors = []
    if summary["std_ei"] < 0.01:
        errors.append("Escalation index is stuck (no variation)")
    if summary["ei_range"] < 0.1:
        errors.append(f"Very low EI range: {summary['ei_range']:.4f}")

    if errors:
        print(f"\n  [WARN] Validation warnings:")
        for e in errors:
            print(f"    - {e}")
    elif verbose:
        print(f"\n  [OK] All validations passed")

    return {
        "summary": summary,
        "faction_finals": faction_finals,
        "escalation_history": [round(float(e), 4) for e in state.escalation_history],
        "military_balance_final": round(state.military_balance, 4),
        "territory_final": round(state.territory_controlled, 4),
        "sanctions_final": round(state.sanctions_level, 4),
        "actions_log": all_actions_log,
        "errors": errors,
    }


def run_baseline_simulation(scenario_config: dict, verbose: bool = True) -> dict:
    """Run a scenario with rule-based agents (no LLM calls).

    Uses hawk/dove scores to deterministically select actions.
    """
    agents, faction_agents = create_agents(scenario_config)
    shocks = scenario_config["shocks"]
    n_periods = scenario_config["n_periods"]

    state = initialize_state(scenario_config)

    all_actions_log = []

    for t in range(n_periods):
        apply_shocks(state, shocks, t)

        # Rule-based recommendations
        recommendations = []
        for agent in agents:
            rec = _rule_based_recommendation(agent, state)
            recommendations.append(rec)

        novaris_recs = [r for r in recommendations if r["faction"] == "novaris"]
        tethys_recs = [r for r in recommendations if r["faction"] == "tethys"]

        novaris_action = aggregate_faction_action(novaris_recs, "novaris")
        tethys_action = aggregate_faction_action(tethys_recs, "tethys")

        period_log = {
            "period": t,
            "recommendations": recommendations,
            "novaris_action": novaris_action.action_name,
            "tethys_action": tethys_action.action_name,
        }

        result = run_period(state, novaris_action, tethys_action)
        period_log["escalation_index"] = result["escalation_index"]

        # Per-period state for forecasting framework
        period_log["military_balance"] = round(state.military_balance, 4)
        period_log["territory_controlled"] = round(state.territory_controlled, 4)
        period_log["sanctions_level"] = round(state.sanctions_level, 4)
        period_log["international_support"] = round(state.international_support, 4)
        period_log["novaris_resources"] = round(state.factions["novaris"].resources, 2)
        period_log["tethys_resources"] = round(state.factions["tethys"].resources, 2)
        period_log["novaris_gdp"] = round(state.factions["novaris"].gdp, 4)
        period_log["tethys_gdp"] = round(state.factions["tethys"].gdp, 4)
        period_log["novaris_military_strength"] = round(state.factions["novaris"].military_strength, 4)
        period_log["tethys_military_strength"] = round(state.factions["tethys"].military_strength, 4)
        period_log["novaris_political_stability"] = round(state.factions["novaris"].political_stability, 4)
        period_log["tethys_political_stability"] = round(state.factions["tethys"].political_stability, 4)

        all_actions_log.append(period_log)

        if verbose and (t < 3 or t >= n_periods - 2 or t % 10 == 0):
            active = get_active_shocks(shocks, t)
            shock_str = f" [SHOCK]" if active else ""
            print(f"  t={t:3d} | EI={result['escalation_index']:5.2f} | "
                  f"Nov={novaris_action.action_name:20s} | "
                  f"Teth={tethys_action.action_name:20s}{shock_str}")

    ei_history = np.array(state.escalation_history)
    ei_changes = np.diff(ei_history) if len(ei_history) > 1 else np.array([0.0])

    summary = {
        "scenario_id": scenario_config["scenario_id"],
        "model": "rule_based",
        "n_periods": n_periods,
        "mean_ei": round(float(np.mean(ei_history)), 4),
        "std_ei": round(float(np.std(ei_history)), 4),
        "min_ei": round(float(np.min(ei_history)), 4),
        "max_ei": round(float(np.max(ei_history)), 4),
        "final_ei": round(float(ei_history[-1]), 4),
        "mean_change": round(float(np.mean(ei_changes)), 4),
        "std_change": round(float(np.std(ei_changes)), 4),
        "ei_range": round(float(np.max(ei_history) - np.min(ei_history)), 4),
    }

    faction_finals = {}
    for fid, faction in state.factions.items():
        faction_finals[fid] = {
            "gdp": round(faction.gdp, 4),
            "military_strength": round(faction.military_strength, 4),
            "political_stability": round(faction.political_stability, 4),
            "resources": round(faction.resources, 2),
        }

    return {
        "summary": summary,
        "faction_finals": faction_finals,
        "escalation_history": [round(float(e), 4) for e in state.escalation_history],
        "actions_log": all_actions_log,
        "errors": [],
    }


def _rule_based_recommendation(agent: dict, state: ConflictState) -> dict:
    """Generate a rule-based action recommendation from hawk/dove score.

    Hawks prefer escalatory actions, doves prefer de-escalatory.
    Current escalation level also influences the choice.
    """
    hawk_score = agent["hawk_dove"]
    state_mod = compute_state_modifier(agent, state)
    effective_hawk = max(0.05, min(0.95, hawk_score + state_mod))
    ei = state.escalation_index

    # Target escalation delta based on effective hawk/dove score
    # Hawks want positive delta, doves want negative
    # But at extremes, even hawks/doves moderate
    if ei > 8.0:
        target_delta = (effective_hawk - 0.5) * 1.0  # even hawks pull back slightly
    elif ei < 2.0:
        target_delta = (effective_hawk - 0.5) * 1.0  # even doves don't over-de-escalate
    else:
        target_delta = (effective_hawk - 0.5) * 3.0  # full range in middle

    # Find affordable action closest to target delta
    own_faction = state.factions[agent["faction"]]
    affordable = [
        (n, s) for n, s in ACTION_SPACE.items()
        if s["cost"] <= own_faction.resources
    ]

    if not affordable:
        action_name = "intelligence_gathering"
    else:
        action_name = min(affordable,
            key=lambda ns: abs(ns[1]["escalation_delta"] - target_delta)
        )[0]

    return {
        "agent_id": agent["agent_id"],
        "agent_role": agent["role"],
        "faction": agent["faction"],
        "action": action_name,
        "reasoning": f"Rule-based (hawk={hawk_score:.2f}, state_mod={state_mod:+.3f}, eff={effective_hawk:.2f}, target_delta={target_delta:.2f})",
    }


def main():
    parser = argparse.ArgumentParser(description="Run conflict simulation with LLM agents")
    parser.add_argument("--n_scenarios", type=int, default=3,
                        help="Number of scenarios to run")
    parser.add_argument("--n_periods", type=int, default=30,
                        help="Periods per scenario")
    parser.add_argument("--model", type=str, default="llama",
                        choices=["llama", "deepseek", "claude", "qwen"],
                        help="LLM model alias")
    parser.add_argument("--baseline", action="store_true",
                        help="Run rule-based baseline (no LLM calls)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for scenario generation")
    parser.add_argument("--output_dir", type=str, default=None,
                        help="Output directory")
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--no-persona", action="store_true",
                        help="Strip agent personas (role + faction only, no backstory)")
    parser.add_argument("--quiet", action="store_true",
                        help="Minimal output")
    args = parser.parse_args()

    model_map = {
        "llama": "meta-llama/llama-3.1-8b-instruct",
        "deepseek": "deepseek/deepseek-v3.2",
        "claude": "anthropic/claude-sonnet-4",
        "qwen": "qwen/qwen3-235b-a22b-2507",
    }

    project_root = Path(__file__).parent.parent
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        if args.baseline:
            mode = "baseline"
        elif args.no_persona:
            mode = f"{args.model}_no_persona"
        else:
            mode = f"{args.model}_persona"
        output_dir = project_root / "outputs" / f"conflict_{mode}"
    output_dir.mkdir(parents=True, exist_ok=True)

    configs = generate_scenario_configs(
        n_scenarios=args.n_scenarios,
        n_periods=args.n_periods,
        seed=args.seed,
    )

    verbose = not args.quiet

    persona_str = " (NO PERSONA)" if args.no_persona else " (with personas)"
    print("=" * 70)
    print(f"CONFLICT SIMULATION -- {'Rule-Based Baseline' if args.baseline else model_map[args.model]}{'' if args.baseline else persona_str}")
    print(f"Scenarios: {args.n_scenarios} | Periods: {args.n_periods} | Seed: {args.seed}")
    print(f"Output: {output_dir}")
    print("=" * 70)

    all_results = []
    t0 = time.time()

    for i, config in enumerate(configs):
        print(f"\n[{i+1}/{args.n_scenarios}] Running {config['scenario_id']}...")

        if args.baseline:
            result = run_baseline_simulation(config, verbose=verbose)
        else:
            api_key = os.getenv("OPENROUTER_API_KEY", "")
            if not api_key:
                try:
                    from archive.wargame_forecasting.config import OPENROUTER_API_KEY
                    api_key = OPENROUTER_API_KEY
                except ImportError:
                    pass
            if not api_key:
                print("[ERROR] OPENROUTER_API_KEY not set")
                sys.exit(1)

            llm_config = {
                "api_key": api_key,
                "model": model_map[args.model],
                "temperature": args.temperature,
                "rate_limit_delay": 0.5,
                "use_persona": not args.no_persona,
            }
            result = run_llm_simulation(config, llm_config, verbose=verbose)

        all_results.append(result)

        scenario_file = output_dir / f"{config['scenario_id']}.json"
        with open(scenario_file, "w") as f:
            json.dump(result, f, indent=2, default=str)

    elapsed = time.time() - t0

    # Cross-scenario summary
    print(f"\n{'='*70}")
    print("CROSS-SCENARIO SUMMARY")
    print(f"{'='*70}")

    summaries = [r["summary"] for r in all_results]
    ei_stds = [s["std_ei"] for s in summaries]
    ei_ranges = [s["ei_range"] for s in summaries]
    change_stds = [s["std_change"] for s in summaries]

    print(f"  Mean EI std:        {np.mean(ei_stds):.4f}")
    print(f"  Mean EI range:      {np.mean(ei_ranges):.4f}")
    print(f"  Mean change std:    {np.mean(change_stds):.4f}")
    print(f"  Elapsed time:       {elapsed:.1f}s")

    if not args.baseline:
        llm_stats = [s.get("llm_stats", {}) for s in summaries]
        total_calls = sum(s.get("total_calls", 0) for s in llm_stats)
        total_tokens = sum(s.get("total_tokens", 0) for s in llm_stats)
        print(f"  Total LLM calls:    {total_calls}")
        print(f"  Total tokens:       {total_tokens}")

    # Variation check
    if np.mean(change_stds) > 0.05:
        print(f"\n  [OK] Sufficient escalation variation for forecasting")
    else:
        print(f"\n  [WARN] Low escalation variation -- forecasting target entropy may be low")

    # Save aggregate summary
    agg = {
        "mode": "baseline" if args.baseline else args.model,
        "n_scenarios": args.n_scenarios,
        "n_periods": args.n_periods,
        "elapsed_seconds": round(elapsed, 1),
        "summaries": summaries,
        "mean_ei_std": round(float(np.mean(ei_stds)), 4),
        "mean_ei_range": round(float(np.mean(ei_ranges)), 4),
        "mean_change_std": round(float(np.mean(change_stds)), 4),
    }
    with open(output_dir / "aggregate_summary.json", "w") as f:
        json.dump(agg, f, indent=2)

    print(f"\n  Results saved to: {output_dir}")


if __name__ == "__main__":
    main()
