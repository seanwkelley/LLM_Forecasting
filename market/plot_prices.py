"""Visualization for market simulation results and PID analysis."""

import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

AGENT_ORDER = [
    "producer_A", "producer_B",
    "consumer_A", "consumer_B", "consumer_C",
    "speculator_A", "speculator_B",
]

AGENT_SHORT = {
    "producer_A": "Prod A", "producer_B": "Prod B",
    "consumer_A": "Con A", "consumer_B": "Con B", "consumer_C": "Con C",
    "speculator_A": "Spec A", "speculator_B": "Spec B",
}

ROLE_COLORS = {
    "producer_A": "#1f77b4", "producer_B": "#aec7e8",
    "consumer_A": "#2ca02c", "consumer_B": "#98df8a", "consumer_C": "#d62728",
    "speculator_A": "#ff7f0e", "speculator_B": "#ffbb78",
}


def _load_scenario(path):
    with open(path) as f:
        return json.load(f)


def _load_pid_csv(path):
    """Load pairwise PID CSV into list of dicts."""
    rows = []
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({k: float(v) if k != "agent_i" and k != "agent_j" else v
                         for k, v in row.items()})
    return rows


def _pid_to_matrix(pid_rows, metric="synergy"):
    """Convert pairwise PID rows to a 7x7 symmetric matrix."""
    n = len(AGENT_ORDER)
    mat = np.zeros((n, n))
    idx = {a: i for i, a in enumerate(AGENT_ORDER)}
    for row in pid_rows:
        i = idx.get(row["agent_i"])
        j = idx.get(row["agent_j"])
        if i is not None and j is not None:
            mat[i, j] = row[metric]
            mat[j, i] = row[metric]
    return mat


# ---------------------------------------------------------------------------
# Plot 1: Price time series comparison (3 conditions, 1 scenario)
# ---------------------------------------------------------------------------

def plot_price_comparison(baseline_path, nopersona_path, persona_path,
                          output_path, scenario_id="001"):
    """3-panel price series: baseline vs no-persona vs persona."""
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    configs = [
        (baseline_path, "Rule-Based Baseline", "#1f77b4"),
        (nopersona_path, "LLM (No Persona)", "#2ca02c"),
        (persona_path, "LLM (With Personas)", "#d62728"),
    ]

    for ax, (fpath, title, color) in zip(axes, configs):
        p = Path(fpath)
        if not p.exists():
            ax.set_title(f"{title} (not found)")
            continue

        data = _load_scenario(p)
        prices = data["price_history"]
        fund = data["fundamental_history"]
        periods = range(len(prices))

        ax.plot(periods, prices, f"-o", color=color, label="Clearing Price",
                markersize=3, linewidth=1.5)
        ax.plot(periods, fund, "k--", label="Fundamental", alpha=0.5, linewidth=1)
        ax.fill_between(periods, prices, fund, alpha=0.1, color=color)
        ax.set_title(f"{title}\nScenario {scenario_id}", fontsize=11, fontweight="bold")
        ax.set_xlabel("Period")
        ax.set_ylabel("Price ($)")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)

        std = np.std(prices)
        vol = np.std(np.diff(np.log(np.array(prices)))) * 100
        ax.text(0.02, 0.02, f"std=${std:.1f}  vol={vol:.1f}%",
                transform=ax.transAxes, fontsize=8, verticalalignment="bottom",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {output_path}")


# ---------------------------------------------------------------------------
# Plot 2: Multi-scenario price overview (one condition)
# ---------------------------------------------------------------------------

def plot_multi_scenario(results_dir, output_path, title_prefix="", n_cols=5):
    """Grid of price series for all scenarios in a results directory."""
    results_dir = Path(results_dir)
    scenario_files = sorted(results_dir.glob("scenario_*.json"))
    n = len(scenario_files)
    if n == 0:
        print(f"No scenarios found in {results_dir}")
        return

    n_rows = (n + n_cols - 1) // n_cols
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(4 * n_cols, 3 * n_rows),
                             squeeze=False)

    for idx, fpath in enumerate(scenario_files):
        row, col = divmod(idx, n_cols)
        ax = axes[row][col]
        data = _load_scenario(fpath)
        prices = data["price_history"]
        fund = data["fundamental_history"]

        ax.plot(prices, "b-", linewidth=1.2, label="Price")
        ax.plot(fund, "r--", linewidth=0.8, alpha=0.5, label="Fundamental")
        sid = fpath.stem.replace("scenario_", "S")
        std = np.std(prices)
        ax.set_title(f"{sid} (std=${std:.0f})", fontsize=9)
        ax.tick_params(labelsize=7)
        ax.grid(True, alpha=0.2)

    # Hide unused axes
    for idx in range(n, n_rows * n_cols):
        row, col = divmod(idx, n_cols)
        axes[row][col].set_visible(False)

    fig.suptitle(f"{title_prefix} Price Histories ({n} scenarios)",
                 fontsize=14, fontweight="bold", y=1.02)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {output_path}")


