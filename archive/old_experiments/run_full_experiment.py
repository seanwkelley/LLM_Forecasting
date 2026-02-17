"""
Full 10-Period Action Prediction Experiment

Tests action prediction across all periods with either:
- Generic agents (baseline)
- Simplified personalized agents (if they prove beneficial)

Usage:
    python run_full_experiment.py --condition generic --n_agents 100
    python run_full_experiment.py --condition simplified --n_agents 100
"""

import sys
sys.path.insert(0, 'D:/Northeastern/LLM_Forecasting')

import json
import random
import argparse
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


def load_period_state(period: int) -> dict:
    """
    Load state variables for a given period.

    In production, this would read from simulation output CSVs.
    For now, using approximate values.
    """
    # Placeholder - would load from outputs/state_history.csv
    # For now, return reasonable approximations

    # These are rough approximations based on typical simulation trajectory
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

    return states.get(period, states[10])


def load_period_events(period: int) -> list:
    """
    Load external events for a given period.

    In production, would read from simulation event logs.
    """
    # Placeholder - would parse from outputs/period_XX_actions.csv or event logs
    # For now, generic event templates

    events_templates = {
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
        # ... would continue for all periods
        10: [
            "Battlefield: Aggressor breakthrough - significant territorial gains and encirclement",
            "Economic: Energy price surge due to supply disruptions",
            "Diplomatic: Peace talks proposed but tensions remain high",
            "Intelligence: Reports of covert operations by both sides"
        ]
    }

    return events_templates.get(period, events_templates[10])


def predict_period_generic(period: int, n_agents: int, plausible_text: str,
                          ground_truth: dict) -> dict:
    """Run generic predictions for a single period"""

    state = load_period_state(period)
    events = load_period_events(period)
    novaris_actual = ground_truth[period]['major_power']['actions']
    tethys_actual = ground_truth[period]['small_power']['actions']

    print(f"\n  Period {period}: {len(novaris_actual)} Novaris actions, {len(tethys_actual)} Tethys actions")

    forecaster = BaseLLMForecaster(model="deepseek/deepseek-v3.2")

    generic_system_prompt = """You are an expert strategic analyst specializing in geopolitical forecasting.

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

        try:
            response_text, success = forecaster.call_llm(
                user_prompt=prompt,
                system_prompt=generic_system_prompt,
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
        'novaris_f1': nov_metrics['mean_f1'],
        'novaris_precision': nov_metrics['mean_precision'],
        'novaris_recall': nov_metrics['mean_recall'],
        'tethys_f1': tet_metrics['mean_f1'],
        'tethys_precision': tet_metrics['mean_precision'],
        'tethys_recall': tet_metrics['mean_recall'],
        'combined_f1': (nov_metrics['mean_f1'] + tet_metrics['mean_f1']) / 2
    }


def predict_period_simplified(period: int, n_agents: int, personas: list,
                              plausible_text: str, ground_truth: dict) -> dict:
    """Run simplified personalized predictions for a single period"""

    state = load_period_state(period)
    events = load_period_events(period)
    novaris_actual = ground_truth[period]['major_power']['actions']
    tethys_actual = ground_truth[period]['small_power']['actions']

    print(f"\n  Period {period}: {len(novaris_actual)} Novaris actions, {len(tethys_actual)} Tethys actions")

    forecaster = BaseLLMForecaster(model="deepseek/deepseek-v3.2")

    def make_prediction(agent_id, faction, prompt_func, actual_actions=None):
        persona = personas[agent_id]

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
        'novaris_f1': nov_metrics['mean_f1'],
        'novaris_precision': nov_metrics['mean_precision'],
        'novaris_recall': nov_metrics['mean_recall'],
        'tethys_f1': tet_metrics['mean_f1'],
        'tethys_precision': tet_metrics['mean_precision'],
        'tethys_recall': tet_metrics['mean_recall'],
        'combined_f1': (nov_metrics['mean_f1'] + tet_metrics['mean_f1']) / 2
    }


def main():
    parser = argparse.ArgumentParser(description='Run full 10-period action prediction experiment')
    parser.add_argument('--condition', choices=['generic', 'simplified'], default='generic',
                       help='Forecasting condition')
    parser.add_argument('--n_agents', type=int, default=100,
                       help='Number of agents per prediction')
    parser.add_argument('--periods', type=int, default=10,
                       help='Number of periods to predict (1-10)')

    args = parser.parse_args()

    print("="*80)
    print(f"FULL EXPERIMENT: {args.condition.upper()} AGENTS")
    print("="*80)
    print(f"Periods: 1-{args.periods}")
    print(f"Agents per prediction: {args.n_agents}")
    print(f"Total predictions: {args.periods * 2 * args.n_agents} ({args.periods} periods × 2 factions × {args.n_agents} agents)")
    print()

    # Load resources
    print("Loading resources...")
    ground_truth = load_ground_truth()
    plausible, descriptions = load_plausible_actions()
    plausible_text = format_plausible_actions_for_prompt(plausible, descriptions)

    personas = None
    if args.condition == 'simplified':
        all_personas = load_simplified_personas()
        random.seed(RANDOM_SEED)
        personas = random.sample(all_personas, args.n_agents)
        random.seed()
        print(f"  Sampled {args.n_agents} simplified personas")

    print()

    # Run predictions for all periods
    results = []
    start_time = datetime.now()

    for period in range(1, args.periods + 1):
        print(f"\nPERIOD {period}/{args.periods}")
        print("-"*40)

        if args.condition == 'generic':
            result = predict_period_generic(period, args.n_agents, plausible_text, ground_truth)
        else:
            result = predict_period_simplified(period, args.n_agents, personas, plausible_text, ground_truth)

        results.append(result)

        print(f"  Novaris F1: {result['novaris_f1']:.3f}")
        print(f"  Tethys F1:  {result['tethys_f1']:.3f}")
        print(f"  Combined:   {result['combined_f1']:.3f}")

    total_time = (datetime.now() - start_time).total_seconds()

    # Save results
    output_dir = Path(__file__).parent.parent / 'outputs' / 'action_prediction_results'
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = output_dir / f'{args.condition}_{args.n_agents}agents_{timestamp}.csv'

    df = pd.DataFrame(results)
    df.to_csv(results_file, index=False)

    # Summary statistics
    print("\n" + "="*80)
    print("SUMMARY RESULTS")
    print("="*80)

    print(f"\nMean Performance Across {args.periods} Periods:")
    print(f"  Novaris F1:    {df['novaris_f1'].mean():.3f} ± {df['novaris_f1'].std():.3f}")
    print(f"  Tethys F1:     {df['tethys_f1'].mean():.3f} ± {df['tethys_f1'].std():.3f}")
    print(f"  Combined F1:   {df['combined_f1'].mean():.3f} ± {df['combined_f1'].std():.3f}")

    print(f"\nInformation Advantage (Tethys - Novaris):")
    info_adv = df['tethys_f1'].mean() - df['novaris_f1'].mean()
    info_adv_pct = (info_adv / df['novaris_f1'].mean() * 100) if df['novaris_f1'].mean() > 0 else 0
    print(f"  {info_adv:+.3f} ({info_adv_pct:+.1f}%)")

    print(f"\nExecution:")
    print(f"  Total time: {total_time/60:.1f} minutes")
    print(f"  Total API calls: {args.periods * 2 * args.n_agents}")

    print(f"\nResults saved to: {results_file}")
    print("\n[OK] Full experiment complete!")


if __name__ == "__main__":
    main()
