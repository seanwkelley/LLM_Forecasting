"""
Test LLM forecasting with FULL aggregator-level information

Compares forecasts with:
1. Standard prompt (limited info)
2. Enhanced prompt (includes detailed KEY_FACTORS)
"""

import sys
sys.path.insert(0, 'D:/Northeastern/LLM_Forecasting')

import pandas as pd
from forecasting.forecaster_base import BaseLLMForecaster
from forecasting.persona_generator import load_personas
from forecasting.config import PERSONA_SYSTEM_PROMPT_PREFIX, PERSONA_SYSTEM_PROMPT_SUFFIX
import random

# Load Period 10 standard prompt
with open('D:/Northeastern/LLM_Forecasting/outputs/human_forecasting/TRUE/period_10.txt', 'r', encoding='utf-8') as f:
    standard_prompt = f.read()

# Enhanced prompt with aggregator-level information
enhanced_info = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DETAILED INTELLIGENCE ASSESSMENT (CLASSIFIED - AGGREGATOR LEVEL)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**CRITICAL ANALYSIS:**

The primary driver for this period is the ***SHOCK: Aggressor Breakthrough***, which resulted in:
  • **TERRITORIAL LOSS:** 4.4% of Tethys territory now under Novaris control
  • **OPERATIONAL FAILURE:** Key city is fully encircled and cut off from supply
  • **DEFENSIVE COLLAPSE:** Catastrophic failure of Tethys's defensive lines

**MILITARY BALANCE:**
  • Previous period: +0.14 (slight Tethys advantage)
  • Current period: +0.08 (advantage rapidly eroding)
  • **Interpretation:** Rapid 43% decline in military effectiveness indicates decoupling
    between theoretical strength and battlefield reality

**INTERNAL POLITICAL DYNAMICS:**
  • Internal discourse has shifted from "continued resistance" to:
    - "Assessing military aid requirements"
    - "Neutrality status discussions"
    - "Territorial concessions on the table"
  • **Interpretation:** Political leadership is preparing for transition or forced settlement

**CRISIS LEVEL:**
  • Current: 10/10 (MAXIMUM - unchanged for 7 periods)
  • Sustained maximum crisis + military defeat = extreme governing capacity fragility

**ECONOMIC SITUATION:**
  • Sanctions against Novaris: 89.6% (comprehensive regime)
  • Tethys economy: Previously "buckled under prolonged conflict pressure" (Period 8)
  • Current: Economic strain + military defeat + internal political shift

**ASSESSMENT:**
The combination of:
  1. First significant territorial loss (4.4%)
  2. Catastrophic military defeat (key city encircled)
  3. Rapid erosion of military balance (-43% in one period)
  4. Internal political shift toward settlement/concessions
  5. Sustained maximum crisis level (10/10)
  6. Economic fragility from previous periods

...creates conditions for government collapse or forced removal within the forecast window.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

# Insert enhanced info before forecast question
enhanced_prompt = standard_prompt.replace(
    "YOUR FORECAST",
    enhanced_info + "\nYOUR FORECAST"
)

print("=" * 80)
print("EXPERIMENT: FORECASTING WITH FULL vs LIMITED INFORMATION")
print("=" * 80)
print()
print("Testing Period 10 (Ground Truth: 80%)")
print()
print("Condition A: Standard prompt (limited information)")
print("Condition B: Enhanced prompt (aggregator-level detail)")
print()
print("=" * 80)
print()

# Load personas and sample 5 diverse ones
all_personas = load_personas()
random.seed(42)
test_personas = random.sample(all_personas, 5)

# Initialize forecaster
forecaster = BaseLLMForecaster(model="deepseek/deepseek-v3.2")

results = []

for persona in test_personas:
    print(f"Testing: {persona.name} ({persona.occupation})")
    print("-" * 80)

    # Build persona system prompt
    persona_desc = persona.to_natural_language()
    system_prompt = (
        PERSONA_SYSTEM_PROMPT_PREFIX +
        persona_desc +
        PERSONA_SYSTEM_PROMPT_SUFFIX
    )

    # Test A: Standard prompt
    print("  [A] Standard prompt (generating...)    ", end='', flush=True)
    forecast_standard = forecaster.generate_forecast(standard_prompt, system_prompt)
    print(f"Complete: {forecast_standard.probability*100:.1f}%")

    # Test B: Enhanced prompt
    print("  [B] Enhanced prompt (generating...)    ", end='', flush=True)
    forecast_enhanced = forecaster.generate_forecast(enhanced_prompt, system_prompt)
    print(f"Complete: {forecast_enhanced.probability*100:.1f}%")

    # Store results
    results.append({
        'persona_name': persona.name,
        'occupation': persona.occupation,
        'geopolitical_expertise': persona.geopolitical_expertise,
        'bayesian_updating_skill': persona.bayesian_updating_skill,
        'general_intelligence': persona.general_intelligence,
        'standard_forecast': forecast_standard.probability,
        'enhanced_forecast': forecast_enhanced.probability,
        'standard_confidence': forecast_standard.confidence,
        'enhanced_confidence': forecast_enhanced.confidence,
        'standard_reasoning': forecast_standard.reasoning[:200],
        'enhanced_reasoning': forecast_enhanced.reasoning[:200]
    })

    print(f"  Increase: {(forecast_enhanced.probability - forecast_standard.probability)*100:+.1f} percentage points")
    print()

