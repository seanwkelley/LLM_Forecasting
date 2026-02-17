"""
Investigate why LLM forecasts don't track crisis escalation

Analyzes actual reasoning text to understand anchoring bias
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Load data
results_dir = Path("D:/Northeastern/LLM_Forecasting/outputs/forecasting_results")
df = pd.read_csv(results_dir / "condition_3_personalized_independent" / "all_forecasts_individual.csv")
ground_truth = pd.read_csv("D:/Northeastern/LLM_Forecasting/outputs/assessments.csv")

print("=" * 80)
print("INVESTIGATING WHY FORECASTS DON'T TRACK CRISIS ESCALATION")
print("=" * 80)
print()

# =========================================================================
# 1. SAMPLE REASONING ACROSS PERIODS
# =========================================================================

# Select same persona across multiple periods to see evolution
sample_persona = df['persona_name'].iloc[0]  # First persona
persona_forecasts = df[df['persona_name'] == sample_persona].sort_values('period')

print(f"TRACKING ONE FORECASTER ACROSS ALL PERIODS: {sample_persona}")
print(f"Occupation: {persona_forecasts.iloc[0]['occupation']}")
print("-" * 80)
print()

for _, row in persona_forecasts.iterrows():
    gt = ground_truth[ground_truth['period'] == row['period']]['probability'].values[0]
    print(f"PERIOD {int(row['period'])} | Forecast: {row['probability']*100:.1f}% | Truth: {gt*100:.1f}% | Error: {(row['probability']-gt)*100:.1f}pp")
    print(f"Confidence: {row['confidence']}")
    print(f"Reasoning: {row['reasoning']}")
    print("-" * 80)
    print()

# =========================================================================
# 2. COMPARE EARLY VS LATE PERIOD REASONING
# =========================================================================

print()
print("=" * 80)
print("REASONING COMPARISON: PERIOD 1 vs PERIOD 10")
print("=" * 80)
print()

# Sample 5 forecasters from Period 1
period_1 = df[df['period'] == 1].sample(5, random_state=42)
print("PERIOD 1 (Ground Truth: 22%)")
print("Early crisis - Limited escalation")
print("-" * 80)

for idx, (_, row) in enumerate(period_1.iterrows(), 1):
    print(f"\n{idx}. {row['persona_name']} ({row['occupation']})")
    print(f"   Forecast: {row['probability']*100:.1f}% | Confidence: {row['confidence']}")
    print(f"   Reasoning: {row['reasoning'][:300]}...")

# Get the same 5 forecasters from Period 10
sample_ids = period_1['persona_id'].tolist()
period_10 = df[(df['period'] == 10) & (df['persona_id'].isin(sample_ids))]

print()
print()
print("PERIOD 10 (Ground Truth: 80%)")
print("Late crisis - Catastrophic: 4.4% territory lost, key city encircled")
print("-" * 80)

for idx, (_, row) in enumerate(period_10.iterrows(), 1):
    print(f"\n{idx}. {row['persona_name']} ({row['occupation']})")
    print(f"   Forecast: {row['probability']*100:.1f}% | Confidence: {row['confidence']}")
    print(f"   Reasoning: {row['reasoning'][:300]}...")

# =========================================================================
# 3. KEYWORD ANALYSIS
# =========================================================================

print()
print()
print("=" * 80)
print("KEYWORD ANALYSIS: What are forecasters focusing on?")
print("=" * 80)
print()

# Keywords that suggest awareness of escalation
escalation_keywords = [
    'escalat', 'increas', 'growing', 'mounting', 'worsen', 'deterior',
    'crisis', 'catastroph', 'critical', 'severe', 'extreme', 'breakthrough'
]

# Keywords that suggest stability bias
stability_keywords = [
    'stable', 'maintain', 'hold', 'defend', 'resist', 'support',
    'unlikely', 'low', 'modest', 'limited', 'contain'
]

# Analyze by period
keyword_analysis = []

for period in range(1, 11):
    period_df = df[df['period'] == period]

    # Count keyword occurrences
    escalation_count = sum(
        period_df['reasoning'].str.lower().str.contains('|'.join(escalation_keywords), na=False)
    )
    stability_count = sum(
        period_df['reasoning'].str.lower().str.contains('|'.join(stability_keywords), na=False)
    )

    gt = ground_truth[ground_truth['period'] == period]['probability'].values[0]
    mean_forecast = period_df['probability'].mean()

    keyword_analysis.append({
        'period': period,
        'ground_truth': gt * 100,
        'mean_forecast': mean_forecast * 100,
        'escalation_mentions': escalation_count,
        'stability_mentions': stability_count,
        'ratio': escalation_count / stability_count if stability_count > 0 else 0
    })

df_keywords = pd.DataFrame(keyword_analysis)

print("Keyword Usage by Period:")
print("-" * 80)
print(f"{'Period':<8} {'Truth':<8} {'Forecast':<10} {'Escalation':<12} {'Stability':<10} {'E/S Ratio':<10}")
print("-" * 80)

for _, row in df_keywords.iterrows():
    print(f"{int(row['period']):<8} {row['ground_truth']:>5.1f}%  {row['mean_forecast']:>7.1f}%  "
          f"{row['escalation_mentions']:>10}  {row['stability_mentions']:>10}  {row['ratio']:>8.2f}")

print()
print("INTERPRETATION:")
print("-" * 80)
print("If forecasters were tracking escalation correctly:")
print("  - Escalation keyword usage should INCREASE as crisis worsens")
print("  - Stability keyword usage should DECREASE")
print("  - E/S ratio should increase dramatically by Period 10")
print()

# =========================================================================
# 4. ANCHORING ON BASE RATES
# =========================================================================

print()
print("=" * 80)
print("EVIDENCE OF ANCHORING BIAS")
print("=" * 80)
print()

# Check if forecasts mention specific numbers
baseline_keywords = ['15%', '10%', '20%', 'base rate', 'historical', 'typical']

baseline_mentions = df['reasoning'].str.lower().str.contains('|'.join(baseline_keywords), na=False).sum()
print(f"Forecasts mentioning baseline/historical rates: {baseline_mentions}/{len(df)} ({baseline_mentions/len(df)*100:.1f}%)")
print()

# Sample forecasts that mention baselines
baseline_forecasts = df[df['reasoning'].str.lower().str.contains('|'.join(baseline_keywords), na=False)].sample(
    min(3, baseline_mentions), random_state=42
)

if len(baseline_forecasts) > 0:
    print("Examples of baseline anchoring:")
    print("-" * 80)
    for idx, (_, row) in enumerate(baseline_forecasts.iterrows(), 1):
        print(f"\n{idx}. Period {int(row['period'])} | Forecast: {row['probability']*100:.1f}%")
        print(f"   {row['reasoning'][:250]}...")

# =========================================================================
# 5. CONFIDENCE PATTERNS
# =========================================================================

print()
print()
print("=" * 80)
print("CONFIDENCE PATTERNS BY PERIOD")
print("=" * 80)
print()

confidence_by_period = df.groupby('period')['confidence'].value_counts(normalize=True).unstack(fill_value=0)
print("Confidence distribution (% of forecasters):")
print("-" * 80)
print(confidence_by_period.round(3))
print()

print("INTERPRETATION:")
print("-" * 80)
print("If forecasters recognized increasing uncertainty/risk:")
print("  - Confidence should DECREASE as crisis escalates")
print("  - Or shift toward 'high' confidence in HIGH probabilities")
print()
print("=" * 80)
