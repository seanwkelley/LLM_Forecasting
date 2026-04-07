"""Generate cross-model comparison tables as ICML/AAAI-style images.

Booktabs aesthetic: no vertical rules, heavy top/bottom rules, thin midrule,
serif font (Times), white background.
"""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "DejaVu Serif"],
    "mathtext.fontset": "dejavuserif",
    "figure.dpi": 300,
})

BASE = Path(__file__).parent.parent
OUT = BASE / "paper" / "figures"


def _booktabs_table(ax, col_headers, row_labels, cell_text, title=None,
                    bold_cols=None, fontsize=10, row_height=1.7, col_widths=None):
    """Render an ICML/AAAI booktabs-style table.

    - No vertical rules
    - Heavy top/bottom rules, thin midrule under header
    - White background, no cell shading
    - Serif font throughout
    """
    ax.set_axis_off()

    n_rows = len(row_labels) if row_labels else len(cell_text)
    n_cols = len(col_headers)
    bold_cols = bold_cols or set()

    tbl_kwargs = dict(
        cellText=cell_text,
        colLabels=col_headers,
        cellLoc="center",
        loc="center",
    )
    if row_labels:
        tbl_kwargs["rowLabels"] = row_labels
        tbl_kwargs["rowLoc"] = "left"

    table = ax.table(**tbl_kwargs)

    table.auto_set_font_size(False)
    table.set_fontsize(fontsize)
    table.scale(1.0, row_height)

    if col_widths:
        for j in range(n_cols):
            for i in range(n_rows + 1):
                table[i, j].set_width(col_widths[j])

    # --- Strip everything: white bg, no edges ---
    for key, cell in table.get_celld().items():
        cell.set_edgecolor("white")
        cell.set_linewidth(0)
        cell.set_facecolor("white")
        cell.set_text_props(fontsize=fontsize)

    # --- Header row: bold, with midrule below ---
    for j in range(n_cols):
        cell = table[0, j]
        cell.set_text_props(fontweight="bold", fontsize=fontsize)
        cell.set_edgecolor("black")
        cell.set_linewidth(0.8)
        cell.visible_edges = "TB"

    # --- Row labels: bold, left-aligned ---
    if row_labels:
        for i in range(n_rows):
            cell = table[i + 1, -1]
            cell.set_text_props(fontweight="bold", fontsize=fontsize)

    # --- Bottom rule on last data row ---
    for j in range(n_cols):
        cell = table[n_rows, j]
        cell.set_edgecolor("black")
        cell.set_linewidth(0.8)
        cell.visible_edges = "B"
    # Row label of last row
    if (n_rows, -1) in table.get_celld():
        cell = table[n_rows, -1]
        cell.set_edgecolor("black")
        cell.set_linewidth(0.8)
        cell.visible_edges = "B"

    # --- Bold specific columns ---
    for j in bold_cols:
        for i in range(1, n_rows + 1):
            cell = table[i, j]
            cell.set_text_props(fontweight="bold", fontsize=fontsize)

    # --- Top rule: heavier than midrule ---
    # Header cells already show TB edges at 0.8; make top edge heavier
    # by overlaying a second set of edges
    for j in range(n_cols):
        cell = table[0, j]
        cell.set_linewidth(1.2)
        cell.visible_edges = "TB"

    # Title
    if title:
        ax.set_title(title, fontsize=fontsize + 2, fontweight="bold", pad=18,
                     fontstyle="normal")


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    # ══════════════════════════════════════════════════════════════════════
    # Table 1: Cross-model DAG agreement with permutation tests
    # ══════════════════════════════════════════════════════════════════════
    _generate_permutation_table()

    # ══════════════════════════════════════════════════════════════════════
    # Table 2: Probe type examples (methods figure)
    # ══════════════════════════════════════════════════════════════════════
    _generate_probe_examples_table()

    # ══════════════════════════════════════════════════════════════════════
    # Table 3: Baseline vs Superforecasting prompt comparison
    # ══════════════════════════════════════════════════════════════════════
    _generate_prompt_comparison_table()


