"""
Canonical rule-based agents for the market engine.

Single source of truth used by:
- market/test_engine.py (for run_baseline_simulation and standalone tests)
- causal_discovery/intervention.py (for rule_based intervention rollouts)
- causal_discovery/run_pilot*.py and multi_agent/agent.py (via intervention wrapper)

Design notes
------------
- Producer margin is elastic to inventory: scarce stock → higher margin,
  abundant stock → thinner margin. This matches real-world seller behavior
  (scarcity commands a premium) and replaces an anti-elastic rule that
  previously inflated margin when inventory grew.
- Consumer discount is elastic to inventory: low stock → small discount
  (urgent), well-stocked → larger discount (patient).
- Consumers respect cash constraints (won't bid more than they can afford).
- Speculator A: momentum (trend-following).
- Speculator B: contrarian (fades extreme moves).

Ground truth edges that these rules instantiate (see ground_truth.py):
- production_cost → agent_orders (producer ask = cost * margin)
- demand_value    → agent_orders (consumer bid = value * (1 - discount))
- demand_per_period → agent_orders (consumer quantity = min(demand, affordable))
- cash            → agent_orders (consumer affordability + speculator sizing)
- inventory       → agent_orders (producer ask price/quantity, contrarian sells)
- price_history   → agent_orders (speculators read trend)

storage_cost affects orders only indirectly (storage_cost → cash → orders),
so it is not referenced by any rule — consistent with the ground truth
treating that path as indirect-only.
"""

from __future__ import annotations

from market.engine import AgentState, Order


def rule_based_order(agent: AgentState, price_history: list) -> Order | None:
    """Generate a single agent's order for the current period.

    Returns None if the agent chooses not to trade this period (e.g. no
    inventory to sell, no cash to buy, or insufficient price history for a
    speculator's trend signal).
    """
    last_price = price_history[-1] if price_history else 100.0

    if agent.role == "producer":
        # Elastic margin: scarce inventory → higher margin, abundant → thinner.
        # Ratio is inventory to production capacity (a natural scale for "how
        # full is the warehouse?").
        capacity = max(1, agent.production_capacity)
        inv_ratio = agent.inventory / capacity
        if inv_ratio < 0.5:
            margin = 1.20   # scarce — hold out for a premium
        elif inv_ratio < 1.5:
            margin = 1.12
        else:
            margin = 1.06   # excess stock — accept thin margin

        ask_price = agent.production_cost * margin
        qty = min(agent.inventory, agent.production_capacity)
        if qty <= 0:
            return None
        return Order(
            agent_id=agent.agent_id,
            side="sell",
            quantity=qty,
            limit_price=round(ask_price, 2),
            reasoning=f"sell at cost*{margin:.2f}, inv={agent.inventory}",
        )

    if agent.role == "consumer":
        # Elastic discount: low stock → small discount (urgent buyer),
        # well-stocked → larger discount (patient buyer).
        demand = max(1, agent.demand_per_period)
        inv_ratio = agent.inventory / demand
        if inv_ratio < 1:
            discount = 0.03   # urgent
        elif inv_ratio < 2:
            discount = 0.08
        else:
            discount = 0.15   # patient

        bid_price = agent.demand_value * (1 - discount)
        if bid_price <= 0:
            return None

        max_affordable = int(agent.cash / bid_price) if bid_price > 0 else 0
        qty = min(demand, max_affordable)
        if qty <= 0:
            return None
        return Order(
            agent_id=agent.agent_id,
            side="buy",
            quantity=qty,
            limit_price=round(bid_price, 2),
            reasoning=f"buy at value*{1 - discount:.2f}, inv={agent.inventory}",
        )

    if agent.role == "speculator":
        if len(price_history) < 2:
            return None
        trend = price_history[-1] - price_history[-2]

        if agent.agent_id == "speculator_A":
            # Momentum: buy uptrends, sell downtrends
            if trend > 0:
                qty = min(5, int(agent.cash / last_price)) if last_price > 0 else 0
                if qty > 0:
                    return Order(
                        agent_id=agent.agent_id,
                        side="buy",
                        quantity=qty,
                        limit_price=round(last_price * 1.02, 2),
                        reasoning=f"momentum buy, trend={trend:.2f}",
                    )
            elif trend < 0:
                qty = min(5, agent.inventory)
                if qty > 0:
                    return Order(
                        agent_id=agent.agent_id,
                        side="sell",
                        quantity=qty,
                        limit_price=round(last_price * 0.98, 2),
                        reasoning=f"momentum sell, trend={trend:.2f}",
                    )
            return None

        if agent.agent_id == "speculator_B":
            # Contrarian: sell uptrends, buy downtrends
            if trend > 0:
                qty = min(5, agent.inventory)
                if qty > 0:
                    return Order(
                        agent_id=agent.agent_id,
                        side="sell",
                        quantity=qty,
                        limit_price=round(last_price * 1.05, 2),
                        reasoning=f"contrarian sell, trend={trend:.2f}",
                    )
            elif trend < 0:
                qty = min(5, int(agent.cash / last_price)) if last_price > 0 else 0
                if qty > 0:
                    return Order(
                        agent_id=agent.agent_id,
                        side="buy",
                        quantity=qty,
                        limit_price=round(last_price * 0.95, 2),
                        reasoning=f"contrarian buy, trend={trend:.2f}",
                    )
            return None

    return None


def collect_rule_based_orders(agents: dict, state) -> list[Order]:
    """Collect orders from all agents in a MarketState.

    Convenience wrapper: iterates agents, calls ``rule_based_order`` for each,
    and returns the list of non-None orders.
    """
    orders: list[Order] = []
    for agent in agents.values():
        order = rule_based_order(agent, state.price_history)
        if order is not None:
            orders.append(order)
    return orders
