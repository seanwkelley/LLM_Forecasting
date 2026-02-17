"""
Temporal PID Analysis Module

Computes time-delayed Partial Information Decomposition (TDMI) following
Riedl (arXiv 2510.05174). Instead of cross-sectional PID (do agents
differentiate across scenarios?), temporal PID asks: do agents adapt
to each other's actions over time within scenarios?

Design:
- Sources: Agent i's action at time t, Agent j's action at time t
- Target: Change in system state from t to t+1 (discretized)
- Pool observations across scenarios (assuming stationarity)

This measures dynamic coordination — whether the joint action pattern
at time t carries synergistic information about what happens next.
"""

import os
import re
import glob
import itertools
import numpy as np
import pandas as pd
from collections import Counter
from pathlib import Path

try:
    import dit
    from dit.pid import PID_BROJA
except ImportError:
    raise ImportError("The `dit` library is required. Install via: pip install dit")

# Import shared utilities from the cross-sectional module
from pid_data_extraction import ESCALATION_MAP, action_to_escalation


# ---------------------------------------------------------------------------
# Data extraction for multi-period scenarios
# ---------------------------------------------------------------------------

def extract_temporal_data(base_dir):
    """Extract per-agent, per-period escalation data from multi-period scenarios.

    Parameters
    ----------
    base_dir : str
        Path to outputs/multiperiod_pilot/ directory.

    Returns
    -------
    pd.DataFrame
        Columns: scenario_id, period, faction_name, agent_role, priority,
                 proposed_action, proposed_escalation, final_action,
                 final_escalation, approval_status.
    pd.DataFrame
        Ground truth: scenario_id, period, collapse_probability, territory,
                      military_balance, crisis_level, sanctions_level, support.
    """
    # Find scenario directories
    pattern = os.path.join(base_dir, "scenario_*")
    scenario_dirs = []
    for d in glob.glob(pattern):
        if os.path.isdir(d):
            m = re.search(r"scenario_(\d+)", os.path.basename(d))
            if m:
                scenario_dirs.append((int(m.group(1)), d))
    scenario_dirs.sort(key=lambda x: x[0])

    if not scenario_dirs:
        raise FileNotFoundError(f"No scenario directories found in {base_dir}")

    # Load ground truth (has per-period data)
    gt_path = os.path.join(base_dir, "ground_truth.csv")
    gt = pd.read_csv(gt_path) if os.path.exists(gt_path) else None

    all_rows = []
    unmapped_actions = set()

    for scen_num, scen_dir in scenario_dirs:
        scenario_id = f"scenario_{scen_num:03d}"

        # Find all period files in this scenario
        proposal_files = sorted(glob.glob(
            os.path.join(scen_dir, "period_*_proposals.csv")
        ))

        for prop_file in proposal_files:
            # Extract period number from filename
            m = re.search(r"period_(\d+)_proposals", os.path.basename(prop_file))
            if not m:
                continue
            period = int(m.group(1))

            proposals = pd.read_csv(prop_file)

            # Also load actions if available
            action_file = os.path.join(scen_dir, f"period_{period:02d}_actions.csv")
            actions = pd.read_csv(action_file) if os.path.exists(action_file) else None

            for _, prop in proposals.iterrows():
                faction = prop.get("faction_name", "")
                if faction not in ("Novaris", "Tethys"):
                    continue

                role = prop.get("proposed_by_role", "")
                priority = prop.get("priority", "")
                proposed_action = prop.get("proposed_action", "")
                proposed_esc = action_to_escalation(proposed_action)

                if pd.isna(proposed_esc) and not pd.isna(proposed_action):
                    unmapped_actions.add(str(proposed_action).strip().lower())

                final_action = np.nan
                final_esc = np.nan
                approval = np.nan
                if actions is not None:
                    match = actions[
                        (actions["faction_name"] == faction)
                        & (actions["proposed_by_role"] == role)
                        & (actions["priority"] == priority)
                    ]
                    if len(match) > 0:
                        final_action = match.iloc[0].get("final_action", np.nan)
                        final_esc = action_to_escalation(final_action)
                        approval = match.iloc[0].get("approval_status", np.nan)

                all_rows.append({
                    "scenario_id": scenario_id,
                    "scenario_num": scen_num,
                    "period": period,
                    "faction_name": faction,
                    "agent_role": role,
                    "priority": priority,
                    "proposed_action": proposed_action,
                    "proposed_escalation": proposed_esc,
                    "final_action": final_action,
                    "final_escalation": final_esc,
                    "approval_status": approval,
                })

    if unmapped_actions:
        print(f"WARNING: {len(unmapped_actions)} unmapped actions: {sorted(unmapped_actions)}")

    actions_df = pd.DataFrame(all_rows)
    return actions_df, gt


