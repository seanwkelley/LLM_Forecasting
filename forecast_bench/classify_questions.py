"""Classify the 100 forecast questions into topic categories using an LLM.

Uses GPT-4o-mini via OpenRouter to classify each question, then caches
the results so the LLM is only called once.

Outputs:
    outputs/sensitivity/causal/question_categories.json
    paper/figures/question_categories.pdf / .png
"""
from __future__ import annotations

import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

BASE = Path(__file__).parent.parent
CAUSAL_DIR = BASE / "outputs" / "sensitivity" / "causal"
FIGURES_DIR = BASE / "paper" / "figures"
QDIR = CAUSAL_DIR / "llama_one_turn" / "question_results"
CACHE_PATH = CAUSAL_DIR / "question_categories.json"

CATEGORIES = [
    "Science & Technology",
    "Finance & Markets",
    "Weather & Climate",
    "Armed Conflict & Protest",
    "Geopolitics & Governance",
    "Entertainment & Culture",
    "Sports",
]

SYSTEM_PROMPT = f"""You are a topic classifier for forecasting questions.
Classify each question into exactly one of these categories:
{json.dumps(CATEGORIES)}

Reply with ONLY the category name, nothing else."""


def _get_api_key() -> str:
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        try:
            from forecasting.config import OPENROUTER_API_KEY
            api_key = OPENROUTER_API_KEY
        except Exception:
            pass
    if not api_key:
        try:
            from archive.wargame_forecasting.config import OPENROUTER_API_KEY
            api_key = OPENROUTER_API_KEY
        except Exception:
            pass
    return api_key


def classify_batch(questions: dict[str, str]) -> dict[str, str]:
    """Classify questions via GPT-4o-mini. Returns {qid: category}."""
    import openai

    api_key = _get_api_key()
    if not api_key:
        print("[ERROR] OPENROUTER_API_KEY not set.")
        sys.exit(1)

    client = openai.OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

    results = {}
    items = list(questions.items())
    for i, (qid, qtxt) in enumerate(items):
        for attempt in range(3):
            try:
                resp = client.chat.completions.create(
                    model="openai/gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": qtxt[:500]},
                    ],
                    temperature=0,
                    max_tokens=30,
                )
                cat = resp.choices[0].message.content.strip()
                # Validate against allowed categories
                if cat not in CATEGORIES:
                    # Try fuzzy match
                    for c in CATEGORIES:
                        if c.lower() in cat.lower() or cat.lower() in c.lower():
                            cat = c
                            break
                    else:
                        print(f"  WARNING: '{cat}' not in categories for: {qtxt[:80]}")
                        cat = "Other"
                results[qid] = cat
                break
            except Exception as e:
                if attempt < 2:
                    time.sleep(2)
                else:
                    print(f"  FAILED after 3 attempts: {qid}: {e}")
                    results[qid] = "Other"

        if (i + 1) % 20 == 0:
            print(f"  Classified {i + 1}/{len(items)}")

    return results


def main():
    # Load all questions
    files = sorted(QDIR.glob("*.json"))
    questions: dict[str, str] = {}
    q_texts: dict[str, str] = {}

    for f in files:
        d = json.loads(f.read_text(encoding="utf-8"))
        qid = d["question_id"]
        qtxt = d.get("question_text", "")
        questions[qid] = qtxt
        q_texts[qid] = qtxt[:200]

    # Check cache — only classify uncached questions
    cached: dict[str, dict] = {}
    if CACHE_PATH.exists():
        cached = json.loads(CACHE_PATH.read_text(encoding="utf-8"))

    to_classify = {
        qid: qtxt for qid, qtxt in questions.items()
        if qid not in cached or "category" not in cached[qid]
    }

    if to_classify:
        print(f"Classifying {len(to_classify)} questions via GPT-4o-mini...")
        new_cats = classify_batch(to_classify)
        for qid, cat in new_cats.items():
            cached[qid] = {
                "question_text": q_texts[qid],
                "category": cat,
            }
    else:
        print("All questions already classified (cached).")

    # Build final output
    categories = {
        qid: cached[qid] for qid in questions if qid in cached
    }

    # Save
    CACHE_PATH.write_text(
        json.dumps(categories, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Wrote {CACHE_PATH}")

    cat_counts: Counter = Counter()
    for v in categories.values():
        cat_counts[v["category"]] += 1

    print(f"\nCategory breakdown (n={len(categories)}):")
    for cat, n in cat_counts.most_common():
        print(f"  {cat}: {n}")

    # ── Bar chart ─────────────────────────────────────────────────────────
    sorted_cats = cat_counts.most_common()
    labels = [c for c, _ in sorted_cats]
    counts = [n for _, n in sorted_cats]

    colors = {
        "Finance & Markets": "#1f77b4",
        "Armed Conflict & Protest": "#d62728",
        "Weather & Climate": "#2ca02c",
        "Science & Technology": "#9467bd",
        "Geopolitics & Governance": "#e6550d",
        "Sports": "#17becf",
        "Entertainment & Culture": "#bcbd22",
        "Other": "#7f7f7f",
    }

    total = sum(counts)
    pcts = [100 * n / total for n in counts]

    fig, ax = plt.subplots(figsize=(6, 3.5))
    bars = ax.barh(
        range(len(labels)),
        pcts,
        color=[colors.get(l, "#7f7f7f") for l in labels],
        edgecolor="black",
        linewidth=0.5,
    )
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel("Percentage of Questions")
    ax.invert_yaxis()

    # Add percentage labels
    total = sum(counts)
    for bar, n in zip(bars, counts):
        pct = 100 * n / total
        ax.text(
            bar.get_width() + 0.3,
            bar.get_y() + bar.get_height() / 2,
            f"{pct:.0f}%",
            va="center",
            fontsize=9,
        )

    ax.set_xlim(0, 100 * max(counts) / total + 3)
    plt.tight_layout()

    for ext in ["png", "pdf"]:
        fig.savefig(
            FIGURES_DIR / f"question_categories.{ext}",
            dpi=300,
            bbox_inches="tight",
        )
    plt.close(fig)
    print(f"\nSaved question_categories.png/pdf")


if __name__ == "__main__":
    main()
