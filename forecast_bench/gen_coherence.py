#!/usr/bin/env python3
"""Combined coherence figure: 4 panels testing reasoning-behavior alignment.

All panels use LME results from lme_results.json (fit in R via lme_analysis.R).
Panels (a)-(b) use old-prompt data (5 models with judge ratings).
Panels (c)-(d) use neutral-prompt / embedding data.
"""

import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from collections import defaultdict
from pathlib import Path

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 15,
    "axes.labelsize": 16,
    "axes.titlesize": 17,
    "legend.fontsize": 12,
    "xtick.labelsize": 13,
    "ytick.labelsize": 13,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.1,
    "mathtext.default": "regular",
    "axes.spines.top": False,
    "axes.spines.right": False,
})

BASE = Path(__file__).parent.parent
CAUSAL_DIR = BASE / "outputs" / "sensitivity" / "causal"
OUT = BASE / "paper" / "figures"

COLORS = {
    "Llama-3.1-8B": "#E69F00",
    "Llama-3.3-70B": "#0072B2",
    "DeepSeek-V3": "#D55E00",
    "Qwen3-235B": "#009E73",
    "Gemini-Flash-Lite": "#CC79A7",
    "GPT-OSS-120B": "#882255",
    "Qwen3-32B": "#56B4E9",
}

JUDGE_KEY_MAP = {"Llama-3.1-8B": "llama-8b", "Llama-3.3-70B": "llama-70b",
                 "DeepSeek-V3": "deepseek", "Qwen3-235B": "qwen",
                 "Gemini-Flash-Lite": "gemini", "GPT-OSS-120B": "gpt-oss"}


def _stars(p):
    if p < 0.001:
        return "***"
    elif p < 0.01:
        return "**"
    elif p < 0.05:
        return "*"
    return "n.s."


def _fmt_lme(coef, p, ci_lower=None, ci_upper=None):
    """Format LME result as annotation string."""
    s = _stars(p)
    base = f"\u03b2 = {coef:.3f}{s}"
    if ci_lower is not None and ci_upper is not None:
        base += f"\n[{ci_lower:.3f}, {ci_upper:.3f}]"
    return base


def panel_a_reasoning(ax, runs, lme_results):
    """Stated-impact rating vs |logit shift| — boxplots with LME β."""
    path = CAUSAL_DIR / "reasoning_judge_ratings.json"
    if not path.exists():
        ax.text(0.5, 0.5, "No reasoning ratings", transform=ax.transAxes, ha="center")
        return

    ratings = json.loads(path.read_text(encoding="utf-8"))
    by_rating = defaultdict(list)
    for display_name, (rows, q_data) in runs.items():
        jk = JUDGE_KEY_MAP.get(display_name)
        if not jk:
            continue
        for qid, qd in q_data.items():
            init_p = qd.get("initial_probability")
            for i, pr in enumerate(qd.get("probe_results", [])):
                if not pr.get("success") or init_p is None:
                    continue
                up = pr.get("updated_probability")
                if up is None:
                    continue
                key = f"{jk}|{qid}|{i}"
                if key not in ratings:
                    continue
                r = ratings[key].get("rating")
                if r is not None and 1 <= r <= 5:
                    eps = 1e-4
                    p0 = max(eps, min(1 - eps, init_p))
                    p1 = max(eps, min(1 - eps, up))
                    lo_shift = abs(np.log(p1 / (1 - p1)) - np.log(p0 / (1 - p0)))
                    by_rating[r].append(lo_shift)

    show = [1, 2, 3, 4, 5]
    box_data = [by_rating[r] for r in show]
    box_labels = [f"{r}\n(n={len(by_rating[r])})" for r in show]

    bp = ax.boxplot(box_data, tick_labels=box_labels, patch_artist=True,
                    widths=0.5, showfliers=False)
    for patch in bp["boxes"]:
        patch.set_facecolor("#332288")
        patch.set_alpha(0.5)
    for i, vals in enumerate(box_data):
        if vals:
            ax.scatter([i + 1], [np.mean(vals)], marker="D", color="black", s=40, zorder=5)

    ax.set_ylabel("|Log-Odds Shift|")
    ax.set_xlabel("Stated-Impact Rating", fontsize=16)

    # LME annotation
    coh = lme_results.get("coherence_reasoning")
    if coh:
        fe = coh.get("fixed_effects", {})
        rating_fe = fe.get("rating")
        if rating_fe:
            txt = _fmt_lme(rating_fe["coef"], rating_fe["p"],
                           rating_fe.get("ci_lower"), rating_fe.get("ci_upper"))
            ax.text(0.95, 0.95, txt, transform=ax.transAxes,
                    ha="right", va="top", fontsize=12,
                    bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.8))


