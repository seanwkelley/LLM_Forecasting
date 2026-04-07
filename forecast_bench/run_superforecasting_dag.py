"""
Sub-analysis: Do superforecasting principles change the causal DAG?

Runs Stage 1 only (causal forecast) with two system prompts:
  1. Baseline — standard causal forecast prompt (already have data)
  2. Superforecasting-augmented — adds reference class thinking, outside view, etc.

Compares the resulting DAGs for the same questions on the same model.

Usage:
    python -m forecast_bench.run_superforecasting_dag --model llama-70b --max-questions 51
    python -m forecast_bench.run_superforecasting_dag --model llama-70b --max-questions 51 --resume
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from forecast_bench.llm_client import LLMClient, parse_json_response
from forecast_bench.questions import load_forecastbench_questions
from forecast_bench.prompts_causal import build_causal_forecast_prompt
from forecast_bench.network_analysis import analyze_network, plot_causal_network

# ── Model map ────────────────────────────────────────────────────────────
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

# ── Superforecasting-augmented system prompt ─────────────────────────────
SUPERFORECASTING_SYSTEM = """\
You are an expert forecaster trained in superforecasting methodology. Your task \
is to estimate the probability that a given event will occur, and to represent \
your reasoning as a directed causal graph.

Apply these superforecasting principles when building your causal model:

1. OUTSIDE VIEW FIRST: Before constructing your causal network, consider the \
base rate. How often do events like this happen historically? Start from \
reference classes before incorporating case-specific details.

2. GRANULAR DECOMPOSITION: Break the problem into independent sub-components. \
Each node should represent a distinct, measurable factor — avoid vague or \
overlapping factors.

3. DISTINGUISH SIGNAL FROM NOISE: Only include factors that have genuine causal \
relevance to the outcome. Resist the temptation to add factors just because \
they are topically related — each edge must represent a defensible causal \
mechanism.

4. CONSIDER COUNTERFACTUALS: For each causal link, ask: "If this factor were \
different, would the outcome probability actually change?" Only include edges \
that survive this test.

5. CALIBRATION: Assign probabilities that genuinely reflect your uncertainty. \
Use historical base rates as anchors and adjust from there. Avoid round numbers \
unless warranted.

Build a causal network where:
- Nodes are factors that influence the outcome
- Directed edges represent causal mechanisms (A -> B means A causally influences B)
- One node is the "outcome" node representing the forecasted event
- All other nodes are "factor" nodes representing causal drivers

