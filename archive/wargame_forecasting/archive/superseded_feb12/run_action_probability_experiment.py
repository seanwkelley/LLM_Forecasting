"""
Action Probability Prediction: Sharding Strategy Comparison
=============================================================

Compares 3 conditions for Periods 1-3, 2 factions each:
1. Baseline: 100% everything (initial scenario + history + current period)
2. Shard Everything: X% of data sections (scenario + history + current period data)
3. Shard Initial Only: X% initial scenario + 100% history + 100% current period

Instructions/output format are NEVER sharded in any condition.
Temperature set to 1.0 for maximum sampling diversity across all conditions.

Predicts binary probability for top 5 actions per faction, evaluated with Brier score.
"""

import sys
sys.path.insert(0, 'D:/Northeastern/LLM_Forecasting')

import json
import time
import argparse
from pathlib import Path
from typing import Dict, List
from datetime import datetime
import concurrent.futures
import numpy as np

# Import core components
from forecasting.forecaster_base import BaseLLMForecaster
from forecasting.action_probability_prompts import (
    get_action_prompt_sections, get_target_actions, get_faction_code,
    NOVARIS_TARGET_ACTIONS, TETHYS_TARGET_ACTIONS
)
from forecasting.action_ground_truth import load_ground_truth
from forecasting.simulation_data import get_state_before, get_events
from forecasting.information_sharding import create_information_distribution
from forecasting.sharding_strategies import apply_sharding_strategy


def create_historical_summary(period: int, ground_truth_actions: dict) -> str:
    """Create historical summary of prior periods (observable info only)."""
    if period <= 1:
        return ""

    history_lines = ["\n" + "="*80]
    history_lines.append("HISTORICAL CONTEXT (Prior Periods)")
    history_lines.append("="*80 + "\n")

    for p in range(1, period):
        history_lines.append(f"PERIOD {p}:")

        # Get state after period ended
        state = get_state_before(p + 1)
        history_lines.append(f"  End State:")
        history_lines.append(f"    - Tethys Territory: {(1-state.get('territory_controlled', 0))*100:.1f}%")
        history_lines.append(f"    - Tethys GDP: ${state.get('tethys_gdp', 30):.1f}B")
        history_lines.append(f"    - Novaris GDP: ${state.get('novaris_gdp', 100):.1f}B")
        history_lines.append(f"    - Military Balance: {state.get('military_balance', 0):.2f}")
        history_lines.append(f"    - International Support: {state.get('international_support', 0.5)*100:.0f}%")
        history_lines.append(f"    - Sanctions Level: {state.get('sanctions_level', 0)*100:.0f}%")

        # Get events
        events = get_events(p)
        if events:
            history_lines.append(f"  Events:")
            for event in events[:3]:
                history_lines.append(f"    - {event}")

        # Get actions
        novaris_acts = ground_truth_actions[p]['major_power']['actions']
        tethys_acts = ground_truth_actions[p]['small_power']['actions']
        history_lines.append(f"  Actions:")
        history_lines.append(f"    Novaris: {', '.join(novaris_acts[:5])}")
        history_lines.append(f"    Tethys: {', '.join(tethys_acts[:5])}")
        history_lines.append("")

    return "\n".join(history_lines)


def build_action_ground_truth(gt_actions: dict) -> Dict:
    """
    Convert ground truth action lists to binary labels for target actions.

    Returns:
        {period: {faction: {action: 0|1}}}
    """
    result = {}

    for period in [1, 2, 3]:
        result[period] = {}

        for faction, faction_code in [('novaris', 'major_power'), ('tethys', 'small_power')]:
            actions_taken = set(gt_actions[period][faction_code]['actions'])
            target_actions = get_target_actions(faction)

            result[period][faction] = {
                action: 1 if action in actions_taken else 0
                for action in target_actions
            }

    return result


def calculate_action_brier(predicted: Dict[str, float], truth: Dict[str, int], actions_list: List[str]) -> Dict:
    """
    Calculate Brier score for action probability predictions.

    Returns per-action Brier, mean Brier, and binary accuracy.
    """
    per_action_brier = {}
    correct = 0

    for action in actions_list:
        pred_prob = predicted.get(action, 0.5)
        actual = truth.get(action, 0)
        brier = (pred_prob - actual) ** 2
        per_action_brier[action] = float(brier)

        # Binary accuracy: (prob >= 0.5) == (actual == 1)
        if (pred_prob >= 0.5) == (actual == 1):
            correct += 1

    mean_brier = np.mean(list(per_action_brier.values()))
    binary_accuracy = correct / len(actions_list)

    return {
        'per_action_brier': per_action_brier,
        'mean_brier': float(mean_brier),
        'binary_accuracy': float(binary_accuracy)
    }


