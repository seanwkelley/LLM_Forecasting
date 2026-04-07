"""
Causal Discovery Pilot — Windowed conversation variant.

Same pipeline as run_pilot.py but uses a sliding conversation window instead
of the full conversation history. Older interventions are summarized as
one-liners; only the most recent N steps are kept as full messages.

This tests whether models can reason effectively with truncated context,
and may improve performance for models that degrade on long conversations.

Usage:
    python -m known_causal_models.causal_discovery.run_pilot_windowed \
        --domain market --budget 30 --model openai/gpt-oss-120b:nitro --window 3
"""

from __future__ import annotations

import sys
import io
if sys.stdout.encoding and sys.stdout.encoding.lower().startswith("cp"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import argparse
import copy
import json
import os
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from causal_discovery.intervention import (
    Intervention, run_market_intervention, format_result_for_agent,
)
from causal_discovery.ground_truth import (
    MARKET_VARIABLES, score_market_graph, get_market_ground_truth,
    edges_to_matrix, structural_hamming_distance,
)
from causal_discovery.prompts import (
    SYSTEM_PROMPT_MARKET, MARKET_INTERVENTION_TYPES,
    build_observation_prompt, build_intervention_prompt,
    build_declaration_prompt, build_evidence_summary,
    format_market_history,
)
from causal_discovery.run_pilot import (
    call_llm, parse_json_response, _summarize_effect,
    _format_accumulated_graph, _build_intervention_summary,
)


def _build_windowed_conversation(
    system_prompt: str,
    observation_msgs: list[dict],  # user + assistant from phase 1
    all_step_msgs: list[list[dict]],  # list of per-step message groups
    window: int = 3,
) -> list[dict]:
    """Build a conversation with only the last `window` steps as full messages.

    Returns [system, observation_user, observation_assistant, ...last N steps...].
    Older steps are NOT included — they're covered by the past_interventions
    summary and accumulated graph in the proposal prompt.
    """
    conv = [{"role": "system", "content": system_prompt}]

    # Always include observation exchange
    conv.extend(observation_msgs)

    # Only include last `window` steps
    recent = all_step_msgs[-window:] if len(all_step_msgs) > window else all_step_msgs
    for step_msgs in recent:
        conv.extend(step_msgs)

    return conv


def run_windowed_pilot(
    budget: int = 30,
    n_warmup: int = 10,
    api_key: str = "",
    model: str = "openai/gpt-oss-120b:nitro",
    dry_run: bool = False,
    output_dir: str = "",
    seed: int = 42,
    window: int = 3,
    verbose: bool = True,
):
    """Run causal discovery with a sliding conversation window.

    Instead of passing the full 60+ message conversation, only the last
    `window` intervention steps are included as full messages. Older
    interventions appear in the compact past_interventions summary.
    """
    from market.engine import MarketState, run_period
    from market.shocks import generate_scenario_configs, apply_shocks
    from market.agents_config import create_agents
    from causal_discovery.intervention import _market_rule_based_orders

    # --- Setup (same as run_pilot) ---
    configs = generate_scenario_configs(n_scenarios=1,
                                         n_periods=n_warmup + budget * 3, seed=seed)
    config = configs[0]
    agents, base_params = create_agents(config)
    shocks = config["shocks"]
    state = MarketState(agents=agents)

    if verbose:
        print("=" * 60)
        print(f"CAUSAL DISCOVERY PILOT — Windowed (window={window})")
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
        last_price = state.price_history[-1] if state.price_history else 0
        print(f"  Warm-up complete. Price=${last_price:.2f}, Period={state.period}")

    state_snapshot = copy.deepcopy(state)
    agents_snapshot = copy.deepcopy(agents)
    base_params_snapshot = copy.deepcopy(base_params)

    history_data = {
        "price_history": [round(p, 2) for p in state.price_history],
        "volume_history": list(state.volume_history),
        "fundamental_history": [round(f, 2) for f in state.fundamental_history],
    }

    # --- Phase 1: Observation ---
    if verbose:
        print(f"\nPhase 1: Observing simulation history...")

    history_summary = format_market_history(history_data, n_periods=n_warmup)
    observation_prompt = build_observation_prompt(
        domain="market",
        history_summary=history_summary,
        variables=MARKET_VARIABLES,
    )

    obs_user_msg = {"role": "user", "content": observation_prompt}
    init_conv = [{"role": "system", "content": SYSTEM_PROMPT_MARKET}, obs_user_msg]

    if dry_run:
        observation_response = {"confident_edges": [], "uncertain_edges": [],
                                 "priority_interventions": []}
        observation_raw = json.dumps(observation_response)
    else:
        observation_raw = call_llm(init_conv, api_key, model)
        observation_response = parse_json_response(observation_raw)

    obs_assistant_msg = {"role": "assistant", "content": observation_raw}
    observation_msgs = [obs_user_msg, obs_assistant_msg]

    if verbose:
        n_confident = len(observation_response.get("confident_edges", []))
        n_uncertain = len(observation_response.get("uncertain_edges", []))
        print(f"  Initial hypothesis: {n_confident} confident edges, "
              f"{n_uncertain} uncertain edges")

    # --- Phase 2: Interventions (windowed) ---
    all_interventions = []
    all_results = []
    all_intervention_keys = set()
    all_step_msgs = []  # list of per-step message groups
    llm_calls = 1

    # Accumulated graph
    accumulated_graph = {}
    for e in observation_response.get("confident_edges", []):
        key = (e.get("from", ""), e.get("to", ""))
        accumulated_graph[key] = {
            "confidence": e.get("confidence", "medium"),
            "reasoning": e.get("reasoning", ""),
        }

    completed_interventions = 0
    consecutive_duplicates = 0
    max_consecutive_duplicates = 5

    while completed_interventions < budget and consecutive_duplicates < max_consecutive_duplicates:
        step = completed_interventions
        if verbose:
            print(f"\nIntervention {step+1}/{budget}:")

        # Build compact summary of past interventions
        past_summary_lines = []
        for intv in all_interventions:
            inv = intv.get("intervention", {})
            result = intv.get("result_summary", "")
            past_summary_lines.append(
                f"  {inv.get('type','?')}: {inv.get('description','?')[:80]} "
                f"-> {result[:60]}"
            )
        past_summary = "\n".join(past_summary_lines) if past_summary_lines else "None yet."

        proposal_prompt = build_intervention_prompt(
            domain="market",
            variables=MARKET_VARIABLES,
            current_hypothesis=_format_accumulated_graph(accumulated_graph),
            past_interventions=past_summary,
            budget_remaining=budget - step,
            intervention_types=MARKET_INTERVENTION_TYPES,
        )

        # Build windowed conversation for this call
        proposal_msg = {"role": "user", "content": proposal_prompt}
        conv = _build_windowed_conversation(
            SYSTEM_PROMPT_MARKET, observation_msgs, all_step_msgs, window)
        conv.append(proposal_msg)

        if dry_run:
            proposal = {"intervention": {"type": "event",
                        "target": {"shock_type": "supply_disruption", "magnitude": 2.0},
                        "description": "Test supply shock"}}
            proposal_raw = json.dumps(proposal)
        else:
            proposal_raw = call_llm(conv, api_key, model)
            proposal = parse_json_response(proposal_raw)
            llm_calls += 1

        proposal_assistant_msg = {"role": "assistant", "content": proposal_raw}

        # Parse intervention
        int_spec = proposal.get("intervention", proposal)
        target = int_spec.get("target", {})
        int_type = int_spec.get("type", "event")

        if int_type not in ("action", "trait", "event"):
            if verbose:
                print(f"  [INVALID] Type '{int_type}'")
            consecutive_duplicates += 1
            continue

        # Normalize targets
        if int_type == "event" and "shock_type" not in target:
            for alt_key in ("event", "shock", "type", "event_type"):
                if alt_key in target:
                    target["shock_type"] = target.pop(alt_key)
                    break
        if int_type == "action" and "value" not in target:
            for alt_key in ("action", "recommendation"):
                if alt_key in target:
                    target["value"] = target.pop(alt_key)
                    break

        intervention = Intervention(
            type=int_type,
            target=target,
            run_periods=3,
            description=int_spec.get("description", f"Intervention {step+1}"),
        )

        # Dedup check
        dedup_key = (int_type, json.dumps(target, sort_keys=True))
        if dedup_key in all_intervention_keys:
            if verbose:
                print(f"  Proposed: {intervention.type} — {intervention.description}")
                print(f"  [DUPLICATE] Already tested")
            consecutive_duplicates += 1
            continue
        all_intervention_keys.add(dedup_key)
        consecutive_duplicates = 0

        if verbose:
            print(f"  Proposed: {intervention.type} — {intervention.description}")

        # Execute
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
            print(f"  Result: {_summarize_effect(result)}")

        # Update prompt
        graph_text = _format_accumulated_graph(accumulated_graph)
        var_list = ", ".join(MARKET_VARIABLES)
        update_prompt = (
            f"GRAPH UPDATE (do NOT propose a new intervention — just update your graph).\n\n"
            f"INTERVENTION RESULT:\n{result_text}\n\n"
            f"YOUR CURRENT CAUSAL GRAPH:\n{graph_text}\n\n"
            f"Based on this result, output your COMPLETE updated causal graph. "
            f"Include ALL edges you currently believe exist (not just changes).\n\n"
            f"Note: If this intervention showed that a variable did NOT change when "
            f"your graph predicts it should have, consider removing or downgrading "
            f"that edge. Edges should have supporting evidence — but only remove an "
            f"edge if you have clear disconfirming evidence, not just absence of signal.\n\n"
            f"The variables are: {var_list}\n\n"
            f"Respond in JSON with:\n"
            f'{{"analysis": "brief interpretation of this result",\n'
            f' "current_graph": [{{"from": "var1", "to": "var2", "confidence": "high/medium/low"}}, ...],\n'
            f' "key_uncertainties": ["..."]}}'
        )

        update_user_msg = {"role": "user", "content": update_prompt}

        # Build windowed conversation for update call
        conv2 = _build_windowed_conversation(
            SYSTEM_PROMPT_MARKET, observation_msgs, all_step_msgs, window)
        conv2.extend([proposal_msg, proposal_assistant_msg, update_user_msg])

        if dry_run:
            update_response = {"analysis": "test", "current_graph": [], "key_uncertainties": []}
            update_raw = json.dumps(update_response)
        else:
            update_raw = call_llm(conv2, api_key, model)
            update_response = parse_json_response(update_raw)
            llm_calls += 1

        update_assistant_msg = {"role": "assistant", "content": update_raw}

        # Save this step's messages for future windowing
        step_msgs = [proposal_msg, proposal_assistant_msg,
                     update_user_msg, update_assistant_msg]
        all_step_msgs.append(step_msgs)

        # Replace accumulated graph
        new_graph = update_response.get("current_graph", [])
        prev_size = len(accumulated_graph)
        if new_graph and isinstance(new_graph, list):
            accumulated_graph = {}
            for e in new_graph:
                if not isinstance(e, dict):
                    continue
                src = e.get("from", "")
                tgt = e.get("to", "")
                if src and tgt:
                    accumulated_graph[(src, tgt)] = {
                        "confidence": e.get("confidence", "medium"),
                        "reasoning": e.get("reasoning", ""),
                    }

        if verbose:
            diff = len(accumulated_graph) - prev_size
            sign = "+" if diff >= 0 else ""
            print(f"  Graph: {len(accumulated_graph)} edges ({sign}{diff} from last step)")

        all_interventions.append({
            "step": step + 1,
            "intervention": {
                "type": intervention.type,
                "target": intervention.target,
                "description": intervention.description,
            },
            "result_summary": _summarize_effect(result) if result else "FAILED",
            "hypothesis_update": update_response,
            "accumulated_graph_size": len(accumulated_graph),
        })

        completed_interventions += 1

        # Checkpoint
        if output_dir:
            ckpt_path = Path(output_dir)
            ckpt_path.mkdir(parents=True, exist_ok=True)
            ckpt = {
                "config": {
                    "domain": "market",
                    "budget": budget,
                    "model": model if not dry_run else "dry_run",
                    "seed": seed,
                    "window": window,
                    "variant": "windowed",
                },
                "step": completed_interventions,
                "accumulated_graph": {f"{k[0]}|{k[1]}": v for k, v in accumulated_graph.items()},
                "interventions": all_interventions,
                "observation": observation_response,
                "llm_calls": llm_calls,
            }
            (ckpt_path / "checkpoint.json").write_text(
                json.dumps(ckpt, indent=2, default=str), encoding="utf-8")

    if consecutive_duplicates >= max_consecutive_duplicates and verbose:
        print(f"\n  [STOPPED] {max_consecutive_duplicates} consecutive duplicates")

    # --- Phase 3: Final Declaration ---
    if verbose:
        print(f"\nPhase 3: Declaring final causal graph...")
        print(f"  Completed {completed_interventions}/{budget} interventions")
        print(f"  Accumulated graph has {len(accumulated_graph)} edges")

    evidence_summary = build_evidence_summary(all_results, MARKET_VARIABLES)
    latest_hypothesis = _format_accumulated_graph(accumulated_graph)
    intervention_summary = _build_intervention_summary(all_interventions)

    declaration_prompt = build_declaration_prompt(
        domain="market",
        variables=MARKET_VARIABLES,
        current_hypothesis=latest_hypothesis,
        all_interventions_summary=intervention_summary,
        evidence_summary=evidence_summary,
    )

    # Declaration uses a fresh conversation (just system + declaration prompt)
    declaration_conversation = [
        {"role": "system", "content": SYSTEM_PROMPT_MARKET},
        {"role": "user", "content": declaration_prompt},
    ]

    if dry_run:
        declaration = {"final_graph": [], "per_variable": {}}
        declaration_raw = json.dumps(declaration)
    else:
        declaration_raw = call_llm(
            declaration_conversation, api_key, model, max_tokens=8000)
        declaration = parse_json_response(declaration_raw)
        llm_calls += 1

    # --- Phase 4: Scoring ---
    if verbose:
        print(f"\nPhase 4: Scoring against ground truth...")

    final_edges = declaration.get("final_graph", [])
    edge_list = []
    for e in final_edges:
        if isinstance(e, dict) and "from" in e and "to" in e:
            edge_list.append((e["from"], e["to"]))

    gt = get_market_ground_truth()
    estimated = edges_to_matrix(edge_list, MARKET_VARIABLES)
    scores = structural_hamming_distance(estimated, gt)

    tp = len(edge_list)
    for src, tgt in edge_list:
        from causal_discovery.ground_truth import MARKET_VAR_INDEX
        si = MARKET_VAR_INDEX.get(src)
        ti = MARKET_VAR_INDEX.get(tgt)
        if si is not None and ti is not None and gt[si, ti] == 0:
            tp -= 1

    true_edges = int(gt.sum())
    est_edges = int(estimated.sum())
    tp = true_edges - scores["missing"]
    fp = scores["extra"]
    fn = scores["missing"]
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    scores.update({
        "precision": precision, "recall": recall, "f1": f1,
        "true_positives": tp, "false_positives": fp, "false_negatives": fn,
        "total_true_edges": true_edges, "total_estimated_edges": est_edges,
        "total_possible_edges": len(MARKET_VARIABLES) ** 2,
    })

    # Per-edge analysis
    per_edge = []
    from causal_discovery.ground_truth import MARKET_VAR_INDEX
    est_set = set(edge_list)
    gt_set = set()
    for i in range(len(MARKET_VARIABLES)):
        for j in range(len(MARKET_VARIABLES)):
            if gt[i, j] == 1:
                gt_set.add((MARKET_VARIABLES[i], MARKET_VARIABLES[j]))

    for e in sorted(gt_set | est_set):
        in_gt = e in gt_set
        in_est = e in est_set
        if in_gt and in_est:
            status = "correct"
        elif in_est and not in_gt:
            status = "false_positive"
        elif in_gt and not in_est:
            status = "false_negative"
        else:
            continue
        per_edge.append({"from": e[0], "to": e[1], "ground_truth": int(in_gt),
                         "estimated": int(in_est), "status": status})

    if verbose:
        print(f"\n{'='*60}")
        print("RESULTS (Windowed)")
        print(f"{'='*60}")
        print(f"  Window size: {window}")
        print(f"  LLM calls: {llm_calls}")
        print(f"  Interventions completed: {completed_interventions}")
        print(f"  Declared edges: {est_edges}")
        print(f"  True edges: {true_edges}")
        print(f"  SHD: {scores['shd']} (extra={scores['extra']}, "
              f"missing={scores['missing']}, reversed={scores['reversed']})")
        print(f"  Precision: {precision:.3f}")
        print(f"  Recall: {recall:.3f}")
        print(f"  F1: {f1:.3f}")

        print(f"\n  Edge analysis:")
        for edge in per_edge:
            sym = {"correct": "  +", "false_positive": " FP",
                   "false_negative": " FN", "reversed": "REV"}.get(edge["status"], "  ?")
            print(f"    [{sym}] {edge['from']:25s} -> {edge['to']}")

    # --- Save results ---
    if output_dir:
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        results = {
            "config": {
                "domain": "market",
                "budget": budget,
                "n_warmup": n_warmup,
                "model": model if not dry_run else "dry_run",
                "seed": seed,
                "window": window,
                "variant": "windowed",
            },
            "scores": scores,
            "per_edge": per_edge,
            "declaration": declaration,
            "interventions": all_interventions,
            "observation": observation_response,
            "llm_calls": llm_calls,
            "conversation_turns": sum(len(s) for s in all_step_msgs) + 2,
        }

        with open(out_path / "pilot_results.json", "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, default=str)

        if verbose:
            print(f"\n  Results saved to: {out_path}")


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Causal Discovery Pilot — Windowed Conversation")
    parser.add_argument("--domain", type=str, choices=["market"],
                        default="market")
    parser.add_argument("--budget", type=int, default=30)
    parser.add_argument("--warmup", type=int, default=10)
    parser.add_argument("--model", type=str,
                        default="openai/gpt-oss-120b:nitro")
    parser.add_argument("--window", type=int, default=3,
                        help="Number of recent intervention steps to keep as full messages")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output-dir", type=str, default="")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    output_dir = args.output_dir
    if not output_dir:
        output_dir = f"outputs/causal_discovery/single_agent/market_windowed_w{args.window}"

    api_key = ""
    if not args.dry_run:
        api_key = os.getenv("OPENROUTER_API_KEY", "")
        if not api_key:
            renviron = Path(__file__).parent.parent.parent / ".Renviron"
            if renviron.exists():
                for line in renviron.read_text().splitlines():
                    if line.startswith("OPENROUTER_API_KEY="):
                        api_key = line.split("=", 1)[1].strip()
        if not api_key:
            print("[ERROR] OPENROUTER_API_KEY not set. Use --dry-run for testing.")
            sys.exit(1)

    run_windowed_pilot(
        budget=args.budget,
        n_warmup=args.warmup,
        api_key=api_key,
        model=args.model,
        dry_run=args.dry_run,
        output_dir=output_dir,
        seed=args.seed,
        window=args.window,
        verbose=not args.quiet,
    )


if __name__ == "__main__":
    main()
