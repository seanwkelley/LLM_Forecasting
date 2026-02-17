"""
Large-scale comparison: Simplified Personalized vs Generic agents (N=100 each)

Tests if simplified domain expertise profiles improve action prediction.
"""

import sys
sys.path.insert(0, 'D:/Northeastern/LLM_Forecasting')

import json
import random
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from forecasting.action_ground_truth import load_ground_truth
from forecasting.action_library import load_plausible_actions, format_plausible_actions_for_prompt
from forecasting.action_prompts import (
    create_novaris_action_prediction_prompt,
    create_tethys_action_prediction_prompt
)
from forecasting.action_evaluation import evaluate_aggregate_predictions
from forecasting.forecaster_base import BaseLLMForecaster
from forecasting.persona_simplified import load_simplified_personas
from forecasting.config import RANDOM_SEED

print("="*80)
print("SIMPLIFIED PERSONAS vs GENERIC COMPARISON")
print("="*80)
print("N=100 agents per condition (400 total predictions)")
print("Period 10 action prediction")
print()

# Setup
print("Loading resources...")
ground_truth = load_ground_truth()
period_10_truth = ground_truth[10]
novaris_actual = period_10_truth['major_power']['actions']
tethys_actual = period_10_truth['small_power']['actions']

print(f"  Ground truth - Novaris: {len(novaris_actual)} actions")
print(f"  Ground truth - Tethys: {len(tethys_actual)} actions")

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

# Load simplified personas
all_personas = load_simplified_personas()
random.seed(RANDOM_SEED)
test_personas = random.sample(all_personas, 100)
random.seed()

print(f"  Sampled 100 diverse simplified personas")
print()

# Generic system prompt (same as before)
generic_system_prompt = """You are an expert strategic analyst specializing in geopolitical forecasting.

Your task is to predict which actions a faction will take based on strategic analysis.
Apply rigorous strategic reasoning. Output ONLY valid JSON in the exact format specified."""

# ============================================================================
# CONDITION 1: GENERIC AGENTS (100 predictions)
# ============================================================================

print("="*80)
print("CONDITION 1: GENERIC AGENTS (baseline)")
print("="*80)

start_time = datetime.now()

def predict_generic(faction, prompt_func, actual_actions=None):
    """Run generic predictions in parallel."""
    predictions = []
    forecaster = BaseLLMForecaster(model="deepseek/deepseek-v3.2")

    def make_prediction(agent_id):
        if faction == 'novaris':
            prompt = prompt_func(
                period=10,
                state_before=state_period_9,
                external_events=events_period_10,
                plausible_actions_text=plausible_text
            )
        else:  # tethys
            prompt = prompt_func(
                period=10,
                state_before=state_period_9,
                external_events=events_period_10,
                novaris_actions=actual_actions,
                plausible_actions_text=plausible_text
            )

        try:
            response_text, success = forecaster.call_llm(
                user_prompt=prompt,
                system_prompt=generic_system_prompt,
                response_format="json"
            )

            if not success:
                return {'agent_id': agent_id, 'predicted_actions': [], 'error': 'LLM call failed'}

            result = json.loads(response_text)
            return {
                'agent_id': agent_id,
                'predicted_actions': result.get('predicted_actions', [])
            }
        except Exception as e:
            return {'agent_id': agent_id, 'predicted_actions': [], 'error': str(e)}

    # Parallel execution
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(make_prediction, i): i for i in range(100)}

        completed = 0
        for future in as_completed(futures):
            result = future.result()
            predictions.append(result)
            completed += 1

            if completed % 20 == 0:
                print(f"  Progress: {completed}/100 predictions")

    return predictions

print("\nNovaris predictions (Generic)...")
generic_novaris_predictions = predict_generic('novaris', create_novaris_action_prediction_prompt)

print("\nTethys predictions (Generic, with Novaris actions)...")
generic_tethys_predictions = predict_generic('tethys', create_tethys_action_prediction_prompt, novaris_actual)

# Evaluate
generic_novaris_metrics = evaluate_aggregate_predictions(generic_novaris_predictions, novaris_actual)
generic_tethys_metrics = evaluate_aggregate_predictions(generic_tethys_predictions, tethys_actual)

generic_time = (datetime.now() - start_time).total_seconds()

print("\n" + "="*80)
print("GENERIC RESULTS (N=100):")
print("="*80)
print(f"\nNovaris:")
print(f"  F1:        {generic_novaris_metrics['mean_f1']:.3f} ± {generic_novaris_metrics['std_f1']:.3f}")
print(f"  Precision: {generic_novaris_metrics['mean_precision']:.3f} ± {generic_novaris_metrics['std_precision']:.3f}")
print(f"  Recall:    {generic_novaris_metrics['mean_recall']:.3f} ± {generic_novaris_metrics['std_recall']:.3f}")
print(f"  Jaccard:   {generic_novaris_metrics['mean_jaccard']:.3f}")

