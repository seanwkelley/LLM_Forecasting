"""
Neutral-probe ablation: regenerate probes WITHOUT importance labels,
then re-run Stage 3 with a neutral system prompt.

Reuses existing DAGs and probe targets from completed runs.
Only re-does Stage 2 (probe generation) and Stage 3 (probed forecast).

Usage:
    python -m forecast_bench.run_neutral_probes --model llama-70b --max-questions 100
    python -m forecast_bench.run_neutral_probes --model llama-70b --resume
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from forecast_bench.llm_client import LLMClient, parse_json_response
from forecast_bench.prompts_causal import (
    CAUSAL_PROBE_GENERATION_SYSTEM,
    PROBE_CATEGORIES,
    _format_network_context,
    CAUSAL_PROBE_TYPES,
)
from forecast_bench.run_sensitivity import (
    MODEL_MAP,
    CAUSAL_CSV_FIELDS,
    save_causal_sensitivity_row,
    _parse_probe_result,
)
from forecast_bench.network_analysis import analyze_network


# ── Neutral prompts (no importance labels) ──────────────────────────────

NEUTRAL_PROBED_FORECAST_SYSTEM = """\
You are an expert forecaster updating your estimate in light of new information \
about your causal model.

When presented with new information, consider how it affects your causal network \
and update your probability estimate accordingly.

Respond with ONLY valid JSON. No other text."""


def _build_neutral_probe_prompt(
    question: str,
    probability: float,
    nodes: list[dict],
    edges: list[dict],
    probe_target: dict,
) -> str:
    """Build probe generation prompt WITHOUT importance labels."""
    network_context = _format_network_context(nodes, edges)
    probe_type = probe_target["probe_type"]
    target_id = probe_target["target_id"]
    target_desc = probe_target["description"]

    # All instructions use uniform framing — no HIGH/LOW/CRITICAL/PERIPHERAL
    type_instructions = {
        "node_negate_high": (
            f"Create a direct negation of the causal factor '{target_id}' "
            f"({target_desc}). "
            f"Provide a specific, plausible argument for why this factor might not "
            f"matter or why the opposite might be true."
        ),
        "node_negate_medium": (
            f"Create a direct negation of the causal factor '{target_id}' "
            f"({target_desc}). "
            f"Argue why this factor might be wrong or irrelevant, with a specific "
            f"mechanism or piece of evidence."
        ),
        "node_negate_low": (
            f"Create a direct negation of the causal factor '{target_id}' "
            f"({target_desc}). "
            f"Argue why this factor might be wrong or irrelevant."
        ),
        "node_strengthen": (
            f"Create a plausible piece of evidence or argument that REINFORCES "
            f"the causal factor '{target_id}' ({target_desc}), making it even "
            f"more likely to be true and more causally important. "
            f"Provide a strong new data point, expert "
            f"endorsement, or development that supports this factor's "
            f"role in the causal network."
        ),
        "node_strengthen_medium": (
            f"Create a plausible piece of evidence or argument that REINFORCES "
            f"the causal factor '{target_id}' ({target_desc}), making it even "
            f"more likely to be true and more causally important. "
            f"Provide a specific piece of evidence "
            f"or development that supports this factor."
        ),
        "node_strengthen_low": (
            f"Create a plausible piece of evidence or argument that REINFORCES "
            f"the causal factor '{target_id}' ({target_desc}), making it even "
            f"more likely to be true and more causally important. "
            f"Provide evidence that supports this factor."
        ),
        "edge_negate_critical": (
            f"Challenge the causal link '{target_id}' ({target_desc}). "
            f"Argue why this causal mechanism might be broken, spurious, or "
            f"much weaker than assumed. Provide a specific counter-mechanism "
            f"or piece of evidence."
        ),
        "edge_negate_peripheral": (
            f"Challenge the causal link '{target_id}' ({target_desc}). "
            f"Argue why this causal mechanism might not hold."
        ),
        "edge_strengthen_critical": (
            f"Provide evidence or argument that REINFORCES the causal link "
            f"'{target_id}' ({target_desc}). "
            f"Argue why this causal mechanism "
            f"is even stronger than assumed, with a specific piece of evidence "
            f"or recent development that confirms this link."
        ),
        "edge_strengthen_peripheral": (
            f"Provide evidence or argument that REINFORCES the causal link "
            f"'{target_id}' ({target_desc}). "
            f"Argue why this causal mechanism is "
            f"stronger than assumed."
        ),
        "edge_reverse": (
            f"Argue that the causal link '{target_id}' ({target_desc}) "
            f"actually runs in the OPPOSITE DIRECTION. Instead of "
            f"{target_id.replace('->', ' causing ')}, argue that the causal "
            f"arrow should be reversed. Provide a specific mechanism for "
            f"reverse causation."
        ),
        "edge_spurious": (
            f"The forecaster's causal network does NOT include a direct link "
            f"'{target_id}'. Argue that this missing causal link DOES exist "
            f"and is important. Describe a specific causal mechanism connecting "
            f"these factors: {target_desc}."
        ),
        "missing_node": (
            "Identify an important causal factor that is MISSING from the "
            "forecaster's network. This should be a plausible factor that could "
            "significantly influence the outcome but was not included. Describe "
            "the factor and explain the causal mechanism by which it would "
            "affect the outcome."
        ),
        "irrelevant": (
            "Create a plausible-sounding piece of information that is TOPICALLY "
            "RELATED to the question's domain but should NOT logically affect "
            "any of the causal paths in the network. It should sound like it "
            "could matter at first glance but on reflection has no causal "
            "bearing on the outcome."
        ),
    }

    instruction = type_instructions.get(probe_type, type_instructions["node_negate_high"])

    return f"""\
