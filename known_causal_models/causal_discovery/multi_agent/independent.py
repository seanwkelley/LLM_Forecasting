"""
Independent communication structure — N agents run in parallel with no
communication, then vote to merge their declared graphs.
"""

from __future__ import annotations

import json
from pathlib import Path

from causal_discovery.multi_agent.agent import (
    AgentResult, run_single_agent, setup_domain,
)
from causal_discovery.multi_agent.aggregation import (
    majority_vote, confidence_weighted_vote, union_merge,
)
from causal_discovery.multi_agent.config import get_causal_personas, get_expertise_personas
from causal_discovery.multi_agent.prompts_multi import build_persona_system_prompt


def _build_shared_context(prior_agents: list[AgentResult]) -> str:
    """Format prior agents' findings as context for the next agent."""
    if not prior_agents:
        return ""
    lines = ["PRIOR AGENTS' FINDINGS:", ""]
    for r in prior_agents:
        valid = [i for i in r.all_interventions
                 if "SKIPPED" not in i.get("result_summary", "")]
        lines.append(f"Agent '{r.agent_id}' ran {len(valid)} interventions:")
        for inv_record in r.all_interventions:
            summary = inv_record.get("result_summary", "")
            if "SKIPPED" in summary:
                continue
            desc = inv_record.get("intervention", {}).get("description", "")
            lines.append(f"  - {desc}")
            lines.append(f"    Result: {summary}")
        lines.append("")
    lines.append("Build on these findings. Do not repeat their interventions.")
    return "\n".join(lines)


def run_independent(
    domain: str,
    budget: int = 30,
    n_agents: int = 5,
    n_warmup: int = 10,
    seed: int = 42,
    api_key: str = "",
    model: str = "meta-llama/llama-3.3-70b-instruct",
    dry_run: bool = False,
    output_dir: str = "",
    verbose: bool = True,
    persona_set: str = "reasoning",
    sequential: bool = False,
) -> dict:
    """Run N independent agents with equal budget splits, then aggregate.

    Parameters
    ----------
    domain : str
        "market" or "conflict".
    budget : int
        Total intervention budget (split equally among agents).
    n_agents : int
        Number of independent agents.
    persona_set : str
        "reasoning" for the original 5 causal personas, or "expertise" for
        the 3 soft expertise personas (systems_engineer, economist, experimentalist).
    sequential : bool
        If True, agents run sequentially — each sees prior agents' intervention
        results via shared_results and context_injection.

    Returns
    -------
    dict with keys: scores (per aggregation method), agent_results, config.
    """
    if persona_set == "expertise":
        personas = get_expertise_personas()[:n_agents]
    else:
        personas = get_causal_personas()[:n_agents]
    per_agent_budget = budget // n_agents

    mode = "Sequential" if sequential else "Independent"
    if verbose:
        print("=" * 60)
        print(f"MULTI-AGENT CAUSAL DISCOVERY — {mode}")
        print(f"Domain: {domain} | Agents: {len(personas)} | Budget: {budget} "
              f"({per_agent_budget}/agent) | Personas: {persona_set}")
        print(f"Model: {'DRY RUN' if dry_run else model}")
        print("=" * 60)

    # Setup domain once
    if verbose:
        print(f"\nPhase 0: Setting up {domain} domain...")
    ds = setup_domain(domain, n_warmup=n_warmup, seed=seed, budget=budget)

    # Run each agent (sequentially in all cases for API rate limits)
    agent_results: list[AgentResult] = []
    accumulated_results = []   # InterventionResult objects for sequential dedup
    accumulated_agents = []    # AgentResult objects for sequential context
    total_llm_calls = 0

    for i, persona in enumerate(personas):
        if verbose:
            print(f"\n{'-' * 40}")
            print(f"Agent {i+1}/{len(personas)}: {persona['name']}")
            print(f"{'-' * 40}")

        context = _build_shared_context(accumulated_agents) if sequential else ""
        shared = accumulated_results if sequential else None

        result = run_single_agent(
            domain_setup=ds,
            agent_id=persona["id"],
            budget=per_agent_budget,
            api_key=api_key,
            model=model,
            persona_prompt=persona["prompt"],
            shared_results=shared,
            context_injection=context,
            dry_run=dry_run,
            verbose=verbose,
        )
        accumulated_results.extend(result.all_results)
        accumulated_agents.append(result)
        agent_results.append(result)
        total_llm_calls += result.llm_calls

    # Aggregate
    if verbose:
        print(f"\n{'=' * 40}")
        print("Aggregating results...")

    variables = ds["variables"]
    score_fn = ds["score_fn"]

    aggregations = {
        "majority_vote": majority_vote(agent_results, variables),
        "confidence_weighted": confidence_weighted_vote(agent_results, variables),
        "union": union_merge(agent_results, variables),
    }

    scores = {}
    for method_name, matrix in aggregations.items():
        s = score_fn(matrix)
        scores[method_name] = {k: v for k, v in s.items() if k != "per_edge"}
        scores[method_name]["per_edge"] = s["per_edge"]
        if verbose:
            print(f"  {method_name}: F1={s['f1']:.3f} "
                  f"(P={s['precision']:.3f}, R={s['recall']:.3f})")

    # Per-agent individual scores
    from causal_discovery.ground_truth import edges_to_matrix
    for r in agent_results:
        m = edges_to_matrix(r.declared_edges, variables)
        s = score_fn(m)
        scores[f"agent_{r.agent_id}"] = {k: v for k, v in s.items() if k != "per_edge"}
        if verbose:
            print(f"  agent_{r.agent_id}: F1={s['f1']:.3f}")

    if verbose:
        print(f"\nTotal LLM calls: {total_llm_calls}")

    # Save results
    output = {
        "config": {
            "communication": "sequential" if sequential else "independent",
            "domain": domain,
            "budget": budget,
            "n_agents": len(personas),
            "per_agent_budget": per_agent_budget,
            "persona_set": persona_set,
            "sequential": sequential,
            "model": model if not dry_run else "dry_run",
            "seed": seed,
        },
        "scores": {k: {kk: vv for kk, vv in v.items() if kk != "per_edge"}
                   for k, v in scores.items()},
        "total_llm_calls": total_llm_calls,
        "per_agent": [
            {
                "agent_id": r.agent_id,
                "n_edges": len(r.declared_edges),
                "llm_calls": r.llm_calls,
                "n_interventions": len([i for i in r.all_interventions
                                        if "SKIPPED" not in i.get("result_summary", "")
                                        and "INVALID" not in i.get("result_summary", "")]),
            }
            for r in agent_results
        ],
    }

    if output_dir:
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        with open(out_path / "results.json", "w") as f:
            json.dump(output, f, indent=2, default=str)

        # Save per-agent details
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

        # Save conversation logs
        conv_dir = out_path / "conversation_logs"
        conv_dir.mkdir(exist_ok=True)
        for r in agent_results:
            with open(conv_dir / f"{r.agent_id}_conversation.json", "w") as f:
                json.dump(r.conversation, f, indent=2, default=str)

        if verbose:
            print(f"\nResults saved to: {out_path}")

    return {"scores": scores, "agent_results": agent_results, "config": output["config"]}
