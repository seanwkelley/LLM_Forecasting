"""
PID Visualization Module

Generates plots for PID analysis results:
1. Pairwise synergy heatmap (agent × agent)
2. Null distribution histograms with observed values
3. Stacked bar charts of PID decomposition
4. Conditional comparison bar charts
5. Proposed vs final comparison
6. Leader value-add visualization
"""

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns


def _ensure_dir(path):
    os.makedirs(path, exist_ok=True)


# ---------------------------------------------------------------------------
# 1. Pairwise synergy heatmap
# ---------------------------------------------------------------------------

def plot_synergy_heatmap(pairwise_results, faction_name, output_dir,
                         value_col="synergy"):
    """Plot agent × agent heatmap of a PID component.

    Parameters
    ----------
    pairwise_results : list of dict
        Output of compute_pairwise_pid().
    faction_name : str
        Faction label for title.
    output_dir : str
        Directory to save plot.
    value_col : str
        Which PID component to plot: synergy, redundancy, mutual_info, etc.
    """
    _ensure_dir(output_dir)

    df = pd.DataFrame(pairwise_results)
    if df.empty or df[value_col].isna().all():
        print(f"  Skipping heatmap for {faction_name}: no valid data")
        return

    # Get all agents
    agents = sorted(set(df["agent_i"]) | set(df["agent_j"]))
    n = len(agents)

    # Build symmetric matrix
    matrix = np.full((n, n), np.nan)
    agent_idx = {a: i for i, a in enumerate(agents)}

    for _, row in df.iterrows():
        i = agent_idx[row["agent_i"]]
        j = agent_idx[row["agent_j"]]
        val = row[value_col]
        matrix[i, j] = val
        matrix[j, i] = val

    # Diagonal = 0 (self-information not computed)
    np.fill_diagonal(matrix, 0)

    fig, ax = plt.subplots(figsize=(7, 6))
    mask = np.eye(n, dtype=bool)

    sns.heatmap(
        matrix, annot=True, fmt=".4f", cmap="YlOrRd",
        xticklabels=agents, yticklabels=agents,
        mask=mask, ax=ax, cbar_kws={"label": f"{value_col} (bits)"},
        linewidths=0.5,
    )

    ax.set_title(f"{faction_name} — Pairwise {value_col.title()}", fontsize=13)
    ax.set_xlabel("Agent Role")
    ax.set_ylabel("Agent Role")
    plt.tight_layout()

    fname = f"{faction_name.lower()}_{value_col}_heatmap.png"
    plt.savefig(os.path.join(output_dir, fname), dpi=150)
    plt.close()
    print(f"  Saved: {fname}")


# ---------------------------------------------------------------------------
# 2. Null distribution plot
# ---------------------------------------------------------------------------

