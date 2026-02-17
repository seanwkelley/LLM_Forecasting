"""
Market PID Analysis — Pairwise PID for market agent coordination.

Implements Williams-Beer Imin PID decomposition using only numpy/scipy.
No dependency on `dit` library (which has Python 3.14 compatibility issues).

Decomposition:
  MI(X_i, X_j; Y) = Synergy + Redundancy + Unique_i + Unique_j

Where Redundancy = Imin (Williams & Beer, 2010):
  Imin = sum_y p(y) * min_i { sum_{x_i} p(x_i|y) * log(p(y|x_i) / p(y)) }
"""

from __future__ import annotations

import itertools
import numpy as np
from collections import Counter


# ---------------------------------------------------------------------------
# Information-theoretic primitives
# ---------------------------------------------------------------------------

def entropy(x: np.ndarray) -> float:
    """Shannon entropy H(X) in bits."""
    counts = Counter(x)
    n = len(x)
    probs = np.array([c / n for c in counts.values()])
    return -float(np.sum(probs * np.log2(probs + 1e-15)))


def joint_entropy(x: np.ndarray, y: np.ndarray) -> float:
    """Joint entropy H(X, Y) in bits."""
    pairs = list(zip(x, y))
    counts = Counter(pairs)
    n = len(pairs)
    probs = np.array([c / n for c in counts.values()])
    return -float(np.sum(probs * np.log2(probs + 1e-15)))


def mutual_info(x: np.ndarray, y: np.ndarray) -> float:
    """Mutual information MI(X; Y) = H(X) + H(Y) - H(X,Y) in bits."""
    return entropy(x) + entropy(y) - joint_entropy(x, y)


def joint_mutual_info(x1: np.ndarray, x2: np.ndarray, y: np.ndarray) -> float:
    """Joint mutual information MI(X1, X2; Y) in bits.

    Treats the pair (X1, X2) as a single variable.
    """
    # Encode pair as single variable
    joint = np.array([f"{a}_{b}" for a, b in zip(x1, x2)])
    return mutual_info(joint, y)


# ---------------------------------------------------------------------------
# Williams-Beer Imin PID
# ---------------------------------------------------------------------------

def specific_info(source: np.ndarray, y: np.ndarray) -> dict[int, float]:
    """Specific information I(source; Y=y) for each y value.

    I(source; Y=y) = sum_s p(s|y) * log2(p(y|s) / p(y))
    """
    n = len(y)
    y_vals = np.unique(y)
    s_vals = np.unique(source)

    # Marginal p(y)
    p_y = {yv: np.sum(y == yv) / n for yv in y_vals}
    # Marginal p(s)
    p_s = {sv: np.sum(source == sv) / n for sv in s_vals}

    result = {}
    for yv in y_vals:
        mask_y = (y == yv)
        n_y = np.sum(mask_y)
        if n_y == 0:
            result[yv] = 0.0
            continue

        total = 0.0
        for sv in s_vals:
            # p(s|y)
            p_s_given_y = np.sum((source == sv) & mask_y) / n_y
            if p_s_given_y < 1e-15:
                continue
            # p(y|s)
            n_s = np.sum(source == sv)
            if n_s == 0:
                continue
            p_y_given_s = np.sum((source == sv) & mask_y) / n_s
            # specific info contribution
            if p_y[yv] > 0:
                total += p_s_given_y * np.log2(p_y_given_s / p_y[yv] + 1e-15)

        result[yv] = max(0.0, total)  # specific info is non-negative

    return result


def imin_redundancy(
    sources: list[np.ndarray],
    y: np.ndarray,
) -> float:
    """Williams-Beer Imin: minimum specific information across sources.

    Imin = sum_y p(y) * min_i { I(source_i; Y=y) }
    """
    n = len(y)
    y_vals = np.unique(y)

    # Compute specific info for each source
    spec_infos = [specific_info(src, y) for src in sources]

    total = 0.0
    for yv in y_vals:
        p_y = np.sum(y == yv) / n
        # Min across sources
        min_spec = min(si.get(yv, 0.0) for si in spec_infos)
        total += p_y * min_spec

    return max(0.0, total)


