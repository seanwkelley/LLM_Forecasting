"""
ELO-based question difficulty ranking via LLM pairwise comparison.

Uses GPT-4o-mini via OpenRouter to judge which of two forecasting questions
is harder to predict accurately, then computes ELO ratings from the results.

Swiss-system tournament: ~15 rounds × 50 matchups = ~750 comparisons
(instead of all 4,950 pairs from 100 questions).

Output:
    outputs/sensitivity/causal/difficulty_elo.json
        - elo_ratings: {qid: rating}
        - comparisons: [{q1, q2, winner, reason}, ...]
        - metadata: tournament parameters

Usage:
    python -m forecast_bench.run_difficulty_elo
"""

from __future__ import annotations

import json
import math
import os
import random
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from forecast_bench.questions import load_forecastbench_questions

# ── Config ──────────────────────────────────────────────────────────────────
BASE = Path(__file__).parent.parent
CAUSAL_DIR = BASE / "outputs" / "sensitivity" / "causal"
OUTPUT_PATH = CAUSAL_DIR / "difficulty_elo.json"

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "") or \
    "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"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
JUDGE_MODEL = "openai/gpt-4o-mini"

# Tournament parameters
N_ROUNDS = 15
K_FACTOR = 32
INITIAL_ELO = 1500

JUDGE_SYSTEM = """\
You are comparing two forecasting questions to determine which is HARDER \
to predict accurately. "Harder" means more difficult for a skilled forecaster \
to assign an accurate probability to, regardless of what that probability is.

Consider these dimensions of difficulty:
- Information availability: Is there rich data and precedent, or is it a novel situation?
- Causal complexity: How many interacting factors determine the outcome?
- Temporal sensitivity: Does the answer hinge on hard-to-predict timing?
- Domain opacity: Are the key drivers observable, or hidden behind closed doors?
- Reference class ambiguity: Are there good historical analogues?
- Strategic interaction: Do actors respond to forecasts or each other's moves?

IMPORTANT: A question can be at any probability level (high, low, or middle) \
and still be easy or hard. A 95% question can be trivially easy (will the sun \
rise?) or very hard (will a specific drug trial succeed, given favorable Phase 2 data?). \
Do NOT equate closeness to 50% with difficulty.

Respond with ONLY a JSON object:
{"harder": 1 or 2, "confidence": "low"|"medium"|"high", \
"reason": "<1-2 sentences explaining why>"}"""


def _call_judge(q1_text: str, q2_text: str) -> dict | None:
    """Ask GPT-4o-mini which question is harder to forecast."""
    user_msg = (
        f"Question 1:\n\"{q1_text}\"\n\n"
        f"Question 2:\n\"{q2_text}\"\n\n"
        "Which question is harder to predict accurately?"
    )

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
        "max_tokens": 150,
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
            harder = int(result["harder"])
            if harder in (1, 2):
                return {
                    "harder": harder,
                    "confidence": result.get("confidence", "medium"),
                    "reason": result.get("reason", ""),
                }
        except (json.JSONDecodeError, KeyError, ValueError, requests.RequestException) as e:
            if attempt < 2:
                time.sleep(1)
                continue
            print(f"    Judge failed after 3 attempts: {e}")
            return None

    return None


def _expected_score(rating_a: float, rating_b: float) -> float:
    """ELO expected score for player A."""
    return 1.0 / (1.0 + 10.0 ** ((rating_b - rating_a) / 400.0))


def _update_elo(
    ratings: dict[str, float], winner_id: str, loser_id: str, k: float = K_FACTOR
) -> None:
    """Update ELO ratings in place. Winner = harder question."""
    e_w = _expected_score(ratings[winner_id], ratings[loser_id])
    e_l = 1.0 - e_w
    ratings[winner_id] += k * (1.0 - e_w)
    ratings[loser_id] += k * (0.0 - e_l)


def _swiss_pairings(
    ratings: dict[str, float], qids: list[str], past_pairs: set[tuple[str, str]],
    rng: random.Random,
) -> list[tuple[str, str]]:
    """Generate Swiss-system pairings: match questions with similar ratings.

    Avoids repeat matchups. Returns list of (qid_a, qid_b) pairs.
    """
    # Sort by current rating
    sorted_qids = sorted(qids, key=lambda q: ratings[q], reverse=True)
    paired = set()
    pairs = []

    for i, qa in enumerate(sorted_qids):
        if qa in paired:
            continue
        # Try adjacent opponents, expanding outward
        candidates = []
        for j in range(i + 1, len(sorted_qids)):
            qb = sorted_qids[j]
            if qb in paired:
                continue
            pair_key = tuple(sorted([qa, qb]))
            if pair_key in past_pairs:
                continue
            candidates.append(qb)
            if len(candidates) >= 3:
                break

        if candidates:
            qb = rng.choice(candidates)
            pairs.append((qa, qb))
            paired.add(qa)
            paired.add(qb)

    return pairs


