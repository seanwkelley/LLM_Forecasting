"""
Fictional Control Analysis — Do LLMs produce meaningful causal structure for fictional entities?

Runs Stage 1 (causal forecast) on 20 fictional questions with entirely invented
entities. Compares resulting DAGs and probabilities to real ForecastBench questions
to test whether structural sensitivity is grounded in real knowledge or is a
surface pattern the model produces for any forecasting question.

Usage:
    python -m forecast_bench.run_fictional_control --model llama-70b
    python -m forecast_bench.run_fictional_control --model llama-70b --analyze-only
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from forecast_bench.llm_client import LLMClient, parse_json_response
from forecast_bench.prompts_causal import (
    CAUSAL_FORECAST_SYSTEM,
    build_causal_forecast_prompt,
)
from forecast_bench.network_analysis import analyze_network
from forecast_bench.run_sensitivity import (
    run_causal_probe_generation,
    run_causal_independent_probing,
)

plt.rcParams.update({"font.family": "Arial", "font.size": 10, "figure.dpi": 300})

BLUE, ORANGE, VERMILLION, GREEN, PINK = "#0072B2", "#E69F00", "#D55E00", "#009E73", "#CC79A7"

MODEL_MAP = {
    "llama": "meta-llama/llama-3.1-8b-instruct",
    "llama-70b": "meta-llama/llama-3.3-70b-instruct",
    "deepseek": "deepseek/deepseek-chat-v3-0324",
    "qwen": "qwen/qwen3-235b-a22b-2507",
}

BASE = Path(__file__).parent.parent
OUT = BASE / "paper" / "figures" / "supplementary"
FICTIONAL_Q_PATH = Path(__file__).parent / "fictional_questions.json"


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


def run_forecast(client, question_text: str, max_retries: int = 2):
    """Run Stage 1 causal forecast with retries."""
    user_prompt = build_causal_forecast_prompt(question_text)

    for attempt in range(1 + max_retries):
        text, ok = client.call_single(CAUSAL_FORECAST_SYSTEM, user_prompt)
        if not ok:
            return None

        data = parse_json_response(text)
        if data is None:
            if attempt < max_retries:
                client.rate_limit_wait()
                continue
            return None

        prob = data.get("probability")
        nodes = data.get("nodes")
        edges = data.get("edges")
        if prob is None or not isinstance(nodes, list) or not isinstance(edges, list):
            if attempt < max_retries:
                client.rate_limit_wait()
                continue
            return None

        prob = max(0.01, min(0.99, float(prob)))
        data["probability"] = prob

        node_ids = set()
        outcome_count = 0
        valid = True
        for n in nodes:
            if not isinstance(n, dict) or "id" not in n:
                valid = False
                break
            n.setdefault("description", "")
            n.setdefault("role", "factor")
            node_ids.add(n["id"])
            if n["role"] == "outcome":
                outcome_count += 1

        if not valid or outcome_count != 1:
            if attempt < max_retries:
                client.rate_limit_wait()
                continue
            return None

        for e in edges:
            if not isinstance(e, dict):
                valid = False
                break
            e.setdefault("mechanism", "")
            if e.get("from") not in node_ids or e.get("to") not in node_ids:
                valid = False
                break

        if not valid or not edges:
            if attempt < max_retries:
                client.rate_limit_wait()
                continue
            return None

        outcome_id = next(n["id"] for n in nodes if n["role"] == "outcome")
        if not any(e["to"] == outcome_id for e in edges):
            if attempt < max_retries:
                client.rate_limit_wait()
                continue
            return None

        return data

    return None


def load_fictional_questions() -> list[dict]:
    """Load the 20 fictional questions."""
    return json.loads(FICTIONAL_Q_PATH.read_text(encoding="utf-8"))


def run_collection(args):
    """Collect DAGs for fictional questions."""
    model_id = MODEL_MAP.get(args.model, args.model)
    api_key = _get_api_key()
    if not api_key:
        print("[ERROR] OPENROUTER_API_KEY not set.")
        sys.exit(1)

    questions = load_fictional_questions()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    client = LLMClient(
        api_key=api_key,
        model=model_id,
        temperature=0.7,
        max_tokens=1200,
    )

    print(f"\n{'='*60}")
    print(f"FICTIONAL CONTROL ANALYSIS")
    print(f"{'='*60}")
    print(f"Model: {model_id}")
    print(f"Questions: {len(questions)}")

    for q_idx, question in enumerate(questions):
        qid = question["id"]
        result_path = output_dir / f"{qid}.json"

        if args.resume and result_path.exists():
            print(f"  [{q_idx+1}/{len(questions)}] {qid} -- cached")
            continue

        print(f"  [{q_idx+1}/{len(questions)}] {qid} ({question['domain']})...", end=" ")

        data = run_forecast(client, question["question"])
        client.rate_limit_wait()

        if data is None:
            print("FAILED")
            continue

        try:
            na = analyze_network(data["nodes"], data["edges"])
            na_dict = na.to_dict()
        except Exception:
            na_dict = {}

        output = {
            "question_id": qid,
            "question_text": question["question"],
            "domain": question["domain"],
            "fictional": True,
            "initial_probability": data["probability"],
            "nodes": data["nodes"],
            "edges": data["edges"],
            "reasoning": data.get("reasoning", ""),
            "network_analysis": na_dict,
        }

        result_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
        n_nodes = len(data["nodes"])
        n_edges = len(data["edges"])
        print(f"p={data['probability']:.2f}, {n_nodes}N/{n_edges}E")

    print(f"\nAPI stats: {json.dumps(client.stats.__dict__)}")


def run_probing(args):
    """Run Stages 1.5, 2, 3 on collected fictional DAGs."""
    model_id = MODEL_MAP.get(args.model, args.model)
    api_key = _get_api_key()
    if not api_key:
        print("[ERROR] OPENROUTER_API_KEY not set.")
        sys.exit(1)

    output_dir = Path(args.output_dir)
    questions = load_fictional_questions()

    # Load Stage 1 results
    stage1 = {}
    for f in sorted(output_dir.glob("fictional_*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        stage1[data["question_id"]] = data

    if not stage1:
        print("[ERROR] No Stage 1 results found. Run collection first.")
        return

    print(f"\n{'='*60}")
    print(f"FICTIONAL CONTROL — PROBING (Stages 1.5, 2, 3)")
    print(f"{'='*60}")
    print(f"Model: {model_id}")
    print(f"Questions with Stage 1: {len(stage1)}")

    # Client for probe generation (temp=0.7) and probed forecast (temp=0.1)
    client_gen = LLMClient(
        api_key=api_key, model=model_id, temperature=0.7, max_tokens=2000,
    )
    client_probe = LLMClient(
        api_key=api_key, model=model_id, temperature=0.1, max_tokens=800,
    )

    for q_idx, question in enumerate(questions):
        qid = question["id"]
        result_path = output_dir / f"{qid}.json"

        if qid not in stage1:
            print(f"  [{q_idx+1}/{len(questions)}] {qid} -- no Stage 1 data")
            continue

        data = stage1[qid]

        # Skip if already has probe results
        if args.resume and data.get("probe_results"):
            print(f"  [{q_idx+1}/{len(questions)}] {qid} -- probes cached")
            continue

        nodes = data["nodes"]
        edges = data["edges"]
        initial_prob = data["initial_probability"]

        # Stage 1.5: Network analysis
        try:
            net_analysis = analyze_network(nodes, edges)
            probe_targets = [pt.to_dict() for pt in net_analysis.probe_targets]
        except Exception as e:
            print(f"  [{q_idx+1}/{len(questions)}] {qid} -- network analysis failed: {e}")
            continue

        print(f"  [{q_idx+1}/{len(questions)}] {qid} "
              f"(p={initial_prob:.2f}, {len(probe_targets)} targets)...", end=" ")

        # Stage 2: Probe generation
        q_dict = {"id": qid, "question": question["question"]}
        probes = run_causal_probe_generation(
            client_gen, q_dict, initial_prob, nodes, edges, probe_targets,
        )
        print(f"{len(probes)} probes", end=" -> ")

        # Stage 3: Probed forecasts (one-turn)
        probe_results = run_causal_independent_probing(
            client_probe, q_dict, initial_prob, nodes, edges, probes,
        )

        successes = sum(1 for r in probe_results if r.get("success"))
        print(f"{successes}/{len(probe_results)} successful")

        # Save back to JSON
        data["probe_targets"] = probe_targets
        data["probes"] = probes
        data["probe_results"] = probe_results
        data["network_analysis"] = net_analysis.to_dict()
        result_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    print(f"\nProbe gen stats: {json.dumps(client_gen.stats.__dict__)}")
    print(f"Probe forecast stats: {json.dumps(client_probe.stats.__dict__)}")


def run_analysis(args):
    """Compare fictional vs real question DAGs."""
    output_dir = Path(args.output_dir)

    # Load fictional results
    fictional = {}
    for f in sorted(output_dir.glob("fictional_*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        fictional[data["question_id"]] = data

    if not fictional:
        print("[ERROR] No fictional results found")
        return

    print(f"\nFictional questions with results: {len(fictional)}")

    # Load real results for comparison (same model)
    model_short = args.model.replace("-", "_")
    real_dirs = {
        "llama_70b": BASE / "outputs" / "sensitivity" / "causal" / "70b_one_turn" / "_shared_stages_causal",
        "llama": BASE / "outputs" / "sensitivity" / "causal" / "8b_one_turn" / "_shared_stages_causal",
        "deepseek": BASE / "outputs" / "sensitivity" / "causal" / "deepseek_one_turn" / "_shared_stages_causal",
        "qwen": BASE / "outputs" / "sensitivity" / "causal" / "qwen_one_turn" / "_shared_stages_causal",
    }

    real_dir = real_dirs.get(model_short)
    real = {}
    if real_dir and real_dir.exists():
        for f in sorted(real_dir.glob("*.json")):
            data = json.loads(f.read_text(encoding="utf-8"))
            qid = data.get("question_id", f.stem)
            real[qid] = data
    print(f"Real questions with results: {len(real)}")

    # ── Compute statistics ──
    def _dag_stats(results: dict) -> dict:
        probs, n_nodes, n_edges, densities = [], [], [], []
        for qid, d in results.items():
            probs.append(d["initial_probability"])
            nodes = [n for n in d["nodes"] if n.get("role") != "outcome"]
            n_nodes.append(len(nodes) + 1)
            n_edges.append(len(d["edges"]))
            nn = len(nodes) + 1
            max_edges = nn * (nn - 1)
            densities.append(len(d["edges"]) / max_edges if max_edges > 0 else 0)
        return {
            "probs": np.array(probs),
            "n_nodes": np.array(n_nodes),
            "n_edges": np.array(n_edges),
            "densities": np.array(densities),
        }

    fic_stats = _dag_stats(fictional)
    real_stats = _dag_stats(real) if real else None

    print(f"\n--- Fictional Questions ---")
    print(f"  Mean probability: {np.mean(fic_stats['probs']):.3f} (SD={np.std(fic_stats['probs']):.3f})")
    print(f"  Mean nodes: {np.mean(fic_stats['n_nodes']):.1f} (SD={np.std(fic_stats['n_nodes']):.1f})")
    print(f"  Mean edges: {np.mean(fic_stats['n_edges']):.1f} (SD={np.std(fic_stats['n_edges']):.1f})")
    print(f"  Mean density: {np.mean(fic_stats['densities']):.3f} (SD={np.std(fic_stats['densities']):.3f})")

    if real_stats is not None:
        print(f"\n--- Real Questions ---")
        print(f"  Mean probability: {np.mean(real_stats['probs']):.3f} (SD={np.std(real_stats['probs']):.3f})")
        print(f"  Mean nodes: {np.mean(real_stats['n_nodes']):.1f} (SD={np.std(real_stats['n_nodes']):.1f})")
        print(f"  Mean edges: {np.mean(real_stats['n_edges']):.1f} (SD={np.std(real_stats['n_edges']):.1f})")
        print(f"  Mean density: {np.mean(real_stats['densities']):.3f} (SD={np.std(real_stats['densities']):.3f})")

    # ── Figure: comparison ──
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))
    fig.patch.set_facecolor("white")

    # (a) Probability distributions
    ax = axes[0]
    ax.hist(fic_stats["probs"], bins=10, range=(0, 1), alpha=0.7, color=VERMILLION,
            edgecolor="black", linewidth=0.5, label="Fictional", density=True)
    if real_stats is not None:
        ax.hist(real_stats["probs"], bins=10, range=(0, 1), alpha=0.5, color=BLUE,
                edgecolor="black", linewidth=0.5, label="Real", density=True)
    ax.axvline(0.5, color="#999", linestyle="--", linewidth=1, alpha=0.5)
    ax.set_xlabel("Initial Probability")
    ax.set_ylabel("Density")
    ax.legend(frameon=False, fontsize=9)

    # (b) Node count comparison
    ax = axes[1]
    positions = [1, 2] if real_stats is not None else [1]
    box_data = [fic_stats["n_nodes"]]
    box_labels = ["Fictional"]
    box_colors = [VERMILLION]
    if real_stats is not None:
        box_data.append(real_stats["n_nodes"])
        box_labels.append("Real")
        box_colors.append(BLUE)
    bp = ax.boxplot(box_data, tick_labels=box_labels, patch_artist=True,
                    widths=0.5, showfliers=True)
    for patch, color in zip(bp["boxes"], box_colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)
    for i, vals in enumerate(box_data):
        ax.scatter([i + 1], [np.mean(vals)], marker="D", color="black", s=40, zorder=5)
    ax.set_ylabel("Number of Nodes")

    # (c) Graph density comparison
    ax = axes[2]
    box_data_d = [fic_stats["densities"]]
    box_labels_d = ["Fictional"]
    box_colors_d = [VERMILLION]
    if real_stats is not None:
        box_data_d.append(real_stats["densities"])
        box_labels_d.append("Real")
        box_colors_d.append(BLUE)
    bp_d = ax.boxplot(box_data_d, tick_labels=box_labels_d, patch_artist=True,
                      widths=0.5, showfliers=True)
    for patch, color in zip(bp_d["boxes"], box_colors_d):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)
    for i, vals in enumerate(box_data_d):
        ax.scatter([i + 1], [np.mean(vals)], marker="D", color="black", s=40, zorder=5)
    ax.set_ylabel("Graph Density")

    # Panel labels
    for i, ax in enumerate(axes):
        ax.text(-0.12, 1.05, f"({'abc'[i]})", transform=ax.transAxes,
                fontsize=14, fontweight="bold")

    plt.tight_layout()
    OUT.mkdir(parents=True, exist_ok=True)
    fig_path = OUT / "fictional_control"
    for ext in ["png", "pdf"]:
        fig.savefig(f"{fig_path}.{ext}", dpi=300, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"\nFigure saved to {fig_path}.png")

    # Print individual fictional results
    print(f"\n--- Individual Fictional Results ---")
    for qid in sorted(fictional.keys()):
        d = fictional[qid]
        q = d["question_text"]
        if len(q) > 70:
            q = q[:67] + "..."
        print(f"  {qid}: p={d['initial_probability']:.2f}, "
              f"{len(d['nodes'])}N/{len(d['edges'])}E, "
              f"domain={d['domain']}")
        print(f"    Q: {q}")


def main():
    parser = argparse.ArgumentParser(
        description="Fictional control analysis for causal DAGs",
    )
    parser.add_argument("--model", default="llama-70b", choices=list(MODEL_MAP.keys()))
    parser.add_argument("--output-dir", type=str, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--analyze-only", action="store_true",
                        help="Skip data collection, just run analysis on existing data")
    parser.add_argument("--probe", action="store_true",
                        help="Run probing pipeline (Stages 2-3) on collected DAGs")
    args = parser.parse_args()

    if args.output_dir is None:
        model_short = args.model.replace("-", "_")
        args.output_dir = f"outputs/sensitivity/causal/{model_short}_fictional"

    if not args.analyze_only:
        run_collection(args)
        if args.probe:
            run_probing(args)

    run_analysis(args)


if __name__ == "__main__":
    main()
