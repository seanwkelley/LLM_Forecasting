"""
Test Ensemble Aggregation vs Individual Average Performance

Compares:
- Individual average F1 (what we've been measuring)
- Ensemble F1 (majority voting from 100 agents)

For both generic and personalized conditions.
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
from forecasting.action_evaluation import (
    evaluate_action_set_prediction,
    evaluate_aggregate_predictions
)
from forecasting.ensemble_aggregation import (
    majority_voting_ensemble,
    top_k_ensemble,
    adaptive_threshold_ensemble,
    ensemble_statistics
)
from forecasting.forecaster_base import BaseLLMForecaster
from forecasting.persona_simplified import load_simplified_personas
from forecasting.config import RANDOM_SEED


print("="*80)
print("ENSEMBLE AGGREGATION TEST")
print("="*80)
print("Testing: Individual Average F1 vs Ensemble F1")
print("Period: 10 (most complex scenario)")
print("N: 100 agents per condition")
print()


def load_period_10_state():
    """Period 10 state variables"""
    return {
        'territory_controlled': 0.18,
        'military_balance': -0.08,
        'crisis_level': 7.5,
        'novaris_gdp': 88.0,
        'tethys_gdp': 26.0,
        'international_support': 0.58,
        'sanctions_level': 0.42
    }


def load_period_10_events():
    """Period 10 external events"""
    return [
        "Battlefield: Aggressor breakthrough - significant territorial gains and encirclement",
        "Economic: Energy price surge due to supply disruptions",
        "Diplomatic: Peace talks proposed but tensions remain high",
        "Intelligence: Reports of covert operations by both sides"
    ]


def run_predictions(condition: str, n_agents: int, personas=None):
    """
    Run predictions for both factions and return individual predictions.

    Returns:
        {
            'novaris': [{'predicted_actions': [...]}, ...],
            'tethys': [{'predicted_actions': [...]}, ...]
        }
    """
    state = load_period_10_state()
    events = load_period_10_events()

    ground_truth = load_ground_truth()
    novaris_actual = ground_truth[10]['major_power']['actions']
    tethys_actual = ground_truth[10]['small_power']['actions']

    plausible, descriptions = load_plausible_actions()
    plausible_text = format_plausible_actions_for_prompt(plausible, descriptions)

    forecaster = BaseLLMForecaster(model="deepseek/deepseek-v3.2")

    # System prompts
    if condition == "generic":
        system_prompt_base = """You are an expert strategic analyst specializing in geopolitical forecasting.