# ---------------------------------------------------------------------------
# Plot 3: PID synergy heatmap
# ---------------------------------------------------------------------------

def plot_pid_heatmap(pid_csv_path, output_path, title="PID Synergy Heatmap"):
    """Heatmap of pairwise synergy values."""
    pid_rows = _load_pid_csv(pid_csv_path)
    mat = _pid_to_matrix(pid_rows, "synergy")

    fig, ax = plt.subplots(figsize=(8, 7))
    labels = [AGENT_SHORT[a] for a in AGENT_ORDER]

    im = ax.imshow(mat, cmap="YlOrRd", interpolation="nearest")
    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=9)
    ax.set_yticklabels(labels, fontsize=9)

    # Annotate cells
    for i in range(len(labels)):
        for j in range(len(labels)):
            val = mat[i, j]
            if i != j:
                color = "white" if val > mat.max() * 0.6 else "black"
                ax.text(j, i, f"{val:.3f}", ha="center", va="center",
                        fontsize=8, color=color)

    cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Synergy (bits)", fontsize=10)
    ax.set_title(title, fontsize=13, fontweight="bold")

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {output_path}")


# ---------------------------------------------------------------------------
# Plot 4: Three-condition PID comparison (side-by-side heatmaps)
# ---------------------------------------------------------------------------

def plot_pid_comparison(baseline_csv, nopersona_csv, persona_csv, output_path):
    """Side-by-side synergy heatmaps for all three conditions."""
    fig, axes = plt.subplots(1, 3, figsize=(22, 6))
    labels = [AGENT_SHORT[a] for a in AGENT_ORDER]

    configs = [
        (baseline_csv, "Baseline (Rule-Based)\nEC=0.041, p<0.001"),
        (nopersona_csv, "LLM No-Persona\nEC=0.005, p=0.744"),
        (persona_csv, "LLM Persona\nEC=0.032, p=0.002"),
    ]

    # Find global max for consistent color scale
    all_mats = []
    for csv_path, _ in configs:
        if Path(csv_path).exists():
            rows = _load_pid_csv(csv_path)
            all_mats.append(_pid_to_matrix(rows, "synergy"))
    vmax = max(m.max() for m in all_mats) if all_mats else 0.1

    for ax, (csv_path, title) in zip(axes, configs):
        if not Path(csv_path).exists():
            ax.set_title(f"{title}\n(not found)")
            continue

        rows = _load_pid_csv(csv_path)
        mat = _pid_to_matrix(rows, "synergy")

        im = ax.imshow(mat, cmap="YlOrRd", interpolation="nearest",
                        vmin=0, vmax=vmax)
        ax.set_xticks(range(len(labels)))
        ax.set_yticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
        ax.set_yticklabels(labels, fontsize=8)

        for i in range(len(labels)):
            for j in range(len(labels)):
                val = mat[i, j]
                if i != j:
                    color = "white" if val > vmax * 0.6 else "black"
                    ax.text(j, i, f"{val:.3f}", ha="center", va="center",
                            fontsize=7, color=color)

        ax.set_title(title, fontsize=11, fontweight="bold")

    cbar = fig.colorbar(im, ax=axes, fraction=0.02, pad=0.02)
    cbar.set_label("Synergy (bits)", fontsize=10)
    fig.suptitle("Pairwise PID Synergy: Three-Condition Comparison",
                 fontsize=14, fontweight="bold")
    fig.subplots_adjust(right=0.92, top=0.88)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {output_path}")


# ---------------------------------------------------------------------------
# Plot 5: EC bar chart comparison
# ---------------------------------------------------------------------------

