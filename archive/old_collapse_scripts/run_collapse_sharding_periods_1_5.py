"""
Collapse Probability Forecasting with Information Sharding: Periods 1-5
========================================================================

Runs both baseline (100% info) and sharding (mixed info) for periods 1-5.

Compares:
- Baseline: All 100 agents see 100% information
- Sharding: 10 agents each at 10%, 20%, ..., 100% information
"""

import sys
sys.path.insert(0, 'D:/Northeastern/LLM_Forecasting')

import json
import time
from pathlib import Path
from typing import Dict, List
from datetime import datetime
import concurrent.futures
import numpy as np

# Import core components
from forecasting.forecaster_base import BaseLLMForecaster
from forecasting.collapse_prompts import create_collapse_forecast_prompt
from forecasting.action_ground_truth import load_ground_truth
from forecasting.simulation_data import get_state_before, get_events
from forecasting.information_sharding import (
    shard_information,
    create_information_distribution
)


def load_collapse_ground_truth() -> Dict[int, float]:
    """Load ground truth collapse probabilities from assessments.csv."""
    import pandas as pd

    df = pd.read_csv("D:/Northeastern/LLM_Forecasting/outputs/assessments.csv")

    ground_truth = {}
    for _, row in df.iterrows():
        period = row['period']
        prob = row['probability']
        ground_truth[period] = prob

    return ground_truth


def calculate_brier_score(predicted_prob: float, actual_outcome: float) -> float:
    """Calculate Brier score for a single prediction."""
    return (predicted_prob - actual_outcome) ** 2


def calculate_ensemble_statistics(probabilities: List[float], ground_truth: float) -> Dict:
    """Calculate statistics for ensemble probability predictions."""
    ensemble_prob = np.mean(probabilities)
    individual_brier = [calculate_brier_score(p, ground_truth) for p in probabilities]
    ensemble_brier = calculate_brier_score(ensemble_prob, ground_truth)

    return {
        'ensemble_probability': float(ensemble_prob),
        'ensemble_brier_score': float(ensemble_brier),
        'individual_mean_brier': float(np.mean(individual_brier)),
        'individual_std_brier': float(np.std(individual_brier)),
        'probability_mean': float(np.mean(probabilities)),
        'probability_std': float(np.std(probabilities)),
        'probability_min': float(np.min(probabilities)),
        'probability_max': float(np.max(probabilities)),
        'ground_truth': float(ground_truth),
        'n_predictions': len(probabilities)
    }


def create_historical_summary(
    period: int,
    ground_truth_actions: dict
) -> str:
    """
    Create summary of observable history from prior periods.

    Includes:
    - Actions taken by both factions
    - External events
    - Observable state variables (NO collapse probability - that's what we're predicting!)
    """
    if period <= 1:
        return ""

    history_lines = ["\n" + "="*80]
    history_lines.append("HISTORICAL CONTEXT (Prior Periods)")
    history_lines.append("="*80 + "\n")

    for p in range(1, period):
        history_lines.append(f"PERIOD {p}:")

        # Get state (observable variables only)
        state = get_state_before(p + 1)  # State at END of period p
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
            for event in events[:3]:  # Limit to top 3 events
                history_lines.append(f"    - {event}")

        # Get actions
        novaris_acts = ground_truth_actions[p]['major_power']['actions']
        tethys_acts = ground_truth_actions[p]['small_power']['actions']
        history_lines.append(f"  Actions:")
        history_lines.append(f"    Novaris: {', '.join(novaris_acts[:5])}")  # Limit to 5
        history_lines.append(f"    Tethys: {', '.join(tethys_acts[:5])}")
        history_lines.append("")

    return "\n".join(history_lines)


