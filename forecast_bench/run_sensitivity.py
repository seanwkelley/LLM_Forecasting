"""
Belief Sensitivity Pipeline -- Causal network probing of LLM forecasts.

Four-stage pipeline:
  1. Causal Forecast:  LLM produces probability + causal DAG
  2. Network Analysis:  Graph metrics, probe target selection (16-18 targets)
  3. Probe Generation: LLM generates targeted challenges for each target
  4. Probed Forecast:   Independent LLM calls measure probability shifts

Usage:
    # Quick smoke test (2 questions)
    python forecast_bench/run_sensitivity.py --max-questions 2 --condition one-turn

    # Full run (51 questions, one-turn probing)
    python forecast_bench/run_sensitivity.py --model llama-70b --max-questions 51 \\
        --condition one-turn --output-dir outputs/sensitivity/causal/70b_one_turn

    # Resume an interrupted run
    python forecast_bench/run_sensitivity.py --model llama-70b --max-questions 51 \\
        --condition one-turn --output-dir outputs/sensitivity/causal/70b_one_turn --resume

Models (via OpenRouter):
    llama       -> meta-llama/llama-3.1-8b-instruct
    llama-70b   -> meta-llama/llama-3.3-70b-instruct
    deepseek    -> deepseek/deepseek-chat-v3-0324
    claude      -> anthropic/claude-sonnet-4
    gpt4        -> openai/gpt-4-turbo
    qwen        -> qwen/qwen-2.5-72b-instruct
    gemini      -> google/gemini-2.5-flash
    mistral     -> mistralai/mistral-small-3.2-24b-instruct
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from forecast_bench.llm_client import LLMClient, parse_json_response
from forecast_bench.questions import load_forecastbench_questions
from forecast_bench.prompts_causal import (
    CAUSAL_FORECAST_SYSTEM,
    CAUSAL_PROBE_GENERATION_SYSTEM,
    CAUSAL_PROBED_FORECAST_SYSTEM,
    CAUSAL_PROBE_TYPES,
    PROBE_CATEGORIES,
    build_causal_forecast_prompt,
    build_causal_probe_prompt,
    build_causal_probed_forecast_prompt,
    build_causal_conversational_probe_message,
)
from forecast_bench.network_analysis import analyze_network, plot_causal_network

MODEL_MAP = {
    "llama": "meta-llama/llama-3.1-8b-instruct",
    "llama-70b": "meta-llama/llama-3.3-70b-instruct",
    "deepseek": "deepseek/deepseek-chat-v3-0324",
    "claude": "anthropic/claude-sonnet-4",
    "gpt4": "openai/gpt-4-turbo",
    "qwen": "qwen/qwen3-235b-a22b-2507",
    "gemini": "google/gemini-2.5-flash",
    "mistral": "mistralai/mistral-small-3.2-24b-instruct",
    "gpt5nano": "openai/gpt-5-nano",
    "gpt-oss": "openai/gpt-oss-120b:nitro",
    "gemini-flash-lite": "google/gemini-2.5-flash-lite",
    "gemini-flash-lite-nitro": "google/gemini-2.5-flash-lite:nitro",
    "qwen-32b": "qwen/qwen3-32b:nitro",
}


def _parse_probe_result(
    client: LLMClient,
    probe: dict,
    reference_prob: float,
    text: str,
    ok: bool,
) -> dict:
    """Parse a probed forecast response into a result dict."""
    result = {
        "probe_type": probe.get("probe_type", ""),
        "target_reason_id": probe.get("target_reason_id"),
        "probe_text": probe.get("probe_text", ""),
        "probe_generated": probe.get("generated", True),
        "success": False,
        "updated_probability": None,
        "absolute_shift": None,
        "shift_direction": None,
        "reasoning": "",
        "raw_response": text if ok else "",
    }

    if not ok:
        return result

    data = parse_json_response(text)
    if data is None or not isinstance(data, dict):
        client.stats.parse_failures += 1
        return result

    updated = data.get("updated_probability")
    if updated is None:
        client.stats.parse_failures += 1
        return result

    updated = max(0.01, min(0.99, float(updated)))
    shift = updated - reference_prob

    result["success"] = True
    result["updated_probability"] = updated
    result["absolute_shift"] = abs(shift)
    result["shift_direction"] = data.get("shift_direction", "")
    result["reasoning"] = data.get("reasoning", "")

    return result


# =============================================================================
# CAUSAL MODE — STAGE 1: CAUSAL FORECAST
# =============================================================================

def run_causal_forecast(
    client: LLMClient,
    question: dict,
    node_range: tuple[int, int] = (6, 10),
    max_retries: int = 3,
) -> dict | None:
    """Get initial probability + causal network for a question.

    Retries up to ``max_retries`` times on parse failures before giving up.

    Returns
    -------
    Parsed response dict with probability, nodes, edges, reasoning -- or None on failure.
    """
    user_prompt = build_causal_forecast_prompt(question["question"], node_range=node_range)

    for attempt in range(1 + max_retries):
        text, ok = client.call_single(CAUSAL_FORECAST_SYSTEM, user_prompt)
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

        # Validate response is a dict
        if not isinstance(data, dict):
            if attempt < max_retries:
                client.rate_limit_wait()
                continue
            client.stats.parse_failures += 1
            return None

        # Validate required fields
        prob = data.get("probability")
        nodes = data.get("nodes")
        edges = data.get("edges")
        if prob is None or not isinstance(nodes, list) or not isinstance(edges, list):
            if attempt < max_retries:
                client.rate_limit_wait()
                continue
            client.stats.parse_failures += 1
            return None

        break  # valid response

    # Clamp probability
    prob = max(0.01, min(0.99, float(prob)))
    data["probability"] = prob

    # Validate node structure
    node_ids = set()
    outcome_count = 0
    for n in nodes:
        if not isinstance(n, dict) or "id" not in n:
            client.stats.parse_failures += 1
            return None
        n.setdefault("description", "")
        n.setdefault("role", "factor")
        node_ids.add(n["id"])
        if n["role"] == "outcome":
            outcome_count += 1

    if outcome_count != 1:
        client.stats.parse_failures += 1
        return None

    factor_nodes = [n for n in nodes if n["role"] != "outcome"]
    if len(factor_nodes) < 2:
        client.stats.parse_failures += 1
        return None

    # Validate edge structure
    for e in edges:
        if not isinstance(e, dict):
            client.stats.parse_failures += 1
            return None
        e.setdefault("mechanism", "")
        if e.get("from") not in node_ids or e.get("to") not in node_ids:
            client.stats.parse_failures += 1
            return None

    # Reject graphs with disconnected nodes (zero in-degree AND zero out-degree)
    edge_node_ids = set(e.get("from") for e in edges) | set(e.get("to") for e in edges)
    if any(n["id"] not in edge_node_ids for n in nodes):
        client.stats.parse_failures += 1
        return None

    # Validate outcome has at least 1 incoming edge
    outcome_id = next(n["id"] for n in nodes if n["role"] == "outcome")
    outcome_has_incoming = any(e["to"] == outcome_id for e in edges)
    if not outcome_has_incoming:
        client.stats.parse_failures += 1
        return None

    return data


# =============================================================================
# CAUSAL MODE — STAGE 2: PROBE GENERATION
# =============================================================================

def run_causal_probe_generation(
    client: LLMClient,
    question: dict,
    initial_prob: float,
    nodes: list[dict],
    edges: list[dict],
    probe_targets: list[dict],
) -> list[dict]:
    """Generate one probe per network-analysis target.

    Returns
    -------
    List of probe dicts, each with probe_text, probe_type, target_id, and
    the original probe_target metadata.
    """
    probes = []
    for target in probe_targets:
        probe = _generate_single_causal_probe(
            client, question, initial_prob, nodes, edges, target,
        )
        probes.append(probe)

    return probes


def _generate_single_causal_probe(
    client: LLMClient,
    question: dict,
    initial_prob: float,
    nodes: list[dict],
    edges: list[dict],
    probe_target: dict,
) -> dict:
    """Generate a single causal probe for one target."""
    user_prompt = build_causal_probe_prompt(
        question["question"], initial_prob, nodes, edges, probe_target,
    )

    fallback_text = f"What if '{probe_target.get('description', 'this element')}' is wrong?"

    # Retry until we get a valid probe (up to 10 attempts)
    for _probe_attempt in range(10):
        text, ok = client.call_single(CAUSAL_PROBE_GENERATION_SYSTEM, user_prompt)
        client.rate_limit_wait()

        if not ok:
            continue

        data = parse_json_response(text)
        if data is not None:
            break
    else:
        # All attempts failed — use fallback
        client.stats.parse_failures += 1
        return {
            "probe_text": fallback_text,
            "probe_type": probe_target["probe_type"],
            "target_id": probe_target["target_id"],
            "generated": False,
            **{k: probe_target[k] for k in ("target_type", "importance", "centrality_rank", "on_critical_path")},
        }

    if not isinstance(data, dict):
        client.stats.parse_failures += 1
        return {
            "probe_text": fallback_text,
            "probe_type": probe_target["probe_type"],
            "target_id": probe_target["target_id"],
            "generated": False,
            **{k: probe_target[k] for k in ("target_type", "importance", "centrality_rank", "on_critical_path")},
        }

    data.setdefault("probe_type", probe_target["probe_type"])
    data.setdefault("target_id", probe_target["target_id"])
    data["generated"] = True
    # Carry over structural metadata from target
    data["target_type"] = probe_target["target_type"]
    data["importance"] = probe_target["importance"]
    data["centrality_rank"] = probe_target["centrality_rank"]
    data["on_critical_path"] = probe_target["on_critical_path"]
    data["description"] = probe_target["description"]
    return data


# =============================================================================
# CAUSAL MODE — STAGE 3: PROBED FORECASTS
# =============================================================================

def run_causal_independent_probing(
    client: LLMClient,
    question: dict,
    initial_prob: float,
    nodes: list[dict],
    edges: list[dict],
    probes: list[dict],
) -> list[dict]:
    """Independent condition for causal mode: fresh call per probe.

    Returns
    -------
    List of result dicts per probe.
    """
    results = []
    for probe in probes:
        # Find the matching probe_target info (carried in probe dict)
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

        # Retry until success (up to 10 rounds of 3 attempts each)
        result = None
        for _round in range(10):
            for _attempt in range(3):
                text, ok = client.call_single(CAUSAL_PROBED_FORECAST_SYSTEM, user_prompt)
                client.rate_limit_wait()
                result = _parse_probe_result(client, probe, initial_prob, text, ok)
                if result.get("success"):
                    break
            if result.get("success"):
                break
        # Enrich with causal metadata
        result["target_id"] = probe.get("target_id", "")
        result["target_type"] = probe.get("target_type", "")
        result["target_importance"] = probe.get("importance", 0.0)
        result["target_centrality_rank"] = probe.get("centrality_rank", 0)
        result["target_on_critical_path"] = probe.get("on_critical_path", False)
        result["probe_category"] = PROBE_CATEGORIES.get(probe.get("probe_type", ""), "structural")
        results.append(result)

    return results


def run_causal_conversational_probing(
    client: LLMClient,
    question: dict,
    initial_prob: float,
    nodes: list[dict],
    edges: list[dict],
    probes: list[dict],
) -> list[dict]:
    """Conversational condition for causal mode: growing messages array.

    Returns
    -------
    List of result dicts per probe.
    """
    from forecast_bench.prompts_causal import _format_network_context

    network_text = _format_network_context(nodes, edges)

    initial_assistant = json.dumps({
        "probability": initial_prob,
        "nodes": nodes,
        "edges": edges,
        "reasoning": f"Initial causal forecast for: {question['question']}",
    })

    messages = [
        {"role": "system", "content": CAUSAL_PROBED_FORECAST_SYSTEM},
        {
            "role": "user",
            "content": (
                f'Forecast this question: "{question["question"]}"\n\n'
                f"Provide your probability estimate and causal network."
            ),
        },
        {"role": "assistant", "content": initial_assistant},
    ]

    results = []
    current_prob = initial_prob

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

        probe_user_msg = build_causal_conversational_probe_message(
            probe, probe_target, current_prob,
        )
        messages.append({"role": "user", "content": probe_user_msg})

        text, ok = client.call(messages)
        client.rate_limit_wait()

        result = _parse_probe_result(client, probe, current_prob, text, ok)
        # Enrich with causal metadata
        result["target_id"] = probe.get("target_id", "")
        result["target_type"] = probe.get("target_type", "")
        result["target_importance"] = probe.get("importance", 0.0)
        result["target_centrality_rank"] = probe.get("centrality_rank", 0)
        result["target_on_critical_path"] = probe.get("on_critical_path", False)
        result["probe_category"] = PROBE_CATEGORIES.get(probe.get("probe_type", ""), "structural")
        results.append(result)

        if ok and text:
            messages.append({"role": "assistant", "content": text})
            if result.get("updated_probability") is not None:
                current_prob = result["updated_probability"]

    return results


# =============================================================================
# OUTPUT HELPERS
# =============================================================================

CAUSAL_CSV_FIELDS = [
    "question_id", "question_text", "condition", "initial_probability",
    "probe_index", "probe_type", "probe_category",
    "target_id", "target_description",
    "target_importance", "target_centrality_rank", "target_on_critical_path",
    "probe_text", "probe_generated",
    "updated_probability", "absolute_shift", "shift_direction",
    "success", "reasoning",
    "n_nodes", "n_edges", "graph_density",
]

QUESTION_SUMMARY_FIELDS = [
    "question_id", "question_text", "source", "condition",
    "initial_probability", "n_probes", "n_successful",
    "mean_absolute_shift", "max_absolute_shift",
]


def save_causal_sensitivity_row(
    writer, question, condition, initial_prob, probe, result, probe_idx, network_analysis_dict,
):
    """Write one row to the causal sensitivity CSV."""
    writer.writerow({
        "question_id": question["id"],
        "question_text": question["question"][:200],
        "condition": condition,
        "initial_probability": f"{initial_prob:.4f}",
        "probe_index": probe_idx,
        "probe_type": result.get("probe_type", probe.get("probe_type", "")),
        "probe_category": result.get("probe_category", PROBE_CATEGORIES.get(probe.get("probe_type", ""), "")),
        "target_id": result.get("target_id", probe.get("target_id", "")),
        "target_description": probe.get("description", "")[:200],
        "target_importance": f"{result.get('target_importance', 0.0):.4f}",
        "target_centrality_rank": result.get("target_centrality_rank", 0),
        "target_on_critical_path": result.get("target_on_critical_path", False),
        "probe_text": result.get("probe_text", "")[:300],
        "probe_generated": result.get("probe_generated", True),
        "updated_probability": f"{result['updated_probability']:.4f}" if result.get("updated_probability") is not None else "",
        "absolute_shift": f"{result['absolute_shift']:.4f}" if result.get("absolute_shift") is not None else "",
        "shift_direction": result.get("shift_direction", ""),
        "success": result.get("success", False),
        "reasoning": result.get("reasoning", "")[:300],
        "n_nodes": network_analysis_dict.get("n_nodes", 0),
        "n_edges": network_analysis_dict.get("n_edges", 0),
        "graph_density": f"{network_analysis_dict.get('density', 0.0):.4f}",
    })


def save_question_json(output_dir: Path, question_id: str, data: dict):
    """Save full detail for one question to JSON."""
    q_dir = output_dir / "question_results"
    q_dir.mkdir(parents=True, exist_ok=True)
    path = q_dir / f"q_{question_id}.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_completed_questions(output_dir: Path) -> set[str]:
    """Check which questions already have saved results (for resume)."""
    q_dir = output_dir / "question_results"
    if not q_dir.exists():
        return set()
    return {
        p.stem.replace("q_", "")
        for p in q_dir.glob("q_*.json")
    }


# =============================================================================
# MAIN PIPELINE
# =============================================================================

def _get_api_key() -> str:
    """Resolve OpenRouter API key from environment or config modules."""
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


def run_pipeline(args):
    """Run the causal network belief sensitivity pipeline."""
    model = MODEL_MAP.get(args.model, args.model)

    api_key = _get_api_key()
    if not api_key:
        print("[ERROR] OPENROUTER_API_KEY not set.")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"CAUSAL NETWORK BELIEF SENSITIVITY")
    print(f"{'='*60}")
    print(f"Model: {model}")
    print(f"Temperature: {args.temperature}")
    print(f"Condition: {args.condition}")
    print(f"Max questions: {args.max_questions}")
    print(f"Seed: {args.seed}")

    questions = load_forecastbench_questions(
        max_questions=args.max_questions,
        seed=args.seed,
        questions_file=args.questions_file,
    )
    print(f"Loaded {len(questions)} questions\n")

    if not questions:
        print("[ERROR] No questions loaded.")
        sys.exit(1)

    conditions = []
    if args.condition in ("one-turn", "both"):
        conditions.append("one-turn")
    if args.condition in ("multi-turn", "both"):
        conditions.append("multi-turn")

    client = LLMClient(
        api_key=api_key,
        model=model,
        temperature=args.temperature,
        max_tokens=2000,  # larger for causal network JSON (verbose models need >1200)
    )

    # Parse node range
    node_range = tuple(args.node_range) if hasattr(args, 'node_range') and args.node_range else (6, 10)

    # Bump max_tokens for larger networks (12-16 node DAGs need ~2500+ tokens)
    if node_range[1] > 10:
        client.max_tokens = 4000
    print(f"Node range: {node_range[0]}-{node_range[1]} factors")

    # Stages 1, 1.5, 2 (shared across conditions)
    shared_results = _run_shared_stages_causal(client, questions, args, node_range=node_range)

    # Stage 3 per condition
    for condition in conditions:
        model_short = args.model if args.model in MODEL_MAP else model.split("/")[-1]
        output_dir = Path(args.output_dir or f"outputs/sensitivity_causal_{model_short}_{condition}")
        output_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n{'-'*60}")
        print(f"CONDITION: {condition.upper()}")
        print(f"Output: {output_dir}")
        print(f"{'-'*60}")

        completed = get_completed_questions(output_dir) if args.resume else set()
        if completed:
            print(f"Resuming: {len(completed)} questions already complete")

        csv_path = output_dir / "sensitivity_results.csv"
        csv_mode = "a" if args.resume and csv_path.exists() else "w"

        with open(csv_path, csv_mode, newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CAUSAL_CSV_FIELDS)
            if csv_mode == "w":
                writer.writeheader()

            question_summaries = []

            for q_idx, question in enumerate(questions):
                if question["id"] in completed:
                    print(f"  [{q_idx+1}/{len(questions)}] {question['id']} -- skipped (resume)")
                    continue

                shared = shared_results.get(question["id"])
                if shared is None:
                    print(f"  [{q_idx+1}/{len(questions)}] {question['id']} -- skipped (stages 1-2 failed)")
                    continue

                initial_prob = shared["initial_probability"]
                nodes = shared["nodes"]
                edges = shared["edges"]
                probes = shared["probes"]
                net_analysis = shared["network_analysis"]

                print(f"  [{q_idx+1}/{len(questions)}] {question['id']} "
                      f"(p={initial_prob:.2f}, {net_analysis['n_nodes']}N/{net_analysis['n_edges']}E, "
                      f"{len(probes)} probes) ...", end=" ")

                # Stage 3
                if condition == "one-turn":
                    probe_results = run_causal_independent_probing(
                        client, question, initial_prob, nodes, edges, probes,
                    )
                else:
                    probe_results = run_causal_conversational_probing(
                        client, question, initial_prob, nodes, edges, probes,
                    )

                # Save rows to CSV
                for pi, result in enumerate(probe_results):
                    save_causal_sensitivity_row(
                        writer, question, condition, initial_prob,
                        probes[pi], result, pi, net_analysis,
                    )
                f.flush()

                # Compute question summary
                successful = [r for r in probe_results if r.get("success")]
                shifts = [r["absolute_shift"] for r in successful if r.get("absolute_shift") is not None]

                summary = {
                    "question_id": question["id"],
                    "question_text": question["question"],
                    "source": question.get("source", ""),
                    "condition": condition,
                    "initial_probability": initial_prob,
                    "n_probes": len(probe_results),
                    "n_successful": len(successful),
                    "mean_absolute_shift": sum(shifts) / len(shifts) if shifts else None,
                    "max_absolute_shift": max(shifts) if shifts else None,
                }
                question_summaries.append(summary)

                # Save per-question JSON (includes full network analysis)
                q_detail = {
                    **shared,
                    "condition": condition,
                    "probe_results": probe_results,
                    "summary": summary,
                }
                save_question_json(output_dir, question["id"], q_detail)

                n_ok = len(successful)
                mean_s = summary["mean_absolute_shift"]
                print(f"{n_ok}/{len(probe_results)} ok, "
                      f"mean shift={mean_s:.3f}" if mean_s is not None else "no shifts")

        _save_question_summary(output_dir, question_summaries)

        print(f"\nCondition '{condition}' complete.")
        print(f"  Sensitivity CSV: {csv_path}")
        print(f"  Question summaries: {output_dir / 'question_summary.csv'}")

    # Final stats
    print(f"\n{'='*60}")
    print("API CALL STATISTICS")
    print(json.dumps(client.stats.to_dict(), indent=2))
    print(f"{'='*60}")


def _run_shared_stages_causal(
    client: LLMClient,
    questions: list[dict],
    args,
    node_range: tuple[int, int] = (4, 8),
) -> dict[str, dict]:
    """Run Stages 1, 1.5, 2 for causal mode.

    Stage 1:   Causal forecast (LLM -> probability + causal graph)
    Stage 1.5: Network analysis (pure computation -> metrics + targets)
    Stage 2:   Probe generation (LLM -> one probe per target)

    Returns
    -------
    Dict mapping question_id to shared data including network_analysis.
    """
    print("STAGES 1-2: Causal forecast + network analysis + probe generation")
    print("-" * 60)

    cache_dir = Path(args.output_dir or "outputs") / "_shared_stages_causal"
    cache_dir.mkdir(parents=True, exist_ok=True)

    results = {}

    for q_idx, question in enumerate(questions):
        cache_path = cache_dir / f"q_{question['id']}.json"

        if args.resume and cache_path.exists():
            try:
                cached = json.loads(cache_path.read_text(encoding="utf-8"))
                results[question["id"]] = cached
                # Generate visualization if missing (retroactive for older caches)
                viz_dir = cache_dir.parent / "network_plots"
                viz_path = viz_dir / f"q_{question['id']}_network.png"
                if not viz_path.exists() and "nodes" in cached and "edges" in cached:
                    try:
                        net_analysis = analyze_network(cached["nodes"], cached["edges"])
                        plot_causal_network(
                            cached["nodes"], cached["edges"], net_analysis,
                            save_path=viz_path,
                            title=cached.get("question_text", "")[:100],
                            initial_prob=cached.get("initial_probability"),
                        )
                    except Exception:
                        pass
                print(f"  [{q_idx+1}/{len(questions)}] {question['id']} -- cached")
                continue
            except (json.JSONDecodeError, KeyError):
                pass

        print(f"  [{q_idx+1}/{len(questions)}] {question['id'][:40]}...", end=" ")

        # Stage 1: Causal forecast (retry indefinitely)
        forecast = None
        stage1_attempts = 0
        while forecast is None:
            stage1_attempts += 1
            forecast = run_causal_forecast(client, question, node_range=node_range)
            client.rate_limit_wait()
            if forecast is None:
                print(f"RETRY (stage 1 attempt {stage1_attempts} failed)", end=" ")
                if stage1_attempts >= 10:
                    print("GIVING UP after 10 attempts")
                    break
        if forecast is None:
            continue

        initial_prob = forecast["probability"]
        nodes = forecast["nodes"]
        edges = forecast["edges"]
        print(f"p={initial_prob:.2f}, {len(nodes)}N/{len(edges)}E", end=" -> ")

        # Stage 1.5: Network analysis (no LLM call)
        net_analysis = analyze_network(nodes, edges)
        net_dict = net_analysis.to_dict()
        probe_targets = [pt.to_dict() for pt in net_analysis.probe_targets]
        print(f"{len(probe_targets)} targets", end=" -> ")

        # Save network visualization
        viz_dir = cache_dir.parent / "network_plots"
        viz_path = viz_dir / f"q_{question['id']}_network.png"
        try:
            plot_causal_network(
                nodes, edges, net_analysis,
                save_path=viz_path,
                title=question["question"][:100],
                initial_prob=initial_prob,
            )
        except Exception as e:
            print(f"[viz warning: {e}]", end=" ")

        # Stage 2: Probe generation
        probes = run_causal_probe_generation(
            client, question, initial_prob, nodes, edges, probe_targets,
        )
        print(f"{len(probes)} probes")

        shared = {
            "question_id": question["id"],
            "question_text": question["question"],
            "source": question.get("source", ""),
            "initial_probability": initial_prob,
            "nodes": nodes,
            "edges": edges,
            "reasoning": forecast.get("reasoning", ""),
            "network_analysis": net_dict,
            "probe_targets": probe_targets,
            "probes": probes,
        }

        results[question["id"]] = shared
        cache_path.write_text(json.dumps(shared, indent=2), encoding="utf-8")

    print(f"\nStages 1-2 complete: {len(results)}/{len(questions)} questions ready\n")
    return results


def _save_question_summary(output_dir: Path, summaries: list[dict]):
    """Save question-level summary CSV."""
    if not summaries:
        return
    path = output_dir / "question_summary.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=QUESTION_SUMMARY_FIELDS)
        writer.writeheader()
        for s in summaries:
            row = {}
            for field in QUESTION_SUMMARY_FIELDS:
                val = s.get(field, "")
                if isinstance(val, float) and val is not None:
                    row[field] = f"{val:.4f}"
                elif isinstance(val, str):
                    row[field] = val[:200]
                else:
                    row[field] = val
            writer.writerow(row)


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Belief Sensitivity Analysis -- causal network probing of LLM forecasts",
    )
    parser.add_argument(
        "--model", default="llama",
        help="Model name or OpenRouter model ID (default: llama)",
    )
    parser.add_argument(
        "--condition", default="one-turn",
        choices=["one-turn", "multi-turn", "both"],
        help="Experimental condition (default: one-turn)",
    )
    parser.add_argument(
        "--max-questions", type=int, default=100,
        help="Maximum number of questions to process (default: 100)",
    )
    parser.add_argument(
        "--temperature", type=float, default=0.7,
        help="Sampling temperature (default: 0.7)",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for question selection (default: 42)",
    )
    parser.add_argument(
        "--output-dir", default=None,
        help="Output directory (default: outputs/sensitivity_{model}_{condition})",
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="Resume from previous run (skip completed questions)",
    )
    parser.add_argument(
        "--questions-file", default=None,
        help="Path to local JSON file with questions (skips HuggingFace)",
    )
    parser.add_argument(
        "--node-range", type=int, nargs=2, default=None, metavar=("MIN", "MAX"),
        help="Min and max factor nodes for causal DAG (default: 6 10)",
    )

    args = parser.parse_args()
    run_pipeline(args)


if __name__ == "__main__":
    main()
