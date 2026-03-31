"""
Compound Probe Analysis — Do probe effects interact through the DAG?

For each question, we select pairs of existing probes at varying graph
distances and present both challenges simultaneously. If the model reasons
through the DAG structure, the compound effect should be super-additive
for nearby nodes (effects compound) and roughly additive for distant nodes
(independent effects).

The interaction term is:
    interaction = shift_AB - (shift_A + shift_B)

where shift_AB is the absolute shift from the compound probe, and shift_A,
shift_B are the individual shifts (already collected in the main pipeline).

Usage:
    python -m forecast_bench.run_compound_probes --model llama-70b --max-questions 100
    python -m forecast_bench.run_compound_probes --model llama-70b --max-questions 100 --resume
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np

from forecast_bench.llm_client import LLMClient, parse_json_response
from forecast_bench.prompts_causal import _format_network_context, PROBE_CATEGORIES
from forecast_bench.run_sensitivity import MODEL_MAP
from forecast_bench.run_propagation import (
    compute_graph_distances,
    compute_undirected_distances,
)

# Probe types eligible for pairing (node-level only — cleaner interpretation)
COMPOUND_PROBE_TYPES = {
    "node_negate_high",
    "node_negate_low",
    "node_strengthen",
    "node_strengthen_low",
}

# Target: ~6 pairs per question, sampling across distance bins
PAIRS_PER_DISTANCE_BIN = 2
DISTANCE_BINS = [(1, 1), (2, 2), (3, 99)]  # (min, max) inclusive

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


# ── Prompt ───────────────────────────────────────────────────────────────

COMPOUND_SYSTEM = """\
You are an expert forecaster updating your estimate in light of new information \
about your causal model.

When presented with new information, consider how it affects your causal network \
and update your probability estimate accordingly.

Respond with ONLY valid JSON. No other text."""


def build_compound_probe_prompt(
    question: str,
    initial_probability: float,
    nodes: list[dict],
    edges: list[dict],
    probe_a: dict,
    probe_b: dict,
    order: str,
) -> str:
    """Build prompt presenting two probes simultaneously.

    Parameters
    ----------
    order : str
        "AB" or "BA" — which probe is presented first.
    """
    network_context = _format_network_context(nodes, edges)

    if order == "AB":
        first, second = probe_a, probe_b
    else:
        first, second = probe_b, probe_a

    def _challenge_desc(probe: dict) -> str:
        category = PROBE_CATEGORIES.get(probe.get("probe_type", ""), "structural")
        target_id = probe.get("target_id", "")
        if category == "node":
            return f"a challenge to the causal factor '{target_id}'"
        elif category == "edge":
            return f"a challenge to the causal link '{target_id}'"
        return "a structural challenge to your causal model"

    return f"""\
You previously forecasted the following question:

"{question}"

Your initial estimate: probability = {initial_probability:.2f}

Your causal network:
{network_context}

Now consider TWO pieces of new information:

1. ({_challenge_desc(first)}):
"{first['probe_text']}"

2. ({_challenge_desc(second)}):
"{second['probe_text']}"

Given BOTH of these considerations together, what is your updated \
probability estimate?

Provide your updated forecast as JSON:
{{
  "reasoning": "<2-3 sentences explaining how these factors interact>",
  "updated_probability": <float between 0.01 and 0.99>
}}

