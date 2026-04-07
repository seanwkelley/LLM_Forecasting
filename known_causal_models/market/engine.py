"""
Market Engine — Deterministic double-auction clearing mechanism.

No LLM involvement. Orders in, prices out.

Clearing algorithm:
1. Sort buy orders descending by price, sell orders ascending by price.
2. Walk both sides; match when buy_price >= sell_price.
3. Clearing price = midpoint of marginal matched pair.
4. All matched orders execute at clearing price (uniform pricing).
5. Unmatched orders are cancelled (no order book persistence).

Each period is an independent call auction (batch clearing), not a continuous
limit order book. This keeps the mechanism simple and PID-friendly — one price
per period, one action per agent per period.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Order:
    """A single buy or sell order."""
    agent_id: str
    side: str          # "buy" or "sell"
    quantity: int       # units
    limit_price: float  # max price (buy) or min price (sell)
    reasoning: str = "" # LLM's reasoning (logged, not used by engine)


@dataclass
class Fill:
    """Execution record for a matched order."""
    agent_id: str
    side: str
    quantity: int
    price: float        # clearing price


@dataclass
class MarketState:
    """Tracks all agent and market state across periods."""

    # Agent states: agent_id -> AgentState
    agents: dict[str, AgentState] = field(default_factory=dict)

    # Market history
    price_history: list[float] = field(default_factory=list)
    volume_history: list[int] = field(default_factory=list)
    order_history: list[list[Order]] = field(default_factory=list)
    fill_history: list[list[Fill]] = field(default_factory=list)

    # Current period
    period: int = 0

    # Fundamental reference price (computed from supply/demand curves)
    fundamental_history: list[float] = field(default_factory=list)


@dataclass
class AgentState:
    """Per-agent state: budget, inventory, role info."""
    agent_id: str
    role: str               # "producer", "consumer", "speculator"
    cash: float             # available cash
    inventory: int          # units held
    initial_cash: float = 0.0
    initial_inventory: int = 0

    # Role-specific parameters
    production_cost: float = 0.0      # producer: cost per unit to produce
    production_capacity: int = 0      # producer: max units per period
    demand_per_period: int = 0        # consumer: units needed per period
    demand_value: float = 0.0         # consumer: value per unit consumed
    storage_cost: float = 0.0         # cost per unit held per period

    # Tracking
    pnl_history: list[float] = field(default_factory=list)
    trade_history: list[Fill] = field(default_factory=list)

    def total_value(self, current_price: float) -> float:
        """Mark-to-market portfolio value."""
        return self.cash + self.inventory * current_price

    def unrealized_pnl(self, current_price: float) -> float:
        """P&L relative to initial endowment."""
        return self.total_value(current_price) - (
            self.initial_cash + self.initial_inventory * current_price
        )


def validate_order(order: Order, agent: AgentState) -> Order:
    """Truncate order to agent's capacity. Returns adjusted order."""
    order = copy.copy(order)

    if order.quantity <= 0:
        order.quantity = 0
        return order

    if order.side == "buy":
        # Can't spend more cash than available
        max_qty = int(agent.cash / order.limit_price) if order.limit_price > 0 else 0
        order.quantity = min(order.quantity, max_qty)
    elif order.side == "sell":
        # Can't sell more than inventory
        order.quantity = min(order.quantity, agent.inventory)

    return order


def clear_market(orders: list[Order]) -> tuple[Optional[float], int, list[Fill]]:
    """Run a single-period call auction.

    Parameters
    ----------
    orders : list[Order]
        All submitted orders for this period.

    Returns
    -------
    clearing_price : float or None
        Uniform clearing price. None if no trades matched.
    total_volume : int
        Total units traded.
    fills : list[Fill]
        Execution records for all matched orders.
    """
    buys = sorted(
        [o for o in orders if o.side == "buy" and o.quantity > 0],
        key=lambda o: -o.limit_price,  # highest bid first
    )
    sells = sorted(
        [o for o in orders if o.side == "sell" and o.quantity > 0],
        key=lambda o: o.limit_price,   # lowest ask first
    )

    if not buys or not sells:
        return None, 0, []

    # Walk both sides to find total matchable volume and marginal price
    matched_pairs = []  # (buy_order, sell_order, qty)
    b_idx, s_idx = 0, 0
    buy_remaining = {i: buys[i].quantity for i in range(len(buys))}
    sell_remaining = {i: sells[i].quantity for i in range(len(sells))}

    while b_idx < len(buys) and s_idx < len(sells):
        if buys[b_idx].limit_price >= sells[s_idx].limit_price:
            qty = min(buy_remaining[b_idx], sell_remaining[s_idx])
            matched_pairs.append((b_idx, s_idx, qty))
            buy_remaining[b_idx] -= qty
            sell_remaining[s_idx] -= qty
            if buy_remaining[b_idx] == 0:
                b_idx += 1
            if sell_remaining[s_idx] == 0:
                s_idx += 1
        else:
            break

    if not matched_pairs:
        return None, 0, []

    # Clearing price = midpoint of marginal matched pair
    last_buy_idx, last_sell_idx, _ = matched_pairs[-1]
    clearing_price = (buys[last_buy_idx].limit_price + sells[last_sell_idx].limit_price) / 2

    # Generate fills
    total_volume = 0
    fills = []
    for b_idx, s_idx, qty in matched_pairs:
        fills.append(Fill(
            agent_id=buys[b_idx].agent_id,
            side="buy",
            quantity=qty,
            price=clearing_price,
        ))
        fills.append(Fill(
            agent_id=sells[s_idx].agent_id,
            side="sell",
            quantity=qty,
            price=clearing_price,
        ))
        total_volume += qty

    return clearing_price, total_volume, fills


