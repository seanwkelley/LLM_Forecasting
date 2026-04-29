"""
Ground Truth Causal Graphs — Adjacency matrices for market and conflict engines.

Defines the variable set (nodes) and causal edges for each engine based on
engine code analysis. Used to score causal modeler agents' recovered graphs.

Scoring uses Structural Hamming Distance (SHD) on cyclic directed graphs.
Both engines have feedback loops, so no DAG assumption is made.
SHD counts extra edges, missing edges, and reversed edges (each as 1 error).
"""

from __future__ import annotations

import numpy as np


# =============================================================================
# Market Engine Ground Truth
# =============================================================================

# Variable set (nodes) — ordered for adjacency matrix indexing.
# Granularity: coarse enough for LLM agents to handle in 30 interventions,
# fine enough to capture the key causal relationships.

MARKET_VARIABLES = [
    "shock",              # 0: exogenous shock (supply_disruption, demand_surge, etc.)
    "production_cost",    # 1: producer cost parameter (affected by shocks)
    "demand_per_period",  # 2: consumer demand parameter (affected by shocks)
    "demand_value",       # 3: consumer willingness-to-pay
    "storage_cost",       # 4: per-unit holding cost (affected by storage_crisis)
    "cash",               # 5: agent cash holdings
    "inventory",          # 6: agent inventory holdings
    "price_history",      # 7: recent price trajectory (observed by agents)
    "agent_orders",       # 8: submitted limit prices and quantities
    "clearing_price",     # 9: market clearing price (THE outcome variable)
    "volume",             # 10: total units traded
    "fundamental_price",  # 11: diagnostic — NOT causal (common-cause confound)
]

MARKET_N = len(MARKET_VARIABLES)
MARKET_VAR_INDEX = {v: i for i, v in enumerate(MARKET_VARIABLES)}


def get_market_ground_truth() -> np.ndarray:
    """Return the ground truth adjacency matrix for the market engine.

    Matrix[i, j] = 1 means variable i causes variable j.
    Cyclic edges are allowed.

    Derived from market/engine.py analysis:
    - clear_market(): orders → clearing_price (deterministic)
    - validate_order(): cash/inventory constrain orders
    - apply_fills(): clearing_price → cash/inventory (feedback)
    - apply_period_costs(): storage_cost drains cash; production/consumption
    - apply_shocks(): shock → production_cost, demand_per_period, storage_cost, cash
    - compute_fundamental_price(): production_cost + demand_value → fundamental (output only)
    """
    M = np.zeros((MARKET_N, MARKET_N), dtype=int)
    idx = MARKET_VAR_INDEX

    # --- Shock effects ---
    # shock → production_cost (supply_disruption, cost_reduction)
    M[idx["shock"], idx["production_cost"]] = 1
    # shock → demand_per_period (demand_surge, demand_drop)
    M[idx["shock"], idx["demand_per_period"]] = 1
    # shock → storage_cost (storage_crisis)
    M[idx["shock"], idx["storage_cost"]] = 1
    # shock → cash (subsidy)
    M[idx["shock"], idx["cash"]] = 1

    # --- Trait → order edges ---
    # production_cost → agent_orders (price floor for producers)
    M[idx["production_cost"], idx["agent_orders"]] = 1
    # demand_value → agent_orders (price ceiling for consumers)
    M[idx["demand_value"], idx["agent_orders"]] = 1
    # demand_per_period → agent_orders (quantity target for consumers)
    M[idx["demand_per_period"], idx["agent_orders"]] = 1
    # NOTE: storage_cost → agent_orders was previously asserted as "indirectly
    # affects urgency to sell" but was removed after audit (2026-04-08): no
    # agent rule references storage_cost, and the only path is the indirect
    # chain storage_cost → cash → agent_orders (already represented via those
    # two edges). Leaving this as a direct edge produced a systematic false
    # negative across all LLM models in prior causal discovery runs.

    # --- State → order edges ---
    # cash → agent_orders (constrains buy quantity via validate_order)
    M[idx["cash"], idx["agent_orders"]] = 1
    # inventory → agent_orders (constrains sell quantity via validate_order)
    M[idx["inventory"], idx["agent_orders"]] = 1
    # price_history → agent_orders (trend signal, esp. speculators)
    M[idx["price_history"], idx["agent_orders"]] = 1

    # --- Clearing mechanism (deterministic) ---
    # agent_orders → clearing_price
    M[idx["agent_orders"], idx["clearing_price"]] = 1
    # agent_orders → volume
    M[idx["agent_orders"], idx["volume"]] = 1

    # --- Feedback loop ---
    # clearing_price → cash (via apply_fills: buyers spend, sellers earn)
    M[idx["clearing_price"], idx["cash"]] = 1
    # clearing_price → inventory (via apply_fills: buyers gain, sellers lose)
    M[idx["clearing_price"], idx["inventory"]] = 1
    # clearing_price → price_history (recorded for next period)
    M[idx["clearing_price"], idx["price_history"]] = 1

    # --- Period costs ---
    # storage_cost → cash (apply_period_costs: storage drains cash)
    M[idx["storage_cost"], idx["cash"]] = 1
    # production_cost → cash (producers pay to produce)
    M[idx["production_cost"], idx["cash"]] = 1
    # production_cost → inventory (producers create inventory at cost)
    M[idx["production_cost"], idx["inventory"]] = 1
    # demand_per_period → inventory (consumers consume inventory)
    M[idx["demand_per_period"], idx["inventory"]] = 1
    # demand_value → cash (consumers gain cash from consumption utility)
    M[idx["demand_value"], idx["cash"]] = 1

    # --- Diagnostic variable (NOT causal) ---
    # production_cost → fundamental_price (computed from supply curve)
    M[idx["production_cost"], idx["fundamental_price"]] = 1
    # demand_value → fundamental_price (computed from demand curve)
    M[idx["demand_value"], idx["fundamental_price"]] = 1

    # NOTE: fundamental_price → clearing_price is ABSENT.
    # This is the critical confound — they share common causes but
    # fundamental_price does not cause clearing_price.

    return M


