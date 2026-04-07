#!/usr/bin/env python3
"""
Factor Ranking Experiment — Do LLMs' stated importance rankings match DAG topology?

For each question, presents the model with its OWN DAG factor nodes and asks it to
rank them by importance to the outcome. No embedding matching needed — the model
ranks the exact node IDs it generated in Stage 1.

Correlates stated rank with betweenness centrality to test whether structural
sensitivity is explicit (accessible to introspection) or implicit (revealed only
through probing behavior).

Usage:
    python -m forecast_bench.run_factor_ranking --model gpt-oss
    python -m forecast_bench.run_factor_ranking --model gpt-oss --resume
    python -m forecast_bench.run_factor_ranking --analyze-only
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

BASE = Path(__file__).parent.parent
CAUSAL_DIR = BASE / "outputs" / "sensitivity" / "causal"

MODEL_MAP = {
    "llama": ("meta-llama/llama-3.1-8b-instruct", "Llama-3.1-8B", "llama_neutral"),
    "llama-70b": ("meta-llama/llama-3.3-70b-instruct", "Llama-3.3-70B", "llama_70b_neutral"),
    "deepseek": ("deepseek/deepseek-chat-v3-0324", "DeepSeek-V3", "deepseek_neutral"),
    "qwen": ("qwen/qwen3-235b-a22b-2507", "Qwen3-235B", "qwen_neutral"),
    "qwen-32b": ("qwen/qwen3-32b", "Qwen3-32B", "qwen_32b_neutral"),
    "gemini": ("google/gemini-2.0-flash-lite-001", "Gemini-Flash-Lite", "gemini_fl_neutral"),
    "gpt-oss": ("openai/gpt-oss-120b:nitro", "GPT-OSS-120B", "gpt_oss_neutral"),
}

RANKING_SYSTEM = """\
You are an expert forecaster. You will be given a forecasting question and a list \
of causal factors that influence the outcome. Your task is to rank these factors \
from most important to least important for determining the outcome.

Respond with ONLY valid JSON. No other text."""

RANKING_PROMPT = """\
Consider the following forecasting question:

"{question}"

Here are the causal factors that influence this outcome:

{factors_list}

Rank ALL of these factors from MOST important (rank 1) to LEAST important \
for determining the outcome. You must include every factor exactly once.

Your response must be valid JSON containing ONLY these exact factor IDs, reordered by importance:
{id_list}

Use this exact format:
{{
  "ranking": [
    {{"rank": 1, "id": "COPY_EXACT_ID_HERE", "reason": "Brief reason"}},
    {{"rank": 2, "id": "COPY_EXACT_ID_HERE", "reason": "Brief reason"}},
    ...one entry per factor, rank 1 = most important...
  ]
}}