Respond with ONLY valid JSON. No other text."""


def run_stage1(client, question_text, system_prompt, max_retries=5):
    """Run Stage 1 (causal forecast) with a given system prompt.

    Returns parsed dict or None on failure.
    """
    user_prompt = build_causal_forecast_prompt(question_text)

    for attempt in range(1 + max_retries):
        text, ok = client.call_single(system_prompt, user_prompt)
        if not ok:
            if attempt < max_retries:
                print(f"  Retry {attempt+1}/{max_retries}...")
                client.rate_limit_wait()
                continue
            return None

        data = parse_json_response(text)
        if data is None or not isinstance(data, dict):
            if attempt < max_retries:
                print(f"  Retry {attempt+1}/{max_retries}...")
                client.rate_limit_wait()
                continue
            client.stats.parse_failures += 1
            return None

        prob = data.get("probability")
        nodes = data.get("nodes")
        edges = data.get("edges")
        if prob is None or not isinstance(nodes, list) or not isinstance(edges, list):
            if attempt < max_retries:
                print(f"  Retry {attempt+1}/{max_retries}...")
                client.rate_limit_wait()
                continue
            client.stats.parse_failures += 1
            return None

        break  # Success

    prob = max(0.01, min(0.99, float(prob)))
    data["probability"] = prob

    # Validate
    node_ids = set()
    outcome_count = 0
    for n in nodes:
        if not isinstance(n, dict) or "id" not in n:
            return None
        n.setdefault("description", "")
        n.setdefault("role", "factor")
        node_ids.add(n["id"])
        if n["role"] == "outcome":
            outcome_count += 1

    if outcome_count != 1 or len([n for n in nodes if n["role"] != "outcome"]) < 2:
        return None

    for e in edges:
        if not isinstance(e, dict):
            return None
        e.setdefault("mechanism", "")
        if e.get("from") not in node_ids or e.get("to") not in node_ids:
            return None

    if not edges:
        return None

    # Reject graphs with disconnected nodes
    edge_node_ids = set(e.get("from") for e in edges) | set(e.get("to") for e in edges)
    if any(n["id"] not in edge_node_ids for n in nodes):
        return None

    outcome_id = next(n["id"] for n in nodes if n["role"] == "outcome")
    if not any(e["to"] == outcome_id for e in edges):
        return None

    return data


def main():
    parser = argparse.ArgumentParser(description="Superforecasting DAG comparison")
    parser.add_argument("--model", default="llama-70b", choices=list(MODEL_MAP.keys()))
    parser.add_argument("--max-questions", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", type=str, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--questions-file", default=None, help="Path to local JSON file with questions")
    args = parser.parse_args()

    model_id = MODEL_MAP[args.model]
    api_key = os.getenv("OPENROUTER_API_KEY", "") or \
        "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"

    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = Path(__file__).parent.parent / "outputs" / "sensitivity" / "causal" / f"{args.model.replace('-', '_')}_superforecasting"

    output_dir.mkdir(parents=True, exist_ok=True)
    results_dir = output_dir / "_superforecasting_results"
    results_dir.mkdir(parents=True, exist_ok=True)

    client = LLMClient(
        api_key=api_key,
        model=model_id,
        temperature=0.7,
        max_tokens=2000,
        max_retries=3,
    )

    # Load questions (same set as baseline)
    questions = load_forecastbench_questions(seed=args.seed, max_questions=args.max_questions,
                                                questions_file=args.questions_file)
    print(f"Loaded {len(questions)} questions for model={args.model} ({model_id})")
    print(f"Output: {output_dir}")

    completed = 0
    skipped = 0

    for qi, q in enumerate(questions):
        qid = q["id"]
        result_path = results_dir / f"{qid}.json"

        # Resume support
        if args.resume and result_path.exists():
            skipped += 1
            continue

        print(f"\n[{qi+1}/{len(questions)}] {q['question'][:80]}...")

        # Run superforecasting-augmented Stage 1
        sf_result = None
        for attempt in range(10):
            sf_result = run_stage1(client, q["question"], SUPERFORECASTING_SYSTEM)
            if sf_result is not None:
                break
            print(f"  Retry {attempt+1}/10...")
            time.sleep(2)

        if sf_result is None:
            print(f"  FAILED after 10 attempts — skipping")
            continue

        # Network analysis
        analysis = analyze_network(sf_result["nodes"], sf_result["edges"])

        # Save result
        output = {
            "question_id": qid,
            "question_text": q["question"],
            "source": q.get("source", ""),
            "condition": "superforecasting",
            "model": args.model,
            "model_id": model_id,
            "initial_probability": sf_result["probability"],
            "nodes": sf_result["nodes"],
            "edges": sf_result["edges"],
            "reasoning": sf_result.get("reasoning", ""),
            "network_analysis": analysis.to_dict(),
        }

        with open(result_path, "w") as f:
            json.dump(output, f, indent=2)

        # Plot
        plot_dir = output_dir / "network_plots"
        plot_dir.mkdir(parents=True, exist_ok=True)
        try:
            plot_causal_network(
                sf_result["nodes"], sf_result["edges"], analysis,
                save_path=plot_dir / f"{qid}_network.png",
                title=q["question"][:80],
                initial_prob=sf_result["probability"],
            )
        except Exception as e:
            print(f"  Plot failed: {e}")

        completed += 1
        print(f"  P={sf_result['probability']:.2f}, "
              f"{len(sf_result['nodes'])} nodes, {len(sf_result['edges'])} edges")

    print(f"\n{'='*60}")
    print(f"Completed: {completed}, Skipped (resumed): {skipped}, Total: {len(questions)}")
    print(f"API stats: {client.stats.to_dict()}")
    print(f"Results saved to: {results_dir}")


if __name__ == "__main__":
    main()
