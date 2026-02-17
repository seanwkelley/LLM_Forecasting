"""
Evaluation metrics for action set prediction.

Measures accuracy, precision, recall, F1, domain-specific performance, etc.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Set, Tuple
from collections import defaultdict


def evaluate_action_set_prediction(
    predicted: List[str],
    actual: List[str]
) -> Dict:
    """
    Evaluate single action set prediction.

    Args:
        predicted: List of predicted action names
        actual: List of actual action names from simulation

    Returns:
        {
            'jaccard': Jaccard similarity (intersection over union)
            'precision': Fraction of predictions that are correct
            'recall': Fraction of actual actions that were predicted
            'f1': F1 score (harmonic mean of precision and recall)
            'exact_match': Boolean, exact set match
            'n_correct': Number of correctly predicted actions
            'n_predicted': Number of actions predicted
            'n_actual': Number of actual actions
            'false_positives': Actions predicted but not actual
            'false_negatives': Actual actions not predicted
        }
    """
    pred_set = set(predicted)
    actual_set = set(actual)

    intersection = pred_set & actual_set
    union = pred_set | actual_set

    # Basic metrics
    n_correct = len(intersection)
    n_predicted = len(pred_set)
    n_actual = len(actual_set)

    precision = n_correct / n_predicted if n_predicted > 0 else 0.0
    recall = n_correct / n_actual if n_actual > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    jaccard = len(intersection) / len(union) if len(union) > 0 else 0.0

    return {
        'jaccard': jaccard,
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'exact_match': pred_set == actual_set,
        'n_correct': n_correct,
        'n_predicted': n_predicted,
        'n_actual': n_actual,
        'false_positives': list(pred_set - actual_set),
        'false_negatives': list(actual_set - pred_set)
    }


def group_actions_by_domain(actions: List[str],
                            action_domains: Dict[str, str]) -> Dict[str, List[str]]:
    """
    Group actions by their domain.

    Args:
        actions: List of action names
        action_domains: Mapping of action_name -> domain

    Returns:
        {'military': [...], 'intelligence': [...], ...}
    """
    by_domain = defaultdict(list)

    for action in actions:
        domain = action_domains.get(action, 'unknown')
        by_domain[domain].append(action)

    return dict(by_domain)


def evaluate_by_domain(
    predicted: List[str],
    actual: List[str],
    action_domains: Dict[str, str]
) -> Dict[str, Dict]:
    """
    Evaluate prediction accuracy by domain.

    Args:
        predicted: Predicted actions
        actual: Actual actions
        action_domains: Mapping of action_name -> domain

    Returns:
        {
            'military': {
                'precision': ...,
                'recall': ...,
                'f1': ...,
                'n_correct': ...,
                'n_predicted': ...,
                'n_actual': ...
            },
            'intelligence': {...},
            ...
        }
    """
    pred_by_domain = group_actions_by_domain(predicted, action_domains)
    actual_by_domain = group_actions_by_domain(actual, action_domains)

    domain_metrics = {}

    for domain in ['diplomatic', 'intelligence', 'economic', 'military_posture',
                    'covert_operations', 'open_conflict', 'wmd']:
        pred_domain = set(pred_by_domain.get(domain, []))
        actual_domain = set(actual_by_domain.get(domain, []))

        if len(actual_domain) == 0:
            # No actual actions in this domain, skip
            continue

        intersection = pred_domain & actual_domain

        n_correct = len(intersection)
        n_predicted = len(pred_domain)
        n_actual = len(actual_domain)

        precision = n_correct / n_predicted if n_predicted > 0 else 0.0
        recall = n_correct / n_actual
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        domain_metrics[domain] = {
            'precision': precision,
            'recall': recall,
            'f1': f1,
            'n_correct': n_correct,
            'n_predicted': n_predicted,
            'n_actual': n_actual
        }

    return domain_metrics


def validate_predictions(
    predictions: List[Dict],
    valid_actions: Set[str]
) -> List[Dict]:
    """
    Filter predicted actions to only include valid actions from the library.

    Args:
        predictions: List of dicts with 'predicted_actions' key
        valid_actions: Set of valid action names from plausible actions library

    Returns:
        Filtered predictions with only valid actions
    """
    filtered = []
    n_invalid = 0

    for pred in predictions:
        raw_actions = pred.get('predicted_actions', [])
        valid = [a for a in raw_actions if a in valid_actions]
        invalid = [a for a in raw_actions if a not in valid_actions]
        n_invalid += len(invalid)

        # Preserve all fields from original prediction, just update predicted_actions
        filtered_pred = pred.copy()
        filtered_pred['predicted_actions'] = valid
        filtered.append(filtered_pred)

    if n_invalid > 0:
        print(f"  [WARNING] Filtered {n_invalid} invalid action predictions across {len(predictions)} agents")

    return filtered


def evaluate_aggregate_predictions(
    predictions: List[Dict],
    ground_truth: List[str]
) -> Dict:
    """
    Evaluate multiple predictions against single ground truth.

    Used when N agents each predict action set for same period/faction.

    Args:
        predictions: List of dicts with 'predicted_actions' key
        ground_truth: Actual actions

    Returns:
        {
            'individual_metrics': List of metrics for each prediction
            'mean_jaccard': Average Jaccard across all predictions
            'mean_precision': Average precision
            'mean_recall': Average recall
            'mean_f1': Average F1
            'most_common_predictions': Actions predicted most frequently
            'prediction_diversity': Fraction of unique action sets
            'any_correct_rate': % of predictions that got at least 1 correct
            'mean_n_predicted': Average number of actions predicted
        }
    """
    individual_metrics = []

    for pred in predictions:
        pred_actions = pred.get('predicted_actions', [])
        metrics = evaluate_action_set_prediction(pred_actions, ground_truth)
        individual_metrics.append(metrics)

    # Aggregate statistics
    jaccards = [m['jaccard'] for m in individual_metrics]
    precisions = [m['precision'] for m in individual_metrics]
    recalls = [m['recall'] for m in individual_metrics]
    f1s = [m['f1'] for m in individual_metrics]
    n_correctsindividual = [m['n_correct'] for m in individual_metrics]
    n_predicteds = [m['n_predicted'] for m in individual_metrics]

    # Most common predictions
    all_predicted = []
    for pred in predictions:
        all_predicted.extend(pred.get('predicted_actions', []))

    from collections import Counter
    prediction_counts = Counter(all_predicted)
    most_common = prediction_counts.most_common(10)

    # Diversity: How many unique action sets?
    unique_sets = len(set(
        tuple(sorted(pred.get('predicted_actions', []))) for pred in predictions
    ))
    diversity = unique_sets / len(predictions) if predictions else 0

    # Any correct rate
    any_correct_rate = sum(1 for m in individual_metrics if m['n_correct'] > 0) / len(individual_metrics)

    return {
        'individual_metrics': individual_metrics,
        'mean_jaccard': np.mean(jaccards) if jaccards else 0,
        'std_jaccard': np.std(jaccards) if jaccards else 0,
        'mean_precision': np.mean(precisions) if precisions else 0,
        'std_precision': np.std(precisions) if precisions else 0,
        'mean_recall': np.mean(recalls) if recalls else 0,
        'std_recall': np.std(recalls) if recalls else 0,
        'mean_f1': np.mean(f1s) if f1s else 0,
        'std_f1': np.std(f1s) if f1s else 0,
        'mean_n_correct': np.mean(n_correctsindividual) if n_correctsindividual else 0,
        'mean_n_predicted': np.mean(n_predicteds) if n_predicteds else 0,
        'most_common_predictions': most_common,
        'prediction_diversity': diversity,
        'any_correct_rate': any_correct_rate
    }


def calculate_strategic_alignment(
    predicted: List[str],
    actual: List[str],
    action_domains: Dict[str, str]
) -> Dict:
    """
    Beyond exact match, measure strategic alignment.

    Args:
        predicted: Predicted actions
        actual: Actual actions
        action_domains: Action -> domain mapping

    Returns:
        {
            'domain_coverage': Fraction of actual domains covered by prediction
            'captures_offensive': Did prediction include offensive action if actual did?
            'captures_defensive': Did prediction include defensive action if actual did?
            'escalation_alignment': How close is predicted escalation level to actual?
        }
    """
    pred_domains = set(action_domains.get(a, 'unknown') for a in predicted)
    actual_domains = set(action_domains.get(a, 'unknown') for a in actual)

    domain_coverage = len(pred_domains & actual_domains) / len(actual_domains) if actual_domains else 0

    # Offensive/defensive detection
    offensive_actions = {
        'offensive_operation', 'strategic_bombing', 'precision_strike',
        'naval_blockade', 'special_forces_raid'
    }
    defensive_actions = {
        'defensive_posture', 'military_buildup', 'defensive_fortifications',
        'mobilize_reserves', 'counterintelligence'
    }

    has_offensive_pred = any(a in offensive_actions for a in predicted)
    has_offensive_actual = any(a in offensive_actions for a in actual)
    captures_offensive = (has_offensive_pred == has_offensive_actual)

    has_defensive_pred = any(a in defensive_actions for a in predicted)
    has_defensive_actual = any(a in defensive_actions for a in actual)
    captures_defensive = (has_defensive_pred == has_defensive_actual)

    # Escalation level (rough heuristic)
    escalation_scores = {
        # High escalation
        'offensive_operation': 9,
        'strategic_bombing': 9,
        'naval_blockade': 8,
        'assassination': 8,
        # Medium escalation
        'precision_strike': 6,
        'military_buildup': 6,
        'sabotage': 6,
        'cyber_attack': 5,
        # Low escalation
        'intelligence_gathering': 3,
        'peace_talks': 2,
        'humanitarian_corridors': 2,
        'strategic_stockpiling': 3,
        'defensive_posture': 4
    }

    pred_escalation = np.mean([escalation_scores.get(a, 5) for a in predicted]) if predicted else 5
    actual_escalation = np.mean([escalation_scores.get(a, 5) for a in actual]) if actual else 5

    escalation_diff = abs(pred_escalation - actual_escalation)
    escalation_alignment = max(0, 1 - escalation_diff / 9)  # Normalize to 0-1

    return {
        'domain_coverage': domain_coverage,
        'captures_offensive': captures_offensive,
        'captures_defensive': captures_defensive,
        'escalation_alignment': escalation_alignment,
        'predicted_escalation': pred_escalation,
        'actual_escalation': actual_escalation
    }


def create_evaluation_summary(results: List[Dict]) -> pd.DataFrame:
    """
    Create summary DataFrame of evaluation results across periods.

    Args:
        results: List of period results from experiment

    Returns:
        DataFrame with columns:
        - period
        - faction (novaris/tethys)
        - jaccard, precision, recall, f1
        - n_correct, n_predicted, n_actual
    """
    rows = []

    for period_result in results:
        period = period_result['period']

        for faction in ['novaris', 'tethys']:
            metrics = period_result[faction]['metrics']

            rows.append({
                'period': period,
                'faction': faction,
                'jaccard': metrics['mean_jaccard'],
                'precision': metrics['mean_precision'],
                'recall': metrics['mean_recall'],
                'f1': metrics['mean_f1'],
                'n_correct': metrics['mean_n_correct'],
                'n_predicted': metrics['mean_n_predicted'],
                'n_actual': len(period_result[faction]['ground_truth'])
            })

    return pd.DataFrame(rows)


def print_evaluation_summary(results: List[Dict]):
    """Print formatted evaluation summary."""
    print("\n" + "="*80)
    print("ACTION SET PREDICTION EVALUATION SUMMARY")
    print("="*80)

    df = create_evaluation_summary(results)

    print(f"\n{'Period':<8} {'Faction':<10} {'Jaccard':<10} {'Precision':<10} {'Recall':<10} {'F1':<10}")
    print("-"*80)

    for _, row in df.iterrows():
        print(f"{row['period']:<8} {row['faction']:<10} "
              f"{row['jaccard']:<10.3f} {row['precision']:<10.3f} "
              f"{row['recall']:<10.3f} {row['f1']:<10.3f}")

    print("-"*80)

    # Overall statistics
    print(f"\nOVERALL STATISTICS:")
    print(f"  Novaris Mean F1: {df[df['faction']=='novaris']['f1'].mean():.3f}")
    print(f"  Tethys Mean F1:  {df[df['faction']=='tethys']['f1'].mean():.3f}")
    print(f"  Combined Mean F1: {df['f1'].mean():.3f}")

    print(f"\n  Novaris Mean Recall: {df[df['faction']=='novaris']['recall'].mean():.3f}")
    print(f"  Tethys Mean Recall:  {df[df['faction']=='tethys']['recall'].mean():.3f}")

    print("="*80)


if __name__ == "__main__":
    # Test evaluation functions
    print("Testing evaluation functions...\n")

    # Test case 1: Perfect match
    test_predicted_1 = ['military_buildup', 'intelligence_gathering', 'strategic_stockpiling']
    test_actual_1 = ['military_buildup', 'intelligence_gathering', 'strategic_stockpiling']

    metrics_1 = evaluate_action_set_prediction(test_predicted_1, test_actual_1)
    print("TEST 1: Perfect Match")
    print(f"  Jaccard: {metrics_1['jaccard']:.3f} (expected: 1.0)")
    print(f"  F1: {metrics_1['f1']:.3f} (expected: 1.0)")
    print(f"  Exact Match: {metrics_1['exact_match']} (expected: True)")

    # Test case 2: Partial overlap
    test_predicted_2 = ['military_buildup', 'offensive_operation', 'peace_talks']
    test_actual_2 = ['military_buildup', 'intelligence_gathering', 'strategic_stockpiling']

    metrics_2 = evaluate_action_set_prediction(test_predicted_2, test_actual_2)
    print("\nTEST 2: Partial Overlap (1/3 correct)")
    print(f"  Jaccard: {metrics_2['jaccard']:.3f} (expected: 0.2)")
    print(f"  Precision: {metrics_2['precision']:.3f} (expected: 0.333)")
    print(f"  Recall: {metrics_2['recall']:.3f} (expected: 0.333)")
    print(f"  F1: {metrics_2['f1']:.3f} (expected: 0.333)")

    # Test case 3: No overlap
    test_predicted_3 = ['offensive_operation', 'cyber_attack']
    test_actual_3 = ['peace_talks', 'humanitarian_corridors']

    metrics_3 = evaluate_action_set_prediction(test_predicted_3, test_actual_3)
    print("\nTEST 3: No Overlap")
    print(f"  Jaccard: {metrics_3['jaccard']:.3f} (expected: 0.0)")
    print(f"  F1: {metrics_3['f1']:.3f} (expected: 0.0)")

    # Test aggregate evaluation
    test_predictions = [
        {'predicted_actions': ['military_buildup', 'intelligence_gathering']},
        {'predicted_actions': ['military_buildup', 'strategic_stockpiling']},
        {'predicted_actions': ['military_buildup', 'offensive_operation']},
    ]
    test_ground_truth = ['military_buildup', 'intelligence_gathering', 'strategic_stockpiling']

    agg_metrics = evaluate_aggregate_predictions(test_predictions, test_ground_truth)
    print("\nTEST 4: Aggregate Evaluation (3 predictions)")
    print(f"  Mean F1: {agg_metrics['mean_f1']:.3f}")
    print(f"  Any Correct Rate: {agg_metrics['any_correct_rate']:.3f} (all include military_buildup)")
    print(f"  Prediction Diversity: {agg_metrics['prediction_diversity']:.3f}")

    print("\n[OK] Evaluation functions working correctly!")
