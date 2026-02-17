"""
Ensemble Aggregation Methods for Action Set Prediction

Compare individual performance vs ensemble aggregation.
"""

from typing import List, Dict, Set
from collections import Counter
import numpy as np


def majority_voting_ensemble(
    predictions: List[Dict],
    threshold: float = 0.5
) -> List[str]:
    """
    Aggregate predictions via majority voting.

    An action is included in the ensemble prediction if >= threshold fraction
    of agents predicted it.

    Args:
        predictions: List of dicts with 'predicted_actions' key
        threshold: Fraction of agents that must predict an action (0.0 to 1.0)

    Returns:
        List of actions for ensemble prediction
    """
    if not predictions:
        return []

    # Count how many agents predicted each action
    action_counts = Counter()
    for pred in predictions:
        actions = pred.get('predicted_actions', [])
        for action in actions:
            action_counts[action] += 1

    # Include actions that meet threshold
    n_agents = len(predictions)
    min_votes = int(np.ceil(threshold * n_agents))

    ensemble_actions = [
        action for action, count in action_counts.items()
        if count >= min_votes
    ]

    return ensemble_actions


def confidence_weighted_ensemble(
    predictions: List[Dict],
    threshold: float = 0.5
) -> List[str]:
    """
    Aggregate predictions weighted by individual agent F1 scores.

    Args:
        predictions: List of dicts with 'predicted_actions' and 'f1_score' keys
        threshold: Weighted fraction required for inclusion

    Returns:
        List of actions for ensemble prediction
    """
    if not predictions:
        return []

    # Weight each action by the F1 score of agents who predicted it
    action_weights = {}
    total_weight = sum(pred.get('f1_score', 1.0) for pred in predictions)

    for pred in predictions:
        weight = pred.get('f1_score', 1.0)
        actions = pred.get('predicted_actions', [])

        for action in actions:
            if action not in action_weights:
                action_weights[action] = 0
            action_weights[action] += weight

    # Include actions that meet weighted threshold
    min_weight = threshold * total_weight

    ensemble_actions = [
        action for action, weight in action_weights.items()
        if weight >= min_weight
    ]

    return ensemble_actions


def top_k_ensemble(
    predictions: List[Dict],
    k: int = 5
) -> List[str]:
    """
    Select the K most commonly predicted actions.

    Args:
        predictions: List of dicts with 'predicted_actions' key
        k: Number of top actions to include

    Returns:
        List of top K actions
    """
    if not predictions:
        return []

    # Count action frequencies
    action_counts = Counter()
    for pred in predictions:
        actions = pred.get('predicted_actions', [])
        for action in actions:
            action_counts[action] += 1

    # Return top K
    top_actions = [action for action, count in action_counts.most_common(k)]

    return top_actions


def adaptive_threshold_ensemble(
    predictions: List[Dict],
    target_set_size: int = 5
) -> List[str]:
    """
    Dynamically adjust threshold to achieve target set size.

    Args:
        predictions: List of dicts with 'predicted_actions' key
        target_set_size: Desired number of actions in ensemble

    Returns:
        List of actions (approximately target_set_size)
    """
    if not predictions:
        return []

    # Count action frequencies
    action_counts = Counter()
    for pred in predictions:
        actions = pred.get('predicted_actions', [])
        for action in actions:
            action_counts[action] += 1

    # Sort by frequency
    sorted_actions = sorted(action_counts.items(), key=lambda x: x[1], reverse=True)

    # Take top target_set_size actions
    ensemble_actions = [action for action, count in sorted_actions[:target_set_size]]

    return ensemble_actions


def threshold_capped_ensemble(
    predictions: List[Dict],
    min_vote_fraction: float = 0.10,
    max_actions: int = 12
) -> List[str]:
    """
    Select actions that meet a vote threshold, capped at maximum.

    This allows the ensemble to predict 0 to max_actions based on what
    agents actually vote for, without forcing a specific count.

    Args:
        predictions: List of dicts with 'predicted_actions' key
        min_vote_fraction: Minimum fraction of agents that must vote for action (default 10%)
        max_actions: Maximum number of actions to include (structural constraint)

    Returns:
        List of actions (0 to max_actions)
    """
    if not predictions:
        return []

    n_agents = len(predictions)
    min_votes = int(np.ceil(min_vote_fraction * n_agents))

    # Count action frequencies
    action_counts = Counter()
    for pred in predictions:
        actions = pred.get('predicted_actions', [])
        for action in actions:
            action_counts[action] += 1

    # Filter by threshold and sort by votes
    qualified_actions = [
        (action, count) for action, count in action_counts.items()
        if count >= min_votes
    ]
    qualified_actions.sort(key=lambda x: x[1], reverse=True)

    # Cap at max_actions
    ensemble_actions = [action for action, count in qualified_actions[:max_actions]]

    return ensemble_actions


def ensemble_statistics(predictions: List[Dict]) -> Dict:
    """
    Compute statistics about ensemble predictions.

    Args:
        predictions: List of dicts with 'predicted_actions' key

    Returns:
        {
            'action_frequencies': {action: count},
            'most_common': List of (action, count),
            'diversity': Fraction of unique action sets,
            'mean_set_size': Average number of actions predicted,
            'std_set_size': Std dev of set sizes
        }
    """
    if not predictions:
        return {}

    # Action frequencies
    action_counts = Counter()
    for pred in predictions:
        actions = pred.get('predicted_actions', [])
        for action in actions:
            action_counts[action] += 1

    # Diversity
    unique_sets = len(set(
        tuple(sorted(pred.get('predicted_actions', []))) for pred in predictions
    ))
    diversity = unique_sets / len(predictions)

    # Set sizes
    set_sizes = [len(pred.get('predicted_actions', [])) for pred in predictions]

    return {
        'action_frequencies': dict(action_counts),
        'most_common': action_counts.most_common(10),
        'diversity': diversity,
        'mean_set_size': np.mean(set_sizes),
        'std_set_size': np.std(set_sizes),
        'n_unique_actions': len(action_counts)
    }
