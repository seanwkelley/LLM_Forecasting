"""
PID Data Extraction Module

Reads per-scenario CSV files from the Tethys-Novaris simulation and produces
structured matrices suitable for Partial Information Decomposition analysis.

Handles:
- Action-to-escalation mapping (~43 distinct actions → 5 ordinal levels)
- Per-agent escalation extraction from proposals and final actions
- Pivot to PID-ready matrices (rows=scenarios, cols=agents, values=escalation)
- Collapse probability discretization
"""

import os
import re
import glob
import pandas as pd
import numpy as np
from pathlib import Path


# ---------------------------------------------------------------------------
# Escalation mapping: action_name → ordinal level {-1, 0, 1, 2, 3}
# ---------------------------------------------------------------------------

ESCALATION_MAP = {
    # Level -1: De-escalatory
    "peace_talks": -1,
    "formal_peace_talks": -1,
    "humanitarian_aid": -1,
    "humanitarian_corridors": -1,
    "prisoner_exchange": -1,
    "mediation_offer": -1,
    "backchannel_negotiations": -1,
    "cultural_exchange": -1,
    "diplomatic_visit": -1,
    "trade_negotiation": -1,
    "trade_agreement": -1,
    "financial_aid": -1,
    "economic_aid_to_allies": -1,
    "economic_aid_request": -1,
    "public_diplomatic_initiative": -1,
    "international_observers": -1,

    # Level 0: Neutral / defensive
    "intelligence_gathering": 0,
    "enhanced_intelligence_gathering": 0,
    "surveillance_operation": 0,
    "surveillance": 0,
    "enhanced_surveillance": 0,
    "strategic_stockpiling": 0,
    "counterintelligence": 0,
    "cyber_defense": 0,
    "enhanced_patrols": 0,
    "air_patrols": 0,
    "naval_patrols": 0,
    "reconnaissance": 0,
    "share_intelligence": 0,
    "war_bonds": 0,
    "sanctions_preparation": 0,
    "sanctions_evasion": 0,
    "defensive_fortification": 0,
    "defensive_reinforcements": 0,
    "troop_movements": 0,
    "information_campaign": 0,

    # Level 1: Assertive
    "military_buildup": 1,
    "naval_deployment": 1,
    "naval_demonstration": 1,
    "show_of_force": 1,
    "military_exercises": 1,
    "joint_exercises": 1,
    "formal_multilateral_engagement": 1,
    "trade_restrictions": 1,
    "coalition_building": 1,
    "sanctions": 1,
    "economic_sanctions": 1,
    "targeted_sanctions": 1,
    "sanctions_coordination": 1,
    "asset_seizure": 1,
    "political_warfare": 1,

    # Level 2: Aggressive
    "cyber_attack": 2,
    "cyber_theft": 2,
    "sabotage": 2,
    "resource_embargo": 2,
    "currency_manipulation": 2,
    "economic_warfare": 2,
    "spread_disinformation": 2,
    "false_flag_operation": 2,
    "proxy_support": 2,
    "propaganda_campaign": 2,

    # Level 3: Extreme
    "limited_strike": 3,
    "border_incursion": 3,
    "blockade": 3,
    "siege_warfare": 3,
    "leadership_targeting": 3,
    "asymmetric_guerrilla_operations": 3,
    "occupation": 3,
    "full_scale_attack": 3,
    "assassination_attempt": 3,
    "regime_destabilization": 3,
    "nuclear_development": 3,
}


def action_to_escalation(action_name):
    """Map an action name to its escalation level {-1, 0, 1, 2, 3}.

    Returns np.nan for unknown actions (logged as warnings during extraction).
    """
    if pd.isna(action_name):
        return np.nan
    action = str(action_name).strip().lower()
    return ESCALATION_MAP.get(action, np.nan)


# ---------------------------------------------------------------------------
# Data extraction
# ---------------------------------------------------------------------------

def _find_scenario_dirs(base_dir):
    """Find all scenario_NNN directories, sorted numerically."""
    pattern = os.path.join(base_dir, "scenario_*")
    dirs = []
    for d in glob.glob(pattern):
        if os.path.isdir(d):
            m = re.search(r"scenario_(\d+)", os.path.basename(d))
            if m:
                dirs.append((int(m.group(1)), d))
    dirs.sort(key=lambda x: x[0])
    return dirs


