#!/usr/bin/env python3
"""
Prepare data for LME regression and invoke R analysis.

Step 1 (Python): Build node/edge/scrambled DataFrames from CSV results,
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
    "Gemini-Flash-Lite": CAUSAL_DIR / "gemini_flash_lite_neutral",
    "GPT-OSS-120B": CAUSAL_DIR / "gpt_oss_neutral",
}

# Original prompt runs (for comparison / legacy)
MODEL_DIRS_ORIGINAL = {
    "Llama-3.1-8B": CAUSAL_DIR / "llama_one_turn",
    "Llama-3.3-70B": CAUSAL_DIR / "70b_one_turn",
    "DeepSeek-V3": CAUSAL_DIR / "deepseek_one_turn",
    "Qwen3-235B": CAUSAL_DIR / "qwen_one_turn",
    "Gemini-Flash-Lite": CAUSAL_DIR / "gemini_flash_lite_one_turn",
}

SCRAMBLED_DIR = CAUSAL_DIR / "70b_scrambled"


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
                all_rows.append({
                    "question_id": r["question_id"],
                    "model": r["model"],
                    "absolute_shift": r["absolute_shift"],
                    "target_importance": r["target_importance"],
                    "probe_type": r.get("probe_type", "unknown"),
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
                all_rows.append({
                    "question_id": qid,
                    "model": name,
                    "absolute_shift": pr["absolute_shift"],
                    "path_relevance": pr_val,
                    "probe_type": pr.get("probe_type", "unknown"),
                })

    df = pd.DataFrame(all_rows)
    if df.empty:
        return df

    df["path_relevance_z"] = df.groupby("question_id")["path_relevance"].transform(
        lambda x: (x - x.mean()) / x.std() if x.std() > 0 else 0.0
    )
    question_var = df.groupby("question_id")["path_relevance_z"].transform("std")
    df = df[question_var > 0].copy()

    print(f"  Path Relevance DataFrame: {len(df)} rows, {df['question_id'].nunique()} questions, "
          f"{df['model'].nunique()} models")
    return df


def build_scrambled_dataframe() -> pd.DataFrame:
    """Build node-probe DataFrame from scrambled-edge data (70B only)."""
    return build_node_dataframe({"Llama-3.3-70B-Scrambled": SCRAMBLED_DIR})


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

    ablation_dir = CAUSAL_DIR / "70b_ablation" / "question_results"
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


def build_network_size_dataframes() -> dict[str, pd.DataFrame]:
    """Build node DataFrames for each network size condition (70B only)."""
    size_dirs = {
        "Small (3-5)": CAUSAL_DIR / "70b_one_turn_small",
        "Medium (4-8)": CAUSAL_DIR / "70b_one_turn",
        "Large (6-10)": CAUSAL_DIR / "70b_one_turn_large",
        "XL (12-16)": CAUSAL_DIR / "70b_one_turn_xl",
    }
    results = {}
    for label, d in size_dirs.items():
        df = build_node_dataframe({f"Llama-3.3-70B": d})
        if not df.empty:
            df["network_size"] = label
            results[label] = df
    return results


def build_original_70b_dataframe(df_node: pd.DataFrame) -> pd.DataFrame:
    """Extract original 70B rows from the full node DataFrame."""
    df_70b = df_node[df_node["model"] == "Llama-3.3-70B"].copy()
    print(f"  Original 70B: {len(df_70b)} rows, {df_70b['question_id'].nunique()} questions")
    return df_70b


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
    df_scrambled = build_scrambled_dataframe()
    df_orig_70b = build_original_70b_dataframe(df_node)
    df_ablation = build_ablation_dataframe()
    net_size_dfs = build_network_size_dataframes()

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
        "lme_scrambled_data.csv": df_scrambled,
        "lme_original_70b_data.csv": df_orig_70b,
        "lme_ablation_data.csv": df_ablation,
        "lme_direct_indirect_data.csv": df_direct,
        "lme_extended_node_data.csv": df_ext_node,
        "lme_extended_edge_data.csv": df_ext_edge,
        "lme_network_size_data.csv": df_net_size,
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
