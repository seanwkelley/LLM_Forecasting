"""
Full 10-Period Comparison with Ensemble Evaluation

Compares:
- Individual average F1 (baseline)
- Ensemble F1 (multiple aggregation methods)

Saves individual predictions for future analysis.
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
from forecasting.action_evaluation import (
    evaluate_action_set_prediction,
    evaluate_aggregate_predictions
)
from forecasting.ensemble_aggregation import (
    majority_voting_ensemble,
    top_k_ensemble,
    adaptive_threshold_ensemble
)
from forecasting.forecaster_base import BaseLLMForecaster
from forecasting.persona_simplified import load_simplified_personas
from forecasting.config import RANDOM_SEED

print("="*80)
print("FULL 10-PERIOD COMPARISON: GENERIC vs SIMPLIFIED (WITH ENSEMBLE)")
print("="*80)
print("N=100 agents per condition per period")
print("Total predictions: 4,000")
print("Saving individual predictions for future analysis")
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
                   plausible_text: str, ground_truth: dict):
    """
    Run predictions for a single period and return both individual and ensemble results.

    Returns:
        {
            'individual_metrics': {...},
            'ensemble_metrics': {...},
            'novaris_predictions': [...],
            'tethys_predictions': [...]
        }
    """

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
                return {'predicted_actions': [], '_status': 'api_failure'}

            result = json.loads(response_text)
            return {'predicted_actions': result.get('predicted_actions', []), '_status': 'success'}
        except Exception as e:
            print(f"[ERROR] API call exception: {str(e)[:60]}")
            return {'predicted_actions': [], '_status': 'parse_error'}

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

    # Individual metrics (averaging individual F1 scores)
    nov_individual = evaluate_aggregate_predictions(novaris_preds, novaris_actual)
    tet_individual = evaluate_aggregate_predictions(tethys_preds, tethys_actual)

    # Ensemble metrics (aggregate predictions first, then evaluate)
    # Use adaptive threshold to match ground truth size
    nov_ensemble = adaptive_threshold_ensemble(novaris_preds, target_set_size=len(novaris_actual))
    tet_ensemble = adaptive_threshold_ensemble(tethys_preds, target_set_size=len(tethys_actual))

    nov_ensemble_metrics = evaluate_action_set_prediction(nov_ensemble, novaris_actual)
    tet_ensemble_metrics = evaluate_action_set_prediction(tet_ensemble, tethys_actual)

    return {
        'period': period,
        'condition': condition,

        # Individual metrics (mean of individual F1s)
        'individual': {
            'novaris_f1': nov_individual['mean_f1'],
            'novaris_precision': nov_individual['mean_precision'],
            'novaris_recall': nov_individual['mean_recall'],
            'tethys_f1': tet_individual['mean_f1'],
            'tethys_precision': tet_individual['mean_precision'],
            'tethys_recall': tet_individual['mean_recall'],
            'combined_f1': (nov_individual['mean_f1'] + tet_individual['mean_f1']) / 2
        },

        # Ensemble metrics (F1 of ensemble prediction)
        'ensemble': {
            'novaris_f1': nov_ensemble_metrics['f1'],
            'novaris_precision': nov_ensemble_metrics['precision'],
            'novaris_recall': nov_ensemble_metrics['recall'],
            'tethys_f1': tet_ensemble_metrics['f1'],
            'tethys_precision': tet_ensemble_metrics['precision'],
            'tethys_recall': tet_ensemble_metrics['recall'],
            'combined_f1': (nov_ensemble_metrics['f1'] + tet_ensemble_metrics['f1']) / 2
        },

        # Raw predictions for future analysis
        'predictions': {
            'novaris': novaris_preds,
            'tethys': tethys_preds
        },

        # Ground truth
        'ground_truth': {
            'novaris': novaris_actual,
            'tethys': tethys_actual
        }
    }


# Setup output directories
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
output_dir = Path(__file__).parent.parent / 'outputs' / 'action_prediction_results' / f'ensemble_experiment_{timestamp}'
output_dir.mkdir(parents=True, exist_ok=True)

predictions_dir = output_dir / 'individual_predictions'
predictions_dir.mkdir(exist_ok=True)

print(f"Output directory: {output_dir}")
print()

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
individual_results = []
ensemble_results = []
start_time = datetime.now()

for period in range(1, 11):
    print(f"\n{'='*80}")
    print(f"PERIOD {period}/10")
    print('='*80)

    # Generic condition
    print(f"\n[1/2] Running GENERIC agents...")
    generic_result = predict_period(period, 100, "generic", None, plausible_text, ground_truth)

    # Save predictions
    pred_file = predictions_dir / f'period_{period:02d}_generic.json'
    with open(pred_file, 'w') as f:
        json.dump(generic_result['predictions'], f, indent=2)

    individual_results.append({
        'period': period,
        'condition': 'generic',
        **generic_result['individual']
    })

    ensemble_results.append({
        'period': period,
        'condition': 'generic',
        **generic_result['ensemble']
    })

    print(f"  Individual: Novaris F1={generic_result['individual']['novaris_f1']:.3f}, "
          f"Tethys F1={generic_result['individual']['tethys_f1']:.3f}, "
          f"Combined={generic_result['individual']['combined_f1']:.3f}")
    print(f"  Ensemble:   Novaris F1={generic_result['ensemble']['novaris_f1']:.3f}, "
          f"Tethys F1={generic_result['ensemble']['tethys_f1']:.3f}, "
          f"Combined={generic_result['ensemble']['combined_f1']:.3f}")

    # Simplified condition
    print(f"\n[2/2] Running SIMPLIFIED PERSONALIZED agents...")
    simplified_result = predict_period(period, 100, "simplified", personas, plausible_text, ground_truth)

    # Save predictions
    pred_file = predictions_dir / f'period_{period:02d}_simplified.json'
    with open(pred_file, 'w') as f:
        json.dump(simplified_result['predictions'], f, indent=2)

    individual_results.append({
        'period': period,
        'condition': 'simplified',
        **simplified_result['individual']
    })

    ensemble_results.append({
        'period': period,
        'condition': 'simplified',
        **simplified_result['ensemble']
    })

    print(f"  Individual: Novaris F1={simplified_result['individual']['novaris_f1']:.3f}, "
          f"Tethys F1={simplified_result['individual']['tethys_f1']:.3f}, "
          f"Combined={simplified_result['individual']['combined_f1']:.3f}")
    print(f"  Ensemble:   Novaris F1={simplified_result['ensemble']['novaris_f1']:.3f}, "
          f"Tethys F1={simplified_result['ensemble']['tethys_f1']:.3f}, "
          f"Combined={simplified_result['ensemble']['combined_f1']:.3f}")

    # Period comparison
    ind_diff = simplified_result['individual']['combined_f1'] - generic_result['individual']['combined_f1']
    ens_diff = simplified_result['ensemble']['combined_f1'] - generic_result['ensemble']['combined_f1']

    print(f"\n  Period {period} Summary:")
    print(f"    Individual: {'Generic' if ind_diff < 0 else 'Simplified'} wins by {abs(ind_diff):.3f}")
    print(f"    Ensemble:   {'Generic' if ens_diff < 0 else 'Simplified'} wins by {abs(ens_diff):.3f}")

    elapsed = (datetime.now() - start_time).total_seconds() / 60
    remaining = (elapsed / period) * (10 - period)
    print(f"  Elapsed: {elapsed:.1f} min, Estimated remaining: {remaining:.1f} min")

total_time = (datetime.now() - start_time).total_seconds()

# Save results
individual_df = pd.DataFrame(individual_results)
individual_df.to_csv(output_dir / 'individual_results.csv', index=False)

ensemble_df = pd.DataFrame(ensemble_results)
ensemble_df.to_csv(output_dir / 'ensemble_results.csv', index=False)

# Analysis
print("\n" + "="*80)
print("FINAL RESULTS")
print("="*80)

for eval_type, df in [('INDIVIDUAL', individual_df), ('ENSEMBLE', ensemble_df)]:
    print(f"\n{eval_type} EVALUATION:")
    print("-"*80)

    generic_df = df[df['condition'] == 'generic']
    simplified_df = df[df['condition'] == 'simplified']

    gen_combined = generic_df['combined_f1'].mean()
    sim_combined = simplified_df['combined_f1'].mean()
    diff = gen_combined - sim_combined
    pct = (diff / sim_combined * 100) if sim_combined > 0 else 0

    print(f"  Generic:    {gen_combined:.3f}")
    print(f"  Simplified: {sim_combined:.3f}")
    print(f"  Difference: {diff:+.3f} ({pct:+.1f}%)")
    print(f"  Winner:     {'Generic' if diff > 0 else 'Simplified'} by {abs(pct):.1f}%")

# Ensemble improvement
print("\n" + "="*80)
print("ENSEMBLE IMPROVEMENT")
print("="*80)

gen_ind = individual_df[individual_df['condition'] == 'generic']['combined_f1'].mean()
gen_ens = ensemble_df[ensemble_df['condition'] == 'generic']['combined_f1'].mean()
gen_improvement = gen_ens - gen_ind
gen_pct = (gen_improvement / gen_ind * 100) if gen_ind > 0 else 0

sim_ind = individual_df[individual_df['condition'] == 'simplified']['combined_f1'].mean()
sim_ens = ensemble_df[ensemble_df['condition'] == 'simplified']['combined_f1'].mean()
sim_improvement = sim_ens - sim_ind
sim_pct = (sim_improvement / sim_ind * 100) if sim_ind > 0 else 0

print(f"\nGeneric:")
print(f"  Individual: {gen_ind:.3f}")
print(f"  Ensemble:   {gen_ens:.3f}")
print(f"  Improvement: {gen_improvement:+.3f} ({gen_pct:+.1f}%)")

print(f"\nSimplified:")
print(f"  Individual: {sim_ind:.3f}")
print(f"  Ensemble:   {sim_ens:.3f}")
print(f"  Improvement: {sim_improvement:+.3f} ({sim_pct:+.1f}%)")

print(f"\n{'='*80}")
print("EXECUTION SUMMARY")
print("="*80)
print(f"  Total time: {total_time/60:.1f} minutes")
print(f"  Total API calls: 4,000")
print(f"  Predictions saved: {predictions_dir}")
print(f"  Results saved: {output_dir}")
print()