A forecaster was asked: "{question}"

They estimated a probability of {probability:.2f} and constructed this causal network:

{network_context}

Your task: {instruction}

Respond as JSON:
{{
  "probe_text": "<your challenge -- 2-4 sentences, specific and plausible>",
  "probe_type": "{probe_type}",
  "target_id": "{target_id}"
}}"""


def _build_neutral_probed_forecast_prompt(
    question: str,
    initial_probability: float,
    nodes: list[dict],
    edges: list[dict],
    probe: dict,
    probe_target: dict,
) -> str:
    """Build Stage 3 prompt WITHOUT importance hints."""
    network_context = _format_network_context(nodes, edges)
    probe_type = probe.get("probe_type", "")
    target_id = probe.get("target_id", "")
    probe_text = probe.get("probe_text", "")

    category = PROBE_CATEGORIES.get(probe_type, "structural")
    if category == "node":
        challenge_desc = f"a challenge to the causal factor '{target_id}'"
    elif category == "edge":
        challenge_desc = f"a challenge to the causal link '{target_id}'"
    else:
        challenge_desc = "a structural challenge to your causal model"

    return f"""\
You previously forecasted the following question:

"{question}"

Your initial estimate: probability = {initial_probability:.2f}

Your causal network:
{network_context}

Now consider the following ({challenge_desc}):

"{probe_text}"

Provide your updated forecast as JSON:
{{
  "updated_probability": <float between 0.01 and 0.99>,
  "shift_direction": "increased" or "decreased" or "unchanged",
  "reasoning": "<explain how this new information affects your estimate>"
}}

