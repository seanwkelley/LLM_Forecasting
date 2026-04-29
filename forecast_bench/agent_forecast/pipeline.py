"""Four-condition pipeline: no_search, untargeted, topology_targeted,
peripheral_targeted.

All four start from the same Stage 1 DAG + p0 (the paper's elicitation).
They differ in how evidence is gathered before producing p1.

Budgets (MAX_SEARCH_QUERIES, MAX_RESULTS_PER_QUERY) are held equal across
search conditions.  peripheral_targeted mirrors topology_targeted exactly but
targets the bottom-k factors by betweenness rather than the top-k.  This
isolates centrality from the decomposition-of-search effect: if topology
beats peripheral, centrality is load-bearing; if they tie, decomposition
alone was the operative mechanism.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Literal

from forecast_bench.llm_client import LLMClient
from forecast_bench.network_analysis import analyze_network
from forecast_bench.prompts_causal import (
    CAUSAL_FORECAST_SYSTEM, build_causal_forecast_prompt,
)
from forecast_bench.agent_forecast.config import (
    MAX_SEARCH_QUERIES, QUERIES_PER_FACTOR, TOP_K_FACTORS,
)
from forecast_bench.agent_forecast.search_tool import SearchTool


Condition = Literal["no_search", "untargeted",
                     "topology_targeted", "peripheral_targeted"]


@dataclass
class TrialResult:
    question_id: str
    question_text: str
    model: str
    condition: Condition
    p0: float | None = None
    dag: dict | None = None
    search_queries: list[dict] = field(default_factory=list)
    p1: float | None = None
    p1_reasoning: str = ""
    error: str | None = None

    def to_dict(self):
        return asdict(self)


# ── Stage 1: DAG elicitation (same as paper) ──────────────────────────────

def elicit_dag(client: LLMClient, question_text: str,
               max_retries: int = 3) -> dict | None:
    """Reuses the paper's Stage 1 causal-forecast prompt and validation."""
    user_prompt = build_causal_forecast_prompt(question_text)
    for attempt in range(max_retries + 1):
        text, ok = client.call_single(CAUSAL_FORECAST_SYSTEM, user_prompt)
        if not ok:
            client.rate_limit_wait()
            continue
        try:
            data = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            continue
        if not _validate_dag(data):
            continue
        data["probability"] = max(0.01, min(0.99, float(data["probability"])))
        return data
    return None


def _validate_dag(data: dict) -> bool:
    if not isinstance(data, dict):
        return False
    if data.get("probability") is None:
        return False
    nodes = data.get("nodes", [])
    edges = data.get("edges", [])
    if not isinstance(nodes, list) or not isinstance(edges, list):
        return False
    node_ids = {n.get("id") for n in nodes if isinstance(n, dict)}
    outcomes = [n for n in nodes if isinstance(n, dict) and n.get("role") == "outcome"]
    if len(outcomes) != 1:
        return False
    for e in edges:
        if not isinstance(e, dict):
            return False
        if e.get("from") not in node_ids or e.get("to") not in node_ids:
            return False
    return bool(edges)


# ── Stage 2: Topology analysis (reuses network_analysis module) ────────────

def _factors_by_betweenness(nodes: list[dict], edges: list[dict],
                             k: int, select: str) -> list[dict]:
    """Return k factor nodes ranked by betweenness.

    select="top" returns the k highest-betweenness factors;
    select="bottom" returns the k lowest.
    """
    analysis = analyze_network(nodes, edges)
    factor_metrics = [m for m in analysis.node_metrics
                      if m.role == "factor"]
    reverse = (select == "top")
    factor_metrics.sort(key=lambda m: m.betweenness, reverse=reverse)
    chosen = factor_metrics[:k]
    desc = {n["id"]: n.get("description", "") for n in nodes}
    return [{"id": m.node_id, "description": desc.get(m.node_id, ""),
             "betweenness": m.betweenness} for m in chosen]


def top_k_factors_by_betweenness(nodes: list[dict], edges: list[dict],
                                  k: int = TOP_K_FACTORS) -> list[dict]:
    """Return the top-k factor nodes by betweenness centrality."""
    return _factors_by_betweenness(nodes, edges, k, select="top")


def bottom_k_factors_by_betweenness(nodes: list[dict], edges: list[dict],
                                     k: int = TOP_K_FACTORS) -> list[dict]:
    """Return the bottom-k factor nodes by betweenness centrality.

    Used by the peripheral_targeted condition as the decomposition control
    for topology_targeted.
    """
    return _factors_by_betweenness(nodes, edges, k, select="bottom")


# ── Stage 3: Condition-specific evidence gathering ─────────────────────────

EVIDENCE_SEARCH_SYSTEM = (
    "You are a research agent gathering evidence to update a forecast. "
    "Given a forecasting question and optionally a specific causal factor, "
    "generate ONE concise web-search query likely to surface current, "
    "pre-resolution evidence. Respond with ONLY the query text (no quotes, "
    "no explanation, under 12 words)."
)


def _generate_search_query(client: LLMClient, question: str,
                           target_factor: dict | None = None,
                           prior_queries: list[str] | None = None) -> str:
    user = f"Forecasting question: {question}\n"
    if target_factor:
        user += (f"\nFocus your query on this causal factor: "
                 f"'{target_factor['id']}' — {target_factor['description']}\n")
    if prior_queries:
        user += "\nAvoid repeating prior queries: " + "; ".join(prior_queries[-4:])
    user += "\n\nReturn just the search query text."
    text, ok = client.call_single(EVIDENCE_SEARCH_SYSTEM, user, json_mode=False)
    if not ok or not text:
        return question  # fallback: search the question itself
    return text.strip().strip('"').strip("'")[:200]