def extract_agent_escalation_matrix(base_dir):
    """Extract per-agent escalation data from all scenarios.

    Parameters
    ----------
    base_dir : str
        Path to outputs/multiscenario/ directory.

    Returns
    -------
    pd.DataFrame
        Columns: scenario_id, faction_name, agent_role, priority,
                 proposed_action, proposed_escalation,
                 final_action, final_escalation, approval_status,
                 collapse_probability, + scenario parameter columns.
    """
    scenario_dirs = _find_scenario_dirs(base_dir)
    if not scenario_dirs:
        raise FileNotFoundError(f"No scenario directories found in {base_dir}")

    # Load ground truth (has collapse_probability)
    gt_path = os.path.join(base_dir, "ground_truth.csv")
    gt = pd.read_csv(gt_path)

    # Load scenario parameters
    sc_path = os.path.join(base_dir, "scenarios.csv")
    sc = pd.read_csv(sc_path)

    all_rows = []
    unmapped_actions = set()

    for scen_num, scen_dir in scenario_dirs:
        scenario_id = f"scenario_{scen_num:03d}"

        # Read proposals
        proposals_path = os.path.join(scen_dir, "period_01_proposals.csv")
        if not os.path.exists(proposals_path):
            continue
        proposals = pd.read_csv(proposals_path)

        # Read actions (final decisions)
        actions_path = os.path.join(scen_dir, "period_01_actions.csv")
        actions = None
        if os.path.exists(actions_path):
            actions = pd.read_csv(actions_path)

        # Get collapse probability from ground truth
        gt_row = gt[gt["scenario_id"] == scenario_id]
        collapse_prob = gt_row["collapse_probability"].values[0] if len(gt_row) > 0 else np.nan

        # Get scenario parameters
        sc_row = sc[sc["scenario_id"] == scenario_id]

        # Process proposals (only Novaris and Tethys domain experts)
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

            # Find matching final action
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

                    if pd.isna(final_esc) and not pd.isna(final_action):
                        unmapped_actions.add(str(final_action).strip().lower())

            row = {
                "scenario_id": scenario_id,
                "scenario_num": scen_num,
                "faction_name": faction,
                "agent_role": role,
                "priority": priority,
                "proposed_action": proposed_action,
                "proposed_escalation": proposed_esc,
                "final_action": final_action,
                "final_escalation": final_esc,
                "approval_status": approval,
                "collapse_probability": collapse_prob,
            }

            # Add scenario parameters
            if len(sc_row) > 0:
                for col in ["territory_controlled", "military_balance",
                             "sanctions_level", "international_support",
                             "crisis_level", "novaris_gdp", "tethys_gdp",
                             "gdp_ratio", "momentum"]:
                    if col in sc_row.columns:
                        row[col] = sc_row.iloc[0][col]

            all_rows.append(row)

    if unmapped_actions:
        print(f"WARNING: {len(unmapped_actions)} unmapped actions: {sorted(unmapped_actions)}")

    df = pd.DataFrame(all_rows)
    return df


# ---------------------------------------------------------------------------
# Pivot to PID matrix
# ---------------------------------------------------------------------------

def _aggregate_escalation(group, method="primary"):
    """Aggregate multiple action priorities into a single escalation value.

    Parameters
    ----------
    group : pd.DataFrame
        Rows for a single (scenario, faction, agent) with different priorities.
    method : str
        "primary" - use only primary proposal
        "max" - maximum escalation across all priorities
        "mean" - mean escalation rounded to nearest int
    """
    if method == "primary":
        primary = group[group["priority"] == "primary"]
        if len(primary) > 0:
            return primary.iloc[0]
        return group.iloc[0]
    elif method == "max":
        idx = group["proposed_escalation"].idxmax()
        row = group.loc[idx].copy()
        row["proposed_escalation"] = group["proposed_escalation"].max()
        return row
    elif method == "mean":
        row = group.iloc[0].copy()
        row["proposed_escalation"] = round(group["proposed_escalation"].mean())
        return row
    else:
        raise ValueError(f"Unknown aggregation method: {method}")


