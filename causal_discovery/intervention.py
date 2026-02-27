"""
Intervention Interface — Clamp-and-react rollouts on market and conflict engines.

Supports three intervention types (action, trait, event) with uniform semantics:
fix the target variable, re-run the engine for N periods, let all other agents
react normally.

Trait overrides support single-agent ("agent_id"), role-level ("role" for market),
and faction-level ("faction" for conflict) targeting.

Usage:
    # Market: force producer_A to set limit_price = 85
    intervention = Intervention(
        type="action",
        target={"agent_id": "producer_A", "param": "limit_price", "value": 85.0},
        run_periods=3,
    )
    result = run_market_intervention(state_snapshot, intervention, ...)

    # Market: override ALL producers' production_cost
    intervention = Intervention(
        type="trait",
        target={"role": "producer", "param": "production_cost", "value": 200},
        run_periods=3,
    )

    # Conflict: set ALL novaris agents' hawk_dove to 0.1
    intervention = Intervention(
        type="trait",
        target={"faction": "novaris", "param": "hawk_dove", "value": 0.1},
        run_periods=3,
    )
    result = run_conflict_intervention(state_snapshot, intervention, ...)
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any


@dataclass
class Intervention:
    """Specification for a single interventional query."""
    type: str               # "action", "trait", "event"
    target: dict            # {agent_id, param, value} or {role/faction, param, value}
                            # or {shock_type, magnitude, ...}
    run_periods: int = 3
    description: str = ""   # human-readable summary


@dataclass
class InterventionResult:
    """Outcome of an interventional rollout vs. baseline."""
    intervention: Intervention
    baseline_trajectory: list[dict]      # per-period outcomes without intervention
    intervention_trajectory: list[dict]  # per-period outcomes with intervention
    variables_returned: list[str]        # which variables are in the trajectory dicts


# =============================================================================
# Market Intervention
# =============================================================================

def run_market_intervention(
    state_snapshot: Any,          # MarketState (deep-copied before use)
    agents_snapshot: dict,        # {agent_id: AgentState}
    base_params: dict,            # shock-resettable params
    shocks: list,                 # shock sequence
    start_period: int,            # which period to start from
    intervention: Intervention,
    return_vars: list[str] | None = None,
    rule_based: bool = True,      # use rule-based agents (fast) or LLM
    llm_pool: Any = None,         # LLMAgentPool if rule_based=False
    scenario_config: dict | None = None,
) -> InterventionResult:
    """Run a market intervention rollout.

    Deep-copies the state, applies the intervention, runs N periods, and
    compares to a baseline rollout from the same starting state.

    Parameters
    ----------
    state_snapshot : MarketState
        Engine state at the intervention start point.
    agents_snapshot : dict
        Agent states at the intervention start point.
    base_params : dict
        Baseline agent parameters for shock reset.
    shocks : list[Shock]
        Pre-generated shock sequence for this scenario.
    start_period : int
        Period number to start the rollout from.
    intervention : Intervention
        What to clamp.
    return_vars : list[str], optional
        Which variables to include in trajectory. Default: all.
    rule_based : bool
        If True, use rule-based agents. If False, use LLM agents (requires llm_pool).
    llm_pool : LLMAgentPool, optional
        Required if rule_based=False.
    scenario_config : dict, optional
        Scenario configuration (needed for price ticks, etc.).
    """
    from market.engine import MarketState, Order, run_period, AgentState
    from market.shocks import apply_shocks, get_active_shocks, describe_shocks

    if return_vars is None:
        return_vars = [
            "clearing_price", "volume", "fundamental_price",
            "avg_bid_price", "avg_ask_price",
            "total_bid_qty", "total_ask_qty",
            "total_cash", "total_inventory",
        ]

    n_periods = intervention.run_periods

    # --- Run baseline rollout ---
    baseline_state = copy.deepcopy(state_snapshot)
    baseline_agents = copy.deepcopy(agents_snapshot)
    baseline_base_params = copy.deepcopy(base_params)
    baseline_trajectory = _run_market_rollout(
        state=baseline_state,
        agents=baseline_agents,
        base_params=baseline_base_params,
        shocks=shocks,
        start_period=start_period,
        n_periods=n_periods,
        overrides=None,
        rule_based=rule_based,
        llm_pool=llm_pool,
        scenario_config=scenario_config,
    )

    # --- Run intervention rollout ---
    int_state = copy.deepcopy(state_snapshot)
    int_agents = copy.deepcopy(agents_snapshot)
    int_base_params = copy.deepcopy(base_params)

    # Build overrides from intervention spec
    overrides = _build_market_overrides(intervention, int_agents, int_base_params)

    int_trajectory = _run_market_rollout(
        state=int_state,
        agents=int_agents,
        base_params=int_base_params,
        shocks=shocks,
        start_period=start_period,
        n_periods=n_periods,
        overrides=overrides,
        rule_based=rule_based,
        llm_pool=llm_pool,
        scenario_config=scenario_config,
    )

    # Filter to requested variables
    baseline_filtered = [
        {k: v for k, v in period.items() if k in return_vars or k == "period"}
        for period in baseline_trajectory
    ]
    int_filtered = [
        {k: v for k, v in period.items() if k in return_vars or k == "period"}
        for period in int_trajectory
    ]

    return InterventionResult(
        intervention=intervention,
        baseline_trajectory=baseline_filtered,
        intervention_trajectory=int_filtered,
        variables_returned=return_vars,
    )


def _build_market_overrides(
    intervention: Intervention,
    agents: dict,
    base_params: dict,
) -> dict:
    """Convert an Intervention spec into engine-level overrides.

    Returns a dict describing what to override during the rollout.
    """
    overrides = {"type": intervention.type}

    if intervention.type == "action":
        # Override a specific agent's order
        target = intervention.target
        overrides["agent_id"] = target["agent_id"]
        overrides["param"] = target["param"]  # "limit_price", "quantity", or "side"
        overrides["value"] = target["value"]

    elif intervention.type == "trait":
        target = intervention.target
        param = target["param"]
        value = target["value"]

        if "role" in target:
            # Role-level override: apply to ALL agents matching this role
            role = target["role"]
            for agent_id, agent in agents.items():
                if agent.role == role:
                    setattr(agent, param, value)
                    if agent_id in base_params and param in base_params[agent_id]:
                        base_params[agent_id][param] = value
        else:
            # Single-agent override
            agent_id = target["agent_id"]
            if agent_id in agents:
                setattr(agents[agent_id], param, value)
            if agent_id in base_params and param in base_params[agent_id]:
                base_params[agent_id][param] = value

        overrides["applied"] = True  # trait overrides are pre-applied

    elif intervention.type == "event":
        # Inject or suppress a shock
        target = intervention.target
        overrides["shock_type"] = target.get("shock_type")
        overrides["magnitude"] = target.get("magnitude")
        overrides["suppress"] = target.get("suppress", False)

    return overrides


def _run_market_rollout(
    state,
    agents: dict,
    base_params: dict,
    shocks: list,
    start_period: int,
    n_periods: int,
    overrides: dict | None,
    rule_based: bool,
    llm_pool,
    scenario_config: dict | None,
) -> list[dict]:
    """Execute N periods of market simulation, optionally with overrides."""
    from market.engine import Order, run_period
    from market.shocks import apply_shocks, get_active_shocks, describe_shocks, Shock, SHOCK_TYPES
    from market.prompts import generate_price_ticks

    # CRITICAL: state.agents and the agents dict must be the same object,
    # otherwise overrides applied to agents won't reach the engine
    # (run_period uses state.agents for validation)
    state.agents = agents

    trajectory = []

    for i in range(n_periods):
        t = start_period + i

        # --- Apply shocks (possibly with event override) ---
        if overrides and overrides["type"] == "event" and not overrides.get("suppress"):
            # Inject a forced shock for this period
            forced_shock = Shock(
                period=t,
                shock_type=overrides["shock_type"],
                magnitude=overrides["magnitude"],
                duration=1,
                target_role=SHOCK_TYPES.get(overrides["shock_type"], {}).get("target_role"),
                description=f"Forced {overrides['shock_type']}",
            )
            augmented_shocks = shocks + [forced_shock]
            apply_shocks(agents, augmented_shocks, t, base_params)
        elif overrides and overrides["type"] == "event" and overrides.get("suppress"):
            # Suppress all shocks of the given type
            filtered = [s for s in shocks if s.shock_type != overrides["shock_type"]]
            apply_shocks(agents, filtered, t, base_params)
        else:
            apply_shocks(agents, shocks, t, base_params)

        # --- Collect orders ---
        if rule_based:
            orders = _market_rule_based_orders(agents, state)
        else:
            ref_price = state.price_history[-1] if state.price_history else (
                scenario_config["base_price"] if scenario_config else 100.0
            )
            price_ticks = generate_price_ticks(ref_price, n_ticks=15, spread_pct=0.30)
            active = get_active_shocks(shocks, t)
            shock_desc = describe_shocks(shocks, t) if active else ""
            orders = llm_pool.collect_orders(
                agent_states=agents,
                market_state=state,
                price_ticks=price_ticks,
                shock_description=shock_desc,
                verbose=False,
            )

        # --- Apply action override ---
        if overrides and overrides["type"] == "action":
            orders = _apply_market_action_override(orders, overrides, agents)

        # --- Run period ---
        result = run_period(state, orders)

        # Add aggregate order stats for causal discovery observability
        buy_orders = [o for o in orders if o.side == "buy"]
        sell_orders = [o for o in orders if o.side == "sell"]
        result["avg_bid_price"] = (
            round(sum(o.limit_price for o in buy_orders) / len(buy_orders), 4)
            if buy_orders else 0
        )
        result["avg_ask_price"] = (
            round(sum(o.limit_price for o in sell_orders) / len(sell_orders), 4)
            if sell_orders else 0
        )
        result["total_bid_qty"] = sum(o.quantity for o in buy_orders)
        result["total_ask_qty"] = sum(o.quantity for o in sell_orders)

        # Add aggregate agent state
        result["total_cash"] = round(
            sum(agent.cash for agent in agents.values()), 4
        )
        result["total_inventory"] = sum(
            agent.inventory for agent in agents.values()
        )

        # Add agent states to result for richer trajectory
        agent_states = {}
        for aid, agent in agents.items():
            agent_states[aid] = {
                "cash": round(agent.cash, 2),
                "inventory": agent.inventory,
            }
        result["agent_states"] = agent_states
        result["orders"] = [
            {"agent_id": o.agent_id, "side": o.side,
             "quantity": o.quantity, "limit_price": o.limit_price}
            for o in orders
        ]

        trajectory.append(result)

    return trajectory


def _market_rule_based_orders(agents: dict, state) -> list:
    """Generate rule-based orders for all agents."""
    from market.engine import Order

    orders = []
    price_history = state.price_history

    for agent in agents.values():
        last_price = price_history[-1] if price_history else 100.0

        if agent.role == "producer":
            # Sell at production cost + margin, proportional to inventory
            margin = 1.10 + (agent.inventory / 100) * 0.05  # higher inventory → lower margin
            ask_price = agent.production_cost * margin
            qty = min(agent.inventory, agent.production_capacity)
            if qty > 0:
                orders.append(Order(
                    agent_id=agent.agent_id,
                    side="sell",
                    quantity=qty,
                    limit_price=round(ask_price, 2),
                ))

        elif agent.role == "consumer":
            # Buy at demand value - margin
            bid_price = agent.demand_value * 0.95
            max_qty = int(agent.cash / bid_price) if bid_price > 0 else 0
            qty = min(agent.demand_per_period, max_qty)
            if qty > 0:
                orders.append(Order(
                    agent_id=agent.agent_id,
                    side="buy",
                    quantity=qty,
                    limit_price=round(bid_price, 2),
                ))

        elif agent.role == "speculator":
            if len(price_history) < 2:
                continue
            trend = price_history[-1] - price_history[-2]
            if trend > 0 and agent.agent_id == "speculator_A":
                # Momentum: buy in uptrend
                qty = min(5, int(agent.cash / last_price) if last_price > 0 else 0)
                if qty > 0:
                    orders.append(Order(
                        agent_id=agent.agent_id,
                        side="buy",
                        quantity=qty,
                        limit_price=round(last_price * 1.02, 2),
                    ))
            elif trend < 0 and agent.agent_id == "speculator_A":
                # Momentum: sell in downtrend
                qty = min(5, agent.inventory)
                if qty > 0:
                    orders.append(Order(
                        agent_id=agent.agent_id,
                        side="sell",
                        quantity=qty,
                        limit_price=round(last_price * 0.98, 2),
                    ))
            elif trend > 0 and agent.agent_id == "speculator_B":
                # Contrarian: sell in uptrend
                qty = min(5, agent.inventory)
                if qty > 0:
                    orders.append(Order(
                        agent_id=agent.agent_id,
                        side="sell",
                        quantity=qty,
                        limit_price=round(last_price * 1.05, 2),
                    ))
            elif trend < 0 and agent.agent_id == "speculator_B":
                # Contrarian: buy in downtrend
                qty = min(5, int(agent.cash / last_price) if last_price > 0 else 0)
                if qty > 0:
                    orders.append(Order(
                        agent_id=agent.agent_id,
                        side="buy",
                        quantity=qty,
                        limit_price=round(last_price * 0.95, 2),
                    ))

    return orders


def _apply_market_action_override(orders: list, overrides: dict, agents: dict) -> list:
    """Replace a specific agent's order parameter with the intervention value."""
    from market.engine import Order

    target_id = overrides["agent_id"]
    param = overrides["param"]
    value = overrides["value"]

    new_orders = []
    found = False

    for order in orders:
        if order.agent_id == target_id:
            found = True
            order = copy.copy(order)
            if param == "limit_price":
                order.limit_price = value
            elif param == "quantity":
                order.quantity = int(value)
            elif param == "side":
                order.side = value
            new_orders.append(order)
        else:
            new_orders.append(order)

    # If agent didn't submit an order, create one with the forced value
    if not found and target_id in agents:
        agent = agents[target_id]
        if param == "limit_price":
            side = "sell" if agent.role == "producer" else "buy"
            qty = 10  # default quantity
            new_orders.append(Order(
                agent_id=target_id,
                side=side,
                quantity=qty,
                limit_price=value,
            ))

    return new_orders


