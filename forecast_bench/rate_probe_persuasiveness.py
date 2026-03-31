"""
Rate probe text persuasiveness using GPT-4o-mini judge.
Blind to importance level — judge sees only the probe text.
Then correlate persuasiveness with importance level and absolute shift.
"""

import csv
import json
import os
import sys
import time
import random
from pathlib import Path

import requests
import numpy as np
from scipy import stats

BASE = Path(__file__).resolve().parent.parent / "outputs" / "sensitivity" / "causal"


def get_api_key():
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


def rate_persuasiveness(probe_text: str, api_key: str) -> int | None:
    """Ask GPT-4o-mini to rate persuasiveness 1-5."""
    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "openai/gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": (
                        "You are evaluating the persuasiveness of arguments. "
                        "Rate how persuasive the following text is on a scale of 1-5:\n"
                        "1 = Very weak, vague, or unconvincing\n"
                        "2 = Somewhat weak, lacks specificity\n"
                        "3 = Moderately persuasive\n"
                        "4 = Strong, specific, and well-argued\n"
                        "5 = Very compelling, with concrete evidence or strong reasoning\n\n"
                        "Respond with ONLY a single integer (1-5). No other text."
                    )},
                    {"role": "user", "content": f"Rate the persuasiveness of this argument:\n\n\"{probe_text}\""},
                ],
                "max_tokens": 5,
                "temperature": 0,
            },
            timeout=30,
        )
        if resp.status_code == 200:
            text = resp.json()["choices"][0]["message"]["content"].strip()
            for ch in text:
                if ch.isdigit() and ch in "12345":
                    return int(ch)
        return None
    except Exception as e:
        print(f"  Error: {e}")
        return None


def main():
    api_key = get_api_key()
    if not api_key:
        print("Error: set OPENROUTER_API_KEY")
        sys.exit(1)

    # Load probes from both conditions
    high_types = {"node_negate_high", "node_strengthen"}
    low_types = {"node_negate_low", "node_strengthen_low"}

    for condition, path in [
        ("ORIGINAL", BASE / "70b_one_turn" / "sensitivity_results.csv"),
        ("NEUTRAL", BASE / "llama_70b_neutral" / "sensitivity_results.csv"),
    ]:
        print(f"\n{'='*60}")
        print(f"  {condition}")
        print(f"{'='*60}")

        rows = []
        with open(path, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r.get("success", "").lower() != "true":
                    continue
                pt = r["probe_type"]
                if pt in high_types:
                    r["importance"] = "high"
                elif pt in low_types:
                    r["importance"] = "low"
                else:
                    continue
                rows.append(r)

        # Sample 100 per importance level (or all if fewer)
        random.seed(42)
        high_rows = [r for r in rows if r["importance"] == "high"]
        low_rows = [r for r in rows if r["importance"] == "low"]
        sample_high = random.sample(high_rows, min(100, len(high_rows)))
        sample_low = random.sample(low_rows, min(100, len(low_rows)))
        sample = sample_high + sample_low
        random.shuffle(sample)

        print(f"  Sampling {len(sample_high)} high + {len(sample_low)} low = {len(sample)} probes")
        print(f"  Rating persuasiveness...")

        ratings = []
        for i, r in enumerate(sample):
            score = rate_persuasiveness(r["probe_text"], api_key)
            ratings.append({
                "importance": r["importance"],
                "probe_type": r["probe_type"],
                "persuasiveness": score,
                "absolute_shift": float(r["absolute_shift"]),
                "probe_text": r["probe_text"][:100],
            })
            if (i + 1) % 20 == 0:
                print(f"    [{i+1}/{len(sample)}]")
                time.sleep(0.3)

        # Filter successful ratings
        valid = [r for r in ratings if r["persuasiveness"] is not None]
        high_scores = [r["persuasiveness"] for r in valid if r["importance"] == "high"]
        low_scores = [r["persuasiveness"] for r in valid if r["importance"] == "low"]

        print(f"\n  Results ({len(valid)} rated):")
        print(f"  HIGH importance: mean persuasiveness = {np.mean(high_scores):.2f} (sd={np.std(high_scores):.2f}, n={len(high_scores)})")
        print(f"  LOW  importance: mean persuasiveness = {np.mean(low_scores):.2f} (sd={np.std(low_scores):.2f}, n={len(low_scores)})")

        u, p = stats.mannwhitneyu(high_scores, low_scores, alternative="two-sided")
        print(f"  Mann-Whitney U={u:.0f}, p={p:.4f}")

        # Correlate persuasiveness with shift
        all_scores = [r["persuasiveness"] for r in valid]
        all_shifts = [r["absolute_shift"] for r in valid]
        rho, p_rho = stats.spearmanr(all_scores, all_shifts)
        print(f"  Persuasiveness-shift Spearman rho={rho:.3f}, p={p_rho:.4f}")

        # Within high only
        high_valid = [r for r in valid if r["importance"] == "high"]
        if len(high_valid) > 10:
            rho_h, p_h = stats.spearmanr(
                [r["persuasiveness"] for r in high_valid],
                [r["absolute_shift"] for r in high_valid],
            )
            print(f"  Within HIGH: persuasiveness-shift rho={rho_h:.3f}, p={p_h:.4f}")

        # Save
        out_path = BASE / f"persuasiveness_ratings_{condition.lower()}.csv"
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["importance", "probe_type", "persuasiveness", "absolute_shift", "probe_text"])
            w.writeheader()
            for r in valid:
                w.writerow(r)
        print(f"  Saved: {out_path}")


if __name__ == "__main__":
    main()
