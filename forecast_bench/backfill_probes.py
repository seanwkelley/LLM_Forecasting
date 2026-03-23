"""
Retry failed probes in existing question result JSONs.

Reads each question's JSON, finds probes with success=False,
re-runs only those probes, updates the JSON, then regenerates the CSV.

Usage:
    python -m forecast_bench.backfill_probes \
        --model gemini-flash-lite \
        --output-dir outputs/sensitivity/causal/gemini_flash_lite_one_turn_retest
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from forecast_bench.llm_client import LLMClient
from forecast_bench.prompts_causal import (
    CAUSAL_PROBED_FORECAST_SYSTEM,
    PROBE_CATEGORIES,
    build_causal_probed_forecast_prompt,
)
from forecast_bench.run_sensitivity import MODEL_MAP, _parse_probe_result
from forecast_bench.regenerate_csv import regenerate


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


def backfill(args):
    model = MODEL_MAP.get(args.model, args.model)
    api_key = _get_api_key()
    if not api_key:
        print("[ERROR] OPENROUTER_API_KEY not set.")
        sys.exit(1)

    output_dir = Path(args.output_dir)
    q_dir = output_dir / "question_results"

    if not q_dir.exists():
        print(f"[ERROR] No question_results in {output_dir}")
        sys.exit(1)

    client = LLMClient(
        api_key=api_key,
        model=model,
        temperature=args.temperature,
        max_tokens=1200,
    )

    files = sorted(q_dir.glob("q_*.json"))
    print(f"\n{'='*60}")
    print(f"BACKFILL FAILED PROBES")
    print(f"{'='*60}")
    print(f"Model: {model}")
    print(f"Output: {output_dir}")
    print(f"Question files: {len(files)}")

    total_retried = 0
    total_fixed = 0
    total_still_failed = 0

    for fi, qf in enumerate(files):
        data = json.loads(qf.read_text(encoding="utf-8"))
        qid = data["question_id"]
        initial_prob = data["initial_probability"]
        nodes = data["nodes"]
        edges = data["edges"]
        probes = data.get("probes", [])
        probe_results = data.get("probe_results", [])

        # Find failed probes
        failed_indices = [
            i for i, r in enumerate(probe_results)
            if not r.get("success", False)
        ]

        if not failed_indices:
            continue

        print(f"  [{fi+1}/{len(files)}] {qid[:40]} -- {len(failed_indices)} failed probes ...", end=" ")

        fixed = 0
        for idx in failed_indices:
            result = probe_results[idx]

            # Find the matching probe definition
            # For main probes (idx < len(probes)), use probes[idx]
            # For supplementary probes, reconstruct from result metadata
            if idx < len(probes):
                probe = probes[idx]
            else:
                # Supplementary probe - reconstruct minimal probe dict
                probe = {
                    "probe_text": result.get("probe_text", ""),
                    "probe_type": result.get("probe_type", ""),
                    "target_id": result.get("target_id", ""),
                    "target_type": result.get("target_type", "node"),
                    "importance": result.get("target_importance", 0),
                    "centrality_rank": result.get("target_centrality_rank", 0),
                    "on_critical_path": result.get("target_on_critical_path", False),
                    "generated": result.get("probe_generated", True),
                    "description": result.get("description", ""),
                }

            probe_target = {
                "target_type": probe.get("target_type", ""),
                "target_id": probe.get("target_id", ""),
                "description": probe.get("description", ""),
                "importance": probe.get("importance", 0.0),
                "centrality_rank": probe.get("centrality_rank", 0),
                "on_critical_path": probe.get("on_critical_path", False),
                "probe_type": probe.get("probe_type", ""),
            }

            user_prompt = build_causal_probed_forecast_prompt(
                data["question_text"], initial_prob, nodes, edges, probe, probe_target,
            )

            text, ok = client.call_single(CAUSAL_PROBED_FORECAST_SYSTEM, user_prompt)
            client.rate_limit_wait()

            new_result = _parse_probe_result(client, probe, initial_prob, text, ok)
            # Preserve metadata from original result
            new_result["target_id"] = result.get("target_id", probe.get("target_id", ""))
            new_result["target_type"] = result.get("target_type", probe.get("target_type", ""))
            new_result["target_importance"] = result.get("target_importance", probe.get("importance", 0.0))
            new_result["target_centrality_rank"] = result.get("target_centrality_rank", probe.get("centrality_rank", 0))
            new_result["target_on_critical_path"] = result.get("target_on_critical_path", probe.get("on_critical_path", False))
            new_result["probe_category"] = result.get("probe_category", PROBE_CATEGORIES.get(probe.get("probe_type", ""), ""))
            new_result["description"] = probe.get("description", result.get("description", ""))

            if new_result.get("success"):
                fixed += 1
                probe_results[idx] = new_result
            else:
                total_still_failed += 1

            total_retried += 1

        total_fixed += fixed
        print(f"fixed {fixed}/{len(failed_indices)}")

        # Save updated JSON
        data["probe_results"] = probe_results
        qf.write_text(json.dumps(data, indent=2), encoding="utf-8")

    print(f"\n{'='*60}")
    print(f"Retried: {total_retried}, Fixed: {total_fixed}, Still failed: {total_still_failed}")
    print(f"API stats: {json.dumps(client.stats.__dict__, indent=2)}")
    print(f"{'='*60}")

    # Regenerate CSV
    if total_fixed > 0:
        print("\nRegenerating CSV...")
        regenerate(output_dir)


def main():
    parser = argparse.ArgumentParser(description="Backfill failed probes")
    parser.add_argument("--model", required=True, help="Model name")
    parser.add_argument("--output-dir", required=True, help="Run output directory")
    parser.add_argument("--temperature", type=float, default=0.3)
    args = parser.parse_args()
    backfill(args)


if __name__ == "__main__":
    main()
