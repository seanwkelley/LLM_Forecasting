"""
Specialization communication structure — 3 specialist agents each responsible
for a variable subgraph, plus 1 LLM aggregator that merges their findings.
"""

from __future__ import annotations

import json
from pathlib import Path

from causal_discovery.multi_agent.agent import (
    AgentResult, run_single_agent, setup_domain,
    call_llm, parse_json_response, mock_llm_response,
)
from causal_discovery.multi_agent.aggregation import union_merge
from causal_discovery.multi_agent.config import get_subgraphs
from causal_discovery.multi_agent.prompts_multi import (
    build_specialist_system_prompt, build_aggregator_prompt,
)
from causal_discovery.ground_truth import edges_to_matrix


def _allocate_budgets(subgraphs: dict, total_budget: int) -> dict:
    """Allocate budget proportional to subgraph size.

    Returns dict mapping subgraph name to budget.
    """
    total_vars = sum(len(sg["variables"]) for sg in subgraphs.values())
    budgets = {}
    allocated = 0
    names = list(subgraphs.keys())
    for i, name in enumerate(names):
        n_vars = len(subgraphs[name]["variables"])
        if i == len(names) - 1:
            # Last one gets remainder
            budgets[name] = total_budget - allocated
        else:
            b = round(total_budget * n_vars / total_vars)
            b = max(b, 2)  # minimum 2 interventions per specialist
            budgets[name] = b
            allocated += b
    return budgets


def run_specialization(
    domain: str,
    budget: int = 30,
    n_warmup: int = 10,
    seed: int = 42,
    api_key: str = "",
    model: str = "meta-llama/llama-3.3-70b-instruct",
    dry_run: bool = False,
    output_dir: str = "",
    verbose: bool = True,
) -> dict:
    """Run 3 specialists + 1 LLM aggregator.

    Each specialist runs run_single_agent() with allowed_variables set to their
    subgraph. The aggregator LLM sees all specialists' declarations + evidence
    summaries and produces a unified graph.

    Returns
    -------
    dict with keys: scores, agent_results, config.
    """
    subgraphs = get_subgraphs(domain)
    budgets = _allocate_budgets(subgraphs, budget)

    if verbose:
        print("=" * 60)
        print(f"MULTI-AGENT CAUSAL DISCOVERY — Specialization")
        print(f"Domain: {domain} | Budget: {budget}")
        for name, b in budgets.items():
            print(f"  {name}: {b} interventions ({', '.join(subgraphs[name]['variables'])})")
        print(f"Model: {'DRY RUN' if dry_run else model}")
        print("=" * 60)

    # Setup domain once
    if verbose:
        print(f"\nPhase 0: Setting up {domain} domain...")
    ds = setup_domain(domain, n_warmup=n_warmup, seed=seed, budget=budget)

    # Run each specialist
    agent_results: list[AgentResult] = []
    total_llm_calls = 0

    for name, sg in subgraphs.items():
        agent_budget = budgets[name]
        if verbose:
            print(f"\n{'-' * 40}")
            print(f"Specialist: {name} (budget={agent_budget})")
            print(f"Variables: {', '.join(sg['variables'])}")
            print(f"{'-' * 40}")

        result = run_single_agent(
            domain_setup=ds,
            agent_id=f"specialist_{name}",
            budget=agent_budget,
            api_key=api_key,
            model=model,
            persona_prompt=sg["prompt"],
            allowed_variables=sg["variables"],
            dry_run=dry_run,
            verbose=verbose,
        )
        agent_results.append(result)
        total_llm_calls += result.llm_calls

    # LLM Aggregator
    if verbose:
        print(f"\n{'=' * 40}")
        print("Running LLM aggregator...")

    variables = ds["variables"]
    score_fn = ds["score_fn"]

    aggregator_prompt = build_aggregator_prompt(agent_results, variables, domain)

    if dry_run:
        aggregator_declaration = mock_llm_response("declaration", 0, domain)
        aggregator_raw = json.dumps(aggregator_declaration)
    else:
        aggregator_messages = [
            {"role": "system", "content": ds["system_prompt"]},
            {"role": "user", "content": aggregator_prompt},
        ]
        aggregator_raw = call_llm(
            aggregator_messages, api_key, model, max_tokens=4000
        )
        aggregator_declaration = parse_json_response(aggregator_raw)
        total_llm_calls += 1

    # Parse aggregator edges
    final_edges = aggregator_declaration.get("final_graph", [])
    aggregator_edge_pairs = [
        (e["from"], e["to"]) for e in final_edges
        if e.get("confidence") in ("high", "medium", "low")
    ]
    aggregator_matrix = edges_to_matrix(aggregator_edge_pairs, variables)

    # Also compute union merge as non-LLM fallback
    union_matrix = union_merge(agent_results, variables)

    # Score
    scores = {}

    s = score_fn(aggregator_matrix)
    scores["llm_aggregator"] = {k: v for k, v in s.items() if k != "per_edge"}
    scores["llm_aggregator"]["per_edge"] = s["per_edge"]
    if verbose:
        print(f"  LLM aggregator: F1={s['f1']:.3f} "
              f"(P={s['precision']:.3f}, R={s['recall']:.3f})")

    s = score_fn(union_matrix)
    scores["union_fallback"] = {k: v for k, v in s.items() if k != "per_edge"}
    scores["union_fallback"]["per_edge"] = s["per_edge"]
    if verbose:
        print(f"  Union fallback: F1={s['f1']:.3f} "
              f"(P={s['precision']:.3f}, R={s['recall']:.3f})")

    # Per-specialist individual scores
    for r in agent_results:
        m = edges_to_matrix(r.declared_edges, variables)
        s = score_fn(m)
        scores[r.agent_id] = {k: v for k, v in s.items() if k != "per_edge"}
        if verbose:
            print(f"  {r.agent_id}: F1={s['f1']:.3f}")

    if verbose:
        print(f"\nTotal LLM calls: {total_llm_calls}")

    # Save results
    output = {
        "config": {
            "communication": "specialization",
            "domain": domain,
            "budget": budget,
            "budgets": budgets,
            "model": model if not dry_run else "dry_run",
            "seed": seed,
        },
        "scores": {k: {kk: vv for kk, vv in v.items() if kk != "per_edge"}
                   for k, v in scores.items()},
        "aggregator_declaration": aggregator_declaration,
        "total_llm_calls": total_llm_calls,
        "per_agent": [
            {
                "agent_id": r.agent_id,
                "n_edges": len(r.declared_edges),
                "llm_calls": r.llm_calls,
            }
            for r in agent_results
        ],
    }

    if output_dir:
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        with open(out_path / "results.json", "w") as f:
            json.dump(output, f, indent=2, default=str)

        per_agent_dir = out_path / "per_agent"
        per_agent_dir.mkdir(exist_ok=True)
        for r in agent_results:
            agent_data = {
                "agent_id": r.agent_id,
                "declared_edges": [list(e) for e in r.declared_edges],
                "declaration": r.declaration_raw,
                "interventions": r.all_interventions,
                "llm_calls": r.llm_calls,
            }
            with open(per_agent_dir / f"{r.agent_id}.json", "w") as f:
                json.dump(agent_data, f, indent=2, default=str)

        conv_dir = out_path / "conversation_logs"
        conv_dir.mkdir(exist_ok=True)
        for r in agent_results:
            with open(conv_dir / f"{r.agent_id}_conversation.json", "w") as f:
                json.dump(r.conversation, f, indent=2, default=str)

        if verbose:
            print(f"\nResults saved to: {out_path}")

    return {"scores": scores, "agent_results": agent_results, "config": output["config"]}
