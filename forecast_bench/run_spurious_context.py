"""
Spurious Context Control — Does irrelevant context contaminate DAG construction?

Takes 20 real ForecastBench questions, injects spurious but real-world context,
and checks whether the model incorporates the irrelevant information into its
causal DAG. Compares against the original DAGs from the main pipeline.

Usage:
    python -m forecast_bench.run_spurious_context --model llama-70b
    python -m forecast_bench.run_spurious_context --model llama-70b --resume
    python -m forecast_bench.run_spurious_context --model llama-70b --analyze-only
"""

from __future__ import annotations

import argparse
import json
import os
import sys
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
from forecast_bench.semantic_graph_match import semantic_jaccard_pair

plt.rcParams.update({"font.family": "Arial", "font.size": 10, "figure.dpi": 300})

BLUE, ORANGE, VERMILLION, GREEN, PINK = "#0072B2", "#E69F00", "#D55E00", "#009E73", "#CC79A7"

MODEL_MAP = {
    "llama": "meta-llama/llama-3.1-8b-instruct",
    "llama-70b": "meta-llama/llama-3.3-70b-instruct",
    "deepseek": "deepseek/deepseek-chat-v3-0324",
    "qwen": "qwen/qwen3-235b-a22b-2507",
    "gemini": "google/gemini-2.5-flash-lite-preview",
}

BASE = Path(__file__).parent.parent
OUT = BASE / "paper" / "figures" / "supplementary"
SPURIOUS_Q_PATH = Path(__file__).parent / "spurious_conditioned_questions.json"

JUDGE_MODEL = "openai/gpt-4o-mini"

JUDGE_SYSTEM = """You are evaluating whether a causal DAG has been contaminated by irrelevant background information.

You will be given:
1. A forecasting question
2. Irrelevant background information that was presented alongside the question
3. The nodes of a causal DAG the model constructed

Your task: determine whether ANY node in the DAG was influenced by or derived from the irrelevant background information. A node counts as "incorporated" if its concept, topic, or reasoning is semantically related to the background — even if the exact words differ.

Respond with ONLY valid JSON:
{"incorporated": true or false, "contaminated_nodes": ["node_id_1"], "explanation": "brief explanation"}"""


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


def _judge_spurious_incorporation(
    judge_client: LLMClient,
    question: str,
    background: str,
    nodes: list[dict],
) -> dict:
    """Use GPT-4o-mini to judge if spurious background was incorporated into DAG."""
    node_desc = "\n".join(
        f"  - {n['id']}: {n.get('description', '')}" for n in nodes
        if n.get("role") != "outcome"
    )

    user_prompt = (
        f"FORECASTING QUESTION:\n{question}\n\n"
        f"IRRELEVANT BACKGROUND:\n{background}\n\n"
        f"DAG FACTOR NODES:\n{node_desc}"
    )

    text, ok = judge_client.call_single(JUDGE_SYSTEM, user_prompt)
    judge_client.rate_limit_wait()

    if not ok:
        return {"incorporated": False, "contaminated_nodes": [], "explanation": "judge call failed"}

    data = parse_json_response(text)
    if data is None:
        return {"incorporated": False, "contaminated_nodes": [], "explanation": "judge parse failed"}

    return {
        "incorporated": bool(data.get("incorporated", False)),
        "contaminated_nodes": data.get("contaminated_nodes", []),
        "explanation": data.get("explanation", ""),
    }


