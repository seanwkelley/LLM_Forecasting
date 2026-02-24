"""
Single-agent causal discovery pipeline — extracted from run_pilot.py for reuse
in multi-agent communication structures.
"""

from __future__ import annotations

import copy
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


# ---------------------------------------------------------------------------
# AgentResult dataclass
# ---------------------------------------------------------------------------

@dataclass
class AgentResult:
    """Result from a single agent's causal discovery run."""
    agent_id: str
    declared_edges: list[tuple[str, str]]       # (from, to) pairs
    edge_confidences: dict[tuple[str, str], str] # edge -> "high"/"medium"/"low"
    declaration_raw: dict
    all_interventions: list[dict]
    all_results: list                            # InterventionResult objects
    evidence_summary: str
    conversation: list[dict]
    llm_calls: int


# ---------------------------------------------------------------------------
# LLM Client (from run_pilot.py)
# ---------------------------------------------------------------------------

def call_llm(
    messages: list[dict],
    api_key: str,
    model: str = "meta-llama/llama-3.3-70b-instruct",
    temperature: float = 0.3,
    max_tokens: int = 2000,
    json_mode: bool = True,
    max_retries: int = 5,
) -> str:
    """Call OpenRouter API with a multi-turn message history."""
    import requests

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    for attempt in range(max_retries):
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=120,
        )

        if response.status_code == 429:
            wait = 10 * (2 ** attempt)
            print(f"  [RATE LIMITED] Waiting {wait}s (attempt {attempt + 1}/{max_retries})...")
            time.sleep(wait)
            continue

        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    raise RuntimeError(f"Rate limited {max_retries} times, giving up")


def parse_json_response(text: str) -> dict:
    """Extract JSON from LLM response, handling markdown code blocks."""
    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return {"error": "Failed to parse JSON", "raw_text": text[:500]}


# ---------------------------------------------------------------------------
# Mock LLM (imported from run_pilot)
# ---------------------------------------------------------------------------

def mock_llm_response(prompt_type: str, step: int, domain: str = "market") -> dict:
    """Return mock responses for dry-run testing."""
    from causal_discovery.run_pilot import mock_llm_response as _mock
    return _mock(prompt_type, step, domain)


# ---------------------------------------------------------------------------
# Helper functions (from run_pilot.py)
# ---------------------------------------------------------------------------

def _extract_latest_hypothesis(all_interventions: list) -> str:
    """Extract the latest current_graph from intervention update responses."""
    for inv in reversed(all_interventions):
        update = inv.get("hypothesis_update", {})
        if "current_graph" in update:
            edges = update["current_graph"]
            lines = ["Current believed edges:"]
            for e in edges:
                if isinstance(e, dict):
                    lines.append(
                        f"  {e.get('from', '?')} -> {e.get('to', '?')} "
                        f"({e.get('confidence', '?')})"
                    )
                else:
                    lines.append(f"  {e}")
            uncertainties = update.get("key_uncertainties", [])
            if uncertainties:
                lines.append("\nKey uncertainties:")
                for u in uncertainties:
                    lines.append(f"  - {u}")
            return "\n".join(lines)
    return "No hypothesis formed yet."


def _build_intervention_summary(all_interventions: list) -> str:
    """Build a brief summary of all interventions run and their effects."""
    lines = []
    for inv in all_interventions:
        step = inv["step"]
        spec = inv["intervention"]
        result = inv["result_summary"]
        lines.append(f"  {step}. [{spec['type']}] {spec['description']} => {result}")
    return "\n".join(lines) if lines else "No interventions completed."


def _summarize_effect(result) -> str:
    """One-line summary of an intervention's effect."""
    if not result or not hasattr(result, 'intervention_trajectory'):
        return "No result"

    deltas = []
    for var in result.variables_returned:
        baseline_vals = [p.get(var) for p in result.baseline_trajectory if p.get(var) is not None]
        int_vals = [p.get(var) for p in result.intervention_trajectory if p.get(var) is not None]
        if baseline_vals and int_vals:
            b_mean = sum(baseline_vals) / len(baseline_vals)
            i_mean = sum(int_vals) / len(int_vals)
            delta = i_mean - b_mean
            if abs(delta) > 0.001:
                deltas.append(f"{var}={delta:+.2f}")

    return ", ".join(deltas) if deltas else "No detectable effect"


