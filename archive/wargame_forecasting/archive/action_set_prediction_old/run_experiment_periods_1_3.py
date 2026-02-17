"""
Multi-Condition Forecasting Experiment: Periods 1-3
====================================================

Runs 6 experimental conditions across periods 1-3:
- Persona complexity: Generic vs Simplified (6 attrs) vs Complex (15+ attrs)
- Temporal context: No history vs With history

Period 1-2: Only "no history" conditions (3 total)
Period 3: All 6 conditions (adds "with history" variants)

Total runs: 3 + 3 + 6 = 12 condition-periods
"""

import sys
sys.path.insert(0, 'D:/Northeastern/LLM_Forecasting')

import json
import time
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import concurrent.futures
from dataclasses import dataclass

# Import core components
from forecasting.forecaster_base import BaseLLMForecaster
from forecasting.action_library import (
    load_plausible_actions,
    get_all_valid_actions,
    format_plausible_actions_for_prompt
)
from forecasting.action_ground_truth import load_ground_truth
from forecasting.action_evaluation import (
    evaluate_action_set_prediction,
    evaluate_aggregate_predictions,
    validate_predictions
)
from forecasting.ensemble_aggregation import threshold_capped_ensemble
from forecasting.action_prompts import (
    create_novaris_action_prediction_prompt,
    create_tethys_action_prediction_prompt
)
from forecasting.persona_simplified import load_simplified_personas
from forecasting.persona_generator import CognitiveProfile
from forecasting.simulation_data import get_state_before, get_events
from forecasting.config import RANDOM_SEED


@dataclass
class ConditionConfig:
    """Configuration for an experimental condition."""
    name: str
    persona_type: Optional[str]  # None, "simplified", or "complex"
    include_history: bool
    min_period: int  # Minimum period this condition can run


# Define all 6 conditions
CONDITIONS = [
    ConditionConfig("generic_no_history", None, False, 1),
    ConditionConfig("generic_with_history", None, True, 3),
    ConditionConfig("simplified_no_history", "simplified", False, 1),
    ConditionConfig("simplified_with_history", "simplified", True, 3),
    ConditionConfig("complex_no_history", "complex", False, 1),
    ConditionConfig("complex_with_history", "complex", True, 3),
]


def load_personas(persona_type: Optional[str], n_agents: int):
    """Load N personas of the specified type."""
    if persona_type is None:
        return [None] * n_agents  # Generic condition

    elif persona_type == "simplified":
        all_personas = load_simplified_personas()
        return all_personas[:n_agents]

    elif persona_type == "complex":
        with open("forecasting/persona_profiles.json") as f:
            data = json.load(f)
        personas = [CognitiveProfile(**p) for p in data['personas'][:n_agents]]
        return personas

    else:
        raise ValueError(f"Unknown persona type: {persona_type}")


def create_historical_summary(ground_truth: dict, period: int) -> str:
    """
    Create summary of observable actions from prior periods.
    Uses external intelligence framing only (no internal decision processes).
    """
    if period <= 1:
        return ""

    history_lines = ["\nOBSERVABLE ACTION HISTORY (External Intelligence):\n"]

    for p in range(1, period):
        period_data = ground_truth.get(p)
        if not period_data:
            continue

        novaris_actions = period_data['major_power']['actions']
        tethys_actions = period_data['small_power']['actions']

        history_lines.append(f"\nPeriod {p}:")
        history_lines.append(f"  Novaris: {', '.join(novaris_actions) if novaris_actions else 'No observed actions'}")
        history_lines.append(f"  Tethys: {', '.join(tethys_actions) if tethys_actions else 'No observed actions'}")

    return "\n".join(history_lines)


