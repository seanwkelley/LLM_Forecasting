"""
Full 10-Period Comparison: Generic vs Simplified Personalized Agents

Runs both conditions across all 10 periods to compare performance over time.
"""

import sys
sys.path.insert(0, 'D:/Northeastern/LLM_Forecasting')

import json
import random
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import pandas as pd

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
print("FULL 10-PERIOD COMPARISON: GENERIC vs SIMPLIFIED PERSONALIZED")
print("="*80)
print("N=100 agents per condition per period")
print("Total predictions: 4,000 (10 periods × 2 factions × 2 conditions × 100 agents)")
print()


def load_period_state(period: int) -> dict:
    """Load state variables for a given period"""
    states = {
        1: {'territory_controlled': 0.02, 'military_balance': 0.0, 'crisis_level': 4.0,
            'novaris_gdp': 100.0, 'tethys_gdp': 30.0, 'international_support': 0.45, 'sanctions_level': 0.15},
        2: {'territory_controlled': 0.05, 'military_balance': -0.02, 'crisis_level': 5.0,
            'novaris_gdp': 98.0, 'tethys_gdp': 29.0, 'international_support': 0.48, 'sanctions_level': 0.20},
        3: {'territory_controlled': 0.08, 'military_balance': -0.03, 'crisis_level': 5.5,
            'novaris_gdp': 96.0, 'tethys_gdp': 28.5, 'international_support': 0.50, 'sanctions_level': 0.25},
        4: {'territory_controlled': 0.10, 'military_balance': -0.04, 'crisis_level': 6.0,
            'novaris_gdp': 94.0, 'tethys_gdp': 28.0, 'international_support': 0.52, 'sanctions_level': 0.28},
        5: {'territory_controlled': 0.12, 'military_balance': -0.05, 'crisis_level': 6.5,
            'novaris_gdp': 92.0, 'tethys_gdp': 27.5, 'international_support': 0.54, 'sanctions_level': 0.32},
        6: {'territory_controlled': 0.14, 'military_balance': -0.06, 'crisis_level': 7.0,
            'novaris_gdp': 90.0, 'tethys_gdp': 27.0, 'international_support': 0.56, 'sanctions_level': 0.36},
        7: {'territory_controlled': 0.16, 'military_balance': -0.07, 'crisis_level': 7.2,
            'novaris_gdp': 89.0, 'tethys_gdp': 26.5, 'international_support': 0.57, 'sanctions_level': 0.38},
        8: {'territory_controlled': 0.17, 'military_balance': -0.075, 'crisis_level': 7.3,
            'novaris_gdp': 88.5, 'tethys_gdp': 26.2, 'international_support': 0.575, 'sanctions_level': 0.40},
        9: {'territory_controlled': 0.18, 'military_balance': -0.08, 'crisis_level': 7.5,
            'novaris_gdp': 88.0, 'tethys_gdp': 26.0, 'international_support': 0.58, 'sanctions_level': 0.42},
        10: {'territory_controlled': 0.18, 'military_balance': -0.08, 'crisis_level': 7.5,
             'novaris_gdp': 88.0, 'tethys_gdp': 26.0, 'international_support': 0.58, 'sanctions_level': 0.42}
    }
    return states[period]


def load_period_events(period: int) -> list:
    """Load external events for a given period"""
    events_by_period = {
        1: [
            "Diplomatic: Initial tensions escalate at border",
            "Military: Minor skirmishes reported",
            "Economic: Sanctions discussions begin",
            "Intelligence: Increased surveillance activities"
        ],
        2: [
            "Military: Border incursion by Novaris forces",
            "Diplomatic: International condemnation of aggression",
            "Economic: First round of sanctions imposed",
            "Intelligence: Cyber attacks against government infrastructure"
        ],
        3: [
            "Battlefield: Novaris captures border territory",
            "Diplomatic: Emergency UN Security Council meeting",
            "Economic: Tethys seeks international aid",
            "Intelligence: Espionage activities intensify"
        ],
        4: [
            "Battlefield: Continued territorial advances by Novaris",
            "Economic: Energy sanctions expanded",
            "Diplomatic: Ceasefire negotiations attempted",
            "Intelligence: Signals intelligence indicates military buildup"
        ],
        5: [
            "Battlefield: Tethys defensive line holds against assault",
            "Economic: Humanitarian crisis deepens",
            "Diplomatic: Regional powers take sides",
            "Intelligence: Reports of foreign military advisors"
        ],
        6: [
            "Battlefield: Urban combat in contested cities",
            "Economic: Oil prices spike globally",
            "Diplomatic: Mediation efforts by neutral parties",
            "Intelligence: Intercepted communications reveal plans"
        ],
        7: [
            "Battlefield: Stalemate develops on main front",
            "Economic: Tethys economy contracts sharply",
            "Diplomatic: International pressure for peace talks",
            "Intelligence: Counter-intelligence operations intensify"
        ],
        8: [
            "Battlefield: Novaris attempts encirclement maneuver",
            "Economic: Novaris faces supply chain disruptions",
            "Diplomatic: Humanitarian corridor negotiations",
            "Intelligence: Cyber warfare escalates"
        ],
        9: [
            "Battlefield: Heavy casualties on both sides",
            "Economic: International aid package for Tethys",
            "Diplomatic: Back-channel negotiations reported",
            "Intelligence: Strategic assets targeted"
        ],
        10: [
            "Battlefield: Aggressor breakthrough - significant territorial gains and encirclement",
            "Economic: Energy price surge due to supply disruptions",
            "Diplomatic: Peace talks proposed but tensions remain high",
            "Intelligence: Reports of covert operations by both sides"
        ]
    }
    return events_by_period[period]


