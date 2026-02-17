"""
Compare Personalized vs Generic agents on Period 10 action prediction.

Tests if cognitive profiles improve prediction accuracy.
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
print("PERSONALIZED vs GENERIC COMPARISON TEST - Period 10")
print("="*80)
print("Testing with 10 agents each (5 Novaris + 5 Tethys)")
print()

# Setup
ground_truth = load_ground_truth()
period_10_truth = ground_truth[10]
novaris_actual = period_10_truth['major_power']['actions']
tethys_actual = period_10_truth['small_power']['actions']

plausible, descriptions = load_plausible_actions()
plausible_text = format_plausible_actions_for_prompt(plausible, descriptions)

state_period_9 = {
    'territory_controlled': 0.18,
    'military_balance': -0.08,
    'crisis_level': 7.5,
    'novaris_gdp': 88.0,
    'tethys_gdp': 26.0,
    'international_support': 0.58,
    'sanctions_level': 0.42
}

events_period_10 = [
    "Battlefield: Aggressor breakthrough - significant territorial gains and encirclement",
    "Economic: Energy price surge due to supply disruptions",
    "Diplomatic: Peace talks proposed but tensions remain high",
    "Intelligence: Reports of covert operations by both sides"
]

# Load personas
all_personas = load_personas()
random.seed(RANDOM_SEED)
test_personas = random.sample(all_personas, 5)
random.seed()

forecaster = BaseLLMForecaster(model="deepseek/deepseek-v3.2")

# ============================================================================
# CONDITION 1: GENERIC AGENTS
# ============================================================================

print("\n" + "="*80)
print("CONDITION 1: GENERIC AGENTS (No Personalization)")
print("="*80)

generic_system_prompt = """You are an expert strategic analyst specializing in geopolitical forecasting.

Your task is to predict which actions a faction will take based on strategic analysis of:
- Current military, economic, and diplomatic position
- External events and their implications
- Strategic objectives and constraints
- Available action options

Apply rigorous strategic reasoning to predict the most likely action set.
Output ONLY valid JSON in the exact format specified."""

print("\nNovaris Predictions (Generic):")
print("-"*80)

generic_novaris_predictions = []

for i in range(5):
    prompt = create_novaris_action_prediction_prompt(
        period=10,
        state_before=state_period_9,
        external_events=events_period_10,
        plausible_actions_text=plausible_text
    )

    try:
        response_text, success = forecaster.call_llm(
            user_prompt=prompt,
            system_prompt=generic_system_prompt,
            response_format="json"
        )

        if not success:
            raise Exception("LLM call failed")

        result = json.loads(response_text)
        predicted_actions = result.get('predicted_actions', [])

        generic_novaris_predictions.append({
            'predicted_actions': predicted_actions
        })

        print(f"  Agent {i+1}: {predicted_actions[:3]}... ({len(predicted_actions)} total)")

    except Exception as e:
        print(f"  Agent {i+1}: [ERROR] {str(e)}")
        generic_novaris_predictions.append({'predicted_actions': []})

print("\nTethys Predictions (Generic, with Novaris actions):")
print("-"*80)

generic_tethys_predictions = []

for i in range(5):
    prompt = create_tethys_action_prediction_prompt(
        period=10,
        state_before=state_period_9,
        external_events=events_period_10,
        novaris_actions=novaris_actual,
        plausible_actions_text=plausible_text
    )

    try:
        response_text, success = forecaster.call_llm(
            user_prompt=prompt,
            system_prompt=generic_system_prompt,
            response_format="json"
        )

        if not success:
            raise Exception("LLM call failed")

        result = json.loads(response_text)
        predicted_actions = result.get('predicted_actions', [])

        generic_tethys_predictions.append({
            'predicted_actions': predicted_actions
        })

        print(f"  Agent {i+1}: {predicted_actions[:3]}... ({len(predicted_actions)} total)")

    except Exception as e:
        print(f"  Agent {i+1}: [ERROR] {str(e)}")
        generic_tethys_predictions.append({'predicted_actions': []})

# Evaluate Generic
generic_novaris_metrics = evaluate_aggregate_predictions(generic_novaris_predictions, novaris_actual)
generic_tethys_metrics = evaluate_aggregate_predictions(generic_tethys_predictions, tethys_actual)

print("\n" + "="*80)
print("GENERIC RESULTS:")
print("="*80)
print(f"\nNovaris:")
print(f"  F1:        {generic_novaris_metrics['mean_f1']:.3f}")
print(f"  Precision: {generic_novaris_metrics['mean_precision']:.3f}")
print(f"  Recall:    {generic_novaris_metrics['mean_recall']:.3f}")

print(f"\nTethys:")
print(f"  F1:        {generic_tethys_metrics['mean_f1']:.3f}")
print(f"  Precision: {generic_tethys_metrics['mean_precision']:.3f}")
print(f"  Recall:    {generic_tethys_metrics['mean_recall']:.3f}")

# ============================================================================
# CONDITION 2: PERSONALIZED AGENTS
# ============================================================================

print("\n" + "="*80)
print("CONDITION 2: PERSONALIZED AGENTS (With Cognitive Profiles)")
print("="*80)

print("\nSelected personas:")
for p in test_personas:
    print(f"  - {p.name}: {p.occupation}")
    print(f"    Geopolitical: {p.geopolitical_expertise}, Military: {p.military_expertise}, "
          f"Bayesian: {p.bayesian_updating_skill}")

print("\nNovaris Predictions (Personalized):")
print("-"*80)

personalized_novaris_predictions = []

for i, persona in enumerate(test_personas):
    prompt = create_novaris_action_prediction_prompt(
        period=10,
        state_before=state_period_9,
        external_events=events_period_10,
        plausible_actions_text=plausible_text
    )

    persona_desc = persona.to_natural_language()
    system_prompt = f"""You are a strategic forecasting agent with the following profile:

