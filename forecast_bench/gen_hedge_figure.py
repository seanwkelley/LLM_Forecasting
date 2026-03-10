"""Hedging figure: uncertainty rating vs shift, split by confidence + rating distribution."""
import json, sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np

from forecast_bench.analysis_full import load_question_jsons

plt.rcParams.update({"font.family": "Arial", "font.size": 10, "figure.dpi": 300})

BLUE, ORANGE, VERMILLION, GREEN = "#0072B2", "#E69F00", "#D55E00", "#009E73"

BASE = Path(__file__).parent.parent
CAUSAL = BASE / "outputs" / "sensitivity" / "causal"
OUT = BASE / "paper" / "figures" / "supplementary"

MODEL_DIRS = {
    "Llama-3.1-8B":  ("llama-8b",  CAUSAL / "llama_one_turn"),
    "Llama-3.3-70B": ("llama-70b", CAUSAL / "70b_one_turn"),
    "DeepSeek-V3":   ("deepseek",  CAUSAL / "deepseek_one_turn"),
}
MODEL_COLORS = {"Llama-3.1-8B": BLUE, "Llama-3.3-70B": ORANGE, "DeepSeek-V3": VERMILLION}


def main():
    with open(CAUSAL / "uncertainty_judge_ratings.json") as f:
        judge_ratings = json.load(f)

    runs = {}
    for display_name, (judge_key, d) in MODEL_DIRS.items():
        q_data = load_question_jsons(d)
        runs[display_name] = (judge_key, q_data)

    # Collect all data points
    all_data = []
    for display_name, (judge_key, q_data) in runs.items():
        for qid, qd in q_data.items():
            init_p = qd.get("initial_probability")
            for i, pr in enumerate(qd.get("probe_results", [])):
                if not pr.get("success"):
                    continue
                up = pr.get("updated_probability")
                if up is None or init_p is None:
                    continue
                key = f"{judge_key}|{qid}|{i}"
                if key not in judge_ratings:
                    continue
                rating = judge_ratings[key].get("rating")
                if rating is None:
                    continue
                shift = abs(up - init_p)
                dist = abs(up - 0.5)
                all_data.append({
                    "model": display_name,
                    "rating": rating,
                    "dist_from_05": dist,
                    "shift": shift,
                })

    print(f"Total data points: {len(all_data)}")

    # ═══════════════════════════════════════════════════════════════════
    # 2-panel figure:
    # (a) Mean shift by rating, split by high/low confidence
    # (b) Rating distribution by model
    # ═══════════════════════════════════════════════════════════════════

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    fig.patch.set_facecolor("white")

    # ── (a) Mean shift by rating, split by high/low confidence ──
    conf_split = 0.2

    for display_name in runs:
        model_data = [d for d in all_data if d["model"] == display_name]

        for conf_label, conf_filter, ls in [
            ("confident", lambda d: d["dist_from_05"] >= conf_split, "-"),
            ("uncertain", lambda d: d["dist_from_05"] < conf_split, "--"),
        ]:
            by_rating = defaultdict(list)
            for d in model_data:
                if conf_filter(d) and d["rating"] in [2, 3, 4]:
                    by_rating[d["rating"]].append(d["shift"])

            ratings = sorted(by_rating.keys())
            means = [np.mean(by_rating[r]) for r in ratings]
            sems = [np.std(by_rating[r]) / np.sqrt(len(by_rating[r])) for r in ratings]

            ax1.errorbar(ratings, means, yerr=sems, fmt=f"o{ls}",
                         color=MODEL_COLORS[display_name], markersize=7, linewidth=2,
                         capsize=4, alpha=0.8)

    legend_elements = [
        Line2D([0], [0], color="gray", linestyle="-", linewidth=2, label="Confident (dist > 0.2)"),
        Line2D([0], [0], color="gray", linestyle="--", linewidth=2, label="Uncertain (dist < 0.2)"),
        Line2D([0], [0], color=BLUE, marker="o", linestyle="", markersize=7, label="Llama-3.1-8B"),
        Line2D([0], [0], color=ORANGE, marker="o", linestyle="", markersize=7, label="Llama-3.3-70B"),
        Line2D([0], [0], color=VERMILLION, marker="o", linestyle="", markersize=7, label="DeepSeek-V3"),
    ]
    ax1.legend(handles=legend_elements, fontsize=8, frameon=False, loc="upper right")
    ax1.set_xlabel("Uncertainty Rating (2=Confident, 4=Hedging)")
    ax1.set_ylabel("Mean |Probability Shift|")
    ax1.set_xticks([2, 3, 4])
    ax1.text(-0.08, 1.05, "(a)", transform=ax1.transAxes, fontsize=14, fontweight="bold")

    # ── (b) Rating distribution by model ──
    all_ratings = [1, 2, 3, 4, 5]
    x = np.arange(len(all_ratings))
    bar_w = 0.25

    for i, display_name in enumerate(runs):
        model_data = [d for d in all_data if d["model"] == display_name]
        total = len(model_data)
        fracs = [len([d for d in model_data if d["rating"] == r]) / total * 100
                 for r in all_ratings]
        ax2.bar(x + (i - 1) * bar_w, fracs, bar_w,
                color=MODEL_COLORS[display_name], alpha=0.7, label=display_name)

    ax2.set_xticks(x)
    ax2.set_xticklabels(all_ratings)
    ax2.set_xlabel("Uncertainty Rating")
    ax2.set_ylabel("% of Responses")
    ax2.legend(fontsize=9, frameon=False)
    ax2.text(-0.08, 1.05, "(b)", transform=ax2.transAxes, fontsize=14, fontweight="bold")

    plt.tight_layout()
    for ext in ["png", "pdf"]:
        fig.savefig(str(OUT / f"hedge_vs_confidence.{ext}"),
                    dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("\nSaved hedge_vs_confidence")


if __name__ == "__main__":
    main()