def predict_period(period: int, n_agents: int, condition: str, personas: list,
                   plausible_text: str, ground_truth: dict) -> dict:
    """Run predictions for a single period"""

    state = load_period_state(period)
    events = load_period_events(period)
    novaris_actual = ground_truth[period]['major_power']['actions']
    tethys_actual = ground_truth[period]['small_power']['actions']

    forecaster = BaseLLMForecaster(model="deepseek/deepseek-v3.2")

    if condition == "generic":
        system_prompt_base = """You are an expert strategic analyst specializing in geopolitical forecasting.

Your task is to predict which actions a faction will take based on strategic analysis.
Apply rigorous strategic reasoning. Output ONLY valid JSON in the exact format specified."""

    def make_prediction(agent_id, faction, prompt_func, actual_actions=None):
        if faction == 'novaris':
            prompt = prompt_func(
                period=period,
                state_before=state,
                external_events=events,
                plausible_actions_text=plausible_text
            )
        else:
            prompt = prompt_func(
                period=period,
                state_before=state,
                external_events=events,
                novaris_actions=actual_actions,
                plausible_actions_text=plausible_text
            )

        if condition == "generic":
            system_prompt = system_prompt_base
        else:  # simplified
            persona = personas[agent_id]
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
                return {'predicted_actions': []}

            result = json.loads(response_text)
            return {'predicted_actions': result.get('predicted_actions', [])}
        except:
            return {'predicted_actions': []}

    # Novaris predictions
    novaris_preds = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(make_prediction, i, 'novaris', create_novaris_action_prediction_prompt)
            for i in range(n_agents)
        ]
        novaris_preds = [f.result() for f in as_completed(futures)]

    # Tethys predictions
    tethys_preds = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(make_prediction, i, 'tethys', create_tethys_action_prediction_prompt, novaris_actual)
            for i in range(n_agents)
        ]
        tethys_preds = [f.result() for f in as_completed(futures)]

    # Evaluate
    nov_metrics = evaluate_aggregate_predictions(novaris_preds, novaris_actual)
    tet_metrics = evaluate_aggregate_predictions(tethys_preds, tethys_actual)

    return {
        'period': period,
        'condition': condition,
        'novaris_f1': nov_metrics['mean_f1'],
        'novaris_precision': nov_metrics['mean_precision'],
        'novaris_recall': nov_metrics['mean_recall'],
        'novaris_jaccard': nov_metrics['mean_jaccard'],
        'tethys_f1': tet_metrics['mean_f1'],
        'tethys_precision': tet_metrics['mean_precision'],
        'tethys_recall': tet_metrics['mean_recall'],
        'tethys_jaccard': tet_metrics['mean_jaccard'],
        'combined_f1': (nov_metrics['mean_f1'] + tet_metrics['mean_f1']) / 2,
        'n_novaris_actions': len(novaris_actual),
        'n_tethys_actions': len(tethys_actual)
    }


# Load resources
print("Loading resources...")
ground_truth = load_ground_truth()
plausible, descriptions = load_plausible_actions()
plausible_text = format_plausible_actions_for_prompt(plausible, descriptions)

all_personas = load_simplified_personas()
random.seed(RANDOM_SEED)
personas = random.sample(all_personas, 100)
random.seed()

print(f"  Ground truth loaded: {sum(len(ground_truth[p]['major_power']['actions']) for p in range(1,11))} Novaris actions")
print(f"  Sampled 100 simplified personas")
print()

# Run experiment
results = []
start_time = datetime.now()

for period in range(1, 11):
    print(f"\n{'='*80}")
    print(f"PERIOD {period}/10")
    print('='*80)

    # Generic condition
    print(f"\n[1/2] Running GENERIC agents...")
    generic_result = predict_period(period, 100, "generic", None, plausible_text, ground_truth)
    results.append(generic_result)

    print(f"  Novaris F1: {generic_result['novaris_f1']:.3f}")
    print(f"  Tethys F1:  {generic_result['tethys_f1']:.3f}")
    print(f"  Combined:   {generic_result['combined_f1']:.3f}")

    # Simplified condition
    print(f"\n[2/2] Running SIMPLIFIED PERSONALIZED agents...")
    simplified_result = predict_period(period, 100, "simplified", personas, plausible_text, ground_truth)
    results.append(simplified_result)

    print(f"  Novaris F1: {simplified_result['novaris_f1']:.3f}")
    print(f"  Tethys F1:  {simplified_result['tethys_f1']:.3f}")
    print(f"  Combined:   {simplified_result['combined_f1']:.3f}")

    # Comparison
    diff = simplified_result['combined_f1'] - generic_result['combined_f1']
    diff_pct = (diff / generic_result['combined_f1'] * 100) if generic_result['combined_f1'] > 0 else 0
    winner = "Simplified" if diff > 0 else "Generic" if diff < 0 else "Tie"

    print(f"\n  Period {period} Winner: {winner} ({diff:+.3f}, {diff_pct:+.1f}%)")

    elapsed = (datetime.now() - start_time).total_seconds() / 60
    remaining = (elapsed / period) * (10 - period)
    print(f"  Elapsed: {elapsed:.1f} min, Estimated remaining: {remaining:.1f} min")