def apply_fills(state: MarketState, fills: list[Fill]):
    """Update agent cash and inventory from fills."""
    for fill in fills:
        agent = state.agents[fill.agent_id]
        if fill.side == "buy":
            agent.cash -= fill.quantity * fill.price
            agent.inventory += fill.quantity
        elif fill.side == "sell":
            agent.cash += fill.quantity * fill.price
            agent.inventory -= fill.quantity
        agent.trade_history.append(fill)


def apply_period_costs(state: MarketState):
    """Apply storage costs and production/consumption at period end."""
    for agent in state.agents.values():
        # Storage cost
        if agent.storage_cost > 0 and agent.inventory > 0:
            cost = agent.storage_cost * agent.inventory
            agent.cash -= cost

        # Producer: produce up to capacity (adds to inventory, costs money)
        # Only produce what the agent can afford
        if agent.role == "producer" and agent.production_capacity > 0:
            max_affordable = int(agent.cash / agent.production_cost) if agent.production_cost > 0 else 0
            produced = min(int(agent.production_capacity), max(0, max_affordable))
            agent.inventory += produced
            agent.cash -= produced * agent.production_cost

        # Consumer: consume from inventory (gains utility value)
        if agent.role == "consumer" and agent.demand_per_period > 0:
            consumed = min(int(agent.demand_per_period), int(agent.inventory))
            agent.inventory -= consumed
            agent.cash += consumed * agent.demand_value
            # Unmet demand penalty (implicit: missed utility)


def compute_fundamental_price(state: MarketState) -> float:
    """Compute theoretical equilibrium price from supply/demand curves.

    Supply curve: producers willing to sell at prices above their production cost.
    Demand curve: consumers willing to buy at prices below their demand value.

    Intersection of these curves gives the fundamental reference price.
    """
    # Build supply schedule: (price, cumulative_quantity)
    supply_points = []
    for agent in state.agents.values():
        if agent.role == "producer":
            # Willing to sell at any price above production cost
            supply_points.append((agent.production_cost, agent.production_capacity))

    # Build demand schedule: (price, cumulative_quantity)
    demand_points = []
    for agent in state.agents.values():
        if agent.role == "consumer":
            # Willing to buy at any price below demand value
            demand_points.append((agent.demand_value, agent.demand_per_period))

    if not supply_points or not demand_points:
        # Fall back to last price or midpoint
        if state.price_history:
            return state.price_history[-1]
        return 100.0  # default

    # Sort supply ascending (cheapest first), demand descending (highest value first)
    supply_points.sort(key=lambda x: x[0])
    demand_points.sort(key=lambda x: -x[0])

    # Walk supply and demand curves to find crossing
    s_idx, d_idx = 0, 0
    cum_supply, cum_demand = 0, 0
    fundamental = (supply_points[0][0] + demand_points[0][0]) / 2  # default

    while s_idx < len(supply_points) and d_idx < len(demand_points):
        s_price, s_qty = supply_points[s_idx]
        d_price, d_qty = demand_points[d_idx]

        if s_price > d_price:
            # No overlap — fundamental is midpoint of closest pair
            break

        # Fundamental price = midpoint of marginal supply/demand
        fundamental = (s_price + d_price) / 2

        cum_supply += s_qty
        cum_demand += d_qty

        if cum_supply <= cum_demand:
            s_idx += 1
        else:
            d_idx += 1

    return fundamental


def run_period(state: MarketState, orders: list[Order]) -> dict:
    """Execute one market period.

    Parameters
    ----------
    state : MarketState
        Current market state (modified in place).
    orders : list[Order]
        Raw orders from agents (will be validated/truncated).

    Returns
    -------
    dict with keys:
        clearing_price, volume, fills, fundamental_price,
        n_buy_orders, n_sell_orders, bid_ask_spread
    """
    # Validate orders against agent constraints
    validated = []
    for order in orders:
        if order.agent_id in state.agents:
            v = validate_order(order, state.agents[order.agent_id])
            if v.quantity > 0:
                validated.append(v)

    # Clear market
    clearing_price, volume, fills = clear_market(validated)

    # If no trades, use last price
    if clearing_price is None:
        clearing_price = state.price_history[-1] if state.price_history else 100.0
        volume = 0
        fills = []

    # Apply fills
    apply_fills(state, fills)

    # Apply period costs (storage, production, consumption)
    apply_period_costs(state)

    # Compute fundamental
    fundamental = compute_fundamental_price(state)

    # Record history
    state.price_history.append(clearing_price)
    state.volume_history.append(volume)
    state.order_history.append(validated)
    state.fill_history.append(fills)
    state.fundamental_history.append(fundamental)

    # Record agent P&L snapshots
    for agent in state.agents.values():
        agent.pnl_history.append(agent.unrealized_pnl(clearing_price))

    state.period += 1

    # Compute spread for diagnostics
    buy_prices = [o.limit_price for o in validated if o.side == "buy"]
    sell_prices = [o.limit_price for o in validated if o.side == "sell"]
    best_bid = max(buy_prices) if buy_prices else None
    best_ask = min(sell_prices) if sell_prices else None
    spread = (best_ask - best_bid) if (best_bid is not None and best_ask is not None) else None

    return {
        "period": state.period,
        "clearing_price": clearing_price,
        "volume": volume,
        "fills": fills,
        "fundamental_price": fundamental,
        "n_buy_orders": len([o for o in validated if o.side == "buy"]),
        "n_sell_orders": len([o for o in validated if o.side == "sell"]),
        "bid_ask_spread": spread,
    }