def pairwise_pid(
    x1: np.ndarray,
    x2: np.ndarray,
    y: np.ndarray,
) -> dict[str, float]:
    """Full Williams-Beer PID decomposition for two sources.

    Returns dict with: synergy, redundancy, unique_1, unique_2, mutual_info
    """
    mi_1 = mutual_info(x1, y)
    mi_2 = mutual_info(x2, y)
    mi_joint = joint_mutual_info(x1, x2, y)

    red = imin_redundancy([x1, x2], y)

    unique_1 = max(0.0, mi_1 - red)
    unique_2 = max(0.0, mi_2 - red)
    synergy = max(0.0, mi_joint - unique_1 - unique_2 - red)

    return {
        "synergy": synergy,
        "redundancy": red,
        "unique_1": unique_1,
        "unique_2": unique_2,
        "mutual_info": mi_joint,
        "mi_1": mi_1,
        "mi_2": mi_2,
    }


# ---------------------------------------------------------------------------
# Full analysis pipeline
# ---------------------------------------------------------------------------

def compute_all_pairwise(
    X: np.ndarray,
    Y: np.ndarray,
    col_names: list[str],
) -> list[dict]:
    """Compute PID for all agent pairs.

    Parameters
    ----------
    X : np.ndarray, shape (n_obs, n_agents)
    Y : np.ndarray, shape (n_obs,)
    col_names : list[str]
        Agent names corresponding to X columns.

    Returns
    -------
    list of dicts, one per pair.
    """
    n_agents = X.shape[1]
    results = []

    for i, j in itertools.combinations(range(n_agents), 2):
        pid = pairwise_pid(X[:, i], X[:, j], Y)
        pid["agent_i"] = col_names[i]
        pid["agent_j"] = col_names[j]
        results.append(pid)

    return results


def emergence_capacity(pair_results: list[dict]) -> float:
    """Median pairwise synergy (Emergence Capacity)."""
    synergies = [r["synergy"] for r in pair_results]
    return float(np.median(synergies))


# ---------------------------------------------------------------------------
# Permutation testing
# ---------------------------------------------------------------------------

def permutation_test(
    X: np.ndarray,
    Y: np.ndarray,
    col_names: list[str],
    n_permutations: int = 1000,
    method: str = "row_shuffle",
    seed: int = 42,
    verbose: bool = True,
) -> dict:
    """Permutation significance test for pairwise synergy and EC.

    Parameters
    ----------
    method : str
        "row_shuffle" — independently shuffle each agent column
        "column_shift" — circularly shift each column by random offset
    """
    rng = np.random.default_rng(seed)

    # Observed values
    obs_results = compute_all_pairwise(X, Y, col_names)
    obs_ec = emergence_capacity(obs_results)
    obs_synergies = {(r["agent_i"], r["agent_j"]): r["synergy"] for r in obs_results}

    # Permutation distribution
    perm_ecs = []
    perm_synergies = {pair: [] for pair in obs_synergies.keys()}

    n_obs, n_agents = X.shape

    for p in range(n_permutations):
        if verbose and (p + 1) % 100 == 0:
            print(f"  Permutation {p+1}/{n_permutations}...")

        # Generate surrogate
        X_perm = X.copy()
        for col in range(n_agents):
            if method == "row_shuffle":
                rng.shuffle(X_perm[:, col])
            elif method == "column_shift":
                shift = rng.integers(1, n_obs)
                X_perm[:, col] = np.roll(X_perm[:, col], shift)

        # Compute PID on surrogate
        perm_results = compute_all_pairwise(X_perm, Y, col_names)
        perm_ecs.append(emergence_capacity(perm_results))

        for r in perm_results:
            pair = (r["agent_i"], r["agent_j"])
            perm_synergies[pair].append(r["synergy"])

    # P-values
    perm_ecs = np.array(perm_ecs)
    ec_pvalue = float(np.mean(perm_ecs >= obs_ec))

    pair_pvalues = {}
    for pair, obs_syn in obs_synergies.items():
        perm_vals = np.array(perm_synergies[pair])
        pair_pvalues[pair] = float(np.mean(perm_vals >= obs_syn))

    return {
        "observed_ec": obs_ec,
        "ec_pvalue": ec_pvalue,
        "observed_pairs": obs_results,
        "pair_pvalues": pair_pvalues,
        "null_ec_distribution": perm_ecs,
    }


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_pid_summary(pair_results: list[dict], label: str = ""):
    """Print formatted PID summary."""
    header = f"Pairwise PID Summary"
    if label:
        header = f"[{label}] {header}"
    print(f"\n{header}")
    print("=" * 70)

    for r in pair_results:
        mi = r["mutual_info"]
        syn = r["synergy"]
        red = r["redundancy"]
        u1 = r["unique_1"]
        u2 = r["unique_2"]

        syn_pct = (syn / mi * 100) if mi > 0 else 0
        red_pct = (red / mi * 100) if mi > 0 else 0
        u1_pct = (u1 / mi * 100) if mi > 0 else 0
        u2_pct = (u2 / mi * 100) if mi > 0 else 0

        print(f"  {r['agent_i']:15s} x {r['agent_j']:15s} | "
              f"MI={mi:.4f} | "
              f"Syn={syn:.4f} ({syn_pct:4.1f}%) | "
              f"Red={red:.4f} ({red_pct:4.1f}%) | "
              f"U_i={u1:.4f} ({u1_pct:4.1f}%) | "
              f"U_j={u2:.4f} ({u2_pct:4.1f}%)")

    ec = emergence_capacity(pair_results)
    mean_mi = np.mean([r["mutual_info"] for r in pair_results])
    mean_syn = np.mean([r["synergy"] for r in pair_results])
    mean_red = np.mean([r["redundancy"] for r in pair_results])

    print(f"\n  Emergence Capacity (median synergy): {ec:.4f} bits")
    print(f"  Mean MI: {mean_mi:.4f} bits")
    print(f"  Mean Synergy: {mean_syn:.4f} bits")
    print(f"  Mean Redundancy: {mean_red:.4f} bits")


