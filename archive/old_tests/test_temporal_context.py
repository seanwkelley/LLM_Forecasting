"""
Test adding temporal context (history) to action predictions.

Tests whether showing previous periods' actions and outcomes improves predictions.
"""

import sys
sys.path.insert(0, 'D:/Northeastern/LLM_Forecasting')

import json
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

from forecasting.action_ground_truth import load_ground_truth
from forecasting.action_library import load_plausible_actions, format_plausible_actions_for_prompt
from forecasting.action_prompts import (
    create_novaris_action_prediction_prompt,
    create_tethys_action_prediction_prompt
)
from forecasting.action_evaluation import evaluate_action_set_prediction, evaluate_aggregate_predictions
from forecasting.ensemble_aggregation import adaptive_threshold_ensemble
from forecasting.forecaster_base import BaseLLMForecaster
from forecasting.config import RANDOM_SEED

print("="*80)
print("TEMPORAL CONTEXT TEST")
print("="*80)
print("Testing: Does adding historical context improve predictions?")
print("Periods: 3-10 (need at least 2 periods of history)")
print("N: 100 generic agents per condition")
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
        1: ["Diplomatic: Initial tensions escalate at border", "Military: Minor skirmishes reported",
            "Economic: Sanctions discussions begin", "Intelligence: Increased surveillance activities"],
        2: ["Military: Border incursion by Novaris forces", "Diplomatic: International condemnation of aggression",
            "Economic: First round of sanctions imposed", "Intelligence: Cyber attacks against government infrastructure"],
        3: ["Battlefield: Novaris captures border territory", "Diplomatic: Emergency UN Security Council meeting",
            "Economic: Tethys seeks international aid", "Intelligence: Espionage activities intensify"],
        4: ["Battlefield: Continued territorial advances by Novaris", "Economic: Energy sanctions expanded",
            "Diplomatic: Ceasefire negotiations attempted", "Intelligence: Signals intelligence indicates military buildup"],
        5: ["Battlefield: Tethys defensive line holds against assault", "Economic: Humanitarian crisis deepens",
            "Diplomatic: Regional powers take sides", "Intelligence: Reports of foreign military advisors"],
        6: ["Battlefield: Urban combat in contested cities", "Economic: Oil prices spike globally",
            "Diplomatic: Mediation efforts by neutral parties", "Intelligence: Intercepted communications reveal plans"],
        7: ["Battlefield: Stalemate develops on main front", "Economic: Tethys economy contracts sharply",
            "Diplomatic: International pressure for peace talks", "Intelligence: Counter-intelligence operations intensify"],
        8: ["Battlefield: Novaris attempts encirclement maneuver", "Economic: Novaris faces supply chain disruptions",
            "Diplomatic: Humanitarian corridor negotiations", "Intelligence: Cyber warfare escalates"],
        9: ["Battlefield: Heavy casualties on both sides", "Economic: International aid package for Tethys",
            "Diplomatic: Back-channel negotiations reported", "Intelligence: Strategic assets targeted"],
        10: ["Battlefield: Aggressor breakthrough - significant territorial gains and encirclement",
             "Economic: Energy price surge due to supply disruptions", "Diplomatic: Peace talks proposed but tensions remain high",
             "Intelligence: Reports of covert operations by both sides"]
    }
    return events_by_period[period]


# Initial scenario context (external intelligence view only)
INITIAL_SCENARIO = """
BACKGROUND (Observable Intelligence):
Novaris (major regional power) has engaged in military operations against Tethys (smaller state).
Stated objective: Territorial control. Current status: Active military conflict with international
involvement. You are analyzing observable actions, state changes, and external events to predict
what strategic actions each side will take next.
"""


