"""Visualization for conflict simulation results (mechanistic baseline)."""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

AGENT_INFO = {
    "krasnov":   ("Military Chief",     "novaris"),
    "volkov":    ("Defense Minister",    "novaris"),
    "petrova":   ("Economic Advisor",    "novaris"),
    "morozov":   ("Intelligence Chief",  "novaris"),
    "marchetti": ("President",           "tethys"),
    "bondar":    ("Military Commander",  "tethys"),
    "kovalenko": ("Foreign Minister",    "tethys"),
}

AGENT_ORDER = list(AGENT_INFO.keys())

AGENT_SHORT = {k: v[0] for k, v in AGENT_INFO.items()}

FACTION_COLORS = {"novaris": "#d62728", "tethys": "#1f77b4"}

AGENT_COLORS = {
    "krasnov": "#d62728", "volkov": "#e45756", "petrova": "#f58518", "morozov": "#ff9da7",
    "marchetti": "#1f77b4", "bondar": "#4c78a8", "kovalenko": "#72b7b2",
}

# Escalatory actions push EI up, de-escalatory push down
ACTION_ESCALATION = {
    "border_incursion": 1, "cyber_attack": 1, "naval_blockade": 1,
    "economic_sanctions": 0.5, "propaganda_campaign": 0.5,
    "intelligence_gathering": 0,
    "humanitarian_aid": -0.5, "trade_agreement": -0.5,
    "ceasefire_offer": -1, "peace_talks": -1,
}

EI_ZONES = [
    (0, 3,  "#2ca02c", "Low"),
    (3, 5,  "#98df8a", "Moderate"),
    (5, 7,  "#ffbb78", "Elevated"),
    (7, 9,  "#ff7f0e", "High"),
    (9, 10, "#d62728", "Critical"),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_scenario(path):
    with open(path) as f:
        return json.load(f)


def _add_ei_zones(ax, alpha=0.06):
    """Add colored background bands for EI severity zones."""
    for lo, hi, color, _ in EI_ZONES:
        ax.axhspan(lo, hi, color=color, alpha=alpha, zorder=0)


# ---------------------------------------------------------------------------
# Plot 1: Multi-scenario escalation index grid
# ---------------------------------------------------------------------------

def plot_ei_grid(results_dir, output_path, title_prefix="Baseline", n_cols=5):
    """Grid of escalation index time-series for all scenarios."""
    results_dir = Path(results_dir)
    scenario_files = sorted(results_dir.glob("scenario_*.json"))
    n = len(scenario_files)
    if n == 0:
        print(f"No scenarios found in {results_dir}")
        return

    n_rows = (n + n_cols - 1) // n_cols
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(4 * n_cols, 3.5 * n_rows),
                             squeeze=False)

    for idx, fpath in enumerate(scenario_files):
        row, col = divmod(idx, n_cols)
        ax = axes[row][col]
        data = _load_scenario(fpath)
        ei = data["escalation_history"]
        periods = range(len(ei))

        _add_ei_zones(ax, alpha=0.08)

        ax.plot(periods, ei, "-o", color="#d62728", linewidth=1.4, markersize=2.5)
        ax.axhline(y=np.mean(ei), color="gray", linestyle="--", alpha=0.5, linewidth=0.8)

        sid = fpath.stem.replace("scenario_", "S")
        std = np.std(ei)
        ax.set_title(f"{sid} (std={std:.2f})", fontsize=9)
        ax.set_ylim(4, 10.5)
        ax.tick_params(labelsize=7)
        ax.grid(True, alpha=0.2)

    # Hide unused axes
    for idx in range(n, n_rows * n_cols):
        row, col = divmod(idx, n_cols)
        axes[row][col].set_visible(False)

    fig.suptitle(f"{title_prefix} — Escalation Index Histories ({n} scenarios)",
                 fontsize=14, fontweight="bold", y=1.02)

    # Add zone legend
    legend_elements = [
        Line2D([0], [0], marker="s", color="w", markerfacecolor=c, markersize=8,
               label=label)
        for _, _, c, label in EI_ZONES
    ]
    fig.legend(handles=legend_elements, loc="lower center", ncol=5,
               fontsize=8, title="EI Severity Zones",
               bbox_to_anchor=(0.5, -0.02))

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {output_path}")


# ---------------------------------------------------------------------------
# Plot 2: Detailed single-scenario (4 panels)
# ---------------------------------------------------------------------------