def print_permutation_results(perm_results: dict, label: str = ""):
    """Print permutation test results."""
    header = f"Permutation Test Results"
    if label:
        header = f"[{label}] {header}"
    print(f"\n{header}")
    print("=" * 70)
    print(f"  Emergence Capacity: {perm_results['observed_ec']:.4f} bits")
    print(f"  EC p-value: {perm_results['ec_pvalue']:.3f}")

    for pair, pval in perm_results["pair_pvalues"].items():
        obs_syn = [r for r in perm_results["observed_pairs"]
                    if (r["agent_i"], r["agent_j"]) == pair][0]["synergy"]
        sig = "***" if pval < 0.001 else "**" if pval < 0.01 else "*" if pval < 0.05 else ""
        print(f"  {pair[0]:15s} x {pair[1]:15s}: "
              f"synergy={obs_syn:.4f}, p={pval:.3f} {sig}")


# ---------------------------------------------------------------------------
# Higher-order synergies (triplet coalition tests)
# ---------------------------------------------------------------------------

def triplet_mutual_info(
    x1: np.ndarray, x2: np.ndarray, x3: np.ndarray, y: np.ndarray,
) -> float:
    """Joint mutual information MI(X1, X2, X3; Y) in bits."""
    joint = np.array([f"{a}_{b}_{c}" for a, b, c in zip(x1, x2, x3)])
    return mutual_info(joint, y)


def triplet_synergy_g3(
    x1: np.ndarray, x2: np.ndarray, x3: np.ndarray, y: np.ndarray,
) -> dict:
    """G3 coalition test (Riedl et al.): does the triplet beat the best pair?

    G3 = MI(X1, X2, X3; Y) - max(MI(Xi, Xj; Y))

    Positive G3 means the three agents together carry information that no
    pair captures — genuine higher-order synergy.

    Returns
    -------
    dict with mi_triplet, mi_best_pair, g3, best_pair_label.
    """
    mi_triplet = triplet_mutual_info(x1, x2, x3, y)

    mi_12 = joint_mutual_info(x1, x2, y)
    mi_13 = joint_mutual_info(x1, x3, y)
    mi_23 = joint_mutual_info(x2, x3, y)

    pairs = {"12": mi_12, "13": mi_13, "23": mi_23}
    best_label = max(pairs, key=pairs.get)
    mi_best = pairs[best_label]

    return {
        "mi_triplet": mi_triplet,
        "mi_best_pair": mi_best,
        "g3": mi_triplet - mi_best,
        "best_pair": best_label,
        "mi_12": mi_12,
        "mi_13": mi_13,
        "mi_23": mi_23,
    }