def create_historical_summary(ground_truth: dict, period: int) -> str:
    """
    Create summary of OBSERVABLE actions taken in periods 1 through period-1.

    Shows only external actions, not internal decision-making processes.
    Returns formatted text showing temporal evolution.
    """
    if period <= 1:
        return ""

    history_lines = ["="*80, "OBSERVED ACTION HISTORY (Intelligence Assessment)", "="*80, ""]

    # Show action history by period
    for p in range(1, period):
        novaris_actions = ground_truth[p]['major_power']['actions']
        tethys_actions = ground_truth[p]['small_power']['actions']

        history_lines.append(f"PERIOD {p} - Observed Actions:")
        history_lines.append(f"  Novaris executed: {', '.join(novaris_actions)}")
        history_lines.append(f"  Tethys executed: {', '.join(tethys_actions)}")
        history_lines.append("")

    history_lines.append("Based on observed patterns, predict what actions will be taken in the current period.")
    history_lines.append("")

    return '\n'.join(history_lines)


def create_temporal_prompt(
    faction: str,
    period: int,
    ground_truth: dict,
    plausible_text: str,
    novaris_actual_actions: list = None
) -> str:
    """
    Create prompt WITH temporal context (initial scenario + history).
    """

    base_prompt = f"""You are a strategic analyst tasked with predicting {faction.upper()}'s action set for Period {period}.

{INITIAL_SCENARIO}

{create_historical_summary(ground_truth, period)}

{'='*80}
YOUR TASK
{'='*80}

Given the background and history above, predict the COMPLETE action set {faction.upper()} will take in Period {period}.

Consider:
1. What patterns have emerged in previous periods?
2. How have they responded to opponent's actions?
3. What strategies have worked or failed?
4. How is the situation evolving over time?

"""

    if faction == 'tethys' and novaris_actual_actions:
        base_prompt += f"""
NOVARIS'S CURRENT ACTIONS (Period {period}):
{', '.join(novaris_actual_actions)}

Given Novaris's actions this period, predict Tethys's response.

"""

    base_prompt += f"""
AVAILABLE ACTIONS:
{plausible_text}

Output ONLY a JSON object with this structure:
{{
  "predicted_actions": ["action1", "action2", ...]
}}

Select 3-9 actions that {faction.upper()} will most likely take this period.
"""

    return base_prompt


def run_predictions_with_context(condition: str, n_agents: int, ground_truth: dict, plausible_text: str):
    """
    Run predictions for periods 3-10 with or without temporal context.

    Args:
        condition: "with_history" or "no_history"
        n_agents: Number of agents
        ground_truth: Full ground truth data
        plausible_text: Formatted actions

    Returns:
        Results for each period
    """

    forecaster = BaseLLMForecaster(model="deepseek/deepseek-v3.2")

    system_prompt = """You are an expert strategic analyst specializing in geopolitical forecasting.

Your task is to predict which actions a faction will take based on strategic analysis.
Apply rigorous strategic reasoning. Output ONLY valid JSON in the exact format specified."""

    results = []

    for period in range(3, 11):  # Periods 3-10 (need 2 periods of history)
        print(f"\nPeriod {period}/10...")

        novaris_actual = ground_truth[period]['major_power']['actions']
        tethys_actual = ground_truth[period]['small_power']['actions']

        def make_prediction(agent_id, faction):
            if condition == "with_history":
                prompt = create_temporal_prompt(
                    faction,
                    period,
                    ground_truth,
                    plausible_text,
                    novaris_actual if faction == 'tethys' else None
                )
            else:
                # No history version - uses SAME prompt structure as main experiment
                # (full strategic context from action_prompts.py, just without history)
                if faction == 'novaris':
                    prompt = create_novaris_action_prediction_prompt(
                        period=period,
                        state_before=load_period_state(period),
                        external_events=load_period_events(period),
                        plausible_actions_text=plausible_text
                    )
                else:
                    prompt = create_tethys_action_prediction_prompt(
                        period=period,
                        state_before=load_period_state(period),
                        external_events=load_period_events(period),
                        novaris_actions=novaris_actual,
                        plausible_actions_text=plausible_text
                    )

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
            futures = [executor.submit(make_prediction, i, 'novaris') for i in range(n_agents)]
            novaris_preds = [f.result() for f in as_completed(futures)]

        # Tethys predictions
        tethys_preds = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_prediction, i, 'tethys') for i in range(n_agents)]
            tethys_preds = [f.result() for f in as_completed(futures)]

        # Individual metrics
        nov_ind = evaluate_aggregate_predictions(novaris_preds, novaris_actual)
        tet_ind = evaluate_aggregate_predictions(tethys_preds, tethys_actual)

        # Ensemble metrics
        nov_ens = adaptive_threshold_ensemble(novaris_preds, target_set_size=len(novaris_actual))
        tet_ens = adaptive_threshold_ensemble(tethys_preds, target_set_size=len(tethys_actual))

        nov_ens_metrics = evaluate_action_set_prediction(nov_ens, novaris_actual)
        tet_ens_metrics = evaluate_action_set_prediction(tet_ens, tethys_actual)

        results.append({
            'period': period,
            'condition': condition,
            'individual': {
                'novaris_f1': nov_ind['mean_f1'],
                'tethys_f1': tet_ind['mean_f1'],
                'combined_f1': (nov_ind['mean_f1'] + tet_ind['mean_f1']) / 2
            },
            'ensemble': {
                'novaris_f1': nov_ens_metrics['f1'],
                'tethys_f1': tet_ens_metrics['f1'],
                'combined_f1': (nov_ens_metrics['f1'] + tet_ens_metrics['f1']) / 2
            }
        })

        print(f"  Individual: {results[-1]['individual']['combined_f1']:.3f}, "
              f"Ensemble: {results[-1]['ensemble']['combined_f1']:.3f}")

    return results