# =============================================================================
# Conflict Intervention
# =============================================================================

def run_conflict_intervention(
    state_snapshot: Any,          # ConflictState
    agents_config: list[dict],    # agent config dicts (with hawk_dove, role, etc.)
    faction_agents: dict,         # {faction_id: [agent_ids]}
    shocks: list,                 # shock sequence
    start_period: int,
    intervention: Intervention,
    return_vars: list[str] | None = None,
    rule_based: bool = True,
    llm_pool: Any = None,
) -> InterventionResult:
    """Run a conflict intervention rollout.

    Parameters
    ----------
    state_snapshot : ConflictState
        Engine state at the intervention start point.
    agents_config : list[dict]
        Agent configuration dicts (each has agent_id, role, faction, hawk_dove, etc.).
    faction_agents : dict
        Mapping from faction_id to list of agent config dicts.
    shocks : list[Shock]
        Pre-generated shock sequence.
    start_period : int
        Period number to start from.
    intervention : Intervention
        What to clamp.
    return_vars : list[str], optional
        Which variables to return. Default: all state variables.
    rule_based : bool
        If True, use rule-based agents.
    llm_pool : LLMAgentPool, optional
        Required if rule_based=False.
    """
    from conflict.engine import ConflictState

    if return_vars is None:
        return_vars = [
            "escalation_index", "military_balance", "territory_controlled",
            "sanctions_level", "international_support",
            "novaris_resources", "tethys_resources",
            "novaris_gdp", "tethys_gdp",
            "novaris_military_strength", "tethys_military_strength",
            "novaris_political_stability", "tethys_political_stability",
            "novaris_rec_escalation", "tethys_rec_escalation",
            "novaris_action_delta", "tethys_action_delta",
        ]

    n_periods = intervention.run_periods

    # --- Baseline rollout ---
    baseline_state = copy.deepcopy(state_snapshot)
    baseline_agents = copy.deepcopy(agents_config)
    baseline_trajectory = _run_conflict_rollout(
        state=baseline_state,
        agents_config=baseline_agents,
        shocks=shocks,
        start_period=start_period,
        n_periods=n_periods,
        overrides=None,
        rule_based=rule_based,
        llm_pool=llm_pool,
    )

    # --- Intervention rollout ---
    int_state = copy.deepcopy(state_snapshot)
    int_agents = copy.deepcopy(agents_config)

    overrides = _build_conflict_overrides(intervention, int_agents, int_state)

    int_trajectory = _run_conflict_rollout(
        state=int_state,
        agents_config=int_agents,
        shocks=shocks,
        start_period=start_period,
        n_periods=n_periods,
        overrides=overrides,
        rule_based=rule_based,
        llm_pool=llm_pool,
    )

    # Filter to requested variables
    baseline_filtered = [
        {k: v for k, v in period.items() if k in return_vars or k == "period"}
        for period in baseline_trajectory
    ]
    int_filtered = [
        {k: v for k, v in period.items() if k in return_vars or k == "period"}
        for period in int_trajectory
    ]

    return InterventionResult(
        intervention=intervention,
        baseline_trajectory=baseline_filtered,
        intervention_trajectory=int_filtered,
        variables_returned=return_vars,
    )


