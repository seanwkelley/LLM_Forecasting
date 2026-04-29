"""Brier scoring and condition comparison for the agent-forecast pipeline.

Brier score for a binary outcome y in {0, 1} and forecast p in [0, 1]:
    BS = (p - y)^2

Lower = better. Range [0, 1]. Reference: random guess on balanced set = 0.25.

We report:
  - per-condition mean Brier (across all question × model trials)
  - PRIMARY paired contrast: Brier_peripheral_targeted - Brier_topology_targeted
    (positive = centrality beats the decomposition-only control)
  - SECONDARY paired contrast: Brier_untargeted - Brier_topology_targeted
    (positive = combined centrality + decomposition effect)
  - TERTIARY: Brier_no_search - Brier_topology_targeted (reference only)
  - LME-style analysis with condition as fixed effect, (question, model) as
    random intercepts -- export CSV for R (lme4).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from forecast_bench.agent_forecast.config import OUT_DIR


TRIALS_PATH = OUT_DIR / "trials.jsonl"
RESOLUTIONS_CACHE = OUT_DIR / "resolutions.json"


def brier(p: float, y: int) -> float:
    return (float(p) - int(y)) ** 2


def load_trials(path: Path = TRIALS_PATH) -> pd.DataFrame:
    rows = []
    if not path.exists():
        raise FileNotFoundError(f"No trials file at {path}")
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return pd.DataFrame(rows)


def merge_with_resolutions(df: pd.DataFrame, res_path: Path = RESOLUTIONS_CACHE) -> pd.DataFrame:
    if not res_path.exists():
        raise FileNotFoundError(f"No resolutions file at {res_path}")
    res = json.loads(res_path.read_text(encoding="utf-8"))
    df["resolved"] = df["question_id"].apply(lambda q: res.get(q, {}).get("resolved", False))
    df["outcome"] = df["question_id"].apply(lambda q: res.get(q, {}).get("outcome"))
    df["observed_value"] = df["question_id"].apply(lambda q: res.get(q, {}).get("observed_value"))
    return df[df["resolved"]].copy()


def score(df: pd.DataFrame, prob_col: str = "p1") -> pd.DataFrame:
    """Attach Brier scores. Uses `prob_col` as the forecast (default p1)."""
    df = df.copy()
    df["brier"] = df.apply(lambda r: brier(r[prob_col], r["outcome"]), axis=1)
    return df


def summarize_by_condition(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("condition")["brier"].agg(["mean", "sem", "count"]).round(4)
    return g.sort_values("mean")


def paired_deltas(df: pd.DataFrame, baseline: str = "peripheral_targeted",
                  treatment: str = "topology_targeted") -> pd.DataFrame:
    """Within (question, model), compare treatment Brier to baseline Brier."""
    pivot = df.pivot_table(index=["question_id", "model"],
                            columns="condition", values="brier")
    pivot = pivot.dropna(subset=[baseline, treatment])
    pivot["delta"] = pivot[baseline] - pivot[treatment]
    return pivot


def paired_test(pivot: pd.DataFrame) -> dict:
    """Wilcoxon signed-rank on paired Brier deltas (positive = treatment wins)."""
    from scipy import stats
    d = pivot["delta"].values
    if len(d) < 5:
        return {"n": len(d), "result": "too_few_pairs"}
    w, p = stats.wilcoxon(d)
    return {
        "n_pairs": len(d),
        "mean_delta": float(np.mean(d)),
        "median_delta": float(np.median(d)),
        "wilcoxon_W": float(w),
        "wilcoxon_p": float(p),
        "pct_treatment_better": float((d > 0).mean()),
    }


def report(df: pd.DataFrame) -> None:
    """Print a summary report: per-condition means + paired tests.

    Three contrasts in order of importance.  Primary isolates centrality
    from decomposition; secondary reports the combined effect; tertiary is
    the no-search reference.
    """
    conds = df["condition"].unique()
    print("\n=== Per-condition Brier (lower is better) ===")
    print(summarize_by_condition(df))

    if "peripheral_targeted" in conds:
        pivot = paired_deltas(df, baseline="peripheral_targeted",
                               treatment="topology_targeted")
        print(f"\n=== PRIMARY: topology vs peripheral (n = {len(pivot)}) ===")
        print("Isolates centrality from the decomposition-of-search effect.")
        print(paired_test(pivot))

    if "untargeted" in conds:
        pivot_u = paired_deltas(df, baseline="untargeted",
                                 treatment="topology_targeted")
        print(f"\n=== SECONDARY: topology vs untargeted (n = {len(pivot_u)}) ===")
        print("Combined centrality + decomposition effect.")
        print(paired_test(pivot_u))

    if "no_search" in conds:
        pivot_ns = paired_deltas(df, baseline="no_search",
                                  treatment="topology_targeted")
        print(f"\n=== TERTIARY: topology vs no_search (n = {len(pivot_ns)}) ===")
        print(paired_test(pivot_ns))