def main():
    rng = random.Random(42)

    # Load questions
    questions = load_forecastbench_questions(max_questions=100, seed=42)
    q_by_id = {q["id"]: q for q in questions}
    qids = list(q_by_id.keys())
    print(f"Loaded {len(qids)} questions")

    # Load existing results for resume
    comparisons = []
    past_pairs: set[tuple[str, str]] = set()
    ratings: dict[str, float] = {qid: INITIAL_ELO for qid in qids}
    start_round = 0

    if OUTPUT_PATH.exists():
        existing = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        comparisons = existing.get("comparisons", [])
        if comparisons:
            # Rebuild ratings from saved comparisons
            for comp in comparisons:
                pair_key = tuple(sorted([comp["q1"], comp["q2"]]))
                past_pairs.add(pair_key)
                winner = comp["q1"] if comp["winner"] == 1 else comp["q2"]
                loser = comp["q2"] if comp["winner"] == 1 else comp["q1"]
                if winner in ratings and loser in ratings:
                    _update_elo(ratings, winner, loser)
            start_round = existing.get("metadata", {}).get("rounds_completed", 0)
            print(f"Resuming from round {start_round} ({len(comparisons)} existing comparisons)")

    # Run Swiss tournament
    for round_num in range(start_round, N_ROUNDS):
        pairs = _swiss_pairings(ratings, qids, past_pairs, rng)
        print(f"\nRound {round_num + 1}/{N_ROUNDS}: {len(pairs)} matchups")

        for i, (qa, qb) in enumerate(pairs):
            # Randomize presentation order to control for position bias
            if rng.random() < 0.5:
                first, second = qa, qb
                flip = False
            else:
                first, second = qb, qa
                flip = True

            result = _call_judge(q_by_id[first]["question"], q_by_id[second]["question"])

            if result is None:
                continue

            # Map judge answer back to original (qa, qb) ordering
            if flip:
                # first=qb, second=qa. Judge says 1=qb harder, 2=qa harder
                winner_idx = 2 if result["harder"] == 1 else 1
            else:
                winner_idx = result["harder"]

            winner = qa if winner_idx == 1 else qb
            loser = qb if winner_idx == 1 else qa
            _update_elo(ratings, winner, loser)

            pair_key = tuple(sorted([qa, qb]))
            past_pairs.add(pair_key)

            comparisons.append({
                "q1": qa,
                "q2": qb,
                "winner": winner_idx,
                "confidence": result["confidence"],
                "reason": result["reason"],
                "round": round_num + 1,
            })

            if (i + 1) % 10 == 0:
                print(f"  {i + 1}/{len(pairs)} done")

        # Checkpoint after each round
        _save(ratings, comparisons, q_by_id, round_num + 1)
        print(f"  Round {round_num + 1} complete. Top 5 hardest:")
        top5 = sorted(ratings, key=lambda q: ratings[q], reverse=True)[:5]
        for q in top5:
            print(f"    {ratings[q]:.0f}  {q_by_id[q]['question'][:80]}")

    _save(ratings, comparisons, q_by_id, N_ROUNDS)
    print(f"\nDone! {len(comparisons)} comparisons, saved to {OUTPUT_PATH}")

    # Print final rankings
    print("\n" + "=" * 80)
    print("FINAL DIFFICULTY RANKINGS (hardest first)")
    print("=" * 80)
    for rank, qid in enumerate(sorted(ratings, key=lambda q: ratings[q], reverse=True), 1):
        print(f"  {rank:3d}. [{ratings[qid]:.0f}] {q_by_id[qid]['question'][:90]}")


def _save(
    ratings: dict[str, float],
    comparisons: list[dict],
    q_by_id: dict[str, dict],
    rounds_completed: int,
) -> None:
    """Save current state to JSON."""
    # Sort ratings for readability
    sorted_ratings = dict(
        sorted(ratings.items(), key=lambda x: x[1], reverse=True)
    )
    # Add question text for convenience
    ratings_with_text = {
        qid: {
            "elo": round(elo, 1),
            "question": q_by_id[qid]["question"][:200],
        }
        for qid, elo in sorted_ratings.items()
    }

    output = {
        "elo_ratings": {qid: round(elo, 1) for qid, elo in sorted_ratings.items()},
        "ratings_detail": ratings_with_text,
        "comparisons": comparisons,
        "metadata": {
            "n_questions": len(ratings),
            "n_comparisons": len(comparisons),
            "rounds_completed": rounds_completed,
            "total_rounds": N_ROUNDS,
            "k_factor": K_FACTOR,
            "initial_elo": INITIAL_ELO,
            "judge_model": JUDGE_MODEL,
        },
    }

    OUTPUT_PATH.write_text(json.dumps(output, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
