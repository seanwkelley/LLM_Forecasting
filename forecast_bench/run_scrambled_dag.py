"""
Causal Structure Placebo Test — Scrambled DAG control condition.

For each question:
1. Pool all factor nodes across models
2. Deduplicate semantically similar nodes (word overlap on descriptions)
3. Randomly sample ~6 nodes, randomly wire DAG edges to an outcome node
4. Present this scrambled DAG to the model as if it were plausible reasoning
5. Run the same probes against it
6. Compare shifts to the real-DAG condition

This tests whether structural sensitivity is real or just sycophancy — if the
model shifts the same amount for a random DAG as for its own, then it's just
responding to being challenged, not to causal structure.

Usage:
    python -m forecast_bench.run_scrambled_dag \
        --model llama-70b \
        --output-dir outputs/sensitivity/causal/70b_one_turn_scrambled \
        --max-questions 100
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from forecast_bench.llm_client import LLMClient, parse_json_response
from forecast_bench.network_analysis import analyze_network
from forecast_bench.prompts_causal import (
    CAUSAL_PROBE_GENERATION_SYSTEM,
    CAUSAL_PROBED_FORECAST_SYSTEM,
    PROBE_CATEGORIES,
    build_causal_probe_prompt,
    build_causal_probed_forecast_prompt,
)
from forecast_bench.questions import load_forecastbench_questions
from forecast_bench.run_sensitivity import (
    CAUSAL_CSV_FIELDS,
    MODEL_MAP,
    _generate_single_causal_probe,
    _parse_probe_result,
    save_question_json,
    get_completed_questions,
)


# All model output directories for pooling nodes
# Source dirs for loading DAGs (_shared_stages_causal cache)
# These point to full pipeline dirs which have the cache
MODEL_DIRS = {
    "llama": "llama_one_turn",
    "llama-70b": "70b_one_turn",
    "deepseek": "deepseek_one_turn",
    "qwen": "qwen_one_turn",
    "gemini-flash-lite": "gemini_flash_lite_neutral",
    "gemini-flash-lite-nitro": "gemini_flash_lite_neutral",
    "gpt-oss": "gpt_oss_neutral",
    "qwen-32b": "qwen32b_one_turn",
}

CAUSAL_BASE = Path(__file__).parent.parent / "outputs" / "sensitivity" / "causal"


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


# ─── Node deduplication ───────────────────────────────────────────────────

def _tokenize(text: str) -> set[str]:
    """Simple word tokenization for similarity."""
    import re
    return set(re.findall(r'[a-z]+', text.lower()))


def _word_overlap(a: str, b: str) -> float:
    """Jaccard similarity on word tokens."""
    ta, tb = _tokenize(a), _tokenize(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def deduplicate_nodes(all_nodes: list[dict], threshold: float = 0.5) -> list[dict]:
    """Deduplicate nodes by ID match or description similarity.

    Returns a list of unique nodes. When duplicates are found, keeps the
    one with the longest description (most informative).
    """
    unique = []

    for node in all_nodes:
        nid = node["id"].lower().strip()
        ndesc = node.get("description", "")
        merged = f"{nid} {ndesc}"

        is_dup = False
        for i, existing in enumerate(unique):
            eid = existing["id"].lower().strip()
            edesc = existing.get("description", "")
            emerged = f"{eid} {edesc}"

            # Check: exact ID match, or high word overlap on id+description
            if nid == eid or _word_overlap(merged, emerged) >= threshold:
                # Keep the one with longer description
                if len(ndesc) > len(edesc):
                    unique[i] = node
                is_dup = True
                break

        if not is_dup:
            unique.append(node)

    return unique


# ─── Scrambled DAG generation ─────────────────────────────────────────────

def build_scrambled_dag(
    pooled_nodes: list[dict],
    n_factors: int = 6,
    seed: int = 42,
) -> tuple[list[dict], list[dict]]:
    """Build a random DAG from a pool of real nodes.

    Samples n_factors nodes, creates a random DAG structure ensuring:
    - All nodes can reach the outcome
    - At least some indirect paths exist (not all direct)
    - DAG has no cycles

    Returns (nodes, edges) in the same format as the real pipeline.
    """
    rng = random.Random(seed)

    # Sample factor nodes
    n_sample = min(n_factors, len(pooled_nodes))
    factors = rng.sample(pooled_nodes, n_sample)

    # Ensure all have role=factor
    factor_nodes = []
    for f in factors:
        factor_nodes.append({
            "id": f["id"],
            "description": f.get("description", ""),
            "role": "factor",
        })

    # Add outcome node
    outcome = {"id": "outcome", "description": "The forecasted event", "role": "outcome"}
    all_nodes = factor_nodes + [outcome]

    # Generate fully random DAG edges.
    # Strategy: enumerate all possible directed edges among nodes (including
    # outcome as target only), randomly select a subset, then verify DAG
    # constraints (acyclic, outcome reachable from all factors).
    all_ids = [n["id"] for n in factor_nodes] + ["outcome"]
    factor_ids = [n["id"] for n in factor_nodes]

    # All possible edges: any factor→factor or factor→outcome
    # (outcome never has outgoing edges)
    possible_edges = []
    for src in factor_ids:
        for tgt in all_ids:
            if src != tgt:
                possible_edges.append((src, tgt))

    # Target edge count: similar density to real DAGs (~1.0-1.2 edges per node)
    target_n_edges = rng.randint(n_sample, int(n_sample * 1.5))
    target_n_edges = min(target_n_edges, len(possible_edges))

    # Repeatedly sample until we get a valid DAG
    import networkx as nx
    for _attempt in range(100):
        sampled = rng.sample(possible_edges, target_n_edges)

        G = nx.DiGraph()
        G.add_nodes_from(all_ids)
        G.add_edges_from(sampled)

        # Check: is it a DAG?
        if not nx.is_directed_acyclic_graph(G):
            continue

        # Check: can all factors reach outcome?
        all_reach = all(
            nx.has_path(G, f, "outcome") for f in factor_ids
        )
        if not all_reach:
            continue

        # Check: outcome has at least 1 incoming edge
        if G.in_degree("outcome") == 0:
            continue

        # Valid DAG found
        edges = []
        for src, tgt in sampled:
            edges.append({
                "from": src,
                "to": tgt,
                "mechanism": f"{src.replace('_', ' ')} influences {tgt.replace('_', ' ')}",
            })
        break
    else:
        # Fallback: simple star topology (all factors → outcome)
        edges = []
        for f in factor_ids:
            edges.append({
                "from": f,
                "to": "outcome",
                "mechanism": f"{f.replace('_', ' ')} influences the outcome",
            })

    return all_nodes, edges


def pool_nodes_for_question(qid: str) -> list[dict]:
    """Pool and deduplicate factor nodes across all models for a question."""
    all_nodes = []

    for model_key, dir_name in MODEL_DIRS.items():
        cache_path = CAUSAL_BASE / dir_name / "_shared_stages_causal" / f"q_{qid}.json"
        if not cache_path.exists():
            continue
        try:
            data = json.loads(cache_path.read_text(encoding="utf-8"))
            nodes = data.get("nodes", [])
            factors = [n for n in nodes if n.get("role") != "outcome"]
            all_nodes.extend(factors)
        except (json.JSONDecodeError, KeyError):
            continue

    return deduplicate_nodes(all_nodes)


# ─── Main pipeline ────────────────────────────────────────────────────────

def run_scrambled(args):
    model = MODEL_MAP.get(args.model, args.model)
    api_key = _get_api_key()
    if not api_key:
        print("[ERROR] OPENROUTER_API_KEY not set.")
        sys.exit(1)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    results_dir = output_dir / "question_results"
    results_dir.mkdir(parents=True, exist_ok=True)

    questions = load_forecastbench_questions(
        max_questions=args.max_questions, seed=42,
        questions_file=args.questions_file,
    )

    print(f"\n{'='*60}")
    print(f"SCRAMBLED DAG PLACEBO TEST")
    print(f"{'='*60}")
    print(f"Model: {model}")
    print(f"Output: {output_dir}")
    print(f"Questions: {len(questions)}")

    client = LLMClient(
        api_key=api_key,
        model=model,
        temperature=args.temperature,
        max_tokens=1200,
    )

    # Get initial probabilities from the model's real run
    model_key = args.model if args.model in MODEL_DIRS else "llama-70b"
    real_shared_dir = CAUSAL_BASE / MODEL_DIRS[model_key] / "_shared_stages_causal"

    completed = get_completed_questions(output_dir) if args.resume else set()
    if completed:
        print(f"Resuming: {len(completed)} questions already complete")

    csv_path = output_dir / "sensitivity_results.csv"
    csv_mode = "a" if args.resume and csv_path.exists() else "w"
    csv_file = open(csv_path, csv_mode, newline="", encoding="utf-8")
    csv_writer = csv.DictWriter(csv_file, fieldnames=CAUSAL_CSV_FIELDS)
    if csv_mode == "w":
        csv_writer.writeheader()

    n_completed = 0
    n_failed = 0

    for q_idx, question in enumerate(questions):
        qid = question["id"]

        if qid in completed:
            print(f"  [{q_idx+1}/{len(questions)}] {qid[:40]} -- skipped (resume)")
            continue

        # Get real initial probability
        real_cache = real_shared_dir / f"q_{qid}.json"
        if not real_cache.exists():
            print(f"  [{q_idx+1}/{len(questions)}] {qid[:40]} -- no real data")
            n_failed += 1
            continue

        real_data = json.loads(real_cache.read_text(encoding="utf-8"))
        initial_prob = real_data["initial_probability"]

        # Pool and deduplicate nodes across models
        pooled = pool_nodes_for_question(qid)
        if len(pooled) < 4:
            print(f"  [{q_idx+1}/{len(questions)}] {qid[:40]} -- too few pooled nodes ({len(pooled)})")
            n_failed += 1
            continue

        # Build scrambled DAG (use question-specific seed for reproducibility)
        scrambled_seed = hash(qid) % (2**31)
        nodes, edges = build_scrambled_dag(pooled, n_factors=6, seed=scrambled_seed)

        # Run network analysis on scrambled DAG
        try:
            net_analysis = analyze_network(nodes, edges)
        except Exception as e:
            print(f"  [{q_idx+1}/{len(questions)}] {qid[:40]} -- network analysis failed: {e}")
            n_failed += 1
            continue

        net_dict = net_analysis.to_dict()
        probe_targets = [pt.to_dict() for pt in net_analysis.probe_targets]

        print(f"  [{q_idx+1}/{len(questions)}] {qid[:40]} "
              f"(p={initial_prob:.2f}, {len(nodes)}N/{len(edges)}E, "
              f"{len(pooled)} pooled, {len(probe_targets)} targets) ...", end=" ")

        # Stage 2: Generate probes for scrambled DAG
        probes = []
        for target in probe_targets:
            probe = _generate_single_causal_probe(
                client, question, initial_prob, nodes, edges, target,
            )
            probes.append(probe)

        # Stage 3: Run probing
        probe_results = []
        for probe in probes:
            probe_target = {
                "target_type": probe.get("target_type", ""),
                "target_id": probe.get("target_id", ""),
                "description": probe.get("description", ""),
                "importance": probe.get("importance", 0.0),
                "centrality_rank": probe.get("centrality_rank", 0),
                "on_critical_path": probe.get("on_critical_path", False),
                "probe_type": probe.get("probe_type", ""),
            }

            user_prompt = build_causal_probed_forecast_prompt(
                question["question"], initial_prob, nodes, edges, probe, probe_target,
            )

            # Retry up to 10 times on parse failure
            result = None
            for _attempt in range(10):
                text, ok = client.call_single(CAUSAL_PROBED_FORECAST_SYSTEM, user_prompt)
                client.rate_limit_wait()
                result = _parse_probe_result(client, probe, initial_prob, text, ok)
                if result.get("success"):
                    break
            result["target_id"] = probe.get("target_id", "")
            result["target_type"] = probe.get("target_type", "")
            result["target_importance"] = probe.get("importance", 0.0)
            result["target_centrality_rank"] = probe.get("centrality_rank", 0)
            result["target_on_critical_path"] = probe.get("on_critical_path", False)
            result["probe_category"] = PROBE_CATEGORIES.get(
                probe.get("probe_type", ""), "structural"
            )
            probe_results.append(result)

        ok_count = sum(1 for r in probe_results if r.get("success"))
        shifts = [r["absolute_shift"] for r in probe_results
                  if r.get("success") and r.get("absolute_shift") is not None]
        mean_shift = sum(shifts) / len(shifts) if shifts else 0
        print(f"{ok_count}/{len(probe_results)} ok, mean shift={mean_shift:.3f}")

        # Save question JSON
        q_output = {
            "question_id": qid,
            "question_text": question["question"],
            "source": question.get("source", ""),
            "condition": "scrambled",
            "initial_probability": initial_prob,
            "nodes": nodes,
            "edges": edges,
            "network_analysis": net_dict,
            "pooled_node_count": len(pooled),
            "scrambled_seed": scrambled_seed,
            "probe_results": probe_results,
        }
        save_question_json(output_dir, qid, q_output)

        # Write CSV rows
        for pi, result in enumerate(probe_results):
            csv_writer.writerow({
                "question_id": qid,
                "question_text": question["question"][:200],
                "condition": "scrambled",
                "initial_probability": f"{initial_prob:.4f}",
                "probe_index": pi,
                "probe_type": result.get("probe_type", ""),
                "probe_category": result.get("probe_category", ""),
                "target_id": result.get("target_id", ""),
                "target_description": "",
                "target_importance": result.get("target_importance", 0),
                "target_centrality_rank": result.get("target_centrality_rank", 0),
                "target_on_critical_path": result.get("target_on_critical_path", False),
                "probe_text": result.get("probe_text", "")[:500],
                "probe_generated": True,
                "updated_probability": result.get("updated_probability"),
                "absolute_shift": result.get("absolute_shift"),
                "shift_direction": result.get("shift_direction", ""),
                "success": result.get("success", False),
                "reasoning": result.get("reasoning", "")[:500],
                "n_nodes": net_dict.get("n_nodes", 0),
                "n_edges": net_dict.get("n_edges", 0),
                "graph_density": net_dict.get("density", 0),
            })
        csv_file.flush()
        n_completed += 1

    csv_file.close()

    print(f"\n{'='*60}")
    print(f"Completed: {n_completed}, Failed: {n_failed}, "
          f"Skipped: {len(completed)}")
    print(f"API stats: {json.dumps(client.stats.__dict__, indent=2)}")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(
        description="Scrambled DAG placebo test for belief sensitivity",
    )
    parser.add_argument("--model", default="llama-70b",
                        help="Model name or OpenRouter model ID")
    parser.add_argument("--output-dir", default=None,
                        help="Output directory (default: outputs/sensitivity/causal/{model}_scrambled)")
    parser.add_argument("--max-questions", type=int, default=100)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--questions-file", default=None, help="Path to local JSON file with questions")
    args = parser.parse_args()

    if args.output_dir is None:
        model_short = args.model if args.model in MODEL_MAP else args.model.split("/")[-1]
        args.output_dir = f"outputs/sensitivity/causal/{model_short.replace('-', '_')}_scrambled"

    run_scrambled(args)


if __name__ == "__main__":
    main()