# =============================================================================
# Conflict Engine Ground Truth
# =============================================================================

CONFLICT_VARIABLES = [
    "shock",                # 0: exogenous event (border_incident, peace_initiative, etc.)
    "hawk_score",           # 1: agent hawk/dove disposition (prompt-mediated)
    "escalation_index",     # 2: global escalation level (THE outcome variable)
    "resources",            # 3: faction resource budget
    "gdp",                  # 4: faction economic health
    "military_strength",    # 5: faction military capability
    "political_stability",  # 6: faction political stability
    "military_balance",     # 7: global military balance (novaris vs tethys)
    "territory_controlled", # 8: fraction of territory held by novaris
    "sanctions_level",      # 9: international sanctions on novaris
    "international_support",# 10: international support for tethys
    "agent_recommendation", # 11: individual agent action recommendation
    "faction_action",       # 12: aggregated faction action (after weighting)
]

CONFLICT_N = len(CONFLICT_VARIABLES)
CONFLICT_VAR_INDEX = {v: i for i, v in enumerate(CONFLICT_VARIABLES)}


def get_conflict_ground_truth() -> np.ndarray:
    """Return the ground truth adjacency matrix for the conflict engine.

    Derived from conflict/engine.py analysis:
    - compute_escalation(): faction actions → EI (with interaction modifier)
    - aggregate_faction_action(): recommendations → faction_action (weighted by role)
    - update_faction_states(): EI → GDP, military, stability, etc.
    - apply_shocks(): shock → EI, military_balance, sanctions, resources
    """
    M = np.zeros((CONFLICT_N, CONFLICT_N), dtype=int)
    idx = CONFLICT_VAR_INDEX

    # --- Shock effects ---
    # shock → escalation_index (border_incident, diplomatic_crisis, peace_initiative)
    M[idx["shock"], idx["escalation_index"]] = 1
    # shock → resources (economic_crisis → novaris resources)
    M[idx["shock"], idx["resources"]] = 1
    # shock → military_balance (military_incident)
    M[idx["shock"], idx["military_balance"]] = 1
    # shock → sanctions_level (international_pressure)
    M[idx["shock"], idx["sanctions_level"]] = 1

    # --- Agent decision ---
    # hawk_score → agent_recommendation (prompt-mediated in LLM, mechanistic in rule-based)
    M[idx["hawk_score"], idx["agent_recommendation"]] = 1
    # escalation_index → agent_recommendation (agents respond to current state)
    M[idx["escalation_index"], idx["agent_recommendation"]] = 1
    # resources → agent_recommendation (affordability constraint)
    M[idx["resources"], idx["agent_recommendation"]] = 1
    # State feedback via compute_state_modifier (agents_config.py):
    # gdp → agent_recommendation (economic pressure: low GDP → dovish)
    M[idx["gdp"], idx["agent_recommendation"]] = 1
    # military_strength → agent_recommendation (military confidence → hawkish)
    M[idx["military_strength"], idx["agent_recommendation"]] = 1
    # political_stability → agent_recommendation (war fatigue: low stability → dovish)
    M[idx["political_stability"], idx["agent_recommendation"]] = 1
    # sanctions_level → agent_recommendation (sanctions erode Novaris resolve)
    M[idx["sanctions_level"], idx["agent_recommendation"]] = 1
    # international_support → agent_recommendation (emboldens Tethys resistance)
    M[idx["international_support"], idx["agent_recommendation"]] = 1
    # military_balance → agent_recommendation (faction-specific advantage → hawkish)
    M[idx["military_balance"], idx["agent_recommendation"]] = 1

    # --- Aggregation ---
    # agent_recommendation → faction_action (weighted by role × action category)
    M[idx["agent_recommendation"], idx["faction_action"]] = 1

    # --- Escalation computation ---
    # faction_action → escalation_index (both factions' actions determine EI)
    M[idx["faction_action"], idx["escalation_index"]] = 1

    # --- State updates from escalation ---
    # escalation_index → gdp (high EI damages GDP)
    M[idx["escalation_index"], idx["gdp"]] = 1
    # escalation_index → political_stability (high EI reduces stability)
    M[idx["escalation_index"], idx["political_stability"]] = 1
    # NOTE: escalation_index does NOT directly update sanctions_level.
    # Sanctions are driven by novaris_action.escalation_delta (engine.py:247-250),
    # which is faction_action → sanctions_level (below).
    # escalation_index → international_support (high EI increases tethys support)
    M[idx["escalation_index"], idx["international_support"]] = 1

    # --- State updates from faction actions ---
    # faction_action → military_strength (military actions build/deplete strength)
    M[idx["faction_action"], idx["military_strength"]] = 1
    # faction_action → territory_controlled (offensive actions + advantage → territory)
    M[idx["faction_action"], idx["territory_controlled"]] = 1
    # faction_action → resources (action costs deplete resources)
    M[idx["faction_action"], idx["resources"]] = 1
    # faction_action → sanctions_level (novaris escalatory actions increase sanctions)
    M[idx["faction_action"], idx["sanctions_level"]] = 1

    # --- Cross-variable state updates ---
    # gdp → resources (GDP-dependent resource regeneration)
    M[idx["gdp"], idx["resources"]] = 1
    # sanctions_level → gdp (sanctions damage novaris GDP)
    M[idx["sanctions_level"], idx["gdp"]] = 1
    # military_strength → military_balance (strength difference → balance)
    M[idx["military_strength"], idx["military_balance"]] = 1
    # military_balance → territory_controlled (advantage enables territory change)
    M[idx["military_balance"], idx["territory_controlled"]] = 1

    # --- Feedback loops (all edges already encoded above) ---
    # Cycle 1: EI → rec → faction_action → EI (core escalation loop)
    # Cycle 2: resources → rec → faction_action → resources (resource depletion loop)
    # Cycle 3: EI → GDP → rec → faction_action → EI (economic pressure loop)
    # Cycle 4: EI → political_stability → rec → faction_action → EI (war fatigue loop)
    # Cycle 5: faction_action → sanctions → GDP → rec → faction_action (sanctions spiral)
    # Cycle 6: faction_action → mil_strength → mil_balance → rec → faction_action (military confidence loop)

    return M


