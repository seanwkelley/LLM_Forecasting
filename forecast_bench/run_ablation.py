"""
Causal Ablation Analysis — Does the forecast mechanically depend on DAG structure?

For each question, takes the model's own DAG and:
1. Ablates each factor node (removes node + all its edges), re-forecasts
2. Ablates each edge (removes single edge), re-forecasts
3. Compares the shift in probability to the node/edge's structural importance

This is complementary to probing: probing tests whether the model *responds to
challenges* proportionally; ablation tests whether the forecast is actually
*derived from* the structure.

Usage:
    python -m forecast_bench.run_ablation \
        --model llama-70b \
        --output-dir outputs/sensitivity/causal/70b_ablation \
        --max-questions 100 --resume
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from forecast_bench.llm_client import LLMClient, parse_json_response
from forecast_bench.network_analysis import analyze_network
from forecast_bench.prompts_causal import CAUSAL_FORECAST_SYSTEM
from forecast_bench.questions import load_forecastbench_questions

MODEL_MAP = {
    "llama": "meta-llama/llama-3.1-8b-instruct",
    "llama-70b": "meta-llama/llama-3.3-70b-instruct",
    "deepseek": "deepseek/deepseek-chat-v3-0324",
    "qwen": "qwen/qwen3-235b-a22b-2507",
    "gpt-oss": "openai/gpt-oss-120b:nitro",
    "qwen-32b": "qwen/qwen3-32b:nitro",
    "gemini-flash-lite": "google/gemini-2.5-flash-lite",
    "gemini-flash-lite-nitro": "google/gemini-2.5-flash-lite:nitro",
}

CAUSAL_BASE = Path(__file__).parent.parent / "outputs" / "sensitivity" / "causal"

# Source dirs for loading DAGs (_shared_stages_causal cache)
MODEL_DIRS = {
    "llama": "llama_one_turn",
    "llama-70b": "70b_one_turn",
    "deepseek": "deepseek_one_turn",
    "qwen": "qwen_one_turn",
    "gpt-oss": "gpt_oss_neutral",
    "qwen-32b": "qwen32b_one_turn",
    "gemini-flash-lite": "gemini_flash_lite_one_turn",
    "gemini-flash-lite-nitro": "gemini_flash_lite_one_turn",
}


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


ABLATION_SYSTEM = """\
You are an expert forecaster. You previously analyzed a forecasting question \
and built a causal network. The network has been modified — a component has \
been removed. Given the modified causal network, provide an updated \
probability estimate.

You must reason from the MODIFIED network as presented. Do not add back \
removed components. Estimate the probability given only the causal factors \
and links that remain.

Respond with ONLY valid JSON:
{
  "probability": <float between 0.01 and 0.99>,
  "reasoning": "<brief explanation of how the removal affects your estimate>"
}"""


def build_ablation_prompt(
    question: str,
    initial_prob: float,
    nodes: list[dict],
    edges: list[dict],
    removed_type: str,
    removed_id: str,
    removed_desc: str,
) -> str:
    """Build prompt for re-forecasting while ignoring a specific factor."""
    node_text = "\n".join(
        f"  - {n['id']}: {n.get('description', '')} [{n.get('role', 'factor')}]"
        for n in nodes
    )
    edge_text = "\n".join(
        f"  - {e['from']} -> {e['to']}: {e.get('mechanism', '')}"
        for e in edges
    )

    return f"""\
You previously forecasted the following question:

"{question}"

Your initial estimate: probability = {initial_prob:.2f}

Your causal network:

Nodes:
{node_text}

Edges:
{edge_text}

Now re-estimate the probability, but DO NOT consider the {removed_type} \
"{removed_id}" ({removed_desc}). Assume this {removed_type} is completely \
irrelevant and should have no influence on the outcome. All other \
factors and causal relationships remain as stated.

Provide your updated forecast as JSON:
{{"updated_probability": <float between 0.01 and 0.99>, "reasoning": "<explain how ignoring this {removed_type} affects your estimate>"}}

