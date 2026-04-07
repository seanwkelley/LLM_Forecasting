"""
Network Propagation Analysis — Do belief updates propagate through the DAG?

For each question, we reuse existing probes (negate_high ×2, negate_low ×1,
strengthen ×2, strengthen_low ×1) and ask the model: given this challenge,
how does each OTHER factor node's causal influence change?

This tests whether the model reasons *through* the graph structure:
- High-importance probes should cause widespread downstream effects
- Low-importance probes should cause localized/no effects
- Effect magnitude should decay with graph distance from the probed node

Usage:
    python -m forecast_bench.run_propagation --model llama-70b --max-questions 100
    python -m forecast_bench.run_propagation --model llama-70b --max-questions 100 --resume
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np

from forecast_bench.llm_client import LLMClient, parse_json_response
from forecast_bench.prompts_causal import _format_network_context, PROBE_CATEGORIES
from forecast_bench.run_sensitivity import MODEL_MAP

# Probe types we use for propagation analysis
PROPAGATION_PROBE_TYPES = {
    "node_negate_high",
    "node_negate_low",
    "node_strengthen",
    "node_strengthen_low",
}

BASE = Path(__file__).parent.parent
CAUSAL_DIR = BASE / "outputs" / "sensitivity" / "causal"


# ── API key ──────────────────────────────────────────────────────────────

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


# ── Prompts ──────────────────────────────────────────────────────────────

PROPAGATION_SYSTEM = """\
You are an expert forecaster reasoning about how new information \
propagates through a causal network.

When presented with a challenge to one element of your causal network, \
consider how the effect ripples through to OTHER factors in the network \
— not just the final outcome. Some factors may be directly downstream \
of the challenged element; others may be unaffected.

Rate the impact on each factor using a scale from -1.0 (strongly \
weakened) to +1.0 (strongly reinforced), with 0.0 meaning no effect.

Respond with ONLY valid JSON. No other text."""


def build_propagation_prompt(
    question: str,
    initial_probability: float,
    nodes: list[dict],
    edges: list[dict],
    probe: dict,
    probe_target: dict,
) -> str:
    """Build user prompt for propagation analysis."""
    network_context = _format_network_context(nodes, edges)
    target_id = probe.get("target_id", "")
    probe_text = probe.get("probe_text", "")

    category = PROBE_CATEGORIES.get(probe.get("probe_type", ""), "structural")
    if category == "node":
        challenge_desc = f"a challenge to the causal factor '{target_id}'"
    elif category == "edge":
        challenge_desc = f"a challenge to the causal link '{target_id}'"
    else:
        challenge_desc = "a structural challenge to your causal model"

    # Build the list of other factor nodes to rate
    other_factors = [n for n in nodes
                     if n.get("role") != "outcome" and n["id"] != target_id]

    effects_template = {}
    for n in other_factors:
        effects_template[n["id"]] = {
            "impact": "<float -1.0 to 1.0>",
            "reasoning": "<1 sentence explaining why>"
        }

    effects_json = json.dumps(effects_template, indent=2)

    return f"""\
You previously forecasted the following question:

"{question}"

Your initial estimate: probability = {initial_probability:.2f}

Your causal network:
{network_context}

Now consider the following ({challenge_desc}):

"{probe_text}"

For each OTHER factor in your network, rate how this new information \
would change its causal influence on the outcome.

Provide your assessment as JSON:
{{
  "probed_node": "{target_id}",
  "downstream_effects": {effects_json},
  "updated_probability": <float between 0.01 and 0.99>
}}

