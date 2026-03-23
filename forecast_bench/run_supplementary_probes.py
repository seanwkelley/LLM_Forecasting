"""
Add supplementary strengthen probes to existing sensitivity results.

Reads cached shared-stage data (DAG + network analysis), generates new
strengthen probe targets (medium node, low node, critical edge, peripheral
edge), creates probe text, runs probing, and appends results to the
existing question JSON and CSV files.

No re-running of DAG generation or existing probes.

Usage:
    python -m forecast_bench.run_supplementary_probes \
        --model llama-70b \
        --output-dir outputs/sensitivity/causal/70b_one_turn \
        --max-questions 100
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
    CAUSAL_PROBE_GENERATION_SYSTEM,
    CAUSAL_PROBED_FORECAST_SYSTEM,
    PROBE_CATEGORIES,
    build_causal_probe_prompt,
    build_causal_probed_forecast_prompt,
)
from forecast_bench.run_sensitivity import (
    CAUSAL_CSV_FIELDS,
    MODEL_MAP,
    _generate_single_causal_probe,
    _parse_probe_result,
)
from forecast_bench.questions import load_forecastbench_questions


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


def compute_new_targets(shared: dict) -> list[dict]:
    """Compute supplementary strengthen probe targets from cached network analysis."""
    na = shared.get("network_analysis", {})
    node_metrics = na.get("node_metrics", [])
    edge_metrics = na.get("edge_metrics", [])

    # Sort factor nodes by betweenness (descending)
    factors = sorted(
        [m for m in node_metrics if m.get("role") != "outcome"],
        key=lambda m: m.get("betweenness", 0),
        reverse=True,
    )
    n_factors = len(factors)

    # Sort edges
    critical_edges = sorted(
        [e for e in edge_metrics if e.get("on_critical_path", False)],
        key=lambda e: e.get("edge_betweenness", 0),
        reverse=True,
    )
    peripheral_edges = sorted(
        [e for e in edge_metrics if not e.get("on_critical_path", False)],
        key=lambda e: e.get("edge_betweenness", 0),
        reverse=True,
    )

    targets = []

    # node_strengthen_medium: median-importance node
    if n_factors >= 3:
        m = factors[n_factors // 2]
        targets.append({
            "target_type": "node",
            "target_id": m["node_id"],
            "description": m.get("description", ""),
            "importance": m.get("betweenness", 0),
            "centrality_rank": n_factors // 2 + 1,
            "on_critical_path": m.get("path_relevance", 0) > 0,
            "probe_type": "node_strengthen_medium",
        })

    # node_strengthen_low: lowest-importance node
    if n_factors >= 2:
        m = factors[-1]
        targets.append({
            "target_type": "node",
            "target_id": m["node_id"],
            "description": m.get("description", ""),
            "importance": m.get("betweenness", 0),
            "centrality_rank": n_factors,
            "on_critical_path": m.get("path_relevance", 0) > 0,
            "probe_type": "node_strengthen_low",
        })

    # edge_strengthen_critical: top 2 critical edges
    for e in critical_edges[:2]:
        edge_id = f"{e['source']}->{e['target']}"
        targets.append({
            "target_type": "edge",
            "target_id": edge_id,
            "description": e.get("mechanism", f"{e['source']} causes {e['target']}"),
            "importance": e.get("edge_betweenness", 0),
            "centrality_rank": 1,
            "on_critical_path": True,
            "probe_type": "edge_strengthen_critical",
        })

    # edge_strengthen_peripheral: top 1 peripheral edge
    for e in peripheral_edges[:1]:
        edge_id = f"{e['source']}->{e['target']}"
        targets.append({
            "target_type": "edge",
            "target_id": edge_id,
            "description": e.get("mechanism", f"{e['source']} causes {e['target']}"),
            "importance": e.get("edge_betweenness", 0),
            "centrality_rank": 1,
            "on_critical_path": False,
            "probe_type": "edge_strengthen_peripheral",
        })

    return targets


NEW_PROBE_TYPES = {
    "node_strengthen_medium",
    "node_strengthen_low",
    "edge_strengthen_critical",
    "edge_strengthen_peripheral",
}


def run_supplementary(args):
    model = MODEL_MAP.get(args.model, args.model)
    api_key = _get_api_key()
    if not api_key:
        print("[ERROR] OPENROUTER_API_KEY not set.")
        sys.exit(1)

    output_dir = Path(args.output_dir)
    shared_dir = output_dir / "_shared_stages_causal"
    results_dir = output_dir / "question_results"

    if not shared_dir.exists():
        print(f"[ERROR] No shared stages found at {shared_dir}")
        sys.exit(1)

    # Load questions to get the right set
    questions = load_forecastbench_questions(
        max_questions=args.max_questions, seed=42,
    )
    question_ids = {q["id"] for q in questions}
    question_map = {q["id"]: q for q in questions}

    print(f"\n{'='*60}")
    print(f"SUPPLEMENTARY STRENGTHEN PROBES")
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

    # Track which questions already have supplementary probes
    supp_marker_dir = output_dir / "_supplementary_done"
    supp_marker_dir.mkdir(parents=True, exist_ok=True)

    csv_path = output_dir / "sensitivity_results.csv"
    csv_file = open(csv_path, "a", newline="", encoding="utf-8")
    csv_writer = csv.DictWriter(csv_file, fieldnames=CAUSAL_CSV_FIELDS)

    completed = 0
    skipped = 0
    failed = 0

    for q_idx, question in enumerate(questions):
        qid = question["id"]
        cache_path = shared_dir / f"q_{qid}.json"
        marker_path = supp_marker_dir / f"q_{qid}.done"

        if marker_path.exists():
            skipped += 1
            print(f"  [{q_idx+1}/{len(questions)}] {qid[:40]} -- already done")
            continue

        if not cache_path.exists():
            print(f"  [{q_idx+1}/{len(questions)}] {qid[:40]} -- no shared data")
            failed += 1
            continue

        shared = json.loads(cache_path.read_text(encoding="utf-8"))
        initial_prob = shared["initial_probability"]
        nodes = shared["nodes"]
        edges = shared["edges"]

        # Compute new targets
        new_targets = compute_new_targets(shared)
        if not new_targets:
            print(f"  [{q_idx+1}/{len(questions)}] {qid[:40]} -- no new targets")
            marker_path.write_text("no_targets")
            continue

        print(f"  [{q_idx+1}/{len(questions)}] {qid[:40]} "
              f"(p={initial_prob:.2f}, {len(new_targets)} new probes) ...", end=" ")

        # Stage 2: Generate probe text for new targets
        new_probes = []
        for target in new_targets:
            probe = _generate_single_causal_probe(
                client, question, initial_prob, nodes, edges, target,
            )
            new_probes.append(probe)

        # Stage 3: Run probing
        new_results = []
        for probe in new_probes:
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
            result["probe_category"] = PROBE_CATEGORIES.get(probe.get("probe_type", ""), "node")
            result["description"] = probe.get("description", "")
            new_results.append(result)

        ok_count = sum(1 for r in new_results if r.get("success"))
        shifts = [r["absolute_shift"] for r in new_results if r.get("success") and r.get("absolute_shift") is not None]
        mean_shift = sum(shifts) / len(shifts) if shifts else 0
        print(f"{ok_count}/{len(new_results)} ok, mean shift={mean_shift:.3f}")

        # Append to question JSON
        q_json_path = results_dir / f"q_{qid}.json"
        if q_json_path.exists():
            q_data = json.loads(q_json_path.read_text(encoding="utf-8"))
            existing_probes = q_data.get("probe_results", [])
            existing_probes.extend(new_results)
            q_data["probe_results"] = existing_probes
            q_json_path.write_text(json.dumps(q_data, indent=2), encoding="utf-8")

        # Append to CSV
        na = shared.get("network_analysis", {})
        for pi, result in enumerate(new_results):
            row = {
                "question_id": qid,
                "question_text": question["question"][:200],
                "condition": "one-turn",
                "initial_probability": f"{initial_prob:.4f}",
                "probe_index": 100 + pi,  # offset to avoid collision
                "probe_type": result.get("probe_type", ""),
                "probe_category": result.get("probe_category", ""),
                "target_id": result.get("target_id", ""),
                "target_description": result.get("description", ""),
                "target_importance": result.get("target_importance", 0),
                "target_centrality_rank": result.get("target_centrality_rank", 0),
                "target_on_critical_path": result.get("target_on_critical_path", False),
                "probe_text": result.get("probe_text", "")[:500],
                "probe_generated": result.get("probe_generated", True),
                "updated_probability": result.get("updated_probability"),
                "absolute_shift": result.get("absolute_shift"),
                "shift_direction": result.get("shift_direction", ""),
                "success": result.get("success", False),
                "reasoning": result.get("reasoning", "")[:500],
                "n_nodes": na.get("n_nodes", 0),
                "n_edges": na.get("n_edges", 0),
                "graph_density": na.get("density", 0),
            }
            csv_writer.writerow(row)

        csv_file.flush()

        # Mark as done
        marker_path.write_text("done")
        completed += 1

    csv_file.close()

    print(f"\n{'='*60}")
    print(f"Completed: {completed}, Skipped: {skipped}, Failed: {failed}")
    print(f"API stats: {json.dumps(client.stats.__dict__, indent=2)}")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(description="Add supplementary strengthen probes")
    parser.add_argument("--model", default="llama-70b",
                        help="Model name or OpenRouter model ID")
    parser.add_argument("--output-dir", required=True,
                        help="Output directory with existing results")
    parser.add_argument("--max-questions", type=int, default=100)
    parser.add_argument("--temperature", type=float, default=0.7)
    args = parser.parse_args()
    run_supplementary(args)


if __name__ == "__main__":
    main()
