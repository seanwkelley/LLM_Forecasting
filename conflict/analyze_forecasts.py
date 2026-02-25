"""
Linear Mixed Model analysis of conflict forecasting experiment.

Compares ToM vs no-ToM and Strategy vs Demographic persona types,
using LMM to account for repeated measures within scenarios and
shared forecaster identities.

Models:
  brier_score ~ tom * persona_type + (1|scenario_id) + (1|forecaster_id)
  sq_ei_error ~ tom * persona_type + (1|scenario_id) + (1|forecaster_id)

Usage:
    python conflict/analyze_forecasts.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

# ---------------------------------------------------------------------------
# Load and combine all 4 conditions
# ---------------------------------------------------------------------------

BASE = Path(__file__).parent.parent / "outputs" / "_archive" / "llm_agents" / "conflict_llama_persona"

CONDITIONS = {
    ("strategy", 0): BASE / "forecasting" / "forecast_results.csv",
    ("strategy", 1): BASE / "forecasting_tom" / "forecast_results.csv",
    ("demographic", 0): BASE / "forecasting_demographic" / "forecast_results.csv",
    ("demographic", 1): BASE / "forecasting_demographic_tom" / "forecast_results.csv",
}


def load_all() -> pd.DataFrame:
    frames = []
    for (persona_type, tom), path in CONDITIONS.items():
        if not path.exists():
            print(f"[WARN] Missing: {path}")
            continue
        df = pd.read_csv(path)
        df["persona_type"] = persona_type
        df["tom"] = tom
        df["tom_label"] = "ToM" if tom else "no-ToM"
        df["condition"] = f"{persona_type}_{'tom' if tom else 'notom'}"
        frames.append(df)

    combined = pd.concat(frames, ignore_index=True)

    # Compute squared EI error
    combined["ei_error"] = pd.to_numeric(combined["ei_error"], errors="coerce")
    combined["sq_ei_error"] = combined["ei_error"] ** 2

    return combined


def print_descriptives(df: pd.DataFrame):
    print("=" * 70)
    print("DESCRIPTIVE STATISTICS")
    print("=" * 70)

    for cond in ["strategy_notom", "strategy_tom", "demographic_notom", "demographic_tom"]:
        sub = df[df["condition"] == cond]
        n = len(sub)
        acc = sub["correct"].mean() * 100
        brier = sub["brier_score"].mean()
        mae = sub["ei_error"].mean()
        sq_err = sub["sq_ei_error"].mean()
        print(f"\n  {cond:25s} (N={n})")
        print(f"    Accuracy:    {acc:.1f}%")
        print(f"    Brier:       {brier:.4f}")
        print(f"    EI MAE:      {mae:.4f}")
        print(f"    EI MSE:      {sq_err:.4f}")

    # Overall
    print(f"\n  {'TOTAL':25s} (N={len(df)})")
    print(f"    Class distribution: "
          f"UP={df['actual'].value_counts().get('UP', 0)}, "
          f"DOWN={df['actual'].value_counts().get('DOWN', 0)}, "
          f"FLAT={df['actual'].value_counts().get('FLAT', 0)}")


def run_lmm(df: pd.DataFrame, dv: str, dv_label: str):
    """Run LMM with main effects and interaction, compare models."""
    print(f"\n{'=' * 70}")
    print(f"LINEAR MIXED MODEL: {dv_label}")
    print(f"{'=' * 70}")

    sub = df.dropna(subset=[dv]).copy()
    print(f"  N = {len(sub)} observations")
    print(f"  Scenarios: {sub['scenario_id'].nunique()}")
    print(f"  Forecasters: {sub['forecaster_id'].nunique()}")

    # --- Main effects model ---
    print(f"\n--- Model 1: Main effects ---")
    print(f"  {dv} ~ tom + persona_type + (1|scenario_id) + (1|forecaster_id)")

    formula_main = f"{dv} ~ tom + C(persona_type, Treatment(reference='strategy'))"
    try:
        md_main = smf.mixedlm(
            formula_main, sub,
            groups=sub["scenario_id"],
            re_formula="1",
            vc_formula={"forecaster_id": "0 + C(forecaster_id)"},
        )
        mdf_main = md_main.fit(reml=True)
        print(mdf_main.summary())

        # Extract key results
        print(f"\n  Key fixed effects:")
        for name in mdf_main.fe_params.index:
            coef = mdf_main.fe_params[name]
            se = mdf_main.bse_fe[name]
            z = mdf_main.tvalues[name]
            p = mdf_main.pvalues[name]
            sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
            print(f"    {name:45s}: coef={coef:+.4f}, SE={se:.4f}, z={z:.2f}, p={p:.4f} {sig}")
    except Exception as e:
        print(f"  [ERROR] Main effects model failed: {e}")
        mdf_main = None

    # --- Interaction model ---
    print(f"\n--- Model 2: Interaction ---")
    print(f"  {dv} ~ tom * persona_type + (1|scenario_id) + (1|forecaster_id)")

    formula_int = f"{dv} ~ tom * C(persona_type, Treatment(reference='strategy'))"
    try:
        md_int = smf.mixedlm(
            formula_int, sub,
            groups=sub["scenario_id"],
            re_formula="1",
            vc_formula={"forecaster_id": "0 + C(forecaster_id)"},
        )
        mdf_int = md_int.fit(reml=True)
        print(mdf_int.summary())

        print(f"\n  Key fixed effects:")
        for name in mdf_int.fe_params.index:
            coef = mdf_int.fe_params[name]
            se = mdf_int.bse_fe[name]
            z = mdf_int.tvalues[name]
            p = mdf_int.pvalues[name]
            sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
            print(f"    {name:45s}: coef={coef:+.4f}, SE={se:.4f}, z={z:.2f}, p={p:.4f} {sig}")
    except Exception as e:
        print(f"  [ERROR] Interaction model failed: {e}")
        mdf_int = None

    # --- Model comparison ---
    if mdf_main is not None and mdf_int is not None:
        print(f"\n--- Model comparison ---")
        ll_main = mdf_main.llf
        ll_int = mdf_int.llf
        lr_stat = 2 * (ll_int - ll_main)
        from scipy import stats
        p_lr = stats.chi2.sf(lr_stat, df=1)
        print(f"  Main effects log-lik:  {ll_main:.2f}")
        print(f"  Interaction log-lik:   {ll_int:.2f}")
        print(f"  LR statistic:          {lr_stat:.3f}")
        print(f"  LR p-value:            {p_lr:.4f}")
        if p_lr < 0.05:
            print(f"  --> Interaction IS significant, prefer interaction model")
        else:
            print(f"  --> Interaction NOT significant, prefer main effects model")

    return mdf_main, mdf_int


def run_simple_tom_test(df: pd.DataFrame, dv: str, dv_label: str, persona: str):
    """Simple within-persona-type ToM comparison."""
    print(f"\n--- Simple ToM effect ({persona} only): {dv_label} ---")
    sub = df[(df["persona_type"] == persona)].dropna(subset=[dv]).copy()

    notom = sub[sub["tom"] == 0][dv]
    tom = sub[sub["tom"] == 1][dv]

    print(f"  no-ToM: mean={notom.mean():.4f}, sd={notom.std():.4f}, N={len(notom)}")
    print(f"  ToM:    mean={tom.mean():.4f}, sd={tom.std():.4f}, N={len(tom)}")
    diff = tom.mean() - notom.mean()
    pooled_sd = np.sqrt((notom.var() + tom.var()) / 2)
    d = diff / pooled_sd if pooled_sd > 0 else 0
    print(f"  Difference: {diff:+.4f} (Cohen's d = {d:.3f})")

    # Per-scenario comparison
    wins_tom = 0
    for sid in sorted(sub["scenario_id"].unique()):
        s_notom = sub[(sub["tom"] == 0) & (sub["scenario_id"] == sid)][dv].mean()
        s_tom = sub[(sub["tom"] == 1) & (sub["scenario_id"] == sid)][dv].mean()
        if s_tom < s_notom:  # lower is better for both brier and sq_error
            wins_tom += 1
    n_scenarios = sub["scenario_id"].nunique()
    print(f"  ToM wins {wins_tom}/{n_scenarios} scenarios (lower = better)")


def main():
    df = load_all()

    if df.empty:
        print("[ERROR] No data loaded")
        sys.exit(1)

    print_descriptives(df)

    # Run LMMs on both DVs
    run_lmm(df, "brier_score", "Brier Score (directional calibration)")
    run_lmm(df, "sq_ei_error", "Squared EI Error (point prediction)")

    # Simple within-persona comparisons
    for persona in ["strategy", "demographic"]:
        run_simple_tom_test(df, "brier_score", "Brier", persona)
        run_simple_tom_test(df, "sq_ei_error", "Sq EI Error", persona)

    print(f"\n{'=' * 70}")
    print("ANALYSIS COMPLETE")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