def _build_conflict_overrides(
    intervention: Intervention,
    agents_config: list[dict],
    state: Any,
) -> dict:
    """Convert an Intervention spec into conflict engine overrides."""
    overrides = {"type": intervention.type}

    if intervention.type == "action":
        # Force a specific agent's recommendation
        target = intervention.target
        overrides["agent_id"] = target["agent_id"]
        overrides["action_name"] = target["value"]

    elif intervention.type == "trait":
        target = intervention.target
        param = target["param"]
        value = target["value"]

        if "faction" in target:
            # Faction-level override: apply to ALL agents in this faction
            faction = target["faction"]
            for agent in agents_config:
                if agent["faction"] == faction:
                    agent[param] = value
        else:
            # Single-agent override
            agent_id = target["agent_id"]
            for agent in agents_config:
                if agent["agent_id"] == agent_id:
                    agent[param] = value
                    break

        overrides["applied"] = True

    elif intervention.type == "event":
        target = intervention.target
        overrides["shock_type"] = target.get("shock_type")
        overrides["magnitude"] = target.get("magnitude")
        overrides["suppress"] = target.get("suppress", False)

    return overrides


def _run_conflict_rollout(
    state,
    agents_config: list[dict],
    shocks: list,
    start_period: int,
    n_periods: int,
    overrides: dict | None,
    rule_based: bool,
    llm_pool,
) -> list[dict]:
    """Execute N periods of conflict simulation, optionally with overrides."""
    from conflict.engine import (
        Action, ACTION_SPACE, aggregate_faction_action, run_period,
    )
    from conflict.shocks import apply_shocks, get_active_shocks, describe_shocks, Shock, SHOCK_TYPES

    trajectory = []

    for i in range(n_periods):
        t = start_period + i

        # --- Apply shocks (possibly with event override) ---
        if overrides and overrides["type"] == "event" and not overrides.get("suppress"):
            forced_shock = Shock(
                period=t,
                shock_type=overrides["shock_type"],
                magnitude=overrides["magnitude"],
                duration=1,
                target_faction=SHOCK_TYPES.get(overrides["shock_type"], {}).get("target_faction"),
                description=f"Forced {overrides['shock_type']}",
            )
            augmented_shocks = shocks + [forced_shock]
            apply_shocks(state, augmented_shocks, t)
        elif overrides and overrides["type"] == "event" and overrides.get("suppress"):
            filtered = [s for s in shocks if s.shock_type != overrides["shock_type"]]
            apply_shocks(state, filtered, t)
        else:
            apply_shocks(state, shocks, t)

        # --- Collect recommendations ---
        if rule_based:
            recommendations = _conflict_rule_based_recommendations(agents_config, state)
        else:
            shock_desc = describe_shocks(shocks, t) if get_active_shocks(shocks, t) else ""
            recommendations = llm_pool.collect_recommendations(
                state=state,
                shock_description=shock_desc,
                verbose=False,
            )

        # --- Apply action override ---
        if overrides and overrides["type"] == "action":
            recommendations = _apply_conflict_action_override(
                recommendations, overrides
            )

        # --- Aggregate by faction ---
        novaris_recs = [r for r in recommendations if r["faction"] == "novaris"]
        tethys_recs = [r for r in recommendations if r["faction"] == "tethys"]

        novaris_action = aggregate_faction_action(novaris_recs, "novaris")
        tethys_action = aggregate_faction_action(tethys_recs, "tethys")

        # --- Run period ---
        result = run_period(state, novaris_action, tethys_action)

        # Add faction-level state for richer observation
        for faction_id in ["novaris", "tethys"]:
            f = state.factions[faction_id]
            result[f"{faction_id}_gdp"] = round(f.gdp, 4)
            result[f"{faction_id}_military_strength"] = round(f.military_strength, 4)
            result[f"{faction_id}_political_stability"] = round(f.political_stability, 4)

        # Add aggregate recommendation stats (scalar proxies for agent_recommendation)
        nov_deltas = []
        teth_deltas = []
        for rec in recommendations:
            spec = ACTION_SPACE.get(rec["action"])
            if spec:
                delta = spec["escalation_delta"]
                if rec["faction"] == "novaris":
                    nov_deltas.append(delta)
                else:
                    teth_deltas.append(delta)
        result["novaris_rec_escalation"] = round(
            sum(nov_deltas) / len(nov_deltas), 4
        ) if nov_deltas else 0
        result["tethys_rec_escalation"] = round(
            sum(teth_deltas) / len(teth_deltas), 4
        ) if teth_deltas else 0

        # Add faction action escalation deltas (scalar proxy for faction_action)
        # Use continuous delta when available (preserves weighted avg before snapping)
        result["novaris_action_delta"] = round(
            novaris_action.continuous_delta if novaris_action.continuous_delta is not None
            else ACTION_SPACE.get(novaris_action.action_name, {}).get("escalation_delta", 0), 4
        )
        result["tethys_action_delta"] = round(
            tethys_action.continuous_delta if tethys_action.continuous_delta is not None
            else ACTION_SPACE.get(tethys_action.action_name, {}).get("escalation_delta", 0), 4
        )

        # Add recommendation details
        result["recommendations"] = [
            {"agent_id": r["agent_id"], "action": r["action"]}
            for r in recommendations
        ]

        trajectory.append(result)

    return trajectory