def plot_null_distribution(permutation_results, faction_name, output_dir):
    """Plot histogram of surrogate synergy with observed value marked.

    Parameters
    ----------
    permutation_results : dict
        Output of permutation_test().
    faction_name : str
        Faction label.
    output_dir : str
        Directory to save plot.
    """
    _ensure_dir(output_dir)

    observed_synergy = permutation_results["observed_synergy"]
    null_synergy = permutation_results["null_synergy"]
    p_values = permutation_results["p_values"]

    pairs = list(observed_synergy.keys())
    n_pairs = len(pairs)

    if n_pairs == 0:
        return

    fig, axes = plt.subplots(1, n_pairs, figsize=(5 * n_pairs, 4), squeeze=False)

    for idx, pair in enumerate(pairs):
        ax = axes[0, idx]
        obs = observed_synergy[pair]
        null = [v for v in null_synergy[pair] if not np.isnan(v)]
        p = p_values.get(pair, np.nan)

        if null:
            ax.hist(null, bins=30, alpha=0.7, color="steelblue",
                    edgecolor="white", label="Null distribution")

        if not np.isnan(obs):
            ax.axvline(obs, color="red", linewidth=2, linestyle="--",
                       label=f"Observed = {obs:.4f}")

        p_str = f"p = {p:.3f}" if not np.isnan(p) else "p = N/A"
        ax.set_title(f"{pair[0]} × {pair[1]}\n{p_str}", fontsize=10)
        ax.set_xlabel("Synergy (bits)")
        ax.set_ylabel("Count")
        ax.legend(fontsize=8)

    fig.suptitle(f"{faction_name} — Synergy Null Distributions "
                 f"({permutation_results['surrogate_type']})",
                 fontsize=13, y=1.02)
    plt.tight_layout()

    fname = f"{faction_name.lower()}_null_distribution_{permutation_results['surrogate_type']}.png"
    plt.savefig(os.path.join(output_dir, fname), dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {fname}")

    # Also plot emergence capacity null distribution
    fig, ax = plt.subplots(figsize=(6, 4))
    null_ec = [v for v in permutation_results["emergence_capacity_null"]
               if not np.isnan(v)]
    obs_ec = permutation_results["emergence_capacity_observed"]
    ec_p = permutation_results["emergence_capacity_p"]

    if null_ec:
        ax.hist(null_ec, bins=30, alpha=0.7, color="steelblue",
                edgecolor="white", label="Null distribution")
    if not np.isnan(obs_ec):
        ax.axvline(obs_ec, color="red", linewidth=2, linestyle="--",
                   label=f"Observed EC = {obs_ec:.4f}")

    p_str = f"p = {ec_p:.3f}" if not np.isnan(ec_p) else "p = N/A"
    ax.set_title(f"{faction_name} — Emergence Capacity\n{p_str}", fontsize=12)
    ax.set_xlabel("Median Synergy (bits)")
    ax.set_ylabel("Count")
    ax.legend()
    plt.tight_layout()

    fname = f"{faction_name.lower()}_emergence_capacity_null_{permutation_results['surrogate_type']}.png"
    plt.savefig(os.path.join(output_dir, fname), dpi=150)
    plt.close()
    print(f"  Saved: {fname}")


# ---------------------------------------------------------------------------
# 3. Stacked bar chart (PID decomposition)
# ---------------------------------------------------------------------------

def plot_pid_decomposition(pairwise_results, faction_name, output_dir):
    """Stacked bar chart showing synergy/redundancy/unique proportions per pair.

    Parameters
    ----------
    pairwise_results : list of dict
        Output of compute_pairwise_pid().
    faction_name : str
        Faction label.
    output_dir : str
        Directory to save plot.
    """
    _ensure_dir(output_dir)

    df = pd.DataFrame(pairwise_results)
    valid = df.dropna(subset=["synergy"])
    if valid.empty:
        return

    pair_labels = [f"{r['agent_i']}\n× {r['agent_j']}" for _, r in valid.iterrows()]

    # Absolute values
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    components = ["synergy", "redundancy", "unique_i", "unique_j"]
    colors = ["#e74c3c", "#3498db", "#2ecc71", "#f39c12"]
    labels = ["Synergy", "Redundancy", "Unique (agent i)", "Unique (agent j)"]

    # Absolute values (bits)
    bottoms = np.zeros(len(valid))
    for comp, color, label in zip(components, colors, labels):
        vals = valid[comp].values
        ax1.bar(range(len(valid)), vals, bottom=bottoms, color=color,
                label=label, edgecolor="white", linewidth=0.5)
        bottoms += vals

    ax1.set_xticks(range(len(valid)))
    ax1.set_xticklabels(pair_labels, fontsize=8)
    ax1.set_ylabel("Information (bits)")
    ax1.set_title("Absolute PID")
    ax1.legend(fontsize=8)

    # Proportional
    totals = valid[components].sum(axis=1).values
    totals = np.where(totals == 0, 1, totals)  # avoid div by zero

    bottoms = np.zeros(len(valid))
    for comp, color, label in zip(components, colors, labels):
        vals = valid[comp].values / totals
        ax2.bar(range(len(valid)), vals, bottom=bottoms, color=color,
                label=label, edgecolor="white", linewidth=0.5)
        bottoms += vals

    ax2.set_xticks(range(len(valid)))
    ax2.set_xticklabels(pair_labels, fontsize=8)
    ax2.set_ylabel("Proportion")
    ax2.set_title("Proportional PID")
    ax2.set_ylim(0, 1)
    ax2.legend(fontsize=8)

    fig.suptitle(f"{faction_name} — PID Decomposition", fontsize=13)
    plt.tight_layout()

    fname = f"{faction_name.lower()}_pid_decomposition.png"
    plt.savefig(os.path.join(output_dir, fname), dpi=150)
    plt.close()
    print(f"  Saved: {fname}")


# ---------------------------------------------------------------------------
# 4. Conditional comparison
# ---------------------------------------------------------------------------

def plot_conditional_comparison(conditional_results, condition_name,
                                faction_name, output_dir):
    """Bar chart comparing emergence capacity across condition splits.

    Parameters
    ----------
    conditional_results : dict
        Output of conditional_pid(). Keys are condition labels.
    condition_name : str
        Name of the condition variable.
    faction_name : str
        Faction label.
    output_dir : str
        Directory to save plot.
    """
    _ensure_dir(output_dir)

    labels = list(conditional_results.keys())
    ecs = [conditional_results[l]["emergence_capacity"] for l in labels]
    ns = [conditional_results[l]["n_scenarios"] for l in labels]

    fig, ax = plt.subplots(figsize=(6, 4))
    bars = ax.bar(labels, ecs, color=["steelblue", "coral"], edgecolor="white")

    for bar, n, ec in zip(bars, ns, ecs):
        ypos = bar.get_height() if not np.isnan(bar.get_height()) else 0
        ax.text(bar.get_x() + bar.get_width() / 2, ypos + 0.002,
                f"n={n}\nEC={ec:.4f}" if not np.isnan(ec) else f"n={n}\nN/A",
                ha="center", va="bottom", fontsize=9)

    ax.set_ylabel("Emergence Capacity (median synergy, bits)")
    ax.set_title(f"{faction_name} — EC by {condition_name}", fontsize=12)
    ax.set_ylim(bottom=0)
    plt.tight_layout()

    fname = f"{faction_name.lower()}_conditional_{condition_name.lower().replace(' ', '_')}.png"
    plt.savefig(os.path.join(output_dir, fname), dpi=150)
    plt.close()
    print(f"  Saved: {fname}")


# ---------------------------------------------------------------------------
# 5. Proposed vs Final comparison
# ---------------------------------------------------------------------------

def plot_proposed_vs_final(proposed_results, final_results, faction_name,
                           output_dir):
    """Side-by-side synergy comparison for proposed vs final actions.

    Parameters
    ----------
    proposed_results : list of dict
        Pairwise PID from proposed actions.
    final_results : list of dict
        Pairwise PID from final actions.
    faction_name : str
        Faction label.
    output_dir : str
        Directory to save plot.
    """
    _ensure_dir(output_dir)

    prop_df = pd.DataFrame(proposed_results).dropna(subset=["synergy"])
    final_df = pd.DataFrame(final_results).dropna(subset=["synergy"])

    if prop_df.empty and final_df.empty:
        return

    # Merge on pair
    prop_df["pair"] = prop_df["agent_i"] + " × " + prop_df["agent_j"]
    final_df["pair"] = final_df["agent_i"] + " × " + final_df["agent_j"]

    merged = prop_df[["pair", "synergy"]].merge(
        final_df[["pair", "synergy"]],
        on="pair", suffixes=("_proposed", "_final"), how="outer"
    )

    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(len(merged))
    width = 0.35

    ax.bar(x - width / 2, merged["synergy_proposed"].fillna(0), width,
           label="Proposed", color="steelblue", edgecolor="white")
    ax.bar(x + width / 2, merged["synergy_final"].fillna(0), width,
           label="Final", color="coral", edgecolor="white")

    ax.set_xticks(x)
    ax.set_xticklabels(merged["pair"], rotation=30, ha="right", fontsize=9)
    ax.set_ylabel("Synergy (bits)")
    ax.set_title(f"{faction_name} — Proposed vs Final Action Synergy", fontsize=12)
    ax.legend()
    plt.tight_layout()

    fname = f"{faction_name.lower()}_proposed_vs_final.png"
    plt.savefig(os.path.join(output_dir, fname), dpi=150)
    plt.close()
    print(f"  Saved: {fname}")


# ---------------------------------------------------------------------------
# 6. Leader value-add visualization
# ---------------------------------------------------------------------------

def plot_leader_value_add(leader_results, faction_name, output_dir):
    """Stacked bar chart of leader value-add PID per domain expert.

    Parameters
    ----------
    leader_results : list of dict
        Output of leader_value_add_pid().
    faction_name : str
        Faction label.
    output_dir : str
        Directory to save plot.
    """
    _ensure_dir(output_dir)

    df = pd.DataFrame(leader_results)
    valid = df.dropna(subset=["synergy"])
    if valid.empty:
        print(f"  Skipping leader plot for {faction_name}: no valid data")
        return

    roles = valid["agent_role"].values
    components = ["synergy", "redundancy", "unique_expert", "unique_leader"]
    colors = ["#e74c3c", "#3498db", "#2ecc71", "#f39c12"]
    labels = ["Synergy", "Redundancy", "Unique (expert)", "Unique (leader)"]

    fig, ax = plt.subplots(figsize=(8, 5))
    bottoms = np.zeros(len(valid))

    for comp, color, label in zip(components, colors, labels):
        vals = valid[comp].values
        ax.bar(roles, vals, bottom=bottoms, color=color, label=label,
               edgecolor="white", linewidth=0.5)
        bottoms += vals

    ax.set_ylabel("Information (bits)")
    ax.set_title(f"{faction_name} — Leader Value-Add PID\n"
                 f"(Expert Proposal × Leader Decision → Outcome)",
                 fontsize=12)
    ax.legend(loc="upper right")
    plt.tight_layout()

    fname = f"{faction_name.lower()}_leader_value_add.png"
    plt.savefig(os.path.join(output_dir, fname), dpi=150)
    plt.close()
    print(f"  Saved: {fname}")


# ---------------------------------------------------------------------------
# Summary table
# ---------------------------------------------------------------------------

def plot_summary_table(all_results, output_dir):
    """Create a summary figure with key metrics as a table.

    Parameters
    ----------
    all_results : dict
        Nested dict with faction → metric results.
    output_dir : str
        Directory to save plot.
    """
    _ensure_dir(output_dir)

    rows = []
    for faction, data in all_results.items():
        pw = data.get("pairwise_results", [])
        pw_df = pd.DataFrame(pw).dropna(subset=["synergy"]) if pw else pd.DataFrame()

        if not pw_df.empty:
            rows.append({
                "Faction": faction,
                "N pairs": len(pw_df),
                "Mean MI (bits)": f"{pw_df['mutual_info'].mean():.4f}",
                "Mean Synergy": f"{pw_df['synergy'].mean():.4f}",
                "Mean Redundancy": f"{pw_df['redundancy'].mean():.4f}",
                "EC (median syn)": f"{data.get('emergence_capacity', np.nan):.4f}",
                "EC p-value": f"{data.get('ec_p_value', np.nan):.3f}",
            })

    if not rows:
        return

    table_df = pd.DataFrame(rows)

    fig, ax = plt.subplots(figsize=(12, 2 + 0.5 * len(rows)))
    ax.axis("off")
    table = ax.table(
        cellText=table_df.values,
        colLabels=table_df.columns,
        cellLoc="center",
        loc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.2, 1.5)

    # Header styling
    for j in range(len(table_df.columns)):
        table[0, j].set_facecolor("#2c3e50")
        table[0, j].set_text_props(color="white", fontweight="bold")

    ax.set_title("PID Emergence Analysis — Summary", fontsize=14, pad=20)
    plt.tight_layout()

    fname = "pid_summary_table.png"
    plt.savefig(os.path.join(output_dir, fname), dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {fname}")
