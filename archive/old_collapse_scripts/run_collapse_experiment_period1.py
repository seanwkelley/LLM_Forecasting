"""
Collapse Probability Forecasting Experiment: Period 1
======================================================

Compares Generic vs Simplified personas on predicting Tethys government collapse.

Conditions:
- Generic (N=100): No persona, baseline strategic analyst
- Simplified (N=100): 6-attribute cognitive profiles

Ensemble: Simple probability averaging
Evaluation: Brier score, calibration
"""

import sys
sys.path.insert(0, 'D:/Northeastern/LLM_Forecasting')

import json
import time
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import concurrent.futures
import numpy as np

# Import core components
from forecasting.forecaster_base import BaseLLMForecaster
from forecasting.collapse_prompts import create_collapse_forecast_prompt
from forecasting.action_ground_truth import load_ground_truth
from forecasting.persona_simplified import load_simplified_personas
from forecasting.simulation_data import get_state_before, get_events


def load_collapse_ground_truth() -> Dict[int, float]:
    """
    Load ground truth collapse probabilities from assessments.csv.

    Returns:
        {period: probability, ...}
    """
    import pandas as pd

    df = pd.read_csv("D:/Northeastern/LLM_Forecasting/outputs/assessments.csv")

    # Extract collapse probability by period
    ground_truth = {}
    for _, row in df.iterrows():
        period = row['period']
        # Probability is in 'probability' column (0-1 scale)
        prob = row['probability']
        ground_truth[period] = prob

    return ground_truth


def calculate_brier_score(predicted_prob: float, actual_outcome: float) -> float:
    """
    Calculate Brier score for a single prediction.

    Args:
        predicted_prob: Forecasted probability (0-1)
        actual_outcome: Actual probability from simulation (0-1)

    Returns:
        Brier score (lower is better, 0 is perfect)
    """
    return (predicted_prob - actual_outcome) ** 2


def calculate_ensemble_statistics(probabilities: List[float], ground_truth: float) -> Dict:
    """
    Calculate statistics for ensemble probability predictions.

    Args:
        probabilities: List of individual probability forecasts
        ground_truth: True collapse probability

    Returns:
        Dictionary with ensemble metrics
    """
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


def run_single_collapse_prediction(
    period: int,
    state_before: dict,
    external_events: list,
    novaris_actions: list,
    tethys_actions: list,
    persona,
    model: str = "deepseek/deepseek-v3.2"
) -> Dict:
    """Run a single agent's collapse probability prediction."""

    # Create forecaster in this thread
    forecaster = BaseLLMForecaster(model=model)

    # Create prompt
    prompt = create_collapse_forecast_prompt(
        period=period,
        state_before=state_before,
        external_events=external_events,
        novaris_actions=novaris_actions,
        tethys_actions=tethys_actions
    )

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

    if persona is not None:
        system_prompt = persona.to_natural_language()

    # Get prediction
    try:
        response_text, success = forecaster.call_llm(
            user_prompt=prompt,
            system_prompt=system_prompt,
            response_format="json"
        )

        if not success:
            print(f"    [ERROR] API call failed")
            return {'probability': 0.5, 'confidence': 'low', 'rationale': 'API error'}

        if not response_text or response_text.strip() == "":
            print(f"    [ERROR] Empty response from API")
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
            print(f"    [WARNING] Probability {prob} out of range, clipping to [0, 1]")
            prob = max(0.0, min(1.0, prob))
            result['probability'] = prob

        return result

    except json.JSONDecodeError as e:
        print(f"    [ERROR] JSON decode failed: {e}")
        print(f"    Response preview: {response_text[:200] if response_text else 'None'}")
        return {'probability': 0.5, 'confidence': 'low', 'rationale': 'JSON error'}
    except Exception as e:
        print(f"    [ERROR] Prediction failed: {e}")
        return {'probability': 0.5, 'confidence': 'low', 'rationale': str(e)}


def run_n_predictions_parallel(
    n: int,
    period: int,
    state_before: dict,
    external_events: list,
    novaris_actions: list,
    tethys_actions: list,
    personas: List,
    max_workers: int = 5
) -> List[Dict]:
    """Run N collapse predictions in parallel."""

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for i in range(n):
            persona = personas[i] if i < len(personas) else None

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
                persona
            )
            futures.append(future)

        # Collect results
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"    [ERROR] Prediction failed: {e}")
                results.append({'probability': 0.5, 'confidence': 'low', 'rationale': 'Error'})

    return results


