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
from forecast_bench.semantic_graph_match import semantic_jaccard_pair

plt.rcParams.update({"font.family": "Arial", "font.size": 10, "figure.dpi": 300})

BLUE, ORANGE, VERMILLION, GREEN = "#0072B2", "#E69F00", "#D55E00", "#009E73"

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


def run_forecast(client, question_text: str, max_retries: int = 3):
    """Run Stage 1 causal forecast with retries."""
    user_prompt = build_causal_forecast_prompt(question_text)

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

        # Check for disconnected nodes (zero in-degree AND zero out-degree)
        edge_nodes = set(e.get("from") for e in edges) | set(e.get("to") for e in edges)
        disconnected = [n["id"] for n in nodes if n["id"] not in edge_nodes]
        if not valid or not edges or len(disconnected) > 0:
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
        questions_file=args.questions_file,
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
            max_tokens=2000,
        )

        print(f"\n--- Temperature {temp} ---")

        for q_idx, question in enumerate(questions):
            qid = question["id"]
            result_path = temp_dir / f"{qid}.json"

            if args.resume and result_path.exists():
                print(f"  [{q_idx+1}/{len(questions)}] {qid[:40]} -- cached")
                continue

            print(f"  [{q_idx+1}/{len(questions)}] {qid[:40]}...", end=" ")

            data = None
            for _outer in range(10):
                data = run_forecast(client, question["question"])
                client.rate_limit_wait()
                if data is not None:
                    break
                print(f"retry {_outer+1}/10...", end=" ")

            if data is None:
                print("FAILED after 10 attempts")
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

    # ── Compute pairwise semantic nGED (embedding-matched nodes, then edge overlap) ──
    from forecast_bench.semantic_graph_match import (
        _ensure_embeddings, _cosine_matrix, _hungarian_match,
        _get_api_key, NODE_EMB_CACHE, NODE_EMB_KEYS_CACHE,
    )
    api_key = _get_api_key()

    # Pre-embed all nodes across all temperatures
    all_texts = {}
    for t in available_temps:
        for qid in shared_all:
            for n in temp_data[t][qid]["nodes"]:
                key = f"node|{qid}|t{t}|{n['id']}"
                all_texts[key] = f"{n['id']}: {n.get('description', n['id'])}"
    print(f"Embedding {len(all_texts)} node texts for semantic nGED...")
    key_to_idx, matrix = _ensure_embeddings(all_texts, NODE_EMB_CACHE, NODE_EMB_KEYS_CACHE, api_key)

    nged_matrix = np.zeros((n_temps, n_temps))
    print("\nSemantic nGED (embedding-matched):")
    for i in range(n_temps):
        for j in range(i + 1, n_temps):
            t_i, t_j = available_temps[i], available_temps[j]
            ngeds = []
            for qid in shared_all:
                d_i = temp_data[t_i][qid]
                d_j = temp_data[t_j][qid]
                nodes_i = d_i["nodes"]
                nodes_j = d_j["nodes"]
                edges_i = d_i["edges"]
                edges_j = d_j["edges"]

                # Get embeddings for this pair
                keys_i = [f"node|{qid}|t{t_i}|{n['id']}" for n in nodes_i]
                keys_j = [f"node|{qid}|t{t_j}|{n['id']}" for n in nodes_j]
                try:
                    vecs_i = matrix[[key_to_idx[k] for k in keys_i]]
                    vecs_j = matrix[[key_to_idx[k] for k in keys_j]]
                except KeyError:
                    continue

                # Hungarian matching on cosine similarity
                cos = _cosine_matrix(vecs_i, vecs_j)
                matches = _hungarian_match(cos, threshold=0.7)

                # Build node remap: j_id -> i_id for matched pairs
                remap = {}
                matched_i = set()
                matched_j = set()
                for mi, mj, sim in matches:
                    remap[nodes_j[mj]["id"]] = nodes_i[mi]["id"]
                    matched_i.add(nodes_i[mi]["id"])
                    matched_j.add(nodes_j[mj]["id"])

                # Compute semantic nGED
                # Nodes: matched count as shared, unmatched count as insertions/deletions
                all_node_ids_i = set(n["id"] for n in nodes_i)
                all_node_ids_j = set(n["id"] for n in nodes_j)
                n_matched = len(matches)
                n_only_i = len(all_node_ids_i) - n_matched
                n_only_j = len(all_node_ids_j) - n_matched
                node_ops = n_only_i + n_only_j

                # Edges: remap j edges to i namespace, then compare
                ei = set((e["from"], e["to"]) for e in edges_i)
                ej_remapped = set((remap.get(e["from"], e["from"]), remap.get(e["to"], e["to"])) for e in edges_j)
                edge_ops = len(ei ^ ej_remapped)

                total = len(all_node_ids_i | all_node_ids_j) + len(ei | ej_remapped)
                nged = (node_ops + edge_ops) / total if total > 0 else 0
                ngeds.append(nged)

            nged_mean = np.mean(ngeds)
            nged_matrix[i, j] = nged_matrix[j, i] = nged_mean
            print(f"  T={t_i:.1f} vs T={t_j:.1f}: mean semantic nGED={nged_mean:.3f} (n={len(ngeds)})")

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
    cbar.set_label("Semantic nGED (0=identical, 1=disjoint)", fontsize=8)
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
    """Plot side-by-side DAGs for the same question at T=0.0 and T=1.0.

    Uses cached node embeddings for semantic matching, unified hierarchical
    layout so matched nodes share positions, and alternating edge curvature
    to keep connections visible.
    """
    import textwrap
    import networkx as nx
    from numpy.linalg import norm
    from scipy.optimize import linear_sum_assignment
    from matplotlib.patches import Patch
    from matplotlib.lines import Line2D
    from forecast_bench.network_analysis import analyze_network, _build_digraph
    from forecast_bench.semantic_graph_match import NODE_EMB_CACHE, NODE_EMB_KEYS_CACHE

    EXEMPLAR_QID = "0x7ffa1fcfaeac86d4a89afcb74c90296f0e7c3744ce5206183c9cb38651526e63"
    T_LO, T_HI = 0.0, 1.0
    THRESHOLD = 0.7
    LAYER_WIDTH, LAYER_HEIGHT = 5.5, 4.5

    if T_LO not in temp_data or T_HI not in temp_data:
        print("[SKIP] Need T=0.0 and T=1.0 for exemplar pair")
        return
    if EXEMPLAR_QID not in temp_data[T_LO] or EXEMPLAR_QID not in temp_data[T_HI]:
        print(f"[SKIP] Exemplar question {EXEMPLAR_QID} not found at both temps")
        return

    d_lo = temp_data[T_LO][EXEMPLAR_QID]
    d_hi = temp_data[T_HI][EXEMPLAR_QID]
    nodes_lo = [n for n in d_lo["nodes"] if n.get("role") != "outcome"]
    nodes_hi = [n for n in d_hi["nodes"] if n.get("role") != "outcome"]

    # ── Semantic matching via cached embeddings ──
    import json
    keys_json = json.loads(NODE_EMB_KEYS_CACHE.read_text())
    key_to_idx = {k: i for i, k in enumerate(keys_json)}
    emb_mat = np.load(NODE_EMB_CACHE)["embeddings"]

    def _get_vecs(nodes, cond):
        keys = [f"node|{EXEMPLAR_QID}|{cond}|{n['id']}" for n in nodes]
        idxs = [key_to_idx[k] for k in keys if k in key_to_idx]
        if len(idxs) != len(nodes):
            return None
        return emb_mat[np.array(idxs)]

    v_lo = _get_vecs(nodes_lo, "temp0.0")
    v_hi = _get_vecs(nodes_hi, "temp1.0")
    if v_lo is None or v_hi is None:
        print("[SKIP] Missing cached embeddings for exemplar pair")
        return

    cos = (v_lo / norm(v_lo, axis=1, keepdims=True)) @ \
          (v_hi / norm(v_hi, axis=1, keepdims=True)).T
    row_ind, col_ind = linear_sum_assignment(1 - cos)

    remap = {}  # hi_id -> lo_id (canonical)
    for r, c in zip(row_ind, col_ind):
        if cos[r, c] >= THRESHOLD:
            remap[nodes_hi[c]["id"]] = nodes_lo[r]["id"]

    # ── Compute semantic nGED ──
    n_matched = len(remap)
    all_ids_lo = set(n["id"] for n in d_lo["nodes"])
    all_ids_hi = set(n["id"] for n in d_hi["nodes"])
    node_ops = (len(all_ids_lo) - n_matched) + (len(all_ids_hi) - n_matched)
    ei = set((e["from"], e["to"]) for e in d_lo["edges"])
    ej_remapped = set((remap.get(e["from"], e["from"]), remap.get(e["to"], e["to"]))
                      for e in d_hi["edges"])
    edge_ops = len(ei ^ ej_remapped)
    total = len(all_ids_lo | all_ids_hi) + len(ei | ej_remapped)
    nged = (node_ops + edge_ops) / total if total > 0 else 0

    # ── Layout: include below-threshold matches for positional alignment ──
    match_lo_to_hi = {v: k for k, v in remap.items()}
    # Add near-miss pairs for layout alignment
    for r, c in zip(row_ind, col_ind):
        lo_id, hi_id = nodes_lo[r]["id"], nodes_hi[c]["id"]
        if lo_id not in match_lo_to_hi and cos[r, c] >= 0.5:
            match_lo_to_hi[lo_id] = hi_id
    match_hi_to_lo = {v: k for k, v in match_lo_to_hi.items()}
    shared_lo = set(match_lo_to_hi.keys())
    shared_hi = set(match_lo_to_hi.values())

    def canonical(nid, is_hi=False):
        if is_hi and nid in match_hi_to_lo:
            return match_hi_to_lo[nid]
        return nid

    # Unified graph for hierarchical layout
    G_union = nx.DiGraph()
    for n in d_lo["nodes"]:
        G_union.add_node(n["id"], role=n.get("role", "factor"))
    for n in d_hi["nodes"]:
        G_union.add_node(canonical(n["id"], True), role=n.get("role", "factor"))
    for e in d_lo["edges"]:
        G_union.add_edge(e["from"], e["to"])
    for e in d_hi["edges"]:
        G_union.add_edge(canonical(e["from"], True), canonical(e["to"], True))

    outcome = [n for n in G_union.nodes if G_union.nodes[n].get("role") == "outcome"]
    R = G_union.reverse()
    dists = nx.shortest_path_length(R, source=outcome[0]) if outcome else {}
    max_d = max(dists.values()) if dists else 1
    layers = {}
    for n in G_union.nodes:
        d = dists.get(n, max_d + 1)
        layers.setdefault(d, []).append(n)

    # Barycenter ordering: sort nodes within each layer by the average
    # x-position of their successors to minimize edge crossings.
    # First pass: place outcome layer, then work upward.
    pos_unified = {}
    sorted_layers = sorted(layers.items())
    # Initial pass with alphabetical order
    for layer_y, layer_nodes in sorted_layers:
        n_in = len(layer_nodes)
        for i, n in enumerate(sorted(layer_nodes)):
            x = (i - (n_in - 1) / 2) * LAYER_WIDTH
            pos_unified[n] = (x, layer_y * LAYER_HEIGHT)
    # Barycenter refinement: reorder each layer by avg x of successors
    for layer_y, layer_nodes in sorted_layers:
        if len(layer_nodes) <= 1:
            continue
        barycenters = {}
        for n in layer_nodes:
            succs = list(G_union.successors(n))
            if succs:
                avg_x = np.mean([pos_unified[s][0] for s in succs
                                 if s in pos_unified])
                barycenters[n] = avg_x
            else:
                barycenters[n] = pos_unified.get(n, (0, 0))[0]
        reordered = sorted(layer_nodes, key=lambda n: barycenters[n])
        n_in = len(reordered)
        for i, n in enumerate(reordered):
            x = (i - (n_in - 1) / 2) * LAYER_WIDTH
            pos_unified[n] = (x, layer_y * LAYER_HEIGHT)

    pos_lo = {n["id"]: pos_unified[n["id"]]
              for n in d_lo["nodes"] if n["id"] in pos_unified}
    pos_hi = {n["id"]: pos_unified[canonical(n["id"], True)]
              for n in d_hi["nodes"] if canonical(n["id"], True) in pos_unified}

    # Shared edges in canonical space
    edges_lo_can = {(e["from"], e["to"]) for e in d_lo["edges"]}
    edges_hi_can = {(canonical(e["from"], True), canonical(e["to"], True))
                    for e in d_hi["edges"]}
    shared_edges_can = edges_lo_can & edges_hi_can

    def _label(node_id):
        label = node_id.replace("_", " ").replace("-", " ").title()
        return "\n".join(textwrap.wrap(label, width=14))

    def _draw_dag(ax, data, pos, panel_label, temp, shared_set, is_hi=False):
        G = _build_digraph(data["nodes"], data["edges"])
        factor_ids = [n for n in G.nodes if G.nodes[n].get("role") != "outcome"]
        outcome_ids = [n for n in G.nodes if G.nodes[n].get("role") == "outcome"]
        shared_f = [n for n in factor_ids if n in shared_set]
        unique_f = [n for n in factor_ids if n not in shared_set]

        # Classify edges as shared/unique in canonical space
        all_edges = [(e["from"], e["to"]) for e in data["edges"]]
        can_edges = ([(canonical(a, True), canonical(b, True)) for a, b in all_edges]
                     if is_hi else all_edges)
        shared_e = [e for e, ce in zip(all_edges, can_edges)
                    if ce in shared_edges_can]
        unique_e = [e for e, ce in zip(all_edges, can_edges)
                    if ce not in shared_edges_can]

        # Pre-sort edges per target by source x-position for clean fan layout
        all_edge_list = shared_e + unique_e
        from collections import defaultdict
        edges_by_target = defaultdict(list)
        for src, tgt in all_edge_list:
            edges_by_target[tgt].append(src)
        # Sort each target's sources by x-position
        target_edge_order = {}
        for tgt, sources in edges_by_target.items():
            sorted_srcs = sorted(sources, key=lambda s: pos.get(s, (0,0))[0])
            target_edge_order[tgt] = {s: i for i, s in enumerate(sorted_srcs)}

        def _draw_edge(src, tgt, color, style, alpha):
            sx, sy = pos.get(src, (0, 0))
            tx, ty = pos.get(tgt, (0, 0))
            layer_diff = abs(sy - ty) / LAYER_HEIGHT
            n_to = len(edges_by_target.get(tgt, []))
            # Index by source x-position rank (0 = leftmost source)
            idx = target_edge_order.get(tgt, {}).get(src, 0)
            # Center the fan: leftmost source gets negative rad,
            # rightmost gets positive, middle gets ~0
            centered = idx - (n_to - 1) / 2.0  # e.g. for 4 edges: -1.5, -0.5, 0.5, 1.5
            if layer_diff < 0.1:
                # Same layer — strong arc
                rad = 0.45 if sx < tx else -0.45
            elif n_to <= 1:
                rad = 0.12
            else:
                # Fan: spread edges evenly, scaled by number of edges.
                # Negate so leftmost source curves right (toward target)
                # and rightmost curves left, creating a natural fan-in.
                spread = 0.18 if layer_diff <= 1.1 else 0.22
                rad = -centered * spread
            nx.draw_networkx_edges(
                G, pos, edgelist=[(src, tgt)], ax=ax,
                edge_color=color, width=1.8, alpha=alpha, style=style,
                arrows=True, arrowsize=20, arrowstyle="-|>",
                connectionstyle=f"arc3,rad={rad}",
                min_source_margin=50, min_target_margin=50)

        # Draw edges FIRST (underneath)
        for src, tgt in shared_e:
            _draw_edge(src, tgt, "#333333", "solid", 0.8)
        for src, tgt in unique_e:
            _draw_edge(src, tgt, "#D55E00", "dashed", 0.7)

        # Draw nodes ON TOP of edges so they occlude crossing edge paths
        NODE_SIZE = 5500
        if shared_f:
            nx.draw_networkx_nodes(G, pos, nodelist=shared_f, ax=ax,
                                   node_color="#A8D0E6", node_size=NODE_SIZE,
                                   edgecolors="#333333", linewidths=1.5)
        if unique_f:
            nx.draw_networkx_nodes(G, pos, nodelist=unique_f, ax=ax,
                                   node_color="#F4A582", node_size=NODE_SIZE,
                                   edgecolors="#333333", linewidths=1.5)
        if outcome_ids:
            nx.draw_networkx_nodes(G, pos, nodelist=outcome_ids, ax=ax,
                                   node_color="#E69F00", node_size=6000,
                                   edgecolors="#333333", linewidths=2.0,
                                   node_shape="s")

        labels = {n: "Outcome" if n in outcome_ids else _label(n)
                  for n in G.nodes}
        nx.draw_networkx_labels(G, pos, labels=labels, ax=ax,
                                font_size=14, font_weight="bold",
                                font_color="black")

        analysis = analyze_network(data["nodes"], data["edges"])
        prob = data["initial_probability"]
        ax.set_title(f"Temperature = {temp}\n"
                     f"{analysis.n_nodes} nodes, {analysis.n_edges} edges  |  "
                     f"P(Yes) = {prob:.0%}",
                     fontsize=18, fontweight="bold", pad=20, linespacing=1.8)
        ax.text(-0.05, 1.08, panel_label, transform=ax.transAxes,
                fontsize=22, fontweight="bold")
        ax.set_axis_off()
        ax.margins(0.30)

    fig, (ax_l, ax_r) = plt.subplots(1, 2, figsize=(26, 11))
    fig.patch.set_facecolor("white")
    _draw_dag(ax_l, d_lo, pos_lo, "(a)", T_LO, shared_lo)
    _draw_dag(ax_r, d_hi, pos_hi, "(b)", T_HI, shared_hi, is_hi=True)

    q_text = d_lo.get("question_text", "")[:80]
    if q_text == "New pandemic in 2025?":
        q_text = "Will there be a new pandemic in 2025?"
    fig.suptitle(q_text, fontsize=20, fontweight="bold", y=1.02)

    legend_elements = [
        Patch(facecolor="#A8D0E6", edgecolor="#333", label="Shared factor"),
        Patch(facecolor="#E69F00", edgecolor="#333", label="Outcome"),
        Line2D([0], [0], color="#333", linewidth=1.8, label="Shared edge"),
        Line2D([0], [0], color="#D55E00", linewidth=1.8, linestyle="dashed",
               label="Unique edge"),
    ]
    fig.legend(handles=legend_elements, loc="lower center", ncol=4,
               fontsize=15, frameon=False, bbox_to_anchor=(0.5, -0.02))
    fig.text(0.5, -0.05, f"Semantic nGED = {nged:.2f}",
             ha="center", fontsize=16, fontstyle="italic", color="#555")

    plt.tight_layout()
    fig_path = OUT / "supplement" / "temperature_exemplar_pair"
    for ext in ["png", "pdf"]:
        fig.savefig(f"{fig_path}.{ext}", dpi=300, bbox_inches="tight",
                    facecolor="white")
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
    parser.add_argument("--questions-file", default=None, help="Path to local JSON file with questions")
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
