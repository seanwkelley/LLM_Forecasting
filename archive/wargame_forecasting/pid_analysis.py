"""
PID Analysis Module

Core Partial Information Decomposition computation using the `dit` library.
Implements pairwise and full-group PID, permutation significance tests,
conditional analysis by scenario parameters, and leader value-add analysis.

Reference: Riedl (arXiv 2510.05174) — PID for emergent coordination.
PID method: BROJA (Bertschinger et al. 2014).
"""

import itertools
import numpy as np
import pandas as pd
from collections import Counter

try:
    import dit
    from dit.pid import PID_BROJA
except ImportError:
    raise ImportError(
        "The `dit` library is required. Install via: pip install dit"
    )


# ---------------------------------------------------------------------------
# Core PID computation
# ---------------------------------------------------------------------------

def _build_joint_distribution(x_cols, y_col, df):
    """Build a dit.Distribution from empirical counts of (X_1, ..., X_k, Y).

    Parameters
    ----------
    x_cols : list of str
        Column names for source variables.
    y_col : str
        Column name for target variable.
    df : pd.DataFrame
        Data with integer-valued columns.

    Returns
    -------
    dit.Distribution
        Joint distribution over the observed (x1, ..., xk, y) tuples.
    """
    cols = list(x_cols) + [y_col]
    subset = df[cols].dropna()

    # Convert to tuples of ints
    tuples = [tuple(int(v) for v in row) for row in subset.values]
    counts = Counter(tuples)
    total = sum(counts.values())

    if total == 0:
        raise ValueError("No valid observations for distribution construction")

    outcomes = [t for t in counts.keys()]
    probs = [counts[t] / total for t in outcomes]

    # dit requires string outcomes or tuple outcomes
    d = dit.Distribution(outcomes, probs)
    return d


def compute_pairwise_pid(matrix_df, agent_cols, target_col="Y"):
    """Compute PID for each pair of agents → target.

    For each pair (X_i, X_j), constructs the joint distribution over
    (X_i, X_j, Y) and runs BROJA PID decomposition.

    Parameters
    ----------
    matrix_df : pd.DataFrame
        Rows = scenarios, columns include agent_cols and target_col.
    agent_cols : list of str
        Column names for agent escalation values.
    target_col : str
        Column name for target variable (discretized outcome).

    Returns
    -------
    list of dict
        Each dict: {agent_i, agent_j, synergy, redundancy, unique_i, unique_j,
                     mutual_info, n_observations}.
    """
    results = []

    for i, j in itertools.combinations(range(len(agent_cols)), 2):
        col_i = agent_cols[i]
        col_j = agent_cols[j]

        try:
            d = _build_joint_distribution([col_i, col_j], target_col, matrix_df)

            # BROJA PID: sources are individual variables, target is last
            # d has variables indexed 0, 1, 2 (x_i, x_j, y)
            pid = PID_BROJA(d, [[0], [1]], [2])

            # Extract PID atoms (dit lattice node naming):
            # ((0, 1),)     = {0:1} = Synergy (joint node, requires both)
            # ((0,), (1,))  = {0}{1} = Redundancy (shared by both individually)
            # ((0,),)       = {0}   = Unique to agent i
            # ((1,),)       = {1}   = Unique to agent j
            synergy = float(pid.get_pi(((0, 1),)))
            redundancy = float(pid.get_pi(((0,), (1,))))
            unique_i = float(pid.get_pi(((0,),)))
            unique_j = float(pid.get_pi(((1,),)))

            mi = synergy + redundancy + unique_i + unique_j

            results.append({
                "agent_i": col_i,
                "agent_j": col_j,
                "synergy": synergy,
                "redundancy": redundancy,
                "unique_i": unique_i,
                "unique_j": unique_j,
                "mutual_info": mi,
                "n_observations": len(matrix_df.dropna(subset=[col_i, col_j, target_col])),
            })

        except Exception as e:
            print(f"  WARNING: PID failed for ({col_i}, {col_j}): {e}")
            results.append({
                "agent_i": col_i,
                "agent_j": col_j,
                "synergy": np.nan,
                "redundancy": np.nan,
                "unique_i": np.nan,
                "unique_j": np.nan,
                "mutual_info": np.nan,
                "n_observations": len(matrix_df.dropna(subset=[col_i, col_j, target_col])),
                "error": str(e),
            })

    return results