Requirements:
- updated_probability must be between 0.01 and 0.99."""


# ── Pipeline ────────────────────────────────────────────────────────────

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


def load_existing_questions(source_dir: Path) -> dict:
    """Load all question JSONs from a completed run."""
    questions = {}
    q_dir = source_dir / "question_results"
    if not q_dir.exists():
        return questions
    for f in sorted(q_dir.glob("q_*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        qid = data["question_id"]
        questions[qid] = data
    return questions


def get_completed_questions(output_dir: Path) -> set:
    csv_path = output_dir / "sensitivity_results.csv"
    if not csv_path.exists():
        return set()
    done = set()
    with open(csv_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            done.add(row["question_id"])
    return done


def main():
    parser = argparse.ArgumentParser(description="Neutral-probe ablation")
    parser.add_argument("--model", default="llama-70b", choices=list(MODEL_MAP.keys()))
    parser.add_argument("--source-dir", type=str, help="Dir with existing run to reuse DAGs from")
    parser.add_argument("--output-dir", type=str, help="Output directory")
    parser.add_argument("--max-questions", type=int, default=100)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    api_key = _get_api_key()
    if not api_key:
        print("[ERROR] OPENROUTER_API_KEY not set.")
        sys.exit(1)

    model = MODEL_MAP[args.model]

    # Default source/output dirs
    source_map = {
        "llama": "outputs/sensitivity/causal/llama_one_turn",
        "llama-70b": "outputs/sensitivity/causal/70b_one_turn",
        "deepseek": "outputs/sensitivity/causal/deepseek_one_turn",
        "qwen": "outputs/sensitivity/causal/qwen_one_turn",
        "gemini-flash-lite": "outputs/sensitivity/causal/gemini_flash_lite_one_turn",
        "gpt-oss": "outputs/sensitivity/causal/gpt_oss_one_turn",
        "qwen-32b": "outputs/sensitivity/causal/qwen32b_one_turn",
    }
    source_dir = Path(args.source_dir or source_map.get(args.model, f"outputs/sensitivity/causal/{args.model}_one_turn"))
    output_dir = Path(args.output_dir or f"outputs/sensitivity/causal/{args.model.replace('-', '_')}_neutral")

    print(f"{'='*60}")
    print(f"NEUTRAL-PROBE ABLATION")
    print(f"Model:  {model}")
    print(f"Source: {source_dir}")
    print(f"Output: {output_dir}")
    print(f"{'='*60}")

    # Load existing question data
    existing = load_existing_questions(source_dir)
    print(f"Loaded {len(existing)} questions from source")

    if not existing:
        print("[ERROR] No question data found in source directory")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Check for resume
    completed = get_completed_questions(output_dir) if args.resume else set()
    if completed:
        print(f"Resuming: {len(completed)} questions already done")

    client = LLMClient(
        api_key=api_key,
        model=model,
        temperature=args.temperature,
        max_tokens=2000,
    )

    csv_path = output_dir / "sensitivity_results.csv"
    csv_mode = "a" if args.resume and csv_path.exists() else "w"

    q_out_dir = output_dir / "question_results"
    q_out_dir.mkdir(parents=True, exist_ok=True)

    question_ids = sorted(existing.keys())[:args.max_questions]

    with open(csv_path, csv_mode, newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CAUSAL_CSV_FIELDS)
        if csv_mode == "w":
            writer.writeheader()

        for qi, qid in enumerate(question_ids):
            if qid in completed:
                print(f"  [{qi+1}/{len(question_ids)}] {qid} -- skipped (resume)")
                continue

            qdata = existing[qid]
            question = {"id": qid, "question": qdata["question_text"]}
            initial_prob = qdata["initial_probability"]
            nodes = qdata["nodes"]
            edges = qdata["edges"]
            # Regenerate probe targets from DAG to get ALL types
            # (saved JSONs may use an older target selection)
            net = analyze_network(nodes, edges)
            probe_targets = [pt.to_dict() for pt in net.probe_targets]
            net_analysis = net.to_dict()

            print(f"  [{qi+1}/{len(question_ids)}] {qid} "
                  f"(p={initial_prob:.2f}, {len(probe_targets)} targets) ...", end=" ")

            # Stage 2: Regenerate probes with NEUTRAL framing
            probes = []
            for target in probe_targets:
                user_prompt = _build_neutral_probe_prompt(
                    question["question"], initial_prob, nodes, edges, target,
                )
                text, ok = client.call_single(CAUSAL_PROBE_GENERATION_SYSTEM, user_prompt)
                client.rate_limit_wait()

                if ok:
                    data = parse_json_response(text)
                    if isinstance(data, dict) and data.get("probe_text"):
                        data.setdefault("probe_type", target["probe_type"])
                        data.setdefault("target_id", target["target_id"])
                        data["generated"] = True
                        data["target_type"] = target["target_type"]
                        data["importance"] = target["importance"]
                        data["centrality_rank"] = target["centrality_rank"]
                        data["on_critical_path"] = target["on_critical_path"]
                        data["description"] = target["description"]
                        probes.append(data)
                        continue

                # Fallback
                probes.append({
                    "probe_text": f"What if '{target.get('description', 'this element')}' is wrong?",
                    "probe_type": target["probe_type"],
                    "target_id": target["target_id"],
                    "generated": False,
                    "target_type": target["target_type"],
                    "importance": target["importance"],
                    "centrality_rank": target["centrality_rank"],
                    "on_critical_path": target["on_critical_path"],
                    "description": target["description"],
                })

            print(f"{len(probes)} probes ...", end=" ")

            # Stage 3: Probed forecasts with NEUTRAL system prompt
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

                user_prompt = _build_neutral_probed_forecast_prompt(
                    question["question"], initial_prob, nodes, edges, probe, probe_target,
                )

                text, ok = client.call_single(NEUTRAL_PROBED_FORECAST_SYSTEM, user_prompt)
                client.rate_limit_wait()

                result = _parse_probe_result(client, probe, initial_prob, text, ok)
                result["target_id"] = probe.get("target_id", "")
                result["target_type"] = probe.get("target_type", "")
                result["target_importance"] = probe.get("importance", 0.0)
                result["target_centrality_rank"] = probe.get("centrality_rank", 0)
                result["target_on_critical_path"] = probe.get("on_critical_path", False)
                result["probe_category"] = PROBE_CATEGORIES.get(probe.get("probe_type", ""), "structural")
                probe_results.append(result)

            # Save CSV rows
            for pi, result in enumerate(probe_results):
                save_causal_sensitivity_row(
                    writer, question, "neutral", initial_prob,
                    probes[pi], result, pi, net_analysis,
                )
            f.flush()

            # Save question JSON
            q_json = {
                "question_id": qid,
                "question_text": qdata["question_text"],
                "source": qdata.get("source", ""),
                "initial_probability": initial_prob,
                "nodes": nodes,
                "edges": edges,
                "reasoning": qdata.get("reasoning", ""),
                "network_analysis": net_analysis,
                "probe_targets": probe_targets,
                "probes": probes,
                "condition": "neutral",
                "probe_results": probe_results,
            }
            q_json_path = q_out_dir / f"q_{qid}.json"
            q_json_path.write_text(json.dumps(q_json, indent=2), encoding="utf-8")

            n_success = sum(1 for r in probe_results if r.get("success"))
            shifts = [r["absolute_shift"] for r in probe_results if r.get("success") and r.get("absolute_shift") is not None]
            mean_shift = sum(shifts) / len(shifts) if shifts else 0
            print(f"{n_success}/{len(probe_results)} ok, mean |shift|={mean_shift:.3f}")

    print(f"\n{'='*60}")
    print(f"Done. Results: {csv_path}")
    print(f"Questions: {q_out_dir}")
    print(client.stats)


if __name__ == "__main__":
    main()