Requirements:
- updated_probability must be between 0.01 and 0.99."""


def ablate_node(nodes: list[dict], edges: list[dict], node_id: str):
    """Remove a node and all its edges, return modified copies."""
    new_nodes = [n for n in nodes if n["id"] != node_id]
    new_edges = [e for e in edges if e["from"] != node_id and e["to"] != node_id]
    return new_nodes, new_edges


def ablate_edge(nodes: list[dict], edges: list[dict], edge_from: str, edge_to: str):
    """Remove a single edge, return modified copies."""
    new_edges = [e for e in edges
                 if not (e["from"] == edge_from and e["to"] == edge_to)]
    return list(nodes), new_edges


def run_ablation_forecast(
    client: LLMClient,
    question_text: str,
    initial_prob: float,
    ablated_nodes: list[dict],
    ablated_edges: list[dict],
    removed_type: str,
    removed_id: str,
    removed_desc: str,
    max_retries: int = 9,
) -> dict | None:
    """Run a single ablation forecast."""
    prompt = build_ablation_prompt(
        question_text, initial_prob,
        ablated_nodes, ablated_edges,
        removed_type, removed_id, removed_desc,
    )

    for attempt in range(1 + max_retries):
        text, ok = client.call_single(ABLATION_SYSTEM, prompt)
        if not ok:
            if attempt < max_retries:
                client.rate_limit_wait()
                continue
            return None

        data = parse_json_response(text)
        if data is None:
            if attempt < max_retries:
                client.rate_limit_wait()
                continue
            client.stats.parse_failures += 1
            return None

        prob = data.get("updated_probability", data.get("probability"))
        if prob is None:
            if attempt < max_retries:
                client.rate_limit_wait()
                continue
            return None

        prob = max(0.01, min(0.99, float(prob)))
        return {
            "updated_probability": prob,
            "absolute_shift": abs(prob - initial_prob),
            "signed_shift": prob - initial_prob,
            "reasoning": data.get("reasoning", ""),
        }

    return None


def run_ablation(args):
    model_id = MODEL_MAP.get(args.model, args.model)
    api_key = _get_api_key()
    if not api_key:
        print("[ERROR] OPENROUTER_API_KEY not set.")
        sys.exit(1)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    results_dir = output_dir / "question_results"
    results_dir.mkdir(parents=True, exist_ok=True)

    # Load questions
    questions = load_forecastbench_questions(
        max_questions=args.max_questions, seed=42,
        questions_file=args.questions_file,
    )
    question_map = {q["id"]: q for q in questions}

    # Load shared stages from the model's main run
    model_key = args.model if args.model in MODEL_DIRS else "llama-70b"
    shared_dir = CAUSAL_BASE / MODEL_DIRS[model_key] / "_shared_stages_causal"

    print(f"\n{'='*60}")
    print(f"CAUSAL ABLATION ANALYSIS")
    print(f"{'='*60}")
    print(f"Model: {model_id}")
    print(f"Source DAGs: {shared_dir}")
    print(f"Output: {output_dir}")
    print(f"Questions: {len(questions)}")

    client = LLMClient(
        api_key=api_key,
        model=model_id,
        temperature=args.temperature,
        max_tokens=800,
    )

    # Check completed
    completed = set()
    if args.resume:
        for p in results_dir.glob("q_*.json"):
            completed.add(p.stem.replace("q_", ""))
        if completed:
            print(f"Resuming: {len(completed)} questions already complete")

    n_completed = 0
    n_failed = 0

    for q_idx, question in enumerate(questions):
        qid = question["id"]

        if qid in completed:
            print(f"  [{q_idx+1}/{len(questions)}] {qid[:40]} -- skipped")
            continue

        cache_path = shared_dir / f"q_{qid}.json"
        if not cache_path.exists():
            n_failed += 1
            continue

        shared = json.loads(cache_path.read_text(encoding="utf-8"))
        initial_prob = shared["initial_probability"]
        nodes = shared["nodes"]
        edges = shared["edges"]
        na = shared.get("network_analysis", {})

        # Build importance lookups
        node_metrics = {m["node_id"]: m for m in na.get("node_metrics", [])}
        edge_metrics = {}
        for m in na.get("edge_metrics", []):
            edge_metrics[(m["source"], m["target"])] = m

        factor_nodes = [n for n in nodes if n.get("role") != "outcome"]

        print(f"  [{q_idx+1}/{len(questions)}] {qid[:40]} "
              f"(p={initial_prob:.2f}, {len(factor_nodes)}N/{len(edges)}E) ...", end=" ")

        ablation_results = []

        # Node ablations — present full graph, instruct model to ignore each factor
        for node in factor_nodes:
            nid = node["id"]
            ndesc = node.get("description", "")

            result = run_ablation_forecast(
                client, question["question"], initial_prob,
                nodes, edges,
                "node", nid, ndesc,
            )
            client.rate_limit_wait()

            metrics = node_metrics.get(nid, {})
            entry = {
                "ablation_type": "node",
                "removed_id": nid,
                "removed_description": ndesc,
                "betweenness": metrics.get("betweenness", 0),
                "path_relevance": metrics.get("path_relevance", 0),
                "success": result is not None,
            }
            if result:
                entry.update(result)
            ablation_results.append(entry)

        ok_count = sum(1 for r in ablation_results if r.get("success"))
        shifts = [r["absolute_shift"] for r in ablation_results
                  if r.get("success") and r.get("absolute_shift") is not None]
        mean_shift = sum(shifts) / len(shifts) if shifts else 0
        print(f"{ok_count}/{len(ablation_results)} ok, mean shift={mean_shift:.3f}")

        # Save
        q_output = {
            "question_id": qid,
            "question_text": question["question"],
            "initial_probability": initial_prob,
            "nodes": nodes,
            "edges": edges,
            "network_analysis": na,
            "ablation_results": ablation_results,
        }
        q_path = results_dir / f"q_{qid}.json"
        q_path.write_text(json.dumps(q_output, indent=2), encoding="utf-8")
        n_completed += 1

    print(f"\n{'='*60}")
    print(f"Completed: {n_completed}, Failed: {n_failed}, "
          f"Skipped: {len(completed)}")
    print(f"API stats: {json.dumps(client.stats.__dict__, indent=2)}")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(
        description="Causal ablation analysis — remove nodes/edges and re-forecast",
    )
    parser.add_argument("--model", default="llama-70b",
                        help="Model name or OpenRouter model ID")
    parser.add_argument("--output-dir", default=None,
                        help="Output directory")
    parser.add_argument("--max-questions", type=int, default=100)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--questions-file", default=None, help="Path to local JSON file with questions")
    args = parser.parse_args()

    if args.output_dir is None:
        model_short = args.model.replace("-", "_")
        args.output_dir = f"outputs/sensitivity/causal/{model_short}_ablation"

    run_ablation(args)


if __name__ == "__main__":
    main()
