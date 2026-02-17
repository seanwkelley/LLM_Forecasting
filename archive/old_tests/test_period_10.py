"""
Quick test: Predict Period 10 actions with 5 personas.

Validates full pipeline: ground truth → prompts → LLM predictions → evaluation
"""

import sys
sys.path.insert(0, 'D:/Northeastern/LLM_Forecasting')

import json
import random
from pathlib import Path

from forecasting.action_ground_truth import load_ground_truth
from forecasting.action_library import load_plausible_actions, format_plausible_actions_for_prompt
from forecasting.action_prompts import (
    create_novaris_action_prediction_prompt,
    create_tethys_action_prediction_prompt
)
from forecasting.action_evaluation import (
    evaluate_action_set_prediction,
    evaluate_aggregate_predictions
)
from forecasting.forecaster_base import BaseLLMForecaster
from forecasting.persona_generator import load_personas
from forecasting.config import RANDOM_SEED

print("="*80)
print("PERIOD 10 ACTION PREDICTION TEST")
print("="*80)
print("Testing with 5 diverse personas")
print()

# 1. Load ground truth
print("[1/6] Loading ground truth...")
ground_truth = load_ground_truth()
period_10_truth = ground_truth[10]

novaris_actual = period_10_truth['major_power']['actions']
tethys_actual = period_10_truth['small_power']['actions']

print(f"  Novaris actual actions (n={len(novaris_actual)}): {novaris_actual[:3]}...")
print(f"  Tethys actual actions (n={len(tethys_actual)}): {tethys_actual[:3]}...")

# 2. Load plausible actions
print("\n[2/6] Loading plausible actions library...")
plausible, descriptions = load_plausible_actions()
plausible_text = format_plausible_actions_for_prompt(plausible, descriptions)
print(f"  Loaded {sum(len(a) for a in plausible.values())} plausible actions")

# 3. Create test state (Period 9 final state)
print("\n[3/6] Creating Period 9 state...")
# These are approximate values from simulation - in real experiment would load from state history
state_period_9 = {
    'territory_controlled': 0.18,  # Novaris controls 18%
    'military_balance': -0.08,     # Slight Novaris advantage
    'crisis_level': 7.5,
    'novaris_gdp': 88.0,
    'tethys_gdp': 26.0,
    'international_support': 0.58,
    'sanctions_level': 0.42
}
print(f"  Territory: {state_period_9['territory_controlled']*100:.0f}% Novaris-controlled")
print(f"  Crisis Level: {state_period_9['crisis_level']:.1f}/10")

# 4. Create test events (Period 10)
print("\n[4/6] Loading Period 10 external events...")
events_period_10 = [
    "Battlefield: Aggressor breakthrough - significant territorial gains and encirclement",
    "Economic: Energy price surge due to supply disruptions",
    "Diplomatic: Peace talks proposed but tensions remain high",
    "Intelligence: Reports of covert operations by both sides"
]
print(f"  {len(events_period_10)} external events")

# 5. Load test personas
print("\n[5/6] Loading test personas...")
all_personas = load_personas()
random.seed(RANDOM_SEED)
test_personas = random.sample(all_personas, 5)
random.seed()  # Reset

print(f"  Selected 5 diverse personas:")
for p in test_personas:
    print(f"    - {p.name}: {p.occupation}, "
          f"geopolitical expertise={p.geopolitical_expertise}, "
          f"military expertise={p.military_expertise}")

# 6. Generate predictions
print("\n[6/6] Generating predictions...")
print("="*80)

forecaster = BaseLLMForecaster(model="deepseek/deepseek-v3.2")

# NOVARIS PREDICTIONS
print("\nNOVARIS ACTION PREDICTIONS:")
print("-"*80)

novaris_predictions = []