IMPORTANT: Copy each factor ID exactly as shown above. Do not rename, rephrase, or modify the IDs."""


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


def _format_factors(nodes: list[dict]) -> str:
    """Format DAG factor nodes for the prompt."""
    lines = []
    for n in nodes:
        if n.get("role") == "outcome":
            continue
        lines.append(f"- {n['id']}: {n['description']}")
    return "\n".join(lines)


def _fuzzy_match_id(returned_id: str, valid_ids: set[str]) -> str | None:
    """Try to match a returned ID to a valid one via normalization."""
    # Exact match
    if returned_id in valid_ids:
        return returned_id
    # Normalize: lowercase, strip whitespace, replace hyphens with underscores
    norm = returned_id.strip().lower().replace("-", "_").replace(" ", "_")
    for vid in valid_ids:
        if norm == vid.lower().replace("-", "_"):
            return vid
    # Substring containment (either direction)
    for vid in valid_ids:
        if norm in vid.lower() or vid.lower() in norm:
            return vid
    return None


def run_factor_ranking(client: LLMClient, question_text: str, factor_nodes: list[dict],
                       max_retries: int = 5) -> dict | None:
    """Ask model to rank its own DAG factors by importance. Returns parsed response or None."""
    factor_ids = {n["id"] for n in factor_nodes if n.get("role") != "outcome"}
    factors_list = _format_factors(factor_nodes)
    id_list = json.dumps(sorted(factor_ids))
    user_prompt = RANKING_PROMPT.format(question=question_text, factors_list=factors_list, id_list=id_list)

    for attempt in range(1 + max_retries):
        text, ok = client.call_single(RANKING_SYSTEM, user_prompt)
        if not ok:
            if attempt < max_retries:
                time.sleep(1)
            continue

        parsed = parse_json_response(text)
        if parsed and "ranking" in parsed:
            ranking = parsed["ranking"]
            ranked_ids = {r.get("id") for r in ranking}

            # Try exact match first
            if ranked_ids == factor_ids:
                for i, r in enumerate(ranking):
                    r["rank"] = i + 1
                return parsed

            # Try fuzzy matching
            if len(ranking) == len(factor_ids):
                matched_valid = set()
                all_matched = True
                for r in ranking:
                    matched = _fuzzy_match_id(r.get("id", ""), factor_ids - matched_valid)
                    if matched and matched not in matched_valid:
                        r["id"] = matched  # fix to canonical ID
                        matched_valid.add(matched)
                    else:
                        all_matched = False
                        break
                if all_matched and matched_valid == factor_ids:
                    for i, r in enumerate(ranking):
                        r["rank"] = i + 1
                    return parsed

        if attempt < max_retries:
            time.sleep(1)

    return None


def run_single_model(model_key: str, max_questions: int, resume: bool):
    """Run factor ranking for one model."""
    if model_key not in MODEL_MAP:
        print(f"[ERROR] Unknown model: {model_key}. Options: {list(MODEL_MAP.keys())}")
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

    # Load 116 high-complexity questions
    hc_path = Path(__file__).parent / "high_complexity_questions.json"
    questions = json.loads(hc_path.read_text(encoding="utf-8"))
    if max_questions:
        questions = questions[:max_questions]
    print(f"Loaded {len(questions)} questions")

    client = LLMClient(
        api_key=api_key, model=model_id,
        temperature=0.7, max_tokens=2000,
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

        factor_nodes = [n for n in dag_nodes if n.get("role") != "outcome"]
        if len(factor_nodes) < 2:
            print(f"  [{q_idx+1}/{len(questions)}] {qid[:30]} -- too few factors, skipping")
            continue

        print(f"  [{q_idx+1}/{len(questions)}] {qid[:30]}...", end=" ")

        # Get factor ranking
        ranking = run_factor_ranking(client, question["question"], dag_nodes)
        client.rate_limit_wait()

        if ranking is None:
            print("FAILED")
            continue

        # Annotate with betweenness from DAG
        ranked = ranking["ranking"]
        for r in ranked:
            nm = node_metrics.get(r["id"], {})
            r["betweenness"] = nm.get("betweenness", 0.0)
            r["outcome_mediation"] = nm.get("path_relevance", 0.0)

        # Save
        result = {
            "question_id": qid,
            "question_text": question["question"],
            "model": display_name,
            "n_factors": len(factor_nodes),
            "ranking": ranked,
            "factor_ids": [n["id"] for n in factor_nodes],
        }

        out_path = results_dir / f"q_{qid}.json"
        out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

        n_success += 1
        print(f"OK ({len(ranked)} factors ranked)")

    print(f"\nDone: {n_success} questions ranked")
    print(f"Results: {results_dir}")
    print(f"Stats: {json.dumps(client.stats.to_dict())}")


def analyze(model_key: str = "gpt-oss"):
    """Analyze factor ranking results: correlate stated rank with betweenness."""
    from scipy import stats as sp_stats

    _, display_name, dag_dir_name = MODEL_MAP[model_key]
    results_dir = CAUSAL_DIR / f"{dag_dir_name}_factor_ranking" / "question_results"

    if not results_dir.exists():
        print(f"[ERROR] No results at {results_dir}")
        return

    files = sorted(results_dir.glob("q_*.json"))
    print(f"Analyzing {len(files)} questions for {display_name}")

    all_ranks = []
    all_betweenness = []
    all_mediation = []
    per_question_rho = []

    for f in files:
        data = json.loads(f.read_text(encoding="utf-8"))
        ranking = data["ranking"]

        ranks = [r["rank"] for r in ranking]
        betw = [r["betweenness"] for r in ranking]
        med = [r["outcome_mediation"] for r in ranking]

        all_ranks.extend(ranks)
        all_betweenness.extend(betw)
        all_mediation.extend(med)

        # Per-question Spearman (rank vs betweenness)
        if len(set(betw)) > 1:  # need variance
            rho, p = sp_stats.spearmanr(ranks, betw)
            per_question_rho.append(rho)

    # Aggregate Spearman
    if len(set(all_betweenness)) > 1:
        rho_betw, p_betw = sp_stats.spearmanr(all_ranks, all_betweenness)
    else:
        rho_betw, p_betw = 0.0, 1.0

    if len(set(all_mediation)) > 1:
        rho_med, p_med = sp_stats.spearmanr(all_ranks, all_mediation)
    else:
        rho_med, p_med = 0.0, 1.0

    print(f"\n{'='*60}")
    print(f"FACTOR RANKING RESULTS: {display_name}")
    print(f"{'='*60}")
    print(f"Questions analyzed: {len(files)}")
    print(f"Total factor-rank pairs: {len(all_ranks)}")
    print(f"\nAggregate correlations (rank vs metric):")
    print(f"  Betweenness:      rho = {rho_betw:.3f}, p = {p_betw:.4f}")
    print(f"  Outcome mediation: rho = {rho_med:.3f}, p = {p_med:.4f}")
    print(f"\nNote: negative rho = high-ranked factors have HIGH betweenness (expected)")
    print(f"      positive rho = high-ranked factors have LOW betweenness (unexpected)")

    if per_question_rho:
        mean_rho = np.mean(per_question_rho)
        n_aligned = sum(1 for r in per_question_rho if r < 0)
        print(f"\nPer-question Spearman rho (rank vs betweenness):")
        print(f"  Mean rho: {mean_rho:.3f}")
        print(f"  Questions with rho < 0 (aligned): {n_aligned}/{len(per_question_rho)} ({100*n_aligned/len(per_question_rho):.0f}%)")

    # Save summary
    summary = {
        "model": display_name,
        "n_questions": len(files),
        "n_pairs": len(all_ranks),
        "aggregate_betweenness_rho": round(rho_betw, 4),
        "aggregate_betweenness_p": round(p_betw, 6),
        "aggregate_mediation_rho": round(rho_med, 4),
        "aggregate_mediation_p": round(p_med, 6),
        "per_question_mean_rho": round(float(np.mean(per_question_rho)), 4) if per_question_rho else None,
        "per_question_n_aligned": sum(1 for r in per_question_rho if r < 0) if per_question_rho else None,
        "per_question_n": len(per_question_rho),
    }
    summary_path = CAUSAL_DIR / f"{dag_dir_name}_factor_ranking" / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nSummary saved: {summary_path}")


def main():
    parser = argparse.ArgumentParser(description="Factor ranking experiment")
    parser.add_argument("--model", default="gpt-oss",
                        help="Model key (llama, llama-70b, deepseek, qwen, qwen-32b, gemini, gpt-oss)")
    parser.add_argument("--max-questions", type=int, default=0,
                        help="Max questions (0 = all)")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--analyze-only", action="store_true")
    args = parser.parse_args()

    if args.analyze_only:
        analyze(args.model)
    else:
        run_single_model(args.model, args.max_questions, args.resume)


if __name__ == "__main__":
    main()