def compute_all_triplets(
    X: np.ndarray,
    Y: np.ndarray,
    col_names: list[str],
) -> list[dict]:
    """Compute G3 higher-order synergy for all agent triplets.

    Parameters
    ----------
    X : np.ndarray, shape (n_obs, n_agents)
    Y : np.ndarray, shape (n_obs,)
    col_names : list[str]

    Returns
    -------
    list of dicts with agent names, G3 values, and component MIs.
    """
    n_agents = X.shape[1]
    results = []

    for i, j, k in itertools.combinations(range(n_agents), 3):
        g3 = triplet_synergy_g3(X[:, i], X[:, j], X[:, k], Y)
        g3["agent_i"] = col_names[i]
        g3["agent_j"] = col_names[j]
        g3["agent_k"] = col_names[k]
        results.append(g3)

    return results


def higher_order_capacity(triplet_results: list[dict]) -> float:
    """Median G3 across all triplets (higher-order emergence capacity)."""
    g3_values = [r["g3"] for r in triplet_results]
    return float(np.median(g3_values))


def print_triplet_summary(triplet_results: list[dict], label: str = ""):
    """Print higher-order synergy summary."""
    header = "Higher-Order Synergy (Triplet G3)"
    if label:
        header = f"[{label}] {header}"
    print(f"\n{header}")
    print("=" * 70)

    # Sort by G3 descending
    sorted_results = sorted(triplet_results, key=lambda r: r["g3"], reverse=True)

    for r in sorted_results:
        sig = "+" if r["g3"] > 0.001 else "-" if r["g3"] < -0.001 else "="
        print(f"  [{sig}] {r['agent_i']:12s} x {r['agent_j']:12s} x {r['agent_k']:12s} | "
              f"G3={r['g3']:+.4f} | MI3={r['mi_triplet']:.4f} | "
              f"best_pair={r['mi_best_pair']:.4f}")

    hoc = higher_order_capacity(triplet_results)
    mean_g3 = np.mean([r["g3"] for r in triplet_results])
    pos_g3 = sum(1 for r in triplet_results if r["g3"] > 0.001)
    total = len(triplet_results)

    print(f"\n  Higher-Order Capacity (median G3): {hoc:+.4f} bits")
    print(f"  Mean G3: {mean_g3:+.4f} bits")
    print(f"  Positive G3 triplets: {pos_g3}/{total} "
          f"({pos_g3/total*100:.0f}%)")


# ---------------------------------------------------------------------------
# Identity-linked differentiation
# ---------------------------------------------------------------------------

def action_distribution(x: np.ndarray) -> dict[int, float]:
    """Compute normalized action distribution for a single agent."""
    vals, counts = np.unique(x, return_counts=True)
    total = counts.sum()
    return {int(v): c / total for v, c in zip(vals, counts)}


def jensen_shannon_divergence(p: dict, q: dict) -> float:
    """Jensen-Shannon divergence between two discrete distributions.

    JSD is symmetric, bounded [0, 1] (in bits with log2), and measures
    how distinguishable two distributions are.
    """
    # Union of all keys
    all_keys = set(p.keys()) | set(q.keys())

    # Convert to aligned arrays
    p_arr = np.array([p.get(k, 0.0) for k in sorted(all_keys)])
    q_arr = np.array([q.get(k, 0.0) for k in sorted(all_keys)])

    # Midpoint distribution
    m_arr = 0.5 * (p_arr + q_arr)

    # KL divergences
    def kl(a, b):
        mask = a > 0
        return float(np.sum(a[mask] * np.log2(a[mask] / (b[mask] + 1e-15))))

    return 0.5 * kl(p_arr, m_arr) + 0.5 * kl(q_arr, m_arr)