def pivot_to_pid_matrix(df, faction, use_final=False, aggregation="primary",
                        collapse_bins=None, target="collapse_probability",
                        target_values=None):
    """Pivot the long-form data into a PID-ready matrix.

    Parameters
    ----------
    df : pd.DataFrame
        Output of extract_agent_escalation_matrix().
    faction : str
        "Novaris" or "Tethys".
    use_final : bool
        If True, use final_escalation; otherwise proposed_escalation.
    aggregation : str
        How to aggregate multiple priorities: "primary", "max", "mean".
    collapse_bins : list of float or None
        Bin boundaries for target variable. Default: [0, 0.45, 0.65, 1.0]
        producing LOW/MEDIUM/HIGH. If None and target != "collapse_probability",
        uses tercile-based binning.
    target : str
        Target variable name. Default "collapse_probability".
        Alternatives: "final_crisis_level", "final_military_balance",
        "final_territory", "final_sanctions", "final_support".
    target_values : pd.DataFrame or None
        If provided, a DataFrame with 'scenario_id' and the target column.
        Used for target variables not in the main extraction (e.g., from ground_truth.csv).

    Returns
    -------
    pd.DataFrame
        Rows = scenarios, columns = agent roles (escalation values) + "Y" (discretized target).
    dict
        Metadata: agent_cols, target_col, bin_labels, bin_boundaries.
    """
    faction_df = df[df["faction_name"] == faction].copy()

    # Exclude government/leader from domain experts
    faction_df = faction_df[faction_df["agent_role"] != "government"]

    esc_col = "final_escalation" if use_final else "proposed_escalation"

    # Aggregate across priorities
    agg_rows = []
    for (scen, role), group in faction_df.groupby(["scenario_id", "agent_role"]):
        agg_row = _aggregate_escalation(group, method=aggregation)
        agg_rows.append({
            "scenario_id": scen,
            "agent_role": role,
            "escalation": agg_row[esc_col],
            "collapse_probability": agg_row["collapse_probability"],
        })

    agg_df = pd.DataFrame(agg_rows)

    # Pivot: rows=scenarios, columns=agent_roles
    pivot = agg_df.pivot_table(
        index="scenario_id",
        columns="agent_role",
        values="escalation",
        aggfunc="first",
    )

    # Add target variable
    if target == "collapse_probability":
        cp = agg_df.groupby("scenario_id")["collapse_probability"].first()
        pivot["_target"] = cp
    elif target_values is not None and target in target_values.columns:
        tv = target_values.set_index("scenario_id")[target]
        pivot["_target"] = tv
    else:
        raise ValueError(f"Target '{target}' not available. Provide target_values DataFrame.")

    # Drop rows with any NaN escalation or target
    agent_cols = [c for c in pivot.columns if c not in ("_target",)]
    pivot = pivot.dropna(subset=agent_cols + ["_target"])

    # Discretize target variable
    if collapse_bins == "tercile":
        # Equal-frequency tercile binning (maximizes target entropy)
        vals = pivot["_target"].values
        pivot["Y"], qcut_bins = pd.qcut(vals, q=3, labels=[0, 1, 2], retbins=True)
        pivot["Y"] = pivot["Y"].astype(int)
        bins = qcut_bins.tolist()
        bin_labels = [0, 1, 2]
        label_names = ["LOW", "MEDIUM", "HIGH"]
    elif collapse_bins == "quartile":
        # Equal-frequency quartile binning
        vals = pivot["_target"].values
        pivot["Y"], qcut_bins = pd.qcut(vals, q=4, labels=[0, 1, 2, 3], retbins=True)
        pivot["Y"] = pivot["Y"].astype(int)
        bins = qcut_bins.tolist()
        bin_labels = [0, 1, 2, 3]
        label_names = ["Q1", "Q2", "Q3", "Q4"]
    elif collapse_bins is not None:
        bins = collapse_bins
        bin_labels = list(range(len(bins) - 1))
        pivot["Y"] = pd.cut(
            pivot["_target"],
            bins=bins,
            labels=bin_labels,
            include_lowest=True,
        ).astype(int)
        if target == "collapse_probability" and len(bins) - 1 == 3:
            label_names = ["LOW", "MEDIUM", "HIGH"]
        else:
            label_names = [f"BIN_{i}" for i in bin_labels]
    elif target == "collapse_probability":
        # Default: tercile binning (equal-frequency)
        vals = pivot["_target"].values
        pivot["Y"], qcut_bins = pd.qcut(vals, q=3, labels=[0, 1, 2], retbins=True)
        pivot["Y"] = pivot["Y"].astype(int)
        bins = qcut_bins.tolist()
        bin_labels = [0, 1, 2]
        label_names = ["LOW", "MEDIUM", "HIGH"]
    else:
        # Tercile-based binning for alternative targets
        vals = pivot["_target"].values
        pivot["Y"], qcut_bins = pd.qcut(vals, q=3, labels=[0, 1, 2], retbins=True)
        pivot["Y"] = pivot["Y"].astype(int)
        bins = qcut_bins.tolist()
        bin_labels = [0, 1, 2]
        label_names = [f"BIN_{i}" for i in bin_labels]

    # Keep target continuous value for reference
    pivot["target_continuous"] = pivot["_target"]
    pivot = pivot.drop(columns=["_target"])

    metadata = {
        "agent_cols": sorted(agent_cols),
        "target_col": "Y",
        "target_name": target,
        "bin_labels": dict(zip(bin_labels, label_names)),
        "bin_boundaries": bins,
        "faction": faction,
        "use_final": use_final,
        "aggregation": aggregation,
        "n_scenarios": len(pivot),
    }

    return pivot, metadata


