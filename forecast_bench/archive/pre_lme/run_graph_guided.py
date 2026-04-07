#!/usr/bin/env python3
"""
Graph-Guided Probing — Tests whether explicit path-tracing prompts improve
structural grounding (specifically edge betweenness sensitivity).

Reuses existing shared stages (DAGs + probes) from 70b_one_turn.
Only re-runs Stage 3 with a modified prompt that asks the model to:
1. Trace the causal path(s) from the probed element to the outcome
2. Identify which intermediate nodes are affected
3. Then update the probability

Usage:
    python -m forecast_bench.run_graph_guided --max-questions 100 --resume
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from forecast_bench.llm_client import LLMClient, parse_json_response
from forecast_bench.prompts_causal import (
    _format_network_context,
    PROBE_CATEGORIES,
)
from forecast_bench.run_sensitivity import (
    CAUSAL_CSV_FIELDS,
    save_causal_sensitivity_row,
    save_question_json,
    get_completed_questions,
)

BASE = Path(__file__).parent.parent
CAUSAL_DIR = BASE / "outputs" / "sensitivity" / "causal"
SOURCE_DIR = CAUSAL_DIR / "70b_one_turn"
OUTPUT_DIR = CAUSAL_DIR / "70b_graph_guided_v2"

MODEL_ID = "meta-llama/llama-3.3-70b-instruct"

# ── Graph-guided prompt ────────────────────────────────────────────────────

GRAPH_GUIDED_SYSTEM = """\
You are an expert forecaster updating your estimate in light of new information \
about your causal model.

When presented with a challenge, you MUST follow this structured process:

STEP 1 — PATH TRACING: Identify ALL causal paths from the challenged element \
to the outcome node. List each path explicitly (e.g., A → B → C → outcome).

STEP 2 — IMPACT PROPAGATION: For each path, explain how the challenge would \
propagate along that specific chain of causal links. Which intermediate nodes \
are affected? How does the effect compound or attenuate?

STEP 3 — STRUCTURAL ASSESSMENT: Determine whether the challenged element is on \
a critical path (the only route between some factor and the outcome) or a \
redundant path (alternative routes exist). Critical paths warrant larger updates.

STEP 4 — UPDATE: Based on your path analysis, provide your updated probability.

Respond with ONLY valid JSON. No other text."""


def build_graph_guided_prompt(
    question: str,
    initial_probability: float,
    nodes: list[dict],
    edges: list[dict],
    probe: dict,
    probe_target: dict,
) -> str:
    """Build Stage 3 prompt with explicit path-tracing instructions."""
    network_context = _format_network_context(nodes, edges)
    probe_type = probe.get("probe_type", "")
    target_id = probe.get("target_id", "")
    probe_text = probe.get("probe_text", "")

    category = PROBE_CATEGORIES.get(probe_type, "structural")
    if category == "node":
        challenge_desc = f"a challenge to the causal factor '{target_id}'"
    elif category == "edge":
        challenge_desc = f"a challenge to the causal link '{target_id}'"
    else:
        challenge_desc = "a structural challenge to your causal model"

    return f"""\
You previously forecasted the following question:

"{question}"

Your initial estimate: probability = {initial_probability:.2f}

Your causal network:
{network_context}

Now consider the following ({challenge_desc}):

"{probe_text}"

Follow this structured reasoning process:

1. PATH TRACING: List every causal path from '{target_id}' to the outcome node. \
Write each path as: node1 → node2 → ... → outcome.

2. IMPACT PROPAGATION: For each path you identified, explain how this challenge \
propagates step by step along the causal chain.

3. STRUCTURAL ASSESSMENT: Is '{target_id}' on the ONLY path between any factor \
and the outcome (critical), or do alternative routes exist (redundant)?

4. UPDATED PROBABILITY: Based on your path analysis above, provide your update.

Respond as JSON:
{{
  "paths_affected": ["path1 → path2 → outcome", ...],
  "n_paths_affected": <integer>,
  "is_critical_path": true or false,
  "updated_probability": <float between 0.01 and 0.99>,
  "shift_direction": "increased" or "decreased" or "unchanged",
  "reasoning": "<your step-by-step path tracing analysis>"
}}

