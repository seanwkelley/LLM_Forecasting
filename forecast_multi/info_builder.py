"""
Information Level Builder — constructs the information section appended to base prompts.

L0: Time-series only (empty — base prompt already has full history)
L1: Random subset of expanded variables (no causal framing)
L2: Full causal graph + all expanded variables
L3: L2 + mechanistic Theory of Mind (agent decision rules)
"""

from __future__ import annotations

import hashlib

import numpy as np

from forecast_multi.causal_text import get_graph_text


def build(
    domain,
    scenario: dict,
    period: int,
    info_level: str,
    seed: int = 42,
) -> str:
    """Build the information section for a given level.

    Parameters
    ----------
    domain : MarketDomain or ConflictDomain
        The domain adapter instance.
    scenario : dict
        The loaded scenario data.
    period : int
        Current period index.
    info_level : str
        One of "L0", "L1", "L2", "L3".
    seed : int
        Base seed for random variable selection (L1).

    Returns
    -------
    str to append to the base prompt.
    """
    if info_level == "L0":
        return _build_l0()
    elif info_level == "L1":
        return _build_l1(domain, scenario, period, seed)
    elif info_level == "L2":
        return _build_l2(domain, scenario, period)
    elif info_level == "L3":
        return _build_l3(domain, scenario, period)
    else:
        raise ValueError(f"Unknown info level: {info_level}")


def _build_l0() -> str:
    """L0: Time-series only. Base prompt already has full history."""
    return ""


def _build_l1(domain, scenario: dict, period: int, seed: int) -> str:
    """L1: Random ~50% subset of expanded variables, no causal framing.

    Same random subset for all periods within a scenario (seeded by scenario hash),
    different across scenarios.
    """
    all_vars = domain.get_expanded_variables(scenario, period)

    # Deterministic seed per scenario
    sid = scenario.get("summary", {}).get("scenario_id", "unknown")
    scenario_seed = int(hashlib.md5(f"{sid}_{seed}".encode()).hexdigest()[:8], 16)
    rng = np.random.default_rng(scenario_seed)

    # Select ~50% of variables (exclude string-valued ones like action names)
    numeric_vars = {k: v for k, v in all_vars.items() if isinstance(v, (int, float))}
    var_names = sorted(numeric_vars.keys())
    n_select = max(1, len(var_names) // 2)
    selected = sorted(rng.choice(var_names, size=n_select, replace=False))

    parts = ["\n## Additional Observations"]
    for var in selected:
        val = numeric_vars[var]
        label = var.replace("_", " ").title()
        if isinstance(val, float):
            parts.append(f"- {label}: {val:.4f}")
        else:
            parts.append(f"- {label}: {val}")

    return "\n".join(parts)


def _build_l2(domain, scenario: dict, period: int) -> str:
    """L2: Causal graph description + ALL expanded variables."""
    parts = []

    # Causal graph description
    graph_text = get_graph_text(domain.name)
    parts.append(f"\n{graph_text}")

    # All expanded variables
    all_vars = domain.get_expanded_variables(scenario, period)
    numeric_vars = {k: v for k, v in all_vars.items() if isinstance(v, (int, float))}

    parts.append("\n## Current Observations (All Variables)")
    for var in sorted(numeric_vars.keys()):
        val = numeric_vars[var]
        label = var.replace("_", " ").title()
        if isinstance(val, float):
            parts.append(f"- {label}: {val:.4f}")
        else:
            parts.append(f"- {label}: {val}")

    return "\n".join(parts)


def _build_l3(domain, scenario: dict, period: int) -> str:
    """L3: L2 content + mechanistic Theory of Mind (decision rules)."""
    l2_content = _build_l2(domain, scenario, period)
    tom_content = domain.get_mechanistic_tom()
    return l2_content + tom_content