def calculate_ensemble_action_probs(all_preds: List[Dict[str, float]], actions_list: List[str]) -> Dict[str, float]:
    """Average probabilities across agents for ensemble prediction."""
    ensemble = {}
    for action in actions_list:
        probs = [pred.get(action, 0.5) for pred in all_preds]
        ensemble[action] = float(np.mean(probs))
    return ensemble


def run_single_action_prediction(
    initial_scenario: str,
    historical_summary: str,
    current_period_data: str,
    instructions: str,
    sharding_strategy: str,
    information_fraction: float,
    agent_id: int,
    faction: str,
    model: str = "deepseek/deepseek-v3.2"
) -> Dict:
    """Run a single agent's action probability prediction."""

    # Create forecaster with temperature=1.0 for max sampling diversity
    forecaster = BaseLLMForecaster(model=model, temperature=1.0)

    # Apply sharding strategy (instructions always protected)
    prompt = apply_sharding_strategy(
        strategy=sharding_strategy,
        initial_scenario=initial_scenario,
        historical_summary=historical_summary,
        current_period_data=current_period_data,
        instructions=instructions,
        information_fraction=information_fraction,
        seed=agent_id
    )

    faction_display = "Novaris" if faction == "novaris" else "Tethys"
    system_prompt = f"""You are an expert geopolitical analyst specializing in military and strategic action forecasting.

Your task is to predict the probability that {faction_display} will take specific actions based on:
- Strategic context and background
- Historical developments
- Current military, economic, and political situation
- Recent events and actions

Apply rigorous analytical reasoning and USE THE FULL PROBABILITY RANGE 0.0 to 1.0.
Do NOT cluster around 0.5 - be decisive based on the evidence.

Output ONLY valid JSON in the exact format specified."""

    try:
        response_text, success = forecaster.call_llm(
            user_prompt=prompt,
            system_prompt=system_prompt,
            response_format="json"
        )

        if not success or not response_text or response_text.strip() == "":
            actions = get_target_actions(faction)
            result = {a: 0.5 for a in actions}
            result['rationale'] = 'API error'
            result['_fallback'] = 'api_error'
            return result

        # Strip markdown fences
        response_text = response_text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        result = json.loads(response_text)

        # Validate each action probability
        actions = get_target_actions(faction)
        for action in actions:
            prob = result.get(action, None)
            if prob is None:
                result[action] = 0.5
                result.setdefault('_fallback', 'missing_action_key')
            elif not isinstance(prob, (int, float)):
                try:
                    result[action] = float(prob)
                except (ValueError, TypeError):
                    result[action] = 0.5
                    result.setdefault('_fallback', 'invalid_prob_type')
            else:
                result[action] = float(prob)
                if result[action] > 1.0:
                    result[action] = result[action] / 100.0
                result[action] = max(0.0, min(1.0, result[action]))

        return result

    except json.JSONDecodeError:
        actions = get_target_actions(faction)
        result = {a: 0.5 for a in actions}
        result['rationale'] = 'JSON parse error'
        result['_fallback'] = 'json_error'
        return result
    except Exception as e:
        actions = get_target_actions(faction)
        result = {a: 0.5 for a in actions}
        result['rationale'] = str(e)
        result['_fallback'] = 'exception'
        return result


def run_n_predictions_parallel(
    n: int,
    initial_scenario: str,
    historical_summary: str,
    current_period_data: str,
    instructions: str,
    sharding_strategy: str,
    information_fractions: List[float],
    faction: str,
    max_workers: int = 5
) -> List[Dict]:
    """Run N action predictions in parallel."""

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for i in range(n):
            info_frac = information_fractions[i]

            if i % 10 == 0 and i > 0:
                time.sleep(0.5)

            future = executor.submit(
                run_single_action_prediction,
                initial_scenario,
                historical_summary,
                current_period_data,
                instructions,
                sharding_strategy,
                info_frac,
                i,
                faction
            )
            futures.append(future)

        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception:
                actions = get_target_actions(faction)
                fallback = {a: 0.5 for a in actions}
                fallback['_fallback'] = 'future_exception'
                results.append(fallback)

    return results


