#!/usr/bin/env python3
"""
Trade-off analysis: fewer agents per scenario vs more scenarios.

Question: Is it better to have N=100 agents × 100 scenarios,
          or N=10 agents × 1000 scenarios (same compute budget)?
"""

import numpy as np
from scipy import stats
import json

print("="*70)
print("AGENT COUNT vs SCENARIO COUNT TRADE-OFF ANALYSIS")
print("="*70)

# ============================================================
# 1. Estimate ensemble noise as a function of agent count
# ============================================================

# From real data: individual prediction variability
# Period 1 baseline: mean=0.146, std=0.029
# Period 1 sharding: mean=0.271, std=0.177 (higher spread due to info asymmetry)
# Period 2 sharding: mean=0.274, std=0.169

# Individual prediction std (from existing experiments)
individual_std_baseline = 0.05  # typical across periods
individual_std_sharding = 0.17  # higher due to info sharding

print("\n--- ENSEMBLE PRECISION BY AGENT COUNT ---\n")
print(f"Individual prediction std (baseline): {individual_std_baseline:.3f}")
print(f"Individual prediction std (sharding): {individual_std_sharding:.3f}")

print(f"\n{'N agents':>10s}  {'SE(baseline)':>14s}  {'SE(sharding)':>14s}  {'SE(diff)':>12s}")
print("-" * 55)

se_diffs = {}
for n_agents in [5, 10, 20, 50, 100]:
    se_base = individual_std_baseline / np.sqrt(n_agents)
    se_shard = individual_std_sharding / np.sqrt(n_agents)
    # SE of the Brier score difference (approximately)
    # Brier = (p - truth)^2, so SE(Brier) depends on SE(p)
    # Roughly: SE(Brier_diff) ~ 2 * |p - truth| * SE(p)
    # For typical |p-truth| ~ 0.15:
    se_brier_base = 2 * 0.15 * se_base
    se_brier_shard = 2 * 0.15 * se_shard
    se_diff = np.sqrt(se_brier_base**2 + se_brier_shard**2)
    se_diffs[n_agents] = se_diff
    print(f"  N={n_agents:3d}       {se_base:.4f}          {se_shard:.4f}        {se_diff:.4f}")

# ============================================================
# 2. Simulate the trade-off
# ============================================================
print(f"\n{'='*70}")
print("SIMULATION: Effect of agent count on detectable effect size")
print(f"{'='*70}")

np.random.seed(42)
n_sims = 5000

# True effect: sharding improves Brier by ~0.018 (from real data)
true_brier_diff = 0.018  # mean(baseline - sharding) from 5-period data
true_brier_std = 0.043   # std of differences from 5-period data

print(f"\nTrue effect: mean diff = {true_brier_diff:.4f}, std = {true_brier_std:.4f}")
print(f"True Cohen's d = {true_brier_diff/true_brier_std:.3f}")

print(f"\n{'N agents':>10s}  {'N scenarios':>12s}  {'API calls':>10s}  {'Power':>8s}  {'Effective d':>12s}")
print("-" * 60)

configs = [
    # (n_agents, n_scenarios)
    (100, 50),
    (100, 100),
    (100, 200),
    (50, 100),
    (50, 200),
    (20, 100),
    (20, 250),
    (20, 500),
    (10, 100),
    (10, 200),
    (10, 500),
    (10, 1000),
    (5, 200),
    (5, 500),
    (5, 1000),
    (5, 2000),
]

for n_agents, n_scenarios in configs:
    api_calls = n_agents * n_scenarios * 2  # 2 conditions

    sig_count = 0
    for _ in range(n_sims):
        # For each scenario, simulate the paired difference
        # True difference plus measurement noise from finite ensemble
        measurement_noise_std = se_diffs.get(n_agents, se_diffs[min(se_diffs.keys(), key=lambda x: abs(x-n_agents))])

        # Each scenario's observed difference = true effect + scenario variance + measurement noise
        scenario_diffs = np.random.normal(
            loc=true_brier_diff,
            scale=np.sqrt(true_brier_std**2 + measurement_noise_std**2),
            size=n_scenarios
        )

        t_stat, p_val = stats.ttest_1samp(scenario_diffs, 0)
        if p_val < 0.05:
            sig_count += 1

    power = sig_count / n_sims
    effective_std = np.sqrt(true_brier_std**2 + se_diffs.get(n_agents, 0)**2)
    effective_d = true_brier_diff / effective_std

    print(f"  N={n_agents:3d}       K={n_scenarios:4d}      {api_calls:6d}      {power:.1%}      d={effective_d:.3f}")

# ============================================================
# 3. Fixed-budget comparison
# ============================================================
print(f"\n{'='*70}")
print("FIXED BUDGET COMPARISON (20,000 API calls)")
print(f"{'='*70}")

budget = 20000
print(f"\nBudget: {budget} API calls (2 conditions)")
print(f"\n{'Config':>20s}  {'Power':>8s}  {'Effective d':>12s}  {'Notes':>30s}")
print("-" * 75)

fixed_budget_configs = [
    (100, 100, "Original plan"),
    (50, 200, "Half agents, 2x scenarios"),
    (20, 500, "20 agents, 5x scenarios"),
    (10, 1000, "10 agents, 10x scenarios"),
    (5, 2000, "5 agents, 20x scenarios"),
]

for n_agents, n_scenarios, note in fixed_budget_configs:
    sig_count = 0
    measurement_noise_std = se_diffs.get(n_agents, se_diffs[min(se_diffs.keys(), key=lambda x: abs(x-n_agents))])

    for _ in range(n_sims):
        scenario_diffs = np.random.normal(
            loc=true_brier_diff,
            scale=np.sqrt(true_brier_std**2 + measurement_noise_std**2),
            size=n_scenarios
        )
        t_stat, p_val = stats.ttest_1samp(scenario_diffs, 0)
        if p_val < 0.05:
            sig_count += 1

    power = sig_count / n_sims
    effective_std = np.sqrt(true_brier_std**2 + measurement_noise_std**2)
    effective_d = true_brier_diff / effective_std

    print(f"  {n_agents:3d} agents × {n_scenarios:4d} scenarios  {power:.1%}      d={effective_d:.3f}      {note}")

# ============================================================
# 4. Recommendation
# ============================================================
print(f"\n{'='*70}")
print("RECOMMENDATION")
print(f"{'='*70}")
print(f"""
The measurement noise from smaller ensembles (N=10) is SMALL relative
to the cross-scenario variance in the treatment effect.

  Measurement noise SE (N=10):   {se_diffs[10]:.4f}
  Measurement noise SE (N=100):  {se_diffs[100]:.4f}
  Cross-scenario std:            {true_brier_std:.4f}

The cross-scenario variance ({true_brier_std:.4f}) DOMINATES the measurement
noise ({se_diffs[10]:.4f} for N=10), so adding more scenarios helps more
than adding more agents.

However, there's a practical concern: with N=10 agents, each ensemble
prediction is based on only 10 forecasts. The sharding strategy creates
10 info levels (10%-100%), so with N=10 you'd have EXACTLY 1 agent per
level. With N=100, you have 10 agents per level.

PRACTICAL MINIMUM: N=10 works if each agent independently samples from
the sharding distribution. If you need multiple agents per sharding level,
N=20 is the minimum (2 per level).

BOTTOM LINE: N=10-20 agents × more scenarios is likely BETTER than
N=100 × fewer scenarios, for the same compute budget.
""")
