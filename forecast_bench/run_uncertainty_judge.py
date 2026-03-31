"""
LLM-as-a-Judge for epistemic uncertainty in reasoning responses.

Rates how much uncertainty/hedging each Stage 3 reasoning response expresses,
independent of the actual probability shift.

Output: JSON file mapping (model, question_id, probe_index) -> uncertainty rating.

Usage:
    python -m forecast_bench.run_uncertainty_judge
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from forecast_bench.analysis_full import load_question_jsons

# ── Config ──────────────────────────────────────────────────────────────────
BASE = Path(__file__).parent.parent
CAUSAL_DIR = BASE / "outputs" / "sensitivity" / "causal"
OUTPUT_PATH = CAUSAL_DIR / "uncertainty_judge_ratings.json"

MODEL_DIRS = {
    "llama-8b": CAUSAL_DIR / "llama_neutral",
    "llama-70b": CAUSAL_DIR / "llama_70b_neutral",
    "deepseek": CAUSAL_DIR / "deepseek_neutral",
    "qwen": CAUSAL_DIR / "qwen_neutral",
    "gemini": CAUSAL_DIR / "gemini_flash_lite_neutral",
    "gpt-oss": CAUSAL_DIR / "gpt_oss_neutral",
}

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "") or \
    "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"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
JUDGE_MODEL = "openai/gpt-4o-mini"

JUDGE_SYSTEM = """\
You are evaluating the level of epistemic uncertainty expressed in a \
forecaster's reasoning about a probability estimate.

Rate how much uncertainty the forecaster EXPRESSES in their reasoning, \
on a scale of 1-5:

1 = Very confident: uses definitive language, no hedging, presents conclusions as certain
2 = Mostly confident: occasional qualifiers but overall assertive tone
3 = Balanced: acknowledges uncertainty while still taking a position
4 = Uncertain: frequent hedging, multiple caveats, expresses doubt about conclusions
5 = Very uncertain: dominated by uncertainty language, unable to commit to a position

Focus ONLY on the VERBAL expression of uncertainty, not on the probability \
value itself. Respond with ONLY a JSON object: \
{"rating": <int 1-5>, "brief_reason": "<1 sentence>"}"""


def _call_judge(reasoning_text: str) -> dict | None:
    """Call GPT-4o-mini to rate uncertainty in a reasoning response."""
    user_msg = f"Reasoning response:\n\"{reasoning_text}\""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": JUDGE_MODEL,
        "messages": [
            {"role": "system", "content": JUDGE_SYSTEM},
            {"role": "user", "content": user_msg},
        ],
        "max_tokens": 100,
        "temperature": 0,
    }

    for attempt in range(3):
        try:
            r = requests.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30,
            )
            if r.status_code == 429:
                time.sleep(2 ** attempt)
                continue
            r.raise_for_status()

            text = r.json()["choices"][0]["message"]["content"].strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            result = json.loads(text)
            rating = int(result["rating"])
            if 1 <= rating <= 5:
                return {
                    "rating": rating,
                    "reason": result.get("brief_reason", ""),
                }
        except (json.JSONDecodeError, KeyError, ValueError, requests.RequestException) as e:
            if attempt < 2:
                time.sleep(1)
                continue
            print(f"    Failed after 3 attempts: {e}")
            return None

    return None


def main():
    if OUTPUT_PATH.exists():
        existing = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    else:
        existing = {}

    total = 0
    new = 0

    for model_name, model_dir in MODEL_DIRS.items():
        q_data = load_question_jsons(model_dir)
        print(f"\n{model_name}: {len(q_data)} questions")

        for qid, qd in q_data.items():
            probe_results = qd.get("probe_results", [])
            for i, pr in enumerate(probe_results):
                key = f"{model_name}|{qid}|{i}"
                total += 1

                if key in existing:
                    continue

                reasoning = pr.get("reasoning", "")
                if not reasoning or len(reasoning) < 20:
                    existing[key] = {"rating": None, "reason": "too_short"}
                    new += 1
                    continue

                judge_result = _call_judge(reasoning)

                if judge_result:
                    existing[key] = judge_result
                else:
                    existing[key] = {"rating": None, "reason": "judge_failed"}

                new += 1

                if new % 50 == 0:
                    OUTPUT_PATH.write_text(
                        json.dumps(existing, indent=2), encoding="utf-8"
                    )
                    rated = sum(1 for v in existing.values() if v.get("rating") is not None)
                    print(f"  Progress: {new} new, {rated}/{total} rated total")

    # Final save
    OUTPUT_PATH.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    rated = sum(1 for v in existing.values() if v.get("rating") is not None)
    print(f"\nDone! {rated}/{total} rated, saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
