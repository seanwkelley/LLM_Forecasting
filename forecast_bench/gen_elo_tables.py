"""Generate LaTeX tables for Elo difficulty analysis.

Outputs:
    paper/figures/elo_exemplars_table.tex
    paper/figures/elo_regression_table.tex
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))
from forecast_bench.analysis_full import load_question_jsons

BASE = Path(__file__).parent.parent
CAUSAL_DIR = BASE / "outputs" / "sensitivity" / "causal"
FIGURES_DIR = BASE / "paper" / "figures"

MODEL_DIRS = {
    "llama-8b": CAUSAL_DIR / "llama_one_turn",
    "llama-70b": CAUSAL_DIR / "70b_one_turn",
    "deepseek": CAUSAL_DIR / "deepseek_one_turn",
    "qwen": CAUSAL_DIR / "qwen_one_turn",
    "gemini": CAUSAL_DIR / "gemini_flash_lite_one_turn",
}


def shorten(text: str, maxlen: int = 72) -> str:
    for ch in ("%", "&", "_", "$", "#"):
        text = text.replace(ch, "\\" + ch)
    if len(text) > maxlen:
        text = text[: maxlen - 3] + "..."
    return text


def main():
    elo_data = json.loads(
        (CAUSAL_DIR / "difficulty_elo.json").read_text(encoding="utf-8")
    )
    elo_ratings = elo_data["elo_ratings"]
    detail = elo_data["ratings_detail"]

    # Mean initial prob across models
    q_probs: dict[str, list[float]] = defaultdict(list)
    for mname, mdir in MODEL_DIRS.items():
        qd = load_question_jsons(mdir)
        for qid, d in qd.items():
            if d.get("initial_probability") is not None:
                q_probs[qid].append(d["initial_probability"])

    sorted_q = sorted(elo_ratings.items(), key=lambda x: x[1], reverse=True)

    # ── Table 1: Exemplar questions ──────────────────────────────────────
    lines = [
        r"\begin{table*}[t]",
        r"\centering",
        r"\small",
        r"\begin{tabular}{clcc}",
        r"\toprule",
        r"\textbf{Rank} & \textbf{Question} & \textbf{Elo} & \textbf{Mean $p_0$} \\",
        r"\midrule",
        r"\multicolumn{4}{l}{\textit{Hardest questions}} \\",
    ]
    for i, (qid, elo) in enumerate(sorted_q[:5], 1):
        mp = np.mean(q_probs[qid])
        txt = shorten(detail[qid]["question"])
        lines.append(f"{i} & {txt} & {elo:.0f} & {mp:.2f} \\\\")

    lines.append(r"\midrule")
    lines.append(r"\multicolumn{4}{l}{\textit{Easiest questions}} \\")

    for i, (qid, elo) in enumerate(sorted_q[-5:][::-1], 96):
        mp = np.mean(q_probs[qid])
        txt = shorten(detail[qid]["question"])
        lines.append(f"{i} & {txt} & {elo:.0f} & {mp:.2f} \\\\")

    lines += [
        r"\bottomrule",
        r"\end{tabular}",
        r"\caption{Exemplar questions at the extremes of the Elo difficulty ranking. "
        r"Mean $p_0$ is averaged across all five models. Hard questions involve "
        r"geopolitical contingencies and long-horizon technology forecasts with "
        r"opaque causal mechanisms; easy questions involve routine economic "
        r"indicators and well-precedented events.}",
        r"\label{tab:elo_exemplars}",
        r"\end{table*}",
    ]

    out1 = FIGURES_DIR / "elo_exemplars_table.tex"
    out1.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out1}")

    # ── Table 2: Regression results ──────────────────────────────────────
    rows = [
        # (name, beta, se, p, lrt_chi2, r2m, r2c, sig)
        ("Mean absolute shift", "+0.007", "0.001", "<.001", "28.13", ".061", ".290", True),
        ("SSR", r"$-$0.237", "0.082", ".004", "8.44", ".027", ".092", True),
        (r"Within-question $\tau$", "+0.017", "0.016", ".285", "1.14", ".003", ".022", False),
        ("Shortest-path premium", "+0.001", "0.001", ".449", "0.58", ".001", ".001", False),
        ("Asymmetry index", r"$-$0.039", "0.018", ".025", "5.00", ".010", ".094", True),
        ("Reasoning judge rating", "+0.083", "0.010", "<.001", "65.60", ".096", ".461", True),
        ("Uncertainty judge rating", r"$-$0.015", "0.007", ".023", "5.22", ".010", ".210", True),
        ("Brier score", r"$-$0.060", "0.010", "<.001", "36.13", ".203", ".207", True),
    ]

    lines2 = [
        r"\begin{table*}[t]",
        r"\centering",
        r"\small",
        r"\begin{tabular}{lcccccc}",
        r"\toprule",
        r"\textbf{Outcome} & \textbf{$\beta$(Elo$_z$)} & \textbf{SE} & "
        r"\textbf{$p$} & \textbf{LRT $\chi^2$(1)} & "
        r"\textbf{$R^2_m$} & \textbf{$R^2_c$} \\",
        r"\midrule",
    ]

    for name, beta, se, p, lrt, r2m, r2c, sig in rows:
        if sig:
            lines2.append(
                f"\\textbf{{{name}}} & {beta} & {se} & {p} & {lrt} & {r2m} & {r2c} \\\\"
            )
        else:
            lines2.append(
                f"{name} & {beta} & {se} & {p} & {lrt} & {r2m} & {r2c} \\\\"
            )

    lines2 += [
        r"\bottomrule",
        r"\end{tabular}",
        r"\caption{Mixed-effects regression: Elo difficulty predicting belief "
        r"sensitivity metrics, controlling for $|p_0 - 0.5|$. All models include "
        r"a random intercept for model identity. $\beta$(Elo$_z$) is the standardized "
        r"coefficient; LRT $\chi^2$ tests whether adding Elo improves fit over "
        r"$|p_0 - 0.5|$ alone. $R^2_m$ = marginal (fixed effects); "
        r"$R^2_c$ = conditional (fixed + random). "
        r"$N = 500$ (100 questions $\times$ 5 models) except Brier "
        r"($N = 240$, 48 questions with ground truth). Bold = $p < .05$.}",
        r"\label{tab:elo_regression}",
        r"\end{table*}",
    ]

    out2 = FIGURES_DIR / "elo_regression_table.tex"
    out2.write_text("\n".join(lines2), encoding="utf-8")
    print(f"Wrote {out2}")


if __name__ == "__main__":
    main()
