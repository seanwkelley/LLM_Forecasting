#!/usr/bin/env python3
"""
Prepare data for LME regression and invoke R analysis.

Step 1 (Python): Build node/edge/permuted DataFrames from CSV results,
                 z-score predictors within each question, export CSVs.
Step 2 (R):      Fit LME models via lme4::lmer(), output JSON + LaTeX tables.

Usage:
    python -m forecast_bench.lme_analysis
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from forecast_bench.analysis_causal import load_causal_results

# ── Paths ──────────────────────────────────────────────────────────────────
BASE = Path(__file__).parent.parent
CAUSAL_DIR = BASE / "outputs" / "sensitivity" / "causal"

# Neutral prompt runs (primary)
MODEL_DIRS = {
    "Llama-3.1-8B": CAUSAL_DIR / "llama_neutral",
    "Llama-3.3-70B": CAUSAL_DIR / "llama_70b_neutral",
    "DeepSeek-V3": CAUSAL_DIR / "deepseek_neutral",
    "Qwen3-235B": CAUSAL_DIR / "qwen_neutral",
    "Gemini-Flash-Lite": CAUSAL_DIR / "gemini_fl_neutral",
    "GPT-OSS-120B": CAUSAL_DIR / "gpt_oss_neutral",
    "Qwen3-32B": CAUSAL_DIR / "qwen_32b_neutral",
}

# Neutral prompt runs (used by coherence builders that join against ratings JSONs)
MODEL_DIRS_NEUTRAL = {
    "Llama-3.1-8B": CAUSAL_DIR / "llama_neutral",
    "Llama-3.3-70B": CAUSAL_DIR / "llama_70b_neutral",
    "DeepSeek-V3": CAUSAL_DIR / "deepseek_neutral",
    "Qwen3-235B": CAUSAL_DIR / "qwen_neutral",
    "Gemini-Flash-Lite": CAUSAL_DIR / "gemini_fl_neutral",
    "GPT-OSS-120B": CAUSAL_DIR / "gpt_oss_neutral",
    "Qwen3-32B": CAUSAL_DIR / "qwen_32b_neutral",
}

PERMUTED_DIR = CAUSAL_DIR / "gpt_oss_permuted"


# ═══════════════════════════════════════════════════════════════════════════
# DATA LOADING & PREP
# ═══════════════════════════════════════════════════════════════════════════

def _load_model_rows(model_name: str, model_dir: Path) -> list[dict]:
    """Load CSV rows for a model, tagging each row with the model name."""
    csv_path = model_dir / "sensitivity_results.csv"
    if not csv_path.exists():
        print(f"  [SKIP] {model_name}: no CSV at {csv_path}")
        return []
    rows = load_causal_results(csv_path)
    for r in rows:
        r["model"] = model_name
    return rows


def build_node_dataframe(model_dirs: dict[str, Path] | None = None) -> pd.DataFrame:
    """Build DataFrame for Model A: node probes across all models.

    Filters to successful node probes with valid importance and shift.
    Z-scores target_importance within each question_id.
    """
    if model_dirs is None:
        model_dirs = MODEL_DIRS

    all_rows = []
    for name, d in model_dirs.items():
        rows = _load_model_rows(name, d)
        for r in rows:
            if (r.get("success")
                    and r.get("absolute_shift") is not None
                    and r.get("target_importance") is not None
                    and r.get("probe_category") == "node"):
                # Determine probe direction
                pt = r.get("probe_type", "")
                if "negate" in pt:
                    direction = "negate"
                elif "strengthen" in pt:
                    direction = "strengthen"
                else:
                    direction = "other"
                all_rows.append({
                    "question_id": r["question_id"],
                    "model": r["model"],
                    "absolute_shift": r["absolute_shift"],
                    "initial_probability": r.get("initial_probability", 0.5),
                    "updated_probability": r.get("updated_probability", 0.5),
                    "target_importance": r["target_importance"],
                    "probe_type": r.get("probe_type", "unknown"),
                    "direction": direction,
                })

    df = pd.DataFrame(all_rows)
    if df.empty:
        return df

    # Z-score importance within each question
    df["importance_z"] = df.groupby("question_id")["target_importance"].transform(
        lambda x: (x - x.mean()) / x.std() if x.std() > 0 else 0.0
    )

    # Drop questions with no variance in importance (z=0 for all)
    question_var = df.groupby("question_id")["importance_z"].transform("std")
    df = df[question_var > 0].copy()

    # Compute log-odds shift
    import numpy as np
    eps = 1e-4  # avoid log(0)
    p0 = df["initial_probability"].clip(eps, 1 - eps)
    p1 = df["updated_probability"].clip(eps, 1 - eps)
    df["logit_shift"] = np.log(p1 / (1 - p1)) - np.log(p0 / (1 - p0))
    df["abs_logit_shift"] = df["logit_shift"].abs()

    print(f"  Node DataFrame: {len(df)} rows, {df['question_id'].nunique()} questions, "
          f"{df['model'].nunique()} models")
    return df


def build_path_relevance_dataframe(model_dirs: dict[str, Path] | None = None) -> pd.DataFrame:
    """Build DataFrame for Model B: node probes with path relevance predictor.

    Path relevance = fraction of source->outcome shortest paths passing through
    the node. Extracted from per-question JSONs (node_metrics.path_relevance).
    Z-scores within each question_id.
    """
    from forecast_bench.analysis_full import load_question_jsons

    if model_dirs is None:
        model_dirs = MODEL_DIRS

    all_rows = []
    for name, d in model_dirs.items():
        q_data = load_question_jsons(d)
        for qid, qinfo in q_data.items():
            na = qinfo.get("network_analysis", {})
            node_metrics = {m["node_id"]: m for m in na.get("node_metrics", [])}
            for pr in qinfo.get("probe_results", []):
                if not pr.get("success") or pr.get("absolute_shift") is None:
                    continue
                if pr.get("target_type") != "node":
                    continue
                tid = pr.get("target_id", "")
                pr_val = node_metrics.get(tid, {}).get("path_relevance")
                if pr_val is None:
                    continue
                pt = pr.get("probe_type", "")
                if "negate" in pt:
                    direction = "negate"
                elif "strengthen" in pt:
                    direction = "strengthen"
                else:
                    direction = "other"
                all_rows.append({
                    "question_id": qid,
                    "model": name,
                    "absolute_shift": pr["absolute_shift"],
                    "initial_probability": pr.get("initial_probability",
                                                   qinfo.get("initial_probability", 0.5)),
                    "updated_probability": pr.get("updated_probability", 0.5),
                    "path_relevance": pr_val,
                    "probe_type": pt,
                    "direction": direction,
                })

    df = pd.DataFrame(all_rows)
    if df.empty:
        return df

    df["path_relevance_z"] = df.groupby("question_id")["path_relevance"].transform(
        lambda x: (x - x.mean()) / x.std() if x.std() > 0 else 0.0
    )
    question_var = df.groupby("question_id")["path_relevance_z"].transform("std")
    df = df[question_var > 0].copy()

    # Compute log-odds shift
    import numpy as np
    eps = 1e-4
    p0 = df["initial_probability"].clip(eps, 1 - eps)
    p1 = df["updated_probability"].clip(eps, 1 - eps)
    df["logit_shift"] = np.log(p1 / (1 - p1)) - np.log(p0 / (1 - p0))
    df["abs_logit_shift"] = df["logit_shift"].abs()

    print(f"  Path Relevance DataFrame: {len(df)} rows, {df['question_id'].nunique()} questions, "
          f"{df['model'].nunique()} models")
    return df


def build_permuted_dataframe() -> pd.DataFrame:
    """Build node-probe DataFrame from edge-permuted data (GPT-OSS only)."""
    return build_node_dataframe({"GPT-OSS-Permuted": PERMUTED_DIR})


def build_direct_indirect_dataframe(model_dirs: dict[str, Path] | None = None) -> pd.DataFrame:
    """Build DataFrame for direct vs indirect cause analysis.

    Classifies node probes as 'direct' (has edge to outcome) or 'indirect'.
    Includes betweenness for controlling.
    """
    import json
    import networkx as nx
    from forecast_bench.analysis_full import load_question_jsons

    if model_dirs is None:
        model_dirs = MODEL_DIRS

    all_rows = []
    for name, d in model_dirs.items():
        q_data = load_question_jsons(d)
        for qid, qinfo in q_data.items():
            nodes = qinfo.get("nodes", [])
            edges = qinfo.get("edges", [])
            na = qinfo.get("network_analysis", {})
            outcome = na.get("outcome_node")
            if not outcome:
                continue

            G = nx.DiGraph()
            for n in nodes:
                G.add_node(n["id"])
            for e in edges:
                if e.get("from") in G and e.get("to") in G:
                    G.add_edge(e["from"], e["to"])

            direct_nodes = set(G.predecessors(outcome)) if outcome in G else set()
            node_metrics = {m["node_id"]: m for m in na.get("node_metrics", [])}

            for pr in qinfo.get("probe_results", []):
                if not pr.get("success") or pr.get("absolute_shift") is None:
                    continue
                if pr.get("target_type") != "node":
                    continue
                tid = pr.get("target_id", "")
                if tid == outcome or tid not in node_metrics:
                    continue

                betw = node_metrics[tid].get("betweenness", 0)
                all_rows.append({
                    "question_id": qid,
                    "model": name,
                    "absolute_shift": pr["absolute_shift"],
                    "betweenness": betw,
                    "is_direct": 1 if tid in direct_nodes else 0,
                })

    df = pd.DataFrame(all_rows)
    if df.empty:
        return df

    df["betweenness_z"] = df.groupby("question_id")["betweenness"].transform(
        lambda x: (x - x.mean()) / x.std() if x.std() > 0 else 0.0
    )

    print(f"  Direct/Indirect DataFrame: {len(df)} rows, "
          f"{(df['is_direct']==1).sum()} direct, {(df['is_direct']==0).sum()} indirect, "
          f"{df['question_id'].nunique()} questions, {df['model'].nunique()} models")
    return df


def build_extended_node_dataframe(model_dirs: dict[str, Path] | None = None) -> pd.DataFrame:
    """Build DataFrame with extended node-level path metrics.

    Adds: causal_depth (shortest path to outcome), n_paths (all simple paths
    to outcome), is_direct (parent of outcome), degree.
    """
    import networkx as nx
    from forecast_bench.analysis_full import load_question_jsons

    if model_dirs is None:
        model_dirs = MODEL_DIRS

    all_rows = []
    for name, d in model_dirs.items():
        q_data = load_question_jsons(d)
        for qid, qinfo in q_data.items():
            nodes = qinfo.get("nodes", [])
            edges = qinfo.get("edges", [])
            na = qinfo.get("network_analysis", {})
            outcome = na.get("outcome_node")
            if not outcome:
                continue

            G = nx.DiGraph()
            for n in nodes:
                G.add_node(n["id"])
            for e in edges:
                if e.get("from") in G and e.get("to") in G:
                    G.add_edge(e["from"], e["to"])

            node_metrics = {m["node_id"]: m for m in na.get("node_metrics", [])}
            direct_nodes = set(G.predecessors(outcome)) if outcome in G else set()

            for pr in qinfo.get("probe_results", []):
                if not pr.get("success") or pr.get("absolute_shift") is None:
                    continue
                if pr.get("target_type") != "node":
                    continue
                tid = pr.get("target_id", "")
                if tid == outcome or tid not in G:
                    continue

                nm = node_metrics.get(tid, {})

                # Causal depth
                try:
                    depth = nx.shortest_path_length(G, tid, outcome)
                except nx.NetworkXNoPath:
                    depth = G.number_of_nodes()  # unreachable

                # Number of simple paths to outcome
                try:
                    n_paths = len(list(nx.all_simple_paths(G, tid, outcome)))
                except:
                    n_paths = 0

                all_rows.append({
                    "question_id": qid,
                    "model": name,
                    "absolute_shift": pr["absolute_shift"],
                    "betweenness": nm.get("betweenness", 0),
                    "path_relevance": nm.get("path_relevance", 0),
                    "causal_depth": depth,
                    "n_paths_to_outcome": n_paths,
                    "is_direct": 1 if tid in direct_nodes else 0,
                    "degree": G.degree(tid),
                })

    df = pd.DataFrame(all_rows)
    if df.empty:
        return df

    # Z-score continuous predictors within each question
    for col in ["betweenness", "path_relevance", "causal_depth", "n_paths_to_outcome", "degree"]:
        df[f"{col}_z"] = df.groupby("question_id")[col].transform(
            lambda x: (x - x.mean()) / x.std() if x.std() > 0 else 0.0
        )

    print(f"  Extended Node DataFrame: {len(df)} rows, {df['question_id'].nunique()} questions, "
          f"{df['model'].nunique()} models")
    return df


def build_extended_edge_dataframe(model_dirs: dict[str, Path] | None = None) -> pd.DataFrame:
    """Build DataFrame with extended edge-level path metrics.

    Adds: on_any_shortest_path (binary), shortest_path_count (how many
    source->outcome shortest paths use this edge), is_direct_to_outcome.
    """
    import networkx as nx
    from forecast_bench.analysis_full import load_question_jsons

    if model_dirs is None:
        model_dirs = MODEL_DIRS

    all_rows = []
    for name, d in model_dirs.items():
        q_data = load_question_jsons(d)
        for qid, qinfo in q_data.items():
            nodes = qinfo.get("nodes", [])
            edges = qinfo.get("edges", [])
            na = qinfo.get("network_analysis", {})
            outcome = na.get("outcome_node")
            if not outcome:
                continue

            G = nx.DiGraph()
            for n in nodes:
                G.add_node(n["id"])
            for e in edges:
                if e.get("from") in G and e.get("to") in G:
                    G.add_edge(e["from"], e["to"])

            edge_metrics = {}
            for em in na.get("edge_metrics", []):
                key = (em.get("source"), em.get("target"))
                edge_metrics[key] = em

            # Precompute: for each edge, count shortest paths using it
            factor_ids = [n["id"] for n in nodes if n.get("role") != "outcome"]
            edge_sp_counts = {}
            edge_on_any_sp = {}
            for e in G.edges():
                edge_sp_counts[e] = 0
                edge_on_any_sp[e] = False

            for src_node in factor_ids:
                if src_node == outcome or src_node not in G:
                    continue
                try:
                    for path in nx.all_shortest_paths(G, src_node, outcome):
                        for i in range(len(path) - 1):
                            e = (path[i], path[i + 1])
                            if e in edge_sp_counts:
                                edge_sp_counts[e] += 1
                                edge_on_any_sp[e] = True
                except nx.NetworkXNoPath:
                    pass

            for pr in qinfo.get("probe_results", []):
                if not pr.get("success") or pr.get("absolute_shift") is None:
                    continue
                if pr.get("target_type") != "edge":
                    continue

                tid = pr.get("target_id", "")
                # Parse edge target_id — format varies
                parts = tid.replace("->", "→").split("→")
                if len(parts) != 2:
                    parts = tid.split("_to_")
                if len(parts) != 2:
                    continue

                src_e, tgt_e = parts[0].strip(), parts[1].strip()
                edge_key = (src_e, tgt_e)
                em = edge_metrics.get(edge_key, {})

                all_rows.append({
                    "question_id": qid,
                    "model": name,
                    "absolute_shift": pr["absolute_shift"],
                    "edge_betweenness": em.get("edge_betweenness", 0),
                    "on_shortest_path": 1 if edge_on_any_sp.get(edge_key, False) else 0,
                    "sp_count": edge_sp_counts.get(edge_key, 0),
                    "is_direct_to_outcome": 1 if tgt_e == outcome else 0,
                })

    df = pd.DataFrame(all_rows)
    if df.empty:
        return df

    for col in ["edge_betweenness", "sp_count"]:
        df[f"{col}_z"] = df.groupby("question_id")[col].transform(
            lambda x: (x - x.mean()) / x.std() if x.std() > 0 else 0.0
        )

    print(f"  Extended Edge DataFrame: {len(df)} rows, "
          f"on_sp={df['on_shortest_path'].sum()}, direct_to_outcome={df['is_direct_to_outcome'].sum()}, "
          f"{df['question_id'].nunique()} questions, {df['model'].nunique()} models")
    return df


def build_edge_betweenness_dataframe(model_dirs: dict[str, Path] | None = None) -> pd.DataFrame:
    """Build DataFrame for edge probes with edge_betweenness as predictor.

    Uses target_importance (= edge_betweenness) from the CSV for edge probes.
    Z-scores within each question_id.
    """
    if model_dirs is None:
        model_dirs = MODEL_DIRS

    all_rows = []
    for name, d in model_dirs.items():
        rows = _load_model_rows(name, d)
        for r in rows:
            if (r.get("success")
                    and r.get("absolute_shift") is not None
                    and r.get("target_importance") is not None
                    and r.get("probe_category") == "edge"):
                all_rows.append({
                    "question_id": r["question_id"],
                    "model": r["model"],
                    "absolute_shift": r["absolute_shift"],
                    "edge_betweenness": r["target_importance"],
                    "probe_type": r.get("probe_type", "unknown"),
                })

    df = pd.DataFrame(all_rows)
    if df.empty:
        return df

    df["edge_betweenness_z"] = df.groupby("question_id")["edge_betweenness"].transform(
        lambda x: (x - x.mean()) / x.std() if x.std() > 0 else 0.0
    )
    question_var = df.groupby("question_id")["edge_betweenness_z"].transform("std")
    df = df[question_var > 0].copy()

    print(f"  Edge Betweenness DataFrame: {len(df)} rows, {df['question_id'].nunique()} questions, "
          f"{df['model'].nunique()} models")
    return df


def build_ablation_dataframe() -> pd.DataFrame:
    """Build DataFrame from structural ablation data (70B only).

    Each row is one node/edge removal with betweenness, path_relevance,
    and the resulting |shift|. Z-scores betweenness within each question.
    """
    import json

    ablation_dir = CAUSAL_DIR / "gpt_oss_ablation" / "question_results"
    if not ablation_dir.exists():
        print("  [SKIP] Ablation: no data directory")
        return pd.DataFrame()

    all_rows = []
    for f in sorted(ablation_dir.glob("q_*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        qid = data["question_id"]
        for r in data.get("ablation_results", []):
            if not r.get("success") or r.get("absolute_shift") is None:
                continue
            betw = r.get("betweenness")
            if betw is None:
                continue
            abl_type = r.get("ablation_type", "")
            row = {
                "question_id": qid,
                "model": "Llama-3.3-70B",
                "absolute_shift": r["absolute_shift"],
                "betweenness": betw,
                "ablation_type": abl_type,
            }
            if abl_type == "node":
                row["path_relevance"] = r.get("path_relevance", 0.0)
            elif abl_type == "edge":
                row["on_critical_path"] = 1 if r.get("on_critical_path") else 0
                row["path_relevance"] = 0.0  # not available for edges
            else:
                continue
            all_rows.append(row)

    df = pd.DataFrame(all_rows)
    if df.empty:
        return df

    df["betweenness_z"] = df.groupby("question_id")["betweenness"].transform(
        lambda x: (x - x.mean()) / x.std() if x.std() > 0 else 0.0
    )
    df["path_relevance_z"] = df.groupby("question_id")["path_relevance"].transform(
        lambda x: (x - x.mean()) / x.std() if x.std() > 0 else 0.0
    )

    # Drop questions with no variance in betweenness
    qvar = df.groupby("question_id")["betweenness_z"].transform("std")
    df = df[qvar > 0].copy()

    n_node = (df["ablation_type"] == "node").sum()
    n_edge = (df["ablation_type"] == "edge").sum()
    print(f"  Ablation DataFrame: {len(df)} rows ({n_node} node, {n_edge} edge), "
          f"{df['question_id'].nunique()} questions")
    return df


def build_factor_ranking_dataframe(model_dirs: dict[str, Path] | None = None) -> pd.DataFrame:
    """Build DataFrame joining factor rankings with probe sensitivity data.

    For each node probe, looks up the stated rank of the target node from
    the factor ranking experiment. Enables LME: |Δlogit| ~ rank_z + betweenness_z.
    """
    import json
    import numpy as np
    from forecast_bench.analysis_full import load_question_jsons

    if model_dirs is None:
        model_dirs = MODEL_DIRS

    # Map model display names to ranking directories
    RANKING_DIR_MAP = {
        "Llama-3.1-8B": "llama_neutral_factor_ranking",
        "Llama-3.3-70B": "llama_70b_neutral_factor_ranking",
        "DeepSeek-V3": "deepseek_neutral_factor_ranking",
        "Qwen3-235B": "qwen_neutral_factor_ranking",
        "Gemini-Flash-Lite": "gemini_fl_neutral_factor_ranking",
        "GPT-OSS-120B": "gpt_oss_neutral_factor_ranking",
        "Qwen3-32B": "qwen_32b_neutral_factor_ranking",
    }

    all_rows = []
    for name, d in model_dirs.items():
        ranking_dir = CAUSAL_DIR / RANKING_DIR_MAP.get(name, "") / "question_results"
        if not ranking_dir.exists():
            print(f"  [SKIP] {name}: no ranking data at {ranking_dir}")
            continue

        # Load ranking data: {qid: {node_id: rank}}
        rank_lookup = {}
        for rf in ranking_dir.glob("q_*.json"):
            rdata = json.loads(rf.read_text(encoding="utf-8"))
            qid = rdata["question_id"]
            rank_lookup[qid] = {r["id"]: r["rank"] for r in rdata["ranking"]}

        # Load probe data
        q_data = load_question_jsons(d)
        for qid, qinfo in q_data.items():
            if qid not in rank_lookup:
                continue
            qranks = rank_lookup[qid]
            na = qinfo.get("network_analysis", {})
            node_metrics = {m["node_id"]: m for m in na.get("node_metrics", [])}

            for pr in qinfo.get("probe_results", []):
                if not pr.get("success") or pr.get("absolute_shift") is None:
                    continue
                if pr.get("target_type") != "node":
                    continue
                tid = pr.get("target_id", "")
                if tid not in qranks or tid not in node_metrics:
                    continue

                nm = node_metrics[tid]
                pt = pr.get("probe_type", "")
                if "negate" in pt:
                    direction = "negate"
                elif "strengthen" in pt:
                    direction = "strengthen"
                else:
                    direction = "other"

                all_rows.append({
                    "question_id": qid,
                    "model": name,
                    "absolute_shift": pr["absolute_shift"],
                    "initial_probability": pr.get("initial_probability",
                                                   qinfo.get("initial_probability", 0.5)),
                    "updated_probability": pr.get("updated_probability", 0.5),
                    "stated_rank": qranks[tid],
                    "betweenness": nm.get("betweenness", 0.0),
                    "path_relevance": nm.get("path_relevance", 0.0),
                    "probe_type": pt,
                    "direction": direction,
                })

    df = pd.DataFrame(all_rows)
    if df.empty:
        return df

    # Z-score within each question
    for col in ["stated_rank", "betweenness", "path_relevance"]:
        df[f"{col}_z"] = df.groupby("question_id")[col].transform(
            lambda x: (x - x.mean()) / x.std() if x.std() > 0 else 0.0
        )

    # Drop questions with no variance in rank
    qvar = df.groupby("question_id")["stated_rank_z"].transform("std")
    df = df[qvar > 0].copy()

    # Compute log-odds shift
    eps = 1e-4
    p0 = df["initial_probability"].clip(eps, 1 - eps)
    p1 = df["updated_probability"].clip(eps, 1 - eps)
    df["logit_shift"] = np.log(p1 / (1 - p1)) - np.log(p0 / (1 - p0))
    df["abs_logit_shift"] = df["logit_shift"].abs()

    print(f"  Factor Ranking DataFrame: {len(df)} rows, {df['question_id'].nunique()} questions, "
          f"{df['model'].nunique()} models")
    return df


def build_network_size_dataframes() -> dict[str, pd.DataFrame]:
    """Build node DataFrames for each network size condition (GPT-OSS)."""
    size_dirs = {
        "Medium (4-8)": CAUSAL_DIR / "gpt_oss_neutral",
        "Large (6-10)": CAUSAL_DIR / "gpt_oss_6_10",
        "XL (12-16)": CAUSAL_DIR / "gpt_oss_12_16",
    }
    results = {}
    for label, d in size_dirs.items():
        df = build_node_dataframe({"GPT-OSS-120B": d})
        if not df.empty:
            df["network_size"] = label
            results[label] = df
    return results


def build_original_testbed_dataframe(df_node: pd.DataFrame) -> pd.DataFrame:
    """Extract GPT-OSS rows from the full node DataFrame (for permutation comparison)."""
    df = df_node[df_node["model"] == "GPT-OSS-120B"].copy()
    print(f"  Original GPT-OSS: {len(df)} rows, {df['question_id'].nunique()} questions")
    return df


# ═══════════════════════════════════════════════════════════════════════════
# COHERENCE DATA BUILDERS
# ═══════════════════════════════════════════════════════════════════════════

def build_coherence_reasoning_dataframe() -> pd.DataFrame:
    """Build DataFrame for coherence: stated-impact rating (1-5) vs |logit shift|.

    Uses reasoning judge ratings (keyed to neutral prompt runs).
    """
    import json
    import numpy as np
    from forecast_bench.analysis_full import load_question_jsons

    ratings_path = CAUSAL_DIR / "reasoning_judge_ratings.json"
    if not ratings_path.exists():
        print("  [SKIP] No reasoning judge ratings")
        return pd.DataFrame()

    ratings = json.loads(ratings_path.read_text(encoding="utf-8"))
    model_key_map = {
        "Llama-3.1-8B": "llama-8b", "Llama-3.3-70B": "llama-70b",
        "DeepSeek-V3": "deepseek", "Qwen3-235B": "qwen-235b",
        "Gemini-Flash-Lite": "gemini", "GPT-OSS-120B": "gpt-oss",
        "Qwen3-32B": "qwen-32b",
    }

    all_rows = []
    for display_name, d in MODEL_DIRS_NEUTRAL.items():
        jk = model_key_map.get(display_name)
        if not jk:
            continue
        q_data = load_question_jsons(d)
        for qid, qinfo in q_data.items():
            init_p = qinfo.get("initial_probability")
            if init_p is None:
                continue
            for i, pr in enumerate(qinfo.get("probe_results", [])):
                if not pr.get("success"):
                    continue
                up = pr.get("updated_probability")
                if up is None:
                    continue
                key = f"{jk}|{qid}|{i}"
                if key not in ratings:
                    continue
                r = ratings[key].get("rating")
                if r is None or r < 1 or r > 5:
                    continue

                eps = 1e-4
                p0 = max(eps, min(1 - eps, init_p))
                p1 = max(eps, min(1 - eps, up))
                logit_shift = np.log(p1 / (1 - p1)) - np.log(p0 / (1 - p0))

                all_rows.append({
                    "question_id": qid,
                    "model": display_name,
                    "rating": int(r),
                    "abs_logit_shift": abs(logit_shift),
                })

    df = pd.DataFrame(all_rows)
    if not df.empty:
        print(f"  Coherence Reasoning DataFrame: {len(df)} rows, "
              f"{df['question_id'].nunique()} questions, {df['model'].nunique()} models")
    return df


def build_coherence_uncertainty_dataframe() -> pd.DataFrame:
    """Build DataFrame for coherence: uncertainty rating (2-4) vs |logit shift|.

    Uses uncertainty judge ratings (keyed to neutral prompt runs).
    """
    import json
    import numpy as np
    from forecast_bench.analysis_full import load_question_jsons

    ratings_path = CAUSAL_DIR / "uncertainty_judge_ratings.json"
    if not ratings_path.exists():
        print("  [SKIP] No uncertainty judge ratings")
        return pd.DataFrame()

    ratings = json.loads(ratings_path.read_text(encoding="utf-8"))
    model_key_map = {
        "Llama-3.1-8B": "llama-8b", "Llama-3.3-70B": "llama-70b",
        "DeepSeek-V3": "deepseek", "Qwen3-235B": "qwen-235b",
        "Gemini-Flash-Lite": "gemini", "GPT-OSS-120B": "gpt-oss",
        "Qwen3-32B": "qwen-32b",
    }

    all_rows = []
    for display_name, d in MODEL_DIRS_NEUTRAL.items():
        jk = model_key_map.get(display_name)
        if not jk:
            continue
        q_data = load_question_jsons(d)
        for qid, qinfo in q_data.items():
            init_p = qinfo.get("initial_probability")
            if init_p is None:
                continue
            for i, pr in enumerate(qinfo.get("probe_results", [])):
                if not pr.get("success"):
                    continue
                up = pr.get("updated_probability")
                if up is None:
                    continue
                key = f"{jk}|{qid}|{i}"
                if key not in ratings:
                    continue
                r = ratings[key].get("rating")
                if r is None or r not in (2, 3, 4):
                    continue

                eps = 1e-4
                p0 = max(eps, min(1 - eps, init_p))
                p1 = max(eps, min(1 - eps, up))
                logit_shift = np.log(p1 / (1 - p1)) - np.log(p0 / (1 - p0))

                all_rows.append({
                    "question_id": qid,
                    "model": display_name,
                    "uncertainty": int(r),
                    "uncertainty_numeric": int(r) - 2,  # 0=Confident, 1=Mixed, 2=Hedging
                    "abs_logit_shift": abs(logit_shift),
                })

    df = pd.DataFrame(all_rows)
    if not df.empty:
        print(f"  Coherence Uncertainty DataFrame: {len(df)} rows, "
              f"{df['question_id'].nunique()} questions, {df['model'].nunique()} models")
    return df


def build_coherence_bayesian_dataframe(model_dirs: dict[str, Path] | None = None) -> pd.DataFrame:
    """Build DataFrame for coherence: initial logit → signed logit shift.

    Uses neutral prompt runs (all models). A negative β indicates
    regression-toward-mean (Bayesian-coherent updating).
    """
    import numpy as np

    if model_dirs is None:
        model_dirs = MODEL_DIRS

    all_rows = []
    for name, d in model_dirs.items():
        rows = _load_model_rows(name, d)
        for r in rows:
            if not r.get("success") or r.get("updated_probability") is None:
                continue
            init_p = r.get("initial_probability")
            up = r.get("updated_probability")
            if init_p is None or up is None:
                continue

            eps = 1e-4
            p0 = max(eps, min(1 - eps, init_p))
            p1 = max(eps, min(1 - eps, up))
            logit_shift = np.log(p1 / (1 - p1)) - np.log(p0 / (1 - p0))
            initial_logit = np.log(p0 / (1 - p0))

            all_rows.append({
                "question_id": r["question_id"],
                "model": name,
                "initial_probability": init_p,
                "initial_logit": initial_logit,
                "logit_shift": logit_shift,
                "abs_logit_shift": abs(logit_shift),
            })

    df = pd.DataFrame(all_rows)
    if not df.empty:
        print(f"  Coherence Bayesian DataFrame: {len(df)} rows, "
              f"{df['question_id'].nunique()} questions, {df['model'].nunique()} models")
    return df


def build_coherence_embedding_dataframe() -> pd.DataFrame:
    """Build DataFrame for coherence: embedding similarity by probe type.

    For each probe, computes mean cosine similarity to other same-type
    probes in the same question. Probe types: structural vs control.
    """
    import json
    import numpy as np

    emb_path = CAUSAL_DIR / "reasoning_embeddings.npz"
    keys_path = CAUSAL_DIR / "reasoning_embeddings_keys.json"

    if not (emb_path.exists() and keys_path.exists()):
        print("  [SKIP] No reasoning embeddings")
        return pd.DataFrame()

    from forecast_bench.shared_utils import _EMBED_PROBE_NORMALIZE, _IMPORTANCE_TIER

    keys = json.loads(keys_path.read_text(encoding="utf-8"))
    embeddings = np.load(str(emb_path))["embeddings"]

    CONTROL_TYPES = {"irrelevant"}
    model_key_map = {
        "llama-8b": "Llama-3.1-8B", "llama-70b": "Llama-3.3-70B",
        "deepseek": "DeepSeek-V3", "qwen": "Qwen3-235B",
        "gemini": "Gemini-Flash-Lite",
    }

    # Index: (model_key, question_id) → list of (is_control, embedding_index)
    from collections import defaultdict
    model_q_index = defaultdict(list)
    for i, k in enumerate(keys):
        parts = k.split("|")
        if len(parts) < 4:
            continue
        pt = _EMBED_PROBE_NORMALIZE.get(parts[1], parts[1])
        if pt not in _IMPORTANCE_TIER:
            continue
        is_control = pt in CONTROL_TYPES
        model_q_index[(parts[3], parts[0])].append((is_control, i))

    def _cosine_sim(a, b):
        dot = np.dot(a, b)
        na, nb = np.linalg.norm(a), np.linalg.norm(b)
        return dot / (na * nb) if na > 0 and nb > 0 else 0.0

    all_rows = []
    for (mk, qid), entries in model_q_index.items():
        display_name = model_key_map.get(mk)
        if not display_name:
            continue
        ctrl_idx = [idx for is_ctrl, idx in entries if is_ctrl]
        struct_idx = [idx for is_ctrl, idx in entries if not is_ctrl]
        if len(ctrl_idx) < 2 or len(struct_idx) < 2:
            continue

        # Per-probe mean similarity to same-type probes
        for idx in struct_idx:
            others = [j for j in struct_idx if j != idx]
            sims = [_cosine_sim(embeddings[idx], embeddings[j]) for j in others]
            all_rows.append({
                "question_id": qid,
                "model": display_name,
                "is_structural": 1,
                "mean_cosine_sim": np.mean(sims),
            })
        for idx in ctrl_idx:
            others = [j for j in ctrl_idx if j != idx]
            sims = [_cosine_sim(embeddings[idx], embeddings[j]) for j in others]
            all_rows.append({
                "question_id": qid,
                "model": display_name,
                "is_structural": 0,
                "mean_cosine_sim": np.mean(sims),
            })

    df = pd.DataFrame(all_rows)
    if not df.empty:
        print(f"  Coherence Embedding DataFrame: {len(df)} rows, "
              f"{df['question_id'].nunique()} questions, {df['model'].nunique()} models")
    return df


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("LME Analysis — Data Preparation (Python) + Fitting (R)")
    print("=" * 60)

    # ── Step 1: Build DataFrames ───────────────────────────────────────
    print("\nBuilding DataFrames...")
    df_node = build_node_dataframe()
    df_path_rel = build_path_relevance_dataframe()
    df_edge_betw = build_edge_betweenness_dataframe()
    df_direct = build_direct_indirect_dataframe()
    df_ext_node = build_extended_node_dataframe()
    df_ext_edge = build_extended_edge_dataframe()
    df_permuted = build_permuted_dataframe()
    df_orig_gptoss = build_original_testbed_dataframe(df_node)
    df_ablation = build_ablation_dataframe()
    df_factor_ranking = build_factor_ranking_dataframe()
    net_size_dfs = build_network_size_dataframes()

    # ── Coherence DataFrames ──────────────────────────────────────────
    print("\nBuilding Coherence DataFrames...")
    df_coh_reasoning = build_coherence_reasoning_dataframe()
    df_coh_uncertainty = build_coherence_uncertainty_dataframe()
    df_coh_bayesian = build_coherence_bayesian_dataframe()
    df_coh_embedding = build_coherence_embedding_dataframe()

    # ── Step 2: Export CSVs for R ──────────────────────────────────────
    # Combine network size dataframes into one CSV with a size column
    if net_size_dfs:
        df_net_size = pd.concat(net_size_dfs.values(), ignore_index=True)
    else:
        df_net_size = pd.DataFrame()

    csvs = {
        "lme_node_data.csv": df_node,
        "lme_path_relevance_data.csv": df_path_rel,
        "lme_edge_betweenness_data.csv": df_edge_betw,
        "lme_permuted_data.csv": df_permuted,
        "lme_orig_gptoss_data.csv": df_orig_gptoss,
        "lme_ablation_data.csv": df_ablation,
        "lme_direct_indirect_data.csv": df_direct,
        "lme_extended_node_data.csv": df_ext_node,
        "lme_extended_edge_data.csv": df_ext_edge,
        "lme_factor_ranking_data.csv": df_factor_ranking,
        "lme_network_size_data.csv": df_net_size,
        "lme_coherence_reasoning.csv": df_coh_reasoning,
        "lme_coherence_uncertainty.csv": df_coh_uncertainty,
        "lme_coherence_bayesian.csv": df_coh_bayesian,
        "lme_coherence_embedding.csv": df_coh_embedding,
    }

    print(f"\nExported CSVs:")
    for name, df in csvs.items():
        if not df.empty:
            path = CAUSAL_DIR / name
            df.to_csv(path, index=False)
            print(f"  {path}")

    # ── Step 3: Invoke R script ────────────────────────────────────────
    r_script = Path(__file__).parent / "lme_analysis.R"
    print(f"\nRunning R analysis: {r_script}")

    result = subprocess.run(
        ["Rscript", str(r_script)],
        cwd=str(BASE),
        capture_output=True, text=True, timeout=300,
    )

    print(result.stdout)
    if result.stderr:
        # Filter out common R warnings that aren't errors
        for line in result.stderr.splitlines():
            if "Warning" in line or "package" in line or "Attaching" in line:
                continue
            print(f"  [R stderr] {line}")

    if result.returncode != 0:
        print(f"\n[ERROR] R script exited with code {result.returncode}")
        print(result.stderr)
        sys.exit(1)

    print("\nLME analysis complete.")


if __name__ == "__main__":
    main()
