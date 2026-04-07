"""
Open-Ended Causal Discovery — model discovers BOTH variables AND edges.

Unlike run_pilot.py (which provides the variable list), this variant gives the
model only raw simulation output. The model must identify relevant causal
variables and then discover edges through interventional experiments.

Scoring uses semantic matching to align discovered variables to ground truth,
then computes SHD on the aligned graph.

Usage:
    python -m known_causal_models.causal_discovery.run_pilot_open \
        --domain market --budget 30 --model openai/gpt-oss-120b:nitro

    python -m known_causal_models.causal_discovery.run_pilot_open \
        --domain market --budget 5 --model openai/gpt-oss-120b:nitro --dry-run
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
import re
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from causal_discovery.intervention import (
    Intervention, run_market_intervention, format_result_for_agent,
)
from causal_discovery.ground_truth import (
    MARKET_VARIABLES, score_market_graph, edges_to_matrix,
    get_market_ground_truth, structural_hamming_distance,
)
from causal_discovery.prompts import (
    MARKET_INTERVENTION_TYPES,
    format_market_history,
)
from causal_discovery.prompts_open import (
    SYSTEM_PROMPT_MARKET_OPEN,
    build_observation_prompt_open,
    build_intervention_prompt_open,
    build_update_prompt_open,
    build_declaration_prompt_open,
)
from causal_discovery.run_pilot import (
    call_llm, parse_json_response, _summarize_effect,
    _build_intervention_summary,
    build_evidence_summary,
)


def _format_open_graph(variables: list[dict], edges: dict) -> str:
    """Format the discovered variables and edges as text for prompts."""
    lines = []
    if variables:
        lines.append(f"Identified variables ({len(variables)}):")
        for v in variables:
            lines.append(f"  - {v['id']}: {v.get('description', '')}")
    else:
        lines.append("No variables identified yet.")

    if edges:
        lines.append(f"\nCausal edges ({len(edges)}):")
        for (src, tgt), info in sorted(edges.items()):
            conf = info.get("confidence", "?")
            lines.append(f"  {src} -> {tgt} ({conf})")
    else:
        lines.append("\nNo edges discovered yet.")

    return "\n".join(lines)


def _align_variables_to_ground_truth(
    discovered: list[dict],
    ground_truth_vars: list[str],
    threshold: float = 0.6,
) -> dict[str, str]:
    """Align discovered variable names to ground truth using embedding similarity.

    Embeds each discovered variable as "id: description" and each ground truth
    variable as its name. Uses cosine similarity + Hungarian matching (same
    approach as belief sensitivity paper's semantic node matching).

    Returns mapping: discovered_id -> ground_truth_var (or None if no match).
    """
    try:
        import requests
        from scipy.optimize import linear_sum_assignment
    except ImportError:
        print("  [WARN] scipy not available, falling back to string matching")
        return _align_variables_string_fallback(discovered, ground_truth_vars)

    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        renviron = Path(__file__).parent.parent.parent / ".Renviron"
        if renviron.exists():
            for line in renviron.read_text().splitlines():
                if line.startswith("OPENROUTER_API_KEY="):
                    api_key = line.split("=", 1)[1].strip()
    if not api_key:
        print("  [WARN] No API key for embeddings, falling back to string matching")
        return _align_variables_string_fallback(discovered, ground_truth_vars)

    # Build texts to embed
    disc_texts = []
    for dvar in discovered:
        desc = dvar.get("description", dvar["id"])
        disc_texts.append(f"{dvar['id']}: {desc}")

    gt_texts = []
    for v in ground_truth_vars:
        gt_texts.append(v.replace("_", " "))

    all_texts = disc_texts + gt_texts

    # Embed all at once
    def _embed_batch(texts, key):
        embeddings = []
        for text in texts:
            for attempt in range(3):
                try:
                    resp = requests.post(
                        "https://openrouter.ai/api/v1/embeddings",
                        headers={
                            "Authorization": f"Bearer {key}",
                            "Content-Type": "application/json",
                        },
                        json={"model": "openai/text-embedding-3-large",
                              "input": text[:8000]},
                        timeout=30,
                    )
                    if resp.status_code == 200:
                        embeddings.append(resp.json()["data"][0]["embedding"])
                        break
                    elif resp.status_code == 429:
                        time.sleep(2 ** attempt)
                    else:
                        embeddings.append(None)
                        break
                except Exception:
                    if attempt == 2:
                        embeddings.append(None)
                    time.sleep(1)
        return embeddings

    all_embs = _embed_batch(all_texts, api_key)

    # Check for failures
    if any(e is None for e in all_embs):
        print("  [WARN] Some embeddings failed, falling back to string matching")
        return _align_variables_string_fallback(discovered, ground_truth_vars)

    disc_mat = np.array(all_embs[:len(disc_texts)])
    gt_mat = np.array(all_embs[len(disc_texts):])

    # Cosine similarity
    disc_norm = disc_mat / (np.linalg.norm(disc_mat, axis=1, keepdims=True) + 1e-10)
    gt_norm = gt_mat / (np.linalg.norm(gt_mat, axis=1, keepdims=True) + 1e-10)
    sim = disc_norm @ gt_norm.T

    # Hungarian matching
    cost = 1.0 - sim
    row_ind, col_ind = linear_sum_assignment(cost)

    mapping = {}
    for r, c in zip(row_ind, col_ind):
        did = discovered[r]["id"]
        if sim[r, c] >= threshold:
            mapping[did] = ground_truth_vars[c]
        else:
            mapping[did] = None

    # Any unmatched discovered vars
    for dvar in discovered:
        if dvar["id"] not in mapping:
            mapping[dvar["id"]] = None

    return mapping


def _align_variables_string_fallback(
    discovered: list[dict],
    ground_truth_vars: list[str],
) -> dict[str, str]:
    """Fallback string-based alignment when embeddings aren't available."""
    mapping = {}
    gt_lower = {v: v.lower().replace("_", " ") for v in ground_truth_vars}

    for dvar in discovered:
        did = dvar["id"]
        desc = dvar.get("description", "").lower()
        did_lower = did.lower().replace("_", " ")

        best_match = None
        best_score = 0

        for gt_var, gt_text in gt_lower.items():
            if did_lower == gt_text:
                best_match = gt_var
                best_score = 100
                break

            score = 0
            if gt_text in did_lower or did_lower in gt_text:
                score = 50
            gt_words = set(gt_text.split())
            did_words = set(did_lower.split()) | set(desc.split())
            overlap = len(gt_words & did_words)
            if overlap > 0:
                score = max(score, overlap * 20)

            if score > best_score:
                best_score = score
                best_match = gt_var

        mapping[did] = best_match if best_score >= 20 else None

    return mapping


def _score_open_discovery(
    discovered_vars: list[dict],
    discovered_edges: dict,
    ground_truth_vars: list[str],
    ground_truth_matrix: np.ndarray,
) -> dict:
    """Score the open-ended discovery against ground truth.

    1. Align discovered variables to ground truth via string matching
    2. Map discovered edges to ground truth variable pairs
    3. Compute SHD on the mapped edges
    """
    var_mapping = _align_variables_to_ground_truth(discovered_vars, ground_truth_vars)

    # Build estimated adjacency matrix in ground truth variable space
    n = len(ground_truth_vars)
    var_idx = {v: i for i, v in enumerate(ground_truth_vars)}
    estimated = np.zeros((n, n), dtype=int)

    mapped_edges = 0
    unmapped_edges = 0
    for (src, tgt), info in discovered_edges.items():
        gt_src = var_mapping.get(src)
        gt_tgt = var_mapping.get(tgt)
        if gt_src and gt_tgt and gt_src in var_idx and gt_tgt in var_idx:
            estimated[var_idx[gt_src], var_idx[gt_tgt]] = 1
            mapped_edges += 1
        else:
            unmapped_edges += 1

    shd_result = structural_hamming_distance(estimated, ground_truth_matrix)

    # Variable discovery metrics
    matched_vars = sum(1 for v in var_mapping.values() if v is not None)
    unique_gt_matched = len(set(v for v in var_mapping.values() if v is not None))

    return {
        "variable_mapping": var_mapping,
        "n_discovered_vars": len(discovered_vars),
        "n_ground_truth_vars": len(ground_truth_vars),
        "n_matched_vars": matched_vars,
        "n_unique_gt_matched": unique_gt_matched,
        "var_recall": unique_gt_matched / len(ground_truth_vars),
        "mapped_edges": mapped_edges,
        "unmapped_edges": unmapped_edges,
        **shd_result,
    }


def run_open_pilot(
    budget: int = 30,
    n_warmup: int = 10,
    api_key: str = "",
    model: str = "openai/gpt-oss-120b:nitro",
    dry_run: bool = False,
    output_dir: str = "",
    seed: int = 42,
    verbose: bool = True,
):
    """Run open-ended causal discovery on the market engine.

    The model does NOT receive the variable list — it must discover variables
    from raw simulation output, then discover edges through interventions.
    """
    from market.engine import MarketState, run_period
    from market.shocks import generate_scenario_configs, apply_shocks
    from market.agents_config import create_agents
    from causal_discovery.intervention import _market_rule_based_orders

    # --- Setup (same as run_pilot) ---
    configs = generate_scenario_configs(n_scenarios=1, n_periods=n_warmup + budget * 3, seed=seed)
    config = configs[0]
    agents, base_params = create_agents(config)
    shocks = config["shocks"]
    state = MarketState(agents=agents)

    if verbose:
        print("=" * 60)
        print("OPEN-ENDED CAUSAL DISCOVERY — Market Engine")
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
        print(f"  Warm-up complete. Price=${last_price:.2f}, "
              f"Period={state.period}")

    state_snapshot = copy.deepcopy(state)
    agents_snapshot = copy.deepcopy(agents)
    base_params_snapshot = copy.deepcopy(base_params)

    # Build history (raw data — no variable names given)
    history_data = {
        "price_history": [round(p, 2) for p in state.price_history[-n_warmup:]],
        "volume_history": [v for v in state.volume_history[-n_warmup:]],
    }
    history_summary = format_market_history(history_data, n_periods=n_warmup)

    # --- Initialize conversation ---
    conversation = [{"role": "system", "content": SYSTEM_PROMPT_MARKET_OPEN}]

    # --- Phase 1: Observation (open-ended) ---
    if verbose:
        print(f"\nPhase 1: Observing simulation history (no variable list given)...")

    observation_prompt = build_observation_prompt_open(
        domain="market",
        history_summary=history_summary,
    )
    conversation.append({"role": "user", "content": observation_prompt})

    if dry_run:
        observation_response = {
            "identified_variables": [
                {"id": "clearing_price", "description": "Market clearing price"},
                {"id": "volume", "description": "Units traded per period"},
                {"id": "agent_orders", "description": "Buy and sell orders"},
            ],
            "confident_edges": [
                {"from": "agent_orders", "to": "clearing_price", "confidence": "high"},
            ],
            "uncertain_edges": [],
            "priority_interventions": [],
        }
        observation_raw = json.dumps(observation_response)
    else:
        observation_raw = call_llm(conversation, api_key, model)
        observation_response = parse_json_response(observation_raw)

    conversation.append({"role": "assistant", "content": observation_raw})

    # Extract discovered variables and initial graph
    discovered_vars = observation_response.get("identified_variables", [])
    accumulated_graph = {}
    for e in observation_response.get("confident_edges", []):
        key = (e.get("from", ""), e.get("to", ""))
        if key[0] and key[1]:
            accumulated_graph[key] = {
                "confidence": e.get("confidence", "medium"),
            }

    if verbose:
        print(f"  Discovered {len(discovered_vars)} variables, "
              f"{len(accumulated_graph)} initial edges")

    # --- Phase 2: Interventions ---
    all_interventions = []
    all_results = []
    all_intervention_keys = set()
    llm_calls = 1

    for step in range(budget):
        if verbose:
            print(f"\nIntervention {step+1}/{budget}:")

        graph_text = _format_open_graph(discovered_vars, accumulated_graph)
        proposal_prompt = build_intervention_prompt_open(
            domain="market",
            current_hypothesis=graph_text,
            budget_remaining=budget - step,
            intervention_types=MARKET_INTERVENTION_TYPES,
        )
        conversation.append({"role": "user", "content": proposal_prompt})

        if dry_run:
            proposal = {
                "intervention": {
                    "type": "event",
                    "target": {"shock_type": "supply_disruption", "magnitude": 2.0},
                    "run_periods": 3,
                    "description": "Test supply shock effects",
                },
            }
            proposal_raw = json.dumps(proposal)
        else:
            proposal_raw = call_llm(conversation, api_key, model)
            proposal = parse_json_response(proposal_raw)
            llm_calls += 1

        conversation.append({"role": "assistant", "content": proposal_raw})

        # Parse intervention
        int_spec = proposal.get("intervention", proposal)
        target = int_spec.get("target", {})
        int_type = int_spec.get("type", "event")

        if int_type not in ("action", "trait", "event"):
            if verbose:
                print(f"  [INVALID] Type '{int_type}'")
            conversation.append({"role": "user", "content":
                f"'{int_type}' is not valid. Use: action, trait, event."})
            conversation.append({"role": "assistant", "content": json.dumps(
                {"acknowledged": "Will propose a valid intervention."})})
            continue

        # Normalize event targets
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
            run_periods=int_spec.get("run_periods", 3),
            description=int_spec.get("description", f"Intervention {step+1}"),
        )

        # Dedup
        dedup_key = (int_type, json.dumps(target, sort_keys=True))
        if dedup_key in all_intervention_keys:
            if verbose:
                print(f"  [SKIPPED] Duplicate")
            conversation.append({"role": "user", "content":
                "Duplicate intervention — propose a DIFFERENT one."})
            conversation.append({"role": "assistant", "content": json.dumps(
                {"acknowledged": "Will propose different intervention."})})
            continue
        all_intervention_keys.add(dedup_key)

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

        # Update prompt (open-ended — model can add new variables)
        graph_text = _format_open_graph(discovered_vars, accumulated_graph)
        update_prompt = build_update_prompt_open(
            domain="market",
            current_graph=graph_text,
            intervention_result=result_text,
        )
        conversation.append({"role": "user", "content": update_prompt})

        if dry_run:
            update_response = {
                "analysis": "Test result",
                "identified_variables": discovered_vars,
                "current_graph": [
                    {"from": k[0], "to": k[1], "confidence": v["confidence"]}
                    for k, v in accumulated_graph.items()
                ],
            }
            update_raw = json.dumps(update_response)
        else:
            update_raw = call_llm(conversation, api_key, model)
            update_response = parse_json_response(update_raw)
            llm_calls += 1

        conversation.append({"role": "assistant", "content": update_raw})

        # Update discovered variables (model may add new ones)
        new_vars = update_response.get("identified_variables", [])
        if new_vars and isinstance(new_vars, list):
            # Merge: keep existing, add new
            existing_ids = {v["id"] for v in discovered_vars}
            for nv in new_vars:
                if isinstance(nv, dict) and nv.get("id") and nv["id"] not in existing_ids:
                    discovered_vars.append(nv)
                    existing_ids.add(nv["id"])

        # Replace accumulated graph from model's full response
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
                    }

        if verbose:
            diff = len(accumulated_graph) - prev_size
            sign = "+" if diff >= 0 else ""
            print(f"  Variables: {len(discovered_vars)}, "
                  f"Edges: {len(accumulated_graph)} ({sign}{diff})")

        all_interventions.append({
            "step": step + 1,
            "intervention": {
                "type": intervention.type,
                "target": intervention.target,
                "description": intervention.description,
            },
            "result_summary": _summarize_effect(result) if result else "FAILED",
            "hypothesis_update": update_response,
            "n_variables": len(discovered_vars),
            "accumulated_graph_size": len(accumulated_graph),
        })

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
                },
                "step": step + 1,
                "discovered_vars": discovered_vars,
                "accumulated_graph": {
                    f"{k[0]}|{k[1]}": v for k, v in accumulated_graph.items()
                },
                "interventions": all_interventions,
                "conversation": conversation,
                "llm_calls": llm_calls,
            }
            (ckpt_path / "checkpoint.json").write_text(
                json.dumps(ckpt, indent=2, default=str), encoding="utf-8")

    # --- Phase 3: Final Declaration ---
    if verbose:
        print(f"\nPhase 3: Declaring final causal model...")
        print(f"  {len(discovered_vars)} variables, {len(accumulated_graph)} edges")

    evidence_summary = build_evidence_summary(all_results, MARKET_VARIABLES)
    graph_text = _format_open_graph(discovered_vars, accumulated_graph)
    intervention_summary = _build_intervention_summary(all_interventions)

    declaration_prompt = build_declaration_prompt_open(
        domain="market",
        current_hypothesis=graph_text,
        all_interventions_summary=intervention_summary,
        evidence_summary=evidence_summary,
    )

    declaration_conversation = [
        {"role": "system", "content": SYSTEM_PROMPT_MARKET_OPEN},
        {"role": "user", "content": declaration_prompt},
    ]

    if dry_run:
        declaration = {
            "identified_variables": discovered_vars,
            "final_graph": [
                {"from": k[0], "to": k[1], "confidence": v["confidence"]}
                for k, v in accumulated_graph.items()
            ],
        }
        declaration_raw = json.dumps(declaration)
    else:
        declaration_raw = call_llm(
            declaration_conversation, api_key, model, max_tokens=8000
        )
        declaration = parse_json_response(declaration_raw)
        llm_calls += 1

    # --- Phase 4: Scoring ---
    if verbose:
        print(f"\nPhase 4: Scoring against ground truth...")

    # Use declared graph if available, else accumulated
    final_vars = declaration.get("identified_variables", discovered_vars)
    final_edges_list = declaration.get("final_graph", [])
    final_edges = {}
    for e in final_edges_list:
        if isinstance(e, dict):
            src = e.get("from", "")
            tgt = e.get("to", "")
            if src and tgt:
                final_edges[(src, tgt)] = {"confidence": e.get("confidence", "medium")}

    gt_matrix = get_market_ground_truth()
    scores = _score_open_discovery(
        final_vars, final_edges, MARKET_VARIABLES, gt_matrix
    )

    # Compute precision/recall/F1 from SHD components
    tp = int(gt_matrix.sum()) - scores["missing"]
    fp = scores["extra"]
    fn = scores["missing"]
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    if verbose:
        print(f"\n{'='*60}")
        print("RESULTS (Open-Ended)")
        print(f"{'='*60}")
        print(f"  LLM calls: {llm_calls}")
        print(f"  Interventions completed: "
              f"{sum(1 for i in all_interventions if i['result_summary'] != 'FAILED')}")
        print(f"\n  Variables discovered: {len(final_vars)}")
        print(f"  Variables matched to ground truth: {scores['n_unique_gt_matched']}"
              f"/{scores['n_ground_truth_vars']}")
        print(f"  Variable recall: {scores['var_recall']:.3f}")
        print(f"\n  Edges declared: {len(final_edges)}")
        print(f"  Edges mapped to GT space: {scores['mapped_edges']}")
        print(f"  Edges unmapped: {scores['unmapped_edges']}")
        print(f"\n  SHD: {scores['shd']} "
              f"(extra={scores['extra']}, missing={scores['missing']}, "
              f"reversed={scores['reversed']})")
        print(f"  Precision: {precision:.3f}")
        print(f"  Recall: {recall:.3f}")
        print(f"  F1: {f1:.3f}")

        print(f"\n  Variable mapping:")
        for did, gt_var in scores["variable_mapping"].items():
            status = f"-> {gt_var}" if gt_var else "-> [UNMATCHED]"
            print(f"    {did:30s} {status}")

    # --- Save results ---
    if output_dir:
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        results = {
            "config": {
                "domain": "market",
                "mode": "open_ended",
                "budget": budget,
                "n_warmup": n_warmup,
                "model": model if not dry_run else "dry_run",
                "seed": seed,
            },
            "scores": {
                "shd": scores["shd"],
                "extra": scores["extra"],
                "missing": scores["missing"],
                "reversed": scores["reversed"],
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "n_discovered_vars": len(final_vars),
                "n_gt_vars": scores["n_ground_truth_vars"],
                "n_matched_vars": scores["n_unique_gt_matched"],
                "var_recall": scores["var_recall"],
                "mapped_edges": scores["mapped_edges"],
                "unmapped_edges": scores["unmapped_edges"],
            },
            "variable_mapping": scores["variable_mapping"],
            "discovered_variables": final_vars,
            "declaration": declaration,
            "interventions": all_interventions,
            "observation": observation_response,
            "llm_calls": llm_calls,
            "conversation_turns": len(conversation),
        }

        with open(out_path / "pilot_results_open.json", "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, default=str)

        with open(out_path / "conversation_log.json", "w", encoding="utf-8") as f:
            json.dump(conversation, f, indent=2, default=str)

        if verbose:
            print(f"\n  Results saved to: {out_path}")


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Open-Ended Causal Discovery (variables + edges)")
    parser.add_argument("--domain", type=str, choices=["market"],
                        default="market", help="Simulation domain (market only for now)")
    parser.add_argument("--budget", type=int, default=30)
    parser.add_argument("--warmup", type=int, default=10)
    parser.add_argument("--model", type=str,
                        default="openai/gpt-oss-120b:nitro")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output-dir", type=str, default="")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    output_dir = args.output_dir
    if not output_dir:
        output_dir = "outputs/causal_discovery/single_agent/market_open"

    api_key = ""
    if not args.dry_run:
        api_key = os.getenv("OPENROUTER_API_KEY", "")
        if not api_key:
            renviron = Path(__file__).parent.parent.parent / ".Renviron"
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

    run_open_pilot(
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
