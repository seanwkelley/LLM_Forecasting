"""
Retry failed probes in neutral run CSVs.
Reads the CSV, finds failed rows, re-calls the API, and overwrites the CSV.
"""

import csv
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from forecast_bench.llm_client import LLMClient, parse_json_response
from forecast_bench.prompts_causal import (
    CAUSAL_PROBED_FORECAST_SYSTEM,
    PROBE_CATEGORIES,
    _format_network_context,
    build_causal_probed_forecast_prompt,
)
from forecast_bench.run_sensitivity import MODEL_MAP


def _get_api_key():
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
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


def main():
    api_key = _get_api_key()
    if not api_key:
        print("Error: set OPENROUTER_API_KEY")
        sys.exit(1)

    base = Path("outputs/sensitivity/causal")

    configs = [
        ("Llama-70B", "meta-llama/llama-3.3-70b-instruct", base / "llama_70b_neutral", base / "llama_70b_neutral"),
        ("Qwen3-235B", "qwen/qwen3-235b-a22b-2507", base / "qwen_neutral", base / "qwen_neutral"),
        ("Gemini-FL", "google/gemini-2.5-flash-lite", base / "gemini_fl_neutral", base / "gemini_fl_neutral"),
        ("GPT-OSS", "openai/gpt-oss-120b:nitro", base / "gpt_oss_neutral", base / "gpt_oss_neutral"),
        ("Qwen3-32B", "qwen/qwen3-32b:nitro", base / "qwen_32b_neutral", base / "qwen_32b_neutral"),
    ]

    for model_name, model_id, neutral_dir, source_dir in configs:
        csv_path = neutral_dir / "sensitivity_results.csv"
        if not csv_path.exists():
            continue

        # Read all rows
        with open(csv_path, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        failed = [(i, r) for i, r in enumerate(rows) if r.get("success", "").lower() != "true"]
        if not failed:
            print(f"{model_name}: no failures")
            continue

        print(f"\n{model_name}: {len(failed)} failed probes, retrying...")

        client = LLMClient(api_key=api_key, model=model_id, temperature=0.7, max_tokens=2000)

        # Load question data for failed probes
        q_dir = source_dir / "question_results"
        q_cache = {}

        for idx, row in failed:
            qid = row["question_id"]
            if qid not in q_cache:
                qpath = q_dir / f"q_{qid}.json"
                if qpath.exists():
                    q_cache[qid] = json.loads(qpath.read_text(encoding="utf-8"))

            qdata = q_cache.get(qid)
            if not qdata:
                print(f"  Skip: no source data for {qid}")
                continue

            nodes = qdata["nodes"]
            edges = qdata["edges"]
            initial_prob = float(row["initial_probability"])
            probe_type = row["probe_type"]
            target_id = row.get("target_id", "")
            probe_text = row.get("probe_text", "")

            probe = {"probe_text": probe_text, "probe_type": probe_type, "target_id": target_id}
            probe_target = {
                "target_type": row.get("probe_category", ""),
                "target_id": target_id,
                "description": row.get("target_description", ""),
                "importance": float(row.get("target_importance", 0)),
                "centrality_rank": int(row.get("target_centrality_rank", 0)),
                "on_critical_path": row.get("target_on_critical_path", "").lower() == "true",
                "probe_type": probe_type,
            }

            user_prompt = build_causal_probed_forecast_prompt(
                qdata["question_text"], initial_prob, nodes, edges, probe, probe_target,
            )

            success = False
            for attempt in range(3):
                text, ok = client.call_single(CAUSAL_PROBED_FORECAST_SYSTEM, user_prompt)
                client.rate_limit_wait()

                if not ok:
                    continue

                data = parse_json_response(text)
                if data is None or not isinstance(data, dict):
                    continue

                updated = data.get("updated_probability")
                if updated is None:
                    continue

                updated = max(0.01, min(0.99, float(updated)))
                shift = abs(updated - initial_prob)

                rows[idx]["success"] = "True"
                rows[idx]["updated_probability"] = f"{updated:.4f}"
                rows[idx]["absolute_shift"] = f"{shift:.4f}"
                rows[idx]["shift_direction"] = data.get("shift_direction", "")
                rows[idx]["reasoning"] = data.get("reasoning", "")[:300]
                success = True
                break

            status = "OK" if success else "STILL FAILED"
            print(f"  {probe_type:30s} {target_id[:30]:30s} -> {status}")

        # Write back
        fieldnames = list(rows[0].keys())
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        new_failed = sum(1 for r in rows if r.get("success", "").lower() != "true")
        print(f"  Done: {len(failed)} retried, {new_failed} still failed")


if __name__ == "__main__":
    main()