def panel_b_uncertainty(ax, runs, lme_results):
    """Uncertainty rating vs |logit shift| — boxplots with LME β."""
    path = CAUSAL_DIR / "uncertainty_judge_ratings.json"
    if not path.exists():
        ax.text(0.5, 0.5, "No uncertainty ratings", transform=ax.transAxes, ha="center")
        return

    ratings = json.loads(path.read_text(encoding="utf-8"))
    by_unc = defaultdict(list)
    for display_name, (rows, q_data) in runs.items():
        jk = JUDGE_KEY_MAP.get(display_name)
        if not jk:
            continue
        for qid, qd in q_data.items():
            init_p = qd.get("initial_probability")
            for i, pr in enumerate(qd.get("probe_results", [])):
                if not pr.get("success") or init_p is None:
                    continue
                up = pr.get("updated_probability")
                if up is None:
                    continue
                key = f"{jk}|{qid}|{i}"
                if key not in ratings:
                    continue
                r = ratings[key].get("rating")
                if r is not None and r in (2, 3, 4):
                    eps = 1e-4
                    p0 = max(eps, min(1 - eps, init_p))
                    p1 = max(eps, min(1 - eps, up))
                    lo_shift = abs(np.log(p1 / (1 - p1)) - np.log(p0 / (1 - p0)))
                    by_unc[r].append(lo_shift)

    label_names = {2: "Confident", 3: "Mixed", 4: "Hedging"}
    show = [2, 3, 4]
    box_data = [by_unc[r] for r in show]
    box_labels = [f"{label_names[r]}\n(n={len(by_unc[r])})" for r in show]

    bp = ax.boxplot(box_data, tick_labels=box_labels, patch_artist=True,
                    widths=0.5, showfliers=False)
    for patch in bp["boxes"]:
        patch.set_facecolor("#332288")
        patch.set_alpha(0.5)
    for i, vals in enumerate(box_data):
        if vals:
            ax.scatter([i + 1], [np.mean(vals)], marker="D", color="black", s=40, zorder=5)

    ax.set_ylabel("|Log-Odds Shift|")
    ax.set_xlabel("Uncertainty in Reasoning", fontsize=16)

    # LME annotation — show Mixed and Hedging contrasts vs Confident (reference)
    coh = lme_results.get("coherence_uncertainty")
    if coh:
        fe = coh.get("fixed_effects", {})
        # Look for the categorical contrasts
        mixed_fe = fe.get("uncertaintyMixed")
        hedging_fe = fe.get("uncertaintyHedging")
        parts = []
        if mixed_fe:
            parts.append(f"Mixed: \u03b2={mixed_fe['coef']:.3f}{_stars(mixed_fe['p'])}")
        if hedging_fe:
            parts.append(f"Hedging: \u03b2={hedging_fe['coef']:.3f}{_stars(hedging_fe['p'])}")
        if parts:
            ax.text(0.95, 0.95, "\n".join(parts), transform=ax.transAxes,
                    ha="right", va="top", fontsize=11,
                    bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.8))


