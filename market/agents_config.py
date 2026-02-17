"""
Agent Configuration — Defines market participants and their initial endowments.

Each scenario creates agents from these templates, with parameters varied
by scenario config (base_price, cost_spread, demand_intensity, etc.).
"""

from __future__ import annotations

from market.engine import AgentState


# Agent templates: role definitions with relative parameter scales.
# Actual values are set by create_agents() based on scenario config.

AGENT_TEMPLATES = [
    # --- Producers ---
    {
        "agent_id": "producer_A",
        "role": "producer",
        "description": "Volume Mover — prioritizes moving inventory over per-unit margin",
        "cost_multiplier": 0.7,      # relative to base_price
        "capacity": 30,              # units per period
        "initial_inventory": 50,     # starting stock
        "initial_cash": 5000,
        "storage_cost_pct": 0.005,   # % of base_price per unit per period
    },
    {
        "agent_id": "producer_B",
        "role": "producer",
        "description": "Margin Optimizer — patient, holds out for target margin",
        "cost_multiplier": 0.85,
        "capacity": 10,
        "initial_inventory": 20,
        "initial_cash": 4000,
        "storage_cost_pct": 0.005,
    },
    # --- Consumers ---
    {
        "agent_id": "consumer_A",
        "role": "consumer",
        "description": "Security Stockpiler — risk-averse, maintains large buffer stocks",
        "demand_base": 25,           # units per period
        "value_multiplier": 1.3,     # relative to base_price
        "initial_inventory": 30,
        "initial_cash": 8000,
        "storage_cost_pct": 0.008,
    },
    {
        "agent_id": "consumer_B",
        "role": "consumer",
        "description": "Bargain Hunter — patient, only buys at a discount",
        "demand_base": 12,
        "value_multiplier": 1.1,
        "initial_inventory": 10,
        "initial_cash": 4000,
        "storage_cost_pct": 0.008,
    },
    {
        "agent_id": "consumer_C",
        "role": "consumer",
        "description": "Shock Anticipator — forward-looking, swings between aggressive and passive",
        "demand_base": 15,
        "value_multiplier": 1.2,
        "initial_inventory": 20,
        "initial_cash": 5000,
        "storage_cost_pct": 0.008,
    },
    # --- Speculators ---
    {
        "agent_id": "speculator_A",
        "role": "speculator",
        "description": "Momentum Rider — trend-following, rides price momentum",
        "initial_inventory": 40,
        "initial_cash": 6000,
        "storage_cost_pct": 0.01,
    },
    {
        "agent_id": "speculator_B",
        "role": "speculator",
        "description": "Value Contrarian — mean-reversion, fades extreme moves",
        "initial_inventory": 30,
        "initial_cash": 5000,
        "storage_cost_pct": 0.01,
    },
]


def create_agents(
    scenario_config: dict,
    templates: list[dict] | None = None,
) -> tuple[dict[str, AgentState], dict[str, dict]]:
    """Create agent states and base parameters from scenario config.

    Parameters
    ----------
    scenario_config : dict
        From generate_scenario_configs(). Keys: base_price, cost_spread,
        demand_intensity, initial_inventory_level.
    templates : list[dict], optional
        Agent templates. Defaults to AGENT_TEMPLATES.

    Returns
    -------
    agents : dict[str, AgentState]
        Agent states keyed by agent_id.
    base_params : dict[str, dict]
        Snapshot of each agent's shock-resettable parameters.
    """
    if templates is None:
        templates = AGENT_TEMPLATES

    bp = scenario_config["base_price"]
    cost_spread = scenario_config.get("cost_spread", 0.5)
    demand_intensity = scenario_config.get("demand_intensity", 1.0)
    inv_level = scenario_config.get("initial_inventory_level", "medium")

    # Inventory multiplier
    inv_mult = {"low": 0.5, "medium": 1.0, "high": 1.5}.get(inv_level, 1.0)

    agents = {}
    base_params = {}

    for tmpl in templates:
        aid = tmpl["agent_id"]
        role = tmpl["role"]

        # Compute role-specific parameters
        if role == "producer":
            # Production cost varies with cost_spread
            base_cost = bp * tmpl["cost_multiplier"]
            # Apply spread: costs diverge more when cost_spread is high
            cost_offset = (tmpl["cost_multiplier"] - 0.775) * cost_spread * bp
            production_cost = max(1.0, base_cost + cost_offset)
            capacity = tmpl["capacity"]
            inv = int(tmpl["initial_inventory"] * inv_mult)
            cash = tmpl["initial_cash"]

            agent = AgentState(
                agent_id=aid,
                role=role,
                cash=cash,
                inventory=inv,
                initial_cash=cash,
                initial_inventory=inv,
                production_cost=round(production_cost, 2),
                production_capacity=capacity,
                storage_cost=round(bp * tmpl["storage_cost_pct"], 2),
            )

            base_params[aid] = {
                "production_cost": agent.production_cost,
                "production_capacity": agent.production_capacity,
                "storage_cost": agent.storage_cost,
            }

        elif role == "consumer":
            demand = max(1, int(tmpl["demand_base"] * demand_intensity))
            demand_value = round(bp * tmpl["value_multiplier"], 2)
            inv = int(tmpl["initial_inventory"] * inv_mult)
            cash = tmpl["initial_cash"]

            agent = AgentState(
                agent_id=aid,
                role=role,
                cash=cash,
                inventory=inv,
                initial_cash=cash,
                initial_inventory=inv,
                demand_per_period=demand,
                demand_value=demand_value,
                storage_cost=round(bp * tmpl["storage_cost_pct"], 2),
            )

            base_params[aid] = {
                "demand_per_period": agent.demand_per_period,
                "demand_value": agent.demand_value,
                "storage_cost": agent.storage_cost,
            }

        elif role == "speculator":
            inv = int(tmpl["initial_inventory"] * inv_mult)
            cash = tmpl["initial_cash"]

            agent = AgentState(
                agent_id=aid,
                role=role,
                cash=cash,
                inventory=inv,
                initial_cash=cash,
                initial_inventory=inv,
                storage_cost=round(bp * tmpl["storage_cost_pct"], 2),
            )

            base_params[aid] = {
                "storage_cost": agent.storage_cost,
            }

        agents[aid] = agent

    return agents, base_params


def get_agent_private_info(agent: AgentState, scenario_config: dict) -> dict:
    """Extract private information visible only to this agent.

    This is what goes into the agent's LLM prompt as private signals.
    Other agents cannot see this.
    """
    info = {
        "agent_id": agent.agent_id,
        "role": agent.role,
        "cash": round(agent.cash, 2),
        "inventory": agent.inventory,
        "storage_cost_per_unit": agent.storage_cost,
    }

    if agent.role == "producer":
        info.update({
            "production_cost_per_unit": agent.production_cost,
            "production_capacity_per_period": agent.production_capacity,
            "breakeven_price": round(agent.production_cost * 1.05, 2),  # 5% margin
        })
    elif agent.role == "consumer":
        info.update({
            "demand_per_period": agent.demand_per_period,
            "value_per_unit": agent.demand_value,
            "periods_of_inventory": (
                agent.inventory // agent.demand_per_period
                if agent.demand_per_period > 0 else 999
            ),
        })
    elif agent.role == "speculator":
        info.update({
            "position_value": round(
                agent.inventory * (scenario_config["base_price"]), 2
            ),
        })

    return info