def compute_identity_differentiation(
    X: np.ndarray,
    col_names: list[str],
    scenario_boundaries: list[int] | None = None,
) -> dict:
    """Measure identity-linked differentiation across agents.

    Computes:
    1. Behavioral distinctiveness: pairwise JSD between agents' action
       distributions. High JSD = agents behave differently.
    2. Temporal consistency (split-half reliability): does each agent
       maintain a consistent behavioral profile across the first and
       second half of the data?

    Parameters
    ----------
    X : np.ndarray, shape (n_obs, n_agents)
        Action matrix (encoded agent orders).
    col_names : list[str]
        Agent names.
    scenario_boundaries : list[int] or None
        If provided, split by scenarios (odd/even) instead of temporal half.

    Returns
    -------
    dict with:
        pairwise_jsd: list of dicts (agent_i, agent_j, jsd)
        mean_jsd: float (mean pairwise JSD = overall differentiation)
        temporal_consistency: list of dicts (agent, jsd_half1_half2)
        mean_consistency: float (mean split-half JSD; lower = more consistent)
    """
    n_obs, n_agents = X.shape

    # --- 1. Behavioral distinctiveness (pairwise JSD) ---
    agent_dists = {}
    for i in range(n_agents):
        agent_dists[col_names[i]] = action_distribution(X[:, i])

    pairwise_jsd = []
    for i, j in itertools.combinations(range(n_agents), 2):
        jsd = jensen_shannon_divergence(
            agent_dists[col_names[i]],
            agent_dists[col_names[j]],
        )
        pairwise_jsd.append({
            "agent_i": col_names[i],
            "agent_j": col_names[j],
            "jsd": jsd,
        })

    mean_jsd = np.mean([r["jsd"] for r in pairwise_jsd])

    # --- 2. Temporal consistency (split-half reliability) ---
    half = n_obs // 2
    temporal = []
    for i in range(n_agents):
        dist_first = action_distribution(X[:half, i])
        dist_second = action_distribution(X[half:, i])
        jsd = jensen_shannon_divergence(dist_first, dist_second)
        temporal.append({
            "agent": col_names[i],
            "jsd_split_half": jsd,
        })

    mean_consistency = np.mean([r["jsd_split_half"] for r in temporal])

    # --- 3. Role entropy: how predictable is each agent's behavior? ---
    agent_entropy = []
    for i in range(n_agents):
        dist = agent_dists[col_names[i]]
        probs = np.array(list(dist.values()))
        h = -float(np.sum(probs * np.log2(probs + 1e-15)))
        agent_entropy.append({
            "agent": col_names[i],
            "action_entropy": h,
        })

    mean_entropy = np.mean([r["action_entropy"] for r in agent_entropy])

    return {
        "pairwise_jsd": pairwise_jsd,
        "mean_jsd": mean_jsd,
        "temporal_consistency": temporal,
        "mean_consistency_jsd": mean_consistency,
        "agent_entropy": agent_entropy,
        "mean_action_entropy": mean_entropy,
    }


def print_differentiation_summary(diff_results: dict, label: str = ""):
    """Print identity-linked differentiation summary."""
    header = "Identity-Linked Differentiation"
    if label:
        header = f"[{label}] {header}"
    print(f"\n{header}")
    print("=" * 70)

    # Pairwise JSD
    print(f"\n  Behavioral distinctiveness (pairwise JSD):")
    sorted_jsd = sorted(diff_results["pairwise_jsd"],
                        key=lambda r: r["jsd"], reverse=True)
    for r in sorted_jsd:
        bar = "#" * int(r["jsd"] * 50)
        print(f"    {r['agent_i']:15s} x {r['agent_j']:15s}: "
              f"JSD={r['jsd']:.4f} {bar}")

    print(f"\n  Mean pairwise JSD: {diff_results['mean_jsd']:.4f}")
    print(f"  (Higher = more differentiated. 0 = identical, 1 = maximally different)")

    # Agent entropy
    print(f"\n  Per-agent behavioral entropy:")
    for r in diff_results["agent_entropy"]:
        bar = "#" * int(r["action_entropy"] * 20)
        print(f"    {r['agent']:15s}: H={r['action_entropy']:.3f} bits {bar}")
    print(f"  Mean action entropy: {diff_results['mean_action_entropy']:.3f} bits")

    # Temporal consistency
    print(f"\n  Temporal consistency (split-half JSD, lower = more consistent):")
    for r in diff_results["temporal_consistency"]:
        status = "[OK]" if r["jsd_split_half"] < 0.1 else "[DRIFT]"
        print(f"    {r['agent']:15s}: JSD={r['jsd_split_half']:.4f} {status}")
    print(f"  Mean split-half JSD: {diff_results['mean_consistency_jsd']:.4f}")
