"""
Full Scramble Placebo Test — Irrelevant nodes + random wiring.

Unlike run_scrambled_dag.py which uses real nodes from the same question
(just randomly wired), this uses nodes from DIFFERENT questions — so both
the node content and the topology are irrelevant to the target question.

This tests whether structural sensitivity is driven by:
- The graph context itself (topology)
- The semantic relevance of node content
- Or purely by the probe framing

Three-level comparison:
  Original DAG:      real nodes + real edges     → SSR = 1.81
  Scrambled edges:   real nodes + random edges   → SSR = 1.76
  Scrambled full:    irrelevant nodes + random edges → SSR = ?

Usage:
    python -m forecast_bench.run_scrambled_full \
        --model llama-70b \
        --output-dir outputs/sensitivity/causal/70b_scrambled_full \
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
from forecast_bench.run_scrambled_dag import (
    build_scrambled_dag,
    deduplicate_nodes,
    MODEL_DIRS,
    CAUSAL_BASE,
)


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


def pool_all_nodes() -> dict[str, list[dict]]:
    """Pool all factor nodes per question across all models.

    Returns {qid: [node_dicts]}.
    """
    all_nodes = defaultdict(list)

    for model_key, dir_name in MODEL_DIRS.items():
        shared_dir = CAUSAL_BASE / dir_name / "_shared_stages_causal"
        if not shared_dir.exists():
            continue
        for f in shared_dir.glob("q_*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                qid = data.get("question_id", f.stem.replace("q_", ""))
                nodes = data.get("nodes", [])
                factors = [n for n in nodes if n.get("role") != "outcome"]
                all_nodes[qid].extend(factors)
            except (json.JSONDecodeError, KeyError):
                continue

    # Deduplicate within each question
    return {qid: deduplicate_nodes(nodes) for qid, nodes in all_nodes.items()}


def get_irrelevant_nodes(
    target_qid: str,
    all_question_nodes: dict[str, list[dict]],
    n_nodes: int = 6,
    seed: int = 42,
) -> list[dict]:
    """Sample nodes from OTHER questions (not target_qid).

    Returns a list of deduplicated factor nodes from random other questions.
    """
    rng = random.Random(seed)

    # Collect nodes from all other questions
    other_nodes = []
    for qid, nodes in all_question_nodes.items():
        if qid == target_qid:
            continue
        other_nodes.extend(nodes)

    # Shuffle and deduplicate
    rng.shuffle(other_nodes)
    deduped = deduplicate_nodes(other_nodes)

    # Sample
    n_sample = min(n_nodes, len(deduped))
    return rng.sample(deduped, n_sample)


def run_scrambled_full(args):
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
    )

    print(f"\n{'='*60}")
    print(f"FULLY SCRAMBLED DAG PLACEBO TEST")
    print(f"{'='*60}")
    print(f"Model: {model}")
    print(f"Output: {output_dir}")
    print(f"Questions: {len(questions)}")

    # Pool all nodes across all questions and models
    print("Pooling nodes across all questions...")
    all_question_nodes = pool_all_nodes()
    total_nodes = sum(len(v) for v in all_question_nodes.values())
    print(f"  {len(all_question_nodes)} questions, {total_nodes} total nodes")

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

        # Get IRRELEVANT nodes from other questions
        scrambled_seed = hash(qid) % (2**31)
        irrelevant_nodes = get_irrelevant_nodes(
            qid, all_question_nodes, n_nodes=6, seed=scrambled_seed,
        )

        if len(irrelevant_nodes) < 4:
            print(f"  [{q_idx+1}/{len(questions)}] {qid[:40]} -- too few irrelevant nodes")
            n_failed += 1
            continue

        # Build scrambled DAG with irrelevant nodes
        nodes, edges = build_scrambled_dag(irrelevant_nodes, n_factors=6, seed=scrambled_seed)

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
              f"{len(probe_targets)} targets) ...", end=" ")

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

            text, ok = client.call_single(CAUSAL_PROBED_FORECAST_SYSTEM, user_prompt)
            client.rate_limit_wait()

            result = _parse_probe_result(client, probe, initial_prob, text, ok)
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
            "condition": "scrambled_full",
            "initial_probability": initial_prob,
            "nodes": nodes,
            "edges": edges,
            "network_analysis": net_dict,
            "source_questions": "cross-question (irrelevant nodes)",
            "scrambled_seed": scrambled_seed,
            "probe_results": probe_results,
        }

        save_question_json(results_dir, qid, q_output)

        # Write CSV rows
        for result in probe_results:
            csv_writer.writerow({
                "question_id": qid,
                "question_text": question["question"][:200],
                "source": question.get("source", ""),
                "initial_probability": initial_prob,
                "probe_type": result.get("probe_type", ""),
                "probe_text": result.get("probe_text", "")[:500],
                "target_type": result.get("target_type", ""),
                "target_id": result.get("target_id", ""),
                "importance": result.get("target_importance", 0),
                "centrality_rank": result.get("target_centrality_rank", 0),
                "on_critical_path": result.get("target_on_critical_path", False),
                "updated_probability": result.get("updated_probability"),
                "absolute_shift": result.get("absolute_shift"),
                "success": result.get("success", False),
                "reasoning": result.get("reasoning", "")[:500],
            })
        csv_file.flush()

        n_completed += 1

    csv_file.close()
    print(f"\nDone: {n_completed} completed, {n_failed} failed")
    print(f"Results: {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Fully scrambled DAG placebo test")
    parser.add_argument("--model", default="llama-70b")
    parser.add_argument("--output-dir",
                        default="outputs/sensitivity/causal/70b_scrambled_full")
    parser.add_argument("--max-questions", type=int, default=100)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    run_scrambled_full(args)


if __name__ == "__main__":
    main()
