"""
Debate communication structure — 2 agents alternate interventions from a shared
budget pool, sharing results and debating hypotheses.
"""

from __future__ import annotations

import json
from pathlib import Path

from causal_discovery.multi_agent.agent import (
    AgentResult,
    call_llm, parse_json_response, mock_llm_response,
    setup_domain,
    _extract_latest_hypothesis, _build_intervention_summary, _summarize_effect,
)
from causal_discovery.multi_agent.aggregation import union_merge, majority_vote
from causal_discovery.multi_agent.config import get_debate_pair
from causal_discovery.multi_agent.prompts_multi import build_debate_injection
from causal_discovery.ground_truth import edges_to_matrix


def run_debate(
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
    """Run 2 agents that alternate interventions from a shared budget.

    Flow:
    1. Both agents observe warmup independently
    2. Interleaved intervention loop (budget steps total):
       - Even steps: Agent A proposes (sees Agent B's latest hypothesis)
       - Odd steps: Agent B proposes (sees Agent A's latest hypothesis)
       - Both agents see all intervention results
    3. Each agent declares independently
    4. Merge with union (primary) and majority_vote (secondary)

    Returns
    -------
    dict with keys: scores, agent_results, config.
    """
    from causal_discovery.intervention import (
        Intervention, run_market_intervention, run_conflict_intervention,
        format_result_for_agent,
    )
    from causal_discovery.prompts import (
        build_observation_prompt, build_intervention_prompt,
        build_declaration_prompt, build_evidence_summary,
    )

    pair = get_debate_pair()
    agent_a, agent_b = pair

    if verbose:
        print("=" * 60)
        print(f"MULTI-AGENT CAUSAL DISCOVERY — Debate")
        print(f"Domain: {domain} | Budget: {budget} (shared)")
        print(f"Agent A: {agent_a['name']} | Agent B: {agent_b['name']}")
        print(f"Model: {'DRY RUN' if dry_run else model}")
        print("=" * 60)

    # Setup
    if verbose:
        print(f"\nPhase 0: Setting up {domain} domain...")
    ds = setup_domain(domain, n_warmup=n_warmup, seed=seed, budget=budget)

    variables = ds["variables"]
    system_prompt = ds["system_prompt"]
    intervention_types = ds["intervention_types"]
    score_fn = ds["score_fn"]

    # Initialize both conversations with persona-injected system prompts
    sys_a = f"ROLE: {agent_a['name']}\n{agent_a['prompt']}\n\n{system_prompt}"
    sys_b = f"ROLE: {agent_b['name']}\n{agent_b['prompt']}\n\n{system_prompt}"

    conv_a = [{"role": "system", "content": sys_a}]
    conv_b = [{"role": "system", "content": sys_b}]

    # Phase 1: Both observe independently
    if verbose:
        print(f"\nPhase 1: Both agents observe...")

    observation_prompt = build_observation_prompt(
        domain=domain,
        history_summary=ds["history_summary"],
        variables=variables,
    )

    llm_calls = 0

    # Agent A observes
    conv_a.append({"role": "user", "content": observation_prompt})
    if dry_run:
        obs_a = mock_llm_response("observation", 0, domain)
        obs_a_raw = json.dumps(obs_a)
    else:
        obs_a_raw = call_llm(conv_a, api_key, model)
        obs_a = parse_json_response(obs_a_raw)
        llm_calls += 1
    conv_a.append({"role": "assistant", "content": obs_a_raw})

    # Agent B observes
    conv_b.append({"role": "user", "content": observation_prompt})
    if dry_run:
        obs_b = mock_llm_response("observation", 0, domain)
        obs_b_raw = json.dumps(obs_b)
    else:
        obs_b_raw = call_llm(conv_b, api_key, model)
        obs_b = parse_json_response(obs_b_raw)
        llm_calls += 1
    conv_b.append({"role": "assistant", "content": obs_b_raw})

    if verbose:
        print(f"  Agent A: {len(obs_a.get('confident_edges', []))} confident edges")
        print(f"  Agent B: {len(obs_b.get('confident_edges', []))} confident edges")

    # Phase 2: Interleaved interventions
    all_interventions_a = []
    all_interventions_b = []
    all_results = []  # shared pool
    all_intervention_keys = set()  # global dedup

    hypothesis_a = "Initial observation — see above."
    hypothesis_b = "Initial observation — see above."
    last_intervention_a = ""
    last_result_a = ""
    last_intervention_b = ""
    last_result_b = ""

    for step in range(budget):
        # Alternate: even=A, odd=B
        is_agent_a = (step % 2 == 0)
        current_agent = agent_a if is_agent_a else agent_b
        current_conv = conv_a if is_agent_a else conv_b
        current_interventions = all_interventions_a if is_agent_a else all_interventions_b
        other_agent = agent_b if is_agent_a else agent_a

        if verbose:
            print(f"\nStep {step+1}/{budget} [{current_agent['name']}]:")

        # Build debate injection from the other agent
        if is_agent_a:
            debate_ctx = build_debate_injection(
                agent_b["name"], hypothesis_b,
                last_intervention_b, last_result_b,
            )
        else:
            debate_ctx = build_debate_injection(
                agent_a["name"], hypothesis_a,
                last_intervention_a, last_result_a,
            )

        # Build intervention prompt
        int_prompt = build_intervention_prompt(
            domain=domain,
            variables=variables,
            current_hypothesis="(see your previous messages above)",
            past_interventions="(see your previous messages above)",
            budget_remaining=budget - step,
            intervention_types=intervention_types,
        )
        int_prompt += f"\n\n{debate_ctx}"

        current_conv.append({"role": "user", "content": int_prompt})

        if dry_run:
            proposal = mock_llm_response("intervention", step, domain)
            proposal_raw = json.dumps(proposal)
        else:
            proposal_raw = call_llm(current_conv, api_key, model)
            proposal = parse_json_response(proposal_raw)
            llm_calls += 1

        current_conv.append({"role": "assistant", "content": proposal_raw})

        # Parse intervention spec
        int_spec = proposal.get("intervention", proposal)
        target = int_spec.get("target", {})
        int_type = int_spec.get("type", "event")

        # Reject invalid types
        if int_type not in ("action", "trait", "event"):
            if verbose:
                print(f"  [INVALID] Type '{int_type}'")
            reject_msg = (
                f"'{int_type}' is not a valid intervention type. "
                f"You MUST use one of: action, trait, event."
            )
            current_conv.append({"role": "user", "content": reject_msg})
            current_conv.append({"role": "assistant", "content": json.dumps(
                {"acknowledged": "Will propose a valid intervention."})})
            current_interventions.append({
                "step": step + 1,
                "agent_id": current_agent["id"],
                "intervention": {"type": int_type, "target": target,
                                 "description": int_spec.get("description", "")},
                "result_summary": f"INVALID TYPE ({int_type})",
                "hypothesis_update": {},
            })
            continue

        # Normalize event targets
        if int_type == "event" and "shock_type" not in target:
            for alt_key in ("event", "shock", "type", "event_type"):
                if alt_key in target:
                    target["shock_type"] = target.pop(alt_key)
                    break

        # Normalize action targets
        if int_type == "action" and "value" not in target:
            for alt_key in ("action", "recommendation", "action_name"):
                if alt_key in target:
                    target["value"] = target.pop(alt_key)
                    break

        if int_type == "action" and "agent_id" not in target:
            for alt_key in ("agent", "agent_name"):
                if alt_key in target:
                    target["agent_id"] = target.pop(alt_key)
                    break

        intervention = Intervention(
            type=int_type,
            target=target,
            run_periods=int_spec.get("run_periods", 3),
            description=int_spec.get("description", f"Intervention {step+1}"),
        )

        # Global dedup
        dedup_key = (int_type, json.dumps(target, sort_keys=True))
        if dedup_key in all_intervention_keys:
            if verbose:
                print(f"  [SKIPPED] Duplicate (already tested by either agent)")
            skip_msg = (
                f"This intervention was already run by one of the agents (duplicate). "
                f"Please propose a DIFFERENT intervention."
            )
            current_conv.append({"role": "user", "content": skip_msg})
            current_conv.append({"role": "assistant", "content": json.dumps(
                {"acknowledged": "Will propose a different intervention."})})
            current_interventions.append({
                "step": step + 1,
                "agent_id": current_agent["id"],
                "intervention": {
                    "type": intervention.type,
                    "target": intervention.target,
                    "description": intervention.description,
                },
                "result_summary": "SKIPPED (duplicate)",
                "hypothesis_update": {},
            })
            continue
        all_intervention_keys.add(dedup_key)

        if verbose:
            print(f"  Proposed: {intervention.type} — {intervention.description}")

        # Execute intervention
        result = None
        try:
            if domain == "market":
                result = run_market_intervention(
                    state_snapshot=ds["state_snapshot"],
                    agents_snapshot=ds["agents_snapshot"],
                    base_params=ds["base_params"],
                    shocks=ds["shocks"],
                    start_period=ds["start_period"],
                    intervention=intervention,
                    rule_based=True,
                )
            else:
                result = run_conflict_intervention(
                    state_snapshot=ds["state_snapshot"],
                    agents_config=ds["agents_snapshot"],
                    faction_agents=ds["faction_agents"],
                    shocks=ds["shocks"],
                    start_period=ds["start_period"],
                    intervention=intervention,
                    rule_based=True,
                )
            result_text = format_result_for_agent(result)
            all_results.append(result)
        except Exception as e:
            result_text = f"INTERVENTION FAILED: {e}"
            if verbose:
                print(f"  [ERROR] {e}")

        effect_summary = _summarize_effect(result)
        if verbose:
            print(f"  Result: {effect_summary}")

        # Feed result to BOTH agents
        update_prompt = (
            f"INTERVENTION RESULT (by {current_agent['name']}):\n{result_text}\n\n"
            f"Update your causal hypothesis based on this result. "
            f"Respond in JSON with: analysis, edge_updates, current_graph, key_uncertainties."
        )

        # Current agent gets the update prompt
        current_conv.append({"role": "user", "content": update_prompt})
        if dry_run:
            update_response = mock_llm_response("update", step, domain)
            update_raw = json.dumps(update_response)
        else:
            update_raw = call_llm(current_conv, api_key, model)
            update_response = parse_json_response(update_raw)
            llm_calls += 1
        current_conv.append({"role": "assistant", "content": update_raw})

        # Other agent gets a summary of the result (no LLM call, just added to context)
        other_conv = conv_b if is_agent_a else conv_a
        other_update = (
            f"YOUR PARTNER ({current_agent['name']}) ran an intervention:\n"
            f"  {intervention.type}: {intervention.description}\n"
            f"  Result: {effect_summary}\n\n"
            f"Keep this in mind for your next intervention."
        )
        other_conv.append({"role": "user", "content": other_update})
        other_conv.append({"role": "assistant", "content": json.dumps(
            {"acknowledged": f"Noted partner's result: {effect_summary}"})})

        # Record
        inv_record = {
            "step": step + 1,
            "agent_id": current_agent["id"],
            "intervention": {
                "type": intervention.type,
                "target": intervention.target,
                "description": intervention.description,
            },
            "result_summary": effect_summary if result else "FAILED",
            "hypothesis_update": update_response,
        }
        current_interventions.append(inv_record)

        # Update tracking for debate injection
        if is_agent_a:
            hypothesis_a = _extract_latest_hypothesis(all_interventions_a)
            last_intervention_a = intervention.description
            last_result_a = effect_summary
        else:
            hypothesis_b = _extract_latest_hypothesis(all_interventions_b)
            last_intervention_b = intervention.description
            last_result_b = effect_summary

    # Phase 3: Both agents declare independently
    if verbose:
        print(f"\n{'=' * 40}")
        print("Phase 3: Both agents declaring...")

    evidence_summary = build_evidence_summary(all_results, variables)

    agent_result_list: list[AgentResult] = []
    for agent_cfg, conv, interventions in [
        (agent_a, conv_a, all_interventions_a),
        (agent_b, conv_b, all_interventions_b),
    ]:
        latest_hyp = _extract_latest_hypothesis(interventions)
        # Combine both agents' interventions for the summary
        combined = sorted(all_interventions_a + all_interventions_b,
                          key=lambda x: x["step"])
        int_summary = _build_intervention_summary(combined)

        declaration_prompt = build_declaration_prompt(
            domain=domain,
            variables=variables,
            current_hypothesis=latest_hyp,
            all_interventions_summary=int_summary,
            evidence_summary=evidence_summary,
        )

        # Truncated conversation for declaration
        sys_prompt = conv[0]["content"]
        decl_conv = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": declaration_prompt},
        ]

        if dry_run:
            declaration = mock_llm_response("declaration", 0, domain)
            declaration_raw = json.dumps(declaration)
        else:
            declaration_raw = call_llm(decl_conv, api_key, model, max_tokens=4000)
            declaration = parse_json_response(declaration_raw)
            llm_calls += 1

        conv.append({"role": "user", "content": declaration_prompt})
        conv.append({"role": "assistant", "content": declaration_raw})

        final_edges = declaration.get("final_graph", [])
        edge_pairs = [(e["from"], e["to"]) for e in final_edges
                      if e.get("confidence") in ("high", "medium", "low")]
        edge_confidences = {
            (e["from"], e["to"]): e.get("confidence", "medium")
            for e in final_edges
            if e.get("confidence") in ("high", "medium", "low")
        }

        # Figure out which results belong to this agent
        own_results = [all_results[i] for i in range(len(all_results))
                       if i < len(all_results)]  # all shared

        ar = AgentResult(
            agent_id=agent_cfg["id"],
            declared_edges=edge_pairs,
            edge_confidences=edge_confidences,
            declaration_raw=declaration,
            all_interventions=interventions,
            all_results=all_results,
            evidence_summary=evidence_summary,
            conversation=conv,
            llm_calls=0,  # tracked globally
        )
        agent_result_list.append(ar)

        if verbose:
            print(f"  {agent_cfg['name']}: {len(edge_pairs)} edges")

    # Aggregate
    if verbose:
        print(f"\nAggregating...")

    scores = {}

    union_matrix = union_merge(agent_result_list, variables)
    s = score_fn(union_matrix)
    scores["union"] = {k: v for k, v in s.items() if k != "per_edge"}
    scores["union"]["per_edge"] = s["per_edge"]
    if verbose:
        print(f"  Union: F1={s['f1']:.3f} (P={s['precision']:.3f}, R={s['recall']:.3f})")

    mv_matrix = majority_vote(agent_result_list, variables)
    s = score_fn(mv_matrix)
    scores["majority_vote"] = {k: v for k, v in s.items() if k != "per_edge"}
    scores["majority_vote"]["per_edge"] = s["per_edge"]
    if verbose:
        print(f"  Majority vote: F1={s['f1']:.3f} (P={s['precision']:.3f}, R={s['recall']:.3f})")

    # Per-agent scores
    for r in agent_result_list:
        m = edges_to_matrix(r.declared_edges, variables)
        s = score_fn(m)
        scores[f"agent_{r.agent_id}"] = {k: v for k, v in s.items() if k != "per_edge"}
        if verbose:
            print(f"  agent_{r.agent_id}: F1={s['f1']:.3f}")

    if verbose:
        print(f"\nTotal LLM calls: {llm_calls}")

    # Save
    output = {
        "config": {
            "communication": "debate",
            "domain": domain,
            "budget": budget,
            "agent_a": agent_a["id"],
            "agent_b": agent_b["id"],
            "model": model if not dry_run else "dry_run",
            "seed": seed,
        },
        "scores": {k: {kk: vv for kk, vv in v.items() if kk != "per_edge"}
                   for k, v in scores.items()},
        "total_llm_calls": llm_calls,
        "n_interventions": len(all_results),
    }

    if output_dir:
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        with open(out_path / "results.json", "w") as f:
            json.dump(output, f, indent=2, default=str)

        per_agent_dir = out_path / "per_agent"
        per_agent_dir.mkdir(exist_ok=True)
        for r in agent_result_list:
            agent_data = {
                "agent_id": r.agent_id,
                "declared_edges": [list(e) for e in r.declared_edges],
                "declaration": r.declaration_raw,
                "interventions": r.all_interventions,
            }
            with open(per_agent_dir / f"{r.agent_id}.json", "w") as f:
                json.dump(agent_data, f, indent=2, default=str)

        conv_dir = out_path / "conversation_logs"
        conv_dir.mkdir(exist_ok=True)
        for r in agent_result_list:
            with open(conv_dir / f"{r.agent_id}_conversation.json", "w") as f:
                json.dump(r.conversation, f, indent=2, default=str)

        if verbose:
            print(f"\nResults saved to: {out_path}")

    return {"scores": scores, "agent_results": agent_result_list, "config": output["config"]}
