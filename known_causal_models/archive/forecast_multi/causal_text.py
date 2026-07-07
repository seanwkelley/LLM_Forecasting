"""
Causal Text — Convert adjacency matrices to natural language descriptions.

Used by L2 and L3 information levels to communicate causal structure
to LLM forecasters in human-readable form.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from causal_discovery.ground_truth import (
    MARKET_VARIABLES,
    MARKET_VAR_INDEX,
    CONFLICT_VARIABLES,
    CONFLICT_VAR_INDEX,
    get_market_ground_truth,
    get_conflict_ground_truth,
)


def adjacency_to_text(
    matrix: np.ndarray,
    variables: list[str],
    target: str,
    domain: str = "market",
) -> str:
    """Convert an adjacency matrix to a structured natural language description.

    Groups edges by functional role rather than listing raw edges.
    """
    if domain == "market":
        return _market_graph_text(matrix, variables, target)
    else:
        return _conflict_graph_text(matrix, variables, target)


def _market_graph_text(
    matrix: np.ndarray, variables: list[str], target: str,
) -> str:
    """Market-specific causal graph description."""
    idx = {v: i for i, v in enumerate(variables)}

    # Collect edges by category
    edges = []
    for i in range(len(variables)):
        for j in range(len(variables)):
            if matrix[i, j] == 1:
                edges.append((variables[i], variables[j]))

    lines = [
        "## Causal Structure",
        "",
        "The following causal relationships govern this market system:",
        "",
        "**Shock effects (exogenous):**",
    ]

    shock_targets = [dst for src, dst in edges if src == "shock"]
    for dst in shock_targets:
        desc = _market_edge_desc("shock", dst)
        lines.append(f"- shock -> {dst} ({desc})")

    lines.append("")
    lines.append("**How orders form (decision inputs):**")
    order_sources = [src for src, dst in edges if dst == "agent_orders" and src != "shock"]
    for src in order_sources:
        desc = _market_edge_desc(src, "agent_orders")
        lines.append(f"- {src} -> agent_orders ({desc})")

    lines.append("")
    lines.append("**Market clearing mechanism:**")
    lines.append("- agent_orders -> clearing_price (supply-demand intersection determines price)")
    lines.append("- agent_orders -> volume (matched quantity of buy/sell orders)")

    lines.append("")
    lines.append("**Feedback loops (next period):**")
    feedback = [(src, dst) for src, dst in edges
                if src == "clearing_price" and dst in ("cash", "inventory", "price_history")]
    for src, dst in feedback:
        desc = _market_edge_desc(src, dst)
        lines.append(f"- {src} -> {dst} ({desc})")

    lines.append("")
    lines.append("**Period costs and production:**")
    cost_edges = [(src, dst) for src, dst in edges
                  if dst in ("cash", "inventory") and src not in ("shock", "clearing_price")]
    for src, dst in cost_edges:
        desc = _market_edge_desc(src, dst)
        lines.append(f"- {src} -> {dst} ({desc})")

    lines.append("")
    lines.append("**Key causal path to clearing_price:**")
    lines.append("[shock, parameters] -> agent_orders -> clearing_price")
    lines.append("")
    lines.append(
        "**Important:** fundamental_price does NOT cause clearing_price. "
        "They share common causes (production_cost, demand_value) but "
        "fundamental_price is a diagnostic output, not an input to the market."
    )

    return "\n".join(lines)


def _market_edge_desc(src: str, dst: str) -> str:
    """Human-readable description of a market causal edge."""
    descs = {
        ("shock", "production_cost"): "supply disruptions raise costs; cost reductions lower them",
        ("shock", "demand_per_period"): "demand surges/drops change quantity demanded",
        ("shock", "storage_cost"): "storage crises increase holding costs",
        ("shock", "cash"): "subsidies inject cash to agents",
        ("production_cost", "agent_orders"): "sets price floor for producers",
        ("demand_value", "agent_orders"): "sets price ceiling for consumers",
        ("demand_per_period", "agent_orders"): "determines consumer quantity targets",
        ("cash", "agent_orders"): "constrains maximum buy quantity",
        ("inventory", "agent_orders"): "constrains maximum sell quantity",
        ("price_history", "agent_orders"): "trend signal influences speculator behavior",
        ("clearing_price", "cash"): "buyers spend cash, sellers earn cash",
        ("clearing_price", "inventory"): "buyers gain inventory, sellers lose inventory",
        ("clearing_price", "price_history"): "recorded for next period's decisions",
        ("storage_cost", "cash"): "holding costs drain cash each period",
        ("production_cost", "cash"): "producers pay production costs",
        ("production_cost", "inventory"): "producers create inventory",
        ("demand_per_period", "inventory"): "consumers consume inventory",
        ("demand_value", "cash"): "consumers gain utility value from consumption",
        ("production_cost", "fundamental_price"): "supply curve component",
        ("demand_value", "fundamental_price"): "demand curve component",
    }
    return descs.get((src, dst), f"{src} affects {dst}")


def _conflict_graph_text(
    matrix: np.ndarray, variables: list[str], target: str,
) -> str:
    """Conflict-specific causal graph description."""
    idx = {v: i for i, v in enumerate(variables)}

    edges = []
    for i in range(len(variables)):
        for j in range(len(variables)):
            if matrix[i, j] == 1:
                edges.append((variables[i], variables[j]))

    lines = [
        "## Causal Structure",
        "",
        "The following causal relationships govern this conflict system:",
        "",
        "**Shock effects (exogenous events):**",
    ]

    shock_targets = [dst for src, dst in edges if src == "shock"]
    for dst in shock_targets:
        desc = _conflict_edge_desc("shock", dst)
        lines.append(f"- shock -> {dst} ({desc})")

    lines.append("")
    lines.append("**Agent decision process:**")
    rec_sources = [src for src, dst in edges if dst == "agent_recommendation"]
    for src in rec_sources:
        desc = _conflict_edge_desc(src, "agent_recommendation")
        lines.append(f"- {src} -> agent_recommendation ({desc})")

    lines.append("")
    lines.append("**Action aggregation:**")
    lines.append("- agent_recommendation -> faction_action (weighted by role importance)")

    lines.append("")
    lines.append("**Escalation computation:**")
    lines.append(
        "- faction_action -> escalation_index "
        "(both factions' actions determine escalation with interaction modifiers)"
    )

    lines.append("")
    lines.append("**State updates from escalation:**")
    ei_targets = [dst for src, dst in edges
                  if src == "escalation_index" and dst != "agent_recommendation"]
    for dst in ei_targets:
        desc = _conflict_edge_desc("escalation_index", dst)
        lines.append(f"- escalation_index -> {dst} ({desc})")

    lines.append("")
    lines.append("**State updates from faction actions:**")
    action_targets = [dst for src, dst in edges
                      if src == "faction_action" and dst != "escalation_index"]
    for dst in action_targets:
        desc = _conflict_edge_desc("faction_action", dst)
        lines.append(f"- faction_action -> {dst} ({desc})")

    lines.append("")
    lines.append("**Cross-variable dynamics:**")
    cross_edges = [(src, dst) for src, dst in edges
                   if src not in ("shock", "escalation_index", "faction_action",
                                  "agent_recommendation", "hawk_score")
                   and dst not in ("agent_recommendation", "faction_action")]
    for src, dst in cross_edges:
        desc = _conflict_edge_desc(src, dst)
        lines.append(f"- {src} -> {dst} ({desc})")

    lines.append("")
    lines.append("**Key feedback loops:**")
    lines.append("- escalation_index -> agent_recommendation -> faction_action -> escalation_index")
    lines.append("- resources -> agent_recommendation -> faction_action -> resources")

    return "\n".join(lines)


def _conflict_edge_desc(src: str, dst: str) -> str:
    """Human-readable description of a conflict causal edge."""
    descs = {
        ("shock", "escalation_index"): "border incidents escalate; peace initiatives de-escalate",
        ("shock", "resources"): "economic crises deplete resources",
        ("shock", "military_balance"): "military incidents shift balance",
        ("shock", "sanctions_level"): "international pressure changes sanctions",
        ("hawk_score", "agent_recommendation"): "hawks push escalation; doves push de-escalation",
        ("escalation_index", "agent_recommendation"): "agents respond to current escalation level",
        ("resources", "agent_recommendation"): "low resources constrain aggressive actions",
        ("escalation_index", "gdp"): "high escalation damages economic output",
        ("escalation_index", "political_stability"): "high escalation reduces stability",
        ("escalation_index", "sanctions_level"): "escalation triggers international sanctions",
        ("escalation_index", "international_support"): "escalation increases support for defender",
        ("faction_action", "military_strength"): "military actions build or deplete strength",
        ("faction_action", "territory_controlled"): "offensive actions can shift territory",
        ("faction_action", "resources"): "action costs deplete resources",
        ("faction_action", "sanctions_level"): "escalatory actions increase sanctions on aggressor",
        ("gdp", "resources"): "GDP drives resource regeneration",
        ("sanctions_level", "gdp"): "sanctions damage economic output",
        ("military_strength", "military_balance"): "strength difference determines balance",
        ("military_balance", "territory_controlled"): "military advantage enables territory change",
    }
    return descs.get((src, dst), f"{src} affects {dst}")


def get_graph_text(domain: str) -> str:
    """Get the full natural language causal graph description for a domain."""
    if domain == "market":
        matrix = get_market_ground_truth()
        variables = MARKET_VARIABLES
        target = "clearing_price"
    elif domain == "conflict":
        matrix = get_conflict_ground_truth()
        variables = CONFLICT_VARIABLES
        target = "escalation_index"
    else:
        raise ValueError(f"Unknown domain: {domain}")

    return adjacency_to_text(matrix, variables, target, domain)
