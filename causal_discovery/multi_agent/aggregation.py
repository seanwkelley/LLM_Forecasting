"""
Graph aggregation — merge multiple agents' declared causal graphs.

All functions return adjacency matrices compatible with score_market_graph()
and score_conflict_graph().
"""

from __future__ import annotations

import numpy as np

from causal_discovery.ground_truth import edges_to_matrix


CONFIDENCE_WEIGHTS = {"high": 3, "medium": 2, "low": 1}


def majority_vote(
    results: list,
    variables: list[str],
    threshold: float = 0.5,
) -> np.ndarray:
    """Include edge if > threshold fraction of agents declare it.

    Parameters
    ----------
    results : list[AgentResult]
        Agent results with declared_edges.
    variables : list[str]
        Variable names for matrix indexing.
    threshold : float
        Fraction of agents that must declare an edge for inclusion.

    Returns
    -------
    np.ndarray
        Adjacency matrix.
    """
    n = len(variables)
    n_agents = len(results)
    if n_agents == 0:
        return np.zeros((n, n), dtype=int)

    vote_matrix = np.zeros((n, n), dtype=float)
    idx = {v: i for i, v in enumerate(variables)}

    for r in results:
        for src, dst in r.declared_edges:
            if src in idx and dst in idx:
                vote_matrix[idx[src], idx[dst]] += 1

    return (vote_matrix / n_agents > threshold).astype(int)


def confidence_weighted_vote(
    results: list,
    variables: list[str],
) -> np.ndarray:
    """Weight edges by confidence: high=3, medium=2, low=1.

    Edge included if weighted_sum > N/2 (where N = number of agents,
    scaled by max possible weight per agent = 3).

    Parameters
    ----------
    results : list[AgentResult]
        Agent results with edge_confidences.
    variables : list[str]
        Variable names for matrix indexing.

    Returns
    -------
    np.ndarray
        Adjacency matrix.
    """
    n = len(variables)
    n_agents = len(results)
    if n_agents == 0:
        return np.zeros((n, n), dtype=int)

    weight_matrix = np.zeros((n, n), dtype=float)
    idx = {v: i for i, v in enumerate(variables)}

    for r in results:
        for (src, dst), conf in r.edge_confidences.items():
            if src in idx and dst in idx:
                weight_matrix[idx[src], idx[dst]] += CONFIDENCE_WEIGHTS.get(conf, 1)

    # Threshold: weighted sum > half of max possible (n_agents * 3 / 2)
    threshold = n_agents * 3 / 2
    return (weight_matrix > threshold).astype(int)


def union_merge(
    results: list,
    variables: list[str],
) -> np.ndarray:
    """Include edge if ANY agent declares it (high recall).

    Parameters
    ----------
    results : list[AgentResult]
    variables : list[str]

    Returns
    -------
    np.ndarray
        Adjacency matrix.
    """
    n = len(variables)
    if not results:
        return np.zeros((n, n), dtype=int)

    M = np.zeros((n, n), dtype=int)
    idx = {v: i for i, v in enumerate(variables)}

    for r in results:
        for src, dst in r.declared_edges:
            if src in idx and dst in idx:
                M[idx[src], idx[dst]] = 1

    return M


def intersection_merge(
    results: list,
    variables: list[str],
) -> np.ndarray:
    """Include edge only if ALL agents declare it (high precision).

    Parameters
    ----------
    results : list[AgentResult]
    variables : list[str]

    Returns
    -------
    np.ndarray
        Adjacency matrix.
    """
    n = len(variables)
    n_agents = len(results)
    if n_agents == 0:
        return np.zeros((n, n), dtype=int)

    vote_matrix = np.zeros((n, n), dtype=int)
    idx = {v: i for i, v in enumerate(variables)}

    for r in results:
        for src, dst in r.declared_edges:
            if src in idx and dst in idx:
                vote_matrix[idx[src], idx[dst]] += 1

    return (vote_matrix == n_agents).astype(int)