{persona_desc}

Your task is to predict which actions a faction will take based on strategic analysis.
Consider your expertise and cognitive profile when making predictions.
Output ONLY valid JSON in the exact format specified."""

    try:
        response_text, success = forecaster.call_llm(
            user_prompt=prompt,
            system_prompt=system_prompt,
            response_format="json"
        )

        if not success:
            raise Exception("LLM call failed")

        result = json.loads(response_text)
        predicted_actions = result.get('predicted_actions', [])

        personalized_novaris_predictions.append({
            'predicted_actions': predicted_actions
        })

        print(f"  {persona.name}: {predicted_actions[:3]}... ({len(predicted_actions)} total)")

    except Exception as e:
        print(f"  {persona.name}: [ERROR] {str(e)}")
        personalized_novaris_predictions.append({'predicted_actions': []})

print("\nTethys Predictions (Personalized, with Novaris actions):")
print("-"*80)

personalized_tethys_predictions = []

for i, persona in enumerate(test_personas):
    prompt = create_tethys_action_prediction_prompt(
        period=10,
        state_before=state_period_9,
        external_events=events_period_10,
        novaris_actions=novaris_actual,
        plausible_actions_text=plausible_text
    )

    persona_desc = persona.to_natural_language()
    system_prompt = f"""You are a strategic forecasting agent with the following profile:

{persona_desc}

