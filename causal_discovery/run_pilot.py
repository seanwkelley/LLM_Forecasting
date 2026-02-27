"""
Causal Discovery Pilot — Single-agent causal modeler on market and conflict domains.

Runs one LLM causal modeler agent with a budget of N interventions.
Uses rule-based simulation agents for intervention rollouts (fast, no API cost
for simulation agents — only the modeler agent makes LLM calls).

Usage:
    # Market domain (default)
    python causal_discovery/run_pilot.py --budget 5
    python causal_discovery/run_pilot.py --dry-run --budget 3

    # Conflict domain
    python causal_discovery/run_pilot.py --domain conflict --budget 5
    python causal_discovery/run_pilot.py --domain conflict --dry-run --budget 3
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import sys
import time
from pathlib import Path

import numpy as np

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from causal_discovery.intervention import (
    Intervention, run_market_intervention, run_conflict_intervention,
    format_result_for_agent,
)
from causal_discovery.ground_truth import (
    MARKET_VARIABLES, score_market_graph,
    CONFLICT_VARIABLES, score_conflict_graph,
    edges_to_matrix,
)
from causal_discovery.prompts import (
    SYSTEM_PROMPT_MARKET, MARKET_INTERVENTION_TYPES,
    SYSTEM_PROMPT_CONFLICT, CONFLICT_INTERVENTION_TYPES,
    build_observation_prompt, build_intervention_prompt,
    build_declaration_prompt, build_evidence_summary,
    format_market_history, format_conflict_history,
)


# =============================================================================
# LLM Client
# =============================================================================

def call_llm(
    messages: list[dict],
    api_key: str,
    model: str = "meta-llama/llama-3.3-70b-instruct",
    temperature: float = 0.3,
    max_tokens: int = 4000,
    json_mode: bool = True,
    max_retries: int = 5,
) -> str:
    """Call OpenRouter API with a multi-turn message history.

    Parameters
    ----------
    messages : list[dict]
        OpenAI-format messages: [{"role": ..., "content": ...}, ...]
    api_key : str
        OpenRouter API key.
    model : str
        Model identifier.
    temperature : float
        Sampling temperature.
    max_tokens : int
        Maximum tokens per response.
    json_mode : bool
        If True, request JSON output format.
    max_retries : int
        Maximum retry attempts on rate limit (429).

    Returns
    -------
    str
        The assistant's response text.
    """
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

        if response.status_code == 400:
            # Context length overflow or unsupported param — trim conversation
            error_body = response.text[:500]
            msg_tokens = sum(len(m.get("content", "")) for m in messages) // 4
            print(f"  [400 ERROR] ~{msg_tokens} prompt tokens. Response: {error_body}")
            # Retry with trimmed history: keep system + last 4 messages
            if len(messages) > 6:
                messages = [messages[0]] + messages[-4:]
                payload["messages"] = messages
                print(f"  [RETRY] Trimmed to {len(messages)} messages, retrying...")
                continue
            response.raise_for_status()

        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    raise RuntimeError(f"Rate limited or errored {max_retries} times, giving up")


def parse_json_response(text: str) -> dict:
    """Extract JSON from LLM response, handling markdown code blocks."""
    # Try to find JSON in code block
    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find any {...} block
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return {"error": "Failed to parse JSON", "raw_text": text[:500]}


# =============================================================================
# Mock LLM for dry runs
# =============================================================================

MOCK_INTERVENTION_SEQUENCE = [
    {
        "intervention": {
            "type": "event",
            "target": {"shock_type": "supply_disruption", "magnitude": 1.5},
            "run_periods": 3,
            "description": "Test if supply shocks cause price changes",
        },
        "hypothesis_being_tested": "shock -> production_cost -> agent_orders -> clearing_price",
        "expected_if_edge_exists": "Clearing price should increase",
        "expected_if_no_edge": "No change in clearing price",
    },
    {
        "intervention": {
            "type": "trait",
            "target": {"agent_id": "consumer_A", "param": "demand_per_period", "value": 50},
            "run_periods": 3,
            "description": "Test if demand changes affect price",
        },
        "hypothesis_being_tested": "demand_per_period -> agent_orders -> clearing_price",
        "expected_if_edge_exists": "Clearing price should increase with higher demand",
        "expected_if_no_edge": "No change in clearing price",
    },
    {
        "intervention": {
            "type": "action",
            "target": {"agent_id": "speculator_A", "param": "quantity", "value": 0},
            "run_periods": 3,
            "description": "Test if removing speculator affects price",
        },
        "hypothesis_being_tested": "agent_orders -> clearing_price",
        "expected_if_edge_exists": "Clearing price should change without speculator orders",
        "expected_if_no_edge": "No change",
    },
]


MOCK_CONFLICT_INTERVENTION_SEQUENCE = [
    {
        "intervention": {
            "type": "event",
            "target": {"shock_type": "border_incident", "magnitude": 1.5},
            "run_periods": 3,
            "description": "Test if border incidents cause escalation changes",
        },
        "hypothesis_being_tested": "shock -> escalation_index -> agent_recommendation",
        "expected_if_edge_exists": "Escalation index should increase",
        "expected_if_no_edge": "No change in escalation index",
    },
    {
        "intervention": {
            "type": "trait",
            "target": {"faction": "novaris", "param": "hawk_dove", "value": 0.1},
            "run_periods": 3,
            "description": "Test if dovish faction shifts reduce escalation",
        },
        "hypothesis_being_tested": "hawk_score -> agent_recommendation -> faction_action -> escalation_index",
        "expected_if_edge_exists": "Escalation should decrease with dovish Novaris",
        "expected_if_no_edge": "No change in escalation",
    },
    {
        "intervention": {
            "type": "action",
            "target": {"agent_id": "krasnov", "value": "peace_talks"},
            "run_periods": 3,
            "description": "Test if forcing hawk agent to peace talks affects escalation",
        },
        "hypothesis_being_tested": "agent_recommendation -> faction_action -> escalation_index",
        "expected_if_edge_exists": "Escalation should decrease with forced de-escalation",
        "expected_if_no_edge": "No change — individual agent may be diluted by aggregation",
    },
]


def mock_llm_response(prompt_type: str, step: int, domain: str = "market") -> dict:
    """Return mock responses for dry-run testing."""
    if domain == "conflict":
        return _mock_conflict_response(prompt_type, step)
    return _mock_market_response(prompt_type, step)


def _mock_market_response(prompt_type: str, step: int) -> dict:
    """Mock responses for market domain dry runs."""
    if prompt_type == "observation":
        return {
            "confident_edges": [
                {"from": "agent_orders", "to": "clearing_price", "confidence": "high",
                 "reasoning": "Orders directly determine price in any auction"},
            ],
            "uncertain_edges": [
                {"from": "fundamental_price", "to": "clearing_price", "confidence": "low",
                 "reasoning": "Correlated but unclear if causal"},
            ],
            "candidate_common_causes": [],
            "priority_interventions": [
                {"description": "Inject supply shock", "rationale": "Test shock -> price pathway"}
            ],
        }
    elif prompt_type == "intervention":
        idx = min(step, len(MOCK_INTERVENTION_SEQUENCE) - 1)
        return MOCK_INTERVENTION_SEQUENCE[idx]
    elif prompt_type == "update":
        return {
            "analysis": "The intervention showed a clear effect on the target variable.",
            "edge_updates": [],
            "current_graph": [
                {"from": "shock", "to": "production_cost", "confidence": "high"},
                {"from": "agent_orders", "to": "clearing_price", "confidence": "high"},
            ],
            "key_uncertainties": ["fundamental_price relationship unclear"],
        }
    elif prompt_type == "declaration":
        return {
            "per_variable": {
                "shock": {"parents": [], "children": ["production_cost", "demand_per_period", "demand_value", "storage_cost"]},
                "production_cost": {"parents": ["shock"], "children": ["agent_orders", "fundamental_price"]},
                "demand_per_period": {"parents": ["shock"], "children": ["agent_orders"]},
                "demand_value": {"parents": ["shock"], "children": ["agent_orders", "fundamental_price"]},
                "storage_cost": {"parents": ["shock"], "children": ["agent_orders"]},
                "agent_orders": {"parents": ["production_cost", "demand_per_period", "demand_value", "storage_cost", "cash", "inventory", "price_history"], "children": ["clearing_price", "volume"]},
                "clearing_price": {"parents": ["agent_orders"], "children": ["cash", "inventory", "price_history", "fundamental_price"]},
                "volume": {"parents": ["agent_orders"], "children": ["cash", "inventory"]},
                "cash": {"parents": ["clearing_price", "volume"], "children": ["agent_orders"]},
                "inventory": {"parents": ["clearing_price", "volume"], "children": ["agent_orders"]},
                "price_history": {"parents": ["clearing_price"], "children": ["agent_orders"]},
                "fundamental_price": {"parents": ["production_cost", "demand_value", "clearing_price"], "children": []},
            },
            "final_graph": [
                {"from": "shock", "to": "production_cost", "confidence": "high"},
                {"from": "shock", "to": "demand_per_period", "confidence": "high"},
                {"from": "shock", "to": "demand_value", "confidence": "medium"},
                {"from": "shock", "to": "storage_cost", "confidence": "low"},
                {"from": "production_cost", "to": "agent_orders", "confidence": "high"},
                {"from": "demand_per_period", "to": "agent_orders", "confidence": "high"},
                {"from": "demand_value", "to": "agent_orders", "confidence": "high"},
                {"from": "storage_cost", "to": "agent_orders", "confidence": "low"},
                {"from": "agent_orders", "to": "clearing_price", "confidence": "high"},
                {"from": "agent_orders", "to": "volume", "confidence": "high"},
                {"from": "clearing_price", "to": "cash", "confidence": "medium"},
                {"from": "clearing_price", "to": "inventory", "confidence": "medium"},
                {"from": "clearing_price", "to": "price_history", "confidence": "high"},
                {"from": "clearing_price", "to": "fundamental_price", "confidence": "low"},
                {"from": "volume", "to": "cash", "confidence": "medium"},
                {"from": "volume", "to": "inventory", "confidence": "medium"},
                {"from": "cash", "to": "agent_orders", "confidence": "medium"},
                {"from": "inventory", "to": "agent_orders", "confidence": "medium"},
                {"from": "price_history", "to": "agent_orders", "confidence": "medium"},
                {"from": "production_cost", "to": "fundamental_price", "confidence": "medium"},
                {"from": "demand_value", "to": "fundamental_price", "confidence": "medium"},
            ],
            "absent_edges": [
                {"from": "fundamental_price", "to": "clearing_price",
                 "reasoning": "Correlated via common cause, not direct"},
            ],
            "feedback_loops": [
                {"cycle": ["clearing_price", "cash", "agent_orders", "clearing_price"],
                 "reasoning": "Price affects wealth affects next orders"},
            ],
            "common_causes": [
                {"effect_1": "fundamental_price", "effect_2": "clearing_price",
                 "cause": "production_cost/demand_value",
                 "reasoning": "Both computed from same underlying parameters"},
            ],
            "limitations": "Effect of storage_cost not well tested",
        }
    return {}


def _mock_conflict_response(prompt_type: str, step: int) -> dict:
    """Mock responses for conflict domain dry runs."""
    if prompt_type == "observation":
        return {
            "confident_edges": [
                {"from": "faction_action", "to": "escalation_index", "confidence": "high",
                 "reasoning": "Actions directly determine escalation changes"},
                {"from": "hawk_score", "to": "agent_recommendation", "confidence": "high",
                 "reasoning": "Hawks recommend escalatory actions, doves recommend peace"},
            ],
            "uncertain_edges": [
                {"from": "resources", "to": "faction_action", "confidence": "low",
                 "reasoning": "Resources constrain but may not directly cause action choice"},
                {"from": "escalation_index", "to": "sanctions_level", "confidence": "medium",
                 "reasoning": "High escalation correlates with sanctions but unclear mechanism"},
            ],
            "candidate_common_causes": [
                {"variables": ["sanctions_level", "gdp"], "possible_cause": "escalation_index",
                 "reasoning": "Both may be driven by overall conflict intensity"},
            ],
            "priority_interventions": [
                {"description": "Inject border incident", "rationale": "Test shock -> escalation pathway"},
                {"description": "Override faction hawk_dove", "rationale": "Test disposition -> action -> escalation"},
            ],
        }
    elif prompt_type == "intervention":
        idx = min(step, len(MOCK_CONFLICT_INTERVENTION_SEQUENCE) - 1)
        return MOCK_CONFLICT_INTERVENTION_SEQUENCE[idx]
    elif prompt_type == "update":
        return {
            "analysis": "The intervention showed a clear effect on escalation dynamics.",
            "edge_updates": [],
            "current_graph": [
                {"from": "shock", "to": "escalation_index", "confidence": "high"},
                {"from": "faction_action", "to": "escalation_index", "confidence": "high"},
                {"from": "hawk_score", "to": "agent_recommendation", "confidence": "high"},
            ],
            "key_uncertainties": ["resources -> faction_action relationship unclear"],
        }
    elif prompt_type == "declaration":
        return {
            "per_variable": {
                "shock": {"parents": [], "children": ["escalation_index", "resources", "military_balance", "sanctions_level"]},
                "hawk_score": {"parents": [], "children": ["agent_recommendation"]},
                "escalation_index": {"parents": ["shock", "faction_action"], "children": ["agent_recommendation", "gdp", "sanctions_level", "international_support", "political_stability"]},
                "resources": {"parents": ["shock", "faction_action", "gdp"], "children": ["agent_recommendation"]},
                "gdp": {"parents": ["escalation_index", "sanctions_level"], "children": ["resources", "political_stability"]},
                "military_strength": {"parents": ["faction_action"], "children": ["military_balance"]},
                "political_stability": {"parents": ["escalation_index", "gdp"], "children": ["agent_recommendation"]},
                "military_balance": {"parents": ["shock", "military_strength"], "children": ["territory_controlled", "faction_action"]},
                "territory_controlled": {"parents": ["military_balance", "faction_action"], "children": []},
                "sanctions_level": {"parents": ["shock", "escalation_index"], "children": ["gdp"]},
                "international_support": {"parents": ["escalation_index"], "children": ["sanctions_level"]},
                "agent_recommendation": {"parents": ["hawk_score", "escalation_index", "resources", "political_stability"], "children": ["faction_action"]},
                "faction_action": {"parents": ["agent_recommendation", "military_balance"], "children": ["escalation_index", "military_strength", "territory_controlled", "resources"]},
            },
            "final_graph": [
                {"from": "shock", "to": "escalation_index", "confidence": "high"},
                {"from": "shock", "to": "resources", "confidence": "high"},
                {"from": "shock", "to": "military_balance", "confidence": "medium"},
                {"from": "shock", "to": "sanctions_level", "confidence": "medium"},
                {"from": "hawk_score", "to": "agent_recommendation", "confidence": "high"},
                {"from": "escalation_index", "to": "agent_recommendation", "confidence": "high"},
                {"from": "escalation_index", "to": "gdp", "confidence": "medium"},
                {"from": "escalation_index", "to": "sanctions_level", "confidence": "high"},
                {"from": "escalation_index", "to": "international_support", "confidence": "medium"},
                {"from": "escalation_index", "to": "political_stability", "confidence": "low"},
                {"from": "resources", "to": "agent_recommendation", "confidence": "medium"},
                {"from": "political_stability", "to": "agent_recommendation", "confidence": "low"},
                {"from": "agent_recommendation", "to": "faction_action", "confidence": "high"},
                {"from": "faction_action", "to": "escalation_index", "confidence": "high"},
                {"from": "faction_action", "to": "military_strength", "confidence": "medium"},
                {"from": "faction_action", "to": "territory_controlled", "confidence": "medium"},
                {"from": "faction_action", "to": "resources", "confidence": "high"},
                {"from": "gdp", "to": "resources", "confidence": "medium"},
                {"from": "gdp", "to": "political_stability", "confidence": "low"},
                {"from": "sanctions_level", "to": "gdp", "confidence": "medium"},
                {"from": "international_support", "to": "sanctions_level", "confidence": "low"},
                {"from": "military_strength", "to": "military_balance", "confidence": "high"},
                {"from": "military_balance", "to": "territory_controlled", "confidence": "medium"},
                {"from": "military_balance", "to": "faction_action", "confidence": "low"},
            ],
            "absent_edges": [
                {"from": "territory_controlled", "to": "escalation_index",
                 "reasoning": "Territory is a consequence, not a direct cause of escalation"},
            ],
            "feedback_loops": [
                {"cycle": ["escalation_index", "agent_recommendation", "faction_action", "escalation_index"],
                 "reasoning": "Escalation drives hawkish recommendations which drive further escalation"},
                {"cycle": ["faction_action", "resources", "agent_recommendation", "faction_action"],
                 "reasoning": "Actions cost resources which constrain future actions"},
            ],
            "common_causes": [
                {"effect_1": "sanctions_level", "effect_2": "gdp",
                 "cause": "escalation_index",
                 "reasoning": "Both driven by escalation level"},
            ],
            "limitations": "Effect of political_stability not well tested; faction_action -> sanctions_level path unclear",
        }
    return {}


# =============================================================================
# Main Pilot Runner
# =============================================================================

def run_pilot(
    budget: int = 30,
    n_warmup: int = 10,
    api_key: str = "",
    model: str = "meta-llama/llama-3.3-70b-instruct",
    dry_run: bool = False,
    output_dir: str = "",
    seed: int = 42,
    verbose: bool = True,
):
    """Run a single-agent causal discovery pilot on the market engine.

    Steps:
    1. Set up market scenario and run warm-up periods (rule-based)
    2. Save state snapshot
    3. Agent observes history and forms initial hypothesis
    4. Agent proposes and executes interventions (budget limited)
    5. Agent declares final causal graph
    6. Score against ground truth
    """
    from market.agents_config import create_agents
    from market.engine import MarketState, run_period
    from market.shocks import generate_scenario_configs, apply_shocks

    from causal_discovery.intervention import _market_rule_based_orders

    # --- Setup ---
    configs = generate_scenario_configs(n_scenarios=1, n_periods=n_warmup + budget * 3, seed=seed)
    config = configs[0]
    agents, base_params = create_agents(config)
    shocks = config["shocks"]
    state = MarketState(agents=agents)

    if verbose:
        print("=" * 60)
        print(f"CAUSAL DISCOVERY PILOT — Market Engine")
        print(f"Budget: {budget} interventions | Warm-up: {n_warmup} periods")
        print(f"Model: {'DRY RUN' if dry_run else model}")
        print(f"Scenario: {config['scenario_id']}")
        print("=" * 60)

    # --- Warm-up ---
    if verbose:
        print(f"\nPhase 0: Running {n_warmup} warm-up periods...")

    for t in range(n_warmup):
        apply_shocks(agents, shocks, t, base_params)
        orders = _market_rule_based_orders(agents, state)
        run_period(state, orders)

    if verbose:
        print(f"  Warm-up complete. Price=${state.price_history[-1]:.2f}, "
              f"Period={state.period}")

    # Save snapshot for intervention rollouts
    state_snapshot = copy.deepcopy(state)
    agents_snapshot = copy.deepcopy(agents)
    base_params_snapshot = copy.deepcopy(base_params)

    # Build history data for observation prompt
    history_data = {
        "price_history": [round(p, 2) for p in state.price_history],
        "volume_history": list(state.volume_history),
        "fundamental_history": [round(f, 2) for f in state.fundamental_history],
    }

    # --- Initialize multi-turn conversation ---
    conversation = [{"role": "system", "content": SYSTEM_PROMPT_MARKET}]

    # --- Phase 1: Observation ---
    if verbose:
        print(f"\nPhase 1: Observing simulation history...")

    history_summary = format_market_history(history_data, n_periods=n_warmup)
    observation_prompt = build_observation_prompt(
        domain="market",
        history_summary=history_summary,
        variables=MARKET_VARIABLES,
    )

    conversation.append({"role": "user", "content": observation_prompt})

    if dry_run:
        observation_response = mock_llm_response("observation", 0)
        observation_raw = json.dumps(observation_response)
    else:
        observation_raw = call_llm(conversation, api_key, model)
        observation_response = parse_json_response(observation_raw)

    conversation.append({"role": "assistant", "content": observation_raw})

    if verbose:
        n_confident = len(observation_response.get("confident_edges", []))
        n_uncertain = len(observation_response.get("uncertain_edges", []))
        print(f"  Initial hypothesis: {n_confident} confident edges, "
              f"{n_uncertain} uncertain edges")

    # --- Phase 2: Interventions ---
    all_interventions = []
    all_results = []
    all_intervention_keys = set()  # track (type, target_key) for dedup
    llm_calls = 1  # observation call

    for step in range(budget):
        if verbose:
            print(f"\nIntervention {step+1}/{budget}:")

        # Propose intervention — the model sees the full conversation history
        # so it knows all past interventions and results. We just need to ask
        # for the next one with the remaining budget.
        proposal_prompt = build_intervention_prompt(
            domain="market",
            variables=MARKET_VARIABLES,
            current_hypothesis="(see your previous messages above)",
            past_interventions="(see your previous messages above)",
            budget_remaining=budget - step,
            intervention_types=MARKET_INTERVENTION_TYPES,
        )

        conversation.append({"role": "user", "content": proposal_prompt})

        if dry_run:
            proposal = mock_llm_response("intervention", step)
            proposal_raw = json.dumps(proposal)
        else:
            proposal_raw = call_llm(conversation, api_key, model)
            proposal = parse_json_response(proposal_raw)
            llm_calls += 1

        conversation.append({"role": "assistant", "content": proposal_raw})

        # Parse intervention spec — normalize common LLM formatting variations
        int_spec = proposal.get("intervention", proposal)
        target = int_spec.get("target", {})
        int_type = int_spec.get("type", "event")

        # Reject invalid intervention types
        if int_type not in ("action", "trait", "event"):
            if verbose:
                print(f"  Proposed: {int_type} — {int_spec.get('description', '?')}")
                print(f"  [INVALID] Type '{int_type}' is not valid")
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
                "intervention": {"type": int_type, "target": target,
                                 "description": int_spec.get("description", "")},
                "result_summary": f"INVALID TYPE ({int_type})",
                "hypothesis_update": {},
            })
            continue

        # Normalize event targets: LLMs sometimes use "event"/"shock"/"type"
        # instead of "shock_type"
        if int_type == "event" and "shock_type" not in target:
            for alt_key in ("event", "shock", "type", "event_type"):
                if alt_key in target:
                    target["shock_type"] = target.pop(alt_key)
                    break

        # Normalize action targets: LLMs sometimes put "action" instead of "value"
        if int_type == "action" and "value" not in target:
            for alt_key in ("action", "recommendation"):
                if alt_key in target:
                    target["value"] = target.pop(alt_key)
                    break

        intervention = Intervention(
            type=int_type,
            target=target,
            run_periods=int_spec.get("run_periods", 3),
            description=int_spec.get("description", f"Intervention {step+1}"),
        )

        # Dedup check — skip if identical intervention was already run
        dedup_key = (int_type, json.dumps(target, sort_keys=True))
        if dedup_key in all_intervention_keys:
            if verbose:
                print(f"  Proposed: {intervention.type} — {intervention.description}")
                print(f"  [SKIPPED] Duplicate intervention — already tested")
            skip_msg = (
                f"This intervention was already run (duplicate). "
                f"It has been skipped. Please propose a DIFFERENT intervention."
            )
            conversation.append({"role": "user", "content": skip_msg})
            conversation.append({"role": "assistant", "content": json.dumps(
                {"acknowledged": "Will propose a different intervention."})})
            all_interventions.append({
                "step": step + 1,
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
            result = run_market_intervention(
                state_snapshot=state_snapshot,
                agents_snapshot=agents_snapshot,
                base_params=base_params_snapshot,
                shocks=shocks,
                start_period=state.period,
                intervention=intervention,
                rule_based=True,
            )
            result_text = format_result_for_agent(result)
            all_results.append(result)
        except Exception as e:
            result_text = f"INTERVENTION FAILED: {e}"
            if verbose:
                print(f"  [ERROR] {e}")

        if verbose:
            effect = _summarize_effect(result)
            print(f"  Result: {effect}")

        # Feed result back into conversation and ask for hypothesis update
        update_prompt = (
            f"INTERVENTION RESULT:\n{result_text}\n\n"
            f"Update your causal hypothesis based on this result. "
            f"What edges are confirmed, disconfirmed, or still uncertain? "
            f"Respond in JSON with: analysis, edge_updates, current_graph, key_uncertainties."
        )

        conversation.append({"role": "user", "content": update_prompt})

        if dry_run:
            update_response = mock_llm_response("update", step)
            update_raw = json.dumps(update_response)
        else:
            update_raw = call_llm(conversation, api_key, model)
            update_response = parse_json_response(update_raw)
            llm_calls += 1

        conversation.append({"role": "assistant", "content": update_raw})

        all_interventions.append({
            "step": step + 1,
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
        print(f"\nPhase 3: Declaring final causal graph...")

    evidence_summary = build_evidence_summary(all_results, MARKET_VARIABLES)
    latest_hypothesis = _extract_latest_hypothesis(all_interventions)
    intervention_summary = _build_intervention_summary(all_interventions)

    declaration_prompt = build_declaration_prompt(
        domain="market",
        variables=MARKET_VARIABLES,
        current_hypothesis=latest_hypothesis,
        all_interventions_summary=intervention_summary,
        evidence_summary=evidence_summary,
    )

    # Use a truncated conversation for declaration — the full 60+ turn history
    # drowns the model in noise. The evidence summary + latest hypothesis contain
    # all the information needed.
    declaration_conversation = [
        {"role": "system", "content": SYSTEM_PROMPT_MARKET},
        {"role": "user", "content": declaration_prompt},
    ]

    if dry_run:
        declaration = mock_llm_response("declaration", 0)
        declaration_raw = json.dumps(declaration)
    else:
        declaration_raw = call_llm(
            declaration_conversation, api_key, model, max_tokens=4000
        )
        declaration = parse_json_response(declaration_raw)
        llm_calls += 1

    conversation.append({"role": "user", "content": declaration_prompt})
    conversation.append({"role": "assistant", "content": declaration_raw})

    # --- Phase 4: Scoring ---
    if verbose:
        print(f"\nPhase 4: Scoring against ground truth...")

    # Convert declared edges to adjacency matrix
    final_edges = declaration.get("final_graph", [])
    edge_pairs = [(e["from"], e["to"]) for e in final_edges
                  if e.get("confidence") in ("high", "medium", "low")]
    estimated_matrix = edges_to_matrix(edge_pairs, MARKET_VARIABLES)

    scores = score_market_graph(estimated_matrix)

    if verbose:
        print(f"\n{'=' * 60}")
        print("RESULTS")
        print(f"{'=' * 60}")
        print(f"  LLM calls: {llm_calls}")
        print(f"  Interventions completed: {len(all_results)}")
        print(f"  Declared edges: {scores['total_estimated_edges']}")
        print(f"  True edges: {scores['total_true_edges']}")
        print(f"  SHD: {scores['shd']} (extra={scores['shd_extra']}, missing={scores['shd_missing']}, reversed={scores['shd_reversed']})")
        print(f"  Precision: {scores['precision']:.3f}")
        print(f"  Recall: {scores['recall']:.3f}")
        print(f"  F1: {scores['f1']:.3f}")

        # Per-edge analysis
        print(f"\n  Edge analysis:")
        for edge in scores["per_edge"]:
            status_sym = {"correct": "+", "false_positive": "FP", "false_negative": "FN", "reversed": "REV"}
            sym = status_sym.get(edge["status"], "?")
            print(f"    [{sym:>3s}] {edge['from']:20s} -> {edge['to']}")

    # --- Save results ---
    if output_dir:
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        results = {
            "config": {
                "budget": budget,
                "n_warmup": n_warmup,
                "model": model if not dry_run else "dry_run",
                "seed": seed,
                "scenario_id": config["scenario_id"],
                "multi_turn": True,
            },
            "scores": {k: v for k, v in scores.items() if k != "per_edge"},
            "per_edge": scores["per_edge"],
            "declaration": declaration,
            "interventions": all_interventions,
            "observation": observation_response,
            "llm_calls": llm_calls,
            "conversation_turns": len(conversation),
        }

        with open(out_path / "pilot_results.json", "w") as f:
            json.dump(results, f, indent=2, default=str)

        # Save full conversation log for debugging/analysis
        with open(out_path / "conversation_log.json", "w") as f:
            json.dump(conversation, f, indent=2, default=str)

        if verbose:
            print(f"\n  Results saved to: {out_path}")

    return scores


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
                    # Some models return edges as strings
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


# =============================================================================
# Conflict Pilot Runner
# =============================================================================

def run_conflict_pilot(
    budget: int = 30,
    n_warmup: int = 10,
    api_key: str = "",
    model: str = "meta-llama/llama-3.3-70b-instruct",
    dry_run: bool = False,
    output_dir: str = "",
    seed: int = 42,
    verbose: bool = True,
):
    """Run a single-agent causal discovery pilot on the conflict engine.

    Same 5-phase structure as run_pilot() but with conflict-specific:
    setup, warm-up, observation, interventions, declaration, and scoring.
    """
    from conflict.agents_config import create_agents
    from conflict.engine import initialize_state, run_period, aggregate_faction_action
    from conflict.shocks import generate_scenario_configs, apply_shocks

    from causal_discovery.intervention import _conflict_rule_based_recommendations

    # --- Setup ---
    configs = generate_scenario_configs(n_scenarios=1, n_periods=n_warmup + budget * 3, seed=seed)
    config = configs[0]
    agents_config, faction_agents = create_agents(config)
    shocks = config["shocks"]
    state = initialize_state(config)

    if verbose:
        print("=" * 60)
        print(f"CAUSAL DISCOVERY PILOT — Conflict Engine")
        print(f"Budget: {budget} interventions | Warm-up: {n_warmup} periods")
        print(f"Model: {'DRY RUN' if dry_run else model}")
        print(f"Scenario: {config['scenario_id']}")
        print(f"Starting EI: {state.escalation_index:.2f}")
        print("=" * 60)

    # --- Warm-up ---
    if verbose:
        print(f"\nPhase 0: Running {n_warmup} warm-up periods...")

    for t in range(n_warmup):
        apply_shocks(state, shocks, t)
        recommendations = _conflict_rule_based_recommendations(agents_config, state)

        novaris_recs = [r for r in recommendations if r["faction"] == "novaris"]
        tethys_recs = [r for r in recommendations if r["faction"] == "tethys"]
        novaris_action = aggregate_faction_action(novaris_recs, "novaris")
        tethys_action = aggregate_faction_action(tethys_recs, "tethys")

        run_period(state, novaris_action, tethys_action)

    if verbose:
        print(f"  Warm-up complete. EI={state.escalation_index:.2f}, "
              f"Period={state.period}")

    # Save snapshot for intervention rollouts
    state_snapshot = copy.deepcopy(state)
    agents_snapshot = copy.deepcopy(agents_config)

    # Build history data for observation prompt
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

    # --- Initialize multi-turn conversation ---
    conversation = [{"role": "system", "content": SYSTEM_PROMPT_CONFLICT}]

    # --- Phase 1: Observation ---
    if verbose:
        print(f"\nPhase 1: Observing simulation history...")

    history_summary = format_conflict_history(history_data, n_periods=n_warmup)
    observation_prompt = build_observation_prompt(
        domain="conflict",
        history_summary=history_summary,
        variables=CONFLICT_VARIABLES,
    )

    conversation.append({"role": "user", "content": observation_prompt})

    if dry_run:
        observation_response = mock_llm_response("observation", 0, domain="conflict")
        observation_raw = json.dumps(observation_response)
    else:
        observation_raw = call_llm(conversation, api_key, model)
        observation_response = parse_json_response(observation_raw)

    conversation.append({"role": "assistant", "content": observation_raw})

    if verbose:
        n_confident = len(observation_response.get("confident_edges", []))
        n_uncertain = len(observation_response.get("uncertain_edges", []))
        print(f"  Initial hypothesis: {n_confident} confident edges, "
              f"{n_uncertain} uncertain edges")

    # --- Phase 2: Interventions ---
    all_interventions = []
    all_results = []
    all_intervention_keys = set()
    llm_calls = 1  # observation call

    for step in range(budget):
        if verbose:
            print(f"\nIntervention {step+1}/{budget}:")

        proposal_prompt = build_intervention_prompt(
            domain="conflict",
            variables=CONFLICT_VARIABLES,
            current_hypothesis="(see your previous messages above)",
            past_interventions="(see your previous messages above)",
            budget_remaining=budget - step,
            intervention_types=CONFLICT_INTERVENTION_TYPES,
        )

        conversation.append({"role": "user", "content": proposal_prompt})

        if dry_run:
            proposal = mock_llm_response("intervention", step, domain="conflict")
            proposal_raw = json.dumps(proposal)
        else:
            proposal_raw = call_llm(conversation, api_key, model)
            proposal = parse_json_response(proposal_raw)
            llm_calls += 1

        conversation.append({"role": "assistant", "content": proposal_raw})

        # Parse intervention spec — normalize common LLM formatting variations
        int_spec = proposal.get("intervention", proposal)
        target = int_spec.get("target", {})
        int_type = int_spec.get("type", "event")

        # Reject invalid intervention types
        if int_type not in ("action", "trait", "event"):
            if verbose:
                print(f"  Proposed: {int_type} — {int_spec.get('description', '?')}")
                print(f"  [INVALID] Type '{int_type}' is not valid")
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

        # Normalize action targets: LLMs sometimes use "action" instead of "value"
        if int_type == "action" and "value" not in target:
            for alt_key in ("action", "recommendation", "action_name"):
                if alt_key in target:
                    target["value"] = target.pop(alt_key)
                    break

        # Normalize agent_id: LLMs sometimes use "faction" or "agent" instead
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

        # Dedup check
        dedup_key = (int_type, json.dumps(target, sort_keys=True))
        if dedup_key in all_intervention_keys:
            if verbose:
                print(f"  Proposed: {intervention.type} — {intervention.description}")
                print(f"  [SKIPPED] Duplicate intervention — already tested")
            skip_msg = (
                f"This intervention was already run (duplicate). "
                f"It has been skipped. Please propose a DIFFERENT intervention."
            )
            conversation.append({"role": "user", "content": skip_msg})
            conversation.append({"role": "assistant", "content": json.dumps(
                {"acknowledged": "Will propose a different intervention."})})
            all_interventions.append({
                "step": step + 1,
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
            result = run_conflict_intervention(
                state_snapshot=state_snapshot,
                agents_config=agents_snapshot,
                faction_agents=faction_agents,
                shocks=shocks,
                start_period=state.period,
                intervention=intervention,
                rule_based=True,
            )
            result_text = format_result_for_agent(result)
            all_results.append(result)
        except Exception as e:
            result_text = f"INTERVENTION FAILED: {e}"
            if verbose:
                print(f"  [ERROR] {e}")

        if verbose:
            effect = _summarize_effect(result)
            print(f"  Result: {effect}")

        # Feed result back and ask for hypothesis update
        update_prompt = (
            f"INTERVENTION RESULT:\n{result_text}\n\n"
            f"Update your causal hypothesis based on this result. "
            f"What edges are confirmed, disconfirmed, or still uncertain? "
            f"Respond in JSON with: analysis, edge_updates, current_graph, key_uncertainties."
        )

        conversation.append({"role": "user", "content": update_prompt})

        if dry_run:
            update_response = mock_llm_response("update", step, domain="conflict")
            update_raw = json.dumps(update_response)
        else:
            update_raw = call_llm(conversation, api_key, model)
            update_response = parse_json_response(update_raw)
            llm_calls += 1

        conversation.append({"role": "assistant", "content": update_raw})

        all_interventions.append({
            "step": step + 1,
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
        print(f"\nPhase 3: Declaring final causal graph...")

    evidence_summary = build_evidence_summary(all_results, CONFLICT_VARIABLES)
    latest_hypothesis = _extract_latest_hypothesis(all_interventions)
    intervention_summary = _build_intervention_summary(all_interventions)

    declaration_prompt = build_declaration_prompt(
        domain="conflict",
        variables=CONFLICT_VARIABLES,
        current_hypothesis=latest_hypothesis,
        all_interventions_summary=intervention_summary,
        evidence_summary=evidence_summary,
    )

    # Use a truncated conversation for declaration — the full 60+ turn history
    # drowns the model in noise. The evidence summary + latest hypothesis contain
    # all the information needed.
    declaration_conversation = [
        {"role": "system", "content": SYSTEM_PROMPT_CONFLICT},
        {"role": "user", "content": declaration_prompt},
    ]

    if dry_run:
        declaration = mock_llm_response("declaration", 0, domain="conflict")
        declaration_raw = json.dumps(declaration)
    else:
        declaration_raw = call_llm(
            declaration_conversation, api_key, model, max_tokens=4000
        )
        declaration = parse_json_response(declaration_raw)
        llm_calls += 1

    conversation.append({"role": "user", "content": declaration_prompt})
    conversation.append({"role": "assistant", "content": declaration_raw})

    # --- Phase 4: Scoring ---
    if verbose:
        print(f"\nPhase 4: Scoring against ground truth...")

    final_edges = declaration.get("final_graph", [])
    edge_pairs = [(e["from"], e["to"]) for e in final_edges
                  if e.get("confidence") in ("high", "medium", "low")]
    estimated_matrix = edges_to_matrix(edge_pairs, CONFLICT_VARIABLES)

    scores = score_conflict_graph(estimated_matrix)

    if verbose:
        print(f"\n{'=' * 60}")
        print("RESULTS")
        print(f"{'=' * 60}")
        print(f"  LLM calls: {llm_calls}")
        print(f"  Interventions completed: {len(all_results)}")
        print(f"  Declared edges: {scores['total_estimated_edges']}")
        print(f"  True edges: {scores['total_true_edges']}")
        print(f"  SHD: {scores['shd']} (extra={scores['shd_extra']}, missing={scores['shd_missing']}, reversed={scores['shd_reversed']})")
        print(f"  Precision: {scores['precision']:.3f}")
        print(f"  Recall: {scores['recall']:.3f}")
        print(f"  F1: {scores['f1']:.3f}")

        print(f"\n  Edge analysis:")
        for edge in scores["per_edge"]:
            status_sym = {"correct": "+", "false_positive": "FP", "false_negative": "FN", "reversed": "REV"}
            sym = status_sym.get(edge["status"], "?")
            print(f"    [{sym:>3s}] {edge['from']:25s} -> {edge['to']}")

    # --- Save results ---
    if output_dir:
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        results = {
            "config": {
                "domain": "conflict",
                "budget": budget,
                "n_warmup": n_warmup,
                "model": model if not dry_run else "dry_run",
                "seed": seed,
                "scenario_id": config["scenario_id"],
                "multi_turn": True,
            },
            "scores": {k: v for k, v in scores.items() if k != "per_edge"},
            "per_edge": scores["per_edge"],
            "declaration": declaration,
            "interventions": all_interventions,
            "observation": observation_response,
            "llm_calls": llm_calls,
            "conversation_turns": len(conversation),
        }

        with open(out_path / "pilot_results.json", "w") as f:
            json.dump(results, f, indent=2, default=str)

        with open(out_path / "conversation_log.json", "w") as f:
            json.dump(conversation, f, indent=2, default=str)

        if verbose:
            print(f"\n  Results saved to: {out_path}")

    return scores


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Causal Discovery Pilot")
    parser.add_argument("--domain", type=str, choices=["market", "conflict"],
                        default="market", help="Simulation domain")
    parser.add_argument("--budget", type=int, default=30,
                        help="Number of interventions")
    parser.add_argument("--warmup", type=int, default=10,
                        help="Warm-up periods before interventions")
    parser.add_argument("--model", type=str,
                        default="meta-llama/llama-3.3-70b-instruct",
                        help="LLM model for causal modeler agent")
    parser.add_argument("--dry-run", action="store_true",
                        help="Use mock LLM responses (no API calls)")
    parser.add_argument("--output-dir", type=str, default="",
                        help="Output directory (default: auto per domain)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    # Set default output dir based on domain
    output_dir = args.output_dir
    if not output_dir:
        if args.domain == "conflict":
            output_dir = "outputs/causal_discovery/conflict_pilot_runs"
        else:
            output_dir = "outputs/causal_discovery/pilot_runs"

    api_key = ""
    if not args.dry_run:
        api_key = os.getenv("OPENROUTER_API_KEY", "")
        if not api_key:
            # Try loading from .Renviron file (project convention)
            renviron = Path(__file__).parent.parent / ".Renviron"
            if renviron.exists():
                for line in renviron.read_text().splitlines():
                    if line.startswith("OPENROUTER_API_KEY="):
                        api_key = line.split("=", 1)[1].strip()
                        break
        if not api_key:
            try:
                from archive.wargame_forecasting.config import OPENROUTER_API_KEY
                api_key = OPENROUTER_API_KEY
            except ImportError:
                pass
        if not api_key:
            print("[ERROR] OPENROUTER_API_KEY not set. Use --dry-run for testing.")
            sys.exit(1)

    pilot_fn = run_conflict_pilot if args.domain == "conflict" else run_pilot
    pilot_fn(
        budget=args.budget,
        n_warmup=args.warmup,
        api_key=api_key,
        model=args.model,
        dry_run=args.dry_run,
        output_dir=output_dir,
        seed=args.seed,
        verbose=not args.quiet,
    )


if __name__ == "__main__":
    main()
