"""
Exogenous Shock Generator for Conflict Simulation.

Generates pre-determined shock sequences that create escalation variation
across scenarios. Shocks modify state parameters (escalation, resources,
military balance, etc.) rather than directly setting outcomes.

Each scenario gets a unique shock sequence (seeded for reproducibility).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Optional

import numpy as np

from conflict.engine import ConflictState


@dataclass
class Shock:
    """A single exogenous shock applied at a specific period."""
    period: int
    shock_type: str
    magnitude: float
    duration: int = 1
    target_faction: Optional[str] = None  # None = affects global state
    description: str = ""


# Shock type definitions
SHOCK_TYPES = {
    "border_incident": {
        "description": "A military incident at the border raises tensions",
        "param": "escalation_index",
        "mode": "add",
        "magnitude_range": (0.5, 1.5),
        "duration_range": (1, 1),
        "probability": 0.12,
        "target_faction": None,
    },
    "diplomatic_crisis": {
        "description": "A diplomatic breakdown increases escalation",
        "param": "escalation_index",
        "mode": "add",
        "magnitude_range": (0.3, 0.8),
        "duration_range": (1, 2),
        "probability": 0.10,
        "target_faction": None,
    },
    "peace_initiative": {
        "description": "International peace initiative reduces tensions",
        "param": "escalation_index",
        "mode": "add",
        "magnitude_range": (-1.0, -0.3),
        "duration_range": (1, 2),
        "probability": 0.08,
        "target_faction": None,
    },
    "economic_crisis": {
        "description": "Economic crisis reduces available resources",
        "param": "resources",
        "mode": "multiply",
        "magnitude_range": (0.6, 0.8),
        "duration_range": (1, 3),
        "probability": 0.10,
        "target_faction": "novaris",
    },
    "military_incident": {
        "description": "A military incident shifts the balance of power",
        "param": "military_balance",
        "mode": "add",
        "magnitude_range": (-0.15, 0.15),
        "duration_range": (1, 1),
        "probability": 0.10,
        "target_faction": None,
    },
    "international_pressure": {
        "description": "International community increases sanctions pressure",
        "param": "sanctions_level",
        "mode": "add",
        "magnitude_range": (0.1, 0.3),
        "duration_range": (1, 3),
        "probability": 0.08,
        "target_faction": None,
    },
}


def generate_shock_sequence(
    n_periods: int,
    scenario_id: str,
    seed: int = 42,
) -> list[Shock]:
    """Generate a reproducible shock sequence for a scenario.

    Uses scenario_id + seed to deterministically generate shocks.
    """
    hash_input = f"{scenario_id}_{seed}".encode()
    scenario_seed = int(hashlib.sha256(hash_input).hexdigest()[:8], 16)
    rng = np.random.default_rng(scenario_seed)

    shocks = []
    active_until: dict[str, int] = {}

    for t in range(n_periods):
        for shock_type, spec in SHOCK_TYPES.items():
            if shock_type in active_until and t <= active_until[shock_type]:
                continue

            if rng.random() < spec["probability"]:
                lo, hi = spec["magnitude_range"]
                magnitude = rng.uniform(lo, hi)

                d_lo, d_hi = spec["duration_range"]
                duration = int(rng.integers(d_lo, d_hi + 1))

                shock = Shock(
                    period=t,
                    shock_type=shock_type,
                    magnitude=round(magnitude, 3),
                    duration=duration,
                    target_faction=spec["target_faction"],
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


def apply_shocks(state: ConflictState, shocks: list[Shock], period: int):
    """Apply active shocks directly to conflict state.

    Unlike the market engine (which resets to base_params first), the conflict
    engine applies shocks as direct modifications to the current state, since
    conflict state variables accumulate over time rather than resetting.
    """
    active = get_active_shocks(shocks, period)

    for shock in active:
        # Only apply on the shock's start period to avoid re-applying each period
        if shock.period != period:
            continue

        spec = SHOCK_TYPES.get(shock.shock_type, {})
        param = spec.get("param")
        mode = spec.get("mode", "add")

        if param is None:
            continue

        if param == "escalation_index":
            if mode == "add":
                state.escalation_index = max(0.0, min(10.0,
                    state.escalation_index + shock.magnitude))

        elif param == "military_balance":
            if mode == "add":
                state.military_balance = max(-1.0, min(1.0,
                    state.military_balance + shock.magnitude))

        elif param == "sanctions_level":
            if mode == "add":
                state.sanctions_level = max(0.0, min(1.0,
                    state.sanctions_level + shock.magnitude))

        elif param == "resources":
            if shock.target_faction and shock.target_faction in state.factions:
                faction = state.factions[shock.target_faction]
                if mode == "multiply":
                    faction.resources = max(0.0, faction.resources * shock.magnitude)
                elif mode == "add":
                    faction.resources = max(0.0, faction.resources + shock.magnitude)


def describe_shocks(shocks: list[Shock], period: int) -> str:
    """Human-readable description of active shocks for agent prompts."""
    active = get_active_shocks(shocks, period)
    if not active:
        return ""

    lines = ["Current special conditions:"]
    for s in active:
        remaining = s.duration - (period - s.period)
        lines.append(f"- {s.description} (magnitude: {s.magnitude:+.2f}, "
                      f"{remaining} period(s) remaining)")
    return "\n".join(lines)


def generate_scenario_configs(
    n_scenarios: int,
    n_periods: int = 30,
    seed: int = 42,
) -> list[dict]:
    """Generate configurations for multiple conflict scenarios.

    Varies initial conditions:
    - Starting escalation (3-7)
    - Military balance (-0.3 to 0.3)
    - Novaris resources (high/medium/low)
    - Starting territory (0-15%)
    - Faction GDP and military strength
    """
    rng = np.random.default_rng(seed)

    configs = []
    for i in range(n_scenarios):
        scenario_id = f"scenario_{i+1:03d}"

        starting_escalation = round(float(rng.uniform(3.0, 7.0)), 2)
        military_balance = round(float(rng.uniform(-0.3, 0.3)), 3)
        starting_territory = round(float(rng.uniform(0.0, 0.15)), 3)
        novaris_resources = round(float(rng.uniform(7.0, 13.0)), 1)
        tethys_resources = round(float(rng.uniform(5.0, 9.0)), 1)
        novaris_military = round(float(rng.uniform(0.45, 0.75)), 3)
        tethys_military = round(float(rng.uniform(0.35, 0.55)), 3)
        sanctions_level = round(float(rng.uniform(0.0, 0.2)), 3)

        shocks = generate_shock_sequence(n_periods, scenario_id, seed)

        configs.append({
            "scenario_id": scenario_id,
            "n_periods": n_periods,
            "starting_escalation": starting_escalation,
            "military_balance": military_balance,
            "starting_territory": starting_territory,
            "novaris_resources": novaris_resources,
            "tethys_resources": tethys_resources,
            "novaris_military": novaris_military,
            "tethys_military": tethys_military,
            "novaris_gdp": round(float(rng.uniform(0.8, 1.2)), 2),
            "tethys_gdp": round(float(rng.uniform(0.6, 1.0)), 2),
            "novaris_stability": round(float(rng.uniform(0.6, 0.85)), 2),
            "tethys_stability": round(float(rng.uniform(0.7, 0.95)), 2),
            "sanctions_level": sanctions_level,
            "international_support": round(float(rng.uniform(0.3, 0.7)), 2),
            "n_shocks": len(shocks),
            "shocks": shocks,
        })

    return configs
