"""
Classify ForecastBench questions into HIGH/LOW causal complexity.

Uses an LLM (default: GPT-5.4 via OpenRouter) to apply five criteria:
  1. Causal factor density (12+ interacting factors)
  2. Multi-domain spanning (3+ domains)
  3. Network structure (indirect pathways, not linear chains)
  4. Grounding in reality (identifiable actors, observable evidence)
  5. Reasoning approach (causal interaction, not simpler methods)

Questions classified as HIGH are suitable for the causal DAG probing pipeline
because they have enough causal structure to produce meaningful networks.

Outputs:
    outputs/sensitivity/causal/question_complexity.json  (full classification)
    forecast_bench/high_complexity_questions.json         (HIGH questions only)

Usage:
    python -m forecast_bench.classify_question_complexity
    python -m forecast_bench.classify_question_complexity --model openai/gpt-5.4
    python -m forecast_bench.classify_question_complexity --resume
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

BASE = Path(__file__).parent.parent
CAUSAL_DIR = BASE / "outputs" / "sensitivity" / "causal"
OUTPUT_PATH = CAUSAL_DIR / "question_complexity.json"
HIGH_COMPLEXITY_PATH = BASE / "forecast_bench" / "high_complexity_questions.json"

CLASSIFICATION_SYSTEM = """\
You are classifying forecasting questions by whether they have sufficient \
causal complexity to support a large (12-16 node) directed acyclic graph \
of interacting causal factors.

A question has HIGH causal complexity if ALL of the following are true:
1. A domain expert would naturally identify 12+ distinct, non-redundant \
causal factors that INTERACT with each other (not just a linear chain)
2. The factors span 3+ domains (e.g., Political, Economic, Social, \
Technological, Military/security, Regulatory/legal, Environmental, \
Organizational)
3. The factors form a genuine causal NETWORK — they influence each other, \
create indirect pathways, and have effects through mediating variables
4. The question is GROUNDED in real, identifiable actors, institutions, \
or measurable conditions with current observable evidence
5. The expert reasoning naturally involves understanding how factors \
interact to shape the outcome, not just checking a sequence of conditions

A question is LOW if ANY of these apply:

Ungrounded/speculative:
- The outcome is speculative with no historical precedent
- It depends on inventions or breakthroughs that do not yet exist
- The causal factors would be entirely hypothetical (sci-fi scenarios)

Simple reasoning structure:
- It is primarily time-series extrapolation ("will metric X increase?")
- The factors are mostly within a single domain
- The factors form a linear chain rather than an interacting network
- A reasonable analyst would rely on base rates, trends, or simple \
conditional reasoning

Expert methodology shortcuts (use these as guides, not hard rules):
- Statistical/actuarial: base rates, trend extrapolation, time series
- Tournament/competition: relative strength comparisons with variance
- Pipeline/stage-gate: linear progression through defined phases
- Market pricing: outcomes aggregated into asset prices

IMPORTANT: Some questions resolve as a single event (a decision, an \
action) but the CONDITIONS that determine that event emerge from a \
complex interacting network. If the context and drivers form a genuine \
multi-domain causal network — even though the resolution is a discrete \
event — classify as HIGH. The test is whether the DRIVERS interact in \
a network, not whether the outcome is binary.