def run_single_prediction(
    faction: str,
    period: int,
    state_before: dict,
    external_events: list,
    plausible_text: str,
    novaris_actions: list,
    persona,
    history_text: str = ""
) -> dict:
    """Run a single agent's prediction."""

    # Create forecaster in this thread to avoid sharing issues
    forecaster = BaseLLMForecaster(model="deepseek/deepseek-v3.2")

    # Create base prompt
    if faction == 'novaris':
        base_prompt = create_novaris_action_prediction_prompt(
            period=period,
            state_before=state_before,
            external_events=external_events,
            plausible_actions_text=plausible_text
        )
    else:
        base_prompt = create_tethys_action_prediction_prompt(
            period=period,
            state_before=state_before,
            external_events=external_events,
            novaris_actions=novaris_actions,
            plausible_actions_text=plausible_text
        )

    # Prepend history if provided
    if history_text:
        prompt = f"{history_text}\n\n{'='*80}\n\n{base_prompt}"
    else:
        prompt = base_prompt

    # Add persona system prompt if provided
    system_prompt = """You are an expert strategic analyst specializing in geopolitical forecasting.

Your task is to predict which actions a faction will take based on strategic analysis of:
- Current military, economic, and diplomatic position
- External events and their implications
- Strategic objectives and constraints
- Available action options

Apply rigorous strategic reasoning to predict the most likely action set.
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
            return {'predicted_actions': []}

        if not response_text or response_text.strip() == "":
            print(f"    [ERROR] Empty response from API")
            return {'predicted_actions': []}

        # Strip markdown code fences if present
        response_text = response_text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]  # Remove ```json
        if response_text.startswith("```"):
            response_text = response_text[3:]  # Remove ```
        if response_text.endswith("```"):
            response_text = response_text[:-3]  # Remove trailing ```
        response_text = response_text.strip()

        result = json.loads(response_text)
        return result

    except json.JSONDecodeError as e:
        print(f"    [ERROR] JSON decode failed: {e}")
        print(f"    Response preview: {response_text[:200] if response_text else 'None'}")
        return {'predicted_actions': []}
    except Exception as e:
        print(f"    [ERROR] Prediction failed: {e}")
        return {'predicted_actions': []}


def run_n_predictions_parallel(
    n: int,
    faction: str,
    period: int,
    state_before: dict,
    external_events: list,
    plausible_text: str,
    novaris_actions: list,
    personas: List,
    history_text: str = "",
    max_workers: int = 5
) -> List[dict]:
    """Run N predictions in parallel."""

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for i in range(n):
            persona = personas[i] if i < len(personas) else None
            # Add small delay between submissions to avoid overwhelming API
            if i % 10 == 0 and i > 0:
                time.sleep(0.5)

            future = executor.submit(
                run_single_prediction,
                faction,
                period,
                state_before,
                external_events,
                plausible_text,
                novaris_actions,
                persona,
                history_text
            )
            futures.append(future)

        # Collect results
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"    [ERROR] Prediction failed: {e}")
                results.append({'predicted_actions': []})

    return results


def run_condition(
    condition: ConditionConfig,
    period: int,
    n_agents: int,
    ground_truth: dict,
    valid_actions: List[str],
    plausible_text: str,
    output_dir: Path
) -> Dict:
    """Run a single condition for a single period."""

    print(f"\n{'='*60}")
    print(f"Condition: {condition.name}")
    print(f"Period: {period}")
    print(f"N agents: {n_agents}")
    print(f"{'='*60}")

    # Get simulation data for this period
    state_before = get_state_before(period)
    external_events = get_events(period)

    # Load personas
    personas = load_personas(condition.persona_type, n_agents)

    # Create history text if needed
    history_text = ""
    if condition.include_history and period >= 3:
        history_text = create_historical_summary(ground_truth, period)

    results = {
        'condition': condition.name,
        'period': period,
        'n_agents': n_agents,
        'factions': {}
    }

    # Get ground truth actions for Novaris (needed for Tethys prompt)
    novaris_actual = ground_truth[period]['major_power']['actions']

    # Run for both factions
    for faction_key, faction_name in [('major_power', 'novaris'), ('small_power', 'tethys')]:
        print(f"\n  Faction: {faction_name.upper()}")

        # Get ground truth
        actual_actions = ground_truth[period][faction_key]['actions']
        print(f"  Ground truth: {len(actual_actions)} actions")

        # Run N predictions in parallel
        start_time = time.time()
        prediction_dicts = run_n_predictions_parallel(
            n=n_agents,
            faction=faction_name,
            period=period,
            state_before=state_before,
            external_events=external_events,
            plausible_text=plausible_text,
            novaris_actions=novaris_actual,
            personas=personas,
            history_text=history_text
        )

        # Validate predictions (expects list of dicts with 'predicted_actions' key)
        validated_predictions = validate_predictions(prediction_dicts, valid_actions)

        duration = time.time() - start_time
        print(f"  Completed in {duration:.1f}s ({duration/n_agents:.2f}s per agent)")

        # Evaluate individual averaging
        print(f"  Evaluating individual averaging...")
        individual_metrics = evaluate_aggregate_predictions(
            validated_predictions,
            actual_actions
        )

        # Evaluate ensemble aggregation
        # Use vote threshold (30% of agents) with max cap of 12
        # Ensemble predicts 0-12 actions based on what agents actually vote for
        print(f"  Evaluating ensemble aggregation...")
        ensemble_pred = threshold_capped_ensemble(
            validated_predictions,
            min_vote_fraction=0.30,
            max_actions=12
        )
        ensemble_metrics = evaluate_action_set_prediction(ensemble_pred, actual_actions)

        print(f"  [RESULTS] Individual F1: {individual_metrics['mean_f1']:.3f}, Ensemble F1: {ensemble_metrics['f1']:.3f}")

        # Store results
        results['factions'][faction_name] = {
            'ground_truth': actual_actions,
            'n_predictions': len(validated_predictions),
            'individual_metrics': individual_metrics,
            'ensemble_prediction': ensemble_pred,
            'ensemble_metrics': ensemble_metrics,
            'duration_seconds': duration
        }

    # Save condition results
    condition_file = output_dir / f"{condition.name}_period_{period}.json"
    with open(condition_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n  Saved: {condition_file}")

    return results


def main():
    """Run the full experiment: periods 1-3 with appropriate conditions."""

    print("="*60)
    print("MULTI-CONDITION FORECASTING EXPERIMENT")
    print("Period 1 ONLY | N=100 agents per condition")
    print("="*60)

    # Setup
    n_agents = 100
    output_dir = Path("outputs/experiment_period_1")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load data
    print("\nLoading data...")
    plausible_actions, descriptions = load_plausible_actions()
    plausible_text = format_plausible_actions_for_prompt(plausible_actions, descriptions)
    valid_actions = get_all_valid_actions()
    ground_truth = load_ground_truth()

    print(f"  Valid actions: {len(valid_actions)}")
    print(f"  Ground truth periods: {len(ground_truth)}")

    # Track all results
    all_results = []

    # Run period 1 only
    for period in [1]:
        print(f"\n{'#'*60}")
        print(f"PERIOD {period}")
        print(f"{'#'*60}")

        # Filter conditions that can run at this period
        applicable_conditions = [
            c for c in CONDITIONS
            if c.min_period <= period
        ]

        print(f"\nRunning {len(applicable_conditions)} conditions for period {period}:")
        for c in applicable_conditions:
            print(f"  - {c.name}")

        # Run each condition
        for condition in applicable_conditions:
            try:
                result = run_condition(
                    condition=condition,
                    period=period,
                    n_agents=n_agents,
                    ground_truth=ground_truth,
                    valid_actions=valid_actions,
                    plausible_text=plausible_text,
                    output_dir=output_dir
                )
                all_results.append(result)

            except Exception as e:
                print(f"\n[ERROR] Condition {condition.name} failed: {e}")
                import traceback
                traceback.print_exc()

    # Save summary
    summary_file = output_dir / "experiment_summary.json"
    with open(summary_file, 'w') as f:
        json.dump({
            'n_agents': n_agents,
            'periods': [1],
            'total_conditions_run': len(all_results),
            'results': all_results,
            'timestamp': datetime.now().isoformat()
        }, f, indent=2)

    print(f"\n{'='*60}")
    print(f"EXPERIMENT COMPLETE")
    print(f"Total condition-periods run: {len(all_results)}")
    print(f"Summary saved: {summary_file}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