def compute_full_group_pid(matrix_df, agent_cols, target_col="Y"):
    """Compute PID with all agents as sources → target.

    Parameters
    ----------
    matrix_df : pd.DataFrame
        PID matrix.
    agent_cols : list of str
        All agent columns.
    target_col : str
        Target column.

    Returns
    -------
    dict
        PID results with all partial information atoms, or error info.
    """
    try:
        d = _build_joint_distribution(agent_cols, target_col, matrix_df)

        sources = [[i] for i in range(len(agent_cols))]
        target = [len(agent_cols)]
        pid = PID_BROJA(d, sources, target)

        # Extract all atoms
        atoms = {}
        for node in pid._lattice:
            val = float(pid.get_pi(node))
            atoms[str(node)] = val

        return {
            "agents": agent_cols,
            "atoms": atoms,
            "n_observations": len(matrix_df.dropna(subset=agent_cols + [target_col])),
        }

    except Exception as e:
        return {
            "agents": agent_cols,
            "error": str(e),
            "n_observations": len(matrix_df.dropna(subset=agent_cols + [target_col])),
        }


def emergence_capacity(pairwise_results):
    """Compute emergence capacity as median pairwise synergy.

    Following Riedl's S_macro metric.

    Parameters
    ----------
    pairwise_results : list of dict
        Output of compute_pairwise_pid().

    Returns
    -------
    float
        Median synergy across all agent pairs.
    """
    synergies = [r["synergy"] for r in pairwise_results if not np.isnan(r.get("synergy", np.nan))]
    if not synergies:
        return np.nan
    return float(np.median(synergies))


# ---------------------------------------------------------------------------
# Permutation significance tests
# ---------------------------------------------------------------------------

def _row_shuffle_surrogate(matrix_df, agent_cols, target_col, rng):
    """Create a row-shuffle surrogate: independently shuffle each agent column.

    Breaks inter-agent correlation while preserving marginal distributions.
    """
    surrogate = matrix_df.copy()
    for col in agent_cols:
        surrogate[col] = rng.permutation(surrogate[col].values)
    return surrogate


def _column_shift_surrogate(matrix_df, agent_cols, target_col, rng):
    """Create a column-shift surrogate: circularly shift each agent column.

    Preserves autocorrelation structure but breaks agent-outcome alignment.
    """
    surrogate = matrix_df.copy()
    n = len(surrogate)
    for col in agent_cols:
        shift = rng.integers(1, n)
        surrogate[col] = np.roll(surrogate[col].values, shift)
    return surrogate


def permutation_test(matrix_df, agent_cols, target_col="Y",
                     n_permutations=1000, surrogate_type="row_shuffle",
                     seed=42):
    """Run permutation test on pairwise PID synergy values.

    Parameters
    ----------
    matrix_df : pd.DataFrame
        PID matrix.
    agent_cols : list of str
        Agent columns.
    target_col : str
        Target column.
    n_permutations : int
        Number of surrogate datasets.
    surrogate_type : str
        "row_shuffle" or "column_shift".
    seed : int
        Random seed.

    Returns
    -------
    dict
        Keys: observed_synergy (per pair), null_distribution (per pair),
              p_values (per pair), emergence_capacity_observed,
              emergence_capacity_null, emergence_capacity_p.
    """
    rng = np.random.default_rng(seed)

    surrogate_fn = {
        "row_shuffle": _row_shuffle_surrogate,
        "column_shift": _column_shift_surrogate,
    }[surrogate_type]

    # Observed PID
    observed = compute_pairwise_pid(matrix_df, agent_cols, target_col)
    observed_ec = emergence_capacity(observed)

    # Pair keys
    pairs = [(r["agent_i"], r["agent_j"]) for r in observed]
    observed_synergy = {(r["agent_i"], r["agent_j"]): r["synergy"] for r in observed}

    # Null distributions
    null_synergy = {pair: [] for pair in pairs}
    null_ec = []

    for perm_i in range(n_permutations):
        if (perm_i + 1) % 100 == 0:
            print(f"  Permutation {perm_i + 1}/{n_permutations}...")

        surrogate = surrogate_fn(matrix_df, agent_cols, target_col, rng)
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
        "surrogate_type": surrogate_type,
    }


# ---------------------------------------------------------------------------
# Conditional analysis
# ---------------------------------------------------------------------------

def conditional_pid(matrix_df, agent_cols, target_col, condition_col,
                    threshold, labels=("low", "high")):
    """Compute PID separately for scenarios above/below a parameter threshold.

    Parameters
    ----------
    matrix_df : pd.DataFrame
        PID matrix with additional parameter columns.
    agent_cols : list of str
        Agent columns.
    target_col : str
        Target column.
    condition_col : str
        Column to split on.
    threshold : float
        Split threshold.
    labels : tuple of str
        Labels for below/above groups.

    Returns
    -------
    dict
        Keys: low/high → {pairwise_results, emergence_capacity, n_scenarios}.
    """
    low = matrix_df[matrix_df[condition_col] < threshold]
    high = matrix_df[matrix_df[condition_col] >= threshold]

    results = {}
    for label, subset in zip(labels, [low, high]):
        if len(subset) < 5:
            results[label] = {
                "pairwise_results": [],
                "emergence_capacity": np.nan,
                "n_scenarios": len(subset),
                "warning": f"Too few scenarios ({len(subset)}) for reliable PID",
            }
        else:
            pw = compute_pairwise_pid(subset, agent_cols, target_col)
            results[label] = {
                "pairwise_results": pw,
                "emergence_capacity": emergence_capacity(pw),
                "n_scenarios": len(subset),
            }

    return results