Requirements:
- impact must be between -1.0 and 1.0 (negative = weakened, positive = reinforced, 0 = unaffected)
- updated_probability must be between 0.01 and 0.99
- Be specific: factors directly downstream of '{target_id}' in the network should be affected more than distant or unrelated factors"""


# ── Graph distance computation ───────────────────────────────────────────

def compute_graph_distances(nodes: list[dict], edges: list[dict], source_id: str) -> dict[str, int]:
    """BFS shortest-path distance from source_id to all other nodes."""
    adjacency = {}
    for n in nodes:
        adjacency[n["id"]] = []
    for e in edges:
        src, tgt = e["from"], e["to"]
        if src in adjacency:
            adjacency[src].append(tgt)

    distances = {source_id: 0}
    queue = [source_id]
    while queue:
        current = queue.pop(0)
        for neighbor in adjacency.get(current, []):
            if neighbor not in distances:
                distances[neighbor] = distances[current] + 1
                queue.append(neighbor)

    # Unreachable nodes get distance -1
    for n in nodes:
        if n["id"] not in distances:
            distances[n["id"]] = -1

    return distances


def compute_undirected_distances(nodes: list[dict], edges: list[dict], source_id: str) -> dict[str, int]:
    """BFS shortest-path distance on undirected version of the graph."""
    adjacency = {}
    for n in nodes:
        adjacency[n["id"]] = []
    for e in edges:
        src, tgt = e["from"], e["to"]
        if src in adjacency:
            adjacency[src].append(tgt)
        if tgt in adjacency:
            adjacency[tgt].append(src)

    distances = {source_id: 0}
    queue = [source_id]
    while queue:
        current = queue.pop(0)
        for neighbor in adjacency.get(current, []):
            if neighbor not in distances:
                distances[neighbor] = distances[current] + 1
                queue.append(neighbor)

    for n in nodes:
        if n["id"] not in distances:
            distances[n["id"]] = -1

    return distances


# ── Main runner ──────────────────────────────────────────────────────────

def load_existing_results(output_dir: Path) -> dict[str, dict]:
    """Load already-completed propagation results."""
    results = {}
    results_dir = output_dir / "propagation_results"
    if results_dir.exists():
        for f in results_dir.glob("*.json"):
            with open(f) as fh:
                d = json.load(fh)
            qid = d.get("question_id", f.stem)
            results[qid] = d
    return results


def run_propagation_analysis(
    client: LLMClient,
    question_data: dict,
    qid: str,
) -> dict:
    """Run propagation analysis for a single question.

    Reuses existing probes from the main pipeline (negate_high, negate_low,
    strengthen, strengthen_low) and asks the model about downstream effects.
    """
    nodes = question_data["nodes"]
    edges = question_data["edges"]
    initial_prob = question_data["initial_probability"]
    question_text = question_data["question_text"]
    probe_results = question_data.get("probe_results", [])

    # Find existing probes for our target types
    target_probes = []
    for pr in probe_results:
        if (pr.get("probe_type") in PROPAGATION_PROBE_TYPES
                and pr.get("success")
                and pr.get("probe_text")):
            target_probes.append(pr)

    if not target_probes:
        return {"question_id": qid, "error": "No matching probes found", "propagation_results": []}

    # Compute graph distances from each probed node
    factor_nodes = [n for n in nodes if n.get("role") != "outcome"]

    propagation_results = []
    for pr in target_probes:
        probe_type = pr["probe_type"]
        target_id = pr.get("target_id", "")

        # Build probe dict in the format build_propagation_prompt expects
        probe = {
            "probe_type": probe_type,
            "target_id": target_id,
            "probe_text": pr["probe_text"],
        }
        probe_target = {
            "target_id": target_id,
            "probe_type": probe_type,
        }

        prompt = build_propagation_prompt(
            question_text, initial_prob, nodes, edges, probe, probe_target)

        # Retry up to 10 times
        data = None
        for _attempt in range(10):
            text, ok = client.call_single(PROPAGATION_SYSTEM, prompt)
            client.rate_limit_wait()

            if not ok:
                continue

            data = parse_json_response(text)
            if data is not None and isinstance(data, dict):
                break
            data = None

        if data is None:
            propagation_results.append({
                "probe_type": probe_type,
                "target_id": target_id,
                "success": False,
                "error": "API/parse failed after retries",
            })
            continue

        # Extract downstream effects
        effects = data.get("downstream_effects") or {}
        updated_prob = data.get("updated_probability")
        if updated_prob is not None:
            updated_prob = max(0.01, min(0.99, float(updated_prob)))

        # Compute graph distances
        directed_dists = compute_graph_distances(nodes, edges, target_id)
        undirected_dists = compute_undirected_distances(nodes, edges, target_id)

        # Annotate each effect with graph distance
        annotated_effects = {}
        for node_id, effect in effects.items():
            impact = effect.get("impact", 0) if isinstance(effect, dict) else 0
            reasoning = effect.get("reasoning", "") if isinstance(effect, dict) else ""
            try:
                impact = max(-1.0, min(1.0, float(impact)))
            except (TypeError, ValueError):
                impact = 0.0

            annotated_effects[node_id] = {
                "impact": impact,
                "abs_impact": abs(impact),
                "reasoning": reasoning,
                "directed_distance": directed_dists.get(node_id, -1),
                "undirected_distance": undirected_dists.get(node_id, -1),
            }

        # Get the original shift from the main pipeline for cross-validation
        original_shift = pr.get("absolute_shift")
        original_updated = pr.get("updated_probability")

        propagation_results.append({
            "probe_type": probe_type,
            "target_id": target_id,
            "target_importance": pr.get("target_importance"),
            "target_centrality_rank": pr.get("target_centrality_rank"),
            "target_on_critical_path": pr.get("target_on_critical_path"),
            "success": True,
            "updated_probability": updated_prob,
            "original_updated_probability": original_updated,
            "original_absolute_shift": original_shift,
            "downstream_effects": annotated_effects,
            "n_affected": sum(1 for e in annotated_effects.values() if e["abs_impact"] > 0.1),
            "mean_abs_impact": float(np.mean([e["abs_impact"] for e in annotated_effects.values()])) if annotated_effects else 0,
        })

    return {
        "question_id": qid,
        "question_text": question_text,
        "initial_probability": initial_prob,
        "n_nodes": len(nodes),
        "n_factor_nodes": len(factor_nodes),
        "n_edges": len(edges),
        "propagation_results": propagation_results,
    }


def main():
    parser = argparse.ArgumentParser(description="Network propagation analysis")
    parser.add_argument("--model", type=str, default="llama-70b",
                        help="Model to use (default: llama-70b)")
    parser.add_argument("--source-dir", type=str, default=None,
                        help="Directory with existing question results (default: auto from model)")
    parser.add_argument("--output-dir", type=str, default=None,
                        help="Output directory (default: same as source-dir)")
    parser.add_argument("--max-questions", type=int, default=100)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    # Resolve directories
    model_dir_map = {
        "llama": "llama_neutral",
        "llama-70b": "llama_70b_neutral",
        "deepseek": "deepseek_neutral",
        "qwen": "qwen_neutral",
        "gemini-flash-lite": "gemini_fl_neutral",
        "gemini-flash-lite-nitro": "gemini_fl_neutral",
        "gpt-oss": "gpt_oss_neutral",
        "qwen-32b": "qwen_32b_neutral",
    }

    if args.source_dir:
        source_dir = Path(args.source_dir)
    else:
        dirname = model_dir_map.get(args.model, f"{args.model}_one_turn")
        source_dir = CAUSAL_DIR / dirname

    output_dir = Path(args.output_dir) if args.output_dir else source_dir
    results_dir = output_dir / "propagation_results"
    results_dir.mkdir(parents=True, exist_ok=True)

    # Load existing question results
    q_results_dir = source_dir / "question_results"
    if not q_results_dir.exists():
        print(f"No question results found in {q_results_dir}")
        sys.exit(1)

    questions = {}
    for f in sorted(q_results_dir.glob("*.json")):
        with open(f) as fh:
            d = json.load(fh)
        qid = d.get("question_id", f.stem.replace("q_", ""))
        questions[qid] = d

    print(f"Loaded {len(questions)} questions from {source_dir}")

    # Resume support
    completed = set()
    if args.resume:
        existing = load_existing_results(output_dir)
        completed = set(existing.keys())
        print(f"Resuming: {len(completed)} already completed")

    # Setup client
    api_key = _get_api_key()
    if not api_key:
        print("No OPENROUTER_API_KEY found")
        sys.exit(1)

    model = MODEL_MAP.get(args.model, args.model)
    client = LLMClient(
        api_key=api_key,
        model=model,
        temperature=args.temperature,
        max_tokens=2000,
    )

    print(f"\nPROPAGATION ANALYSIS")
    print(f"{'='*60}")
    print(f"Model: {model}")
    print(f"Source: {source_dir}")
    print(f"Output: {output_dir}")
    print(f"Temperature: {args.temperature}")

    # Run
    n_done = 0
    all_results = []
    for qid, qdata in sorted(questions.items()):
        if n_done >= args.max_questions:
            break
        if qid in completed:
            n_done += 1
            continue

        print(f"\n[{n_done+1}/{min(len(questions), args.max_questions)}] {qid[:40]}...", end=" ")

        result = run_propagation_analysis(client, qdata, qid)
        n_probes = len(result.get("propagation_results", []))
        n_success = sum(1 for r in result.get("propagation_results", []) if r.get("success"))
        print(f"{n_success}/{n_probes} probes")

        # Save per-question
        out_path = results_dir / f"q_{qid}.json"
        with open(out_path, "w") as fh:
            json.dump(result, fh, indent=2)

        all_results.append(result)
        n_done += 1

    # Summary
    print(f"\n{'='*60}")
    print(f"PROPAGATION ANALYSIS COMPLETE")
    print(f"{'='*60}")
    print(f"Questions processed: {n_done}")

    # Quick aggregate stats
    high_impacts = []
    low_impacts = []
    distance_impacts = []  # (distance, abs_impact)

    for result in all_results:
        for pr in result.get("propagation_results", []):
            if not pr.get("success"):
                continue
            probe_type = pr["probe_type"]
            is_high = probe_type in ("node_negate_high", "node_strengthen")
            effects = pr.get("downstream_effects", {})

            for node_id, eff in effects.items():
                ai = eff["abs_impact"]
                dist = eff["undirected_distance"]
                if is_high:
                    high_impacts.append(ai)
                else:
                    low_impacts.append(ai)
                if dist >= 0:
                    distance_impacts.append((dist, ai))

    if high_impacts and low_impacts:
        print(f"\nHigh-importance probes: mean |impact| = {np.mean(high_impacts):.3f} "
              f"(n={len(high_impacts)})")
        print(f"Low-importance probes:  mean |impact| = {np.mean(low_impacts):.3f} "
              f"(n={len(low_impacts)})")
        print(f"Ratio (high/low): {np.mean(high_impacts)/np.mean(low_impacts):.2f}")

    if distance_impacts:
        by_dist = {}
        for d, ai in distance_impacts:
            by_dist.setdefault(d, []).append(ai)
        print(f"\nEffect by graph distance:")
        for d in sorted(by_dist.keys()):
            vals = by_dist[d]
            print(f"  distance {d}: mean |impact| = {np.mean(vals):.3f} (n={len(vals)})")

    print(f"\nResults saved to {results_dir}")


if __name__ == "__main__":
    main()
