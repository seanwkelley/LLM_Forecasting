"""
Conflict PID Extraction — Convert conflict simulation actions into PID-ready matrices.

For each period t:
  X_i(t) = agent i's action encoding (escalatory / neutral / de-escalatory)
  Y(t)   = next-period escalation index change class (DOWN / FLAT / UP)

This lets us test: "Do agent pairs' actions jointly predict where escalation goes next?"

Design rationale (mirrors market PID):
- Target is t+1 EI change, NOT current EI level
- This avoids detecting mechanical correlation from the execution engine
- We measure genuine predictive information about escalation dynamics

Encoding stages (parallel to market):
  Stage 1 (direction):       {-1=de-escalatory, 0=neutral, +1=escalatory}    -> 3 levels
  Stage 2 (direction_aggr):  intensity x direction                            -> 5 levels
  Stage 3 (full):            unique integer per action type                   -> 13 levels

Pure numpy implementation (no pandas dependency).
"""

from __future__ import annotations

import json
import numpy as np
from pathlib import Path


# ---------------------------------------------------------------------------
# Action classification
# ---------------------------------------------------------------------------

# Direction: escalatory (+1), neutral (0), de-escalatory (-1)
ACTION_DIRECTION = {
    # Escalatory
    "limited_strike": 1,
    "border_incursion": 1,
    "naval_blockade": 1,
    "cyber_attack": 1,
    "military_buildup": 1,
    "proxy_support": 1,
    "propaganda_campaign": 1,
    # Neutral
    "intelligence_gathering": 0,
    "economic_sanctions": 0,
    # De-escalatory
    "ceasefire_offer": -1,
    "humanitarian_aid": -1,
    "peace_talks": -1,
    "trade_agreement": -1,
}

# Direction x intensity: strong escalatory (+2), mild escalatory (+1),
# neutral (0), mild de-escalatory (-1), strong de-escalatory (-2)
ACTION_DIRECTION_AGGR = {
    # Strong escalatory (kinetic / territorial)
    "limited_strike": 2,
    "border_incursion": 2,
    "naval_blockade": 2,
    # Mild escalatory (non-kinetic / preparatory)
    "cyber_attack": 1,
    "military_buildup": 1,
    "proxy_support": 1,
    "propaganda_campaign": 1,
    # Neutral (information / economic pressure)
    "intelligence_gathering": 0,
    "economic_sanctions": 0,
    # Mild de-escalatory (gestures)
    "ceasefire_offer": -1,
    "humanitarian_aid": -1,
    # Strong de-escalatory (commitment to resolution)
    "peace_talks": -2,
    "trade_agreement": -2,
}

# Full encoding: unique integer per action type (alphabetical)
ALL_ACTIONS = sorted(ACTION_DIRECTION.keys())
ACTION_FULL = {action: i for i, action in enumerate(ALL_ACTIONS)}


def load_scenario_result(filepath: str | Path) -> dict:
    """Load a saved scenario JSON from run_conflict_sim.py."""
    with open(filepath) as f:
        return json.load(f)


def tercile_bin(values: np.ndarray) -> np.ndarray:
    """Bin values into 3 equal-frequency classes (0, 1, 2).

    Uses percentile-based boundaries to ensure balanced classes.
    """
    p33 = np.percentile(values, 33.33)
    p67 = np.percentile(values, 66.67)
    result = np.zeros(len(values), dtype=int)
    result[values > p33] = 1
    result[values > p67] = 2
    return result