Your task is to predict which actions a faction will take based on strategic analysis.
Consider your expertise and cognitive profile when making predictions.
Output ONLY valid JSON in the exact format specified."""

    try:
        response_text, success = forecaster.call_llm(
            user_prompt=prompt,
            system_prompt=system_prompt,
            response_format="json"
        )

        if not success:
            raise Exception("LLM call failed")

        result = json.loads(response_text)
        predicted_actions = result.get('predicted_actions', [])

        personalized_tethys_predictions.append({
            'predicted_actions': predicted_actions
        })

        print(f"  {persona.name}: {predicted_actions[:3]}... ({len(predicted_actions)} total)")

    except Exception as e:
        print(f"  {persona.name}: [ERROR] {str(e)}")
        personalized_tethys_predictions.append({'predicted_actions': []})

# Evaluate Personalized
personalized_novaris_metrics = evaluate_aggregate_predictions(personalized_novaris_predictions, novaris_actual)
personalized_tethys_metrics = evaluate_aggregate_predictions(personalized_tethys_predictions, tethys_actual)

print("\n" + "="*80)
print("PERSONALIZED RESULTS:")
print("="*80)
print(f"\nNovaris:")
print(f"  F1:        {personalized_novaris_metrics['mean_f1']:.3f}")
print(f"  Precision: {personalized_novaris_metrics['mean_precision']:.3f}")
print(f"  Recall:    {personalized_novaris_metrics['mean_recall']:.3f}")

print(f"\nTethys:")
print(f"  F1:        {personalized_tethys_metrics['mean_f1']:.3f}")
print(f"  Precision: {personalized_tethys_metrics['mean_precision']:.3f}")
print(f"  Recall:    {personalized_tethys_metrics['mean_recall']:.3f}")

# ============================================================================
# COMPARISON
# ============================================================================

print("\n" + "="*80)
print("DIRECT COMPARISON: PERSONALIZED vs GENERIC")
print("="*80)

print(f"\n{'Metric':<20} {'Generic':<12} {'Personalized':<12} {'Difference':<12} {'Winner':<12}")
print("-"*80)

# Novaris comparison
nov_f1_diff = personalized_novaris_metrics['mean_f1'] - generic_novaris_metrics['mean_f1']
nov_f1_pct = (nov_f1_diff / generic_novaris_metrics['mean_f1'] * 100) if generic_novaris_metrics['mean_f1'] > 0 else 0
nov_winner = "Personalized" if nov_f1_diff > 0.01 else "Generic" if nov_f1_diff < -0.01 else "Tie"

print(f"{'Novaris F1':<20} {generic_novaris_metrics['mean_f1']:<12.3f} "
      f"{personalized_novaris_metrics['mean_f1']:<12.3f} "
      f"{nov_f1_diff:+.3f} ({nov_f1_pct:+.1f}%)  {nov_winner:<12}")

nov_recall_diff = personalized_novaris_metrics['mean_recall'] - generic_novaris_metrics['mean_recall']
nov_recall_winner = "Personalized" if nov_recall_diff > 0.01 else "Generic" if nov_recall_diff < -0.01 else "Tie"

print(f"{'Novaris Recall':<20} {generic_novaris_metrics['mean_recall']:<12.3f} "
      f"{personalized_novaris_metrics['mean_recall']:<12.3f} "
      f"{nov_recall_diff:+.3f}        {nov_recall_winner:<12}")

# Tethys comparison
tet_f1_diff = personalized_tethys_metrics['mean_f1'] - generic_tethys_metrics['mean_f1']
tet_f1_pct = (tet_f1_diff / generic_tethys_metrics['mean_f1'] * 100) if generic_tethys_metrics['mean_f1'] > 0 else 0
tet_winner = "Personalized" if tet_f1_diff > 0.01 else "Generic" if tet_f1_diff < -0.01 else "Tie"

print(f"{'Tethys F1':<20} {generic_tethys_metrics['mean_f1']:<12.3f} "
      f"{personalized_tethys_metrics['mean_f1']:<12.3f} "
      f"{tet_f1_diff:+.3f} ({tet_f1_pct:+.1f}%)  {tet_winner:<12}")

tet_recall_diff = personalized_tethys_metrics['mean_recall'] - generic_tethys_metrics['mean_recall']
tet_recall_winner = "Personalized" if tet_recall_diff > 0.01 else "Generic" if tet_recall_diff < -0.01 else "Tie"

print(f"{'Tethys Recall':<20} {generic_tethys_metrics['mean_recall']:<12.3f} "
      f"{personalized_tethys_metrics['mean_recall']:<12.3f} "
      f"{tet_recall_diff:+.3f}        {tet_recall_winner:<12}")

# Overall comparison
print(f"\n{'OVERALL (Combined)':<20}")
generic_combined_f1 = (generic_novaris_metrics['mean_f1'] + generic_tethys_metrics['mean_f1']) / 2
personalized_combined_f1 = (personalized_novaris_metrics['mean_f1'] + personalized_tethys_metrics['mean_f1']) / 2
combined_diff = personalized_combined_f1 - generic_combined_f1
combined_pct = (combined_diff / generic_combined_f1 * 100) if generic_combined_f1 > 0 else 0
combined_winner = "Personalized" if combined_diff > 0.01 else "Generic" if combined_diff < -0.01 else "Tie"

print(f"{'Combined F1':<20} {generic_combined_f1:<12.3f} "
      f"{personalized_combined_f1:<12.3f} "
      f"{combined_diff:+.3f} ({combined_pct:+.1f}%)  {combined_winner:<12}")

# Prediction diversity
print(f"\n{'Prediction Diversity':<20}")
print(f"{'Generic':<20} {generic_novaris_metrics['prediction_diversity']:.3f} (Novaris)  "
      f"{generic_tethys_metrics['prediction_diversity']:.3f} (Tethys)")
print(f"{'Personalized':<20} {personalized_novaris_metrics['prediction_diversity']:.3f} (Novaris)  "
      f"{personalized_tethys_metrics['prediction_diversity']:.3f} (Tethys)")

print("\n" + "="*80)
print("CONCLUSION:")
print("="*80)

if combined_diff > 0.05:
    print("\n[OK] PERSONALIZED WINS: Cognitive profiles improve prediction accuracy")
    print(f"     Personalized agents achieved {combined_pct:.1f}% better F1 score")
    print(f"     Evidence that expertise and cognitive traits matter for strategic forecasting")
elif combined_diff < -0.05:
    print("\n[UNEXPECTED] GENERIC WINS: Personalization actually hurt performance")
    print(f"     Generic agents achieved {-combined_pct:.1f}% better F1 score")
    print(f"     May indicate that persona details are distracting or adding noise")
else:
    print("\n[NEUTRAL] TIE: No clear advantage for personalization")
    print(f"     Difference: {combined_pct:+.1f}% (too small to be conclusive)")
    print(f"     May need larger sample size (N=5 too small) to detect effect")

print("\n" + "="*80)

# API stats
stats = forecaster.get_statistics()
print(f"\nAPI Statistics:")
print(f"  Total calls: {stats['total_calls']}")
print(f"  Success rate: {stats['success_rate']*100:.1f}%")

print("\n[OK] Comparison test complete!")
