"""
Classify ForecastBench questions into topic categories using GPT-4o-mini.

One-shot classification: replaces the brittle keyword regex in the explorer's
prepare-data.ts script. Adds a `topic` field to each question and writes back
to high_complexity_questions.json.

Categories (7):
  - Conflict & Security
  - Politics & Governance
  - Finance & Economics
  - Climate & Energy
  - Health & Science
  - Technology
  - Society & Culture

Usage:
    python -m forecast_bench.classify_question_topic
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

BASE = Path(__file__).parent.parent
HIGH_COMPLEXITY_PATH = BASE / "forecast_bench" / "high_complexity_questions.json"

CATEGORIES = [
    "Conflict & Security",
    "Politics & Governance",
    "Finance & Economics",
    "Climate & Energy",
    "Health & Science",
    "Technology",
    "Society & Culture",
]

SYSTEM_PROMPT = f"""You classify forecasting questions into exactly one topic category.

Categories:
- Conflict & Security: war, military conflict, terrorism, weapons, sanctions, refugees, humanitarian crises
- Politics & Governance: elections, legislation, court cases, impeachment, government appointments, political institutions
- Finance & Economics: stocks, bonds, crypto, market prices, GDP, inflation, unemployment, trade, tariffs, monetary policy, recession, corporate finance
- Climate & Energy: weather, climate change, emissions, renewables, energy markets, EVs
- Health & Science: disease, vaccines, medical treatments, biology, scientific research
- Technology: AI, software, semiconductors, robotics, hardware, internet platforms
- Society & Culture: sports, entertainment, awards, demographics, cultural trends

Pick the SINGLE best fit. Respond with ONLY the category name, no other text."""


def get_api_key() -> str:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        try:
            from archive.wargame_forecasting.config import OPENROUTER_API_KEY
            api_key = OPENROUTER_API_KEY
        except ImportError:
            pass
    return api_key


def classify(question: str, api_key: str) -> str | None:
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
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Question: {question}"},
                ],
                "max_tokens": 20,
                "temperature": 0,
            },
            timeout=30,
        )
        if resp.status_code != 200:
            print(f"  HTTP {resp.status_code}: {resp.text[:200]}")
            return None
        text = resp.json()["choices"][0]["message"]["content"].strip()
        # Match against canonical categories
        for cat in CATEGORIES:
            if cat.lower() in text.lower():
                return cat
        print(f"  Unrecognized: {text!r}")
        return None
    except Exception as e:
        print(f"  Error: {e}")
        return None


def main():
    api_key = get_api_key()
    if not api_key:
        print("Error: set OPENROUTER_API_KEY")
        sys.exit(1)

    questions = json.loads(HIGH_COMPLEXITY_PATH.read_text(encoding="utf-8"))
    print(f"Loaded {len(questions)} questions")

    for i, q in enumerate(questions):
        if "topic" in q:
            continue
        topic = classify(q["question"], api_key)
        if topic is None:
            topic = "Society & Culture"  # fallback
        q["topic"] = topic
        if (i + 1) % 10 == 0:
            print(f"  [{i+1}/{len(questions)}]")
            time.sleep(0.3)

    HIGH_COMPLEXITY_PATH.write_text(
        json.dumps(questions, indent=2), encoding="utf-8"
    )

    # Print distribution
    from collections import Counter
    counts = Counter(q["topic"] for q in questions)
    print(f"\nDistribution:")
    for cat in CATEGORIES:
        print(f"  {cat}: {counts.get(cat, 0)}")
    print(f"\nSaved to {HIGH_COMPLEXITY_PATH}")


if __name__ == "__main__":
    main()
