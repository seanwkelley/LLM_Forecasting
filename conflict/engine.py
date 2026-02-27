"""
Conflict Engine -- Deterministic escalation mechanism for wargame simulation.

No LLM involvement. Actions in, escalation index out.

Mechanism:
1. Each faction submits one action per period (aggregated from agent recommendations).
2. Escalation index is computed from the action pair + interaction effects + momentum.
3. Faction states (GDP, military, stability, resources) are updated mechanistically.
4. The escalation index (0-10 scale) is the "price" analog for forecasting.

Each period is an independent action round -- one escalation index per period,
one action per faction per period.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Optional


# =============================================================================
# Action Space
# =============================================================================

ACTION_SPACE = {
    # De-escalatory (negative delta)
    "peace_talks":        {"escalation_delta": -0.8, "cost": 0.1, "category": "diplomatic"},
    "ceasefire_offer":    {"escalation_delta": -0.6, "cost": 0.05, "category": "diplomatic"},
    "diplomatic_summit":  {"escalation_delta": -0.5, "cost": 0.15, "category": "diplomatic"},
    "humanitarian_aid":   {"escalation_delta": -0.3, "cost": 0.5, "category": "diplomatic"},
    "trade_agreement":    {"escalation_delta": -0.4, "cost": 0.1, "category": "economic"},
    "troop_withdrawal":   {"escalation_delta": -1.0, "cost": 0.2, "category": "military"},
    "backchannel_talks":  {"escalation_delta": -0.1, "cost": 0.05, "category": "diplomatic"},

    # Neutral / positioning
    "intelligence_gathering": {"escalation_delta": 0.1, "cost": 0.3, "category": "intelligence"},
    "economic_sanctions":     {"escalation_delta": 0.3, "cost": 0.2, "category": "economic"},
    "propaganda_campaign":    {"escalation_delta": 0.2, "cost": 0.1, "category": "information"},
    "military_buildup":       {"escalation_delta": 0.4, "cost": 1.0, "category": "military"},

    # Escalatory (positive delta)
    "cyber_attack":       {"escalation_delta": 0.6, "cost": 0.5, "category": "covert"},
    "proxy_support":      {"escalation_delta": 0.5, "cost": 1.0, "category": "covert"},
    "naval_blockade":     {"escalation_delta": 0.8, "cost": 1.5, "category": "military"},
    "border_incursion":   {"escalation_delta": 1.2, "cost": 2.0, "category": "military"},
    "limited_strike":     {"escalation_delta": 1.5, "cost": 3.0, "category": "military"},
    "full_scale_attack":  {"escalation_delta": 2.5, "cost": 5.0, "category": "military"},
}

ACTION_NAMES = sorted(ACTION_SPACE.keys())


@dataclass
class Action:
    """A single faction action for one period."""
    faction_id: str
    action_name: str
    escalation_delta: float = 0.0
    cost: float = 0.0
    category: str = ""
    reasoning: str = ""
    continuous_delta: Optional[float] = None  # preserves weighted avg before snapping

    @classmethod
    def from_name(cls, faction_id: str, action_name: str, reasoning: str = "") -> "Action":
        """Create an Action from a valid action name."""
        spec = ACTION_SPACE.get(action_name)
        if spec is None:
            # Default to intelligence_gathering if invalid
            action_name = "intelligence_gathering"
            spec = ACTION_SPACE[action_name]
        return cls(
            faction_id=faction_id,
            action_name=action_name,
            escalation_delta=spec["escalation_delta"],
            cost=spec["cost"],
            category=spec["category"],
            reasoning=reasoning,
        )


# =============================================================================
# State Model
# =============================================================================

@dataclass
class FactionState:
    """Per-faction state variables."""
    faction_id: str
    gdp: float = 1.0                   # economic health (0-2, starts at 1.0)
    military_strength: float = 0.5      # 0-1
    political_stability: float = 0.8    # 0-1
    resources: float = 10.0             # budget for actions

    def copy(self) -> "FactionState":
        return copy.copy(self)


@dataclass
class ConflictState:
    """Full simulation state -- tracks both factions + global escalation."""

    # Per-faction state
    factions: dict[str, FactionState] = field(default_factory=dict)

    # Global state (the "price" analog)
    escalation_index: float = 5.0       # 0-10 scale
    escalation_history: list[float] = field(default_factory=list)

    # Additional global state variables
    military_balance: float = 0.0       # -1 (novaris dominant) to +1 (tethys dominant)
    territory_controlled: float = 0.05  # fraction controlled by novaris (0-1)
    sanctions_level: float = 0.0        # 0-1
    international_support: float = 0.5  # 0-1 (for tethys)

    # History
    action_history: list[list[Action]] = field(default_factory=list)

    # Current period
    period: int = 0


# =============================================================================
# Escalation Computation (Deterministic)
# =============================================================================

def _effective_delta(action: Action) -> float:
    """Return continuous delta if available, else snapped escalation_delta."""
    return action.continuous_delta if action.continuous_delta is not None else action.escalation_delta


def compute_escalation(
    state: ConflictState,
    novaris_action: Action,
    tethys_action: Action,
) -> float:
    """Compute new escalation index from faction actions.

    Formula:
    EI_new = EI_old + (novaris_delta + tethys_delta) * interaction_modifier + momentum

    Where:
    - novaris_delta, tethys_delta = continuous delta from aggregation (or snapped delta)
    - interaction_modifier accounts for action-pair interactions
    - momentum = mean-reverting pressure at extremes
    """
    nov_d = _effective_delta(novaris_action)
    teth_d = _effective_delta(tethys_action)
    base_delta = nov_d + teth_d

    # Interaction effects
    if nov_d > 0 and teth_d > 0:
        interaction = 1.2  # mutual escalation amplifies
    elif nov_d < 0 and teth_d < 0:
        interaction = 1.3  # mutual de-escalation amplifies
    else:
        interaction = 0.8  # asymmetric dampens

    # Mean reversion at extremes
    momentum = -0.06 * (state.escalation_index - 5.0)

    new_ei = state.escalation_index + base_delta * interaction + momentum
    return max(0.0, min(10.0, new_ei))


# =============================================================================
# Faction State Updates
# =============================================================================

def update_faction_states(
    state: ConflictState,
    novaris_action: Action,
    tethys_action: Action,
    new_ei: float,
):
    """Update faction-level and global state variables after actions resolve.

    Modifies state in place.
    """
    nov = state.factions["novaris"]
    teth = state.factions["tethys"]

    # --- Resource costs ---
    nov.resources = max(0.0, nov.resources - novaris_action.cost)
    teth.resources = max(0.0, teth.resources - tethys_action.cost)

    # --- Resource regeneration (GDP-dependent) ---
    nov.resources = min(15.0, nov.resources + 0.5 * nov.gdp)
    teth.resources = min(15.0, teth.resources + 0.4 * teth.gdp)

    # --- GDP effects ---
    # High escalation damages both economies; sanctions hurt novaris more
    ei_damage = max(0.0, (new_ei - 5.0) * 0.01)
    nov.gdp = max(0.2, nov.gdp - ei_damage - state.sanctions_level * 0.02)
    teth.gdp = max(0.2, teth.gdp - ei_damage * 0.8)  # defender takes less economic damage

    # GDP recovery in low escalation
    if new_ei < 4.0:
        nov.gdp = min(1.5, nov.gdp + 0.01)
        teth.gdp = min(1.5, teth.gdp + 0.015)

    # --- Military strength ---
    # Military actions build strength; combat depletes it
    if novaris_action.category == "military":
        if novaris_action.escalation_delta > 0.5:
            # Offensive action: costs strength
            nov.military_strength = max(0.1, nov.military_strength - 0.03)
        else:
            # Buildup: gains strength
            nov.military_strength = min(1.0, nov.military_strength + 0.04)

    if tethys_action.category == "military":
        if tethys_action.escalation_delta > 0.5:
            teth.military_strength = max(0.1, teth.military_strength - 0.03)
        else:
            teth.military_strength = min(1.0, teth.military_strength + 0.04)

    # --- Political stability ---
    # High escalation costs stability; peace efforts restore it
    if new_ei > 7.0:
        nov.political_stability = max(0.1, nov.political_stability - 0.02)
        teth.political_stability = max(0.1, teth.political_stability - 0.01)
    elif new_ei < 3.0:
        nov.political_stability = min(1.0, nov.political_stability + 0.01)
        teth.political_stability = min(1.0, teth.political_stability + 0.01)

    # --- Military balance ---
    # Shifts toward whichever side has higher military strength and is more active
    strength_diff = nov.military_strength - teth.military_strength
    state.military_balance = max(-1.0, min(1.0,
        state.military_balance + strength_diff * 0.05
    ))

    # --- Territory controlled ---
    # Novaris gains territory through escalatory military actions when dominant
    if novaris_action.category == "military" and novaris_action.escalation_delta > 0.5:
        if state.military_balance < -0.1:  # novaris has advantage (negative = novaris dominant)
            state.territory_controlled = min(1.0, state.territory_controlled + 0.02)
    # Territory recovery when Tethys is militarily active
    if tethys_action.category == "military" and tethys_action.escalation_delta > 0.5:
        if state.military_balance > 0.1:  # tethys has advantage
            state.territory_controlled = max(0.0, state.territory_controlled - 0.01)

    # --- Sanctions level ---
    if novaris_action.escalation_delta > 0.5:
        state.sanctions_level = min(1.0, state.sanctions_level + 0.03)
    if novaris_action.escalation_delta < -0.3:
        state.sanctions_level = max(0.0, state.sanctions_level - 0.02)

    # --- International support for Tethys ---
    if new_ei > 6.0:
        state.international_support = min(1.0, state.international_support + 0.02)
    elif new_ei < 3.0:
        # Low escalation: support fades (less urgency)
        state.international_support = max(0.2, state.international_support - 0.01)


# =============================================================================
# Action Aggregation
# =============================================================================

def get_agent_weight(agent_role: str, action_category: str) -> float:
    """Weight an agent's recommendation based on their role and the action category.

    Military leaders have more influence on military actions, etc.
    """
    role_weights = {
        "military_chief":    {"military": 2.0, "covert": 1.5, "diplomatic": 0.5, "economic": 0.5, "intelligence": 1.0, "information": 0.8},
        "defense_minister":  {"military": 1.5, "covert": 1.0, "diplomatic": 1.0, "economic": 1.0, "intelligence": 1.0, "information": 1.0},
        "economic_advisor":  {"military": 0.5, "covert": 0.5, "diplomatic": 1.0, "economic": 2.0, "intelligence": 0.8, "information": 0.8},
        "intelligence_chief":{"military": 0.8, "covert": 2.0, "diplomatic": 0.8, "economic": 0.5, "intelligence": 2.0, "information": 1.5},
        "president":         {"military": 1.5, "covert": 1.0, "diplomatic": 2.0, "economic": 1.5, "intelligence": 1.0, "information": 1.5},
        "military_commander":{"military": 2.0, "covert": 1.0, "diplomatic": 0.5, "economic": 0.5, "intelligence": 1.0, "information": 0.5},
        "foreign_minister":  {"military": 0.5, "covert": 0.5, "diplomatic": 2.0, "economic": 1.5, "intelligence": 0.8, "information": 1.5},
    }
    weights = role_weights.get(agent_role, {})
    return weights.get(action_category, 1.0)


def closest_action(target_delta: float, faction_id: str = "") -> Action:
    """Find the action with escalation_delta closest to target_delta."""
    best_name = min(
        ACTION_SPACE.keys(),
        key=lambda name: abs(ACTION_SPACE[name]["escalation_delta"] - target_delta),
    )
    return Action.from_name(faction_id, best_name)


def aggregate_faction_action(
    recommendations: list[dict],
    faction_id: str,
) -> Action:
    """Aggregate individual agent recommendations into a single faction action.

    Method: Weighted average of escalation deltas, snap to nearest action.

    Parameters
    ----------
    recommendations : list[dict]
        Each dict has keys: agent_id, agent_role, action, reasoning.
    faction_id : str
        "novaris" or "tethys".

    Returns
    -------
    The faction's aggregated Action.
    """
    if not recommendations:
        return Action.from_name(faction_id, "intelligence_gathering", "No recommendations")

    total_weight = 0.0
    weighted_delta = 0.0
    all_reasoning = []

    for rec in recommendations:
        action_name = rec["action"]
        spec = ACTION_SPACE.get(action_name)
        if spec is None:
            continue

        weight = get_agent_weight(rec.get("agent_role", ""), spec["category"])
        weighted_delta += spec["escalation_delta"] * weight
        total_weight += weight
        all_reasoning.append(f"{rec['agent_id']}: {rec.get('reasoning', '')[:80]}")

    if total_weight == 0:
        return Action.from_name(faction_id, "intelligence_gathering", "Fallback")

    avg_delta = weighted_delta / total_weight
    action = closest_action(avg_delta, faction_id)
    action.continuous_delta = avg_delta  # preserve the continuous value
    action.reasoning = " | ".join(all_reasoning)
    return action


# =============================================================================
# Period Execution
# =============================================================================

def run_period(
    state: ConflictState,
    novaris_action: Action,
    tethys_action: Action,
) -> dict:
    """Execute one conflict period. Analog to market's run_period.

    Parameters
    ----------
    state : ConflictState
        Current state (modified in place).
    novaris_action : Action
        Novaris faction's chosen action.
    tethys_action : Action
        Tethys faction's chosen action.

    Returns
    -------
    dict with period results.
    """
    # 1. Compute new escalation index
    new_ei = compute_escalation(state, novaris_action, tethys_action)

    # 2. Update faction states
    update_faction_states(state, novaris_action, tethys_action, new_ei)

    # 3. Record history
    state.escalation_history.append(new_ei)
    state.escalation_index = new_ei
    state.action_history.append([novaris_action, tethys_action])
    state.period += 1

    return {
        "period": state.period,
        "escalation_index": round(new_ei, 4),
        "novaris_action": novaris_action.action_name,
        "tethys_action": tethys_action.action_name,
        "military_balance": round(state.military_balance, 4),
        "territory_controlled": round(state.territory_controlled, 4),
        "sanctions_level": round(state.sanctions_level, 4),
        "international_support": round(state.international_support, 4),
        "novaris_resources": round(state.factions["novaris"].resources, 2),
        "tethys_resources": round(state.factions["tethys"].resources, 2),
    }


def initialize_state(scenario_config: dict) -> ConflictState:
    """Create initial ConflictState from a scenario configuration.

    Parameters
    ----------
    scenario_config : dict
        Keys: starting_escalation, military_balance, novaris_resources,
        tethys_resources, starting_territory, sanctions_level.
    """
    novaris = FactionState(
        faction_id="novaris",
        gdp=scenario_config.get("novaris_gdp", 1.0),
        military_strength=scenario_config.get("novaris_military", 0.6),
        political_stability=scenario_config.get("novaris_stability", 0.7),
        resources=scenario_config.get("novaris_resources", 10.0),
    )

    tethys = FactionState(
        faction_id="tethys",
        gdp=scenario_config.get("tethys_gdp", 0.8),
        military_strength=scenario_config.get("tethys_military", 0.45),
        political_stability=scenario_config.get("tethys_stability", 0.85),
        resources=scenario_config.get("tethys_resources", 7.0),
    )

    state = ConflictState(
        factions={"novaris": novaris, "tethys": tethys},
        escalation_index=scenario_config.get("starting_escalation", 5.0),
        military_balance=scenario_config.get("military_balance", -0.1),
        territory_controlled=scenario_config.get("starting_territory", 0.05),
        sanctions_level=scenario_config.get("sanctions_level", 0.1),
        international_support=scenario_config.get("international_support", 0.5),
    )

    return state
