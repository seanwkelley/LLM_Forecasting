"""
Exogenous Shock Generator for Market Simulation.

Generates pre-determined shock sequences that create price variation across
scenarios. Shocks modify agent-level parameters (production costs, demand,
etc.) rather than directly setting prices.

Each scenario gets a unique shock sequence (seeded for reproducibility).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass
class Shock:
    """A single exogenous shock applied at a specific period."""
    period: int
    shock_type: str
    magnitude: float        # multiplier or additive, depends on type
    duration: int = 1       # how many periods the shock lasts
    target_role: Optional[str] = None  # which agent role is affected (None = all)
    description: str = ""


# Shock type definitions
SHOCK_TYPES = {
    "supply_disruption": {
        "description": "Production costs increase for producers",
        "target_role": "producer",
        "param": "production_cost",
        "mode": "multiply",     # multiply current value
        "magnitude_range": (1.2, 1.8),  # 20-80% cost increase
        "duration_range": (1, 3),
        "probability": 0.15,
    },
    "demand_surge": {
        "description": "Consumer demand increases",
        "target_role": "consumer",
        "param": "demand_per_period",
        "mode": "multiply",
        "magnitude_range": (1.3, 1.8),  # 30-80% demand increase
        "duration_range": (1, 3),
        "probability": 0.12,
    },
    "demand_drop": {
        "description": "Consumer demand decreases",
        "target_role": "consumer",
        "param": "demand_per_period",
        "mode": "multiply",
        "magnitude_range": (0.4, 0.7),  # 30-60% demand decrease
        "duration_range": (1, 2),
        "probability": 0.10,
    },
    "cost_reduction": {
        "description": "Production costs decrease (technology improvement)",
        "target_role": "producer",
        "param": "production_cost",
        "mode": "multiply",
        "magnitude_range": (0.6, 0.85),  # 15-40% cost reduction
        "duration_range": (2, 4),
        "probability": 0.08,
    },
    "storage_crisis": {
        "description": "Storage costs spike for all agents",
        "target_role": None,
        "param": "storage_cost",
        "mode": "multiply",
        "magnitude_range": (2.0, 4.0),  # 2-4x storage cost
        "duration_range": (1, 2),
        "probability": 0.08,
    },
    "subsidy": {
        "description": "Consumers receive cash subsidy",
        "target_role": "consumer",
        "param": "cash",
        "mode": "add",
        "magnitude_range": (500, 2000),  # cash injection
        "duration_range": (1, 1),
        "probability": 0.07,
    },
}


def generate_shock_sequence(
    n_periods: int,
    scenario_id: str,
    seed: int = 42,
) -> list[Shock]:
    """Generate a reproducible shock sequence for a scenario.

    Uses scenario_id + seed to deterministically generate shocks.
    Each period independently rolls for each shock type.

    Parameters
    ----------
    n_periods : int
        Number of trading periods.
    scenario_id : str
        Scenario identifier (e.g., "scenario_001").
    seed : int
        Base random seed.

    Returns
    -------
    list[Shock]
        All shocks, sorted by period.
    """
    # Deterministic seed from scenario_id
    hash_input = f"{scenario_id}_{seed}".encode()
    scenario_seed = int(hashlib.sha256(hash_input).hexdigest()[:8], 16)
    rng = np.random.default_rng(scenario_seed)

    shocks = []
    # Track active shocks to avoid stacking same type
    active_until = {}  # shock_type -> last active period

    for t in range(n_periods):
        for shock_type, spec in SHOCK_TYPES.items():
            # Skip if this shock type is still active
            if shock_type in active_until and t <= active_until[shock_type]:
                continue

            # Roll for shock occurrence
            if rng.random() < spec["probability"]:
                lo, hi = spec["magnitude_range"]
                magnitude = rng.uniform(lo, hi)

                d_lo, d_hi = spec["duration_range"]
                duration = rng.integers(d_lo, d_hi + 1)

                shock = Shock(
                    period=t,
                    shock_type=shock_type,
                    magnitude=round(magnitude, 3),
                    duration=duration,
                    target_role=spec["target_role"],
                    description=spec["description"],
                )
                shocks.append(shock)
                active_until[shock_type] = t + duration - 1

    shocks.sort(key=lambda s: s.period)
    return shocks


def get_active_shocks(shocks: list[Shock], period: int) -> list[Shock]:
    """Return shocks active at a given period."""
    return [
        s for s in shocks
        if s.period <= period < s.period + s.duration
    ]


def apply_shocks(
    agents: dict,
    shocks: list[Shock],
    period: int,
    base_params: dict,
):
    """Apply active shocks to agent parameters.

    First resets agents to base parameters, then applies all active shocks.
    This ensures shocks are additive from baseline, not compounding.

    Parameters
    ----------
    agents : dict[str, AgentState]
        Agent states to modify.
    shocks : list[Shock]
        Full shock sequence.
    period : int
        Current period.
    base_params : dict
        Original agent parameters: {agent_id: {param: value}}.
    """
    # Reset to base parameters
    for agent_id, params in base_params.items():
        agent = agents[agent_id]
        for param, value in params.items():
            setattr(agent, param, value)

    # Apply active shocks
    active = get_active_shocks(shocks, period)
    for shock in active:
        spec = SHOCK_TYPES.get(shock.shock_type, {})
        param = spec.get("param")
        mode = spec.get("mode", "multiply")

        if param is None:
            continue

        for agent in agents.values():
            # Check role filter
            if shock.target_role is not None and agent.role != shock.target_role:
                continue

            current = getattr(agent, param, None)
            if current is None:
                continue

            if mode == "multiply":
                setattr(agent, param, current * shock.magnitude)
            elif mode == "add":
                setattr(agent, param, current + shock.magnitude)


def describe_shocks(shocks: list[Shock], period: int) -> str:
    """Human-readable description of active shocks for agent prompts."""
    active = get_active_shocks(shocks, period)
    if not active:
        return "No unusual market conditions this period."

    lines = ["Current market conditions:"]
    for s in active:
        remaining = s.duration - (period - s.period)
        lines.append(
            f"- {s.description} (magnitude: {s.magnitude:.1%} of normal, "
            f"{remaining} period(s) remaining)"
        )
    return "\n".join(lines)


def generate_scenario_configs(
    n_scenarios: int,
    n_periods: int = 30,
    seed: int = 42,
) -> list[dict]:
    """Generate configurations for multiple market scenarios.

    Varies initial conditions using Latin Hypercube-like sampling:
    - Base price level
    - Production cost spread
    - Demand intensity
    - Initial inventories

    Parameters
    ----------
    n_scenarios : int
        Number of scenarios to generate.
    n_periods : int
        Periods per scenario.
    seed : int
        Random seed.

    Returns
    -------
    list[dict]
        Per-scenario configuration dicts.
    """
    rng = np.random.default_rng(seed)

    configs = []
    for i in range(n_scenarios):
        scenario_id = f"scenario_{i+1:03d}"

        # Vary market parameters
        base_price = rng.uniform(80, 120)
        cost_spread = rng.uniform(0.3, 0.7)  # how much costs vary across producers
        demand_intensity = rng.uniform(0.8, 1.4)  # multiplier on base demand
        initial_inventory_level = rng.choice(["low", "medium", "high"])

        # Generate shock sequence
        shocks = generate_shock_sequence(n_periods, scenario_id, seed)

        configs.append({
            "scenario_id": scenario_id,
            "n_periods": n_periods,
            "base_price": round(base_price, 2),
            "cost_spread": round(cost_spread, 3),
            "demand_intensity": round(demand_intensity, 3),
            "initial_inventory_level": initial_inventory_level,
            "n_shocks": len(shocks),
            "shocks": shocks,
        })

    return configs