# ---------------------------------------------------------------------------
# Domain setup
# ---------------------------------------------------------------------------

def setup_domain(domain: str, n_warmup: int = 10, seed: int = 42, budget: int = 30) -> dict:
    """Run warmup for a domain, return snapshots + history.

    Returns
    -------
    dict with keys:
        state_snapshot, agents_snapshot, shocks, start_period, variables,
        history_data, system_prompt, intervention_types, score_fn,
        # domain-specific:
        base_params (market only), faction_agents (conflict only),
        config (scenario config)
    """
    if domain == "market":
        return _setup_market(n_warmup, seed, budget)
    elif domain == "conflict":
        return _setup_conflict(n_warmup, seed, budget)
    raise ValueError(f"Unknown domain: {domain}")


def _setup_market(n_warmup: int, seed: int, budget: int) -> dict:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    from market.agents_config import create_agents
    from market.engine import MarketState, run_period
    from market.shocks import generate_scenario_configs, apply_shocks
    from causal_discovery.intervention import _market_rule_based_orders
    from causal_discovery.ground_truth import MARKET_VARIABLES, score_market_graph
    from causal_discovery.prompts import (
        SYSTEM_PROMPT_MARKET, MARKET_INTERVENTION_TYPES,
        format_market_history,
    )

    configs = generate_scenario_configs(n_scenarios=1, n_periods=n_warmup + budget * 3, seed=seed)
    config = configs[0]
    agents, base_params = create_agents(config)
    shocks = config["shocks"]
    state = MarketState(agents=agents)

    for t in range(n_warmup):
        apply_shocks(agents, shocks, t, base_params)
        orders = _market_rule_based_orders(agents, state)
        run_period(state, orders)

    history_data = {
        "price_history": [round(p, 2) for p in state.price_history],
        "volume_history": list(state.volume_history),
        "fundamental_history": [round(f, 2) for f in state.fundamental_history],
    }

    return {
        "domain": "market",
        "state_snapshot": copy.deepcopy(state),
        "agents_snapshot": copy.deepcopy(agents),
        "base_params": copy.deepcopy(base_params),
        "shocks": shocks,
        "start_period": state.period,
        "variables": MARKET_VARIABLES,
        "history_data": history_data,
        "history_summary": format_market_history(history_data, n_periods=n_warmup),
        "system_prompt": SYSTEM_PROMPT_MARKET,
        "intervention_types": MARKET_INTERVENTION_TYPES,
        "score_fn": score_market_graph,
        "config": config,
        "faction_agents": None,
    }


def _setup_conflict(n_warmup: int, seed: int, budget: int) -> dict:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    from conflict.agents_config import create_agents
    from conflict.engine import initialize_state, run_period, aggregate_faction_action
    from conflict.shocks import generate_scenario_configs, apply_shocks
    from causal_discovery.intervention import _conflict_rule_based_recommendations
    from causal_discovery.ground_truth import CONFLICT_VARIABLES, score_conflict_graph
    from causal_discovery.prompts import (
        SYSTEM_PROMPT_CONFLICT, CONFLICT_INTERVENTION_TYPES,
        format_conflict_history,
    )

    configs = generate_scenario_configs(n_scenarios=1, n_periods=n_warmup + budget * 3, seed=seed)
    config = configs[0]
    agents_config, faction_agents = create_agents(config)
    shocks = config["shocks"]
    state = initialize_state(config)

    for t in range(n_warmup):
        apply_shocks(state, shocks, t)
        recommendations = _conflict_rule_based_recommendations(agents_config, state)
        novaris_recs = [r for r in recommendations if r["faction"] == "novaris"]
        tethys_recs = [r for r in recommendations if r["faction"] == "tethys"]
        novaris_action = aggregate_faction_action(novaris_recs, "novaris")
        tethys_action = aggregate_faction_action(tethys_recs, "tethys")
        run_period(state, novaris_action, tethys_action)

    actions_log = []
    for action_pair in state.action_history:
        if len(action_pair) == 2:
            actions_log.append({
                "novaris_action": action_pair[0].action_name,
                "tethys_action": action_pair[1].action_name,
            })

    history_data = {
        "escalation_history": [round(e, 2) for e in state.escalation_history],
        "actions_log": actions_log,
    }

    return {
        "domain": "conflict",
        "state_snapshot": copy.deepcopy(state),
        "agents_snapshot": copy.deepcopy(agents_config),
        "base_params": None,
        "shocks": shocks,
        "start_period": state.period,
        "variables": CONFLICT_VARIABLES,
        "history_data": history_data,
        "history_summary": format_conflict_history(history_data, n_periods=n_warmup),
        "system_prompt": SYSTEM_PROMPT_CONFLICT,
        "intervention_types": CONFLICT_INTERVENTION_TYPES,
        "score_fn": score_conflict_graph,
        "config": config,
        "faction_agents": faction_agents,
    }