# =============================================================================
# Scoring Functions
# =============================================================================

def structural_hamming_distance(
    estimated: np.ndarray, ground_truth: np.ndarray
) -> dict:
    """Structural Hamming Distance (SHD) for directed graphs.

    Counts three error types:
    - extra: edge in estimated but not in ground truth
    - missing: edge in ground truth but not in estimated
    - reversed: edge exists in both but with opposite orientation
      (truth has i→j only, estimate has j→i only) — counted as 1 error

    This matches the standard SHD definition (Tsamardinos et al. 2006).
    Works on cyclic graphs — no DAG assumption.
    """
    assert estimated.shape == ground_truth.shape
    n = estimated.shape[0]
    extra = 0
    missing = 0
    reversed_ = 0
    reversal_cells = set()

    # First pass: detect reversals (pairs where direction is swapped)
    for i in range(n):
        for j in range(i + 1, n):
            t_ij, t_ji = ground_truth[i, j], ground_truth[j, i]
            e_ij, e_ji = estimated[i, j], estimated[j, i]
            # Reversal: truth has one direction, estimate has the other
            if t_ij == 1 and t_ji == 0 and e_ij == 0 and e_ji == 1:
                reversed_ += 1
                reversal_cells.update(((i, j), (j, i)))
            elif t_ij == 0 and t_ji == 1 and e_ij == 1 and e_ji == 0:
                reversed_ += 1
                reversal_cells.update(((i, j), (j, i)))

    # Second pass: count remaining extra/missing (excluding reversal cells)
    for i in range(n):
        for j in range(n):
            if i == j or (i, j) in reversal_cells:
                continue
            if estimated[i, j] == 1 and ground_truth[i, j] == 0:
                extra += 1
            elif estimated[i, j] == 0 and ground_truth[i, j] == 1:
                missing += 1

    return {
        "shd": extra + missing + reversed_,
        "extra": extra,
        "missing": missing,
        "reversed": reversed_,
    }


