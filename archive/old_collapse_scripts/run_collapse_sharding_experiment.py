"""
Collapse Probability Forecasting with Information Sharding
===========================================================

Tests whether information asymmetry improves probabilistic forecasting.

Distribution (N=100):
- 10 agents @ 10% information
- 10 agents @ 20% information
- ... (every 10%)
- 10 agents @ 100% information

Hypothesis: Information diversity improves ensemble probability estimates.
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


def analyze_by_information_level(predictions: List[Dict], ground_truth: float) -> Dict:
    """Analyze how prediction quality varies by information level."""

    by_level = {}
    for pred in predictions:
        level = pred.get('information_fraction', 1.0)
        if level not in by_level:
            by_level[level] = []
        by_level[level].append(pred['probability'])

    stats_by_level = {}
    for level, probs in by_level.items():
        brier_scores = [calculate_brier_score(p, ground_truth) for p in probs]

        stats_by_level[level] = {
            'n_predictions': len(probs),
            'mean_probability': float(np.mean(probs)),
            'std_probability': float(np.std(probs)),
            'mean_brier': float(np.mean(brier_scores)),
            'std_brier': float(np.std(brier_scores)),
            'min_probability': float(np.min(probs)),
            'max_probability': float(np.max(probs))
        }

    return stats_by_level


def run_single_collapse_prediction(
    period: int,
    state_before: dict,
    external_events: list,
    novaris_actions: list,
    tethys_actions: list,
    information_fraction: float,
    agent_id: int,
    model: str = "deepseek/deepseek-v3.2"
) -> Dict:
    """Run a single agent's collapse probability prediction with information sharding."""

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

    # Apply information sharding
    if information_fraction < 1.0:
        prompt = shard_information(base_prompt, information_fraction, seed=agent_id)
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
            return {
                'probability': 0.5,
                'confidence': 'low',
                'rationale': 'API error',
                'information_fraction': information_fraction,
                'agent_id': agent_id
            }

        if not response_text or response_text.strip() == "":
            return {
                'probability': 0.5,
                'confidence': 'low',
                'rationale': 'Empty response',
                'information_fraction': information_fraction,
                'agent_id': agent_id
            }

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

        # Add metadata
        result['information_fraction'] = information_fraction
        result['agent_id'] = agent_id

        return result

    except json.JSONDecodeError as e:
        return {
            'probability': 0.5,
            'confidence': 'low',
            'rationale': 'JSON error',
            'information_fraction': information_fraction,
            'agent_id': agent_id
        }
    except Exception as e:
        return {
            'probability': 0.5,
            'confidence': 'low',
            'rationale': str(e),
            'information_fraction': information_fraction,
            'agent_id': agent_id
        }


def run_n_predictions_parallel(
    n: int,
    period: int,
    state_before: dict,
    external_events: list,
    novaris_actions: list,
    tethys_actions: list,
    information_fractions: List[float],
    max_workers: int = 5
) -> List[Dict]:
    """Run N collapse predictions in parallel with information sharding."""

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for i in range(n):
            info_frac = information_fractions[i]

            # Small delay to avoid overwhelming API
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
                i
            )
            futures.append(future)

        # Collect results
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"    [ERROR] Prediction failed: {e}")
                results.append({
                    'probability': 0.5,
                    'confidence': 'low',
                    'rationale': 'Error',
                    'information_fraction': 1.0,
                    'agent_id': -1
                })

    return results