def build_temporal_pid_matrix(actions_df, gt_df, faction, use_final=False,
                               target="delta_crisis"):
    """Build a matrix for temporal PID: agent actions at t → state change t→t+1.

    Parameters
    ----------
    actions_df : pd.DataFrame
        Output of extract_temporal_data() — per-agent, per-period data.
    gt_df : pd.DataFrame
        Ground truth with per-period state variables.
    faction : str
        "Novaris" or "Tethys".
    use_final : bool
        Use final (post-leader) actions instead of proposed.
    target : str
        Target variable for PID:
        - "delta_crisis": Change in crisis_level from t to t+1
        - "delta_collapse": Change in collapse_probability from t to t+1
        - "collapse_next": Collapse probability at t+1 (absolute)

    Returns
    -------
    pd.DataFrame
        Rows = (scenario, period t) transitions. Columns = agent roles
        (escalation values at time t) + "Y" (discretized target at t+1).
    dict
        Metadata.
    """
    esc_col = "final_escalation" if use_final else "proposed_escalation"

    # Filter to faction and primary proposals
    faction_df = actions_df[
        (actions_df["faction_name"] == faction)
        & (actions_df["agent_role"] != "government")
        & (actions_df["priority"] == "primary")
    ].copy()

    if faction_df.empty:
        raise ValueError(f"No data for faction {faction}")

    # Get unique periods per scenario
    scenario_periods = gt_df.groupby("scenario_id")["period"].apply(list).to_dict()

    transition_rows = []

    for scenario_id, periods in scenario_periods.items():
        periods = sorted(periods)
        for idx in range(len(periods) - 1):
            t = periods[idx]
            t_next = periods[idx + 1]

            # Get agent actions at time t
            agents_at_t = faction_df[
                (faction_df["scenario_id"] == scenario_id)
                & (faction_df["period"] == t)
            ]

            if agents_at_t.empty:
                continue

            # Get state at t and t+1
            gt_t = gt_df[(gt_df["scenario_id"] == scenario_id) & (gt_df["period"] == t)]
            gt_next = gt_df[(gt_df["scenario_id"] == scenario_id) & (gt_df["period"] == t_next)]

            if gt_t.empty or gt_next.empty:
                continue

            # Compute target
            if target == "delta_crisis":
                y_val = gt_next.iloc[0]["crisis_level"] - gt_t.iloc[0]["crisis_level"]
            elif target == "delta_collapse":
                y_val = gt_next.iloc[0]["collapse_probability"] - gt_t.iloc[0]["collapse_probability"]
            elif target == "collapse_next":
                y_val = gt_next.iloc[0]["collapse_probability"]
            else:
                raise ValueError(f"Unknown target: {target}")

            row = {
                "scenario_id": scenario_id,
                "period_t": t,
                "period_t_next": t_next,
                "y_continuous": y_val,
            }

            # Add per-agent escalation at time t
            for _, agent_row in agents_at_t.iterrows():
                role = agent_row["agent_role"]
                esc = agent_row[esc_col]
                row[role] = esc

            transition_rows.append(row)

    if not transition_rows:
        raise ValueError("No valid temporal transitions found")

    matrix = pd.DataFrame(transition_rows)

    # Identify agent columns
    meta_cols = {"scenario_id", "period_t", "period_t_next", "y_continuous"}
    agent_cols = sorted([c for c in matrix.columns if c not in meta_cols])

    # Drop rows with missing agent data
    matrix = matrix.dropna(subset=agent_cols)

    # Discretize target variable into 3 bins
    y_vals = matrix["y_continuous"].values
    if target.startswith("delta"):
        # Tertile split for deltas
        q33 = np.percentile(y_vals, 33.3)
        q67 = np.percentile(y_vals, 66.7)
        matrix["Y"] = pd.cut(
            matrix["y_continuous"],
            bins=[-np.inf, q33, q67, np.inf],
            labels=[0, 1, 2],
        ).astype(int)
        bin_labels = {0: "DECREASE", 1: "STABLE", 2: "INCREASE"}
    else:
        # Fixed bins for absolute values
        bins = [0, 0.45, 0.65, 1.0]
        matrix["Y"] = pd.cut(
            matrix["y_continuous"],
            bins=bins,
            labels=[0, 1, 2],
            include_lowest=True,
        ).astype(int)
        bin_labels = {0: "LOW", 1: "MEDIUM", 2: "HIGH"}

    metadata = {
        "agent_cols": agent_cols,
        "target_col": "Y",
        "target_type": target,
        "bin_labels": bin_labels,
        "faction": faction,
        "use_final": use_final,
        "n_transitions": len(matrix),
        "n_scenarios": matrix["scenario_id"].nunique(),
    }

    return matrix, metadata


# ---------------------------------------------------------------------------
# Temporal PID computation (reuses core PID from pid_analysis.py)
# ---------------------------------------------------------------------------

def compute_temporal_pairwise_pid(matrix_df, agent_cols, target_col="Y"):
    """Compute pairwise PID on temporal transitions.

    Same as cross-sectional, but rows are (scenario, t→t+1) transitions
    instead of individual scenarios.
    """
    from pid_analysis import compute_pairwise_pid
    return compute_pairwise_pid(matrix_df, agent_cols, target_col)


def compute_temporal_emergence_capacity(pairwise_results):
    """Compute temporal emergence capacity (median pairwise synergy)."""
    from pid_analysis import emergence_capacity
    return emergence_capacity(pairwise_results)