def run_faction_condition(
    period: int,
    condition_name: str,
    sharding_strategy: str,
    faction: str,
    n_agents: int,
    ground_truth_actions: dict,
    action_truth: Dict[str, int]
) -> Dict:
    """Run a single condition for a single period and faction."""

    faction_display = "Novaris" if faction == "novaris" else "Tethys"
    print(f"\n    {faction_display} ({condition_name}):")

    # Get simulation data
    state_before = get_state_before(period)
    external_events = get_events(period)
    novaris_actions = ground_truth_actions[period]['major_power']['actions']

    # Create historical summary
    historical_summary = create_historical_summary(period, ground_truth_actions)

    # Get prompt sections (4-part: scenario, history, data, instructions)
    initial_scenario, _, current_period_data, instructions = get_action_prompt_sections(
        faction=faction,
        period=period,
        state_before=state_before,
        events=external_events,
        novaris_actions=novaris_actions,
        history=historical_summary
    )

    # Create information distribution
    info_fractions = create_information_distribution(n_agents)

    # Run predictions
    start_time = time.time()
    prediction_dicts = run_n_predictions_parallel(
        n=n_agents,
        initial_scenario=initial_scenario,
        historical_summary=historical_summary,
        current_period_data=current_period_data,
        instructions=instructions,
        sharding_strategy=sharding_strategy,
        information_fractions=info_fractions,
        faction=faction
    )
    duration = time.time() - start_time

    # Track fallbacks
    fallback_count = sum(1 for pred in prediction_dicts if '_fallback' in pred)
    fallback_types = {}
    for pred in prediction_dicts:
        if '_fallback' in pred:
            ft = pred['_fallback']
            fallback_types[ft] = fallback_types.get(ft, 0) + 1

    # Extract just the action probabilities
    actions_list = get_target_actions(faction)
    action_preds = []
    for pred in prediction_dicts:
        action_pred = {a: pred.get(a, 0.5) for a in actions_list}
        action_preds.append(action_pred)

    # Calculate ensemble probabilities
    ensemble_probs = calculate_ensemble_action_probs(action_preds, actions_list)

    # Calculate ensemble Brier
    ensemble_metrics = calculate_action_brier(ensemble_probs, action_truth, actions_list)

    # Calculate individual Brier scores
    individual_briers = []
    individual_accuracies = []
    for pred in action_preds:
        metrics = calculate_action_brier(pred, action_truth, actions_list)
        individual_briers.append(metrics['mean_brier'])
        individual_accuracies.append(metrics['binary_accuracy'])

    # Print results
    print(f"      Completed in {duration:.1f}s")
    print(f"      Ensemble probs: {', '.join(f'{a}={ensemble_probs[a]:.2f}' for a in actions_list)}")
    print(f"      Ground truth:   {', '.join(f'{a}={action_truth[a]}' for a in actions_list)}")
    print(f"      Ensemble Brier: {ensemble_metrics['mean_brier']:.4f} | Binary Acc: {ensemble_metrics['binary_accuracy']:.2f}")
    print(f"      Fallbacks: {fallback_count}/{n_agents}", end="")
    if fallback_types:
        print(f" ({fallback_types})", end="")
    print()

    return {
        'condition': condition_name,
        'sharding_strategy': sharding_strategy,
        'period': period,
        'faction': faction,
        'n_agents': n_agents,
        'duration_seconds': duration,
        'ensemble_probabilities': ensemble_probs,
        'ground_truth': action_truth,
        'ensemble_brier': ensemble_metrics['mean_brier'],
        'ensemble_per_action_brier': ensemble_metrics['per_action_brier'],
        'ensemble_binary_accuracy': ensemble_metrics['binary_accuracy'],
        'individual_mean_brier': float(np.mean(individual_briers)),
        'individual_std_brier': float(np.std(individual_briers)),
        'individual_mean_accuracy': float(np.mean(individual_accuracies)),
        'fallback_count': fallback_count,
        'fallback_types': fallback_types
    }