def _conflict_rule_based_recommendations(
    agents_config: list[dict],
    state,
) -> list[dict]:
    """Generate rule-based recommendations using hawk/dove scores."""
    from conflict.engine import ACTION_SPACE
    from conflict.agents_config import compute_state_modifier

    recommendations = []

    for agent in agents_config:
        hawk_score = agent["hawk_dove"]
        state_mod = compute_state_modifier(agent, state)
        effective_hawk = max(0.05, min(0.95, hawk_score + state_mod))
        ei = state.escalation_index

        # Target delta from effective hawk/dove score, modulated by EI
        if ei > 8.0:
            target_delta = (effective_hawk - 0.5) * 1.0
        elif ei < 2.0:
            target_delta = (effective_hawk - 0.5) * 1.0
        else:
            target_delta = (effective_hawk - 0.5) * 3.0

        # Find affordable action closest to target delta
        own_faction = state.factions[agent["faction"]]
        affordable = [
            (name, spec) for name, spec in ACTION_SPACE.items()
            if spec["cost"] <= own_faction.resources
        ]

        if not affordable:
            action_name = "intelligence_gathering"
        else:
            action_name = min(
                affordable,
                key=lambda ns: abs(ns[1]["escalation_delta"] - target_delta),
            )[0]

        recommendations.append({
            "agent_id": agent["agent_id"],
            "agent_role": agent["role"],
            "faction": agent["faction"],
            "action": action_name,
            "reasoning": f"Rule-based (hawk={hawk_score:.2f}, state_mod={state_mod:+.3f}, eff={effective_hawk:.2f})",
        })

    return recommendations


