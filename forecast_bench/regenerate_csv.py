"""
Regenerate sensitivity_results.csv from per-question JSON files.

Fixes missing metadata (target_description, etc.) by re-joining
probe_results with probe/probe_target data from the shared stages cache.

Usage:
    python -m forecast_bench.regenerate_csv \
        --output-dir outputs/sensitivity/causal/70b_one_turn_retest
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from forecast_bench.run_sensitivity import CAUSAL_CSV_FIELDS
from forecast_bench.prompts_causal import PROBE_CATEGORIES

# Import supplementary target computation for backfilling descriptions
try:
    from forecast_bench.run_supplementary_probes import compute_new_targets
except ImportError:
    compute_new_targets = None


def regenerate(output_dir: Path):
    q_dir = output_dir / "question_results"
    shared_dir = output_dir / "_shared_stages_causal"
    csv_path = output_dir / "sensitivity_results.csv"

    if not q_dir.exists():
        print(f"[ERROR] No question_results in {output_dir}")
        return

    files = sorted(q_dir.glob("q_*.json"))
    print(f"Regenerating CSV from {len(files)} question JSONs")
    print(f"  Shared stages dir: {shared_dir} (exists={shared_dir.exists()})")

    total_rows = 0
    fixed_desc = 0

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CAUSAL_CSV_FIELDS)
        writer.writeheader()

        for qf in files:
            data = json.loads(qf.read_text(encoding="utf-8"))
            qid = data["question_id"]
            q_text = data.get("question_text", "")[:200]
            condition = data.get("condition", "one-turn")
            initial_prob = data["initial_probability"]
            na = data.get("network_analysis", {})
            probes = data.get("probes", [])
            probe_targets = data.get("probe_targets", [])
            probe_results = data.get("probe_results", [])

            # Build lookup: target_id+probe_type -> description from probes list
            desc_lookup = {}        # (target_id, probe_type) -> description
            desc_by_id = {}         # target_id -> description (fallback)
            for p in probes:
                key = (p.get("target_id", ""), p.get("probe_type", ""))
                desc_lookup[key] = p.get("description", "")
                tid = p.get("target_id", "")
                if tid and p.get("description"):
                    desc_by_id[tid] = p["description"]
            for pt in probe_targets:
                key = (pt.get("target_id", ""), pt.get("probe_type", ""))
                if key not in desc_lookup or not desc_lookup[key]:
                    desc_lookup[key] = pt.get("description", "")
                tid = pt.get("target_id", "")
                if tid and pt.get("description") and tid not in desc_by_id:
                    desc_by_id[tid] = pt["description"]

            # Also compute supplementary targets from shared stages cache
            if compute_new_targets is not None:
                cache_path = shared_dir / f"q_{qid}.json"
                if cache_path.exists():
                    shared = json.loads(cache_path.read_text(encoding="utf-8"))
                    for t in compute_new_targets(shared):
                        tid = t.get("target_id", "")
                        key = (tid, t.get("probe_type", ""))
                        if key not in desc_lookup or not desc_lookup[key]:
                            desc_lookup[key] = t.get("description", "")
                        if tid and t.get("description") and tid not in desc_by_id:
                            desc_by_id[tid] = t["description"]

            for pi, result in enumerate(probe_results):
                # Try to get description from the result, then from probe lookup
                target_desc = result.get("description", "")
                if not target_desc:
                    key = (result.get("target_id", ""), result.get("probe_type", ""))
                    target_desc = desc_lookup.get(key, "")
                    if target_desc:
                        fixed_desc += 1

                # Fallback: lookup by just target_id
                if not target_desc:
                    target_desc = desc_by_id.get(result.get("target_id", ""), "")
                    if target_desc:
                        fixed_desc += 1

                # Also try matching by probe index if within range of probes list
                if not target_desc and pi < len(probes):
                    target_desc = probes[pi].get("description", "")
                    if target_desc:
                        fixed_desc += 1

                row = {
                    "question_id": qid,
                    "question_text": q_text,
                    "condition": condition,
                    "initial_probability": f"{initial_prob:.4f}",
                    "probe_index": pi,
                    "probe_type": result.get("probe_type", ""),
                    "probe_category": result.get("probe_category", PROBE_CATEGORIES.get(result.get("probe_type", ""), "")),
                    "target_id": result.get("target_id", ""),
                    "target_description": target_desc[:200],
                    "target_importance": f"{result.get('target_importance', 0.0):.4f}" if result.get("target_importance") is not None else "",
                    "target_centrality_rank": result.get("target_centrality_rank", 0),
                    "target_on_critical_path": result.get("target_on_critical_path", False),
                    "probe_text": result.get("probe_text", "")[:300],
                    "probe_generated": result.get("probe_generated", True),
                    "updated_probability": f"{result['updated_probability']:.4f}" if result.get("updated_probability") is not None else "",
                    "absolute_shift": f"{result['absolute_shift']:.4f}" if result.get("absolute_shift") is not None else "",
                    "shift_direction": result.get("shift_direction", ""),
                    "success": result.get("success", False),
                    "reasoning": result.get("reasoning", "")[:300],
                    "n_nodes": na.get("n_nodes", 0),
                    "n_edges": na.get("n_edges", 0),
                    "graph_density": f"{na.get('density', 0.0):.4f}",
                }
                writer.writerow(row)
                total_rows += 1

    print(f"  Wrote {total_rows} rows to {csv_path}")
    print(f"  Fixed {fixed_desc} missing target_descriptions")


def main():
    parser = argparse.ArgumentParser(description="Regenerate sensitivity CSV from question JSONs")
    parser.add_argument("--output-dir", required=True, help="Run output directory")
    args = parser.parse_args()
    regenerate(Path(args.output_dir))


if __name__ == "__main__":
    main()
