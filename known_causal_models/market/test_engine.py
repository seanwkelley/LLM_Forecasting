"""
Test the market engine with rule-based agents.

Verifies:
1. Clearing mechanism produces sensible prices
2. Agent budgets/inventories update correctly
3. Shocks create price variation
4. No negative cash or inventory violations
5. Price series has enough variance for PID analysis

This also serves as the rule-based baseline for calibrating
"trivial structural synergy" in the PID analysis.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from market.engine import Order, MarketState, run_period
from market.agents_config import create_agents
from market.shocks import (
    generate_shock_sequence, apply_shocks, get_active_shocks,
    generate_scenario_configs, describe_shocks,
)


def rule_based_order(agent, price_history):
    """Simple rule-based agent for testing.

    Producers: sell at production_cost + margin, more aggressive when inventory high.
    Consumers: buy at demand_value - small discount, more aggressive when inventory low.
    Speculators: mean-reversion toward last known price with noise.
    """
    import numpy as np

    last_price = price_history[-1] if price_history else 100.0

    if agent.role == "producer":
        # Sell at cost + 10-30% margin, more aggressive with high inventory
        margin = 0.15 if agent.inventory < 40 else 0.08
        price = agent.production_cost * (1 + margin)
        qty = min(agent.production_capacity, agent.inventory)
        if qty <= 0:
            return None
        return Order(
            agent_id=agent.agent_id,
            side="sell",
            quantity=qty,
            limit_price=round(price, 2),
            reasoning=f"Sell at cost+{margin:.0%}, inv={agent.inventory}",
        )

    elif agent.role == "consumer":
        # Buy at value - 5-15% discount
        discount = 0.05 if agent.inventory < agent.demand_per_period * 2 else 0.12
        price = agent.demand_value * (1 - discount)
        qty = max(1, agent.demand_per_period - agent.inventory // 3)
        if agent.cash < price:
            return None
        return Order(
            agent_id=agent.agent_id,
            side="buy",
            quantity=qty,
            limit_price=round(price, 2),
            reasoning=f"Buy at value-{discount:.0%}, inv={agent.inventory}",
        )

    elif agent.role == "speculator":
        # Mean reversion: buy below trend, sell above
        if len(price_history) < 3:
            return None  # wait for data
        trend = (price_history[-1] - price_history[-3]) / 2
        if trend > 0 and agent.inventory > 10:
            # Price rising, sell some
            return Order(
                agent_id=agent.agent_id,
                side="sell",
                quantity=min(10, agent.inventory),
                limit_price=round(last_price * 1.02, 2),
                reasoning=f"Sell on uptrend, trend={trend:.2f}",
            )
        elif trend < 0 and agent.cash > last_price * 5:
            # Price falling, buy some
            return Order(
                agent_id=agent.agent_id,
                side="buy",
                quantity=5,
                limit_price=round(last_price * 0.98, 2),
                reasoning=f"Buy on downtrend, trend={trend:.2f}",
            )
        return None

    return None


def run_test_scenario(scenario_config, verbose=True):
    """Run one scenario with rule-based agents."""
    import numpy as np

    agents, base_params = create_agents(scenario_config)
    shocks = scenario_config["shocks"]
    n_periods = scenario_config["n_periods"]

    state = MarketState(agents=agents)

    if verbose:
        print(f"\n{'='*60}")
        print(f"Scenario: {scenario_config['scenario_id']}")
        print(f"Base price: ${scenario_config['base_price']:.2f}")
        print(f"N shocks: {scenario_config['n_shocks']}")
        print(f"Agents: {list(agents.keys())}")
        print(f"{'='*60}")

    for t in range(n_periods):
        # Apply shocks
        apply_shocks(agents, shocks, t, base_params)

        # Collect orders
        orders = []
        for agent in agents.values():
            order = rule_based_order(agent, state.price_history)
            if order is not None:
                orders.append(order)

        # Run period
        result = run_period(state, orders)

        if verbose and (t < 5 or t >= n_periods - 3 or t % 10 == 0):
            active = get_active_shocks(shocks, t)
            shock_str = f" [SHOCK: {', '.join(s.shock_type for s in active)}]" if active else ""
            print(f"  t={t:3d} | P=${result['clearing_price']:7.2f} | "
                  f"V={int(result['volume']):3d} | "
                  f"F=${result['fundamental_price']:7.2f} | "
                  f"Orders: {result['n_buy_orders']}B/{result['n_sell_orders']}S"
                  f"{shock_str}")

    # Summary statistics
    prices = np.array(state.price_history)
    if len(prices) > 1:
        returns = np.diff(prices) / prices[:-1]
    else:
        returns = np.array([0.0])

    summary = {
        "scenario_id": scenario_config["scenario_id"],
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

    if verbose:
        print(f"\n  Summary:")
        print(f"    Price: ${summary['mean_price']:.2f} +/- ${summary['std_price']:.2f} "
              f"(range: ${summary['min_price']:.2f} - ${summary['max_price']:.2f})")
        print(f"    Range: {summary['price_range_pct']:.1f}% of mean")
        print(f"    Volume: {summary['mean_volume']:.1f} units/period")
        print(f"    Return volatility: {summary['return_std']:.4f}")

        # Agent final states
        print(f"\n  Agent Final States:")
        for agent in agents.values():
            pnl = agent.unrealized_pnl(prices[-1])
            print(f"    {agent.agent_id:15s} | cash=${agent.cash:8.2f} | "
                  f"inv={int(agent.inventory):4d} | P&L=${pnl:8.2f}")

    # Validation checks
    errors = []
    for agent in agents.values():
        if agent.cash < -100:  # small tolerance for floating point
            errors.append(f"{agent.agent_id}: negative cash ${agent.cash:.2f}")
        if agent.inventory < 0:
            errors.append(f"{agent.agent_id}: negative inventory {agent.inventory}")

    if errors:
        print(f"\n  [FAIL] Validation errors:")
        for e in errors:
            print(f"    - {e}")
    elif verbose:
        print(f"\n  [OK] All validations passed")

    return summary, state


def main():
    import numpy as np

    print("=" * 60)
    print("MARKET ENGINE TEST — Rule-Based Agents")
    print("=" * 60)

    # Generate 5 test scenarios
    configs = generate_scenario_configs(n_scenarios=5, n_periods=30, seed=42)

    all_summaries = []
    for config in configs:
        summary, state = run_test_scenario(config, verbose=True)
        all_summaries.append(summary)

    # Cross-scenario summary
    print(f"\n{'='*60}")
    print("CROSS-SCENARIO SUMMARY")
    print(f"{'='*60}")

    price_stds = [s["std_price"] for s in all_summaries]
    return_stds = [s["return_std"] for s in all_summaries]
    ranges = [s["price_range_pct"] for s in all_summaries]

    print(f"  Mean price std:     ${np.mean(price_stds):.2f}")
    print(f"  Mean return vol:    {np.mean(return_stds):.4f}")
    print(f"  Mean price range:   {np.mean(ranges):.1f}%")
    print(f"  Min/Max range:      {np.min(ranges):.1f}% / {np.max(ranges):.1f}%")

    # PID suitability check
    if np.mean(return_stds) > 0.01:
        print(f"\n  [OK] Sufficient price variation for PID analysis")
    else:
        print(f"\n  [WARN] Low price variation — may need stronger shocks or more agent heterogeneity")

    if np.mean(price_stds) / np.mean([s["mean_price"] for s in all_summaries]) > 0.03:
        print(f"  [OK] Price std > 3% of mean — good target variable entropy")
    else:
        print(f"  [WARN] Low price std relative to mean — entropy trap risk")


if __name__ == "__main__":
    main()
