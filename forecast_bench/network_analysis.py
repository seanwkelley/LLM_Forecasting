"""
Causal Network Analysis — Graph metrics and probe target selection.

Builds a networkx DiGraph from LLM-elicited causal structure, computes
per-node and per-edge centrality metrics, and selects structurally
motivated probe targets.

No LLM calls — pure graph computation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import networkx as nx


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class NodeMetrics:
    """Centrality metrics for a single node."""
    node_id: str
    description: str
    role: str  # "factor" or "outcome"
    in_degree: int = 0
    out_degree: int = 0
    betweenness: float = 0.0
    closeness: float = 0.0
    pagerank: float = 0.0
    path_relevance: float = 0.0  # fraction of shortest paths to outcome that pass through this node
    composite_importance: float = 0.0

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "description": self.description,
            "role": self.role,
            "in_degree": self.in_degree,
            "out_degree": self.out_degree,
            "betweenness": round(self.betweenness, 4),
            "closeness": round(self.closeness, 4),
            "pagerank": round(self.pagerank, 4),
            "path_relevance": round(self.path_relevance, 4),
            "composite_importance": round(self.composite_importance, 4),
        }


@dataclass
class EdgeMetrics:
    """Metrics for a single edge."""
    source: str
    target: str
    mechanism: str
    edge_betweenness: float = 0.0
    on_critical_path: bool = False

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "target": self.target,
            "mechanism": self.mechanism,
            "edge_betweenness": round(self.edge_betweenness, 4),
            "on_critical_path": self.on_critical_path,
        }


@dataclass
class ProbeTarget:
    """A selected target for probe generation."""
    target_type: str      # "node" or "edge" or "missing_edge"
    target_id: str        # node_id, or "source->target"
    description: str      # human-readable description
    importance: float     # composite importance (node) or edge betweenness (edge)
    centrality_rank: int  # rank among same-type targets (1=highest)
    on_critical_path: bool
    probe_type: str       # the specific probe to generate

    def to_dict(self) -> dict:
        return {
            "target_type": self.target_type,
            "target_id": self.target_id,
            "description": self.description,
            "importance": round(self.importance, 4),
            "centrality_rank": self.centrality_rank,
            "on_critical_path": self.on_critical_path,
            "probe_type": self.probe_type,
        }


@dataclass
class NetworkAnalysis:
    """Complete analysis results for a causal network."""
    n_nodes: int = 0
    n_edges: int = 0
    density: float = 0.0
    is_dag: bool = True
    n_weakly_connected: int = 0
    n_strongly_connected: int = 0
    outcome_node: str = ""
    node_metrics: list[NodeMetrics] = field(default_factory=list)
    edge_metrics: list[EdgeMetrics] = field(default_factory=list)
    probe_targets: list[ProbeTarget] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "n_nodes": self.n_nodes,
            "n_edges": self.n_edges,
            "density": round(self.density, 4),
            "is_dag": self.is_dag,
            "n_weakly_connected": self.n_weakly_connected,
            "n_strongly_connected": self.n_strongly_connected,
            "outcome_node": self.outcome_node,
            "node_metrics": [nm.to_dict() for nm in self.node_metrics],
            "edge_metrics": [em.to_dict() for em in self.edge_metrics],
            "probe_targets": [pt.to_dict() for pt in self.probe_targets],
        }


# =============================================================================
# GRAPH BUILDING
# =============================================================================

def _build_digraph(nodes: list[dict], edges: list[dict]) -> nx.DiGraph:
    """Build a networkx DiGraph from LLM-elicited causal structure.

    Parameters
    ----------
    nodes : list[dict]
        Each with "id", "description", "role".
    edges : list[dict]
        Each with "from", "to", "mechanism".

    Returns
    -------
    nx.DiGraph with node attributes (description, role) and edge attributes (mechanism).
    """
    G = nx.DiGraph()
    for node in nodes:
        G.add_node(
            node["id"],
            description=node.get("description", ""),
            role=node.get("role", "factor"),
        )
    for edge in edges:
        G.add_edge(
            edge["from"],
            edge["to"],
            mechanism=edge.get("mechanism", ""),
        )
    return G


# =============================================================================
# NODE METRICS
# =============================================================================

def _compute_node_metrics(G: nx.DiGraph, outcome_node: str) -> list[NodeMetrics]:
    """Compute centrality metrics for all nodes.

    Parameters
    ----------
    G : nx.DiGraph
    outcome_node : str
        The ID of the outcome node.

    Returns
    -------
    List of NodeMetrics, one per node.
    """
    betweenness = nx.betweenness_centrality(G)
    closeness = nx.closeness_centrality(G)
    pagerank = nx.pagerank(G, alpha=0.85)

    # Path relevance: fraction of factor nodes whose shortest path to outcome
    # passes through this node
    factor_nodes = [n for n in G.nodes if G.nodes[n].get("role") != "outcome"]
    path_counts = {n: 0 for n in G.nodes}
    total_paths = 0

    for src in factor_nodes:
        if src == outcome_node:
            continue
        try:
            paths = list(nx.all_shortest_paths(G, src, outcome_node))
            total_paths += len(paths)
            for path in paths:
                for node in path[1:-1]:  # exclude src and outcome
                    path_counts[node] += 1
        except nx.NetworkXNoPath:
            continue

    metrics = []
    for node_id in G.nodes:
        data = G.nodes[node_id]
        pr = path_counts.get(node_id, 0) / total_paths if total_paths > 0 else 0.0
        metrics.append(NodeMetrics(
            node_id=node_id,
            description=data.get("description", ""),
            role=data.get("role", "factor"),
            in_degree=G.in_degree(node_id),
            out_degree=G.out_degree(node_id),
            betweenness=betweenness.get(node_id, 0.0),
            closeness=closeness.get(node_id, 0.0),
            pagerank=pagerank.get(node_id, 0.0),
            path_relevance=pr,
        ))

    return metrics


def _compute_composite_importance(metrics: list[NodeMetrics]) -> list[NodeMetrics]:
    """Compute composite importance score for each node.

    Score = 0.3 * betweenness + 0.2 * pagerank + 0.2 * out_degree_norm + 0.3 * path_relevance

    Modifies metrics in place and returns them.
    """
    # Normalize out_degree to [0, 1]
    max_out = max((m.out_degree for m in metrics), default=1)
    if max_out == 0:
        max_out = 1

    for m in metrics:
        out_norm = m.out_degree / max_out
        m.composite_importance = (
            0.3 * m.betweenness
            + 0.2 * m.pagerank
            + 0.2 * out_norm
            + 0.3 * m.path_relevance
        )

    return metrics


# =============================================================================
# EDGE METRICS
# =============================================================================

def _compute_edge_metrics(G: nx.DiGraph, outcome_node: str) -> list[EdgeMetrics]:
    """Compute edge betweenness and critical-path flags.

    Parameters
    ----------
    G : nx.DiGraph
    outcome_node : str
        The ID of the outcome node.

    Returns
    -------
    List of EdgeMetrics, one per edge.
    """
    edge_betweenness = nx.edge_betweenness_centrality(G)

    # Find all edges on shortest paths to the outcome
    critical_edges = set()
    factor_nodes = [n for n in G.nodes if G.nodes[n].get("role") != "outcome"]

    for src in factor_nodes:
        if src == outcome_node:
            continue
        try:
            for path in nx.all_shortest_paths(G, src, outcome_node):
                for i in range(len(path) - 1):
                    critical_edges.add((path[i], path[i + 1]))
        except nx.NetworkXNoPath:
            continue

    metrics = []
    for u, v, data in G.edges(data=True):
        metrics.append(EdgeMetrics(
            source=u,
            target=v,
            mechanism=data.get("mechanism", ""),
            edge_betweenness=edge_betweenness.get((u, v), 0.0),
            on_critical_path=(u, v) in critical_edges,
        ))

    return metrics


# =============================================================================
# TARGET SELECTION
# =============================================================================

def _select_probe_targets(
    node_metrics: list[NodeMetrics],
    edge_metrics: list[EdgeMetrics],
    G: nx.DiGraph,
    outcome_node: str,
) -> list[ProbeTarget]:
    """Select structurally motivated probe targets.

    Target allocation (up to ~18 probes):
    - 2 high-centrality node negations
    - 1 medium-centrality node negation
    - 1 low-centrality node negation
    - 2 high-centrality node strengthening
    - 2 critical-path edge negations
    - 1 peripheral edge negation
    - 1 critical-path edge reversal
    - 2 missing-edge fabrications
    - 2 missing-node probes (LLM-generated)
    - 2 irrelevant probes (LLM-generated)

    Returns
    -------
    List of ProbeTarget objects.
    """
    targets = []

    # Sort factor nodes by composite importance (descending)
    factor_metrics = sorted(
        [m for m in node_metrics if m.role != "outcome"],
        key=lambda m: m.composite_importance,
        reverse=True,
    )

    # Assign centrality ranks
    for rank, m in enumerate(factor_metrics, start=1):
        m._rank = rank

    n_factors = len(factor_metrics)

    # --- Node targets ---

    # 2 highest-importance nodes: negation
    for m in factor_metrics[:2]:
        targets.append(ProbeTarget(
            target_type="node",
            target_id=m.node_id,
            description=m.description,
            importance=m.composite_importance,
            centrality_rank=m._rank,
            on_critical_path=m.path_relevance > 0,
            probe_type="node_negate_high",
        ))

    # 1 median-importance node: negation
    if n_factors >= 3:
        mid_idx = n_factors // 2
        m = factor_metrics[mid_idx]
        targets.append(ProbeTarget(
            target_type="node",
            target_id=m.node_id,
            description=m.description,
            importance=m.composite_importance,
            centrality_rank=m._rank,
            on_critical_path=m.path_relevance > 0,
            probe_type="node_negate_medium",
        ))

    # 1 lowest-importance node: negation
    if n_factors >= 2:
        m = factor_metrics[-1]
        targets.append(ProbeTarget(
            target_type="node",
            target_id=m.node_id,
            description=m.description,
            importance=m.composite_importance,
            centrality_rank=m._rank,
            on_critical_path=m.path_relevance > 0,
            probe_type="node_negate_low",
        ))

    # 2 highest-importance nodes: strengthening
    for m in factor_metrics[:2]:
        targets.append(ProbeTarget(
            target_type="node",
            target_id=m.node_id,
            description=m.description,
            importance=m.composite_importance,
            centrality_rank=m._rank,
            on_critical_path=m.path_relevance > 0,
            probe_type="node_strengthen",
        ))

    # --- Edge targets ---

    # Sort edges: critical-path first, then by betweenness
    critical_edges = sorted(
        [e for e in edge_metrics if e.on_critical_path],
        key=lambda e: e.edge_betweenness,
        reverse=True,
    )
    peripheral_edges = sorted(
        [e for e in edge_metrics if not e.on_critical_path],
        key=lambda e: e.edge_betweenness,
        reverse=True,
    )

    # 2 critical-path edge negations
    for i, e in enumerate(critical_edges[:2]):
        targets.append(ProbeTarget(
            target_type="edge",
            target_id=f"{e.source}->{e.target}",
            description=e.mechanism,
            importance=e.edge_betweenness,
            centrality_rank=i + 1,
            on_critical_path=True,
            probe_type="edge_negate_critical",
        ))

    # 1 peripheral edge negation
    if peripheral_edges:
        e = peripheral_edges[0]
        targets.append(ProbeTarget(
            target_type="edge",
            target_id=f"{e.source}->{e.target}",
            description=e.mechanism,
            importance=e.edge_betweenness,
            centrality_rank=len(critical_edges) + 1,
            on_critical_path=False,
            probe_type="edge_negate_peripheral",
        ))
    elif len(critical_edges) > 2:
        # Fallback: use least-important critical edge as peripheral
        e = critical_edges[-1]
        targets.append(ProbeTarget(
            target_type="edge",
            target_id=f"{e.source}->{e.target}",
            description=e.mechanism,
            importance=e.edge_betweenness,
            centrality_rank=len(critical_edges),
            on_critical_path=True,
            probe_type="edge_negate_peripheral",
        ))

    # 1 critical-path edge reversal
    if critical_edges:
        e = critical_edges[0]
        targets.append(ProbeTarget(
            target_type="edge",
            target_id=f"{e.source}->{e.target}",
            description=e.mechanism,
            importance=e.edge_betweenness,
            centrality_rank=1,
            on_critical_path=True,
            probe_type="edge_reverse",
        ))

    # --- Missing-edge targets ---

    # Find plausible missing edges: node pairs not directly connected
    # but both adjacent to the outcome
    outcome_predecessors = set(G.predecessors(outcome_node))
    missing_candidates = []

    for u in outcome_predecessors:
        for v in outcome_predecessors:
            if u != v and not G.has_edge(u, v) and not G.has_edge(v, u):
                missing_candidates.append((u, v))

    # If not enough from outcome neighbors, expand to all non-connected factor pairs
    if len(missing_candidates) < 2:
        factor_ids = {m.node_id for m in factor_metrics}
        for u in factor_ids:
            for v in factor_ids:
                if u != v and not G.has_edge(u, v) and (u, v) not in missing_candidates:
                    missing_candidates.append((u, v))

    # Deduplicate (keep only one direction per pair)
    seen_pairs = set()
    deduped = []
    for u, v in missing_candidates:
        pair = tuple(sorted([u, v]))
        if pair not in seen_pairs:
            seen_pairs.add(pair)
            deduped.append((u, v))
    missing_candidates = deduped

    for u, v in missing_candidates[:2]:
        u_desc = G.nodes[u].get("description", u)
        v_desc = G.nodes[v].get("description", v)
        targets.append(ProbeTarget(
            target_type="missing_edge",
            target_id=f"{u}->{v}",
            description=f"Potential link: {u_desc} -> {v_desc}",
            importance=0.0,
            centrality_rank=0,
            on_critical_path=False,
            probe_type="edge_fabricate",
        ))

    # --- Structural targets (LLM-generated) ---

    # 2 missing-node probes
    targets.append(ProbeTarget(
        target_type="structural",
        target_id="missing_node_1",
        description="A plausible factor not in the current network",
        importance=0.0,
        centrality_rank=0,
        on_critical_path=False,
        probe_type="missing_node",
    ))
    targets.append(ProbeTarget(
        target_type="structural",
        target_id="missing_node_2",
        description="Another plausible missing factor",
        importance=0.0,
        centrality_rank=0,
        on_critical_path=False,
        probe_type="missing_node",
    ))

    # 2 irrelevant probes
    targets.append(ProbeTarget(
        target_type="structural",
        target_id="irrelevant_1",
        description="Topically related but causally irrelevant information",
        importance=0.0,
        centrality_rank=0,
        on_critical_path=False,
        probe_type="irrelevant",
    ))
    targets.append(ProbeTarget(
        target_type="structural",
        target_id="irrelevant_2",
        description="Another topically related but irrelevant piece of information",
        importance=0.0,
        centrality_rank=0,
        on_critical_path=False,
        probe_type="irrelevant",
    ))

    return targets


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def analyze_network(
    nodes: list[dict],
    edges: list[dict],
) -> NetworkAnalysis:
    """Build graph and compute all metrics + probe targets.

    Parameters
    ----------
    nodes : list[dict]
        LLM-elicited nodes: [{"id": str, "description": str, "role": str}, ...].
    edges : list[dict]
        LLM-elicited edges: [{"from": str, "to": str, "mechanism": str}, ...].

    Returns
    -------
    NetworkAnalysis with graph-level metrics, per-node metrics, per-edge metrics,
    and selected probe targets.
    """
    G = _build_digraph(nodes, edges)

    # Identify outcome node
    outcome_nodes = [n for n in G.nodes if G.nodes[n].get("role") == "outcome"]
    outcome_node = outcome_nodes[0] if outcome_nodes else ""

    # Graph-level metrics
    analysis = NetworkAnalysis()
    analysis.n_nodes = G.number_of_nodes()
    analysis.n_edges = G.number_of_edges()
    analysis.density = nx.density(G)
    analysis.is_dag = nx.is_directed_acyclic_graph(G)
    analysis.n_weakly_connected = nx.number_weakly_connected_components(G)
    analysis.n_strongly_connected = nx.number_strongly_connected_components(G)
    analysis.outcome_node = outcome_node

    # Per-node metrics
    node_metrics = _compute_node_metrics(G, outcome_node)
    node_metrics = _compute_composite_importance(node_metrics)
    analysis.node_metrics = node_metrics

    # Per-edge metrics
    edge_metrics = _compute_edge_metrics(G, outcome_node)
    analysis.edge_metrics = edge_metrics

    # Probe target selection
    analysis.probe_targets = _select_probe_targets(
        node_metrics, edge_metrics, G, outcome_node,
    )

    return analysis