for i, persona in enumerate(test_personas, 1):
    print(f"\nAgent {i}: {persona.name}")

    # Create prompt
    prompt = create_novaris_action_prediction_prompt(
        period=10,
        state_before=state_period_9,
        external_events=events_period_10,
        plausible_actions_text=plausible_text
    )

    # Create persona system prompt
    persona_desc = persona.to_natural_language()
    system_prompt = f"""You are a strategic forecasting agent with the following profile:

{persona_desc}

Your task is to predict which actions a faction will take based on strategic analysis.
Consider your expertise and cognitive profile when making predictions.
Output ONLY valid JSON in the exact format specified."""

    try:
        # Call LLM using forecaster's method
        response_text, success = forecaster.call_llm(
            user_prompt=prompt,
            system_prompt=system_prompt,
            response_format="json"
        )

        if not success:
            raise Exception("LLM call failed")

        result = json.loads(response_text)
        predicted_actions = result.get('predicted_actions', [])
        rationale = result.get('rationale', 'No rationale provided')
        confidence = result.get('confidence', 'unknown')

        novaris_predictions.append({
            'persona_id': persona.persona_id,
            'predicted_actions': predicted_actions
        })

        print(f"  Predicted: {predicted_actions}")
        print(f"  Rationale: {rationale[:100]}...")
        print(f"  Confidence: {confidence}")

    except Exception as e:
        print(f"  [ERROR] Prediction failed: {str(e)}")
        novaris_predictions.append({
            'persona_id': persona.persona_id,
            'predicted_actions': []
        })

# Evaluate Novaris
print("\n" + "="*80)
print("NOVARIS EVALUATION:")
print("="*80)
novaris_metrics = evaluate_aggregate_predictions(novaris_predictions, novaris_actual)

print(f"\nGround Truth (n={len(novaris_actual)}): {novaris_actual}")
print(f"\nAggregate Metrics:")
print(f"  Mean F1:        {novaris_metrics['mean_f1']:.3f}")
print(f"  Mean Precision: {novaris_metrics['mean_precision']:.3f}")
print(f"  Mean Recall:    {novaris_metrics['mean_recall']:.3f}")
print(f"  Mean Jaccard:   {novaris_metrics['mean_jaccard']:.3f}")
print(f"  Any Correct:    {novaris_metrics['any_correct_rate']*100:.0f}%")

print(f"\nMost Commonly Predicted Actions:")
for action, count in novaris_metrics['most_common_predictions'][:5]:
    in_truth = "[OK]" if action in novaris_actual else "[X]"
    print(f"  {in_truth} {action}: {count}/5 agents")

# TETHYS PREDICTIONS (with Novaris actions visible)
print("\n" + "="*80)
print("TETHYS ACTION PREDICTIONS (with Novaris actions visible):")
print("-"*80)

tethys_predictions = []

for i, persona in enumerate(test_personas, 1):
    print(f"\nAgent {i}: {persona.name}")

    # Create prompt with Novaris's ACTUAL actions
    prompt = create_tethys_action_prediction_prompt(
        period=10,
        state_before=state_period_9,
        external_events=events_period_10,
        novaris_actions=novaris_actual,  # KEY: Give actual Novaris actions
        plausible_actions_text=plausible_text
    )

    persona_desc = persona.to_natural_language()
    system_prompt = f"""You are a strategic forecasting agent with the following profile:

{persona_desc}

Your task is to predict which actions a faction will take based on strategic analysis.
Consider your expertise and cognitive profile when making predictions.
Output ONLY valid JSON in the exact format specified."""

    try:
        # Call LLM using forecaster's method
        response_text, success = forecaster.call_llm(
            user_prompt=prompt,
            system_prompt=system_prompt,
            response_format="json"
        )

        if not success:
            raise Exception("LLM call failed")

        result = json.loads(response_text)
        predicted_actions = result.get('predicted_actions', [])
        rationale = result.get('rationale', 'No rationale provided')
        confidence = result.get('confidence', 'unknown')

        tethys_predictions.append({
            'persona_id': persona.persona_id,
            'predicted_actions': predicted_actions
        })

        print(f"  Predicted: {predicted_actions}")
        print(f"  Rationale: {rationale[:100]}...")
        print(f"  Confidence: {confidence}")

    except Exception as e:
        print(f"  [ERROR] Prediction failed: {str(e)}")
        tethys_predictions.append({
            'persona_id': persona.persona_id,
            'predicted_actions': []
        })