Your task is to predict which actions a faction will take based on strategic analysis.
Apply rigorous strategic reasoning. Output ONLY valid JSON in the exact format specified."""

    def make_prediction(agent_id, faction, prompt_func, actual_actions=None):
        """Make a single prediction"""
        if faction == 'novaris':
            prompt = prompt_func(
                period=10,
                state_before=state,
                external_events=events,
                plausible_actions_text=plausible_text
            )
        else:
            prompt = prompt_func(
                period=10,
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
        except Exception as e:
            print(f"[ERROR] Agent {agent_id} ({faction}): {e}")
            return {'predicted_actions': []}

    # Novaris predictions
    print(f"  Running {n_agents} Novaris predictions...")
    novaris_preds = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(make_prediction, i, 'novaris', create_novaris_action_prediction_prompt)
            for i in range(n_agents)
        ]
        novaris_preds = [f.result() for f in as_completed(futures)]

    # Tethys predictions
    print(f"  Running {n_agents} Tethys predictions...")
    tethys_preds = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(make_prediction, i, 'tethys', create_tethys_action_prediction_prompt, novaris_actual)
            for i in range(n_agents)
        ]
        tethys_preds = [f.result() for f in as_completed(futures)]

    return {
        'novaris': novaris_preds,
        'tethys': tethys_preds
    }


def evaluate_ensemble_methods(predictions, ground_truth, faction_name):
    """
    Evaluate multiple ensemble methods and compare to individual average.

    Returns metrics for:
    - Individual average (baseline)
    - Majority voting (threshold=0.5)
    - Majority voting (threshold=0.3)
    - Top-K (K=5)
    - Adaptive threshold
    """
    print(f"\n  {faction_name.upper()} Evaluation:")
    print("  " + "-"*50)

    # 1. Individual average (baseline)
    agg_metrics = evaluate_aggregate_predictions(predictions, ground_truth)
    individual_avg_f1 = agg_metrics['mean_f1']

    print(f"  Individual Average F1: {individual_avg_f1:.3f}")
    print(f"    Mean predictions/agent: {agg_metrics['mean_n_predicted']:.1f}")
    print(f"    Diversity: {agg_metrics['prediction_diversity']:.3f}")

    # 2. Majority voting (threshold=0.5)
    ensemble_50 = majority_voting_ensemble(predictions, threshold=0.5)
    metrics_50 = evaluate_action_set_prediction(ensemble_50, ground_truth)

    print(f"\n  Majority Voting (50% threshold):")
    print(f"    F1: {metrics_50['f1']:.3f} ({metrics_50['f1'] - individual_avg_f1:+.3f})")
    print(f"    Precision: {metrics_50['precision']:.3f}")
    print(f"    Recall: {metrics_50['recall']:.3f}")
    print(f"    Actions predicted: {len(ensemble_50)}")

    # 3. Majority voting (threshold=0.3)
    ensemble_30 = majority_voting_ensemble(predictions, threshold=0.3)
    metrics_30 = evaluate_action_set_prediction(ensemble_30, ground_truth)

    print(f"\n  Majority Voting (30% threshold):")
    print(f"    F1: {metrics_30['f1']:.3f} ({metrics_30['f1'] - individual_avg_f1:+.3f})")
    print(f"    Precision: {metrics_30['precision']:.3f}")
    print(f"    Recall: {metrics_30['recall']:.3f}")
    print(f"    Actions predicted: {len(ensemble_30)}")

    # 4. Top-K (K=len(ground_truth))
    target_k = len(ground_truth)
    ensemble_topk = top_k_ensemble(predictions, k=target_k)
    metrics_topk = evaluate_action_set_prediction(ensemble_topk, ground_truth)

    print(f"\n  Top-K (K={target_k}):")
    print(f"    F1: {metrics_topk['f1']:.3f} ({metrics_topk['f1'] - individual_avg_f1:+.3f})")
    print(f"    Precision: {metrics_topk['precision']:.3f}")
    print(f"    Recall: {metrics_topk['recall']:.3f}")
    print(f"    Actions predicted: {len(ensemble_topk)}")

    # 5. Adaptive threshold (target size = ground truth size)
    ensemble_adaptive = adaptive_threshold_ensemble(predictions, target_set_size=target_k)
    metrics_adaptive = evaluate_action_set_prediction(ensemble_adaptive, ground_truth)

    print(f"\n  Adaptive Threshold (target={target_k}):")
    print(f"    F1: {metrics_adaptive['f1']:.3f} ({metrics_adaptive['f1'] - individual_avg_f1:+.3f})")
    print(f"    Precision: {metrics_adaptive['precision']:.3f}")
    print(f"    Recall: {metrics_adaptive['recall']:.3f}")
    print(f"    Actions predicted: {len(ensemble_adaptive)}")

    # Find best method
    methods = {
        'Individual Avg': individual_avg_f1,
        'Majority 50%': metrics_50['f1'],
        'Majority 30%': metrics_30['f1'],
        f'Top-{target_k}': metrics_topk['f1'],
        'Adaptive': metrics_adaptive['f1']
    }

    best_method = max(methods.items(), key=lambda x: x[1])
    print(f"\n  [OK] BEST: {best_method[0]} (F1={best_method[1]:.3f})")

    return {
        'individual_avg_f1': individual_avg_f1,
        'majority_50_f1': metrics_50['f1'],
        'majority_30_f1': metrics_30['f1'],
        'topk_f1': metrics_topk['f1'],
        'adaptive_f1': metrics_adaptive['f1'],
        'best_method': best_method[0],
        'best_f1': best_method[1],
        'improvement': best_method[1] - individual_avg_f1
    }


# Main experiment
print("Loading resources...")
ground_truth = load_ground_truth()
all_personas = load_simplified_personas()
random.seed(RANDOM_SEED)
personas = random.sample(all_personas, 100)
random.seed()

print(f"  Ground truth: Novaris={len(ground_truth[10]['major_power']['actions'])}, "
      f"Tethys={len(ground_truth[10]['small_power']['actions'])}")
print()

# Test 1: Generic agents
print("="*80)
print("CONDITION 1: GENERIC AGENTS (N=100)")
print("="*80)

generic_preds = run_predictions("generic", 100)

generic_novaris_results = evaluate_ensemble_methods(
    generic_preds['novaris'],
    ground_truth[10]['major_power']['actions'],
    'Novaris'
)

generic_tethys_results = evaluate_ensemble_methods(
    generic_preds['tethys'],
    ground_truth[10]['small_power']['actions'],
    'Tethys'
)

# Test 2: Simplified personalized agents
print("\n" + "="*80)
print("CONDITION 2: SIMPLIFIED PERSONALIZED AGENTS (N=100)")
print("="*80)

simplified_preds = run_predictions("simplified", 100, personas)

simplified_novaris_results = evaluate_ensemble_methods(
    simplified_preds['novaris'],
    ground_truth[10]['major_power']['actions'],
    'Novaris'
)

simplified_tethys_results = evaluate_ensemble_methods(
    simplified_preds['tethys'],
    ground_truth[10]['small_power']['actions'],
    'Tethys'
)

# Final comparison
print("\n" + "="*80)
print("FINAL COMPARISON")
print("="*80)

print("\nGENERIC AGENTS:")
print(f"  Novaris: {generic_novaris_results['best_method']} = {generic_novaris_results['best_f1']:.3f} "
      f"({generic_novaris_results['improvement']:+.3f} vs individual avg)")
print(f"  Tethys:  {generic_tethys_results['best_method']} = {generic_tethys_results['best_f1']:.3f} "
      f"({generic_tethys_results['improvement']:+.3f} vs individual avg)")

generic_combined = (generic_novaris_results['best_f1'] + generic_tethys_results['best_f1']) / 2
generic_individual_combined = (generic_novaris_results['individual_avg_f1'] + generic_tethys_results['individual_avg_f1']) / 2

print(f"\n  Combined ensemble F1: {generic_combined:.3f}")
print(f"  Combined individual F1: {generic_individual_combined:.3f}")
print(f"  Ensemble improvement: {generic_combined - generic_individual_combined:+.3f} "
      f"({(generic_combined - generic_individual_combined)/generic_individual_combined*100:+.1f}%)")

print("\nSIMPLIFIED PERSONALIZED AGENTS:")
print(f"  Novaris: {simplified_novaris_results['best_method']} = {simplified_novaris_results['best_f1']:.3f} "
      f"({simplified_novaris_results['improvement']:+.3f} vs individual avg)")
print(f"  Tethys:  {simplified_tethys_results['best_method']} = {simplified_tethys_results['best_f1']:.3f} "
      f"({simplified_tethys_results['improvement']:+.3f} vs individual avg)")

simplified_combined = (simplified_novaris_results['best_f1'] + simplified_tethys_results['best_f1']) / 2
simplified_individual_combined = (simplified_novaris_results['individual_avg_f1'] + simplified_tethys_results['individual_avg_f1']) / 2

print(f"\n  Combined ensemble F1: {simplified_combined:.3f}")
print(f"  Combined individual F1: {simplified_individual_combined:.3f}")
print(f"  Ensemble improvement: {simplified_combined - simplified_individual_combined:+.3f} "
      f"({(simplified_combined - simplified_individual_combined)/simplified_individual_combined*100:+.1f}%)")

# Key finding
print("\n" + "="*80)
print("KEY FINDING")
print("="*80)

if generic_combined > simplified_combined:
    diff = generic_combined - simplified_combined
    pct = (diff / simplified_combined * 100) if simplified_combined > 0 else 0
    print(f"\n[OK] GENERIC ENSEMBLE WINS: {pct:.1f}% better than simplified ensemble")
    print(f"     Generic: {generic_combined:.3f} vs Simplified: {simplified_combined:.3f}")
else:
    diff = simplified_combined - generic_combined
    pct = (diff / generic_combined * 100) if generic_combined > 0 else 0
    print(f"\n[SURPRISING] SIMPLIFIED ENSEMBLE WINS: {pct:.1f}% better than generic ensemble")
    print(f"     Simplified: {simplified_combined:.3f} vs Generic: {generic_combined:.3f}")

ensemble_helps_generic = generic_combined > generic_individual_combined
ensemble_helps_simplified = simplified_combined > simplified_individual_combined

if ensemble_helps_generic and ensemble_helps_simplified:
    print(f"\n[OK] ENSEMBLE IMPROVES BOTH CONDITIONS")
    print(f"     Generic: +{(generic_combined - generic_individual_combined)/generic_individual_combined*100:.1f}%")
    print(f"     Simplified: +{(simplified_combined - simplified_individual_combined)/simplified_individual_combined*100:.1f}%")
elif ensemble_helps_generic:
    print(f"\n[OK] ENSEMBLE HELPS GENERIC ONLY (+{(generic_combined - generic_individual_combined)/generic_individual_combined*100:.1f}%)")
elif ensemble_helps_simplified:
    print(f"\n[SURPRISING] ENSEMBLE HELPS SIMPLIFIED ONLY (+{(simplified_combined - simplified_individual_combined)/simplified_individual_combined*100:.1f}%)")
else:
    print(f"\n[FAIL] ENSEMBLE HURTS BOTH CONDITIONS")

print()
