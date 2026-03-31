#!/usr/bin/env python3
"""
Factor Ranking Experiment — Do LLMs' stated importance rankings match DAG topology?

For each question, asks the model to rank factors by importance (no DAG context).
Then correlates the stated ranks with betweenness centrality from the existing DAGs.
Uses semantic embedding matching to align ranked factors with DAG nodes.

Usage:
    python -m forecast_bench.run_factor_ranking --model llama-70b --max-questions 100 --resume
    python -m forecast_bench.run_factor_ranking --all-models --max-questions 100 --resume
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from forecast_bench.llm_client import LLMClient, parse_json_response
from forecast_bench.questions import load_forecastbench_questions

BASE = Path(__file__).parent.parent
CAUSAL_DIR = BASE / "outputs" / "sensitivity" / "causal"

MODEL_MAP = {
    "llama": ("meta-llama/llama-3.1-8b-instruct", "Llama-3.1-8B", "llama_one_turn"),
    "llama-70b": ("meta-llama/llama-3.3-70b-instruct", "Llama-3.3-70B", "70b_one_turn"),
    "deepseek": ("deepseek/deepseek-chat-v3-0324", "DeepSeek-V3", "deepseek_one_turn"),
    "qwen": ("qwen/qwen3-235b-a22b-2507", "Qwen3-235B", "qwen_one_turn"),
    "gemini": ("google/gemini-2.0-flash-lite-001", "Gemini-Flash-Lite", "gemini_flash_lite_one_turn"),
}

RANKING_SYSTEM = """\
You are an expert forecaster. Your task is to identify the key factors that \
influence whether a given event will occur, and rank them from most important \
to least important.

Respond with ONLY valid JSON. No other text."""

RANKING_PROMPT = """\
Consider the following forecasting question:

"{question}"

List the key factors that influence this outcome, ranked from MOST important \
(rank 1) to LEAST important. Provide between 4 and 8 factors.

Respond as JSON with exactly this structure:
{{
  "factors": [
    {{"rank": 1, "id": "short_snake_case_id", "description": "What this factor represents and why it matters"}},
    {{"rank": 2, "id": "another_factor", "description": "Description"}},
    ...
  ],
  "reasoning": "<brief paragraph explaining your ranking logic>"
}}