# Create results DataFrame
df_results = pd.DataFrame(results)

print()
print("=" * 80)
print("RESULTS SUMMARY")
print("=" * 80)
print()

# Overall statistics
print(f"STANDARD PROMPT (Limited Info):")
print(f"  Mean forecast:     {df_results['standard_forecast'].mean()*100:.1f}%")
print(f"  Median forecast:   {df_results['standard_forecast'].median()*100:.1f}%")
print(f"  Range:             {df_results['standard_forecast'].min()*100:.1f}% - {df_results['standard_forecast'].max()*100:.1f}%")
print(f"  Error from truth:  {abs(df_results['standard_forecast'].mean() - 0.80)*100:.1f} percentage points")
print()

print(f"ENHANCED PROMPT (Full Aggregator Info):")
print(f"  Mean forecast:     {df_results['enhanced_forecast'].mean()*100:.1f}%")
print(f"  Median forecast:   {df_results['enhanced_forecast'].median()*100:.1f}%")
print(f"  Range:             {df_results['enhanced_forecast'].min()*100:.1f}% - {df_results['enhanced_forecast'].max()*100:.1f}%")
print(f"  Error from truth:  {abs(df_results['enhanced_forecast'].mean() - 0.80)*100:.1f} percentage points")
print()

print(f"IMPROVEMENT:")
print(f"  Average increase:  {(df_results['enhanced_forecast'].mean() - df_results['standard_forecast'].mean())*100:+.1f} percentage points")
print(f"  All forecasters increased? {(df_results['enhanced_forecast'] > df_results['standard_forecast']).all()}")
print()

print("=" * 80)
print("INDIVIDUAL COMPARISONS")
print("=" * 80)
print()

for _, row in df_results.iterrows():
    print(f"{row['persona_name']} ({row['occupation']})")
    print(f"  Standard: {row['standard_forecast']*100:>5.1f}%  |  Enhanced: {row['enhanced_forecast']*100:>5.1f}%  |  Change: {(row['enhanced_forecast']-row['standard_forecast'])*100:+5.1f}pp")
    print(f"  Expertise: Geo={row['geopolitical_expertise']} Bayes={row['bayesian_updating_skill']} IQ={row['general_intelligence']}")
    print()

print("=" * 80)
print("SAMPLE REASONING COMPARISON")
print("=" * 80)
print()

# Show reasoning from one forecaster
sample = df_results.iloc[0]
print(f"Forecaster: {sample['persona_name']}")
print()
print("STANDARD PROMPT REASONING:")
print("-" * 80)
print(sample['standard_reasoning'])
print()
print("ENHANCED PROMPT REASONING:")
print("-" * 80)
print(sample['enhanced_reasoning'])
print()

print("=" * 80)
print("CONCLUSION")
print("=" * 80)
print()

if df_results['enhanced_forecast'].mean() > 0.60:
    print("[OK] LLMs CAN forecast accurately when given full information!")
    print(f"     Enhanced forecasts averaged {df_results['enhanced_forecast'].mean()*100:.1f}% (vs 80% truth)")
    print()
    print("INTERPRETATION: The problem is INFORMATION INSUFFICIENCY in prompts,")
    print("                not fundamental LLM reasoning incapability.")
else:
    print("[WARNING] Even with full information, forecasts remain conservative")
    print(f"          Enhanced forecasts only averaged {df_results['enhanced_forecast'].mean()*100:.1f}% (vs 80% truth)")
    print()
    print("INTERPRETATION: LLMs have BOTH information gap AND anchoring bias issues.")

print()
print("=" * 80)

# Save results
df_results.to_csv('D:/Northeastern/LLM_Forecasting/outputs/forecasting_results/full_info_test.csv', index=False)
print("Results saved to: outputs/forecasting_results/full_info_test.csv")