def main():
    """Run action probability sharding comparison for periods 1-3."""

    parser = argparse.ArgumentParser(description="Action Probability Prediction Experiment")
    parser.add_argument('--test', action='store_true', help='Quick test: 1 period, 1 condition, N=5')
    args = parser.parse_args()

    if args.test:
        n_agents = 5
        periods = [1]
        conditions = [("baseline", "none")]
        factions = ['novaris', 'tethys']
    else:
        n_agents = 100
        periods = [1, 2, 3]
        conditions = [
            ("baseline", "none"),
            ("shard_everything", "shard_everything"),
            ("shard_initial_only", "shard_initial_only")
        ]
        factions = ['novaris', 'tethys']

    total_calls = n_agents * len(periods) * len(conditions) * len(factions)

    print("="*60)
    print("ACTION PROBABILITY PREDICTION: SHARDING COMPARISON")
    print(f"Periods {periods} | {len(conditions)} Conditions | {len(factions)} Factions | N={n_agents}")
    print(f"Total LLM calls: {total_calls}")
    print("Temperature: 1.0 | Instructions: Protected")
    print("="*60)

    # Setup output directory
    output_dir = Path("outputs/action_probability_experiment")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load data
    print("\nLoading data...")
    ground_truth_actions = load_ground_truth()
    action_ground_truth = build_action_ground_truth(ground_truth_actions)

    # Print ground truth summary
    print("\nGround Truth (binary labels):")
    for period in periods:
        for faction in factions:
            truth = action_ground_truth[period][faction]
            labels = ', '.join(f'{a}={v}' for a, v in truth.items())
            print(f"  Period {period} {faction}: {labels}")

    # Run experiment
    all_results = []

    for period in periods:
        print(f"\n{'='*60}")
        print(f"PERIOD {period}")
        print(f"{'='*60}")

        for condition_name, strategy in conditions:
            for faction in factions:
                try:
                    action_truth = action_ground_truth[period][faction]
                    result = run_faction_condition(
                        period=period,
                        condition_name=condition_name,
                        sharding_strategy=strategy,
                        faction=faction,
                        n_agents=n_agents,
                        ground_truth_actions=ground_truth_actions,
                        action_truth=action_truth
                    )
                    all_results.append(result)
                except Exception as e:
                    print(f"\n[ERROR] {condition_name}/{faction} failed: {e}")
                    import traceback
                    traceback.print_exc()

    # Summary table
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")

    print(f"\n{'Period':<8} {'Condition':<22} {'Faction':<10} {'Ens Brier':<12} {'Bin Acc':<10} {'Fallbacks':<10}")
    print("-"*80)

    for result in all_results:
        p = result['period']
        cond = result['condition']
        faction = result['faction']
        brier = result['ensemble_brier']
        acc = result['ensemble_binary_accuracy']
        fallbacks = result['fallback_count']
        print(f"{p:<8} {cond:<22} {faction:<10} {brier:<12.4f} {acc:<10.2f} {fallbacks:<10}")

    # Average by condition
    print(f"\n{'='*80}")
    print("AVERAGE PERFORMANCE BY CONDITION")
    print(f"{'='*80}")

    for cond_name, _ in conditions:
        cond_results = [r for r in all_results if r['condition'] == cond_name]
        if not cond_results:
            continue
        avg_brier = np.mean([r['ensemble_brier'] for r in cond_results])
        avg_acc = np.mean([r['ensemble_binary_accuracy'] for r in cond_results])
        total_fallbacks = sum(r['fallback_count'] for r in cond_results)
        print(f"{cond_name:<22} Avg Brier: {avg_brier:.4f}  Avg Acc: {avg_acc:.2f}  Fallbacks: {total_fallbacks}")

    # Per-action analysis
    print(f"\n{'='*80}")
    print("PER-ACTION ANALYSIS (Ensemble Brier)")
    print(f"{'='*80}")

    for faction in factions:
        actions_list = get_target_actions(faction)
        print(f"\n{faction.upper()}:")
        print(f"  {'Action':<28} {'Avg Brier':<12} {'Best Cond':<22}")
        print("  " + "-"*65)

        for action in actions_list:
            faction_results = [r for r in all_results if r['faction'] == faction]
            action_briers = {}
            for r in faction_results:
                cond = r['condition']
                if cond not in action_briers:
                    action_briers[cond] = []
                action_briers[cond].append(r['ensemble_per_action_brier'].get(action, 0.25))

            if not action_briers:
                continue
            avg_across_all = np.mean([b for blist in action_briers.values() for b in blist])
            best_cond = min(action_briers.keys(), key=lambda c: np.mean(action_briers[c]))
            print(f"  {action:<28} {avg_across_all:<12.4f} {best_cond:<22}")

    # Save results
    summary_file = output_dir / "experiment_summary.json"
    with open(summary_file, 'w') as f:
        json.dump({
            'periods': periods,
            'n_agents': n_agents,
            'temperature': 1.0,
            'instructions_protected': True,
            'conditions': [c[0] for c in conditions],
            'factions': factions,
            'novaris_target_actions': NOVARIS_TARGET_ACTIONS,
            'tethys_target_actions': TETHYS_TARGET_ACTIONS,
            'action_ground_truth': {str(k): v for k, v in action_ground_truth.items()},
            'results': all_results,
            'timestamp': datetime.now().isoformat()
        }, f, indent=2)

    print(f"\n{'='*60}")
    print(f"EXPERIMENT COMPLETE")
    print(f"Results saved: {summary_file}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
