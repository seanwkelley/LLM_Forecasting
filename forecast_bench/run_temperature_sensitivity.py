"""
Temperature Sensitivity Analysis — How stable are causal DAGs across temperatures?

Runs Stage 1 only (causal forecast) at multiple temperatures for the same
model and questions. Compares resulting DAGs using node/edge Jaccard,
probability correlation, and graph structure metrics.

Usage:
    python -m forecast_bench.run_temperature_sensitivity \
        --model llama-70b --max-questions 100

    python -m forecast_bench.run_temperature_sensitivity \
        --model llama-70b --max-questions 100 --resume
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
try:
    from scipy import stats as sp_stats
except ImportError:
    sp_stats = None

from forecast_bench.llm_client import LLMClient, parse_json_response
from forecast_bench.prompts_causal import (
    CAUSAL_FORECAST_SYSTEM,
    build_causal_forecast_prompt,
)
from forecast_bench.network_analysis import analyze_network
from forecast_bench.questions import load_forecastbench_questions
from forecast_bench.analyze_superforecasting_dag import normalized_ged
from forecast_bench.semantic_graph_match import semantic_jaccard_pair

plt.rcParams.update({"font.family": "Arial", "font.size": 10, "figure.dpi": 300})

BLUE, ORANGE, VERMILLION, GREEN = "#0072B2", "#E69F00", "#D55E00", "#009E73"

MODEL_MAP = {
    "llama": "meta-llama/llama-3.1-8b-instruct",
    "llama-70b": "meta-llama/llama-3.3-70b-instruct",
    "deepseek": "deepseek/deepseek-chat-v3-0324",
    "qwen": "qwen/qwen3-235b-a22b-2507",
}

TEMPERATURES = [0.0, 0.3, 0.7, 1.0]

BASE = Path(__file__).parent.parent
OUT = BASE / "paper" / "figures"


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
            client.stats.parse_failures += 1
            return None

        prob = data.get("probability")
        nodes = data.get("nodes")
        edges = data.get("edges")
        if prob is None or not isinstance(nodes, list) or not isinstance(edges, list):
            if attempt < max_retries:
                client.rate_limit_wait()
                continue
            client.stats.parse_failures += 1
            return None

        # Validate
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


def jaccard(set_a, set_b):
    if not set_a and not set_b:
        return 1.0
    inter = len(set_a & set_b)
    union = len(set_a | set_b)
    return inter / union if union > 0 else 0.0


def run_collection(args):
    """Collect DAGs at each temperature."""
    model_id = MODEL_MAP.get(args.model, args.model)
    api_key = _get_api_key()
    if not api_key:
        print("[ERROR] OPENROUTER_API_KEY not set.")
        sys.exit(1)

    questions = load_forecastbench_questions(
        max_questions=args.max_questions, seed=42,
    )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"TEMPERATURE SENSITIVITY ANALYSIS")
    print(f"{'='*60}")
    print(f"Model: {model_id}")
    print(f"Temperatures: {TEMPERATURES}")
    print(f"Questions: {len(questions)}")

    for temp in TEMPERATURES:
        temp_dir = output_dir / f"temp_{temp:.1f}"
        temp_dir.mkdir(parents=True, exist_ok=True)

        client = LLMClient(
            api_key=api_key,
            model=model_id,
            temperature=temp,
            max_tokens=1200,
        )

        print(f"\n--- Temperature {temp} ---")

        for q_idx, question in enumerate(questions):
            qid = question["id"]
            result_path = temp_dir / f"{qid}.json"

            if args.resume and result_path.exists():
                print(f"  [{q_idx+1}/{len(questions)}] {qid[:40]} -- cached")
                continue

            print(f"  [{q_idx+1}/{len(questions)}] {qid[:40]}...", end=" ")

            data = run_forecast(client, question["question"])
            client.rate_limit_wait()

            if data is None:
                print("FAILED")
                continue

            # Run network analysis
            try:
                na = analyze_network(data["nodes"], data["edges"])
                na_dict = na.to_dict()
            except Exception:
                na_dict = {}

            output = {
                "question_id": qid,
                "question_text": question["question"],
                "temperature": temp,
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

        print(f"  API stats: {json.dumps(client.stats.__dict__)}")


def run_analysis(args):
    """Analyze and plot temperature sensitivity."""
    output_dir = Path(args.output_dir)

    # Load all results
    temp_data = {}  # temp -> {qid -> data}
    for temp in TEMPERATURES:
        temp_dir = output_dir / f"temp_{temp:.1f}"
        if not temp_dir.exists():
            continue
        temp_data[temp] = {}
        for f in sorted(temp_dir.glob("*.json")):
            data = json.loads(f.read_text(encoding="utf-8"))
            qid = data.get("question_id", f.stem)
            temp_data[temp][qid] = data

    if len(temp_data) < 2:
        print("[ERROR] Need at least 2 temperatures to compare")
        return

    available_temps = sorted(temp_data.keys())
    print(f"\nTemperatures with data: {available_temps}")
    print(f"Questions per temp: {[len(v) for v in temp_data.values()]}")

    # Find questions shared across all temperatures
    shared_all = set(temp_data[available_temps[0]].keys())
    for t in available_temps[1:]:
        shared_all &= set(temp_data[t].keys())
    shared_all = sorted(shared_all)
    n_q = len(shared_all)
    print(f"Shared questions across all temps: {n_q}")

    if n_q < 5:
        print("[ERROR] Need at least 5 shared questions")
        return

    n_temps = len(available_temps)
    prob_diff_matrix = np.zeros((n_temps, n_temps))

    for i in range(n_temps):
        for j in range(i + 1, n_temps):
            t_i, t_j = available_temps[i], available_temps[j]
            diffs = []
            for qid in shared_all:
                p_i = temp_data[t_i][qid]["initial_probability"]
                p_j = temp_data[t_j][qid]["initial_probability"]
                diffs.append(abs(p_i - p_j))
            mean_diff = np.mean(diffs)
            prob_diff_matrix[i, j] = prob_diff_matrix[j, i] = mean_diff
            print(f"  T={t_i:.1f} vs T={t_j:.1f}: mean |dp|={mean_diff:.3f}")

    # ── Compute pairwise normalized GED (all temp pairs) ──
    nged_matrix = np.zeros((n_temps, n_temps))

    for i in range(n_temps):
        for j in range(i + 1, n_temps):
            t_i, t_j = available_temps[i], available_temps[j]
            ngeds = []
            for qid in shared_all:
                d_i = temp_data[t_i][qid]
                d_j = temp_data[t_j][qid]
                ni = {n["id"] for n in d_i["nodes"] if n.get("role") != "outcome"}
                nj = {n["id"] for n in d_j["nodes"] if n.get("role") != "outcome"}
                ei = {(e["from"], e["to"]) for e in d_i["edges"]}
                ej = {(e["from"], e["to"]) for e in d_j["edges"]}
                ngeds.append(normalized_ged(ni, ei, nj, ej))
            nged_mean = np.mean(ngeds)
            nged_matrix[i, j] = nged_matrix[j, i] = nged_mean
            print(f"  T={t_i:.1f} vs T={t_j:.1f}: mean nGED={nged_mean:.3f}")

    # ── Compute pairwise semantic node Jaccard ──
    sem_node_matrix = np.zeros((n_temps, n_temps))
    print("\nSemantic node Jaccard (embedding-based):")
    for i in range(n_temps):
        for j in range(i + 1, n_temps):
            t_i, t_j = available_temps[i], available_temps[j]
            sem_jaccards = []
            for qid in shared_all:
                d_i = temp_data[t_i][qid]
                d_j = temp_data[t_j][qid]
                nodes_i = [n for n in d_i["nodes"] if n.get("role") != "outcome"]
                nodes_j = [n for n in d_j["nodes"] if n.get("role") != "outcome"]
                try:
                    sem = semantic_jaccard_pair(
                        nodes_i, nodes_j,
                        edges1=d_i.get("edges", []),
                        edges2=d_j.get("edges", []),
                        condition1=f"t{t_i}", condition2=f"t{t_j}",
                        qid=qid,
                    )
                    sem_jaccards.append(sem["node_jaccard"])
                except Exception:
                    pass
            if sem_jaccards:
                sem_mean = np.mean(sem_jaccards)
                sem_node_matrix[i, j] = sem_node_matrix[j, i] = sem_mean
                print(f"  T={t_i:.1f} vs T={t_j:.1f}: mean semantic node J={sem_mean:.3f}")

    # ── Figure: 2 panels + exemplar ──
    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(10, 4.2))
    fig.patch.set_facecolor("white")

    # (a) Heatmap: pairwise mean |Δp|
    temp_labels = [f"T={t:.1f}" for t in available_temps]
    # Use same 0-1 scale as (b) for direct comparison
    prob_max = max(prob_diff_matrix.max(), 0.1)  # ensure reasonable scale
    im_a = ax_a.imshow(prob_diff_matrix, cmap="YlOrRd", vmin=0, vmax=1, aspect="equal")

    for i in range(n_temps):
        for j in range(n_temps):
            val = prob_diff_matrix[i, j]
            text_color = "white" if val > 0.5 else "black"
            ax_a.text(j, i, f"{val:.2f}",
                      ha="center", va="center", fontsize=10, fontweight="bold",
                      color=text_color)

    ax_a.set_xticks(range(n_temps))
    ax_a.set_xticklabels(temp_labels)
    ax_a.set_yticks(range(n_temps))
    ax_a.set_yticklabels(temp_labels)
    cbar_a = fig.colorbar(im_a, ax=ax_a, fraction=0.046, pad=0.04)
    cbar_a.set_label("Mean |Δp| (same question)", fontsize=8)
    ax_a.text(-0.15, 1.05, "(a)", transform=ax_a.transAxes, fontsize=14, fontweight="bold")

    # (b) Heatmap: normalized graph edit distance
    temp_labels = [f"T={t:.1f}" for t in available_temps]
    im = ax_b.imshow(nged_matrix, cmap="YlOrRd", vmin=0, vmax=1, aspect="equal")

    # Annotate cells
    for i in range(n_temps):
        for j in range(n_temps):
            val = nged_matrix[i, j]
            text_color = "white" if val > 0.5 else "black"
            ax_b.text(j, i, f"{val:.2f}",
                      ha="center", va="center", fontsize=10, fontweight="bold",
                      color=text_color)

    ax_b.set_xticks(range(n_temps))
    ax_b.set_xticklabels(temp_labels)
    ax_b.set_yticks(range(n_temps))
    ax_b.set_yticklabels(temp_labels)
    cbar = fig.colorbar(im, ax=ax_b, fraction=0.046, pad=0.04)
    cbar.set_label("Normalized Graph Edit Distance", fontsize=8)
    ax_b.text(-0.15, 1.05, "(b)", transform=ax_b.transAxes, fontsize=14, fontweight="bold")

    plt.tight_layout()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "supplementary").mkdir(parents=True, exist_ok=True)
    fig_path = OUT / "supplementary" / "temperature_sensitivity"
    for ext in ["png", "pdf"]:
        fig.savefig(f"{fig_path}.{ext}", dpi=300, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"\nFigure saved to {fig_path}.png")

    # ── Exemplar network pair figure ──
    _plot_exemplar_pair(temp_data, available_temps, shared_all)


def _plot_exemplar_pair(temp_data, available_temps, shared_all):
    """Plot side-by-side DAGs for the same question at T=0.0 and T=1.0."""
    import textwrap
    import networkx as nx
    from matplotlib.patches import Patch
    from matplotlib.lines import Line2D
    from forecast_bench.network_analysis import analyze_network, _build_digraph

    EXEMPLAR_QID = "7L7arFnaO0Nom1bLY295"  # Musk/Tesla CEO question
    T_LO, T_HI = 0.0, 1.0

    if T_LO not in temp_data or T_HI not in temp_data:
        print("[SKIP] Need T=0.0 and T=1.0 for exemplar pair")
        return
    if EXEMPLAR_QID not in temp_data[T_LO] or EXEMPLAR_QID not in temp_data[T_HI]:
        print(f"[SKIP] Exemplar question {EXEMPLAR_QID} not found at both temps")
        return

    d_lo = temp_data[T_LO][EXEMPLAR_QID]
    d_hi = temp_data[T_HI][EXEMPLAR_QID]

    # Shared node IDs (excluding outcome)
    nodes_lo = {n["id"] for n in d_lo["nodes"] if n.get("role") != "outcome"}
    nodes_hi = {n["id"] for n in d_hi["nodes"] if n.get("role") != "outcome"}
    shared_nodes = nodes_lo & nodes_hi

    # Compute nGED for subtitle
    edges_lo_set = {(e["from"], e["to"]) for e in d_lo["edges"]}
    edges_hi_set = {(e["from"], e["to"]) for e in d_hi["edges"]}
    nged = normalized_ged(nodes_lo, edges_lo_set, nodes_hi, edges_hi_set)
    shared_edge_set = edges_lo_set & edges_hi_set

    # ── Build unified layout from union graph ──
    # Combine both graphs into one for layout computation
    G_union = nx.DiGraph()
    for n in d_lo["nodes"] + d_hi["nodes"]:
        G_union.add_node(n["id"], role=n.get("role", "factor"))
    for e in d_lo["edges"] + d_hi["edges"]:
        G_union.add_edge(e["from"], e["to"])

    # Hand-tuned positions for shared nodes so both panels align cleanly.
    # Shared: tesla_stock, board_confidence, succession_plans, regulatory_pressure, outcome
    # Unique T=0.0: elon_ambitions, elon_health
    # Unique T=1.0: company-performance, elon_personal_life
    shared_pos = {
        "outcome":             (0.0, -0.9),
        "tesla_stock":         (-0.6,  0.9),
        "board_confidence":    ( 0.6,  0.9),
        "regulatory_pressure": (-0.6, -0.1),
        "succession_plans":    ( 0.6, -0.1),
    }
    pos_lo = dict(shared_pos)
    pos_lo["elon_ambitions"] = (-1.4,  0.4)
    pos_lo["elon_health"]    = (-1.4, -0.6)

    pos_hi = dict(shared_pos)
    pos_hi["company-performance"] = (-1.4,  0.4)
    pos_hi["elon_personal_life"]  = (-1.4, -0.6)

    def _label(node_id):
        label = node_id.replace("_", " ").replace("-", " ").title()
        return "\n".join(textwrap.wrap(label, width=14))

    def _draw_dag(ax, data, temp, panel_label, pos):
        nodes = data["nodes"]
        edges = data["edges"]
        prob = data["initial_probability"]
        G = _build_digraph(nodes, edges)

        factor_ids = [n["id"] for n in nodes if n.get("role") != "outcome"]
        outcome_ids = [n["id"] for n in nodes if n.get("role") == "outcome"]

        # Color shared vs unique nodes
        shared_factors = [n for n in factor_ids if n in shared_nodes]
        unique_factors = [n for n in factor_ids if n not in shared_nodes]

        NODE_SIZE = 4500
        if shared_factors:
            nx.draw_networkx_nodes(G, pos, nodelist=shared_factors, ax=ax,
                                   node_color="#A8D0E6", node_size=NODE_SIZE,
                                   edgecolors="#333333", linewidths=1.5)
        if unique_factors:
            nx.draw_networkx_nodes(G, pos, nodelist=unique_factors, ax=ax,
                                   node_color="#F4A582", node_size=NODE_SIZE,
                                   edgecolors="#333333", linewidths=1.5)
        if outcome_ids:
            nx.draw_networkx_nodes(G, pos, nodelist=outcome_ids, ax=ax,
                                   node_color="#E69F00", node_size=5000,
                                   edgecolors="#333333", linewidths=2.0,
                                   node_shape="s")

        # Shared vs unique edges
        all_edges = [(e["from"], e["to"]) for e in edges]
        shared_e = [e for e in all_edges if e in shared_edge_set]
        unique_e = [e for e in all_edges if e not in shared_edge_set]

        if shared_e:
            nx.draw_networkx_edges(G, pos, edgelist=shared_e, ax=ax,
                                   edge_color="#333333", width=2.0, alpha=0.8,
                                   arrows=True, arrowsize=18, arrowstyle="-|>",
                                   connectionstyle="arc3,rad=0.12",
                                   min_source_margin=45, min_target_margin=45)
        if unique_e:
            nx.draw_networkx_edges(G, pos, edgelist=unique_e, ax=ax,
                                   edge_color="#D55E00", width=2.0, alpha=0.7,
                                   arrows=True, arrowsize=18, arrowstyle="-|>",
                                   connectionstyle="arc3,rad=0.12",
                                   min_source_margin=40, min_target_margin=40,
                                   style="dashed")

        labels = {n: _label(n) if n != outcome_ids[0] else "Outcome"
                  for n in G.nodes}
        nx.draw_networkx_labels(G, pos, labels=labels, ax=ax,
                                font_size=9, font_weight="bold", font_color="black")

        analysis = analyze_network(nodes, edges)
        title_str = (f"Temperature = {temp}\n"
                     f"{analysis.n_nodes} nodes, {analysis.n_edges} edges  |  "
                     f"P(Yes) = {prob:.0%}")
        ax.set_title(title_str, fontsize=13, fontweight="bold", pad=16,
                     linespacing=1.8)
        ax.text(-0.05, 1.08, panel_label, transform=ax.transAxes,
                fontsize=16, fontweight="bold")
        ax.set_axis_off()
        ax.margins(0.25)

    fig, (ax_l, ax_r) = plt.subplots(1, 2, figsize=(18, 9))
    fig.patch.set_facecolor("white")

    _draw_dag(ax_l, d_lo, T_LO, "(a)", pos_lo)
    _draw_dag(ax_r, d_hi, T_HI, "(b)", pos_hi)

    # Question as suptitle
    q_text = d_lo.get("question_text", "")
    if len(q_text) > 80:
        q_text = q_text[:77] + "..."
    fig.suptitle(q_text, fontsize=13, fontweight="bold", y=1.02)

    # Legend
    legend_elements = [
        Patch(facecolor="#A8D0E6", edgecolor="#333", label="Shared factor"),
        Patch(facecolor="#F4A582", edgecolor="#333", label="Unique factor"),
        Patch(facecolor="#E69F00", edgecolor="#333", label="Outcome"),
        Line2D([0], [0], color="#333", linewidth=2, label="Shared edge"),
        Line2D([0], [0], color="#D55E00", linewidth=2, linestyle="dashed",
               label="Unique edge"),
    ]
    fig.legend(handles=legend_elements, loc="lower center", ncol=5,
               fontsize=10, frameon=False, bbox_to_anchor=(0.5, -0.02))

    # nGED annotation
    fig.text(0.5, -0.06, f"Normalized Graph Edit Distance = {nged:.2f}",
             ha="center", fontsize=12, fontstyle="italic", color="#555")

    plt.tight_layout()
    fig_path = OUT / "supplementary" / "temperature_exemplar_pair"
    for ext in ["png", "pdf"]:
        fig.savefig(f"{fig_path}.{ext}", dpi=300, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"Figure saved to {fig_path}.png")


def main():
    parser = argparse.ArgumentParser(
        description="Temperature sensitivity analysis for causal DAGs",
    )
    parser.add_argument("--model", default="llama-70b", choices=list(MODEL_MAP.keys()))
    parser.add_argument("--max-questions", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", type=str, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--analyze-only", action="store_true",
                        help="Skip data collection, just run analysis on existing data")
    args = parser.parse_args()

    if args.output_dir is None:
        model_short = args.model.replace("-", "_")
        args.output_dir = f"outputs/sensitivity/causal/{model_short}_temperature"

    if not args.analyze_only:
        run_collection(args)

    run_analysis(args)


if __name__ == "__main__":
    main()
