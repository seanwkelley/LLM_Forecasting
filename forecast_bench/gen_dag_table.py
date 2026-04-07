#!/usr/bin/env python3
"""Generate DAG characteristics LaTeX table."""

import csv
import json
import sys
from pathlib import Path

import numpy as np
import networkx as nx

sys.path.insert(0, str(Path(__file__).parent.parent))

BASE = Path(__file__).parent.parent
CAUSAL_DIR = BASE / "outputs" / "sensitivity" / "causal"

MODELS = [
    ("Llama 3.1 8B", "llama_neutral"),
    ("Llama 3.3 70B", "llama_70b_neutral"),
    ("DeepSeek V3", "deepseek_neutral"),
    ("Qwen3 235B", "qwen_neutral"),
    ("Qwen3 32B", "qwen_32b_neutral"),
    ("Gemini FL", "gemini_fl_neutral"),
    ("GPT-OSS 120B", "gpt_oss_neutral"),
]


def main():
    lines = []
    lines.append("\\begin{table}[t]")
    lines.append("\\centering")
    lines.append("\\small")
    lines.append("\\begin{tabular}{lcccccc}")
    lines.append("\\toprule")
    lines.append("\\textbf{Model} & \\textbf{Nodes} & \\textbf{Edges} & \\textbf{Density} & \\textbf{Depth} & \\textbf{$p_0$ Mean} & \\textbf{$p_0$ SD} \\\\")
    lines.append("\\midrule")

    for name, d in MODELS:
        csv_path = CAUSAL_DIR / d / "sensitivity_results.csv"
        if not csv_path.exists():
            print(f"  [SKIP] {name}")
            continue

        rows = list(csv.DictReader(open(csv_path, encoding="utf-8")))

        seen = set()
        nodes_list, edges_list, density_list, p0_list = [], [], [], []
        for r in rows:
            qid = r["question_id"]
            if qid in seen:
                continue
            seen.add(qid)
            nodes_list.append(int(r.get("n_nodes", 0)))
            edges_list.append(int(r.get("n_edges", 0)))
            density_list.append(float(r.get("graph_density", 0)))
            p0_list.append(float(r.get("initial_probability", 0)))

        # Depth from JSONs
        q_dir = CAUSAL_DIR / d / "question_results"
        depths = []
        if q_dir.exists():
            for f in sorted(q_dir.glob("q_*.json")):
                data = json.loads(f.read_text(encoding="utf-8"))
                nodes = data.get("nodes", [])
                edges = data.get("edges", [])
                outcome = next((n["id"] for n in nodes if n.get("role") == "outcome"), None)
                if outcome:
                    G = nx.DiGraph()
                    for e in edges:
                        G.add_edge(e["from"], e["to"])
                    max_d = 0
                    for n in nodes:
                        if n.get("role") == "factor" and n["id"] in G:
                            try:
                                max_d = max(max_d, nx.shortest_path_length(G, n["id"], outcome))
                            except nx.NetworkXNoPath:
                                pass
                    depths.append(max_d)

        mean_depth = np.mean(depths) if depths else 0

        row_str = (
            f"{name} & {np.mean(nodes_list):.1f} & {np.mean(edges_list):.1f} & "
            f"{np.mean(density_list):.3f} & {mean_depth:.1f} & "
            f"{np.mean(p0_list):.2f} & {np.std(p0_list):.2f} \\\\"
        )
        lines.append(row_str)
        print(f"  {name}: {len(seen)} questions")

    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\caption{DAG characteristics by model (means across 116 questions). "
                 "Density is the ratio of edges to possible directed edges. "
                 "Depth is the longest shortest path from any factor to the outcome node. "
                 "$p_0$ is the initial probability estimate.}")
    lines.append("\\label{tab:dag_characteristics}")
    lines.append("\\end{table}")

    out = BASE / "paper" / "figures" / "dag_characteristics_table.tex"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nSaved to {out}")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