def panel_c_bayesian(ax, runs, lme_results):
    """Bayesian coherence: pooled scatter of log-odds shift vs initial prob, with LME β."""
    all_p0 = []
    all_lo_shift = []

    for name, (rows, q_data) in runs.items():
        for r in rows:
            if not r.get("success") or r.get("updated_probability") is None:
                continue
            initial = r.get("initial_probability")
            updated = r.get("updated_probability")
            if initial is None or updated is None:
                continue
            initial = max(0.01, min(0.99, initial))
            updated = max(0.01, min(0.99, updated))
            lo_shift = np.log(updated / (1 - updated)) - np.log(initial / (1 - initial))
            all_p0.append(initial)
            all_lo_shift.append(lo_shift)

    if len(all_p0) < 20:
        return

    p0_arr = np.array(all_p0)
    lo_arr = np.array(all_lo_shift)

    ax.scatter(all_p0, all_lo_shift, alpha=0.08, s=8, color="#332288", edgecolors="none")
    ax.axhline(0, color="#999", linestyle="--", linewidth=1, zorder=0)

    # LME regression line (using initial_logit as predictor)
    coh = lme_results.get("coherence_bayesian")
    if coh:
        fe = coh.get("fixed_effects", {})
        logit_fe = fe.get("initial_logit")
        intercept_fe = fe.get("(Intercept)")
        if logit_fe and intercept_fe:
            b0 = intercept_fe["coef"]
            b1 = logit_fe["coef"]
            # Plot LME regression line (transform x-axis from prob to logit)
            x_prob = np.linspace(0.02, 0.98, 200)
            x_logit = np.log(x_prob / (1 - x_prob))
            y_pred = b0 + b1 * x_logit
            ax.plot(x_prob, y_pred, color="#332288", linewidth=2.5, zorder=5)

            txt = _fmt_lme(b1, logit_fe["p"],
                           logit_fe.get("ci_lower"), logit_fe.get("ci_upper"))
            ax.text(0.95, 0.95, txt, transform=ax.transAxes,
                    ha="right", va="top", fontsize=12,
                    bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.8))
    else:
        # Fallback: simple linear regression
        from scipy.stats import pearsonr
        slope, intercept = np.polyfit(p0_arr, lo_arr, 1)
        r, p = pearsonr(p0_arr, lo_arr)
        x_line = np.linspace(0, 1, 100)
        ax.plot(x_line, slope * x_line + intercept, color="#332288", linewidth=2.5, zorder=5)
        ax.text(0.95, 0.95, f"r = {r:.2f}{_stars(p)}", transform=ax.transAxes,
                ha="right", va="top", fontsize=14)

    ax.set_xlabel("Initial Probability")
    ax.set_ylabel("Log-Odds Shift")
    ax.set_xlim(0, 1)
    q01, q99 = np.percentile(lo_arr, [1, 99])
    ax.set_ylim(q01 * 1.2, q99 * 1.2)