def run_single_collapse_prediction(
    period: int,
    state_before: dict,
    external_events: list,
    novaris_actions: list,
    tethys_actions: list,
    information_fraction: float,
    agent_id: int,
    history_text: str = "",
    model: str = "deepseek/deepseek-v3.2"
) -> Dict:
    """Run a single agent's collapse probability prediction."""

    # Create forecaster in this thread
    forecaster = BaseLLMForecaster(model=model)

    # Create base prompt
    base_prompt = create_collapse_forecast_prompt(
        period=period,
        state_before=state_before,
        external_events=external_events,
        novaris_actions=novaris_actions,
        tethys_actions=tethys_actions
    )

    # Prepend history if provided
    if history_text:
        base_prompt = f"{history_text}\n\n{base_prompt}"

    # Apply information sharding
    if information_fraction < 1.0:
        prompt = shard_information(base_prompt, information_fraction, seed=agent_id * period)
    else:
        prompt = base_prompt

    # System prompt
    system_prompt = """You are an expert geopolitical analyst specializing in government stability forecasting.

Your task is to predict the probability of government collapse based on:
- Military and territorial situation
- Economic sustainability
- Internal political stability
- International support and diplomatic position
- Recent events and actions

Apply rigorous analytical reasoning and USE THE FULL PROBABILITY RANGE 0.0 to 1.0.
Do NOT cluster around 0.5 - be decisive based on the evidence.

Output ONLY valid JSON in the exact format specified."""

    # Get prediction
    try:
        response_text, success = forecaster.call_llm(
            user_prompt=prompt,
            system_prompt=system_prompt,
            response_format="json"
        )

        if not success:
            return {'probability': 0.5, 'confidence': 'low', 'rationale': 'API error'}

        if not response_text or response_text.strip() == "":
            return {'probability': 0.5, 'confidence': 'low', 'rationale': 'Empty response'}

        # Strip markdown code fences
        response_text = response_text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        result = json.loads(response_text)

        # Validate probability in range
        prob = result.get('probability', 0.5)
        if not (0.0 <= prob <= 1.0):
            prob = max(0.0, min(1.0, prob))
            result['probability'] = prob

        return result

    except Exception as e:
        return {'probability': 0.5, 'confidence': 'low', 'rationale': str(e)}


def run_n_predictions_parallel(
    n: int,
    period: int,
    state_before: dict,
    external_events: list,
    novaris_actions: list,
    tethys_actions: list,
    information_fractions: List[float],
    history_text: str = "",
    max_workers: int = 5
) -> List[Dict]:
    """Run N collapse predictions in parallel."""

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for i in range(n):
            info_frac = information_fractions[i]

            if i % 10 == 0 and i > 0:
                time.sleep(0.5)

            future = executor.submit(
                run_single_collapse_prediction,
                period,
                state_before,
                external_events,
                novaris_actions,
                tethys_actions,
                info_frac,
                i,
                history_text
            )
            futures.append(future)

        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                results.append({'probability': 0.5, 'confidence': 'low', 'rationale': 'Error'})

    return results


def run_period_condition(
    period: int,
    condition_name: str,
    use_sharding: bool,
    n_agents: int,
    ground_truth_actions: dict,
    collapse_ground_truth_all: dict,
    collapse_ground_truth: float
) -> Dict:
    """Run a single condition for a single period."""

    print(f"\n  Condition: {condition_name}")

    # Get simulation data
    state_before = get_state_before(period)
    external_events = get_events(period)
    novaris_actions = ground_truth_actions[period]['major_power']['actions']
    tethys_actions = ground_truth_actions[period]['small_power']['actions']

    # Create historical summary (observable info only - NO collapse probabilities!)
    history_text = create_historical_summary(period, ground_truth_actions)

    # Create information distribution
    if use_sharding:
        info_fractions = create_information_distribution(n_agents)
    else:
        info_fractions = [1.0] * n_agents

    # Run predictions
    start_time = time.time()
    prediction_dicts = run_n_predictions_parallel(
        n=n_agents,
        period=period,
        state_before=state_before,
        external_events=external_events,
        novaris_actions=novaris_actions,
        tethys_actions=tethys_actions,
        information_fractions=info_fractions,
        history_text=history_text
    )
    duration = time.time() - start_time

    # Extract probabilities and calculate statistics
    probabilities = [pred['probability'] for pred in prediction_dicts]
    stats = calculate_ensemble_statistics(probabilities, collapse_ground_truth)

    print(f"    Completed in {duration:.1f}s")
    print(f"    Ensemble prob: {stats['ensemble_probability']:.3f} (truth: {collapse_ground_truth:.3f})")
    print(f"    Brier score: {stats['ensemble_brier_score']:.4f}")

    return {
        'condition': condition_name,
        'period': period,
        'use_sharding': use_sharding,
        'n_agents': n_agents,
        'duration_seconds': duration,
        'statistics': stats
    }