# Load resources
print("Loading resources...")
ground_truth = load_ground_truth()
plausible, descriptions = load_plausible_actions()
plausible_text = format_plausible_actions_for_prompt(plausible, descriptions)
print("  Ground truth loaded")
print()

# Test 1: Without history (baseline)
print("="*80)
print("CONDITION 1: NO HISTORY (Baseline)")
print("="*80)
no_history_results = run_predictions_with_context("no_history", 100, ground_truth, plausible_text)

# Test 2: With history
print("\n" + "="*80)
print("CONDITION 2: WITH HISTORY (Initial scenario + action history)")
print("="*80)
with_history_results = run_predictions_with_context("with_history", 100, ground_truth, plausible_text)

# Analysis
print("\n" + "="*80)
print("RESULTS COMPARISON")
print("="*80)

no_hist_ind = sum(r['individual']['combined_f1'] for r in no_history_results) / len(no_history_results)
no_hist_ens = sum(r['ensemble']['combined_f1'] for r in no_history_results) / len(no_history_results)

with_hist_ind = sum(r['individual']['combined_f1'] for r in with_history_results) / len(with_history_results)
with_hist_ens = sum(r['ensemble']['combined_f1'] for r in with_history_results) / len(with_history_results)

print("\nNO HISTORY:")
print(f"  Individual: {no_hist_ind:.3f}")
print(f"  Ensemble:   {no_hist_ens:.3f}")

print("\nWITH HISTORY:")
print(f"  Individual: {with_hist_ind:.3f}")
print(f"  Ensemble:   {with_hist_ens:.3f}")

print("\nIMPROVEMENT FROM ADDING HISTORY:")
ind_improvement = with_hist_ind - no_hist_ind
ens_improvement = with_hist_ens - no_hist_ens

print(f"  Individual: {ind_improvement:+.3f} ({ind_improvement/no_hist_ind*100:+.1f}%)")
print(f"  Ensemble:   {ens_improvement:+.3f} ({ens_improvement/no_hist_ens*100:+.1f}%)")

if ens_improvement > 0.05:
    print("\n[OK] HISTORY HELPS! Temporal context significantly improves predictions.")
elif ens_improvement > 0:
    print("\n[MARGINAL] History helps slightly.")
else:
    print("\n[FAIL] History doesn't help (or hurts slightly).")

print()