print(f"\nTethys:")
print(f"  F1:        {generic_tethys_metrics['mean_f1']:.3f} ± {generic_tethys_metrics['std_f1']:.3f}")
print(f"  Precision: {generic_tethys_metrics['mean_precision']:.3f} ± {generic_tethys_metrics['std_precision']:.3f}")
print(f"  Recall:    {generic_tethys_metrics['mean_recall']:.3f} ± {generic_tethys_metrics['std_recall']:.3f}")
print(f"  Jaccard:   {generic_tethys_metrics['mean_jaccard']:.3f}")

print(f"\nTime: {generic_time:.1f}s")

# ============================================================================
# CONDITION 2: SIMPLIFIED PERSONALIZED AGENTS (100 predictions)
# ============================================================================

print("\n" + "="*80)
print("CONDITION 2: SIMPLIFIED PERSONALIZED AGENTS")
print("="*80)

start_time = datetime.now()

def predict_simplified(faction, prompt_func, personas, actual_actions=None):
    """Run simplified personalized predictions in parallel."""
    predictions = []
    forecaster = BaseLLMForecaster(model="deepseek/deepseek-v3.2")

    def make_prediction(agent_id):
        persona = personas[agent_id]

        if faction == 'novaris':
            prompt = prompt_func(
                period=10,
                state_before=state_period_9,
                external_events=events_period_10,
                plausible_actions_text=plausible_text
            )
        else:  # tethys
            prompt = prompt_func(
                period=10,
                state_before=state_period_9,
                external_events=events_period_10,
                novaris_actions=actual_actions,
                plausible_actions_text=plausible_text
            )

        persona_desc = persona.to_natural_language()
        system_prompt = f"""{persona_desc}

Your task is to predict which actions a faction will take based on strategic analysis.
Draw on your domain expertise and strategic orientation when making predictions.
Output ONLY valid JSON in the exact format specified."""

        try:
            response_text, success = forecaster.call_llm(
                user_prompt=prompt,
                system_prompt=system_prompt,
                response_format="json"
            )

            if not success:
                return {
                    'agent_id': agent_id,
                    'persona_id': persona.persona_id,
                    'predicted_actions': [],
                    'error': 'LLM call failed'
                }

            result = json.loads(response_text)
            return {
                'agent_id': agent_id,
                'persona_id': persona.persona_id,
                'predicted_actions': result.get('predicted_actions', []),
                'geopolitical_expertise': persona.geopolitical_expertise,
                'military_expertise': persona.military_expertise,
                'economic_expertise': persona.economic_expertise,
                'strategic_orientation': persona.strategic_orientation
            }
        except Exception as e:
            return {
                'agent_id': agent_id,
                'persona_id': persona.persona_id,
                'predicted_actions': [],
                'error': str(e)
            }

    # Parallel execution
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(make_prediction, i): i for i in range(100)}

        completed = 0
        for future in as_completed(futures):
            result = future.result()
            predictions.append(result)
            completed += 1

            if completed % 20 == 0:
                print(f"  Progress: {completed}/100 predictions")

    return predictions

print("\nNovaris predictions (Simplified Personalized)...")
simplified_novaris_predictions = predict_simplified(
    'novaris', create_novaris_action_prediction_prompt, test_personas
)

print("\nTethys predictions (Simplified Personalized, with Novaris actions)...")
simplified_tethys_predictions = predict_simplified(
    'tethys', create_tethys_action_prediction_prompt, test_personas, novaris_actual
)

# Evaluate
simplified_novaris_metrics = evaluate_aggregate_predictions(simplified_novaris_predictions, novaris_actual)
simplified_tethys_metrics = evaluate_aggregate_predictions(simplified_tethys_predictions, tethys_actual)

simplified_time = (datetime.now() - start_time).total_seconds()

print("\n" + "="*80)
print("SIMPLIFIED PERSONALIZED RESULTS (N=100):")
print("="*80)
print(f"\nNovaris:")
print(f"  F1:        {simplified_novaris_metrics['mean_f1']:.3f} ± {simplified_novaris_metrics['std_f1']:.3f}")
print(f"  Precision: {simplified_novaris_metrics['mean_precision']:.3f} ± {simplified_novaris_metrics['std_precision']:.3f}")
print(f"  Recall:    {simplified_novaris_metrics['mean_recall']:.3f} ± {simplified_novaris_metrics['std_recall']:.3f}")
print(f"  Jaccard:   {simplified_novaris_metrics['mean_jaccard']:.3f}")

print(f"\nTethys:")
print(f"  F1:        {simplified_tethys_metrics['mean_f1']:.3f} ± {simplified_tethys_metrics['std_f1']:.3f}")
print(f"  Precision: {simplified_tethys_metrics['mean_precision']:.3f} ± {simplified_tethys_metrics['std_precision']:.3f}")
print(f"  Recall:    {simplified_tethys_metrics['mean_recall']:.3f} ± {simplified_tethys_metrics['std_recall']:.3f}")
print(f"  Jaccard:   {simplified_tethys_metrics['mean_jaccard']:.3f}")