def gather_untargeted(client: LLMClient, search: SearchTool,
                      question: str) -> list[dict]:
    """Free-form search on the question with budget MAX_SEARCH_QUERIES."""
    queries = []
    history = []
    for i in range(MAX_SEARCH_QUERIES):
        q = _generate_search_query(client, question, prior_queries=history)
        history.append(q)
        call = search.search(q)
        queries.append({
            "query": q, "targeted_factor": None,
            "results": call.results, "tool": call.tool,
        })
    return queries


def gather_factor_targeted(client: LLMClient, search: SearchTool,
                            question: str, factors: list[dict]) -> list[dict]:
    """Focus search on a supplied list of factor nodes.

    Used by both topology_targeted (top-k by betweenness) and
    peripheral_targeted (bottom-k) conditions; the caller chooses which
    factors to pass in so the two conditions are structurally identical
    except for factor selection.

    Budget: len(factors) * QUERIES_PER_FACTOR queries, up to
    MAX_SEARCH_QUERIES total.
    """
    queries = []
    history = []
    total_budget = min(MAX_SEARCH_QUERIES, len(factors) * QUERIES_PER_FACTOR)
    per_factor = max(1, total_budget // max(len(factors), 1))
    for factor in factors:
        for _ in range(per_factor):
            if len(queries) >= total_budget:
                break
            q = _generate_search_query(client, question, target_factor=factor,
                                       prior_queries=history)
            history.append(q)
            call = search.search(q)
            queries.append({
                "query": q, "targeted_factor": factor["id"],
                "results": call.results, "tool": call.tool,
            })
    return queries


# Kept for backward compatibility with any external callers.
gather_topology_targeted = gather_factor_targeted


# ── Stage 4: Evidence integration → p1 ─────────────────────────────────────

EVIDENCE_UPDATE_SYSTEM = (
    "You are an expert forecaster updating a probability estimate in light "
    "of new evidence. Integrate the evidence with your existing causal model "
    "and produce a revised probability.\n\n"
    "Respond with ONLY valid JSON: "
    '{"updated_probability": <float 0.01-0.99>, '
    '"reasoning": "<2-4 sentences>"}'
)


def _format_evidence(queries: list[dict]) -> str:
    lines = []
    for qi, q in enumerate(queries, 1):
        tag = f"[Q{qi}]"
        if q.get("targeted_factor"):
            tag += f" (factor: {q['targeted_factor']})"
        lines.append(f"{tag} Search: {q['query']}")
        for r in q.get("results", [])[:3]:
            title = r.get("title", "")
            snip = r.get("snippet", "")
            pub = r.get("published", "")
            lines.append(f"  - {title} ({pub}): {snip}")
    return "\n".join(lines) if lines else "(no evidence gathered)"


def integrate_evidence(client: LLMClient, question: str, p0: float,
                       dag: dict, queries: list[dict]) -> tuple[float, str]:
    user = (
        f"Forecasting question: {question}\n"
        f"Your initial probability estimate: {p0:.3f}\n\n"
        f"Your causal network factors:\n"
        + "\n".join(f"  - {n['id']}: {n.get('description','')}"
                    for n in dag["nodes"] if n.get("role") != "outcome")
        + "\n\nEvidence gathered from web search:\n"
        + _format_evidence(queries)
        + "\n\nGiven this evidence, produce your updated probability."
    )
    text, ok = client.call_single(EVIDENCE_UPDATE_SYSTEM, user)
    if not ok or not text:
        return p0, "(evidence integration failed)"
    try:
        data = json.loads(text)
        p1 = max(0.01, min(0.99, float(data["updated_probability"])))
        return p1, data.get("reasoning", "")
    except (json.JSONDecodeError, KeyError, ValueError):
        return p0, "(parse error)"


# ── Top-level entry point ─────────────────────────────────────────────────

def run_trial(question: dict, model_id: str, model_name: str,
              condition: Condition, client: LLMClient,
              search: SearchTool | None = None) -> TrialResult:
    """Run one question × model × condition trial and return the result."""
    result = TrialResult(
        question_id=question["id"],
        question_text=question["question"],
        model=model_name,
        condition=condition,
    )

    # Stage 1: DAG + p0 (all conditions share this)
    dag = elicit_dag(client, question["question"])
    if dag is None:
        result.error = "dag_elicitation_failed"
        return result
    result.dag = dag
    result.p0 = dag["probability"]

    if condition == "no_search":
        result.p1 = result.p0
        result.p1_reasoning = "(no search; p1 = p0)"
        return result

    if search is None:
        result.error = "search_tool_not_provided"
        return result

    # Stage 2 + 3: gather evidence
    if condition == "untargeted":
        queries = gather_untargeted(client, search, question["question"])
    elif condition == "topology_targeted":
        factors = top_k_factors_by_betweenness(dag["nodes"], dag["edges"])
        queries = gather_factor_targeted(client, search,
                                          question["question"], factors)
    elif condition == "peripheral_targeted":
        factors = bottom_k_factors_by_betweenness(dag["nodes"], dag["edges"])
        queries = gather_factor_targeted(client, search,
                                          question["question"], factors)
    else:
        result.error = f"unknown_condition:{condition}"
        return result
    result.search_queries = queries

    # Stage 4: update p0 -> p1 using gathered evidence
    p1, reasoning = integrate_evidence(client, question["question"],
                                        result.p0, dag, queries)
    result.p1 = p1
    result.p1_reasoning = reasoning
    return result