def _apply_conflict_action_override(
    recommendations: list[dict],
    overrides: dict,
) -> list[dict]:
    """Replace a specific agent's recommendation with the forced action."""
    target_id = overrides["agent_id"]
    forced_action = overrides["action_name"]

    new_recs = []
    for rec in recommendations:
        if rec["agent_id"] == target_id:
            rec = copy.copy(rec)
            rec["action"] = forced_action
            rec["reasoning"] = f"FORCED: {forced_action}"
        new_recs.append(rec)

    return new_recs


# =============================================================================
# Convenience: format intervention results for LLM consumption
# =============================================================================

def format_result_for_agent(result: InterventionResult) -> str:
    """Format an intervention result as text for a causal modeler LLM agent."""
    lines = []
    lines.append(f"INTERVENTION: {result.intervention.type}")

    target = result.intervention.target
    if result.intervention.type == "action":
        if "param" in target:
            lines.append(f"  Fixed: {target['agent_id']}.{target['param']} = {target['value']}")
        else:
            lines.append(f"  Fixed: {target['agent_id']} action = {target['value']}")
    elif result.intervention.type == "trait":
        if "role" in target:
            lines.append(f"  Fixed: all {target['role']}s.{target['param']} = {target['value']}")
        elif "faction" in target:
            lines.append(f"  Fixed: all {target['faction']} agents.{target['param']} = {target['value']}")
        else:
            lines.append(f"  Fixed: {target['agent_id']}.{target['param']} = {target['value']}")
    elif result.intervention.type == "event":
        suppress = target.get("suppress", False)
        if suppress:
            lines.append(f"  Suppressed: {target['shock_type']}")
        else:
            lines.append(f"  Injected: {target['shock_type']} (magnitude={target['magnitude']})")

    lines.append(f"  Rollout: {result.intervention.run_periods} periods")
    lines.append("")

    # Compare trajectories
    lines.append("BASELINE trajectory:")
    for period in result.baseline_trajectory:
        vals = " | ".join(f"{k}={v}" for k, v in period.items() if k != "period")
        lines.append(f"  Period {period.get('period', '?')}: {vals}")

    lines.append("")
    lines.append("INTERVENTION trajectory:")
    for period in result.intervention_trajectory:
        vals = " | ".join(f"{k}={v}" for k, v in period.items() if k != "period")
        lines.append(f"  Period {period.get('period', '?')}: {vals}")

    # Compute deltas
    lines.append("")
    lines.append("EFFECT (intervention - baseline):")
    for var in result.variables_returned:
        baseline_vals = [p.get(var) for p in result.baseline_trajectory if p.get(var) is not None]
        int_vals = [p.get(var) for p in result.intervention_trajectory if p.get(var) is not None]
        if baseline_vals and int_vals:
            b_mean = sum(baseline_vals) / len(baseline_vals)
            i_mean = sum(int_vals) / len(int_vals)
            delta = i_mean - b_mean
            lines.append(f"  {var}: baseline_mean={b_mean:.4f}, intervention_mean={i_mean:.4f}, delta={delta:+.4f}")

    return "\n".join(lines)
