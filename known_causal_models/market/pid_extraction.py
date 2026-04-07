"""
Market PID Extraction — Convert market simulation orders into PID-ready matrices.

For each period t:
  X_i(t) = agent i's order encoding (direction + aggressiveness)
  Y(t)   = next-period price change class (DOWN / FLAT / UP)

This lets us test: "Do agent pairs' orders jointly predict where price goes next?"

Design rationale (Section 7.1 of design doc):
- Target is t+1 price change, NOT current clearing price
- This avoids detecting mechanical synergy from the clearing algorithm
- We measure genuine predictive information

Encoding stages (Section 7.4):
  Stage 1 (simplest):  direction only — {-1, 0, +1} -> 3 levels
  Stage 2 (add aggr):  direction x aggressiveness -> 5 levels
  Stage 3 (full):      direction, aggressiveness, size separately

Pure numpy implementation (no pandas dependency).
"""

from __future__ import annotations

import json
import numpy as np
from pathlib import Path


def load_scenario_result(filepath: str | Path) -> dict:
    """Load a saved scenario JSON from run_market_sim.py."""
    with open(filepath) as f:
        return json.load(f)


def tercile_bin(values: np.ndarray) -> np.ndarray:
    """Bin values into 3 equal-frequency classes (0, 1, 2).

    Uses percentile-based boundaries to ensure balanced classes,
    avoiding the entropy trap from fixed bins.
    """
    p33 = np.percentile(values, 33.33)
    p67 = np.percentile(values, 66.67)
    result = np.zeros(len(values), dtype=int)
    result[values > p33] = 1
    result[values > p67] = 2
    return result


def extract_order_matrix(
    result: dict,
    encoding: str = "direction",
) -> tuple[np.ndarray, np.ndarray, list[str], np.ndarray]:
    """Extract PID-ready matrix from a single scenario result.

    Parameters
    ----------
    result : dict
        Output from run_market_sim.py (single scenario).
    encoding : str
        How to encode agent actions:
        - "direction": {-1=sell, 0=hold, +1=buy}
        - "direction_aggr": direction x aggressiveness (5 levels)
        - "full": direction, aggressiveness, size as separate columns

    Returns
    -------
    X : np.ndarray, shape (n_periods-1, n_agents) or (n_periods-1, n_agents*3)
        Action matrix. Excludes last period (no Y for it).
    Y : np.ndarray, shape (n_periods-1,)
        Next-period price change class (0=DOWN, 1=FLAT, 2=UP).
    agent_names : list[str]
        Agent IDs (column labels for X).
    prices : np.ndarray
        Raw price series for reference.
    """
    orders_log = result["orders_log"]
    price_history = np.array(result["price_history"], dtype=float)

    # Identify all agents
    all_agents = set()
    for period_data in orders_log:
        for order in period_data["orders"]:
            all_agents.add(order["agent_id"])
    all_agents = sorted(all_agents)

    n_periods = len(orders_log)

    if encoding == "direction":
        X, col_names = _encode_direction(orders_log, price_history, all_agents, n_periods)
    elif encoding == "direction_aggr":
        X, col_names = _encode_direction_aggr(orders_log, price_history, all_agents, n_periods)
    elif encoding == "full":
        X, col_names = _encode_full(orders_log, price_history, all_agents, n_periods)
    else:
        raise ValueError(f"Unknown encoding: {encoding}")

    # Compute target: next-period price return, tercile-binned
    returns = np.diff(price_history) / price_history[:-1]  # return from t to t+1

    # Drop last period (no next-period return)
    # X has n_periods rows, returns has n_periods-1 values
    # X[t] predicts returns[t] = (price[t+1] - price[t]) / price[t]
    X = X[:len(returns)]
    Y = tercile_bin(returns)

    return X, Y, col_names, price_history


def _encode_direction(
    orders_log: list[dict],
    price_history: np.ndarray,
    all_agents: list[str],
    n_periods: int,
) -> tuple[np.ndarray, list[str]]:
    """Stage 1: Direction only {-1=sell, 0=hold, +1=buy}."""
    n_agents = len(all_agents)
    agent_idx = {aid: i for i, aid in enumerate(all_agents)}
    X = np.zeros((n_periods, n_agents), dtype=int)

    for t in range(n_periods):
        for order in orders_log[t]["orders"]:
            idx = agent_idx.get(order["agent_id"])
            if idx is not None:
                if order["side"] == "buy":
                    X[t, idx] = 1
                elif order["side"] == "sell":
                    X[t, idx] = -1

    return X, all_agents