# ---------------------------------------------------------------------------
# Leader value-add analysis
# ---------------------------------------------------------------------------

def leader_value_add_pid(leader_df, collapse_bins=None):
    """Compute PID for (expert_proposal, leader_decision) → outcome.

    For each domain expert, measures whether the leader's approval/veto/counter
    adds synergistic information beyond what the expert's proposal carries.

    Parameters
    ----------
    leader_df : pd.DataFrame
        Output of extract_leader_decisions(). Columns: scenario_id, agent_role,
        expert_escalation, leader_decision, collapse_probability.
    collapse_bins : list of float
        Bin boundaries for collapse probability.

    Returns
    -------
    list of dict
        Per-agent PID results: {agent_role, synergy, redundancy,
        unique_expert, unique_leader, mutual_info}.
    """
    results = []

    for role, group in leader_df.groupby("agent_role"):
        # Discretize collapse probability
        group = group.copy()
        if collapse_bins in ("tercile", None):
            group["Y"] = pd.qcut(
                group["collapse_probability"], q=3, labels=[0, 1, 2]
            ).astype(int)
        elif collapse_bins == "quartile":
            group["Y"] = pd.qcut(
                group["collapse_probability"], q=4, labels=[0, 1, 2, 3]
            ).astype(int)
        else:
            group["Y"] = pd.cut(
                group["collapse_probability"],
                bins=collapse_bins,
                labels=list(range(len(collapse_bins) - 1)),
                include_lowest=True,
            ).astype(int)

        try:
            d = _build_joint_distribution(
                ["expert_escalation", "leader_decision"], "Y", group
            )

            pid = PID_BROJA(d, [[0], [1]], [2])

            synergy = float(pid.get_pi(((0, 1),)))
            redundancy = float(pid.get_pi(((0,), (1,))))
            unique_expert = float(pid.get_pi(((0,),)))
            unique_leader = float(pid.get_pi(((1,),)))
            mi = synergy + redundancy + unique_expert + unique_leader

            results.append({
                "agent_role": role,
                "synergy": synergy,
                "redundancy": redundancy,
                "unique_expert": unique_expert,
                "unique_leader": unique_leader,
                "mutual_info": mi,
                "n_observations": len(group),
            })

        except Exception as e:
            print(f"  WARNING: Leader PID failed for {role}: {e}")
            results.append({
                "agent_role": role,
                "synergy": np.nan,
                "redundancy": np.nan,
                "unique_expert": np.nan,
                "unique_leader": np.nan,
                "mutual_info": np.nan,
                "n_observations": len(group),
                "error": str(e),
            })

    return results


# ---------------------------------------------------------------------------
# Summary utilities
# ---------------------------------------------------------------------------

def pairwise_results_to_df(results):
    """Convert pairwise PID results list to a DataFrame."""
    return pd.DataFrame(results)


def summarize_pid(pairwise_results, faction_name=""):
    """Print a summary of PID results."""
    df = pairwise_results_to_df(pairwise_results)

    prefix = f"[{faction_name}] " if faction_name else ""
    print(f"\n{prefix}Pairwise PID Summary")
    print("=" * 70)

    valid = df.dropna(subset=["synergy"])
    if len(valid) == 0:
        print("  No valid PID results.")
        return

    for _, row in valid.iterrows():
        total = row["synergy"] + row["redundancy"] + row["unique_i"] + row["unique_j"]
        if total > 0:
            s_pct = 100 * row["synergy"] / total
            r_pct = 100 * row["redundancy"] / total
            ui_pct = 100 * row["unique_i"] / total
            uj_pct = 100 * row["unique_j"] / total
        else:
            s_pct = r_pct = ui_pct = uj_pct = 0

        print(f"  {row['agent_i']:12s} × {row['agent_j']:12s} | "
              f"MI={row['mutual_info']:.4f} | "
              f"Syn={row['synergy']:.4f} ({s_pct:4.1f}%) | "
              f"Red={row['redundancy']:.4f} ({r_pct:4.1f}%) | "
              f"U_i={row['unique_i']:.4f} ({ui_pct:4.1f}%) | "
              f"U_j={row['unique_j']:.4f} ({uj_pct:4.1f}%)")

    ec = emergence_capacity(pairwise_results)
    print(f"\n  Emergence Capacity (median synergy): {ec:.4f} bits")
    print(f"  Mean MI: {valid['mutual_info'].mean():.4f} bits")
    print(f"  Mean Synergy: {valid['synergy'].mean():.4f} bits")
    print(f"  Mean Redundancy: {valid['redundancy'].mean():.4f} bits")