def run_collection(args):
    """Run Stage 1 on questions with spurious background, then judge incorporation."""
    model_id = MODEL_MAP.get(args.model, args.model)
    api_key = _get_api_key()
    if not api_key:
        print("[ERROR] OPENROUTER_API_KEY not set.")
        sys.exit(1)

    questions = json.loads(SPURIOUS_Q_PATH.read_text(encoding="utf-8"))
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Forecasting model
    client = LLMClient(
        api_key=api_key,
        model=model_id,
        temperature=0.7,
        max_tokens=1200,
    )

    # Judge model (GPT-4o-mini, separate from pipeline models)
    judge_client = LLMClient(
        api_key=api_key,
        model=JUDGE_MODEL,
        temperature=0.0,
        max_tokens=500,
    )

    print(f"\n{'='*60}")
    print(f"SPURIOUS CONTEXT CONTROL")
    print(f"{'='*60}")
    print(f"Model: {model_id}")
    print(f"Judge: {JUDGE_MODEL}")
    print(f"Questions: {len(questions)}")

    for q_idx, q in enumerate(questions):
        qid = q["id"]
        result_path = output_dir / f"{qid}.json"

        if args.resume and result_path.exists():
            print(f"  [{q_idx+1}/{len(questions)}] {qid[:30]} -- cached")
            continue

        print(f"  [{q_idx+1}/{len(questions)}] {qid[:30]}...", end=" ")

        # Present as: background + question
        prompt_text = f"{q['background']}\n\n{q['original']}"
        data = run_forecast(client, prompt_text)
        client.rate_limit_wait()

        if data is None:
            print("FAILED")
            continue

        try:
            na = analyze_network(data["nodes"], data["edges"])
            na_dict = na.to_dict()
        except Exception:
            na_dict = {}

        # LLM judge: was spurious background incorporated?
        spurious_check = _judge_spurious_incorporation(
            judge_client, q["original"], q["background"], data["nodes"],
        )

        output = {
            "question_id": qid,
            "original_question": q["original"],
            "background": q["background"],
            "initial_probability": data["probability"],
            "nodes": data["nodes"],
            "edges": data["edges"],
            "reasoning": data.get("reasoning", ""),
            "network_analysis": na_dict,
            "spurious_check": spurious_check,
        }

        result_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
        n_nodes = len(data["nodes"])
        n_edges = len(data["edges"])
        inc = "INCORPORATED" if spurious_check["incorporated"] else "filtered"
        contam = spurious_check.get("contaminated_nodes", [])
        print(f"p={data['probability']:.2f}, {n_nodes}N/{n_edges}E, "
              f"spurious={inc} {contam if contam else ''}")

    print(f"\nForecast stats: {json.dumps(client.stats.__dict__)}")
    print(f"Judge stats: {json.dumps(judge_client.stats.__dict__)}")


def _compute_node_betweenness(nodes: list[dict], edges: list[dict]) -> dict[str, float]:
    """Compute betweenness centrality for all nodes in a DAG."""
    import networkx as nx
    G = nx.DiGraph()
    for n in nodes:
        G.add_node(n["id"])
    for e in edges:
        if e.get("from") in G and e.get("to") in G:
            G.add_edge(e["from"], e["to"])
    if len(G) < 2:
        return {n["id"]: 0.0 for n in nodes}
    return nx.betweenness_centrality(G)


