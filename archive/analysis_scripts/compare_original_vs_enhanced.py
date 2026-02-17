"""
Compare Original vs Enhanced Condition 3 Results

Shows impact of providing full KEY_FACTORS information
"""

import pandas as pd
import numpy as np

# Load results
original = pd.read_csv("D:/Northeastern/LLM_Forecasting/outputs/forecasting_results/condition_3_personalized_independent/all_forecasts_aggregated.csv")
enhanced = pd.read_csv("D:/Northeastern/LLM_Forecasting/outputs/forecasting_results/condition_3_personalized_independent_ENHANCED/all_forecasts_aggregated.csv")
ground_truth = pd.read_csv("D:/Northeastern/LLM_Forecasting/outputs/assessments.csv")

print("=" * 80)
print("COMPARISON: ORIGINAL vs ENHANCED PROMPTS")
print("=" * 80)
print()

print("PERIOD-BY-PERIOD COMPARISON:")
print("-" * 80)
print(f"{'Period':<8} {'Truth':<10} {'Original':<12} {'Enhanced':<12} {'Improvement':<12} {'Orig Error':<12} {'Enh Error':<12}")
print("-" * 80)

total_orig_error = 0
total_enh_error = 0

for period in range(1, 11):
    truth = ground_truth[ground_truth['period'] == period]['probability'].values[0]
    orig = original[original['period'] == period]['mean_probability'].values[0]
    enh = enhanced[enhanced['period'] == period]['mean_probability'].values[0]

    improvement = enh - orig
    orig_error = abs(orig - truth)
    enh_error = abs(enh - truth)

    total_orig_error += orig_error
    total_enh_error += enh_error

    print(f"{period:<8} {truth*100:>5.0f}%     {orig*100:>7.1f}%      {enh*100:>7.1f}%      {improvement*100:>+6.1f}pp     {orig_error*100:>6.1f}pp     {enh_error*100:>6.1f}pp")

print("-" * 80)
print(f"{'MEAN':<8} {ground_truth['probability'].mean()*100:>5.0f}%     {original['mean_probability'].mean()*100:>7.1f}%      {enhanced['mean_probability'].mean()*100:>7.1f}%      {(enhanced['mean_probability'].mean()-original['mean_probability'].mean())*100:>+6.1f}pp     {total_orig_error/10*100:>6.1f}pp     {total_enh_error/10*100:>6.1f}pp")

print()
print()
print("OVERALL STATISTICS:")
print("-" * 80)

# Correlation
orig_corr = np.corrcoef(original['mean_probability'].values, ground_truth['probability'].values)[0, 1]
enh_corr = np.corrcoef(enhanced['mean_probability'].values, ground_truth['probability'].values)[0, 1]

print(f"Correlation with ground truth:")
print(f"  Original: r = {orig_corr:.3f}")
print(f"  Enhanced: r = {enh_corr:.3f}")
print(f"  Improvement: {enh_corr - orig_corr:+.3f}")
print()

# Mean Absolute Error
orig_mae = np.mean(np.abs(original['mean_probability'].values - ground_truth['probability'].values))
enh_mae = np.mean(np.abs(enhanced['mean_probability'].values - ground_truth['probability'].values))

print(f"Mean Absolute Error:")
print(f"  Original: {orig_mae*100:.1f} percentage points")
print(f"  Enhanced: {enh_mae*100:.1f} percentage points")
print(f"  Improvement: {(orig_mae - enh_mae)*100:+.1f} percentage points")
print()

# Bias
orig_bias = np.mean(original['mean_probability'].values - ground_truth['probability'].values)
enh_bias = np.mean(enhanced['mean_probability'].values - ground_truth['probability'].values)

print(f"Bias (negative = under-forecasting):")
print(f"  Original: {orig_bias*100:.1f}pp")
print(f"  Enhanced: {enh_bias*100:.1f}pp")
print(f"  Improvement: {(enh_bias - orig_bias)*100:+.1f}pp")
print()

