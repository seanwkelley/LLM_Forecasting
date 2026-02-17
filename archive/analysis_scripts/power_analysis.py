#!/usr/bin/env python3
"""
Power analysis for multi-scenario experiment.

Design: 100 scenarios, each run under baseline and sharding.
        Paired comparison of ensemble Brier scores.
Test:   Paired t-test (one Brier score per scenario per condition)
N:      100 paired observations
"""

import numpy as np
from scipy import stats

print("="*70)
print("POWER ANALYSIS: Multi-Scenario Sharding Experiment")
print("="*70)

# ============================================================
# 1. Estimate effect size from our 3-scenario test
# ============================================================
print("\n--- EFFECT SIZE ESTIMATION FROM TEST DATA (N=3) ---\n")

# Real simulation results (from ground_truth.csv)
# These are ensemble Brier scores from the mock forecasting test
baseline_brier = np.array([0.1031, 0.0799, 0.1695])  # 3 scenarios
sharding_brier = np.array([0.1019, 0.0649, 0.0634])  # 3 scenarios

differences = baseline_brier - sharding_brier
mean_diff = np.mean(differences)
std_diff = np.std(differences, ddof=1)
d_observed = mean_diff / std_diff

print(f"Paired differences: {differences}")
print(f"Mean difference:    {mean_diff:.4f}")
print(f"Std of differences: {std_diff:.4f}")
print(f"Observed Cohen's d: {d_observed:.3f}")
print(f"\nCaveat: N=3 is too small for reliable estimation.")
print(f"  95% CI for d: roughly ({d_observed - 2/np.sqrt(3):.2f}, {d_observed + 2/np.sqrt(3):.2f})")

# ============================================================
# 2. Power analysis for range of effect sizes
# ============================================================
print("\n" + "="*70)
print("POWER TABLE: Paired t-test, alpha=0.05 (two-tailed)")
print("="*70)

def compute_power(n, d, alpha=0.05):
    """Power for paired t-test (= one-sample t-test on differences)."""
    df = n - 1
    t_crit = stats.t.ppf(1 - alpha/2, df)
    ncp = d * np.sqrt(n)  # non-centrality parameter
    # Power = P(reject H0 | H1 true) = P(|t| > t_crit | ncp)
    power = 1 - stats.nct.cdf(t_crit, df, ncp) + stats.nct.cdf(-t_crit, df, ncp)
    return power

effect_sizes = [0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50, 0.60, 0.70, 0.80, 1.00]
sample_sizes = [50, 75, 100, 150, 200]

print(f"\n{'Cohen d':>10s}", end="")
for n in sample_sizes:
    print(f"  N={n:3d}", end="")
print(f"  | Interpretation")
print("-" * 80)

for d in effect_sizes:
    print(f"  d={d:.2f}  ", end="")
    for n in sample_sizes:
        power = compute_power(n, d)
        marker = " *" if power >= 0.80 else "  "
        print(f"  {power:.1%}{marker}", end="")

    # Interpretation
    if d <= 0.20:
        interp = "Small (pessimistic)"
    elif d <= 0.35:
        interp = "Small-medium (conservative)"
    elif d <= 0.50:
        interp = "Medium (moderate)"
    elif d <= 0.80:
        interp = "Medium-large"
    else:
        interp = "Large (optimistic)"
    print(f"  | {interp}")

print("\n * = Power >= 80% (adequate)")

# ============================================================
# 3. What effect size can we detect with 80% power?
# ============================================================
print("\n" + "="*70)
print("MINIMUM DETECTABLE EFFECT SIZE (80% power, alpha=0.05)")
print("="*70)

for n in sample_sizes:
    # Binary search for d that gives 80% power
    lo, hi = 0.01, 2.0
    for _ in range(100):
        mid = (lo + hi) / 2
        if compute_power(n, mid) < 0.80:
            lo = mid
        else:
            hi = mid
    min_d = (lo + hi) / 2

    # Convert to Brier score difference (using observed std)
    min_brier_diff = min_d * std_diff
    min_pct_improvement = (min_brier_diff / np.mean(baseline_brier)) * 100

    print(f"  N={n:3d}: d >= {min_d:.3f} (Brier diff >= {min_brier_diff:.4f}, "
          f"~{min_pct_improvement:.1f}% improvement)")

# ============================================================
# 4. Practical considerations
# ============================================================
print("\n" + "="*70)
print("PRACTICAL CONSIDERATIONS")
print("="*70)

print(f"""
What effect size should we assume?

FROM OUR DATA:
  - Observed d = {d_observed:.2f} (N=3, very uncertain)
  - Mean improvement: {mean_diff/np.mean(baseline_brier)*100:.1f}%
  - But this is from MOCK forecasting data, not production

REASONABLE ASSUMPTIONS:
  - Optimistic:  d = 0.50-0.70 (sharding consistently helps a lot)
  - Moderate:    d = 0.30-0.50 (sharding helps, but variable across scenarios)
  - Conservative: d = 0.20-0.30 (small but real effect)
  - Pessimistic: d = 0.10-0.20 (minimal effect, hard to detect)

WITH N=100 SCENARIOS:
  - Can detect d >= 0.28 with 80% power
  - Can detect d >= 0.35 with 95% power
  - If true d = 0.30: Power = {compute_power(100, 0.30):.0%}
  - If true d = 0.40: Power = {compute_power(100, 0.40):.0%}
  - If true d = 0.50: Power = {compute_power(100, 0.50):.0%}

RECOMMENDATION:
  If we believe the effect is at least "small-medium" (d >= 0.30):
    N=100 gives {compute_power(100, 0.30):.0%} power -> ADEQUATE

  If we're worried the effect might be small (d ~ 0.20):
    N=100 gives only {compute_power(100, 0.20):.0%} power
    Would need N=200 for {compute_power(200, 0.20):.0%} power

  If the effect is medium (d >= 0.40):
    N=100 gives {compute_power(100, 0.40):.0%} power -> VERY STRONG

VERDICT: N=100 is adequate if we expect d >= 0.28.
         Given our preliminary results (d ~ 0.72), N=100 is likely overkill,
         but provides insurance against effect size inflation in pilot data.
""")

# ============================================================
# 5. Simulation-based power check
# ============================================================
print("="*70)
print("SIMULATION-BASED POWER VERIFICATION (10,000 simulations)")
print("="*70)

np.random.seed(42)
n_sims = 10000
n = 100

for d in [0.20, 0.30, 0.40, 0.50]:
    sig_count = 0
    for _ in range(n_sims):
        # Simulate paired differences
        diffs = np.random.normal(loc=d, scale=1.0, size=n)
        t_stat, p_val = stats.ttest_1samp(diffs, 0)
        if p_val < 0.05:
            sig_count += 1
    sim_power = sig_count / n_sims
    analytic_power = compute_power(n, d)
    print(f"  d={d:.2f}: Simulated power = {sim_power:.1%} "
          f"(Analytic = {analytic_power:.1%})")

print("\n" + "="*70)