def extract_leader_decisions(df, faction):
    """Extract leader decision data for leader value-add analysis.

    For each domain expert's proposal, returns:
    - expert_escalation: the proposed escalation level
    - leader_decision: 0=approved, 1=counter_proposed, 2=vetoed
    - collapse_probability: scenario outcome

    Parameters
    ----------
    df : pd.DataFrame
        Output of extract_agent_escalation_matrix().
    faction : str
        "Novaris" or "Tethys".

    Returns
    -------
    pd.DataFrame
        Columns: scenario_id, agent_role, expert_escalation,
                 leader_decision, collapse_probability.
    """
    faction_df = df[
        (df["faction_name"] == faction)
        & (df["agent_role"] != "government")
        & (df["priority"] == "primary")
    ].copy()

    decision_map = {"approved": 0, "counter_proposed": 1, "vetoed": 2}
    faction_df["leader_decision"] = faction_df["approval_status"].map(decision_map)

    result = faction_df[[
        "scenario_id", "agent_role", "proposed_escalation",
        "leader_decision", "collapse_probability"
    ]].rename(columns={"proposed_escalation": "expert_escalation"})

    return result.dropna()


def collapse_escalation_to_3_levels(df, escalation_cols):
    """Collapse 5-level escalation to 3 levels for small-sample robustness.

    Mapping: {-1, 0} → 0 (passive), {1} → 1 (assertive), {2, 3} → 2 (aggressive)

    Parameters
    ----------
    df : pd.DataFrame
        Matrix with escalation columns.
    escalation_cols : list of str
        Column names containing escalation values.

    Returns
    -------
    pd.DataFrame
        Copy of df with escalation values collapsed to {0, 1, 2}.
    """
    df = df.copy()
    mapping = {-1: 0, 0: 0, 1: 1, 2: 2, 3: 2}
    for col in escalation_cols:
        df[col] = df[col].map(mapping)
    return df


# ---------------------------------------------------------------------------
# Diagnostic utilities
# ---------------------------------------------------------------------------

def print_escalation_distribution(df):
    """Print the distribution of escalation levels across all agents."""
    esc_cols = ["proposed_escalation", "final_escalation"]
    for col in esc_cols:
        if col in df.columns:
            print(f"\n{col} distribution:")
            valid = df[col].dropna()
            counts = valid.value_counts().sort_index()
            total = counts.sum()
            for level, count in counts.items():
                pct = 100 * count / total
                level_int = int(level)
                label = {-1: "de-escalatory", 0: "neutral",
                         1: "assertive", 2: "aggressive", 3: "extreme"}.get(level_int, "?")
                print(f"  {level_int:+d} ({label:14s}): {count:4d} ({pct:5.1f}%)")


def print_collapse_distribution(df, bins=None):
    """Print the distribution of collapse probability across scenarios."""
    cp = df.groupby("scenario_id")["collapse_probability"].first()

    if bins in ("tercile", "quartile", None):
        q = 3 if bins != "quartile" else 4
        binned, boundaries = pd.qcut(cp, q=q, retbins=True)
        labels = sorted(binned.unique())
        print(f"\nCollapse probability distribution — {bins or 'tercile'} binning (n={len(cp)} scenarios):")
        print(f"  Bin boundaries: {[round(b, 4) for b in boundaries]}")
        for label in labels:
            count = (binned == label).sum()
            print(f"  {str(label):20s}: {count:3d} ({100*count/len(cp):5.1f}%)")
    else:
        labels = [f"BIN_{i}" for i in range(len(bins) - 1)]
        if len(bins) - 1 == 3:
            labels = ["LOW", "MEDIUM", "HIGH"]
        binned = pd.cut(cp, bins=bins, labels=labels, include_lowest=True)
        print(f"\nCollapse probability distribution — fixed bins (n={len(cp)} scenarios):")
        print(f"  Bin boundaries: {bins}")
        for label in labels:
            count = (binned == label).sum()
            print(f"  {label:8s}: {count:3d} ({100*count/len(cp):5.1f}%)")

    print(f"  Range: [{cp.min():.3f}, {cp.max():.3f}], Mean: {cp.mean():.3f}")
