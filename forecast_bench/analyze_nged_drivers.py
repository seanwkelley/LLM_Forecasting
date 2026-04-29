"""Diagnose what drives cross-model nGED = 0.881.

Breaks the aggregate number into interpretable components:
  1. Graph size per model (nodes, edges, density)
  2. Node-ops vs edge-ops share of nGED
  3. Node-matching rate per pair
  4. Core-spine overlap (top-k centrality nodes)
  5. Where unmatched nodes sit in the centrality distribution
"""
from __future__ import annotations

import itertools
import json
from pathlib import Path

import networkx as nx
import numpy as np
from scipy.optimize import linear_sum_assignment

from forecast_bench.semantic_graph_match import (
    NODE_EMB_CACHE, NODE_EMB_KEYS_CACHE,
    _cosine_matrix, _load_cache,
)
from forecast_bench.analyze_cross_model_ged import MODEL_DIRS, load_all_model_dags


THRESHOLD = 0.7


def build_dg(nodes, edges):
    g = nx.DiGraph()
    for n in nodes:
        g.add_node(n["id"])
    for e in edges:
        g.add_edge(e["from"], e["to"])
    return g


def top_centrality_nodes(nodes, edges, k=5):
    g = build_dg(nodes, edges)
    if g.number_of_nodes() == 0:
        return set()
    bc = nx.betweenness_centrality(g)
    # tie-break deterministically by id
    ranked = sorted(bc.items(), key=lambda kv: (-kv[1], kv[0]))
    return {nid for nid, _ in ranked[:k]}


def match_pair(nodes1, nodes2, model1, model2, qid, node_idx, node_mat, thr=THRESHOLD):
    """Hungarian match, return list of matched (i,j) indices above threshold."""
    if not nodes1 or not nodes2:
        return []

    def vecs(nodes, model):
        keys = [f"node|{qid}|{model}|{n['id']}" for n in nodes]
        idxs = [node_idx.get(k) for k in keys]
        if any(i is None for i in idxs):
            return None
        return node_mat[np.array(idxs)]

    v1 = vecs(nodes1, model1)
    v2 = vecs(nodes2, model2)
    if v1 is None or v2 is None:
        return []
    sim = _cosine_matrix(v1, v2)
    cost = 1.0 - sim
    r, c = linear_sum_assignment(cost)
    return [(int(a), int(b)) for a, b in zip(r, c) if float(sim[a, b]) >= thr]