Requirements:
- updated_probability must be between 0.01 and 0.99.
- Consider how the two challenges may reinforce, counteract, or be \
independent of each other through the causal network."""


# ── Pair selection ───────────────────────────────────────────────────────

def select_probe_pairs(
    probe_results: list[dict],
    nodes: list[dict],
    edges: list[dict],
    rng: random.Random,
) -> list[dict]:
    """Select probe pairs at varying graph distances.

    Returns list of dicts with keys: probe_a, probe_b, undirected_distance,
    directed_distance_ab, directed_distance_ba.
    """
    # Filter to eligible probes that succeeded
    eligible = [
        p for p in probe_results
        if p.get("probe_type") in COMPOUND_PROBE_TYPES
        and p.get("success")
        and p.get("probe_text")
        and p.get("target_id")
    ]

    if len(eligible) < 2:
        return []

    # Compute pairwise distances
    pairs_by_bin: dict[tuple[int, int], list[dict]] = {b: [] for b in DISTANCE_BINS}

    for i, pa in enumerate(eligible):
        undirected_dists = compute_undirected_distances(
            nodes, edges, pa["target_id"]
        )
        directed_dists = compute_graph_distances(
            nodes, edges, pa["target_id"]
        )

        for j, pb in enumerate(eligible):
            if j <= i:
                continue
            if pa["target_id"] == pb["target_id"]:
                continue

            ud = undirected_dists.get(pb["target_id"], -1)
            if ud < 1:
                continue

            dd_ab = directed_dists.get(pb["target_id"], -1)
            dd_ba_dists = compute_graph_distances(
                nodes, edges, pb["target_id"]
            )
            dd_ba = dd_ba_dists.get(pa["target_id"], -1)

            pair = {
                "probe_a": pa,
                "probe_b": pb,
                "undirected_distance": ud,
                "directed_distance_ab": dd_ab,
                "directed_distance_ba": dd_ba,
            }

            for (lo, hi) in DISTANCE_BINS:
                if lo <= ud <= hi:
                    pairs_by_bin[(lo, hi)].append(pair)
                    break

    # Sample from each bin
    selected = []
    for bin_key, candidates in pairs_by_bin.items():
        if candidates:
            k = min(PAIRS_PER_DISTANCE_BIN, len(candidates))
            selected.extend(rng.sample(candidates, k))

    return selected


# ── Main runner ──────────────────────────────────────────────────────────

def run_compound_analysis(
    client: LLMClient,
    question_data: dict,
    qid: str,
    rng: random.Random,
) -> dict:
    """Run compound probe analysis for a single question."""
    nodes = question_data["nodes"]
    edges = question_data["edges"]
    initial_prob = question_data["initial_probability"]
    question_text = question_data["question_text"]
    probe_results = question_data.get("probe_results", [])

    pairs = select_probe_pairs(probe_results, nodes, edges, rng)

    if not pairs:
        return {
            "question_id": qid,
            "error": "No valid probe pairs found",
            "compound_results": [],
        }

    compound_results = []
    for pair in pairs:
        pa = pair["probe_a"]
        pb = pair["probe_b"]

        # Randomize presentation order
        order = rng.choice(["AB", "BA"])

        prompt = build_compound_probe_prompt(
            question_text, initial_prob, nodes, edges, pa, pb, order,
        )

        text, ok = client.call_single(COMPOUND_SYSTEM, prompt)
        client.rate_limit_wait()

        if not ok:
            compound_results.append({
                "probe_a_type": pa["probe_type"],
                "probe_a_target": pa["target_id"],
                "probe_b_type": pb["probe_type"],
                "probe_b_target": pb["target_id"],
                "success": False,
                "error": "API call failed",
            })
            continue

        data = parse_json_response(text)
        if data is None:
            compound_results.append({
                "probe_a_type": pa["probe_type"],
                "probe_a_target": pa["target_id"],
                "probe_b_type": pb["probe_type"],
                "probe_b_target": pb["target_id"],
                "success": False,
                "error": "JSON parse failed",
                "raw_response": text[:500],
            })
            continue

        updated_prob = data.get("updated_probability")
        if updated_prob is not None:
            updated_prob = max(0.01, min(0.99, float(updated_prob)))

        shift_ab = abs(updated_prob - initial_prob) if updated_prob else None
        shift_a = pa.get("absolute_shift")
        shift_b = pb.get("absolute_shift")

        interaction = None
        if shift_ab is not None and shift_a is not None and shift_b is not None:
            interaction = shift_ab - (shift_a + shift_b)

        compound_results.append({
            "probe_a_type": pa["probe_type"],
            "probe_a_target": pa["target_id"],
            "probe_a_shift": shift_a,
            "probe_b_type": pb["probe_type"],
            "probe_b_target": pb["target_id"],
            "probe_b_shift": shift_b,
            "presentation_order": order,
            "undirected_distance": pair["undirected_distance"],
            "directed_distance_ab": pair["directed_distance_ab"],
            "directed_distance_ba": pair["directed_distance_ba"],
            "success": True,
            "updated_probability": updated_prob,
            "compound_shift": shift_ab,
            "sum_individual_shifts": (shift_a + shift_b) if shift_a is not None and shift_b is not None else None,
            "interaction": interaction,
            "reasoning": data.get("reasoning", ""),
        })

    return {
        "question_id": qid,
        "question_text": question_text,
        "initial_probability": initial_prob,
        "n_nodes": len(nodes),
        "n_edges": len(edges),
        "n_pairs": len(pairs),
        "compound_results": compound_results,
    }


def main():
    parser = argparse.ArgumentParser(description="Compound probe interaction analysis")
    parser.add_argument("--model", type=str, default="llama-70b",
                        help="Model to use (default: llama-70b)")
    parser.add_argument("--source-dir", type=str, default=None)
    parser.add_argument("--output-dir", type=str, default=None)
    parser.add_argument("--max-questions", type=int, default=100)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    rng = random.Random(args.seed)

    model_dir_map = {
        "llama": "llama_one_turn",
        "llama-70b": "70b_one_turn",
        "deepseek": "deepseek_one_turn",
        "qwen": "qwen_one_turn",
        "gemini-flash-lite": "gemini_flash_lite_one_turn",
    }

    if args.source_dir:
        source_dir = Path(args.source_dir)
    else:
        dirname = model_dir_map.get(args.model, f"{args.model}_one_turn")
        source_dir = CAUSAL_DIR / dirname

    output_dir = Path(args.output_dir) if args.output_dir else source_dir
    results_dir = output_dir / "compound_results"
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
        for f in (results_dir).glob("*.json"):
            with open(f) as fh:
                d = json.load(fh)
            completed.add(d.get("question_id", f.stem.replace("q_", "")))
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
        max_tokens=1000,
    )

    print(f"\nCOMPOUND PROBE ANALYSIS")
    print(f"{'='*60}")
    print(f"Model: {model}")
    print(f"Source: {source_dir}")
    print(f"Output: {results_dir}")
    print(f"Temperature: {args.temperature}")
    print(f"Seed: {args.seed}")

    n_done = 0
    total_pairs = 0
    total_success = 0

    for qid, qdata in sorted(questions.items()):
        if n_done >= args.max_questions:
            break
        if qid in completed:
            n_done += 1
            continue

        print(f"\n[{n_done+1}/{min(len(questions), args.max_questions)}] {qid[:40]}...", end=" ")

        result = run_compound_analysis(client, qdata, qid, rng)
        n_pairs = len(result.get("compound_results", []))
        n_success = sum(1 for r in result.get("compound_results", []) if r.get("success"))
        total_pairs += n_pairs
        total_success += n_success
        print(f"{n_success}/{n_pairs} pairs")

        out_path = results_dir / f"q_{qid}.json"
        with open(out_path, "w") as fh:
            json.dump(result, fh, indent=2)

        n_done += 1

    # Summary statistics
    print(f"\n{'='*60}")
    print(f"COMPOUND PROBE ANALYSIS COMPLETE")
    print(f"{'='*60}")
    print(f"Questions processed: {n_done}")
    print(f"Total pairs: {total_pairs} ({total_success} successful)")

    # Quick aggregate
    all_results = []
    for f in results_dir.glob("*.json"):
        with open(f) as fh:
            d = json.load(fh)
        for cr in d.get("compound_results", []):
            if cr.get("success") and cr.get("interaction") is not None:
                all_results.append(cr)

    if all_results:
        from collections import defaultdict
        by_dist = defaultdict(list)
        for cr in all_results:
            by_dist[cr["undirected_distance"]].append(cr["interaction"])

        print(f"\nInteraction by graph distance (super-additive > 0):")
        for d in sorted(by_dist.keys()):
            vals = by_dist[d]
            print(f"  distance {d}: mean interaction = {np.mean(vals):+.4f} "
                  f"(median = {np.median(vals):+.4f}, n={len(vals)})")

        # Order effect check
        by_order = defaultdict(list)
        for cr in all_results:
            by_order[cr["presentation_order"]].append(cr["compound_shift"])
        print(f"\nOrder effect check:")
        for order, vals in sorted(by_order.items()):
            print(f"  {order}: mean compound shift = {np.mean(vals):.4f} (n={len(vals)})")

    print(f"\nResults saved to {results_dir}")


if __name__ == "__main__":
    main()