def precision_recall(estimated: np.ndarray, ground_truth: np.ndarray) -> dict:
    """Compute precision and recall on edges.

    Precision: fraction of reported edges that are correct.
    Recall: fraction of true edges that are reported.
    """
    true_positives = int(np.sum((estimated == 1) & (ground_truth == 1)))
    false_positives = int(np.sum((estimated == 1) & (ground_truth == 0)))
    false_negatives = int(np.sum((estimated == 0) & (ground_truth == 1)))

    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    shd = structural_hamming_distance(estimated, ground_truth)

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "shd": shd["shd"],
        "shd_extra": shd["extra"],
        "shd_missing": shd["missing"],
        "shd_reversed": shd["reversed"],
        "total_true_edges": int(np.sum(ground_truth)),
        "total_estimated_edges": int(np.sum(estimated)),
        "total_possible_edges": ground_truth.shape[0] * ground_truth.shape[1],
    }


def per_edge_analysis(
    estimated: np.ndarray,
    ground_truth: np.ndarray,
    variable_names: list[str],
) -> list[dict]:
    """Per-edge analysis: which edges were correctly/incorrectly identified?

    Returns a list of dicts for edges that were either in ground truth or
    in the estimated graph (or both). Detects reversed edges (truth has
    i→j only, estimate has j→i only).
    """
    n = ground_truth.shape[0]

    # Detect reversal pairs first
    reversal_cells = set()
    for i in range(n):
        for j in range(i + 1, n):
            t_ij, t_ji = ground_truth[i, j], ground_truth[j, i]
            e_ij, e_ji = estimated[i, j], estimated[j, i]
            if t_ij == 1 and t_ji == 0 and e_ij == 0 and e_ji == 1:
                reversal_cells.update(((i, j), (j, i)))
            elif t_ij == 0 and t_ji == 1 and e_ij == 1 and e_ji == 0:
                reversal_cells.update(((i, j), (j, i)))

    edges = []
    for i in range(n):
        for j in range(n):
            gt = int(ground_truth[i, j])
            est = int(estimated[i, j])

            if gt == 0 and est == 0:
                continue  # neither — skip

            if (i, j) in reversal_cells:
                # This cell is part of a reversal pair
                if gt == 1 and est == 0:
                    status = "reversed"  # truth has i→j, estimate has j→i
                else:
                    continue  # skip the FP half; reversal reported on the FN side
            elif gt == est:
                status = "correct"
            elif est == 1:
                status = "false_positive"
            else:
                status = "false_negative"

            edges.append({
                "from": variable_names[i],
                "to": variable_names[j],
                "ground_truth": gt,
                "estimated": est,
                "status": status,
            })

    return edges