def main():
    all_dags = load_all_model_dags()
    model_names = list(all_dags.keys())

    # shared qids
    shared = set(all_dags[model_names[0]].keys())
    for m in model_names[1:]:
        shared &= set(all_dags[m].keys())
    shared = sorted(shared)
    print(f"\n{len(shared)} shared questions across {len(model_names)} models\n")

    # ── 1. Graph size per model ───────────────────────────────────────────
    print("=" * 72)
    print("1. Graph size per model (on shared questions)")
    print("=" * 72)
    size_stats = {}
    for m in model_names:
        nn, ne, dens = [], [], []
        for qid in shared:
            d = all_dags[m][qid]
            n = len(d.get("nodes", []))
            e = len(d.get("edges", []))
            nn.append(n)
            ne.append(e)
            if n > 1:
                dens.append(e / (n * (n - 1)))
        size_stats[m] = {
            "nodes_mean": float(np.mean(nn)),
            "nodes_median": float(np.median(nn)),
            "edges_mean": float(np.mean(ne)),
            "edges_median": float(np.median(ne)),
            "density_mean": float(np.mean(dens)),
        }
        print(f"  {m:22s}  nodes={np.mean(nn):5.2f} (med {np.median(nn):.0f})  "
              f"edges={np.mean(ne):5.2f} (med {np.median(ne):.0f})  "
              f"density={np.mean(dens):.3f}")

    all_sizes = [size_stats[m]["nodes_mean"] for m in model_names]
    print(f"\n  Cross-model node-count range: {min(all_sizes):.1f} – {max(all_sizes):.1f}")
    print(f"  Cross-model node-count std:   {np.std(all_sizes):.2f}")

    # ── 2. Node-ops vs edge-ops share of nGED ─────────────────────────────
    node_idx, node_mat = _load_cache(NODE_EMB_CACHE, NODE_EMB_KEYS_CACHE)
    if node_mat is None:
        raise RuntimeError("No node embeddings cache — run analyze_cross_model_ged first")

    print("\n" + "=" * 72)
    print("2. Decomposition of nGED: node_ops vs edge_ops contribution")
    print("=" * 72)
    pairs = list(itertools.combinations(model_names, 2))

    # Aggregate across all pairs x questions
    node_ops_frac = []      # node_ops / (node_ops + edge_ops)
    nged_total = []
    match_rate_g1 = []      # matched / |V1| per pair (asymmetric)
    match_rate_g2 = []
    size_ratio = []         # min(|V1|,|V2|) / max(|V1|,|V2|)

    for qid in shared:
        for m1, m2 in pairs:
            d1 = all_dags[m1][qid]
            d2 = all_dags[m2][qid]
            n1 = d1.get("nodes", [])
            n2 = d2.get("nodes", [])
            e1 = d1.get("edges", [])
            e2 = d2.get("edges", [])
            if not n1 or not n2:
                continue
            matches = match_pair(n1, n2, m1, m2, qid, node_idx, node_mat)
            matched = len(matches)
            node_ops = (len(n1) - matched) + (len(n2) - matched)

            remap = {n2[j]["id"]: n1[i]["id"] for i, j in matches}
            e1_set = {(e["from"], e["to"]) for e in e1}
            G2_PREFIX = "__g2__"
            ids2 = {n["id"] for n in n2}
            canon_g2 = {nid: (remap.get(nid, f"{G2_PREFIX}{nid}")) for nid in ids2}
            e2_remap = {(canon_g2.get(e["from"], e["from"]),
                         canon_g2.get(e["to"], e["to"])) for e in e2}
            edge_ops = len(e1_set ^ e2_remap)

            ids1 = {n["id"] for n in n1}
            canon_union = ids1 | set(canon_g2.values())
            denom = len(canon_union) + len(e1_set | e2_remap)
            if denom > 0:
                nged = (node_ops + edge_ops) / denom
                nged_total.append(nged)
                total_ops = node_ops + edge_ops
                if total_ops > 0:
                    node_ops_frac.append(node_ops / total_ops)
            match_rate_g1.append(matched / len(n1))
            match_rate_g2.append(matched / len(n2))
            size_ratio.append(min(len(n1), len(n2)) / max(len(n1), len(n2)))

    print(f"  Mean nGED (recomputed):            {np.mean(nged_total):.3f}")
    print(f"  Node-ops share of total edits:     {np.mean(node_ops_frac)*100:.1f}%")
    print(f"  Edge-ops share of total edits:     {(1 - np.mean(node_ops_frac))*100:.1f}%")
    print(f"  Mean node-match rate per graph:    {np.mean(match_rate_g1 + match_rate_g2)*100:.1f}%")
    print(f"  Mean size ratio (small/large):     {np.mean(size_ratio):.3f}")

    # ── 3. Core-spine overlap (top-k centrality) ──────────────────────────
    print("\n" + "=" * 72)
    print("3. Core-spine overlap: are top-k centrality nodes shared across models?")
    print("=" * 72)
    for k in [3, 5]:
        spine_overlap_cnt = []
        spine_overlap_any = []  # at least one matched
        for qid in shared:
            for m1, m2 in pairs:
                d1 = all_dags[m1][qid]
                d2 = all_dags[m2][qid]
                top1 = top_centrality_nodes(d1["nodes"], d1["edges"], k=k)
                top2 = top_centrality_nodes(d2["nodes"], d2["edges"], k=k)
                if not top1 or not top2:
                    continue
                matches = match_pair(d1["nodes"], d2["nodes"], m1, m2, qid,
                                     node_idx, node_mat)
                # which of top1 nodes got matched to any top2 node via Hungarian?
                top1_ids = [d1["nodes"][i]["id"] for i, _ in matches
                            if d1["nodes"][i]["id"] in top1]
                matched_top2 = [d2["nodes"][j]["id"] for i, j in matches
                                if d1["nodes"][i]["id"] in top1
                                and d2["nodes"][j]["id"] in top2]
                # spine overlap = |top1 members matched to top2 members| / k
                spine_overlap_cnt.append(len(matched_top2) / k)
                spine_overlap_any.append(1 if matched_top2 else 0)

        print(f"  Top-{k} centrality nodes:  "
              f"mean overlap = {np.mean(spine_overlap_cnt)*100:.1f}% of k, "
              f"any shared >=1: {np.mean(spine_overlap_any)*100:.1f}% of pairs")

    # ── 4. Where do unmatched nodes sit? ──────────────────────────────────
    print("\n" + "=" * 72)
    print("4. Are unmatched nodes peripheral (low-centrality) or central?")
    print("=" * 72)
    matched_centralities = []
    unmatched_centralities = []
    for qid in shared:
        for m1, m2 in pairs:
            d1 = all_dags[m1][qid]
            d2 = all_dags[m2][qid]
            n1 = d1["nodes"]; e1 = d1["edges"]
            n2 = d2["nodes"]; e2 = d2["edges"]
            if not n1 or not n2:
                continue
            g1 = build_dg(n1, e1)
            bc1 = nx.betweenness_centrality(g1) if g1.number_of_nodes() else {}
            matches = match_pair(n1, n2, m1, m2, qid, node_idx, node_mat)
            matched_ids = {n1[i]["id"] for i, _ in matches}
            for n in n1:
                c = bc1.get(n["id"], 0.0)
                if n["id"] in matched_ids:
                    matched_centralities.append(c)
                else:
                    unmatched_centralities.append(c)
    print(f"  Matched nodes   betweenness: mean = {np.mean(matched_centralities):.4f}  "
          f"median = {np.median(matched_centralities):.4f}  n = {len(matched_centralities)}")
    print(f"  Unmatched nodes betweenness: mean = {np.mean(unmatched_centralities):.4f}  "
          f"median = {np.median(unmatched_centralities):.4f}  n = {len(unmatched_centralities)}")
    ratio = np.mean(matched_centralities) / max(np.mean(unmatched_centralities), 1e-9)
    print(f"  Matched / unmatched ratio:   {ratio:.2f}×")

    # ── 5. Outcome-node matching rate specifically ────────────────────────
    print("\n" + "=" * 72)
    print("5. Outcome-node matching (should be ~universal since question is fixed)")
    print("=" * 72)
    outcome_matched = 0
    outcome_total = 0
    for qid in shared:
        for m1, m2 in pairs:
            d1 = all_dags[m1][qid]
            d2 = all_dags[m2][qid]
            n1 = d1["nodes"]; n2 = d2["nodes"]
            outcome1 = next((n for n in n1 if n.get("role") == "outcome"), None)
            outcome2 = next((n for n in n2 if n.get("role") == "outcome"), None)
            if not outcome1 or not outcome2:
                continue
            matches = match_pair(n1, n2, m1, m2, qid, node_idx, node_mat)
            matched_outcome = any(
                n1[i]["id"] == outcome1["id"] and n2[j]["id"] == outcome2["id"]
                for i, j in matches)
            outcome_total += 1
            outcome_matched += int(matched_outcome)
    print(f"  Outcome nodes matched across pairs: "
          f"{outcome_matched}/{outcome_total} = {outcome_matched/outcome_total*100:.1f}%")

    # ── 6. Conditional edge agreement on matched subgraph ────────────────
    print("\n" + "=" * 72)
    print("6. Edge agreement on matched subgraph (ignoring unmatched nodes)")
    print("=" * 72)
    cond_edge_jaccard = []
    nmatched_list = []
    for qid in shared:
        for m1, m2 in pairs:
            d1 = all_dags[m1][qid]
            d2 = all_dags[m2][qid]
            n1 = d1["nodes"]; n2 = d2["nodes"]
            e1 = d1["edges"]; e2 = d2["edges"]
            if not n1 or not n2:
                continue
            matches = match_pair(n1, n2, m1, m2, qid, node_idx, node_mat)
            if len(matches) < 2:
                continue
            remap = {n2[j]["id"]: n1[i]["id"] for i, j in matches}
            matched_g1 = {n1[i]["id"] for i, _ in matches}
            e1_sub = {(e["from"], e["to"]) for e in e1
                      if e["from"] in matched_g1 and e["to"] in matched_g1}
            e2_sub = {(remap[e["from"]], remap[e["to"]]) for e in e2
                      if e["from"] in remap and e["to"] in remap}
            if not e1_sub and not e2_sub:
                continue
            jacc = len(e1_sub & e2_sub) / max(len(e1_sub | e2_sub), 1)
            cond_edge_jaccard.append(jacc)
            nmatched_list.append(len(matches))
    print(f"  Edge Jaccard on matched subgraph:  {np.mean(cond_edge_jaccard):.3f}")
    print(f"  (Mean matched nodes per pair:      {np.mean(nmatched_list):.1f})")

    # ── 7. Unique outcome-node centrality, for context ───────────────────
    print("\n" + "=" * 72)
    print("7. Outcome node centrality per model (should be high for coherent DAGs)")
    print("=" * 72)
    for m in model_names:
        bcs = []
        for qid in shared:
            d = all_dags[m][qid]
            n = d["nodes"]; e = d["edges"]
            if not n:
                continue
            out = next((x for x in n if x.get("role") == "outcome"), None)
            if not out:
                continue
            g = build_dg(n, e)
            if g.number_of_nodes() < 2:
                continue
            bc = nx.betweenness_centrality(g)
            bcs.append(bc.get(out["id"], 0.0))
        print(f"  {m:22s}  outcome betweenness = {np.mean(bcs):.3f}")


if __name__ == "__main__":
    main()
