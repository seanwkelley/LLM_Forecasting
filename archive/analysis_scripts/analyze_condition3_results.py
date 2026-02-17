"""
Detailed analysis of Condition 3 results

Analyzes which personas performed best and why
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Load data
results_dir = Path("D:/Northeastern/LLM_Forecasting/outputs/forecasting_results")
df = pd.read_csv(results_dir / "condition_3_personalized_independent" / "all_forecasts_individual.csv")
ground_truth = pd.read_csv("D:/Northeastern/LLM_Forecasting/outputs/assessments.csv")

print("=" * 80)
print("DETAILED ANALYSIS: CONDITION 3 PERSONALIZED INDEPENDENT")
print("=" * 80)
print()

# Merge with ground truth
df = df.merge(
    ground_truth[['period', 'probability']].rename(columns={'probability': 'true_probability'}),
    on='period'
)

# Calculate individual errors
df['error'] = df['probability'] - df['true_probability']
df['abs_error'] = df['error'].abs()

# =========================================================================
# 1. TOP AND BOTTOM PERFORMERS
# =========================================================================
print("TOP 10 BEST FORECASTERS (Lowest Average Absolute Error):")
print("-" * 80)

best_forecasters = df.groupby('persona_name').agg({
    'abs_error': 'mean',
    'error': 'mean',
    'probability': 'mean',
    'occupation': 'first',
    'geopolitical_expertise': 'first',
    'bayesian_updating_skill': 'first',
    'general_intelligence': 'first',
    'risk_tolerance': 'first'
}).sort_values('abs_error').head(10)

for idx, (name, row) in enumerate(best_forecasters.iterrows(), 1):
    print(f"{idx}. {name} ({row['occupation']})")
    print(f"   MAE: {row['abs_error']:.3f} | Mean forecast: {row['probability']:.3f} | Bias: {row['error']:.3f}")
    print(f"   Geopolitical: {row['geopolitical_expertise']} | Bayesian: {row['bayesian_updating_skill']} | IQ: {row['general_intelligence']} | Risk tolerance: {row['risk_tolerance']}")
    print()

print()
print("BOTTOM 10 WORST FORECASTERS (Highest Average Absolute Error):")
print("-" * 80)

worst_forecasters = df.groupby('persona_name').agg({
    'abs_error': 'mean',
    'error': 'mean',
    'probability': 'mean',
    'occupation': 'first',
    'geopolitical_expertise': 'first',
    'bayesian_updating_skill': 'first',
    'general_intelligence': 'first',
    'risk_tolerance': 'first'
}).sort_values('abs_error', ascending=False).head(10)

for idx, (name, row) in enumerate(worst_forecasters.iterrows(), 1):
    print(f"{idx}. {name} ({row['occupation']})")
    print(f"   MAE: {row['abs_error']:.3f} | Mean forecast: {row['probability']:.3f} | Bias: {row['error']:.3f}")
    print(f"   Geopolitical: {row['geopolitical_expertise']} | Bayesian: {row['bayesian_updating_skill']} | IQ: {row['general_intelligence']} | Risk tolerance: {row['risk_tolerance']}")
    print()

# =========================================================================
# 2. CORRELATION BETWEEN PERSONA ATTRIBUTES AND ACCURACY
# =========================================================================
print()
print("=" * 80)
print("CORRELATION: PERSONA ATTRIBUTES vs FORECAST ACCURACY")
print("=" * 80)
print()

persona_accuracy = df.groupby('persona_id').agg({
    'abs_error': 'mean',
    'geopolitical_expertise': 'first',
    'economic_expertise': 'first',
    'military_expertise': 'first',
    'statistical_expertise': 'first',
    'general_intelligence': 'first',
    'bayesian_updating_skill': 'first',
    'coherence_forecasting': 'first',
    'cognitive_reflection_test': 'first',
    'risk_tolerance': 'first',
    'decision_rule_competence': 'first'
})

print("Correlation between attributes and accuracy (negative = more accurate):")
print("-" * 80)

attributes = [
    'geopolitical_expertise',
    'military_expertise',
    'bayesian_updating_skill',
    'general_intelligence',
    'cognitive_reflection_test',
    'risk_tolerance',
    'coherence_forecasting',
    'decision_rule_competence'
]

correlations = []
for attr in attributes:
    corr = persona_accuracy[attr].corr(persona_accuracy['abs_error'])
    correlations.append((attr, corr))

correlations.sort(key=lambda x: abs(x[1]), reverse=True)

for attr, corr in correlations:
    direction = "MORE accurate" if corr < 0 else "LESS accurate"
    print(f"{attr:<30}: r={corr:>6.3f}  (higher {attr} -> {direction})")

# =========================================================================
# 3. MOST PESSIMISTIC vs MOST OPTIMISTIC
# =========================================================================
print()
print("=" * 80)
print("MOST PESSIMISTIC vs MOST OPTIMISTIC FORECASTERS")
print("=" * 80)
print()

persona_means = df.groupby('persona_name').agg({
    'probability': 'mean',
    'abs_error': 'mean',
    'occupation': 'first'
})

print("TOP 5 MOST PESSIMISTIC (Highest average forecasts):")
print("-" * 80)
for idx, (name, row) in enumerate(persona_means.nlargest(5, 'probability').iterrows(), 1):
    print(f"{idx}. {name} ({row['occupation']}): {row['probability']*100:.1f}% average (MAE: {row['abs_error']:.3f})")

print()
print("TOP 5 MOST OPTIMISTIC (Lowest average forecasts):")
print("-" * 80)
for idx, (name, row) in enumerate(persona_means.nsmallest(5, 'probability').iterrows(), 1):
    print(f"{idx}. {name} ({row['occupation']}): {row['probability']*100:.1f}% average (MAE: {row['abs_error']:.3f})")

# =========================================================================
# 4. PERIOD-SPECIFIC INSIGHTS
# =========================================================================
print()
print("=" * 80)
print("WHO SAW THE CATASTROPHE COMING? (Period 10: 80% True Probability)")
print("=" * 80)
print()

period_10 = df[df['period'] == 10].copy()
period_10 = period_10.sort_values('probability', ascending=False)

print("TOP 10 HIGHEST FORECASTS FOR PERIOD 10:")
print("-" * 80)
for idx, (_, row) in enumerate(period_10.head(10).iterrows(), 1):
    print(f"{idx}. {row['persona_name']}: {row['probability']*100:.1f}% (Error: {row['abs_error']*100:.1f}pp)")

print()
print(f"Even the most pessimistic forecaster only predicted {period_10['probability'].max()*100:.1f}%")
print(f"when the true probability was 80.0%")
print()
print("=" * 80)