# Evaluate Tethys
print("\n" + "="*80)
print("TETHYS EVALUATION:")
print("="*80)
tethys_metrics = evaluate_aggregate_predictions(tethys_predictions, tethys_actual)

print(f"\nGround Truth (n={len(tethys_actual)}): {tethys_actual}")
print(f"\nAggregate Metrics:")
print(f"  Mean F1:        {tethys_metrics['mean_f1']:.3f}")
print(f"  Mean Precision: {tethys_metrics['mean_precision']:.3f}")
print(f"  Mean Recall:    {tethys_metrics['mean_recall']:.3f}")
print(f"  Mean Jaccard:   {tethys_metrics['mean_jaccard']:.3f}")
print(f"  Any Correct:    {tethys_metrics['any_correct_rate']*100:.0f}%")

print(f"\nMost Commonly Predicted Actions:")
for action, count in tethys_metrics['most_common_predictions'][:5]:
    in_truth = "[OK]" if action in tethys_actual else "[X]"
    print(f"  {in_truth} {action}: {count}/5 agents")

# Final comparison
print("\n" + "="*80)
print("COMPARATIVE SUMMARY:")
print("="*80)

print(f"\n{'Metric':<20} {'Novaris':<15} {'Tethys':<15} {'Difference':<15}")
print("-"*65)
print(f"{'F1 Score':<20} {novaris_metrics['mean_f1']:<15.3f} {tethys_metrics['mean_f1']:<15.3f} {tethys_metrics['mean_f1']-novaris_metrics['mean_f1']:+.3f}")
print(f"{'Recall':<20} {novaris_metrics['mean_recall']:<15.3f} {tethys_metrics['mean_recall']:<15.3f} {tethys_metrics['mean_recall']-novaris_metrics['mean_recall']:+.3f}")
print(f"{'Jaccard':<20} {novaris_metrics['mean_jaccard']:<15.3f} {tethys_metrics['mean_jaccard']:<15.3f} {tethys_metrics['mean_jaccard']-novaris_metrics['mean_jaccard']:+.3f}")

print("\n" + "="*80)
print("HYPOTHESIS TEST: Information Advantage")
print("="*80)

if tethys_metrics['mean_f1'] > novaris_metrics['mean_f1']:
    if novaris_metrics['mean_f1'] > 0:
        improvement = (tethys_metrics['mean_f1'] - novaris_metrics['mean_f1']) / novaris_metrics['mean_f1'] * 100
    else:
        improvement = 100 if tethys_metrics['mean_f1'] > 0 else 0
    print(f"\n[OK] SUPPORTED: Tethys performed {improvement:.1f}% better than Novaris")
    print(f"  Tethys had access to Novaris's actions -> reactive prediction easier")
else:
    print(f"\n[FAIL] NOT SUPPORTED: No clear information advantage detected")
    print(f"  May need larger sample size (N=5 too small)")

print("\n" + "="*80)
print("TEST COMPLETE!")
print("="*80)

# Print API stats
stats = forecaster.get_statistics()
print(f"\nAPI Statistics:")
print(f"  Total calls: {stats['total_calls']}")
print(f"  Successful: {stats['successful_calls']}")
print(f"  Failed: {stats['failed_calls']}")
print(f"  Success rate: {stats['success_rate']*100:.1f}%")

print("\n[OK] Period 10 test complete!")
print("\nNext steps:")
print("  - If results look good: Run full experiment (all 10 periods, 100 agents)")
print("  - If results need improvement: Adjust prompts or plausible actions")