def main():
    """Run collapse probability forecasting for periods 1-5."""

    print("="*60)
    print("COLLAPSE PROBABILITY: PERIODS 1-5")
    print("Baseline vs Information Sharding | N=100 per condition")
    print("="*60)

    # Setup
    n_agents = 100
    periods = [1, 2, 3, 4, 5]
    output_dir = Path("outputs/collapse_sharding_periods_1_5")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load data
    print("\nLoading data...")
    ground_truth_actions = load_ground_truth()
    collapse_ground_truth_all = load_collapse_ground_truth()

    print(f"  Periods to process: {periods}")
    print(f"  N agents per condition: {n_agents}")

    # Track all results
    all_results = []

    # Run each period
    for period in periods:
        print(f"\n{'='*60}")
        print(f"PERIOD {period}")
        print(f"{'='*60}")

        collapse_truth = collapse_ground_truth_all[period]
        print(f"  Ground truth: {collapse_truth:.3f}")

        # Run baseline (100% info)
        baseline_result = run_period_condition(
            period=period,
            condition_name="baseline",
            use_sharding=False,
            n_agents=n_agents,
            ground_truth_actions=ground_truth_actions,
            collapse_ground_truth_all=collapse_ground_truth_all,
            collapse_ground_truth=collapse_truth
        )
        all_results.append(baseline_result)

        # Run sharding (mixed info)
        sharding_result = run_period_condition(
            period=period,
            condition_name="sharding",
            use_sharding=True,
            n_agents=n_agents,
            ground_truth_actions=ground_truth_actions,
            collapse_ground_truth_all=collapse_ground_truth_all,
            collapse_ground_truth=collapse_truth
        )
        all_results.append(sharding_result)

        # Calculate improvement
        baseline_brier = baseline_result['statistics']['ensemble_brier_score']
        sharding_brier = sharding_result['statistics']['ensemble_brier_score']
        improvement = ((baseline_brier - sharding_brier) / baseline_brier) * 100 if baseline_brier > 0 else 0

        print(f"\n  Period {period} Summary:")
        print(f"    Baseline Brier: {baseline_brier:.4f}")
        print(f"    Sharding Brier: {sharding_brier:.4f}")
        print(f"    Improvement: {improvement:+.1f}%")

    # Summary across all periods
    print(f"\n{'='*60}")
    print("SUMMARY ACROSS ALL PERIODS")
    print(f"{'='*60}")

    print(f"\n{'Period':<10} {'Truth':<10} {'Baseline':<12} {'Sharding':<12} {'Improvement':<12}")
    print("-"*60)

    for period in periods:
        baseline = next(r for r in all_results if r['period'] == period and r['condition'] == 'baseline')
        sharding = next(r for r in all_results if r['period'] == period and r['condition'] == 'sharding')

        truth = baseline['statistics']['ground_truth']
        base_brier = baseline['statistics']['ensemble_brier_score']
        shard_brier = sharding['statistics']['ensemble_brier_score']
        improvement = ((base_brier - shard_brier) / base_brier) * 100 if base_brier > 0 else 0

        print(f"{period:<10} {truth:<10.3f} {base_brier:<12.4f} {shard_brier:<12.4f} {improvement:+<12.1f}%")

    # Average improvement
    baseline_avg_brier = np.mean([r['statistics']['ensemble_brier_score'] for r in all_results if r['condition'] == 'baseline'])
    sharding_avg_brier = np.mean([r['statistics']['ensemble_brier_score'] for r in all_results if r['condition'] == 'sharding'])
    avg_improvement = ((baseline_avg_brier - sharding_avg_brier) / baseline_avg_brier) * 100

    print(f"\n{'AVERAGE':<10} {'-':<10} {baseline_avg_brier:<12.4f} {sharding_avg_brier:<12.4f} {avg_improvement:+<12.1f}%")

    # Save results
    summary_file = output_dir / "experiment_summary.json"
    with open(summary_file, 'w') as f:
        json.dump({
            'periods': periods,
            'n_agents': n_agents,
            'results': all_results,
            'average_baseline_brier': float(baseline_avg_brier),
            'average_sharding_brier': float(sharding_avg_brier),
            'average_improvement_pct': float(avg_improvement),
            'timestamp': datetime.now().isoformat()
        }, f, indent=2)

    print(f"\n{'='*60}")
    print(f"EXPERIMENT COMPLETE")
    print(f"Periods run: {len(periods)}")
    print(f"Total conditions: {len(all_results)}")
    print(f"Results saved: {summary_file}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