def _generate_permutation_table():
    """Compute pairwise DAG agreement metrics with permutation tests and render table."""
    from forecast_bench.analysis_full import load_question_jsons
    from forecast_bench.analyze_superforecasting_dag import spectral_distance

    CAUSAL = BASE / "outputs" / "sensitivity" / "causal"
    MODEL_DIRS = {
        "Llama-3.1-8B":  CAUSAL / "llama_neutral",
        "Llama-3.3-70B": CAUSAL / "llama_70b_neutral",
        "DeepSeek-V3":   CAUSAL / "deepseek_neutral",
        "Qwen3-235B":    CAUSAL / "qwen_neutral",
        "Gemini-Flash-Lite": CAUSAL / "gemini_fl_neutral",
        "GPT-OSS-120B":  CAUSAL / "gpt_oss_neutral",
        "Qwen3-32B":     CAUSAL / "qwen_32b_neutral",
    }

    def jaccard(a, b):
        if not a and not b:
            return 1.0
        union = len(a | b)
        return len(a & b) / union if union > 0 else 0.0

    # Load question JSONs per model
    q_data = {}
    for name, d in MODEL_DIRS.items():
        q_data[name] = load_question_jsons(d)
        print(f"  Loaded {name}: {len(q_data[name])} questions")

    model_names = ["Llama-3.1-8B", "Llama-3.3-70B", "DeepSeek-V3", "Qwen3-235B", "Gemini-Flash-Lite", "GPT-OSS-120B"]
    N_PERM = 5000
    rng = np.random.default_rng(42)

    pair_labels = []
    pair_short = []
    cell_rows = []

    short_names = {
        "Llama-3.1-8B": "Llama-8B", "Llama-3.3-70B": "Llama-70B",
        "DeepSeek-V3": "DeepSeek-V3", "Qwen3-235B": "Qwen3-235B",
        "Gemini-Flash-Lite": "Gemini-FL",
    }

    for i, m1 in enumerate(model_names):
        for m2 in model_names[i + 1:]:
            qd1, qd2 = q_data[m1], q_data[m2]
            shared = sorted(set(qd1.keys()) & set(qd2.keys()))
            n_sh = len(shared)

            # Observed metrics
            node_jaccards, edge_jaccards, spec_dists = [], [], []
            nodes_list1, nodes_list2, edges_list1, edges_list2 = [], [], [], []

            for qid in shared:
                n1 = {n["id"] for n in qd1[qid].get("nodes", [])}
                n2 = {n["id"] for n in qd2[qid].get("nodes", [])}
                e1 = {(e["from"], e["to"]) for e in qd1[qid].get("edges", [])}
                e2 = {(e["from"], e["to"]) for e in qd2[qid].get("edges", [])}

                node_jaccards.append(jaccard(n1, n2))
                edge_jaccards.append(jaccard(e1, e2))
                spec_dists.append(spectral_distance(e1, n1, e2, n2))

                nodes_list1.append(n1); nodes_list2.append(n2)
                edges_list1.append(e1); edges_list2.append(e2)

            obs_nj = np.mean(node_jaccards)
            obs_ej = np.mean(edge_jaccards)
            obs_sd = np.mean(spec_dists)

            # Permutation null: shuffle question pairings
            perm_nj = np.zeros(N_PERM)
            perm_ej = np.zeros(N_PERM)
            perm_sd = np.zeros(N_PERM)

            for p in range(N_PERM):
                pidx = rng.permutation(n_sh)
                pnj, pej, psd = [], [], []
                for k in range(n_sh):
                    j = pidx[k]
                    pnj.append(jaccard(nodes_list1[k], nodes_list2[j]))
                    pej.append(jaccard(edges_list1[k], edges_list2[j]))
                    psd.append(spectral_distance(edges_list1[k], nodes_list1[k],
                                                 edges_list2[j], nodes_list2[j]))
                perm_nj[p] = np.mean(pnj)
                perm_ej[p] = np.mean(pej)
                perm_sd[p] = np.mean(psd)

            # Two-sided p-values
            p_nj = 2 * min(np.mean(perm_nj >= obs_nj), np.mean(perm_nj <= obs_nj))
            p_ej = 2 * min(np.mean(perm_ej >= obs_ej), np.mean(perm_ej <= obs_ej))
            p_sd = 2 * min(np.mean(perm_sd >= obs_sd), np.mean(perm_sd <= obs_sd))

            label = f"{short_names[m1]} vs {short_names[m2]}"
            pair_labels.append(label)

            def _fmt(val, p):
                star = ""
                if p < 0.001:
                    star = "***"
                elif p < 0.01:
                    star = "**"
                elif p < 0.05:
                    star = "*"
                return f"{val:.3f}{star}"

            cell_rows.append([
                _fmt(obs_nj, p_nj),
                _fmt(obs_ej, p_ej),
                _fmt(obs_sd, p_sd),
            ])

            print(f"  {label}: NJ={obs_nj:.3f} (p={p_nj:.4f}), "
                  f"EJ={obs_ej:.3f} (p={p_ej:.4f}), "
                  f"SD={obs_sd:.3f} (p={p_sd:.4f})")

    # Include model pair as first data column (not row label) so it gets a header
    col_headers = ["Model Pair", "Node\nJaccard", "Edge\nJaccard", "Spectral\nDistance"]
    full_rows = []
    for label, row in zip(pair_labels, cell_rows):
        full_rows.append([label] + row)

    fig, ax = plt.subplots(figsize=(11, 5.0))
    fig.patch.set_facecolor("white")
    _booktabs_table(ax, col_headers, None, full_rows, bold_cols={0},
                    title="Cross-Model DAG Agreement (Permutation Test, 5,000 permutations)")

    # Add significance legend below table
    ax.text(0.5, -0.02,
            "* p < .05   ** p < .01   *** p < .001  (two-sided permutation test)",
            transform=ax.transAxes, ha="center", va="top",
            fontsize=9, fontstyle="italic", color="#555555")

    plt.tight_layout()
    for ext in ["png", "pdf"]:
        fig.savefig(str(OUT / f"permutation_test_table.{ext}"),
                    dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("Saved permutation_test_table")


def _generate_probe_examples_table():
    """Render a methods table showing one example per probe type with updating."""
    import pandas as pd

    causal_dir = BASE / "outputs" / "sensitivity" / "causal" / "gpt_oss_neutral"
    df = pd.read_csv(causal_dir / "sensitivity_results.csv")

    # Use Cynthia Erivo question — has all 14 probe types with consistent p0
    qdf = df[df["question_text"].str.contains("Cynthia Erivo", na=False)]
    init_p = qdf["initial_probability"].iloc[0]

    type_order = [
        ("node_negate_high", "Negate node (high imp.)"),
        ("node_negate_medium", "Negate node (med imp.)"),
        ("node_negate_low", "Negate node (low imp.)"),
        ("node_strengthen", "Strengthen node (high imp.)"),
        ("node_strengthen_medium", "Strengthen node (med imp.)"),
        ("node_strengthen_low", "Strengthen node (low imp.)"),
        ("edge_negate_critical", "Negate edge (shortest-path)"),
        ("edge_negate_peripheral", "Negate edge (peripheral)"),
        ("edge_strengthen_critical", "Strengthen edge (shortest-path)"),
        ("edge_strengthen_peripheral", "Strengthen edge (peripheral)"),
        ("edge_reverse", "Reverse edge"),
        ("edge_spurious", "Spurious edge"),
        ("missing_node", "Missing node"),
        ("irrelevant", "Control (irrelevant)"),
    ]

    # Curated short summaries of example probes
    probe_descriptions = {
        "node_negate_high": "\"Pre-award hype often leads\nto voter fatigue...\"",
        "node_negate_medium": "\"Several strong Best Actress\ncontenders have recently\nwithdrawn...\"",
        "node_negate_low": "\"Academy voters often prioritize\nnewcomers over repeat nominees...\"",
        "node_strengthen": "\"Renowned critic publishes a\nglowing review of Erivo's\nperformance...\"",
        "node_strengthen_medium": "\"Emma Stone, a highly acclaimed\nactress, will also be competing\nfor the award...\"",
        "node_strengthen_low": "\"Erivo has been nominated for\nseveral prestigious pre-Oscar\nawards...\"",
        "edge_negate_critical": "\"The Academy often prioritizes\nperformances that are not\nnecessarily popular...\"",
        "edge_negate_peripheral": "\"Academy voters often make\ndecisions based on individual\nperformances, not reviews...\"",
        "edge_strengthen_critical": "\"Erivo's powerful stage\nperformance has further elevated\nher Oscar narrative...\"",
        "edge_strengthen_peripheral": "\"Academy voters report being\nheavily influenced by critical\nconsensus this year...\"",
        "edge_reverse": "\"Award season buzz often precedes\nfilm release, not the reverse...\"",
        "edge_spurious": "\"Several popular, acclaimed films\nthis year failed to secure any\nnominations...\"",
        "missing_node": "\"Erivo's performance has been\nwidely compared to a previous\niconic portrayal...\"",
        "irrelevant": "\"The ceremony will be broadcast\non a new streaming platform...\"",
    }

    col_headers = ["Probe Type", "Example Probe", "P(Yes)\nBefore", "P(Yes)\nAfter", "Shift"]
    rows = []

    for pt, label in type_order:
        match = qdf[qdf["probe_type"] == pt]
        if match.empty:
            continue
        row = match.iloc[0]

        p0 = row["initial_probability"]
        p1 = row["updated_probability"]
        shift = p1 - p0

        rows.append([
            label,
            probe_descriptions.get(pt, ""),
            f"{p0:.2f}",
            f"{p1:.2f}",
            f"{shift:+.2f}",
        ])

    q_text = "Will Cynthia Erivo win Best Actress at the 98th Academy Awards?"

    fig, ax = plt.subplots(figsize=(14, 12))
    fig.patch.set_facecolor("white")
    _booktabs_table(ax, col_headers, None, rows, bold_cols={0},
                    title="Probe Type Examples with Probability Updating",
                    fontsize=10, row_height=2.2)

    ax.text(0.5, -0.01,
            f'Example question: "{q_text}"   (Llama-3.3-70B, initial P(Yes) = {init_p:.2f})',
            transform=ax.transAxes, ha="center", va="top",
            fontsize=10, fontstyle="italic", color="#555555")

    plt.tight_layout()
    for ext in ["png", "pdf"]:
        fig.savefig(str(OUT / f"probe_examples_table.{ext}"),
                    dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("Saved probe_examples_table")


def _generate_prompt_comparison_table():
    """Side-by-side comparison of Baseline vs Superforecasting system prompts."""

    # Distill each prompt into its key instructional components
    col_headers = ["Dimension", "Baseline", "Superforecasting"]
    rows = [
        [
            "Role framing",
            "\"Expert forecaster\"",
            "\"Expert forecaster trained in\nsuperforecasting methodology\"",
        ],
        [
            "Starting point",
            "\u2014",
            "Outside view first: consider base rates\nand reference classes",
        ],
        [
            "Factor selection",
            "\u2014",
            "Granular decomposition: distinct,\nmeasurable; no vague/overlapping factors",
        ],
        [
            "Edge criteria",
            "\u2014",
            "Signal vs noise: defensible causal\nmechanism, not just topical relevance",
        ],
        [
            "Edge validation",
            "\u2014",
            "Counterfactual test: \"Would the outcome\nchange if this factor were different?\"",
        ],
        [
            "Calibration",
            "Be well-calibrated;\navoid defaulting to 50%",
            "Use historical base rates as anchors;\navoid round numbers",
        ],
        [
            "DAG structure",
            "Nodes = factors,\nedges = causal links,\n1 outcome node",
            "Same",
        ],
    ]

    fig, ax = plt.subplots(figsize=(12, 5.5))
    fig.patch.set_facecolor("white")
    _booktabs_table(ax, col_headers, None, rows, bold_cols={0},
                    title=None,
                    fontsize=10, row_height=2.0,
                    col_widths=[0.13, 0.22, 0.35])

    ax.text(0.5, -0.01,
            "Superforecasting prompt adds 5 structured principles; "
            "baseline relies on implicit LLM priors for factor selection and edge validation.",
            transform=ax.transAxes, ha="center", va="top",
            fontsize=9, fontstyle="italic", color="#555555")

    plt.tight_layout()
    for ext in ["png", "pdf"]:
        fig.savefig(str(OUT / f"prompt_comparison_table.{ext}"),
                    dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("Saved prompt_comparison_table")


if __name__ == "__main__":
    main()