Requirements:
- Rank 1 = most important factor for determining the outcome.
- Each factor must have a unique short_snake_case id.
- Descriptions should be specific enough to identify the factor unambiguously.
- Do NOT include the outcome itself as a factor."""


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


def run_factor_ranking(client: LLMClient, question: dict, max_retries: int = 2) -> dict | None:
    """Ask model to rank factors by importance. Returns parsed response or None."""
    user_prompt = RANKING_PROMPT.format(question=question["question"])

    for attempt in range(1 + max_retries):
        text, ok = client.call_single(RANKING_SYSTEM, user_prompt)
        if not ok:
            return None

        parsed = parse_json_response(text)
        if parsed and "factors" in parsed and len(parsed["factors"]) >= 2:
            # Validate structure
            factors = parsed["factors"]
            valid = all(
                isinstance(f, dict) and "rank" in f and "description" in f
                for f in factors
            )
            if valid:
                # Ensure ranks are sequential
                for i, f in enumerate(factors):
                    f["rank"] = i + 1
                return parsed

        if attempt < max_retries:
            time.sleep(1)

    return None


def match_factors_to_nodes(ranked_factors: list[dict], dag_nodes: list[dict],
                           api_key: str) -> list[dict]:
    """Match ranked factors to DAG nodes using semantic embeddings.

    Returns list of matches: [{rank, factor_desc, node_id, node_desc, cosine_sim}]
    """
    from forecast_bench.semantic_graph_match import _get_embedding, _cosine_matrix

    # Embed factor descriptions
    factor_texts = [f["description"] for f in ranked_factors]
    factor_embs = []
    for text in factor_texts:
        emb = _get_embedding(text, api_key)
        if emb is None:
            return []
        factor_embs.append(emb)
        time.sleep(0.1)

    # Embed DAG node descriptions (only factors, not outcome)
    dag_factors = [n for n in dag_nodes if n.get("role") != "outcome"]
    node_texts = [n["description"] for n in dag_factors]
    node_embs = []
    for text in node_texts:
        emb = _get_embedding(text, api_key)
        if emb is None:
            return []
        node_embs.append(emb)
        time.sleep(0.1)

    if not factor_embs or not node_embs:
        return []

    # Compute cosine similarity matrix and do Hungarian matching
    factor_arr = np.array(factor_embs)
    node_arr = np.array(node_embs)
    sim_matrix = _cosine_matrix(factor_arr, node_arr)

    from scipy.optimize import linear_sum_assignment
    cost = 1.0 - sim_matrix
    row_ind, col_ind = linear_sum_assignment(cost)

    matches = []
    for r, c in zip(row_ind, col_ind):
        sim = float(sim_matrix[r, c])
        if sim >= 0.5:  # lower threshold than graph matching — more lenient for free-text
            matches.append({
                "rank": ranked_factors[r]["rank"],
                "factor_id": ranked_factors[r].get("id", ""),
                "factor_description": ranked_factors[r]["description"],
                "node_id": dag_factors[c]["id"],
                "node_description": dag_factors[c]["description"],
                "cosine_similarity": round(sim, 4),
            })

    return sorted(matches, key=lambda m: m["rank"])


def run_single_model(model_key: str, max_questions: int, resume: bool):
    """Run factor ranking for one model."""
    if model_key not in MODEL_MAP:
        print(f"[ERROR] Unknown model: {model_key}")
        return

    model_id, display_name, dag_dir_name = MODEL_MAP[model_key]
    dag_dir = CAUSAL_DIR / dag_dir_name
    output_dir = CAUSAL_DIR / f"{dag_dir_name}_factor_ranking"
    output_dir.mkdir(parents=True, exist_ok=True)
    results_dir = output_dir / "question_results"
    results_dir.mkdir(exist_ok=True)

    api_key = _get_api_key()
    if not api_key:
        print("[ERROR] OPENROUTER_API_KEY not set.")
        return

    print(f"\n{'='*60}")
    print(f"FACTOR RANKING: {display_name}")
    print(f"{'='*60}")

    questions = load_forecastbench_questions(max_questions=max_questions, seed=42)
    print(f"Loaded {len(questions)} questions")

    client = LLMClient(
        api_key=api_key, model=model_id,
        temperature=0.7, max_tokens=1500,
    )

    # Load existing DAG data for this model
    dag_question_dir = dag_dir / "question_results"
    if not dag_question_dir.exists():
        print(f"[ERROR] No DAG data at {dag_question_dir}")
        return

    completed = set()
    if resume:
        for f in results_dir.glob("q_*.json"):
            completed.add(f.stem.replace("q_", ""))
        if completed:
            print(f"Resuming: {len(completed)} questions already complete")

    n_success = 0
    n_matched = 0

    for q_idx, question in enumerate(questions):
        qid = question["id"]
        if qid in completed:
            continue

        # Load existing DAG
        dag_path = dag_question_dir / f"q_{qid}.json"
        if not dag_path.exists():
            continue

        dag_data = json.loads(dag_path.read_text(encoding="utf-8"))
        dag_nodes = dag_data.get("nodes", [])
        node_metrics = {
            m["node_id"]: m
            for m in dag_data.get("network_analysis", {}).get("node_metrics", [])
        }

        print(f"  [{q_idx+1}/{len(questions)}] {qid[:40]}...", end=" ")

        # Get factor ranking
        ranking = run_factor_ranking(client, question)
        client.rate_limit_wait()

        if ranking is None:
            print("FAILED")
            continue

        factors = ranking["factors"]
        print(f"{len(factors)} factors ranked...", end=" ")

        # Semantic matching to DAG nodes
        matches = match_factors_to_nodes(factors, dag_nodes, api_key)
        print(f"{len(matches)} matched")

        # Annotate matches with betweenness from DAG
        for m in matches:
            nm = node_metrics.get(m["node_id"], {})
            m["betweenness"] = nm.get("betweenness", 0.0)
            m["path_relevance"] = nm.get("path_relevance", 0.0)

        # Save
        result = {
            "question_id": qid,
            "question_text": question["question"],
            "model": display_name,
            "ranked_factors": factors,
            "reasoning": ranking.get("reasoning", ""),
            "matches": matches,
            "n_factors": len(factors),
            "n_matched": len(matches),
        }

        out_path = results_dir / f"q_{qid}.json"
        out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

        n_success += 1
        if matches:
            n_matched += 1

    print(f"\nDone: {n_success} questions ranked, {n_matched} with matches")
    print(f"Results: {results_dir}")


def main():
    parser = argparse.ArgumentParser(description="Factor ranking experiment")
    parser.add_argument("--model", default="llama-70b",
                        help="Model key (llama, llama-70b, deepseek, qwen, gemini)")
    parser.add_argument("--all-models", action="store_true",
                        help="Run all 6 models")
    parser.add_argument("--max-questions", type=int, default=100)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    if args.all_models:
        for model_key in MODEL_MAP:
            run_single_model(model_key, args.max_questions, args.resume)
    else:
        run_single_model(args.model, args.max_questions, args.resume)


if __name__ == "__main__":
    main()