print(f"\nTime: {simplified_time:.1f}s")

# ============================================================================
# STATISTICAL COMPARISON
# ============================================================================

print("\n" + "="*80)
print("STATISTICAL COMPARISON (N=100 each)")
print("="*80)

print(f"\n{'Metric':<25} {'Generic':<15} {'Simplified':<15} {'Difference':<15} {'Effect':<10}")
print("-"*85)

# Novaris
nov_f1_diff = simplified_novaris_metrics['mean_f1'] - generic_novaris_metrics['mean_f1']
nov_f1_pct = (nov_f1_diff / generic_novaris_metrics['mean_f1'] * 100) if generic_novaris_metrics['mean_f1'] > 0 else 0
nov_f1_effect = "LARGE" if abs(nov_f1_pct) > 20 else "MEDIUM" if abs(nov_f1_pct) > 10 else "SMALL"

print(f"{'Novaris F1':<25} {generic_novaris_metrics['mean_f1']:<15.3f} "
      f"{simplified_novaris_metrics['mean_f1']:<15.3f} {nov_f1_diff:+.3f} ({nov_f1_pct:+.1f}%)  {nov_f1_effect:<10}")

nov_recall_diff = simplified_novaris_metrics['mean_recall'] - generic_novaris_metrics['mean_recall']
print(f"{'Novaris Recall':<25} {generic_novaris_metrics['mean_recall']:<15.3f} "
      f"{simplified_novaris_metrics['mean_recall']:<15.3f} {nov_recall_diff:+.3f}")

# Tethys
tet_f1_diff = simplified_tethys_metrics['mean_f1'] - generic_tethys_metrics['mean_f1']
tet_f1_pct = (tet_f1_diff / generic_tethys_metrics['mean_f1'] * 100) if generic_tethys_metrics['mean_f1'] > 0 else 0
tet_f1_effect = "LARGE" if abs(tet_f1_pct) > 20 else "MEDIUM" if abs(tet_f1_pct) > 10 else "SMALL"

print(f"{'Tethys F1':<25} {generic_tethys_metrics['mean_f1']:<15.3f} "
      f"{simplified_tethys_metrics['mean_f1']:<15.3f} {tet_f1_diff:+.3f} ({tet_f1_pct:+.1f}%)  {tet_f1_effect:<10}")

tet_recall_diff = simplified_tethys_metrics['mean_recall'] - generic_tethys_metrics['mean_recall']
print(f"{'Tethys Recall':<25} {generic_tethys_metrics['mean_recall']:<15.3f} "
      f"{simplified_tethys_metrics['mean_recall']:<15.3f} {tet_recall_diff:+.3f}")

# Combined
print(f"\n{'OVERALL (Combined)':<25}")
generic_combined_f1 = (generic_novaris_metrics['mean_f1'] + generic_tethys_metrics['mean_f1']) / 2
simplified_combined_f1 = (simplified_novaris_metrics['mean_f1'] + simplified_tethys_metrics['mean_f1']) / 2
combined_diff = simplified_combined_f1 - generic_combined_f1
combined_pct = (combined_diff / generic_combined_f1 * 100) if generic_combined_f1 > 0 else 0
combined_effect = "LARGE" if abs(combined_pct) > 20 else "MEDIUM" if abs(combined_pct) > 10 else "SMALL"

print(f"{'Combined F1':<25} {generic_combined_f1:<15.3f} "
      f"{simplified_combined_f1:<15.3f} {combined_diff:+.3f} ({combined_pct:+.1f}%)  {combined_effect:<10}")

# ============================================================================
# CONCLUSION
# ============================================================================

print("\n" + "="*80)
print("CONCLUSION (N=100, statistically powered)")
print("="*80)

if combined_diff > 0.05:
    print(f"\n[OK] SIMPLIFIED WINS: {combined_pct:.1f}% improvement")
    print(f"     Domain expertise helps - cognitive noise removed")
    if nov_f1_diff > 0.05 and tet_f1_diff > 0.05:
        print(f"     Effect consistent across both factions")
    elif nov_f1_diff > 0.05:
        print(f"     Effect stronger for Novaris (offensive planning)")
    elif tet_f1_diff > 0.05:
        print(f"     Effect stronger for Tethys (reactive defense)")

elif combined_diff < -0.05:
    print(f"\n[FAIL] GENERIC WINS: {-combined_pct:.1f}% better")
    print(f"     Even simplified personas add noise")
    if nov_f1_diff < -0.05 and tet_f1_diff < -0.05:
        print(f"     Effect consistent across both factions")

else:
    print(f"\n[NEUTRAL] NO SIGNIFICANT DIFFERENCE: {combined_pct:+.1f}%")
    print(f"     Simplified personas neither help nor hurt significantly")
    print(f"     Proceed with generic agents for full experiment")

print("\n" + "="*80)
print(f"Total time: {(generic_time + simplified_time)/60:.1f} minutes")
print(f"Total API calls: 400")
print("[OK] Simplified persona comparison complete!")