def _encode_direction_aggr(
    orders_log: list[dict],
    price_history: np.ndarray,
    all_agents: list[str],
    n_periods: int,
) -> tuple[np.ndarray, list[str]]:
    """Stage 2: Direction x aggressiveness -> 5 levels.

    Encoding:
      -2 = aggressive sell (price far below market)
      -1 = passive sell (price near market)
       0 = hold (no order)
      +1 = passive buy (price near market)
      +2 = aggressive buy (price far above market)
    """
    n_agents = len(all_agents)
    agent_idx = {aid: i for i, aid in enumerate(all_agents)}
    X = np.zeros((n_periods, n_agents), dtype=int)

    for t in range(n_periods):
        ref_price = price_history[t] if t < len(price_history) else price_history[-1]

        for order in orders_log[t]["orders"]:
            idx = agent_idx.get(order["agent_id"])
            if idx is None:
                continue

            limit = order["limit_price"]
            deviation = abs(limit - ref_price) / ref_price if ref_price > 0 else 0
            aggressive = deviation > 0.05  # >5% from market

            if order["side"] == "buy":
                X[t, idx] = 2 if aggressive else 1
            elif order["side"] == "sell":
                X[t, idx] = -2 if aggressive else -1

    return X, all_agents


def _encode_full(
    orders_log: list[dict],
    price_history: np.ndarray,
    all_agents: list[str],
    n_periods: int,
) -> tuple[np.ndarray, list[str]]:
    """Stage 3: Separate direction, aggressiveness, size columns."""
    n_agents = len(all_agents)
    agent_idx = {aid: i for i, aid in enumerate(all_agents)}
    X = np.zeros((n_periods, n_agents * 3), dtype=int)

    col_names = []
    for aid in all_agents:
        col_names.extend([f"{aid}_dir", f"{aid}_aggr", f"{aid}_size"])

    for t in range(n_periods):
        ref_price = price_history[t] if t < len(price_history) else price_history[-1]

        for order in orders_log[t]["orders"]:
            idx = agent_idx.get(order["agent_id"])
            if idx is None:
                continue

            limit = order["limit_price"]
            qty = order["quantity"]
            base = idx * 3

            # Direction
            if order["side"] == "buy":
                X[t, base] = 1
            elif order["side"] == "sell":
                X[t, base] = -1

            # Aggressiveness (3 levels)
            deviation = abs(limit - ref_price) / ref_price if ref_price > 0 else 0
            if deviation < 0.03:
                X[t, base + 1] = 0  # passive
            elif deviation < 0.08:
                X[t, base + 1] = 1  # moderate
            else:
                X[t, base + 1] = 2  # aggressive

            # Size (3 levels)
            if qty < 10:
                X[t, base + 2] = 0  # small
            elif qty <= 25:
                X[t, base + 2] = 1  # medium
            else:
                X[t, base + 2] = 2  # large

    return X, col_names


def extract_multi_scenario(
    results_dir: str | Path,
    encoding: str = "direction",
    min_periods: int = 10,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Extract PID matrix from multiple scenario results.

    Concatenates all scenarios. Each scenario contributes (n_periods - 1) rows.

    Parameters
    ----------
    results_dir : str or Path
        Directory with scenario_NNN.json files from run_market_sim.py.
    encoding : str
        Action encoding method.
    min_periods : int
        Skip scenarios with fewer periods than this.

    Returns
    -------
    X : np.ndarray
        Action matrix.
    Y : np.ndarray
        Target price change class.
    col_names : list[str]
        Column names for X.
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
        if result["summary"]["n_periods"] < min_periods:
            continue

        X, Y, names, _ = extract_order_matrix(result, encoding=encoding)
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
    print(f"\n  Target distribution (Y):")
    labels = {0: "DOWN", 1: "FLAT", 2: "UP"}
    for val in sorted(np.unique(Y)):
        count = int(np.sum(Y == val))
        pct = count / len(Y) * 100
        print(f"    {labels.get(val, str(val)):5s}: {count:4d} ({pct:.1f}%)")

    # Entropy
    counts = np.bincount(Y)
    probs = counts[counts > 0] / len(Y)
    entropy = -np.sum(probs * np.log2(probs + 1e-10))
    max_entropy = np.log2(len(probs))
    print(f"\n  H(Y) = {entropy:.3f} bits (max = {max_entropy:.3f}, "
          f"efficiency = {entropy/max_entropy:.1%})")

    # Agent action distributions
    print(f"\n  Agent action distributions:")
    for i, col in enumerate(col_names[:7]):
        vals, counts = np.unique(X[:, i], return_counts=True)
        dist_str = ", ".join(f"{v}:{c}" for v, c in zip(vals, counts))
        print(f"    {col}: {dist_str}")

    if len(col_names) > 7:
        print(f"    ... ({len(col_names) - 7} more)")