total_time = (datetime.now() - start_time).total_seconds()

# Save results
output_dir = Path(__file__).parent.parent / 'outputs' / 'action_prediction_results'
output_dir.mkdir(parents=True, exist_ok=True)

timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
results_file = output_dir / f'full_comparison_{timestamp}.csv'

df = pd.DataFrame(results)
df.to_csv(results_file, index=False)

# Analysis
print("\n" + "="*80)
print("FINAL RESULTS: GENERIC vs SIMPLIFIED PERSONALIZED")
print("="*80)

generic_df = df[df['condition'] == 'generic']
simplified_df = df[df['condition'] == 'simplified']

print(f"\nMean Performance Across 10 Periods:")
print(f"\n{'Metric':<25} {'Generic':<15} {'Simplified':<15} {'Difference':<15}")
print("-"*70)

gen_nov_f1 = generic_df['novaris_f1'].mean()
sim_nov_f1 = simplified_df['novaris_f1'].mean()
nov_diff = sim_nov_f1 - gen_nov_f1
nov_pct = (nov_diff / gen_nov_f1 * 100) if gen_nov_f1 > 0 else 0

print(f"{'Novaris F1':<25} {gen_nov_f1:<15.3f} {sim_nov_f1:<15.3f} {nov_diff:+.3f} ({nov_pct:+.1f}%)")

gen_tet_f1 = generic_df['tethys_f1'].mean()
sim_tet_f1 = simplified_df['tethys_f1'].mean()
tet_diff = sim_tet_f1 - gen_tet_f1
tet_pct = (tet_diff / gen_tet_f1 * 100) if gen_tet_f1 > 0 else 0

print(f"{'Tethys F1':<25} {gen_tet_f1:<15.3f} {sim_tet_f1:<15.3f} {tet_diff:+.3f} ({tet_pct:+.1f}%)")

gen_combined = generic_df['combined_f1'].mean()
sim_combined = simplified_df['combined_f1'].mean()
combined_diff = sim_combined - gen_combined
combined_pct = (combined_diff / gen_combined * 100) if gen_combined > 0 else 0

print(f"{'Combined F1':<25} {gen_combined:<15.3f} {sim_combined:<15.3f} {combined_diff:+.3f} ({combined_pct:+.1f}%)")

print(f"\nInformation Advantage (Tethys - Novaris):")
gen_info_adv = gen_tet_f1 - gen_nov_f1
sim_info_adv = sim_tet_f1 - sim_nov_f1
print(f"  Generic:    {gen_info_adv:+.3f}")
print(f"  Simplified: {sim_info_adv:+.3f}")

print(f"\nWins by Period:")
wins = {'Generic': 0, 'Simplified': 0, 'Tie': 0}
for period in range(1, 11):
    gen_row = generic_df[generic_df['period'] == period].iloc[0]
    sim_row = simplified_df[simplified_df['period'] == period].iloc[0]

    diff = sim_row['combined_f1'] - gen_row['combined_f1']
    if abs(diff) < 0.01:
        winner = 'Tie'
    elif diff > 0:
        winner = 'Simplified'
    else:
        winner = 'Generic'

    wins[winner] += 1

print(f"  Generic wins:    {wins['Generic']}/10 periods")
print(f"  Simplified wins: {wins['Simplified']}/10 periods")
print(f"  Ties:            {wins['Tie']}/10 periods")

print(f"\nExecution:")
print(f"  Total time: {total_time/60:.1f} minutes")
print(f"  Total API calls: 4,000")
print(f"  Average per period: {total_time/10:.1f} seconds")

print(f"\nResults saved to: {results_file}")

# Final verdict
print("\n" + "="*80)
print("CONCLUSION")
print("="*80)

if combined_pct > 5:
    print(f"\n[OK] SIMPLIFIED WINS: {combined_pct:.1f}% improvement across all periods")
    print("     Domain expertise provides consistent benefit")
elif combined_pct < -5:
    print(f"\n[FAIL] GENERIC WINS: {-combined_pct:.1f}% better across all periods")
    print("     Personalization consistently adds noise")
else:
    print(f"\n[NEUTRAL] NO SIGNIFICANT DIFFERENCE: {combined_pct:+.1f}%")
    print("     Neither approach shows clear advantage")

print("\n[OK] Full 10-period comparison complete!")