def panel_d_embeddings(ax, runs, lme_results):
    """Reasoning embedding separation: structural vs control, with LME β."""
    from forecast_bench.generate_figures import (
        _EMBED_PROBE_NORMALIZE, _IMPORTANCE_TIER,
    )

    emb_path = CAUSAL_DIR / "reasoning_embeddings.npz"
    keys_path = CAUSAL_DIR / "reasoning_embeddings_keys.json"

    if not (emb_path.exists() and keys_path.exists()):
        ax.text(0.5, 0.5, "No embeddings", transform=ax.transAxes, ha="center")
        return

    keys = json.loads(keys_path.read_text(encoding="utf-8"))
    embeddings = np.load(str(emb_path))["embeddings"]

    CONTROL_TYPES = {"irrelevant"}
    model_key_map = {"Llama-3.1-8B": "llama-8b", "Llama-3.3-70B": "llama-70b",
                     "DeepSeek-V3": "deepseek", "Qwen3-235B": "qwen",
                     "Gemini-Flash-Lite": "gemini"}

    model_q_index = defaultdict(list)
    for i, k in enumerate(keys):
        parts = k.split("|")
        if len(parts) < 4:
            continue
        pt = _EMBED_PROBE_NORMALIZE.get(parts[1], parts[1])
        if pt not in _IMPORTANCE_TIER:
            continue
        is_control = pt in CONTROL_TYPES
        model_q_index[(parts[3], parts[0])].append((is_control, i))

    def _cosine_sim(a, b):
        dot = np.dot(a, b)
        na, nb = np.linalg.norm(a), np.linalg.norm(b)
        return dot / (na * nb) if na > 0 and nb > 0 else 0.0

    all_struct, all_control = [], []
    for name in runs.keys():
        mk = model_key_map.get(name)
        if not mk:
            continue
        model_questions = set(qid for (m, qid) in model_q_index if m == mk)
        for qid in model_questions:
            entries = model_q_index[(mk, qid)]
            ctrl_idx = [idx for is_ctrl, idx in entries if is_ctrl]
            struct_idx = [idx for is_ctrl, idx in entries if not is_ctrl]
            if len(ctrl_idx) < 2 or len(struct_idx) < 2:
                continue
            rng = np.random.RandomState(42)
            pairs_s = [(struct_idx[a], struct_idx[b])
                       for a in range(len(struct_idx)) for b in range(a + 1, len(struct_idx))]
            if len(pairs_s) > 50:
                sel = rng.choice(len(pairs_s), 50, replace=False)
                pairs_s = [pairs_s[p] for p in sel]
            s_sims = [_cosine_sim(embeddings[a], embeddings[b]) for a, b in pairs_s]
            pairs_c = [(ctrl_idx[a], ctrl_idx[b])
                       for a in range(len(ctrl_idx)) for b in range(a + 1, len(ctrl_idx))]
            c_sims = [_cosine_sim(embeddings[a], embeddings[b]) for a, b in pairs_c]
            if s_sims:
                all_struct.append(np.mean(s_sims))
            if c_sims:
                all_control.append(np.mean(c_sims))

    if not all_struct or not all_control:
        ax.text(0.5, 0.5, "Insufficient data", transform=ax.transAxes, ha="center")
        return

    s_mean = np.mean(all_struct)
    c_mean = np.mean(all_control)
    s_se = np.std(all_struct, ddof=1) / np.sqrt(len(all_struct))
    c_se = np.std(all_control, ddof=1) / np.sqrt(len(all_control))

    ax.bar([0, 1], [s_mean, c_mean],
           yerr=[1.96 * s_se, 1.96 * c_se],
           color=["#332288", "#BBBBBB"], alpha=0.8,
           capsize=5, error_kw={"linewidth": 1.5}, width=0.6)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["Targeted\nProbes", "Irrelevant\nProbes"], fontsize=12)
    ax.set_ylabel("Within-Question\nCosine Similarity")

    # LME annotation
    coh = lme_results.get("coherence_embedding")
    if coh:
        fe = coh.get("fixed_effects", {})
        struct_fe = fe.get("is_structuralStructural")
        if struct_fe:
            txt = _fmt_lme(struct_fe["coef"], struct_fe["p"],
                           struct_fe.get("ci_lower"), struct_fe.get("ci_upper"))
            y_top = max(s_mean + 1.96 * s_se, c_mean + 1.96 * c_se) + 0.003
            ax.plot([0, 0, 1, 1], [y_top, y_top + 0.002, y_top + 0.002, y_top],
                    color="black", linewidth=0.8)
            ax.text(0.5, y_top + 0.003, _stars(struct_fe["p"]),
                    ha="center", va="bottom", fontsize=14, fontweight="bold")
            ax.text(0.95, 0.95, txt, transform=ax.transAxes,
                    ha="right", va="top", fontsize=12,
                    bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.8))
    else:
        # Fallback: Mann-Whitney
        from scipy.stats import mannwhitneyu
        _, p = mannwhitneyu(all_struct, all_control, alternative="two-sided")
        stars = _stars(p)
        y_top = max(s_mean + 1.96 * s_se, c_mean + 1.96 * c_se) + 0.003
        ax.plot([0, 0, 1, 1], [y_top, y_top + 0.002, y_top + 0.002, y_top],
                color="black", linewidth=0.8)
        ax.text(0.5, y_top + 0.003, stars, ha="center", va="bottom",
                fontsize=14, fontweight="bold")

    ax.set_ylim(bottom=0.55, top=0.85)


def main():
    from forecast_bench.generate_figures import _load_all_runs
    runs = _load_all_runs()

    # Load LME results
    lme_path = CAUSAL_DIR / "lme_results.json"
    if lme_path.exists():
        lme_results = json.loads(lme_path.read_text(encoding="utf-8"))
        print(f"Loaded LME results: {[k for k in lme_results if k.startswith('coherence')]}")
    else:
        print("No LME results found — using fallback statistics")
        lme_results = {}

    fig, axes = plt.subplots(2, 2, figsize=(14, 11),
                              gridspec_kw={"hspace": 0.35, "wspace": 0.35})
    ax_a, ax_b = axes[0]
    ax_c, ax_d = axes[1]

    panel_a_reasoning(ax_a, runs, lme_results)
    panel_b_uncertainty(ax_b, runs, lme_results)
    panel_c_bayesian(ax_c, runs, lme_results)
    panel_d_embeddings(ax_d, runs, lme_results)

    for ax, label in zip([ax_a, ax_b, ax_c, ax_d], ["(a)", "(b)", "(c)", "(d)"]):
        ax.text(-0.02, 1.02, label, transform=ax.transAxes,
                fontsize=16, fontweight="bold", va="bottom", ha="right")

    OUT.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT / f"coherence.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("Saved coherence.png/pdf")


if __name__ == "__main__":
    main()