def temporal_permutation_test(matrix_df, agent_cols, target_col="Y",
                               n_permutations=500, seed=42):
    """Permutation test adapted for temporal data.

    Uses block-shuffle: shuffle entire scenario blocks rather than
    individual rows, preserving within-scenario temporal structure.
    """
    from pid_analysis import compute_pairwise_pid, emergence_capacity

    rng = np.random.default_rng(seed)

    # Observed PID
    observed = compute_pairwise_pid(matrix_df, agent_cols, target_col)
    observed_ec = emergence_capacity(observed)

    pairs = [(r["agent_i"], r["agent_j"]) for r in observed]
    observed_synergy = {(r["agent_i"], r["agent_j"]): r["synergy"] for r in observed}

    null_synergy = {pair: [] for pair in pairs}
    null_ec = []

    for perm_i in range(n_permutations):
        if (perm_i + 1) % 100 == 0:
            print(f"  Permutation {perm_i + 1}/{n_permutations}...")

        # Block-shuffle: for each agent, shuffle scenario labels
        # (preserving within-scenario temporal order)
        surrogate = matrix_df.copy()
        scenarios = surrogate["scenario_id"].unique()

        for col in agent_cols:
            # Group by scenario, shuffle the scenario assignment
            scenario_map = dict(zip(scenarios, rng.permutation(scenarios)))
            # For each row, replace agent value with value from shuffled scenario
            new_vals = []
            for _, row in surrogate.iterrows():
                source_scen = scenario_map[row["scenario_id"]]
                source_rows = matrix_df[
                    (matrix_df["scenario_id"] == source_scen)
                    & (matrix_df["period_t"] == row["period_t"])
                ]
                if len(source_rows) > 0:
                    new_vals.append(source_rows.iloc[0][col])
                else:
                    # Fallback: random row from source scenario
                    source_all = matrix_df[matrix_df["scenario_id"] == source_scen]
                    if len(source_all) > 0:
                        new_vals.append(source_all.iloc[rng.integers(len(source_all))][col])
                    else:
                        new_vals.append(row[col])
            surrogate[col] = new_vals

        surr_results = compute_pairwise_pid(surrogate, agent_cols, target_col)

        for r in surr_results:
            pair = (r["agent_i"], r["agent_j"])
            null_synergy[pair].append(r.get("synergy", np.nan))

        null_ec.append(emergence_capacity(surr_results))

    # Compute p-values
    p_values = {}
    for pair in pairs:
        obs = observed_synergy[pair]
        null = np.array([v for v in null_synergy[pair] if not np.isnan(v)])
        if len(null) > 0 and not np.isnan(obs):
            p_values[pair] = float(np.mean(null >= obs))
        else:
            p_values[pair] = np.nan

    null_ec_arr = np.array([v for v in null_ec if not np.isnan(v)])
    ec_p = float(np.mean(null_ec_arr >= observed_ec)) if len(null_ec_arr) > 0 else np.nan

    return {
        "observed": observed,
        "observed_synergy": observed_synergy,
        "null_synergy": null_synergy,
        "p_values": p_values,
        "emergence_capacity_observed": observed_ec,
        "emergence_capacity_null": null_ec,
        "emergence_capacity_p": ec_p,
        "n_permutations": n_permutations,
    }


# ---------------------------------------------------------------------------
# Action adaptation analysis
# ---------------------------------------------------------------------------

def compute_action_adaptation(actions_df, faction):
    """Measure how much each agent's actions change across periods.

    Returns per-agent metrics:
    - action_entropy: How varied their actions are across time
    - period_to_period_change_rate: Fraction of periods where action changes
    - escalation_range: Max - min escalation across periods
    """
    faction_df = actions_df[
        (actions_df["faction_name"] == faction)
        & (actions_df["agent_role"] != "government")
        & (actions_df["priority"] == "primary")
    ].copy()

    results = []

    for role, group in faction_df.groupby("agent_role"):
        for scenario_id, scen_group in group.groupby("scenario_id"):
            scen_group = scen_group.sort_values("period")
            actions = scen_group["proposed_action"].tolist()
            escalations = scen_group["proposed_escalation"].dropna().tolist()

            # Change rate
            changes = sum(1 for a, b in zip(actions[:-1], actions[1:]) if a != b)
            change_rate = changes / max(len(actions) - 1, 1)

            # Escalation range
            esc_range = (max(escalations) - min(escalations)) if escalations else 0

            # Unique actions
            n_unique = len(set(actions))

            results.append({
                "scenario_id": scenario_id,
                "agent_role": role,
                "n_periods": len(actions),
                "n_unique_actions": n_unique,
                "change_rate": change_rate,
                "escalation_range": esc_range,
                "mean_escalation": np.mean(escalations) if escalations else np.nan,
            })

    return pd.DataFrame(results)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def summarize_temporal_pid(pairwise_results, faction_name=""):
    """Print temporal PID summary."""
    from pid_analysis import summarize_pid
    print(f"\n[{faction_name}] Temporal PID (time-delayed)")
    summarize_pid(pairwise_results, faction_name)