def run_analysis(args):
    """Analyze spurious context incorporation with betweenness centrality."""
    output_dir = Path(args.output_dir)

    # Load spurious results
    spurious = {}
    for f in sorted(output_dir.glob("*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        spurious[data["question_id"]] = data

    if not spurious:
        print("[ERROR] No spurious results found")
        return

    questions = json.loads(SPURIOUS_Q_PATH.read_text(encoding="utf-8"))
    q_map = {q["id"]: q for q in questions}

    # Load original DAGs for comparison
    model_short = args.model.replace("-", "_")
    real_dirs = {
        "llama_70b": BASE / "outputs" / "sensitivity" / "causal" / "70b_one_turn" / "_shared_stages_causal",
        "llama": BASE / "outputs" / "sensitivity" / "causal" / "8b_one_turn" / "_shared_stages_causal",
        "deepseek": BASE / "outputs" / "sensitivity" / "causal" / "deepseek_one_turn" / "_shared_stages_causal",
        "qwen": BASE / "outputs" / "sensitivity" / "causal" / "qwen_one_turn" / "_shared_stages_causal",
        "gemini": BASE / "outputs" / "sensitivity" / "causal" / "gemini_one_turn" / "_shared_stages_causal",
    }

    real_dir = real_dirs.get(model_short)
    real = {}
    if real_dir and real_dir.exists():
        for f in sorted(real_dir.glob("*.json")):
            data = json.loads(f.read_text(encoding="utf-8"))
            qid = data.get("question_id", f.stem)
            real[qid] = data

    print(f"\n{'='*60}")
    print(f"SPURIOUS CONTEXT ANALYSIS")
    print(f"{'='*60}")
    print(f"Spurious results: {len(spurious)}")
    print(f"Original DAGs for comparison: {len(real)}")

    # ── Metrics ──
    n_incorporated = 0
    n_total = 0
    prob_diffs = []
    node_overlaps = []
    semantic_node_overlaps = []
    # Betweenness tracking: contaminated vs clean nodes
    contam_betweenness = []  # betweenness of contaminated nodes
    clean_betweenness = []   # betweenness of all non-outcome, non-contaminated nodes
    all_betweenness = []     # betweenness of all non-outcome nodes (for reference)
    contam_details = []      # (qid, node_id, betweenness, n_nodes) for each contaminated node

    print(f"\n--- Per-Question Results ---")
    for qid, d in sorted(spurious.items()):
        n_total += 1
        sc = d.get("spurious_check", {})
        inc = sc.get("incorporated", False)
        contam_node_ids = set(sc.get("contaminated_nodes", []))
        if inc:
            n_incorporated += 1

        # Compute betweenness centrality for this DAG
        bc = _compute_node_betweenness(d["nodes"], d["edges"])
        n_factor_nodes = sum(1 for n in d["nodes"] if n.get("role") != "outcome")

        for n in d["nodes"]:
            if n.get("role") == "outcome":
                continue
            nid = n["id"]
            b = bc.get(nid, 0.0)
            all_betweenness.append(b)
            if nid in contam_node_ids:
                contam_betweenness.append(b)
                contam_details.append((qid, nid, b, n_factor_nodes))
            else:
                clean_betweenness.append(b)

        # Compare probability to original
        real_key = None
        for rk in real:
            if rk == qid or rk == f"q_{qid}" or qid.startswith(rk) or rk.startswith(qid):
                real_key = rk
                break

        prob_diff = None
        node_overlap = None
        if real_key and real_key in real:
            orig = real[real_key]
            orig_p = orig.get("initial_probability")
            if orig_p is not None:
                prob_diff = d["initial_probability"] - orig_p
                prob_diffs.append(prob_diff)

            # Node overlap (exact)
            orig_nodes = {n["id"] for n in orig["nodes"] if n.get("role") != "outcome"}
            spur_nodes = {n["id"] for n in d["nodes"] if n.get("role") != "outcome"}
            if orig_nodes or spur_nodes:
                overlap = len(orig_nodes & spur_nodes) / len(orig_nodes | spur_nodes)
                node_overlaps.append(overlap)
                node_overlap = overlap

            # Semantic node overlap
            try:
                sem = semantic_jaccard_pair(
                    [n for n in orig["nodes"] if n.get("role") != "outcome"],
                    [n for n in d["nodes"] if n.get("role") != "outcome"],
                    edges1=orig.get("edges", []),
                    edges2=d.get("edges", []),
                    condition1="orig", condition2="spurious",
                    qid=qid,
                )
                semantic_node_overlaps.append(sem["node_jaccard"])
            except Exception:
                pass

        inc_str = "YES" if inc else "no"
        contam = sc.get("contaminated_nodes", [])
        explanation = sc.get("explanation", "")
        prob_str = f"dp={prob_diff:+.2f}" if prob_diff is not None else "no orig"
        overlap_str = f"J={node_overlap:.2f}" if node_overlap is not None else ""

        # Show betweenness for contaminated nodes
        contam_bc_str = ""
        if contam:
            contam_bc_str = " bc=" + ",".join(f"{bc.get(c, 0):.3f}" for c in contam)

        print(f"  {qid[:25]:25s} p={d['initial_probability']:.2f} {prob_str:10s} "
              f"{overlap_str:8s} spurious={inc_str:3s} {contam}{contam_bc_str}")
        if explanation:
            print(f"    Judge: {explanation[:80]}")

    print(f"\n--- Summary ---")
    print(f"Spurious incorporation rate: {n_incorporated}/{n_total} "
          f"({100*n_incorporated/n_total:.0f}%)")
    if prob_diffs:
        print(f"Mean probability shift: {np.mean(prob_diffs):+.3f} "
              f"(SD={np.std(prob_diffs):.3f})")
        print(f"Mean |probability shift|: {np.mean(np.abs(prob_diffs)):.3f}")
    if node_overlaps:
        print(f"Mean node Jaccard (exact) with original: {np.mean(node_overlaps):.3f} "
              f"(SD={np.std(node_overlaps):.3f})")
    if semantic_node_overlaps:
        print(f"Mean node Jaccard (semantic) with original: {np.mean(semantic_node_overlaps):.3f} "
              f"(SD={np.std(semantic_node_overlaps):.3f})")

    # Betweenness centrality analysis
    print(f"\n--- Betweenness Centrality of Spurious Nodes ---")
    print(f"All factor nodes: n={len(all_betweenness)}, "
          f"mean={np.mean(all_betweenness):.4f}, median={np.median(all_betweenness):.4f}")
    if contam_betweenness:
        print(f"Contaminated nodes: n={len(contam_betweenness)}, "
              f"mean={np.mean(contam_betweenness):.4f}, median={np.median(contam_betweenness):.4f}")
        print(f"Clean nodes: n={len(clean_betweenness)}, "
              f"mean={np.mean(clean_betweenness):.4f}, median={np.median(clean_betweenness):.4f}")

        # Percentile rank of contaminated nodes among all nodes
        all_sorted = np.sort(all_betweenness)
        for qid, nid, b, n_nodes in contam_details:
            pct = np.searchsorted(all_sorted, b) / len(all_sorted) * 100
            print(f"  {qid[:25]} / {nid}: betweenness={b:.4f} "
                  f"(percentile={pct:.0f}%, DAG has {n_nodes} factor nodes)")
    else:
        print("No contaminated nodes found — model fully filtered spurious context.")

    # ── Figure ──
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))
    fig.patch.set_facecolor("white")

    # (a) Incorporation rate — simple bar
    ax = axes[0]
    n_filtered = n_total - n_incorporated
    bars = ax.bar(["Incorporated", "Filtered"], [n_incorporated, n_filtered],
                  color=[VERMILLION, GREEN], edgecolor="black", linewidth=0.5)
    for bar, val in zip(bars, [n_incorporated, n_filtered]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                str(val), ha="center", fontweight="bold", fontsize=12)
    ax.set_ylabel("Number of Questions")
    ax.set_title("Spurious Context in DAG?", fontsize=11)
    ax.set_ylim(0, n_total + 2)

    # (b) Probability shift — paired comparison
    ax = axes[1]
    if prob_diffs:
        ax.hist(prob_diffs, bins=15, color=BLUE, edgecolor="black",
                linewidth=0.5, alpha=0.7)
        ax.axvline(0, color="#999", linestyle="--", linewidth=1)
        ax.axvline(np.mean(prob_diffs), color=VERMILLION, linewidth=2,
                   label=f"Mean = {np.mean(prob_diffs):+.3f}")
        ax.set_xlabel("Probability Shift\n(Conditioned − Original)")
        ax.set_ylabel("Count")
        ax.legend(frameon=False, fontsize=9)
    else:
        ax.text(0.5, 0.5, "No paired data", transform=ax.transAxes, ha="center")

    # (c) Betweenness centrality: contaminated vs clean nodes
    ax = axes[2]
    if contam_betweenness:
        # Strip plot / swarm showing contaminated nodes vs distribution of clean
        ax.hist(clean_betweenness, bins=20, color=BLUE, edgecolor="black",
                linewidth=0.5, alpha=0.5, density=True, label="Clean nodes")
        # Mark contaminated nodes
        for b in contam_betweenness:
            ax.axvline(b, color=VERMILLION, linewidth=2, alpha=0.8)
        # Dummy line for legend
        ax.axvline(np.nan, color=VERMILLION, linewidth=2, label="Spurious nodes")
        ax.set_xlabel("Betweenness Centrality")
        ax.set_ylabel("Density")
        ax.set_title("Spurious Nodes: Peripheral?", fontsize=11)
        ax.legend(frameon=False, fontsize=9)
    else:
        # No contaminated nodes — show that as a positive result
        ax.text(0.5, 0.55, f"0/{n_total} DAGs\ncontaminated",
                transform=ax.transAxes, ha="center", va="center",
                fontsize=16, fontweight="bold", color=GREEN)
        ax.text(0.5, 0.3, "No spurious nodes to analyze",
                transform=ax.transAxes, ha="center", va="center",
                fontsize=10, color="#666")
        ax.set_xlabel("Betweenness Centrality")
        ax.set_ylabel("Density")
        ax.set_title("Spurious Nodes: Peripheral?", fontsize=11)

    for i, ax in enumerate(axes):
        ax.text(-0.12, 1.05, f"({'abc'[i]})", transform=ax.transAxes,
                fontsize=14, fontweight="bold")

    plt.tight_layout()
    OUT.mkdir(parents=True, exist_ok=True)
    fig_path = OUT / "spurious_context_control"
    for ext in ["png", "pdf"]:
        fig.savefig(f"{fig_path}.{ext}", dpi=300, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"\nFigure saved to {fig_path}.png")


def main():
    parser = argparse.ArgumentParser(
        description="Spurious context control analysis",
    )
    parser.add_argument("--model", default="llama-70b",
                        choices=list(MODEL_MAP.keys()) + ["all"])
    parser.add_argument("--output-dir", type=str, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--analyze-only", action="store_true")
    args = parser.parse_args()

    if args.output_dir is None:
        model_short = args.model.replace("-", "_")
        args.output_dir = f"outputs/sensitivity/causal/{model_short}_spurious_context"

    if not args.analyze_only:
        run_collection(args)

    run_analysis(args)


if __name__ == "__main__":
    main()