def score_market_graph(estimated: np.ndarray) -> dict:
    """Score an estimated market causal graph against ground truth."""
    gt = get_market_ground_truth()
    metrics = precision_recall(estimated, gt)
    metrics["per_edge"] = per_edge_analysis(estimated, gt, MARKET_VARIABLES)
    return metrics


def score_conflict_graph(estimated: np.ndarray) -> dict:
    """Score an estimated conflict causal graph against ground truth."""
    gt = get_conflict_ground_truth()
    metrics = precision_recall(estimated, gt)
    metrics["per_edge"] = per_edge_analysis(estimated, gt, CONFLICT_VARIABLES)
    return metrics


# =============================================================================
# Utility: convert agent's edge list to adjacency matrix
# =============================================================================

def edges_to_matrix(
    edges: list[tuple[str, str]],
    variable_names: list[str],
) -> np.ndarray:
    """Convert a list of (from, to) variable name pairs to an adjacency matrix."""
    n = len(variable_names)
    idx = {v: i for i, v in enumerate(variable_names)}
    M = np.zeros((n, n), dtype=int)

    for src, dst in edges:
        if src in idx and dst in idx:
            M[idx[src], idx[dst]] = 1

    return M


def print_graph_summary(domain: str = "market"):
    """Print a human-readable summary of the ground truth graph."""
    if domain == "market":
        gt = get_market_ground_truth()
        variables = MARKET_VARIABLES
    else:
        gt = get_conflict_ground_truth()
        variables = CONFLICT_VARIABLES

    n = len(variables)
    total_edges = int(np.sum(gt))
    total_possible = n * n

    print(f"\n{domain.upper()} Ground Truth Causal Graph")
    print(f"  Variables: {n}")
    print(f"  Edges: {total_edges} / {total_possible} possible ({total_edges/total_possible:.1%})")
    print(f"\n  Edges:")
    for i in range(n):
        for j in range(n):
            if gt[i, j] == 1:
                print(f"    {variables[i]} -> {variables[j]}")


if __name__ == "__main__":
    print_graph_summary("market")
    print_graph_summary("conflict")

    # Quick self-test: score a perfect recovery
    gt_market = get_market_ground_truth()
    perfect = score_market_graph(gt_market)
    assert perfect["precision"] == 1.0
    assert perfect["recall"] == 1.0
    assert perfect["shd"] == 0
    print("\n[OK] Perfect recovery scores correctly")

    # Score an empty graph
    empty = np.zeros_like(gt_market)
    empty_score = score_market_graph(empty)
    assert empty_score["precision"] == 0.0
    assert empty_score["recall"] == 0.0
    assert empty_score["shd"] == int(np.sum(gt_market))
    print("[OK] Empty graph scores correctly")

    # Test reversal detection
    gt_rev = np.zeros((3, 3), dtype=int)
    gt_rev[0, 1] = 1  # truth: 0→1
    est_rev = np.zeros((3, 3), dtype=int)
    est_rev[1, 0] = 1  # estimate: 1→0 (reversed)
    shd_rev = structural_hamming_distance(est_rev, gt_rev)
    assert shd_rev["shd"] == 1, f"Reversal should be 1 error, got {shd_rev['shd']}"
    assert shd_rev["reversed"] == 1
    assert shd_rev["extra"] == 0
    assert shd_rev["missing"] == 0
    print("[OK] Reversal counted as 1 SHD error (not 2)")

    # Score a random graph
    rng = np.random.default_rng(42)
    random_graph = (rng.random((MARKET_N, MARKET_N)) > 0.8).astype(int)
    random_score = score_market_graph(random_graph)
    print(f"\nRandom graph (20% density): {random_score['precision']:.2f} precision, "
          f"{random_score['recall']:.2f} recall, "
          f"SHD={random_score['shd']} "
          f"(extra={random_score['shd_extra']}, "
          f"missing={random_score['shd_missing']}, "
          f"reversed={random_score['shd_reversed']})")