def plot_detailed(scenario_path, output_path):
    """4-panel detailed view of a single conflict scenario."""
    data = _load_scenario(scenario_path)
    log = data["actions_log"]
    ei = data["escalation_history"]
    periods = range(len(ei))

    fig, axes = plt.subplots(4, 1, figsize=(14, 14), sharex=True,
                             gridspec_kw={"height_ratios": [3, 2, 2, 2]})

    # --- Panel 1: Escalation Index ---
    ax = axes[0]
    _add_ei_zones(ax, alpha=0.10)
    ax.plot(periods, ei, "-o", color="#d62728", linewidth=2, markersize=4,
            label="Escalation Index", zorder=5)
    ax.axhline(y=np.mean(ei), color="gray", linestyle="--", alpha=0.6,
               linewidth=1, label=f"Mean EI = {np.mean(ei):.2f}")
    ax.fill_between(periods, np.mean(ei), ei, alpha=0.08, color="#d62728")

    sid = data["summary"]["scenario_id"]
    ax.set_title(f"Conflict Simulation — Rule-Based Baseline — {sid}",
                 fontsize=13, fontweight="bold")
    ax.set_ylabel("Escalation Index")
    ax.set_ylim(4, 10.5)
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(True, alpha=0.3)

    # Zone labels on right
    ax2 = ax.twinx()
    ax2.set_ylim(ax.get_ylim())
    ax2.set_yticks([1.5, 4, 6, 8, 9.5])
    ax2.set_yticklabels(["Low", "Moderate", "Elevated", "High", "Critical"],
                        fontsize=7, alpha=0.6)
    ax2.tick_params(length=0)

    # --- Panel 2: State indicators ---
    ax = axes[1]
    mil_bal = [e.get("military_balance", 0) for e in log]
    territory = [e.get("territory_controlled", 0) for e in log]
    sanctions = [e.get("sanctions_level", 0) for e in log]
    intl = [e.get("international_support", 0) for e in log]
    log_periods = range(len(log))

    ax.plot(log_periods, mil_bal, "-s", label="Military Balance", color="#9467bd",
            markersize=3, linewidth=1.2)
    ax.plot(log_periods, territory, "-^", label="Territory Ctrl", color="#2ca02c",
            markersize=3, linewidth=1.2)
    ax.plot(log_periods, sanctions, "-D", label="Sanctions Level", color="#e377c2",
            markersize=3, linewidth=1.2)
    ax.plot(log_periods, intl, "-v", label="Int'l Support", color="#17becf",
            markersize=3, linewidth=1.2)

    ax.axhline(y=0, color="black", linewidth=0.5, alpha=0.3)
    ax.set_ylabel("Indicator Value")
    ax.set_title("State Indicators Over Time", fontsize=11)
    ax.legend(loc="upper right", fontsize=8, ncol=2)
    ax.grid(True, alpha=0.3)

    # --- Panel 3: Faction resources & GDP ---
    ax = axes[2]
    nov_res = [e.get("novaris_resources", 0) for e in log]
    tet_res = [e.get("tethys_resources", 0) for e in log]
    nov_gdp = [e.get("novaris_gdp", 0) for e in log]
    tet_gdp = [e.get("tethys_gdp", 0) for e in log]

    ax.plot(log_periods, nov_res, "-o", color="#d62728", markersize=3,
            linewidth=1.2, label="Novaris Resources")
    ax.plot(log_periods, tet_res, "-o", color="#1f77b4", markersize=3,
            linewidth=1.2, label="Tethys Resources")

    ax_gdp = ax.twinx()
    ax_gdp.plot(log_periods, nov_gdp, "--", color="#d62728", alpha=0.5,
                linewidth=1, label="Novaris GDP")
    ax_gdp.plot(log_periods, tet_gdp, "--", color="#1f77b4", alpha=0.5,
                linewidth=1, label="Tethys GDP")
    ax_gdp.set_ylabel("GDP", fontsize=9, alpha=0.6)
    ax_gdp.tick_params(labelsize=7)

    ax.set_ylabel("Resources")
    ax.set_title("Faction Resources & GDP", fontsize=11)
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax_gdp.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, loc="upper right", fontsize=8, ncol=2)
    ax.grid(True, alpha=0.3)

    # --- Panel 4: Agent actions (escalatory vs de-escalatory) ---
    ax = axes[3]
    for t, entry in enumerate(log):
        for rec in entry["recommendations"]:
            aid = rec["agent_id"]
            action = rec["action"]
            esc_val = ACTION_ESCALATION.get(action, 0)
            color = AGENT_COLORS.get(aid, "gray")
            ax.scatter(t, esc_val, color=color, s=40, alpha=0.7,
                       edgecolors="black", linewidths=0.3, zorder=5)

    ax.axhline(y=0, color="black", linewidth=0.8, alpha=0.5)
    ax.fill_between(range(len(log)), 0, 1.2, alpha=0.04, color="red")
    ax.fill_between(range(len(log)), -1.2, 0, alpha=0.04, color="green")

    legend_elements = [
        Line2D([0], [0], marker="o", color="w", label=f"{AGENT_SHORT[aid]} ({AGENT_INFO[aid][1].title()})",
               markerfacecolor=AGENT_COLORS.get(aid, "gray"), markersize=8)
        for aid in AGENT_ORDER
    ]
    ax.legend(handles=legend_elements, loc="center left", bbox_to_anchor=(1.01, 0.5),
              fontsize=7, title="Agents")
    ax.set_ylabel("Action Escalation")
    ax.set_yticks([-1, -0.5, 0, 0.5, 1])
    ax.set_yticklabels(["De-escalatory", "Mild de-esc", "Neutral", "Mild esc", "Escalatory"],
                       fontsize=8)
    ax.set_xlabel("Period")
    ax.set_title("Agent Action Directions", fontsize=11)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {output_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    root = Path(__file__).parent.parent
    out = root / "outputs" / "plots" / "conflict"
    out.mkdir(parents=True, exist_ok=True)

    baseline_dir = root / "outputs" / "simulations" / "conflict"

    # 1. Multi-scenario EI grid
    plot_ei_grid(baseline_dir, str(out / "ei_grid_Baseline.png"),
                 title_prefix="Rule-Based Baseline")

    # 2. Detailed plots for scenarios with interesting dynamics
    for sid in ["001", "003", "009"]:
        fpath = baseline_dir / f"scenario_{sid}.json"
        if fpath.exists():
            plot_detailed(str(fpath), str(out / f"detailed_baseline_s{sid}.png"))
