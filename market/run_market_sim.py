"""
Market Simulation Runner — Runs LLM agents in the market engine.

Usage:
    # Quick test (1 scenario, 10 periods)
    python market/run_market_sim.py --n_scenarios 1 --n_periods 10

    # Full run (5 scenarios, 30 periods each)
    python market/run_market_sim.py --n_scenarios 5 --n_periods 30 --model llama

    # Rule-based baseline (no LLM calls)
    python market/run_market_sim.py --baseline --n_scenarios 5 --n_periods 30
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

from market.engine import MarketState, Order, run_period
from market.agents_config import create_agents
from market.shocks import (
    generate_shock_sequence, apply_shocks, get_active_shocks,
    generate_scenario_configs, describe_shocks,
)
from market.prompts import generate_price_ticks


def run_llm_simulation(
    scenario_config: dict,
    llm_config: dict,
    verbose: bool = True,
) -> dict:
    """Run a single market simulation with LLM agents.

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
    dict with summary statistics and full state.
    """
    from market.llm_agent import LLMAgentConfig, LLMAgentPool

    agents, base_params = create_agents(scenario_config)
    shocks = scenario_config["shocks"]
    n_periods = scenario_config["n_periods"]
    base_price = scenario_config["base_price"]

    state = MarketState(agents=agents)

    # Set up LLM agent pool
    config = LLMAgentConfig(
        api_key=llm_config["api_key"],
        model=llm_config.get("model", "meta-llama/llama-3.1-8b-instruct"),
        temperature=llm_config.get("temperature", 0.7),
        max_tokens=llm_config.get("max_tokens", 300),
        rate_limit_delay=llm_config.get("rate_limit_delay", 0.5),
    )
    pool = LLMAgentPool(config)
    pool.register_all(agents)

    if verbose:
        print(f"\n{'='*70}")
        print(f"Scenario: {scenario_config['scenario_id']} | LLM: {config.model}")
        print(f"Base price: ${base_price:.2f} | Periods: {n_periods}")
        print(f"Agents: {list(agents.keys())}")
        print(f"{'='*70}")

    # Track orders for PID analysis
    all_orders_log = []

    for t in range(n_periods):
        # Apply shocks
        apply_shocks(agents, shocks, t, base_params)

        # Generate price ticks centered on last price
        ref_price = state.price_history[-1] if state.price_history else base_price
        price_ticks = generate_price_ticks(ref_price, n_ticks=15, spread_pct=0.30)

        # Describe active shocks (public information)
        active = get_active_shocks(shocks, t)
        shock_desc = describe_shocks(shocks, t) if active else ""

        if verbose:
            shock_str = f" [SHOCK: {', '.join(s.shock_type for s in active)}]" if active else ""
            print(f"\n  --- Period {t+1}/{n_periods}{shock_str} ---")

        # Collect LLM orders
        orders = pool.collect_orders(
            agent_states=agents,
            market_state=state,
            price_ticks=price_ticks,
            shock_description=shock_desc,
            verbose=verbose,
        )

        # Log orders for PID
        period_log = {
            "period": t,
            "orders": [
                {
                    "agent_id": o.agent_id,
                    "side": o.side,
                    "quantity": o.quantity,
                    "limit_price": o.limit_price,
                    "reasoning": o.reasoning,
                }
                for o in orders
            ],
        }

        # Run period
        result = run_period(state, orders)

        period_log["clearing_price"] = result["clearing_price"]
        period_log["volume"] = result["volume"]
        period_log["fundamental_price"] = result["fundamental_price"]
        all_orders_log.append(period_log)

        if verbose:
            print(f"  >> Price: ${result['clearing_price']:.2f} | "
                  f"Vol: {int(result['volume'])} | "
                  f"Fund: ${result['fundamental_price']:.2f} | "
                  f"Orders: {result['n_buy_orders']}B/{result['n_sell_orders']}S")

    # Summary
    prices = np.array(state.price_history)
    returns = np.diff(prices) / prices[:-1] if len(prices) > 1 else np.array([0.0])

    summary = {
        "scenario_id": scenario_config["scenario_id"],
        "model": config.model,
        "n_periods": n_periods,
        "mean_price": round(float(np.mean(prices)), 2),
        "std_price": round(float(np.std(prices)), 2),
        "min_price": round(float(np.min(prices)), 2),
        "max_price": round(float(np.max(prices)), 2),
        "mean_volume": round(float(np.mean(state.volume_history)), 1),
        "return_std": round(float(np.std(returns)), 4),
        "price_range_pct": round(
            float((np.max(prices) - np.min(prices)) / np.mean(prices) * 100), 1
        ),
        "llm_stats": pool.get_aggregate_stats(),
    }

    # Agent final states
    agent_finals = {}
    for agent in agents.values():
        pnl = agent.unrealized_pnl(prices[-1])
        agent_finals[agent.agent_id] = {
            "role": agent.role,
            "cash": round(agent.cash, 2),
            "inventory": int(agent.inventory),
            "pnl": round(pnl, 2),
        }

    if verbose:
        print(f"\n  {'='*50}")
        print(f"  Summary: P=${summary['mean_price']:.2f} +/- ${summary['std_price']:.2f} "
              f"(range {summary['price_range_pct']:.1f}%)")
        print(f"  Return vol: {summary['return_std']:.4f} | "
              f"Mean vol: {summary['mean_volume']:.1f}")
        print(f"  LLM: {summary['llm_stats']}")
        print(f"\n  Agent Finals:")
        for aid, af in agent_finals.items():
            print(f"    {aid:15s} | cash=${af['cash']:8.2f} | "
                  f"inv={af['inventory']:4d} | P&L=${af['pnl']:8.2f}")

    # Validation
    errors = []
    for agent in agents.values():
        if agent.cash < -100:
            errors.append(f"{agent.agent_id}: negative cash ${agent.cash:.2f}")
        if agent.inventory < 0:
            errors.append(f"{agent.agent_id}: negative inventory {agent.inventory}")

    if errors:
        print(f"\n  [FAIL] Validation errors:")
        for e in errors:
            print(f"    - {e}")
    elif verbose:
        print(f"\n  [OK] All validations passed")

    return {
        "summary": summary,
        "agent_finals": agent_finals,
        "price_history": [round(float(p), 2) for p in state.price_history],
        "volume_history": [int(v) for v in state.volume_history],
        "fundamental_history": [round(float(f), 2) for f in state.fundamental_history],
        "orders_log": all_orders_log,
        "errors": errors,
    }


def run_baseline_simulation(scenario_config: dict, verbose: bool = True) -> dict:
    """Run a scenario with rule-based agents (no LLM calls).

    This is the baseline for calibrating 'trivial structural synergy'.
    """
    from market.test_engine import rule_based_order

    agents, base_params = create_agents(scenario_config)
    shocks = scenario_config["shocks"]
    n_periods = scenario_config["n_periods"]

    state = MarketState(agents=agents)

    all_orders_log = []

    for t in range(n_periods):
        apply_shocks(agents, shocks, t, base_params)

        orders = []
        for agent in agents.values():
            order = rule_based_order(agent, state.price_history)
            if order is not None:
                orders.append(order)

        period_log = {
            "period": t,
            "orders": [
                {
                    "agent_id": o.agent_id,
                    "side": o.side,
                    "quantity": o.quantity,
                    "limit_price": o.limit_price,
                    "reasoning": o.reasoning,
                }
                for o in orders
            ],
        }

        result = run_period(state, orders)
        period_log["clearing_price"] = result["clearing_price"]
        period_log["volume"] = result["volume"]
        period_log["fundamental_price"] = result["fundamental_price"]
        all_orders_log.append(period_log)

        if verbose and (t < 3 or t >= n_periods - 2 or t % 10 == 0):
            active = get_active_shocks(shocks, t)
            shock_str = f" [SHOCK: {', '.join(s.shock_type for s in active)}]" if active else ""
            print(f"  t={t:3d} | P=${result['clearing_price']:7.2f} | "
                  f"V={int(result['volume']):3d} | "
                  f"F=${result['fundamental_price']:7.2f}{shock_str}")

    prices = np.array(state.price_history)
    returns = np.diff(prices) / prices[:-1] if len(prices) > 1 else np.array([0.0])

    summary = {
        "scenario_id": scenario_config["scenario_id"],
        "model": "rule_based",
        "n_periods": n_periods,
        "mean_price": round(float(np.mean(prices)), 2),
        "std_price": round(float(np.std(prices)), 2),
        "min_price": round(float(np.min(prices)), 2),
        "max_price": round(float(np.max(prices)), 2),
        "mean_volume": round(float(np.mean(state.volume_history)), 1),
        "return_std": round(float(np.std(returns)), 4),
        "price_range_pct": round(
            float((np.max(prices) - np.min(prices)) / np.mean(prices) * 100), 1
        ),
    }

    agent_finals = {}
    for agent in agents.values():
        pnl = agent.unrealized_pnl(prices[-1])
        agent_finals[agent.agent_id] = {
            "role": agent.role,
            "cash": round(agent.cash, 2),
            "inventory": int(agent.inventory),
            "pnl": round(pnl, 2),
        }

    return {
        "summary": summary,
        "agent_finals": agent_finals,
        "price_history": [round(float(p), 2) for p in state.price_history],
        "volume_history": [int(v) for v in state.volume_history],
        "fundamental_history": [round(float(f), 2) for f in state.fundamental_history],
        "orders_log": all_orders_log,
        "errors": [],
    }


def main():
    parser = argparse.ArgumentParser(description="Run market simulation with LLM agents")
    parser.add_argument("--n_scenarios", type=int, default=3,
                        help="Number of market scenarios to run")
    parser.add_argument("--n_periods", type=int, default=20,
                        help="Trading periods per scenario")
    parser.add_argument("--model", type=str, default="llama",
                        choices=["llama", "deepseek", "claude", "gpt4"],
                        help="LLM model alias")
    parser.add_argument("--baseline", action="store_true",
                        help="Run rule-based baseline (no LLM calls)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for scenario generation")
    parser.add_argument("--output_dir", type=str, default=None,
                        help="Output directory (default: outputs/market_sim)")
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--quiet", action="store_true",
                        help="Minimal output")
    args = parser.parse_args()

    # Model mapping
    model_map = {
        "llama": "meta-llama/llama-3.1-8b-instruct",
        "deepseek": "deepseek/deepseek-v3.2",
        "claude": "anthropic/claude-sonnet-4",
        "gpt4": "openai/gpt-4-turbo",
    }

    # Output directory
    project_root = Path(__file__).parent.parent
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        mode = "baseline" if args.baseline else f"{args.model}_persona"
        output_dir = project_root / "outputs" / f"market_{mode}"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate scenarios
    configs = generate_scenario_configs(
        n_scenarios=args.n_scenarios,
        n_periods=args.n_periods,
        seed=args.seed,
    )

    verbose = not args.quiet

    print("=" * 70)
    print(f"MARKET SIMULATION — {'Rule-Based Baseline' if args.baseline else model_map[args.model]}")
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
                # Fall back to config file
                try:
                    from forecasting.config import OPENROUTER_API_KEY
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
            }
            result = run_llm_simulation(config, llm_config, verbose=verbose)

        all_results.append(result)

        # Save individual scenario result
        scenario_file = output_dir / f"{config['scenario_id']}.json"
        with open(scenario_file, "w") as f:
            json.dump(result, f, indent=2, default=str)

    elapsed = time.time() - t0

    # Cross-scenario summary
    print(f"\n{'='*70}")
    print("CROSS-SCENARIO SUMMARY")
    print(f"{'='*70}")

    summaries = [r["summary"] for r in all_results]
    price_stds = [s["std_price"] for s in summaries]
    return_stds = [s["return_std"] for s in summaries]
    ranges = [s["price_range_pct"] for s in summaries]

    print(f"  Mean price std:     ${np.mean(price_stds):.2f}")
    print(f"  Mean return vol:    {np.mean(return_stds):.4f}")
    print(f"  Mean price range:   {np.mean(ranges):.1f}%")
    print(f"  Elapsed time:       {elapsed:.1f}s")

    if not args.baseline:
        llm_stats = [s.get("llm_stats", {}) for s in summaries]
        total_calls = sum(s.get("total_calls", 0) for s in llm_stats)
        total_tokens = sum(s.get("total_tokens", 0) for s in llm_stats)
        print(f"  Total LLM calls:    {total_calls}")
        print(f"  Total tokens:       {total_tokens}")

    # PID suitability
    if np.mean(return_stds) > 0.01:
        print(f"\n  [OK] Sufficient price variation for PID analysis")
    else:
        print(f"\n  [WARN] Low price variation — PID target entropy may be low")

    # Save aggregate summary
    agg = {
        "mode": "baseline" if args.baseline else args.model,
        "n_scenarios": args.n_scenarios,
        "n_periods": args.n_periods,
        "elapsed_seconds": round(elapsed, 1),
        "summaries": summaries,
        "mean_price_std": round(float(np.mean(price_stds)), 2),
        "mean_return_vol": round(float(np.mean(return_stds)), 4),
        "mean_price_range_pct": round(float(np.mean(ranges)), 1),
    }
    with open(output_dir / "aggregate_summary.json", "w") as f:
        json.dump(agg, f, indent=2)

    print(f"\n  Results saved to: {output_dir}")


if __name__ == "__main__":
    main()
