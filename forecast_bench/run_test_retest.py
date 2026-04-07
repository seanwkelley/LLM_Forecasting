"""
Test-retest reliability: Re-run Stage 1 (causal forecast) to measure DAG
and initial probability reproducibility across independent runs.

For each model, generates a fresh DAG + probability for all 116 questions
(no probing). Results are compared to the main run to compute:
  - Spearman rho for initial probabilities
  - Semantic node Jaccard for DAG structure

Usage:
    python -m forecast_bench.run_test_retest --model llama --resume
    python -m forecast_bench.run_test_retest --model gpt-oss --resume
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from forecast_bench.llm_client import LLMClient, parse_json_response
from forecast_bench.prompts_causal import (
    CAUSAL_FORECAST_SYSTEM,
    build_causal_forecast_prompt,
)
from forecast_bench.network_analysis import analyze_network
from forecast_bench.run_sensitivity import MODEL_MAP

BASE = Path(__file__).parent.parent
CAUSAL_DIR = BASE / "outputs" / "sensitivity" / "causal"


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


def run_forecast(client, question_text, node_range=(6, 10), max_outer=10):
    """Run Stage 1 with retries. Returns parsed dict or None."""
    prompt = build_causal_forecast_prompt(question_text, node_range=node_range)
    for outer in range(max_outer):
        text, ok = client.call_single(CAUSAL_FORECAST_SYSTEM, prompt)
        client.rate_limit_wait()
        if not ok:
            continue
        data = parse_json_response(text)
        if data is None:
            continue
        prob = data.get("probability")
        nodes = data.get("nodes", [])
        edges = data.get("edges", [])
        if prob is not None and len(nodes) >= 2 and len(edges) >= 1:
            # Reject graphs with disconnected nodes
            edge_node_ids = set(e.get("from") for e in edges) | set(e.get("to") for e in edges)
            if any(n.get("id") not in edge_node_ids for n in nodes):
                continue
            data["probability"] = max(0.01, min(0.99, float(prob)))
            return data
    return None


def main():
    parser = argparse.ArgumentParser(description="Test-retest: re-run Stage 1 for reliability")
    parser.add_argument("--model", default="llama", help="Model name or OpenRouter ID")
    parser.add_argument("--max-questions", type=int, default=116)
    parser.add_argument("--questions-file", default=None)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--node-range", type=int, nargs=2, default=[6, 10])
    args = parser.parse_args()

    model_id = MODEL_MAP.get(args.model, args.model)
    api_key = _get_api_key()
    if not api_key:
        print("[ERROR] OPENROUTER_API_KEY not set.")
        sys.exit(1)

    # Load questions
    from forecast_bench.questions import load_forecastbench_questions
    questions = load_forecastbench_questions(
        max_questions=args.max_questions, seed=42,
        questions_file=args.questions_file,
    )

    # Output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        model_short = args.model if args.model in MODEL_MAP else model_id.split("/")[-1]
        output_dir = CAUSAL_DIR / f"{model_short.replace('-', '_')}_retest"
    output_dir.mkdir(parents=True, exist_ok=True)
    results_dir = output_dir / "_shared_stages_causal"
    results_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"TEST-RETEST: Stage 1 only (DAG + probability)")
    print(f"{'='*60}")
    print(f"Model: {model_id}")
    print(f"Output: {output_dir}")
    print(f"Questions: {len(questions)}")

    client = LLMClient(
        api_key=api_key,
        model=model_id,
        temperature=0.7,
        max_tokens=2000,
    )

    completed = 0
    skipped = 0

    for i, q in enumerate(questions):
        qid = q["id"]
        result_path = results_dir / f"q_{qid}.json"

        if args.resume and result_path.exists():
            skipped += 1
            continue

        sys.stdout.buffer.write(f"  [{i+1}/{len(questions)}] {q['question'][:60]}... ".encode("utf-8", errors="replace"))
        sys.stdout.buffer.flush()

        data = run_forecast(client, q["question"], node_range=tuple(args.node_range))

        if data is None:
            print("FAILED after 10 attempts")
            continue

        nodes = data["nodes"]
        edges = data["edges"]

        try:
            na = analyze_network(nodes, edges)
            na_dict = na.to_dict()
        except Exception:
            na_dict = {}

        result = {
            "question_id": qid,
            "question_text": q["question"],
            "initial_probability": data["probability"],
            "nodes": nodes,
            "edges": edges,
            "reasoning": data.get("reasoning", ""),
            "network_analysis": na_dict,
        }

        result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        completed += 1
        print(f"p={data['probability']:.2f}, {len(nodes)}N/{len(edges)}E")

    print(f"\nCompleted: {completed}, Skipped: {skipped}, Total: {len(questions)}")
    print(f"Results: {results_dir}")


if __name__ == "__main__":
    main()