def run_condition(
    condition_name: str,
    persona_type: Optional[str],
    period: int,
    n_agents: int,
    ground_truth_actions: dict,
    collapse_ground_truth: float,
    output_dir: Path
) -> Dict:
    """Run a single condition for collapse probability forecasting."""

    print(f"\n{'='*60}")
    print(f"Condition: {condition_name}")
    print(f"Period: {period}")
    print(f"N agents: {n_agents}")
    print(f"Ground truth collapse probability: {collapse_ground_truth:.3f}")
    print(f"{'='*60}")

    # Get simulation data
    state_before = get_state_before(period)
    external_events = get_events(period)

    # Get actual actions taken (for context in prompt)
    novaris_actions = ground_truth_actions[period]['major_power']['actions']
    tethys_actions = ground_truth_actions[period]['small_power']['actions']

    print(f"  Novaris actions: {len(novaris_actions)}")
    print(f"  Tethys actions: {len(tethys_actions)}")

    # Load personas
    if persona_type is None:
        personas = [None] * n_agents  # Generic
    elif persona_type == "simplified":
        all_personas = load_simplified_personas()
        personas = all_personas[:n_agents]
    else:
        raise ValueError(f"Unknown persona type: {persona_type}")

    # Run predictions
    start_time = time.time()
    prediction_dicts = run_n_predictions_parallel(
        n=n_agents,
        period=period,
        state_before=state_before,
        external_events=external_events,
        novaris_actions=novaris_actions,
        tethys_actions=tethys_actions,
        personas=personas
    )
    duration = time.time() - start_time

    print(f"  Completed in {duration:.1f}s ({duration/n_agents:.2f}s per agent)")

    # Extract probabilities
    probabilities = [pred['probability'] for pred in prediction_dicts]

    # Calculate statistics
    stats = calculate_ensemble_statistics(probabilities, collapse_ground_truth)

    print(f"  [RESULTS] Ensemble probability: {stats['ensemble_probability']:.3f} (truth: {collapse_ground_truth:.3f})")
    print(f"            Ensemble Brier: {stats['ensemble_brier_score']:.4f}")
    print(f"            Individual mean Brier: {stats['individual_mean_brier']:.4f}")
    print(f"            Probability range: [{stats['probability_min']:.3f}, {stats['probability_max']:.3f}]")
    print(f"            Probability std: {stats['probability_std']:.3f}")

    # Store results
    results = {
        'condition': condition_name,
        'period': period,
        'n_agents': n_agents,
        'duration_seconds': duration,
        'statistics': stats,
        'individual_predictions': prediction_dicts
    }

    # Save condition results
    condition_file = output_dir / f"{condition_name}_period_{period}_collapse.json"
    with open(condition_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n  Saved: {condition_file}")

    return results


def main():
    """Run collapse probability forecasting: Generic vs Simplified, Period 1."""

    print("="*60)
    print("COLLAPSE PROBABILITY FORECASTING EXPERIMENT")
    print("Generic vs Simplified | Period 1 | N=100")
    print("="*60)

    # Setup
    period = 1
    n_agents = 100
    output_dir = Path("outputs/collapse_experiment_period1")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load data
    print("\nLoading data...")
    ground_truth_actions = load_ground_truth()
    collapse_ground_truth_all = load_collapse_ground_truth()
    collapse_ground_truth = collapse_ground_truth_all[period]

    print(f"  Ground truth actions loaded for {len(ground_truth_actions)} periods")
    print(f"  Period {period} collapse probability: {collapse_ground_truth:.3f}")

    # Define conditions
    conditions = [
        ("generic", None),
        ("simplified", "simplified")
    ]

    # Run each condition
    all_results = []
    for condition_name, persona_type in conditions:
        try:
            result = run_condition(
                condition_name=condition_name,
                persona_type=persona_type,
                period=period,
                n_agents=n_agents,
                ground_truth_actions=ground_truth_actions,
                collapse_ground_truth=collapse_ground_truth,
                output_dir=output_dir
            )
            all_results.append(result)

        except Exception as e:
            print(f"\n[ERROR] Condition {condition_name} failed: {e}")
            import traceback
            traceback.print_exc()

    # Compare conditions
    print(f"\n{'='*60}")
    print("COMPARISON SUMMARY")
    print(f"{'='*60}")
    print(f"\nGround truth: {collapse_ground_truth:.3f}")
    print(f"\n{'Condition':<15} {'Ensemble P':<12} {'Brier':<10} {'Individual Brier':<18}")
    print("-"*60)

    for result in all_results:
        stats = result['statistics']
        print(f"{result['condition']:<15} {stats['ensemble_probability']:<12.3f} {stats['ensemble_brier_score']:<10.4f} {stats['individual_mean_brier']:<18.4f}")

    # Calculate improvement
    if len(all_results) == 2:
        generic_brier = all_results[0]['statistics']['ensemble_brier_score']
        simplified_brier = all_results[1]['statistics']['ensemble_brier_score']
        improvement = ((generic_brier - simplified_brier) / generic_brier) * 100

        print(f"\nSimplified vs Generic improvement: {improvement:+.1f}%")
        if improvement > 0:
            print(f"  [OK] Simplified personas IMPROVE collapse forecasting")
        else:
            print(f"  [--] Simplified personas do not improve collapse forecasting")

    # Save summary
    summary_file = output_dir / "experiment_summary.json"
    with open(summary_file, 'w') as f:
        json.dump({
            'period': period,
            'n_agents': n_agents,
            'ground_truth': collapse_ground_truth,
            'results': all_results,
            'timestamp': datetime.now().isoformat()
        }, f, indent=2)

    print(f"\n{'='*60}")
    print(f"EXPERIMENT COMPLETE")
    print(f"Conditions run: {len(all_results)}")
    print(f"Summary saved: {summary_file}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