def extract_action_matrix(
    result: dict,
    encoding: str = "direction",
) -> tuple[np.ndarray, np.ndarray, list[str], np.ndarray]:
    """Extract PID-ready matrix from a single conflict scenario.

    Parameters
    ----------
    result : dict
        Output from run_conflict_sim.py (single scenario).
    encoding : str
        How to encode agent actions:
        - "direction": {-1=de-escalatory, 0=neutral, +1=escalatory}
        - "direction_aggr": 5-level intensity scale
        - "full": unique integer per action type

    Returns
    -------
    X : np.ndarray, shape (n_periods-1, n_agents)
        Action matrix. Excludes last period (no Y for it).
    Y : np.ndarray, shape (n_periods-1,)
        Next-period EI change class (0=DOWN, 1=FLAT, 2=UP).
    agent_names : list[str]
        Agent IDs (column labels for X).
    ei_history : np.ndarray
        Raw escalation index series for reference.
    """
    actions_log = result["actions_log"]
    ei_history = np.array(result["escalation_history"], dtype=float)

    # Identify all agents from recommendations
    all_agents = set()
    for period_data in actions_log:
        for rec in period_data.get("recommendations", []):
            all_agents.add(rec["agent_id"])
    all_agents = sorted(all_agents)

    n_periods = len(actions_log)
    n_agents = len(all_agents)
    agent_idx = {aid: i for i, aid in enumerate(all_agents)}

    # Select encoding lookup
    if encoding == "direction":
        lookup = ACTION_DIRECTION
    elif encoding == "direction_aggr":
        lookup = ACTION_DIRECTION_AGGR
    elif encoding == "full":
        lookup = ACTION_FULL
    else:
        raise ValueError(f"Unknown encoding: {encoding}")

    # Build action matrix
    X = np.zeros((n_periods, n_agents), dtype=int)

    for t in range(n_periods):
        for rec in actions_log[t].get("recommendations", []):
            idx = agent_idx.get(rec["agent_id"])
            if idx is None:
                continue
            action = rec.get("action", "")
            X[t, idx] = lookup.get(action, 0)

    # Compute target: next-period EI change, tercile-binned
    # EI changes from period t to t+1
    ei_changes = np.diff(ei_history)

    # Drop last period (no next-period EI change)
    # X has n_periods rows, ei_changes has n_periods-1 values
    # X[t] predicts ei_changes[t] = ei_history[t+1] - ei_history[t]
    X = X[:len(ei_changes)]
    Y = tercile_bin(ei_changes)

    return X, Y, all_agents, ei_history


def extract_multi_scenario(
    results_dir: str | Path,
    encoding: str = "direction",
    min_periods: int = 5,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Extract PID matrix from multiple conflict scenario results.

    Concatenates all scenarios. Each scenario contributes (n_periods - 1) rows.

    Parameters
    ----------
    results_dir : str or Path
        Directory with scenario_NNN.json files.
    encoding : str
        Action encoding method.
    min_periods : int
        Skip scenarios with fewer periods than this.

    Returns
    -------
    X : np.ndarray
        Action matrix.
    Y : np.ndarray
        Target EI change class.
    col_names : list[str]
        Agent names (column labels).
    """
    results_dir = Path(results_dir)
    scenario_files = sorted(results_dir.glob("scenario_*.json"))

    if not scenario_files:
        raise FileNotFoundError(f"No scenario files in {results_dir}")

    all_X = []
    all_Y = []
    col_names = None

    for f in scenario_files:
        result = load_scenario_result(f)
        n_periods = result.get("summary", {}).get("n_periods", len(result["actions_log"]))
        if n_periods < min_periods:
            continue

        X, Y, names, _ = extract_action_matrix(result, encoding=encoding)
        if col_names is None:
            col_names = names
        all_X.append(X)
        all_Y.append(Y)

    X = np.concatenate(all_X, axis=0)
    Y = np.concatenate(all_Y, axis=0)

    return X, Y, col_names


def print_extraction_summary(
    X: np.ndarray,
    Y: np.ndarray,
    col_names: list[str],
):
    """Print diagnostic summary of extracted PID data."""
    print(f"\nPID Extraction Summary")
    print(f"{'='*50}")
    print(f"  Total observations: {len(X)}")
    print(f"  Agent features: {X.shape[1]}")
    print(f"  Agents: {col_names}")

    # Target distribution
    print(f"\n  Target distribution (Y = next-period EI change):")
    labels = {0: "DOWN", 1: "FLAT", 2: "UP"}
    for val in sorted(np.unique(Y)):
        count = int(np.sum(Y == val))
        pct = count / len(Y) * 100
        print(f"    {labels.get(val, str(val)):5s}: {count:4d} ({pct:.1f}%)")

    # Entropy
    counts = np.bincount(Y)
    probs = counts[counts > 0] / len(Y)
    h = -np.sum(probs * np.log2(probs + 1e-10))
    max_h = np.log2(len(probs))
    print(f"\n  H(Y) = {h:.3f} bits (max = {max_h:.3f}, "
          f"efficiency = {h/max_h:.1%})")

    # Agent action distributions
    print(f"\n  Agent action distributions:")
    for i, col in enumerate(col_names):
        vals, counts = np.unique(X[:, i], return_counts=True)
        dist_str = ", ".join(f"{v}:{c}" for v, c in zip(vals, counts))
        print(f"    {col}: {dist_str}")