def main():
    """Run collapse probability forecasting with information sharding."""

    print("="*60)
    print("COLLAPSE PROBABILITY WITH INFORMATION SHARDING")
    print("Period 1 | N=100 | 10 information levels")
    print("="*60)

    # Setup
    period = 1
    n_agents = 100
    output_dir = Path("outputs/collapse_sharding_experiment")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load data
    print("\nLoading data...")
    ground_truth_actions = load_ground_truth()
    collapse_ground_truth_all = load_collapse_ground_truth()
    collapse_ground_truth = collapse_ground_truth_all[period]

    print(f"  Ground truth collapse probability: {collapse_ground_truth:.3f}")

    # Get simulation data
    state_before = get_state_before(period)
    external_events = get_events(period)
    novaris_actions = ground_truth_actions[period]['major_power']['actions']
    tethys_actions = ground_truth_actions[period]['small_power']['actions']

    print(f"  Novaris actions: {len(novaris_actions)}")
    print(f"  Tethys actions: {len(tethys_actions)}")

    # Load baseline results
    baseline_file = Path("outputs/collapse_experiment_period1/generic_period_1_collapse.json")
    baseline_stats = None
    if baseline_file.exists():
        with open(baseline_file) as f:
            baseline_data = json.load(f)
            baseline_stats = baseline_data['statistics']
        print(f"\n[OK] Loaded baseline results (100% info): Brier = {baseline_stats['ensemble_brier_score']:.4f}")

    # Create information distribution
    info_fractions = create_information_distribution(n_agents)
    print(f"\n  Information distribution:")
    from collections import Counter
    counts = Counter(info_fractions)
    for level in sorted(counts.keys()):
        print(f"    {level*100:.0f}%: {counts[level]} agents")

    # Run predictions
    print(f"\n  Running predictions...")
    start_time = time.time()
    prediction_dicts = run_n_predictions_parallel(
        n=n_agents,
        period=period,
        state_before=state_before,
        external_events=external_events,
        novaris_actions=novaris_actions,
        tethys_actions=tethys_actions,
        information_fractions=info_fractions
    )
    duration = time.time() - start_time

    print(f"  Completed in {duration:.1f}s ({duration/n_agents:.2f}s per agent)")

    # Extract probabilities
    probabilities = [pred['probability'] for pred in prediction_dicts]

    # Calculate statistics
    stats = calculate_ensemble_statistics(probabilities, collapse_ground_truth)
    stats_by_level = analyze_by_information_level(prediction_dicts, collapse_ground_truth)

    # Print results
    print(f"\n{'='*60}")
    print("RESULTS")
    print(f"{'='*60}")
    print(f"\nGround truth: {collapse_ground_truth:.3f}")
    print(f"\n{'Condition':<20} {'Ensemble Prob':<15} {'Brier Score':<15}")
    print("-"*60)

    if baseline_stats:
        print(f"{'Baseline (100%)':<20} {baseline_stats['ensemble_probability']:<15.3f} {baseline_stats['ensemble_brier_score']:<15.4f}")

    print(f"{'Sharding (mixed)':<20} {stats['ensemble_probability']:<15.3f} {stats['ensemble_brier_score']:<15.4f}")

    # Calculate improvement
    if baseline_stats:
        baseline_brier = baseline_stats['ensemble_brier_score']
        sharding_brier = stats['ensemble_brier_score']
        improvement = ((baseline_brier - sharding_brier) / baseline_brier) * 100

        print(f"\nSharding vs Baseline improvement: {improvement:+.1f}%")
        if improvement > 0:
            print(f"  [OK] Information sharding IMPROVES collapse forecasting")
        else:
            print(f"  [--] Information sharding does not improve collapse forecasting")

    # Print by-level statistics
    print(f"\n{'='*60}")
    print("PERFORMANCE BY INFORMATION LEVEL")
    print(f"{'='*60}")
    print(f"\n{'Info %':<10} {'Mean Prob':<12} {'Std Prob':<12} {'Mean Brier':<12}")
    print("-"*60)

    for level in sorted(stats_by_level.keys()):
        level_stats = stats_by_level[level]
        print(f"{level*100:<10.0f} {level_stats['mean_probability']:<12.3f} {level_stats['std_probability']:<12.3f} {level_stats['mean_brier']:<12.4f}")

    # Save results
    results = {
        'period': period,
        'n_agents': n_agents,
        'duration_seconds': duration,
        'statistics': stats,
        'statistics_by_level': stats_by_level,
        'individual_predictions': prediction_dicts,
        'baseline_comparison': {
            'baseline_brier': baseline_stats['ensemble_brier_score'] if baseline_stats else None,
            'sharding_brier': stats['ensemble_brier_score'],
            'improvement_pct': improvement if baseline_stats else None
        }
    }

    result_file = output_dir / f"sharding_period_{period}_collapse.json"
    with open(result_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n{'='*60}")
    print(f"EXPERIMENT COMPLETE")
    print(f"Results saved: {result_file}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
