"""Generate Elo vs probability extremity scatter plot.

Outputs:
    paper/figures/supplementary/elo_vs_extremity.pdf / .png
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

sys.path.insert(0, str(Path(__file__).parent.parent))
from forecast_bench.analysis_full import load_question_jsons

BASE = Path(__file__).parent.parent
CAUSAL_DIR = BASE / "outputs" / "sensitivity" / "causal"
FIGURES_DIR = BASE / "paper" / "figures" / "supplementary"

MODEL_DIRS = {
    "llama-8b": CAUSAL_DIR / "llama_neutral",
    "llama-70b": CAUSAL_DIR / "llama_70b_neutral",
    "deepseek": CAUSAL_DIR / "deepseek_neutral",
    "qwen": CAUSAL_DIR / "qwen_neutral",
    "gemini": CAUSAL_DIR / "gemini_fl_neutral",
    "gpt-oss": CAUSAL_DIR / "gpt_oss_neutral",
    "qwen-32b": CAUSAL_DIR / "qwen_32b_neutral",
}

# Match paper figure style
plt.rcParams.update({
    "font.family": "Arial",
    "font.size": 12,
    "axes.spines.top": False,
    "axes.spines.right": False,
})


def main():
    elo_data = json.loads(
        (CAUSAL_DIR / "difficulty_elo.json").read_text(encoding="utf-8")
    )
    elo_ratings = elo_data["elo_ratings"]

    # Mean initial prob across models
    q_probs: dict[str, list[float]] = defaultdict(list)
    for mname, mdir in MODEL_DIRS.items():
        qd = load_question_jsons(mdir)
        for qid, d in qd.items():
            if d.get("initial_probability") is not None:
                q_probs[qid].append(d["initial_probability"])

    # Build arrays
    qids = [q for q in elo_ratings if q in q_probs]
    elos = np.array([elo_ratings[q] for q in qids])
    extremity = np.array([abs(np.mean(q_probs[q]) - 0.5) for q in qids])

    rho, pval = stats.spearmanr(extremity, elos)

    fig, ax = plt.subplots(figsize=(6, 5))

    ax.scatter(extremity, elos, alpha=0.6, s=40, color="#0072B2", edgecolors="none")

    # Trend line
    z = np.polyfit(extremity, elos, 1)
    x_line = np.linspace(0, 0.5, 100)
    ax.plot(x_line, np.polyval(z, x_line), color="#D55E00", linewidth=2.5,
            linestyle="--", zorder=0)

    # Baseline at 1500
    ax.axhline(1500, color="#999999", linewidth=1, linestyle=":", zorder=0)

    ax.set_xlabel(r"$|p_0 - 0.5|$  (distance from maximum uncertainty)")
    ax.set_ylabel("Question Elo Difficulty Rating")
    ax.set_xlim(-0.01, 0.51)

    # Stats in top-left, no box
    ax.text(0.03, 0.97, f"$\\rho = {rho:.3f}$ ($p = {pval:.3f}$)",
            transform=ax.transAxes, ha="left", va="top", fontsize=11)

    plt.tight_layout()
    for ext in ["png", "pdf"]:
        fig.savefig(str(FIGURES_DIR / f"elo_vs_extremity.{ext}"),
                    dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("Saved elo_vs_extremity.png/pdf")


if __name__ == "__main__":
    main()