# ---------------------------------------------------------------------------
# Single-agent pipeline
# ---------------------------------------------------------------------------

def run_single_agent(
    domain_setup: dict,
    agent_id: str,
    budget: int,
    api_key: str = "",
    model: str = "meta-llama/llama-3.3-70b-instruct",
    persona_prompt: str = "",
    allowed_variables: list[str] | None = None,
    shared_results: list | None = None,
    context_injection: str = "",
    dry_run: bool = False,
    verbose: bool = True,
) -> AgentResult:
    """Run the full observation -> intervention loop -> declaration pipeline for one agent.

    Parameters
    ----------
    domain_setup : dict
        Output of setup_domain().
    agent_id : str
        Identifier for this agent.
    budget : int
        Number of interventions this agent can run.
    persona_prompt : str
        Prepended to system prompt for persona injection.
    allowed_variables : list[str] | None
        If set, restrict intervention targets to these variables (specialization).
    shared_results : list | None
        Pre-existing InterventionResult objects to include in evidence summary.
    context_injection : str
        Extra context injected into intervention prompts (e.g. debate partner's hypothesis).
    dry_run : bool
        Use mock LLM responses.
    verbose : bool
        Print progress.
    """
    from causal_discovery.intervention import (
        Intervention, run_market_intervention, run_conflict_intervention,
        format_result_for_agent,
    )
    from causal_discovery.prompts import (
        build_observation_prompt, build_intervention_prompt,
        build_declaration_prompt, build_evidence_summary,
    )
    from causal_discovery.ground_truth import edges_to_matrix

    domain = domain_setup["domain"]
    variables = domain_setup["variables"]
    system_prompt = domain_setup["system_prompt"]
    intervention_types = domain_setup["intervention_types"]

    # Build system prompt with persona
    if persona_prompt:
        system_prompt = f"{persona_prompt}\n\n{system_prompt}"

    # Initialize conversation
    conversation = [{"role": "system", "content": system_prompt}]

    # --- Phase 1: Observation ---
    if verbose:
        print(f"  [{agent_id}] Phase 1: Observing...")

    observation_prompt = build_observation_prompt(
        domain=domain,
        history_summary=domain_setup["history_summary"],
        variables=variables,
    )
    if context_injection:
        observation_prompt += f"\n\nADDITIONAL CONTEXT:\n{context_injection}"

    conversation.append({"role": "user", "content": observation_prompt})

    if dry_run:
        observation_response = mock_llm_response("observation", 0, domain)
        observation_raw = json.dumps(observation_response)
    else:
        observation_raw = call_llm(conversation, api_key, model)
        observation_response = parse_json_response(observation_raw)

    conversation.append({"role": "assistant", "content": observation_raw})
    llm_calls = 1

    if verbose:
        n_confident = len(observation_response.get("confident_edges", []))
        n_uncertain = len(observation_response.get("uncertain_edges", []))
        print(f"  [{agent_id}] Initial: {n_confident} confident, {n_uncertain} uncertain edges")

    # --- Phase 2: Interventions ---
    all_interventions = []
    all_results = list(shared_results) if shared_results else []
    own_results = []  # only this agent's results
    all_intervention_keys = set()

    for step in range(budget):
        if verbose:
            print(f"  [{agent_id}] Intervention {step+1}/{budget}:")

        # Build intervention prompt
        intervention_prompt = build_intervention_prompt(
            domain=domain,
            variables=variables,
            current_hypothesis="(see your previous messages above)",
            past_interventions="(see your previous messages above)",
            budget_remaining=budget - step,
            intervention_types=intervention_types,
        )

        # Add allowed_variables constraint
        if allowed_variables:
            intervention_prompt += (
                f"\n\nIMPORTANT: You are a specialist agent. You may ONLY propose "
                f"interventions that target these variables: {', '.join(allowed_variables)}. "
                f"Interventions targeting other variables will be rejected."
            )

        # Add context injection (debate partner's hypothesis, etc.)
        if context_injection:
            intervention_prompt += f"\n\n{context_injection}"

        conversation.append({"role": "user", "content": intervention_prompt})

        if dry_run:
            proposal = mock_llm_response("intervention", step, domain)
            proposal_raw = json.dumps(proposal)
        else:
            proposal_raw = call_llm(conversation, api_key, model)
            proposal = parse_json_response(proposal_raw)
            llm_calls += 1

        conversation.append({"role": "assistant", "content": proposal_raw})

        # Parse intervention spec
        int_spec = proposal.get("intervention", proposal)
        target = int_spec.get("target", {})
        int_type = int_spec.get("type", "event")

        # Reject invalid types
        if int_type not in ("action", "trait", "event"):
            if verbose:
                print(f"  [{agent_id}] [INVALID] Type '{int_type}'")
            reject_msg = (
                f"'{int_type}' is not a valid intervention type. "
                f"You MUST use one of: action, trait, event. "
                f"Propose a valid intervention."
            )
            conversation.append({"role": "user", "content": reject_msg})
            conversation.append({"role": "assistant", "content": json.dumps(
                {"acknowledged": "Will propose a valid intervention."})})
            all_interventions.append({
                "step": step + 1,
                "agent_id": agent_id,
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

        # Normalize agent_id for conflict domain
        if int_type == "action" and "agent_id" not in target:
            for alt_key in ("agent", "agent_name"):
                if alt_key in target:
                    target["agent_id"] = target.pop(alt_key)
                    break

        # Check allowed_variables constraint (specialization)
        if allowed_variables and int_type == "trait":
            param = target.get("param", "")
            if param and param not in allowed_variables:
                if verbose:
                    print(f"  [{agent_id}] [REJECTED] Variable '{param}' not in allowed set")
                reject_msg = (
                    f"Variable '{param}' is not in your assigned variables: "
                    f"{', '.join(allowed_variables)}. Propose an intervention "
                    f"targeting one of your assigned variables."
                )
                conversation.append({"role": "user", "content": reject_msg})
                conversation.append({"role": "assistant", "content": json.dumps(
                    {"acknowledged": "Will target an assigned variable."})})
                all_interventions.append({
                    "step": step + 1,
                    "agent_id": agent_id,
                    "intervention": {"type": int_type, "target": target,
                                     "description": int_spec.get("description", "")},
                    "result_summary": f"REJECTED (variable not allowed)",
                    "hypothesis_update": {},
                })
                continue

        intervention = Intervention(
            type=int_type,
            target=target,
            run_periods=int_spec.get("run_periods", 3),
            description=int_spec.get("description", f"Intervention {step+1}"),
        )

        # Dedup check
        dedup_key = (int_type, json.dumps(target, sort_keys=True))
        if dedup_key in all_intervention_keys:
            if verbose:
                print(f"  [{agent_id}] [SKIPPED] Duplicate")
            skip_msg = (
                f"This intervention was already run (duplicate). "
                f"It has been skipped. Please propose a DIFFERENT intervention."
            )
            conversation.append({"role": "user", "content": skip_msg})
            conversation.append({"role": "assistant", "content": json.dumps(
                {"acknowledged": "Will propose a different intervention."})})
            all_interventions.append({
                "step": step + 1,
                "agent_id": agent_id,
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
            print(f"  [{agent_id}] Proposed: {intervention.type} — {intervention.description}")

        # Execute intervention
        result = None
        try:
            if domain == "market":
                result = run_market_intervention(
                    state_snapshot=domain_setup["state_snapshot"],
                    agents_snapshot=domain_setup["agents_snapshot"],
                    base_params=domain_setup["base_params"],
                    shocks=domain_setup["shocks"],
                    start_period=domain_setup["start_period"],
                    intervention=intervention,
                    rule_based=True,
                )
            else:
                result = run_conflict_intervention(
                    state_snapshot=domain_setup["state_snapshot"],
                    agents_config=domain_setup["agents_snapshot"],
                    faction_agents=domain_setup["faction_agents"],
                    shocks=domain_setup["shocks"],
                    start_period=domain_setup["start_period"],
                    intervention=intervention,
                    rule_based=True,
                )
            result_text = format_result_for_agent(result)
            all_results.append(result)
            own_results.append(result)
        except Exception as e:
            result_text = f"INTERVENTION FAILED: {e}"
            if verbose:
                print(f"  [{agent_id}] [ERROR] {e}")

        if verbose:
            effect = _summarize_effect(result)
            print(f"  [{agent_id}] Result: {effect}")

        # Feed result back and ask for hypothesis update
        update_prompt = (
            f"INTERVENTION RESULT:\n{result_text}\n\n"
            f"Update your causal hypothesis based on this result. "
            f"What edges are confirmed, disconfirmed, or still uncertain? "
            f"Respond in JSON with: analysis, edge_updates, current_graph, key_uncertainties."
        )

        conversation.append({"role": "user", "content": update_prompt})

        if dry_run:
            update_response = mock_llm_response("update", step, domain)
            update_raw = json.dumps(update_response)
        else:
            update_raw = call_llm(conversation, api_key, model)
            update_response = parse_json_response(update_raw)
            llm_calls += 1

        conversation.append({"role": "assistant", "content": update_raw})

        all_interventions.append({
            "step": step + 1,
            "agent_id": agent_id,
            "intervention": {
                "type": intervention.type,
                "target": intervention.target,
                "description": intervention.description,
            },
            "result_summary": _summarize_effect(result) if result else "FAILED",
            "hypothesis_update": update_response,
        })

    # --- Phase 3: Final Declaration ---
    if verbose:
        print(f"  [{agent_id}] Phase 3: Declaring final graph...")

    evidence_summary = build_evidence_summary(all_results, variables)
    latest_hypothesis = _extract_latest_hypothesis(all_interventions)
    intervention_summary = _build_intervention_summary(all_interventions)

    declaration_prompt = build_declaration_prompt(
        domain=domain,
        variables=variables,
        current_hypothesis=latest_hypothesis,
        all_interventions_summary=intervention_summary,
        evidence_summary=evidence_summary,
    )

    # Truncated conversation for declaration
    declaration_conversation = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": declaration_prompt},
    ]

    if dry_run:
        declaration = mock_llm_response("declaration", 0, domain)
        declaration_raw = json.dumps(declaration)
    else:
        declaration_raw = call_llm(
            declaration_conversation, api_key, model, max_tokens=4000
        )
        declaration = parse_json_response(declaration_raw)
        llm_calls += 1

    conversation.append({"role": "user", "content": declaration_prompt})
    conversation.append({"role": "assistant", "content": declaration_raw})

    # Extract edges
    final_edges = declaration.get("final_graph", [])
    edge_pairs = [(e["from"], e["to"]) for e in final_edges
                  if e.get("confidence") in ("high", "medium", "low")]
    edge_confidences = {
        (e["from"], e["to"]): e.get("confidence", "medium")
        for e in final_edges
        if e.get("confidence") in ("high", "medium", "low")
    }

    if verbose:
        print(f"  [{agent_id}] Declared {len(edge_pairs)} edges")

    return AgentResult(
        agent_id=agent_id,
        declared_edges=edge_pairs,
        edge_confidences=edge_confidences,
        declaration_raw=declaration,
        all_interventions=all_interventions,
        all_results=own_results,
        evidence_summary=evidence_summary,
        conversation=conversation,
        llm_calls=llm_calls,
    )