Requirements:
- updated_probability must be between 0.01 and 0.99.
- You MUST list the specific paths before giving your probability update.
- If the element is on a critical path with no alternative routes, update substantially.
- If alternative paths exist, the update should be smaller."""


def _get_api_key() -> str:
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        try:
            from forecasting.config import OPENROUTER_API_KEY
            api_key = OPENROUTER_API_KEY
        except ImportError:
            pass
    if not api_key:
        try:
            from archive.wargame_forecasting.config import OPENROUTER_API_KEY
            api_key = OPENROUTER_API_KEY
        except ImportError:
            pass
    return api_key


def main():
    parser = argparse.ArgumentParser(description="Graph-guided probing experiment")
    parser.add_argument("--max-questions", type=int, default=100)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    api_key = _get_api_key()
    if not api_key:
        print("[ERROR] OPENROUTER_API_KEY not set.")
        sys.exit(1)

    print(f"\n{'='*60}")
    print("GRAPH-GUIDED PROBING (Llama 70B)")
    print(f"{'='*60}")
    print(f"Source: {SOURCE_DIR}")
    print(f"Output: {OUTPUT_DIR}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results_dir = OUTPUT_DIR / "question_results"
    results_dir.mkdir(exist_ok=True)

    client = LLMClient(
        api_key=api_key, model=MODEL_ID,
        temperature=0.7, max_tokens=2000,
    )

    # Load source question files
    source_qdir = SOURCE_DIR / "question_results"
    if not source_qdir.exists():
        print(f"[ERROR] No source data at {source_qdir}")
        sys.exit(1)

    source_files = sorted(source_qdir.glob("q_*.json"))
    print(f"Source questions: {len(source_files)}")

    completed = set()
    if args.resume:
        completed = get_completed_questions(OUTPUT_DIR)
        if completed:
            print(f"Resuming: {len(completed)} questions already complete")

    csv_path = OUTPUT_DIR / "sensitivity_results.csv"
    csv_mode = "a" if args.resume and csv_path.exists() else "w"

    n_processed = 0

    with open(csv_path, csv_mode, newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CAUSAL_CSV_FIELDS)
        if csv_mode == "w":
            writer.writeheader()

        for q_idx, src_file in enumerate(source_files):
            if q_idx >= args.max_questions:
                break

            src_data = json.loads(src_file.read_text(encoding="utf-8"))
            qid = src_data["question_id"]

            if qid in completed:
                continue

            question_text = src_data["question_text"]
            initial_prob = src_data["initial_probability"]
            nodes = src_data["nodes"]
            edges = src_data["edges"]
            net_analysis = src_data["network_analysis"]

            # Use ALL probes from the original probe_results (includes strengthen
            # variants not in probe_targets). Build probe/target pairs from them.
            orig_results = src_data.get("probe_results", [])
            if not orig_results:
                continue

            # Build matched probe + target dicts from original results
            all_probes = []
            all_targets = []
            for pr in orig_results:
                all_probes.append({
                    "probe_text": pr.get("probe_text", pr.get("raw_response", "")),
                    "probe_type": pr.get("probe_type", ""),
                    "target_id": pr.get("target_id", ""),
                    "generated": pr.get("probe_generated", True),
                })
                all_targets.append({
                    "probe_type": pr.get("probe_type", ""),
                    "target_id": pr.get("target_id", ""),
                    "target_type": pr.get("target_type", pr.get("probe_category", "")),
                    "importance": pr.get("target_importance", 0),
                    "centrality_rank": pr.get("target_centrality_rank", 0),
                    "on_critical_path": pr.get("target_on_critical_path", False),
                    "description": pr.get("description", pr.get("target_id", "")),
                })

            print(f"  [{q_idx+1}/{min(len(source_files), args.max_questions)}] {qid[:40]}... "
                  f"({len(all_probes)} probes) ", end="")

            # Re-run Stage 3 only with graph-guided prompt
            probe_results = []

            def _inject_target_meta(result_dict, target):
                """Copy probe target metadata into result for CSV saving."""
                result_dict["probe_type"] = target.get("probe_type", "")
                result_dict["target_id"] = target.get("target_id", "")
                result_dict["target_importance"] = target.get("importance", 0)
                result_dict["target_centrality_rank"] = target.get("centrality_rank", 0)
                result_dict["target_on_critical_path"] = target.get("on_critical_path", False)
                result_dict["probe_category"] = target.get("target_type", "")
                result_dict["description"] = target.get("description", "")
                result_dict["probe_text"] = probe.get("probe_text", "")
                result_dict["probe_generated"] = probe.get("generated", True)
                return result_dict

            for pi, (probe, target) in enumerate(zip(all_probes, all_targets)):
                prompt = build_graph_guided_prompt(
                    question_text, initial_prob, nodes, edges, probe, target,
                )

                text, ok = client.call_single(GRAPH_GUIDED_SYSTEM, prompt)
                client.rate_limit_wait()

                if not ok:
                    probe_results.append(_inject_target_meta({
                        "success": False,
                        "updated_probability": None,
                        "absolute_shift": None,
                        "shift_direction": "unchanged",
                        "reasoning": "",
                        "raw_response": "",
                    }, target))
                    continue

                parsed = parse_json_response(text)
                if parsed and "updated_probability" in parsed:
                    up = parsed["updated_probability"]
                    try:
                        up = float(up)
                        up = max(0.01, min(0.99, up))
                    except (ValueError, TypeError):
                        up = None

                    if up is not None:
                        shift = abs(up - initial_prob)
                        direction = "increased" if up > initial_prob else "decreased" if up < initial_prob else "unchanged"
                        probe_results.append(_inject_target_meta({
                            "success": True,
                            "updated_probability": up,
                            "absolute_shift": shift,
                            "shift_direction": direction,
                            "reasoning": parsed.get("reasoning", "")[:300],
                            "raw_response": text[:500],
                            "paths_affected": parsed.get("paths_affected", []),
                            "n_paths_affected": parsed.get("n_paths_affected", 0),
                            "is_critical_path": parsed.get("is_critical_path", None),
                        }, target))
                    else:
                        probe_results.append(_inject_target_meta({
                            "success": False, "updated_probability": None,
                            "absolute_shift": None, "shift_direction": "unchanged",
                            "reasoning": "", "raw_response": text[:300],
                        }, target))
                else:
                    probe_results.append(_inject_target_meta({
                        "success": False, "updated_probability": None,
                        "absolute_shift": None, "shift_direction": "unchanged",
                        "reasoning": "", "raw_response": (text or "")[:300],
                    }, target))

            # Save CSV rows
            net_dict = net_analysis if isinstance(net_analysis, dict) else net_analysis
            for pi, result in enumerate(probe_results):
                save_causal_sensitivity_row(
                    writer, {"id": qid, "question": question_text},
                    "one-turn", initial_prob,
                    all_targets[pi], result, pi, net_dict,
                )
            f.flush()

            # Save per-question JSON
            successful = [r for r in probe_results if r.get("success")]
            shifts = [r["absolute_shift"] for r in successful if r.get("absolute_shift") is not None]

            q_detail = {
                "question_id": qid,
                "question_text": question_text,
                "initial_probability": initial_prob,
                "nodes": nodes,
                "edges": edges,
                "reasoning": src_data.get("reasoning", ""),
                "network_analysis": net_analysis,
                "probe_targets": all_targets,
                "probes": all_probes,
                "condition": "one-turn",
                "prompt_variant": "graph_guided",
                "probe_results": probe_results,
                "summary": {
                    "question_id": qid,
                    "n_probes": len(probe_results),
                    "n_successful": len(successful),
                    "mean_absolute_shift": sum(shifts) / len(shifts) if shifts else None,
                    "max_absolute_shift": max(shifts) if shifts else None,
                },
            }
            save_question_json(OUTPUT_DIR, qid, q_detail)

            n_ok = len(successful)
            mean_s = q_detail["summary"]["mean_absolute_shift"]
            print(f"{n_ok}/{len(probe_results)} ok" +
                  (f", mean shift={mean_s:.3f}" if mean_s else ""))

            n_processed += 1

    print(f"\nDone: {n_processed} questions processed")
    print(f"Results: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