# Variance
print(f"Forecast variance (diversity):")
print(f"  Original: std = {original['std_probability'].mean():.3f}")
print(f"  Enhanced: std = {enhanced['std_probability'].mean():.3f}")
print(f"  Change: {enhanced['std_probability'].mean() - original['std_probability'].mean():+.3f}")
print()

print()
print("=" * 80)
print("KEY INSIGHTS:")
print("=" * 80)
print()

# When did enhancement help most?
diff = enhanced['mean_probability'].values - original['mean_probability'].values
best_periods = np.argsort(diff)[-3:][::-1]

print("PERIODS WHERE ENHANCED PROMPTS HELPED MOST:")
for i, period_idx in enumerate(best_periods, 1):
    period = period_idx + 1
    truth = ground_truth.iloc[period_idx]['probability'] * 100
    orig = original.iloc[period_idx]['mean_probability'] * 100
    enh = enhanced.iloc[period_idx]['mean_probability'] * 100
    print(f"  {i}. Period {period}: {orig:.1f}% -> {enh:.1f}% (+{enh-orig:.1f}pp) [Truth: {truth:.0f}%]")

print()

# When did it not help?
worst_periods = np.argsort(diff)[:3]

print("PERIODS WHERE ENHANCEMENT HAD MINIMAL EFFECT:")
for i, period_idx in enumerate(worst_periods, 1):
    period = period_idx + 1
    truth = ground_truth.iloc[period_idx]['probability'] * 100
    orig = original.iloc[period_idx]['mean_probability'] * 100
    enh = enhanced.iloc[period_idx]['mean_probability'] * 100
    print(f"  {i}. Period {period}: {orig:.1f}% -> {enh:.1f}% ({enh-orig:+.1f}pp) [Truth: {truth:.0f}%]")

print()
print()

# Check if early vs late periods differ
early_orig = original[original['period'] <= 6]['mean_probability'].mean()
early_enh = enhanced[enhanced['period'] <= 6]['mean_probability'].mean()
early_truth = ground_truth[ground_truth['period'] <= 6]['probability'].mean()

late_orig = original[original['period'] > 6]['mean_probability'].mean()
late_enh = enhanced[enhanced['period'] > 6]['mean_probability'].mean()
late_truth = ground_truth[ground_truth['period'] > 6]['probability'].mean()

print("EARLY vs LATE PERIODS:")
print("-" * 80)
print(f"Periods 1-6 (Early Crisis):")
print(f"  Truth: {early_truth*100:.1f}%")
print(f"  Original: {early_orig*100:.1f}% (error: {abs(early_orig-early_truth)*100:.1f}pp)")
print(f"  Enhanced: {early_enh*100:.1f}% (error: {abs(early_enh-early_truth)*100:.1f}pp)")
print(f"  Improvement: {(early_enh-early_orig)*100:+.1f}pp")
print()
print(f"Periods 7-10 (Late Crisis):")
print(f"  Truth: {late_truth*100:.1f}%")
print(f"  Original: {late_orig*100:.1f}% (error: {abs(late_orig-late_truth)*100:.1f}pp)")
print(f"  Enhanced: {late_enh*100:.1f}% (error: {abs(late_enh-late_truth)*100:.1f}pp)")
print(f"  Improvement: {(late_enh-late_orig)*100:+.1f}pp")
print()

print("=" * 80)
print("CONCLUSION:")
print("=" * 80)

if enh_corr > 0.7:
    print("[OK] Enhanced prompts SIGNIFICANTLY improved tracking (r > 0.7)")
elif enh_corr > 0.5:
    print("[PARTIAL] Enhanced prompts improved tracking somewhat (0.5 < r < 0.7)")
else:
    print("[LIMITED] Enhanced prompts had limited effect (r < 0.5)")

print()

if enh_mae < orig_mae * 0.7:
    print("[OK] Enhanced prompts reduced error by >30%")
elif enh_mae < orig_mae:
    print("[PARTIAL] Enhanced prompts reduced error but not dramatically")
else:
    print("[FAIL] Enhanced prompts did not reduce error")

print()
print("=" * 80)