def plot_ec_comparison(output_path):
    """Bar chart comparing EC across conditions."""
    conditions = ["Baseline\n(Rule-Based)", "LLM\nNo-Persona", "LLM\nPersona"]
    ec_values = [0.041, 0.005, 0.032]
    p_values = [0.000, 0.744, 0.002]
    colors = ["#1f77b4", "#aec7e8", "#d62728"]

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(conditions, ec_values, color=colors, edgecolor="black",
                  linewidth=0.5, width=0.5)

    for bar, pval in zip(bars, p_values):
        height = bar.get_height()
        sig = "***" if pval < 0.001 else "**" if pval < 0.01 else "*" if pval < 0.05 else "n.s."
        ax.text(bar.get_x() + bar.get_width() / 2., height + 0.001,
                f"EC={height:.3f}\np={pval:.3f} {sig}",
                ha="center", va="bottom", fontsize=10)

    ax.set_ylabel("Emergence Capacity (bits)", fontsize=12)
    ax.set_title("Emergence Capacity Across Market Conditions",
                 fontsize=13, fontweight="bold")
    ax.set_ylim(0, max(ec_values) * 1.35)
    ax.axhline(y=0, color="black", linewidth=0.5)
    ax.grid(True, axis="y", alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {output_path}")


# ---------------------------------------------------------------------------
# Plot 6: Detailed single-scenario plot
# ---------------------------------------------------------------------------

def plot_detailed(scenario_path, output_path):
    """Detailed 3-panel plot for a single scenario."""
    data = _load_scenario(scenario_path)

    fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
    periods = range(len(data["price_history"]))

    # Panel 1: Price vs Fundamental
    ax = axes[0]
    ax.plot(periods, data["price_history"], "g-o", label="Clearing Price",
            markersize=5, linewidth=2)
    ax.plot(periods, data["fundamental_history"], "r--", label="Fundamental Value",
            linewidth=2, alpha=0.7)
    ax.fill_between(periods, data["price_history"], data["fundamental_history"],
                    alpha=0.15, color="orange")
    ax.set_ylabel("Price ($)")

    model = data["summary"].get("model", "unknown")
    sid = data["summary"].get("scenario_id", "")
    ax.set_title(f"Market Simulation -- {model} -- {sid}",
                 fontsize=13, fontweight="bold")
    ax.legend(loc="upper left")
    ax.grid(True, alpha=0.3)

    # Panel 2: Volume
    ax = axes[1]
    ax.bar(periods, data["volume_history"], color="steelblue", alpha=0.7)
    ax.set_ylabel("Volume (units)")
    ax.set_title("Trading Volume per Period")
    ax.grid(True, alpha=0.3)

    # Panel 3: Agent order aggressiveness
    ax = axes[2]
    for t, period_data in enumerate(data["orders_log"]):
        for order in period_data["orders"]:
            aid = order["agent_id"]
            side_val = 1 if order["side"] == "buy" else -1
            color = ROLE_COLORS.get(aid, "gray")
            ax.scatter(t, side_val, color=color, s=40, alpha=0.7,
                       edgecolors="black", linewidths=0.3)

    legend_elements = [
        Line2D([0], [0], marker="o", color="w", label=AGENT_SHORT.get(aid, aid),
               markerfacecolor=ROLE_COLORS.get(aid, "gray"), markersize=8)
        for aid in AGENT_ORDER
    ]
    ax.legend(handles=legend_elements, loc="center left", bbox_to_anchor=(1.01, 0.5),
              fontsize=8, title="Agents")
    ax.set_yticks([-1, 1])
    ax.set_yticklabels(["SELL", "BUY"])
    ax.set_xlabel("Period")
    ax.set_title("Agent Order Directions")
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
    out = root / "outputs" / "market_plots"
    out.mkdir(exist_ok=True)

    baseline_dir = root / "outputs" / "market_baseline"
    nopersona_dir = root / "outputs" / "market_llama_no_persona"
    persona_dir = root / "outputs" / "market_llama_persona"

    # 1. Price comparison (scenario 001)
    plot_price_comparison(
        baseline_dir / "scenario_001.json",
        nopersona_dir / "scenario_001.json",
        persona_dir / "scenario_001.json",
        str(out / "price_comparison_s001.png"),
    )

    # 2. Multi-scenario grids
    for label, d in [("Baseline", baseline_dir),
                     ("LLM_NoPersona", nopersona_dir),
                     ("LLM_Persona", persona_dir)]:
        if d.exists():
            plot_multi_scenario(d, str(out / f"price_grid_{label}.png"),
                                title_prefix=label.replace("_", " "))

    # 3. Individual PID heatmaps
    for label, d in [("Baseline", baseline_dir),
                     ("LLM_NoPersona", nopersona_dir),
                     ("LLM_Persona", persona_dir)]:
        csv_path = d / "pid_analysis" / "market_pairwise_pid.csv"
        if csv_path.exists():
            plot_pid_heatmap(str(csv_path), str(out / f"pid_heatmap_{label}.png"),
                             title=f"PID Synergy: {label.replace('_', ' ')}")

    # 4. Side-by-side PID comparison
    plot_pid_comparison(
        str(baseline_dir / "pid_analysis" / "market_pairwise_pid.csv"),
        str(nopersona_dir / "pid_analysis" / "market_pairwise_pid.csv"),
        str(persona_dir / "pid_analysis" / "market_pairwise_pid.csv"),
        str(out / "pid_comparison_3conditions.png"),
    )

    # 5. EC bar chart
    plot_ec_comparison(str(out / "ec_comparison.png"))

    # 6. Detailed plots for persona scenarios 1 and 7 (best diversity)
    for sid in ["001", "007"]:
        fpath = persona_dir / f"scenario_{sid}.json"
        if fpath.exists():
            plot_detailed(str(fpath), str(out / f"detailed_persona_s{sid}.png"))
