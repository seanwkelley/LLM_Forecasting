#!/usr/bin/env python3
"""
Analyze factor ranking results — correlate stated importance ranks with DAG topology.

Computes:
- Spearman rank correlation: stated rank vs betweenness centrality
- Spearman rank correlation: stated rank vs path relevance
- Per-model and pooled results
- Supplementary figure: per-model correlation dot plot

Usage:
    python -m forecast_bench.analyze_factor_ranking
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats as sp_stats

sys.path.insert(0, str(Path(__file__).parent.parent))

BASE = Path(__file__).parent.parent
CAUSAL_DIR = BASE / "outputs" / "sensitivity" / "causal"
FIGURES_DIR = BASE / "paper" / "figures" / "supplementary"

MODEL_DIRS = {
    "Llama-3.1-8B": "llama_neutral_factor_ranking",
    "Llama-3.3-70B": "llama_70b_neutral_factor_ranking",
    "DeepSeek-V3": "deepseek_neutral_factor_ranking",
    "Qwen3-235B": "qwen_neutral_factor_ranking",
    "Gemini-Flash-Lite": "gemini_fl_neutral_factor_ranking",
    "GPT-OSS-120B": "gpt_oss_neutral_factor_ranking",
    "Qwen3-32B": "qwen_32b_neutral_factor_ranking",
}

COLORS = {
    "Llama-3.1-8B": "#E69F00",
    "Llama-3.3-70B": "#0072B2",
    "DeepSeek-V3": "#D55E00",
    "Qwen3-235B": "#009E73",
    "Gemini-Flash-Lite": "#CC79A7",
    "GPT-OSS-120B": "#882255",
    "Qwen3-32B": "#56B4E9",
}

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 11,
    "axes.labelsize": 12,
    "axes.titlesize": 13,
    "legend.fontsize": 10,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.1,
    "mathtext.default": "regular",
    "axes.spines.top": False,
    "axes.spines.right": False,
})


def load_ranking_results(model_name: str) -> list[dict]:
    """Load all question results for a model."""
    dir_name = MODEL_DIRS.get(model_name)
    if not dir_name:
        return []
    results_dir = CAUSAL_DIR / dir_name / "question_results"
    if not results_dir.exists():
        return []

    results = []
    for f in sorted(results_dir.glob("q_*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        if data.get("matches") and len(data["matches"]) >= 3:
            results.append(data)
    return results


def compute_correlations(results: list[dict]) -> dict:
    """Compute per-question and pooled rank correlations."""
    per_q_rho_betw = []
    per_q_rho_pr = []
    all_ranks = []
    all_betw = []
    all_pr = []

    for r in results:
        matches = r["matches"]
        if len(matches) < 3:
            continue

        ranks = [m["rank"] for m in matches]
        betw = [m["betweenness"] for m in matches]
        pr = [m.get("path_relevance", 0) for m in matches]

        # Stated rank is 1=most important, but betweenness is higher=more important
        # So we expect NEGATIVE correlation (rank 1 → high betweenness)
        rho_b, _ = sp_stats.spearmanr(ranks, betw)
        if not np.isnan(rho_b):
            per_q_rho_betw.append(rho_b)

        rho_p, _ = sp_stats.spearmanr(ranks, pr)
        if not np.isnan(rho_p):
            per_q_rho_pr.append(rho_p)

        all_ranks.extend(ranks)
        all_betw.extend(betw)
        all_pr.extend(pr)

    # Pooled correlation
    pooled_rho_betw, pooled_p_betw = sp_stats.spearmanr(all_ranks, all_betw) if len(all_ranks) >= 3 else (None, None)
    pooled_rho_pr, pooled_p_pr = sp_stats.spearmanr(all_ranks, all_pr) if len(all_ranks) >= 3 else (None, None)

    return {
        "n_questions": len(results),
        "n_matched_questions": len(per_q_rho_betw),
        "n_total_matches": len(all_ranks),
        "mean_cosine_sim": round(float(np.mean([
            m["cosine_similarity"] for r in results for m in r["matches"]
        ])), 4) if results else None,
        "per_question_rho_betweenness": {
            "mean": round(float(np.mean(per_q_rho_betw)), 4) if per_q_rho_betw else None,
            "median": round(float(np.median(per_q_rho_betw)), 4) if per_q_rho_betw else None,
            "n": len(per_q_rho_betw),
        },
        "per_question_rho_path_relevance": {
            "mean": round(float(np.mean(per_q_rho_pr)), 4) if per_q_rho_pr else None,
            "median": round(float(np.median(per_q_rho_pr)), 4) if per_q_rho_pr else None,
            "n": len(per_q_rho_pr),
        },
        "pooled_rho_betweenness": round(float(pooled_rho_betw), 4) if pooled_rho_betw is not None else None,
        "pooled_p_betweenness": round(float(pooled_p_betw), 6) if pooled_p_betw is not None else None,
        "pooled_rho_path_relevance": round(float(pooled_rho_pr), 4) if pooled_rho_pr is not None else None,
        "pooled_p_path_relevance": round(float(pooled_p_pr), 6) if pooled_p_pr is not None else None,
    }


def generate_figure(all_correlations: dict[str, dict]):
    """Generate dot plot of per-model rank correlations."""
    models = [m for m in COLORS if m in all_correlations]
    if not models:
        print("  [SKIP] No data for figure")
        return

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))

    metrics = [
        ("pooled_rho_betweenness", "pooled_p_betweenness",
         "Stated Rank vs Betweenness rho"),
        ("pooled_rho_path_relevance", "pooled_p_path_relevance",
         "Stated Rank vs Path Relevance rho"),
    ]

    for ax, (rho_key, p_key, title) in zip(axes, metrics):
        for i, model in enumerate(models):
            corr = all_correlations[model]
            rho = corr.get(rho_key)
            p = corr.get(p_key)
            if rho is None:
                continue

            color = COLORS[model]
            ax.plot(rho, i, "o", color=color, markersize=10, zorder=5)

            stars = ""
            if p is not None:
                stars = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
            ax.text(rho + 0.02, i, stars, va="center", fontsize=10, fontweight="bold")

        ax.axvline(x=0, color="#333", linewidth=1, linestyle="--", alpha=0.5)
        ax.set_yticks(range(len(models)))
        ax.set_yticklabels([m.replace("-", "\n", 1) for m in models], fontsize=9)
        ax.set_xlabel(title)

    # Panel labels
    for i, ax in enumerate(axes):
        label = chr(ord("a") + i)
        ax.text(-0.02, 1.02, f"({label})", transform=ax.transAxes,
                fontsize=14, fontweight="bold", va="bottom", ha="right")

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(FIGURES_DIR / f"factor_ranking.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("  Saved supplementary/factor_ranking.pdf/png")


def main():
    print("Factor Ranking Analysis")
    print("=" * 60)

    all_correlations = {}

    for model_name in COLORS:
        results = load_ranking_results(model_name)
        if not results:
            print(f"  {model_name}: no data")
            continue

        corr = compute_correlations(results)
        all_correlations[model_name] = corr

        print(f"\n  {model_name}: {corr['n_matched_questions']} questions, "
              f"{corr['n_total_matches']} matches")
        print(f"    Mean cosine similarity: {corr['mean_cosine_sim']}")
        print(f"    Pooled rho (betweenness):    {corr['pooled_rho_betweenness']} "
              f"(p={corr['pooled_p_betweenness']})")
        print(f"    Pooled rho (path relevance): {corr['pooled_rho_path_relevance']} "
              f"(p={corr['pooled_p_path_relevance']})")
        print(f"    Per-Q mean rho (betweenness): {corr['per_question_rho_betweenness']['mean']}")
        print(f"    Per-Q mean rho (path rel.):   {corr['per_question_rho_path_relevance']['mean']}")

    # Save JSON
    out_path = CAUSAL_DIR / "factor_ranking_analysis.json"
    out_path.write_text(json.dumps(all_correlations, indent=2), encoding="utf-8")
    print(f"\nSaved: {out_path}")

    # Generate figure
    if all_correlations:
        generate_figure(all_correlations)


if __name__ == "__main__":
    main()