Respond with ONLY valid JSON:
{"complex": true or false, "reason": "<1-2 sentences>"}"""


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


def classify_question(client, question_text: str, max_retries: int = 3) -> dict | None:
    """Classify a single question. Returns {"classification": "HIGH"/"LOW", "reason": ...}."""
    for attempt in range(max_retries):
        try:
            resp = client.chat.completions.create(
                model=client._model_id,
                messages=[
                    {"role": "system", "content": CLASSIFICATION_SYSTEM},
                    {"role": "user", "content": question_text[:2000]},
                ],
                temperature=0,
                max_tokens=200,
            )
            text = resp.choices[0].message.content.strip()
            # Parse JSON
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            data = json.loads(text)
            if "complex" in data and isinstance(data["complex"], bool):
                return {"classification": "HIGH" if data["complex"] else "LOW", "reason": data.get("reason", "")}
            if data.get("classification") in ("HIGH", "LOW"):
                return data
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                print(f"  FAILED: {e}")
    return None


def classify_batch(client, questions: list[dict], max_retries: int = 3) -> list[dict] | None:
    """Classify a batch of questions in one API call. Returns list of {complex, reason}."""
    numbered = "\n".join(f"{i+1}. {q['question'][:500]}" for i, q in enumerate(questions))
    user_prompt = f"Classify each of these {len(questions)} questions:\n\n{numbered}"

    for attempt in range(max_retries):
        try:
            resp = client.chat.completions.create(
                model=client._model_id,
                messages=[
                    {"role": "system", "content": CLASSIFICATION_SYSTEM},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0,
                max_tokens=200 * len(questions),
            )
            text = resp.choices[0].message.content.strip()
            # Parse JSON array
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            data = json.loads(text)
            if isinstance(data, list) and len(data) == len(questions):
                results = []
                for item in data:
                    if "complex" in item and isinstance(item["complex"], bool):
                        results.append({"classification": "HIGH" if item["complex"] else "LOW",
                                        "reason": item.get("reason", "")})
                    else:
                        results.append(None)
                return results
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                print(f"  BATCH FAILED: {e}")
    return None


def main():
    parser = argparse.ArgumentParser(description="Classify ForecastBench questions by causal complexity")
    parser.add_argument("--model", default="openai/gpt-5.4",
                        help="Model to use for classification (default: openai/gpt-5.4)")
    parser.add_argument("--max-questions", type=int, default=None,
                        help="Max questions to classify (default: all)")
    parser.add_argument("--resume", action="store_true",
                        help="Skip already-classified questions")
    parser.add_argument("--batch-size", type=int, default=1,
                        help="Questions per API call (default: 1, original used 25)")
    args = parser.parse_args()

    import openai

    api_key = _get_api_key()
    if not api_key:
        print("[ERROR] OPENROUTER_API_KEY not set.")
        sys.exit(1)

    client = openai.OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )
    # Store model ID for use in classify_question
    client._model_id = args.model

    # Load all ForecastBench questions
    from forecast_bench.questions import load_forecastbench_questions
    questions = load_forecastbench_questions(max_questions=500, seed=42)
    print(f"Loaded {len(questions)} ForecastBench questions")

    if args.max_questions:
        questions = questions[:args.max_questions]

    # Load existing classifications if resuming
    existing = {}
    if args.resume and OUTPUT_PATH.exists():
        existing_list = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        existing = {item["id"]: item for item in existing_list}
        print(f"Resuming: {len(existing)} already classified")

    results = []
    # Collect questions that still need classification
    todo = []
    for q in questions:
        if q["id"] in existing:
            results.append(existing[q["id"]])
        else:
            todo.append(q)

    print(f"Need to classify: {len(todo)} questions (batch_size={args.batch_size})")

    if args.batch_size > 1:
        # Batch mode
        for batch_start in range(0, len(todo), args.batch_size):
            batch = todo[batch_start:batch_start + args.batch_size]
            sys.stdout.buffer.write(f"  Batch {batch_start//args.batch_size + 1} ({len(batch)} questions)... ".encode("utf-8", errors="replace"))
            sys.stdout.buffer.flush()

            batch_results = classify_batch(client, batch)
            if batch_results is None:
                print("FAILED")
                continue

            for q, classification in zip(batch, batch_results):
                if classification is None:
                    continue
                entry = {
                    "id": q["id"],
                    "text": q["question"],
                    "complex": classification["classification"] == "HIGH",
                    "reason": classification["reason"],
                }
                results.append(entry)

            n_high = sum(1 for r in batch_results if r and r["classification"] == "HIGH")
            print(f"{n_high}/{len(batch)} HIGH")

            CAUSAL_DIR.mkdir(parents=True, exist_ok=True)
            OUTPUT_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")
            time.sleep(1)
    else:
        # Single question mode
        for i, q in enumerate(todo):
            sys.stdout.buffer.write(f"  [{i+1}/{len(todo)}] {q['question'][:60]}... ".encode("utf-8", errors="replace"))
            sys.stdout.buffer.flush()
            classification = classify_question(client, q["question"])

            if classification is None:
                print("FAILED")
                continue

            entry = {
                "id": q["id"],
                "text": q["question"],
                "complex": classification["classification"] == "HIGH",
                "reason": classification["reason"],
            }
            results.append(entry)
            print(classification["classification"])

            CAUSAL_DIR.mkdir(parents=True, exist_ok=True)
            OUTPUT_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")
            time.sleep(0.5)

    # Final save
    CAUSAL_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")

    high = [r for r in results if r["complex"]]
    low = [r for r in results if not r["complex"]]
    print(f"\nClassified {len(results)} questions: {len(high)} HIGH, {len(low)} LOW")

    # Save high-complexity questions in ForecastBench format
    high_ids = {r["id"] for r in high}
    high_questions = [q for q in questions if q["id"] in high_ids]
    HIGH_COMPLEXITY_PATH.write_text(json.dumps(high_questions, indent=2), encoding="utf-8")
    print(f"Saved {len(high_questions)} high-complexity questions to {HIGH_COMPLEXITY_PATH}")


if __name__ == "__main__":
    main()
