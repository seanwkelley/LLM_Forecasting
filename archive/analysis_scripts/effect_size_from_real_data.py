#!/usr/bin/env python3
"""
Estimate effect size from existing 10-period experiment data.
Use this to inform power analysis for the multi-scenario experiment.
"""

import json
import numpy as np
from scipy import stats
from pathlib import Path

print("="*70)
print("EFFECT SIZE ESTIMATION FROM REAL EXPERIMENT DATA")
print("="*70)

# Load the 5-period sharding comparison data
with open("outputs/collapse_sharding_periods_1_5/experiment_summary.json") as f:
    data = json.load(f)

# Extract paired Brier scores
baseline_brier = []
sharding_brier = []
ground_truths = []

for result in data['results']:
    period = result['period']
    condition = result['condition']
    brier = result['statistics']['ensemble_brier_score']
    gt = result['statistics']['ground_truth']

    if condition == 'baseline':
        baseline_brier.append(brier)
        ground_truths.append(gt)
    else:
        sharding_brier.append(brier)

baseline_brier = np.array(baseline_brier)
sharding_brier = np.array(sharding_brier)
ground_truths = np.array(ground_truths)

print(f"\nN = {len(baseline_brier)} paired observations (periods 1-5)")
print(f"\n{'Period':>8s}  {'Truth':>8s}  {'Baseline':>10s}  {'Sharding':>10s}  {'Diff':>10s}  {'Winner':>10s}")
print("-" * 65)

differences = baseline_brier - sharding_brier  # positive = sharding better
for i in range(len(baseline_brier)):
    winner = "Sharding" if differences[i] > 0 else "Baseline"
    print(f"  P{i+1:d}      {ground_truths[i]:.3f}     {baseline_brier[i]:.6f}    {sharding_brier[i]:.6f}    {differences[i]:+.6f}    {winner}")

print(f"\n{'Mean':>8s}  {'':>8s}  {baseline_brier.mean():.6f}    {sharding_brier.mean():.6f}    {differences.mean():+.6f}")

# Effect size calculation
mean_diff = np.mean(differences)
std_diff = np.std(differences, ddof=1)
d = mean_diff / std_diff

print(f"\n{'='*70}")
print(f"PAIRED EFFECT SIZE")
print(f"{'='*70}")
print(f"\nMean difference (baseline - sharding): {mean_diff:.6f}")
print(f"Std of differences:                    {std_diff:.6f}")
print(f"Cohen's d (paired):                    {d:.3f}")
print(f"Direction:                             {'Sharding better' if mean_diff > 0 else 'Baseline better'}")

# Paired t-test
t_stat, p_val = stats.ttest_rel(baseline_brier, sharding_brier)
print(f"\nPaired t-test: t = {t_stat:.3f}, p = {p_val:.3f}")
print(f"  {'Significant' if p_val < 0.05 else 'Not significant'} at alpha = 0.05")

# Win rate
n_sharding_wins = np.sum(differences > 0)
print(f"\nSharding wins: {n_sharding_wins}/{len(differences)} periods ({n_sharding_wins/len(differences)*100:.0f}%)")

# IMPORTANT: Analyze by period to understand heterogeneity
print(f"\n{'='*70}")
print(f"HETEROGENEITY ANALYSIS")
print(f"{'='*70}")

print(f"\nImprovement by period:")
for i in range(len(differences)):
    if baseline_brier[i] > 0:
        pct = (differences[i] / baseline_brier[i]) * 100
    else:
        pct = 0
    print(f"  Period {i+1}: {pct:+.1f}% {'[OK]' if differences[i] > 0 else '[WORSE]'}")

avg_improvement = data.get('average_improvement_pct', 0)
print(f"\nAverage improvement: {avg_improvement:.1f}%")

# Check if there are also other experiment files
print(f"\n{'='*70}")
print(f"CHECKING OTHER EXPERIMENT DATA")
print(f"{'='*70}")

# Check collapse_sharding_comparison
try:
    with open("outputs/collapse_sharding_comparison/experiment_summary.json") as f:
        comp_data = json.load(f)
    print(f"\nCollapse sharding comparison:")
    print(json.dumps(comp_data, indent=2)[:500])
except:
    print("\nNo collapse_sharding_comparison data found")

# Check information_sharding_experiment
import os
ise_dir = "outputs/information_sharding_experiment"
if os.path.exists(ise_dir):
    files = os.listdir(ise_dir)
    print(f"\nInformation sharding experiment files: {files}")
    for f in files:
        if f.endswith('.json'):
            try:
                with open(os.path.join(ise_dir, f)) as fh:
                    ise_data = json.load(fh)
                print(f"\n{f}:")
                if isinstance(ise_data, dict):
                    for k, v in ise_data.items():
                        if isinstance(v, (int, float, str)):
                            print(f"  {k}: {v}")
            except:
                pass

# Power re-analysis with real effect size
print(f"\n{'='*70}")
print(f"UPDATED POWER ANALYSIS WITH REAL EFFECT SIZE")
print(f"{'='*70}")

def compute_power(n, d, alpha=0.05):
    df = n - 1
    t_crit = stats.t.ppf(1 - alpha/2, df)
    ncp = d * np.sqrt(n)
    power = 1 - stats.nct.cdf(t_crit, df, ncp) + stats.nct.cdf(-t_crit, df, ncp)
    return power

print(f"\nObserved Cohen's d from real data: {d:.3f}")
print(f"95% CI for d (approximate):        ({d - 2/np.sqrt(len(differences)):.3f}, {d + 2/np.sqrt(len(differences)):.3f})")

# But the multi-scenario design is DIFFERENT from the multi-period design
print(f"""
IMPORTANT CAVEAT:
  The 5-period data comes from ONE scenario across time.
  The multi-scenario experiment has 100 DIFFERENT scenarios × 1 period.

  Key differences:
  1. Multi-period: Same context, evolving over time
     - Correlation between periods (not independent)
     - Agents may "learn" the scenario over time

  2. Multi-scenario: Different contexts, same time point
     - Independent observations (good for stats)
     - More variance in scenario parameters
     - Effect size may differ from multi-period

  The multi-scenario effect size could be:
  - LARGER if sharding helps more with diverse/novel scenarios
  - SMALLER if sharding benefit is scenario-specific
  - SIMILAR if the mechanism (info diversity) is robust
""")

# Conservative, moderate, optimistic estimates
d_conservative = abs(d) * 0.5  # halve for caution
d_moderate = abs(d) * 0.75
d_optimistic = abs(d)

print(f"Effect size assumptions for multi-scenario:")
print(f"  Conservative (50% of observed): d = {d_conservative:.3f}")
print(f"  Moderate (75% of observed):     d = {d_moderate:.3f}")
print(f"  Optimistic (100% of observed):  d = {d_optimistic:.3f}")

for label, d_est in [("Conservative", d_conservative), ("Moderate", d_moderate), ("Optimistic", d_optimistic)]:
    for n in [50, 100, 150]:
        power = compute_power(n, d_est)
        print(f"  {label} (d={d_est:.3f}), N={n}: Power = {power:.1%}")
    print()
